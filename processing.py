#processing.py
import os
import subprocess
import xml.etree.ElementTree as ET
import datetime
from ai import AI
import dotenv
import json
from simple_salesforce import Salesforce
from math import radians, sin, cos, sqrt, atan2
from PIL import Image
import exifread
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from utils import *
from logging_config import logger
from analysis import *
from bisect import bisect_left
import asyncio
import shutil
import geojson
from box import Box






dotenv.load_dotenv()

class Processor():
    FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"
    FFPROBE_PATH = "/opt/homebrew/bin/ffprobe"
    TEMP_BIN_FILE = "temp_metadata.bin"
    TEMP_GPX_FILE = "temp_metadata.gpx"

    def __init__(self, mode="video", box: Box=None):
        self.ensure_ffmpeg_installed()
        self.ai = AI(os.getenv("OPENAI_API_KEY"))
        self.box: Box = box
        self.video_fps = None
        self.analysis_frames_per_second = None
        self.analysis_max_frames = None
        self.analysis_batch_size = None
        self.seconds_analyzed = None
        self.minutes_analyzed = None
        self.base_timestamp = None
        self.processing_status = "Idle"
        self.processing_stages = {
            "Metadata": "Pending",
            "Frame Extraction": "Pending",
            "Analysis Prep": "Pending",
            "AI Analysis": "Pending",
            "Finalization": "Pending"
        }
        self.mode = mode

    @staticmethod
    def ensure_ffmpeg_installed():
        """Ensure ffmpeg and ffprobe are installed and accessible."""
        if not os.path.exists(Processor.FFMPEG_PATH) or not os.path.exists(Processor.FFPROBE_PATH):
            raise FileNotFoundError("Ensure ffmpeg and ffprobe are installed and paths are correct.")
        logger.info(f"ffmpeg and ffprobe are installed and paths are correct.")

    def save_pipeline_settings(self, frame_rate, max_frames, batch_size):
        self.analysis_frames_per_second = frame_rate
        self.analysis_max_frames = max_frames
        self.analysis_batch_size = batch_size

    def validate_video_file(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file '{file_path}' not found.")
        logger.info(f"Video file {file_path} found and validated.")

    def extract_all_metadata(self, mp4_file_path):  # Runs at the start of the program
        """Extracts binary metadata and converts it to GPX format."""
        logger.info(f"Extracting metadata from {mp4_file_path}...")
        try:
            # Extract binary metadata
            subprocess.run(
                [Processor.FFMPEG_PATH, "-y", "-i", mp4_file_path, "-codec", "copy", "-map", "0:2", "-f", "rawvideo", Processor.TEMP_BIN_FILE],
                check=True
            )
            logger.info(f"Extracted binary metadata to {Processor.TEMP_BIN_FILE}.")
            logger.info(f"TEMP_GPX_FILE: {Processor.TEMP_GPX_FILE}")

            # Generate GPX file
            gpx_prefix = os.path.splitext(Processor.TEMP_GPX_FILE)[0]
            logger.info(f"GPX prefix: {gpx_prefix}")
            gopro2gpx_path = shutil.which("gopro2gpx")

            if not gopro2gpx_path:
                raise FileNotFoundError("gopro2gpx not found. Ensure the virtual environment is activated!")

            result = subprocess.run(
                ["gopro2gpx", "-s", "-vv", mp4_file_path, gpx_prefix]
            )

            if result.returncode != 0:
                logger.error(f"gopro2gpx failed with error:\n{result.stderr}")
                raise RuntimeError(f"gopro2gpx failed. See logs for details.")
            logger.info(f"Generated GPX file {Processor.TEMP_GPX_FILE}.")

            # Check GPX file size and number of trackpoints
            if not os.path.exists(Processor.TEMP_GPX_FILE):
                raise FileNotFoundError(f"GPX file {Processor.TEMP_GPX_FILE} not created.")\
                
            self._save_gpx_to_folder(mp4_file_path)
            
            tree = ET.parse(Processor.TEMP_GPX_FILE)
            root = tree.getroot()
            namespaces = {'default': 'http://www.topografix.com/GPX/1/1'}
            trkpts = root.findall('.//default:trkpt', namespaces)
            
            if len(trkpts) == 0:
                raise ValueError(f"GPX file {Processor.TEMP_GPX_FILE} contains no trackpoints.")

            logger.info(f"Extracted metadata from {mp4_file_path}. GPX contains {len(trkpts)} trackpoints.")

            tree = ET.parse(Processor.TEMP_GPX_FILE)
            root = tree.getroot()

            namespaces = {'default': 'http://www.topografix.com/GPX/1/1'}
            metadata_time = root.find('./default:metadata/default:time', namespaces)

            if metadata_time is not None:
                base_time = datetime.datetime.strptime(metadata_time.text.strip(), '%Y-%m-%dT%H:%M:%S.%fZ')
                self.base_timestamp = base_time
                logger.info(f"Base timestamp extracted from GPX: {base_time}")
        except Exception as e:
            logger.exception(f"Failed to extract metadata: {e}")
            raise
    
    def _save_gpx_to_folder(self, video_filename):
        """Save the GPX file into a GPX_files/ folder with a video-based name."""
        gpx_folder = "GPX_files"
        os.makedirs(gpx_folder, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(video_filename))[0]
        dest_path = os.path.join(gpx_folder, f"{base_name}.gpx")

        shutil.copy2(Processor.TEMP_GPX_FILE, dest_path)
        logger.info(f"Copied GPX file to {dest_path}")

    @staticmethod
    def cleanup_temp_files(*files):
        """Remove temporary files."""
        for file in files:
            if os.path.exists(file):
                os.remove(file)

        # Clear out the frames folder
        if os.path.exists("frames"):
            frames = os.listdir("frames")
            for frame in frames:
                os.remove(f"frames/{frame}")

        # Remove specific temporary files if they exist
        for temp_file in ["temp_metadata.bin", "temp_metadata.gpx", "temp_metadata.kml"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def preprocess_gpx_file(self):
        """Preprocess the GPX file to extract and sort all timestamps with telemetry data."""
        try:
            tree = ET.parse(Processor.TEMP_GPX_FILE)
            root = tree.getroot()

            namespaces = {
                'default': 'http://www.topografix.com/GPX/1/1',
                'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v2'
            }

            telemetry_data = []

            for trkpt in root.findall('.//default:trkpt', namespaces):
                time_element = trkpt.find('default:time', namespaces)
                if time_element is not None:
                    # Parse and truncate microseconds
                    timestamp = datetime.datetime.strptime(time_element.text.strip(), '%Y-%m-%dT%H:%M:%S.%fZ')
                    timestamp = timestamp.replace(microsecond=0)  # Drop microseconds
                    telemetry = {
                        'timestamp': timestamp,
                        'lat': float(trkpt.attrib.get('lat', 0.0)),
                        'lon': float(trkpt.attrib.get('lon', 0.0)),
                        'elevation': trkpt.findtext('default:ele', "N/A", namespaces),
                        'heart_rate': trkpt.findtext('.//gpxtpx:hr', "N/A", namespaces),
                        'speed': trkpt.findtext('.//gpxtpx:speed', "N/A", namespaces)
                    }
                    telemetry_data.append(telemetry)

            # Sort telemetry data by timestamp
            telemetry_data.sort(key=lambda x: x['timestamp'])
            logger.info(f"Preprocessed and sorted {len(telemetry_data)} telemetry data points.")
            return telemetry_data

        except FileNotFoundError:
            logger.error("GPX file not found.")
            return []
        
    @staticmethod
    def convert_to_gpx_timestamp(self, seconds):
        """
        Convert a timestamp in seconds to ISO 8601 format.
        Example: 15.5 seconds -> '2024-09-26T16:37:34.500000Z'
        """
        base_time = self.base_timestamp
        delta = datetime.timedelta(seconds=seconds)
        target_time = base_time + delta
        return target_time.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ') 
    
    def get_base_timestamp_from_gpx(self):
        """
        Extract the base timestamp from the <metadata><time> element in the GPX file.
        Returns:
            datetime: The base timestamp as a datetime object.
        """
        try:
            tree = ET.parse(Processor.TEMP_GPX_FILE)
            root = tree.getroot()

            namespaces = {'default': 'http://www.topografix.com/GPX/1/1'}
            metadata_time = root.find('./default:metadata/default:time', namespaces)

            if metadata_time is not None:
                base_time = datetime.datetime.strptime(metadata_time.text.strip(), '%Y-%m-%dT%H:%M:%S.%fZ')
                logger.info(f"Base timestamp extracted from GPX: {base_time}")
                return base_time
            else:
                raise ValueError("No <time> element found in <metadata>.")

        except Exception as e:
            logger.error(f"Failed to extract base timestamp from GPX file: {e}")
            raise

    def extract_all_frames_ffmpeg(self, video_path, output_folder="frames", crop_top=0):
        """
        Extracts **all** frames from a video using FFmpeg.
        
        Args:
            video_path (str): Path to the video file.
            output_folder (str): Directory to save extracted frames.
            crop_top (int): Number of pixels to crop from the top.
        
        Returns:
            list[tuple]: List of tuples containing frame file paths and timestamps.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Get video metadata using FFprobe
        command = [
            self.FFPROBE_PATH,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,nb_frames,avg_frame_rate",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)

        # Get video width and height
        video_width = int(metadata["streams"][0]["width"])
        video_height = int(metadata["streams"][0]["height"])

        # Ensure crop height is valid
        crop_height = video_height - crop_top
        if crop_height <= 0:
            raise ValueError(f"Invalid crop height: {crop_height}. Ensure crop_top is not greater than video height.")

        # Extract **all** frames using FFmpeg
        ffmpeg_command = [
            self.FFMPEG_PATH,
            "-i", video_path,  # Input video
            "-vsync", "0",  # Extract every frame
            "-frame_pts", "1",  # Preserve frame order
            "-vf", f"crop={video_width}:{crop_height}:0:{crop_top}",  # Crop if needed
            "-q:v", "2",  # High-quality frames
            os.path.join(output_folder, "frame_%04d.jpg")  # Save frames sequentially
        ]

        try:
            subprocess.run(ffmpeg_command, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed with error: {e}")
            raise RuntimeError("Failed to extract frames using FFmpeg.")

        # Generate frame file paths
        extracted_frames = [
            (os.path.join(output_folder, f"frame_{i+1:04d}.jpg"), i)  # No timestamps, just frame index
            for i in range(len(os.listdir(output_folder)))
        ]

        logger.info(f"Extracted {len(extracted_frames)} frames to {output_folder}.")
        return extracted_frames
    
    def extract_frames_ffmpeg(self, video_path, frame_rate=1, output_folder="frames", max_frames=None, crop_top=360):
        """
        Extract frames at specific intervals from a video using FFmpeg, respecting max_frames.
        Args:
            video_path (str): Path to the video file.
            frame_rate (int): Frames per second to extract.
            output_folder (str): Directory to save extracted frames.
            max_frames (int): Maximum number of frames to extract.
        Returns:
            list[tuple]: List of tuples containing frame file paths and timestamps.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Get video metadata using FFprobe
        command = [
            self.FFPROBE_PATH,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,nb_frames,avg_frame_rate",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)

        # Calculate total frames and FPS from metadata
        total_frames = int(metadata["streams"][0]["nb_frames"])
        avg_frame_rate = metadata["streams"][0]["avg_frame_rate"]
        fps = int(eval(avg_frame_rate))  # Handles fractional frame rates like "30000/1001"

        # Pre-calculate frame timestamps
        frame_interval = max(1, round(fps / frame_rate))
        target_indices = list(range(0, total_frames, frame_interval))
        if max_frames:
            target_indices = target_indices[:max_frames]

        # Convert frame indices to timestamps
        timestamps = [index / fps for index in target_indices]

        # Get original video width and height
        video_width = int(metadata["streams"][0]["width"])
        video_height = int(metadata["streams"][0]["height"])

        # Ensure crop height is valid
        crop_height = video_height - crop_top
        if crop_height <= 0:
            raise ValueError(f"Invalid crop height: {crop_height}. Ensure crop_top is not greater than video height.")

        # Build FFmpeg command to extract specific frames using the 'select' filter
        select_filter = "+".join([f"eq(n\\,{index})" for index in target_indices])
        video_basename = os.path.splitext(os.path.basename(video_path))[0]

        ffmpeg_command = [
            self.FFMPEG_PATH,
            "-i", video_path,
            "-map", "0:v:0",  # Process only the video stream
            "-an",  # Disable audio processing
            "-vf", f"select='{select_filter}',setpts=N/FRAME_RATE/TB,crop={video_width}:{crop_height}:0:{crop_top}",  # Select specific frames
            "-vsync", "vfr",  # Variable frame rate
            "-frames:v", str(len(target_indices)),  # Stop after extracting the desired frames
            os.path.join(output_folder, f"{video_basename}_%04d.jpg")  # Save frames sequentially
        ]

        # Run the FFmpeg command and handle errors
        try:
            subprocess.run(ffmpeg_command, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed with error: {e}")
            raise RuntimeError("Failed to extract frames using FFmpeg.")

        # Generate frame file paths and return them with timestamps
        extracted_frames = [
            (os.path.join(output_folder, f"{video_basename}_{i+1:04d}.jpg"), timestamps[i])
            for i in range(len(timestamps))
        ]
        logger.info(f"Extracted {len(extracted_frames)} frames to {output_folder}.")
        return extracted_frames
        
    def create_telemetry_objects(self, extracted_frame_tuples: list, video_path: str='Default'): #Runs once, using all extracted_frame_tuples collected in extract_frames
        telemetry_objects = []

        for frame in extracted_frame_tuples:
            telemetry_object = self._create_telemetry_object(frame, video_path=video_path)
            telemetry_objects.append(telemetry_object)

        logger.info(f"Created {len(telemetry_objects)} telemetry objects with frame image filename and timestamp data. ")
        return telemetry_objects
    
    def _create_telemetry_object(self, extracted_frame_tuple: tuple, video_path: str=None): #Runs for each extracted_frame_tuple in create_telemetry_objects
        name = os.path.basename(extracted_frame_tuple[0])
        timestamp = extracted_frame_tuple[1]
        filepath = extracted_frame_tuple[0]
        telemetry_object = TelemetryObject(filename=name, filepath=filepath, timestamp=timestamp, source_video=video_path)
        print(f"{telemetry_object = }")
        return telemetry_object

    def add_coords_to_telemetry_objects(self, telemetry_objects: list): #Runs once, using all telemetry_objects created in create_telemetry_objects
        telemetry_objects = telemetry_objects

        for object in telemetry_objects: 
            self._add_coords_to_telemetry_object(object)

        logger.info(f"Collected and saved coordinates for {len(telemetry_objects)} telemetry objects.")
        return telemetry_objects
    
    def _add_coords_to_telemetry_object(self, telemetry_object): #Runs for each telemetry_object in add_coords_to_telemetry_objects
        timestamp = self.convert_to_gpx_timestamp(self, telemetry_object.timestamp)
        telemetry = self.get_telemetry_for_timestamp_binary(timestamp, self.telemetry_data)
        telem_lat = telemetry.get('lat', 0.0)
        telem_lon = telemetry.get('lon', 0.0)
        telemetry_object.lat = telem_lat
        telemetry_object.lon = telem_lon
        telemetry_object.timestamp = timestamp
        return telemetry_object

    def get_telemetry_for_timestamp_binary(self, target_time, telemetry_data) -> dict:
        """
        Find the GPS telemetry closest to the specified timestamp using binary search.
        
        Args:
            target_time (str): Target timestamp in ISO 8601 format.
            telemetry_data (list): Preprocessed list of telemetry data, sorted by timestamp.
            
        Returns:
            dict: Telemetry data closest to the target timestamp.
        """
        try:
            # Parse and truncate microseconds
            target_time_dt = datetime.datetime.strptime(target_time, '%Y-%m-%dT%H:%M:%SZ')
            target_time_dt = target_time_dt.replace(microsecond=0)

            # Extract all timestamps from telemetry data
            timestamps = [entry['timestamp'] for entry in telemetry_data]

            # Use binary search to find the closest timestamp
            pos = bisect_left(timestamps, target_time_dt)

            if pos == 0:
                # Target is earlier than all data points; return the first
                closest_entry = telemetry_data[0]
            elif pos == len(timestamps):
                # Target is later than all data points; return the last
                closest_entry = telemetry_data[-1]
            else:
                # Check the two closest points (before and after the target)
                before = telemetry_data[pos - 1]
                after = telemetry_data[pos]
                if abs(before['timestamp'] - target_time_dt) <= abs(after['timestamp'] - target_time_dt):
                    closest_entry = before
                else:
                    closest_entry = after

            return closest_entry

        except Exception as e:
            logger.error(f"Error finding telemetry for {target_time}: {e}")
            return {
                'lat': 0.0,
                'lon': 0.0,
                'elevation': 0,
                'heart_rate': 0,
                'speed': 0
            }
        
    def get_telemetry_for_timestamp(self, target_time) -> dict:
        """Extract GPS coordinates closest to a specified timestamp from the GPX file."""
        try:
            tree = ET.parse(Processor.TEMP_GPX_FILE)
            root = tree.getroot()

            namespaces = {
                'default': 'http://www.topografix.com/GPX/1/1',
                'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v2'
            }

            for trkpt in root.findall('.//default:trkpt', namespaces):
                time_element = trkpt.find('default:time', namespaces)
                if time_element is not None and time_element.text == target_time:
                    telemetry = {
                        'lat': trkpt.attrib.get('lat', 0.0),
                        'lon': trkpt.attrib.get('lon', 0.0),
                        'elevation': trkpt.findtext('default:ele', "N/A", namespaces),
                        'heart_rate': trkpt.findtext('.//gpxtpx:hr', "N/A", namespaces),
                        'speed': trkpt.findtext('.//gpxtpx:speed', "N/A", namespaces)
                    }
                    return telemetry

            logger.error("No matching telemetry data found.")
            errored_telemetry = {
                'lat': 0.0,
                'lon': 0.0,
                'elevation': 0,
                'heart_rate': 0,
                'speed': 0
            }
            return errored_telemetry

        except FileNotFoundError:
            logger.error("GPX file not found.")
            return None

    """
    By this time, the telemetry_objects have been created for each extracted frame and look something like this: 

    TelemetryObject
    self.filename = '2025-01-21_frame_10_12.34.jpg'
    self.filepath = 'extracted_frames/2025-01-21_frame_10_12.34.jpg'
    self.timestamp = '<whatever the gpx timestamp format is>'
    self.lat = -73.102857
    self.lon = 44.187568
    self.openai_file_id: str = None
    self.analysis_results: dict = None
    
    Next on the agenda: 
        - Upload files to OpenAI
        - Prepare messages for OpenAI
        - Assemble/Send messages to OpenAI
        - Parse the results from OpenAI
        - Add analyses to the TelemetryObjects
        - profit
    """
        
    def get_ai_analyses(self, telemetry_objects: list, batch_size: int=3) -> list:
        analyzed_telem_objects, file_upload_start, image_analysis_start = self.ai.analyze_images_with_ai(telemetry_objects=telemetry_objects, batch_size=batch_size, multithreaded=True)
        logger.info(f"Successfully analyzed {len(analyzed_telem_objects)} frames with AI.")
        return analyzed_telem_objects

    def save_telemetry_objects(self, telemetry_objects: list):
        """
        Save each telemetry object as a JSON file in the same folder as the frame JPG.

        Args:
            telemetry_objects (list): List of telemetry objects.
        """

        print(f'{telemetry_objects = }')

        flat_telemetry_objects = []
        for item in telemetry_objects:
            if isinstance(item, list):
                flat_telemetry_objects.extend(item)
            else:
                flat_telemetry_objects.append(item)

        work_order_folder = "work_order_frames"
        os.makedirs(work_order_folder, exist_ok=True)

        

        for obj in flat_telemetry_objects:
            video_base = os.path.splitext(os.path.basename(obj.source_video))[0]
            frame_base = os.path.splitext(os.path.basename(obj.filepath))[0]
            json_filename = f"{video_base}_{frame_base}.json"
            json_path = os.path.join(os.path.dirname(obj.filepath), json_filename)

            telemetry_data = {
                "filename": obj.filename,
                "filepath": obj.filepath,
                "source_video": obj.source_video,
                "timestamp": obj.timestamp,
                "lat": obj.lat,
                "lon": obj.lon,
                "openai_file_id": obj.openai_file_id,
                "box_file_id": obj.box_file_id,
                "box_file_url": obj.box_file_url,
                "analysis_results": obj.analysis_results
            }
            with open(json_path, "w") as json_file:
                json.dump(telemetry_data, json_file, indent=4)

            # Check pothole criteria
            ai_analysis = obj.analysis_results or {}
            pothole = ai_analysis.get("pothole", "no")
            pothole_confidence = ai_analysis.get("pothole_confidence", 0)

            if pothole == "yes" and pothole_confidence >= 0.9:
                # Copy frame and metadata JSON to work_order_frames/
                work_order_frame_path = os.path.join(work_order_folder, os.path.basename(obj.filepath))

                shutil.copy2(obj.filepath, work_order_frame_path)

                logger.info(f"Copied {obj.filename} to work_order_frames/ (Pothole confidence: {pothole_confidence})")

        logger.info(f"Saved {len(telemetry_objects)} telemetry objects as JSON files.")

    def save_overview_json(self, telemetry_objects: list, output_path="overview.json"):
        """
        Save an overview JSON file with summary statistics, counts of 'yes' values, 
        PCI score histograms, and filenames for pothole detections.

        Args:
            telemetry_objects (list): List of telemetry objects.
            output_path (str): Path to save the overview JSON file.
        """
        num_objects = len(telemetry_objects)
        stats = {
            "total_frames": num_objects,
            "average_pothole_confidence": 0.0,
            "average_alligator_cracking_confidence": 0.0,
            "average_line_cracking_confidence": 0.0,
            "average_debris_confidence": 0.0,
            "road_health_index_average": 0.0,
            "counts": {
                "pothole": 0,
                "line_cracking": 0,
                "alligator_cracking": 0,
                "debris": 0,
            },
            "pci_histogram": {
                "0-19": 0,
                "20-39": 0,
                "40-59": 0,
                "60-79": 0,
                "80-100": 0,
            },
            "pothole_filenames": [],
            "pothole_details": [],
        }

        if num_objects > 0:
            # Gather analysis data
            pothole_confidences = []
            alligator_cracking_confidences = []
            line_cracking_confidences = []
            debris_confidences = []
            road_health_indices = []

            for obj in telemetry_objects:
                analysis = obj.analysis_results
                pothole_confidences.append(analysis.get("pothole_confidence", 0.0))
                alligator_cracking_confidences.append(analysis.get("alligator_cracking_confidence", 0.0))
                line_cracking_confidences.append(analysis.get("line_cracking_confidence", 0.0))
                debris_confidences.append(analysis.get("debris_confidence", 0.0))
                road_health_indices.append(analysis.get("road_health_index", 0))

                # Count 'yes' values for each category
                if analysis.get("pothole") == "yes":
                    stats["counts"]["pothole"] += 1
                    stats["pothole_filenames"].append(obj.filename)
                    stats["pothole_details"].append(obj.to_dict())
                if analysis.get("line_cracking") == "yes":
                    stats["counts"]["line_cracking"] += 1
                if analysis.get("alligator_cracking") == "yes":
                    stats["counts"]["alligator_cracking"] += 1
                if analysis.get("debris") == "yes":
                    stats["counts"]["debris"] += 1

                # Categorize PCI scores into histogram ranges
                pci_score = analysis.get("road_health_index", 0)
                if 0 <= pci_score <= 19:
                    stats["pci_histogram"]["0-19"] += 1
                elif 20 <= pci_score <= 39:
                    stats["pci_histogram"]["20-39"] += 1
                elif 40 <= pci_score <= 59:
                    stats["pci_histogram"]["40-59"] += 1
                elif 60 <= pci_score <= 79:
                    stats["pci_histogram"]["60-79"] += 1
                elif 80 <= pci_score <= 100:
                    stats["pci_histogram"]["80-100"] += 1

            # Calculate averages
            stats["average_pothole_confidence"] = sum(pothole_confidences) / num_objects
            stats["average_alligator_cracking_confidence"] = sum(alligator_cracking_confidences) / num_objects
            stats["average_line_cracking_confidence"] = sum(line_cracking_confidences) / num_objects
            stats["average_debris_confidence"] = sum(debris_confidences) / num_objects
            stats["road_health_index_average"] = sum(road_health_indices) / num_objects

        # Save to overview.json
        with open(output_path, "w") as json_file:
            json.dump(stats, json_file, indent=4)
        logger.info(f"Saved overview statistics to {output_path}.")

    def save_full_list(self, telemetry_objects: list, output_path='default_all_frames.json'):
        analyses = []
        
        for object in telemetry_objects:
            dict_version = object.to_dict()
            analyses.append(dict_version)

        with open(output_path, "w") as json_file:
            json.dump(analyses, json_file, indent=4)
        logger.info(f"Saved all analyses in {output_path}.")
    
    def calculate_video_coverage(self, telemetry_objects: list):
        num_frames = len(telemetry_objects)
        video_fps = self.video_fps
        analysis_frames_per_second = self.analysis_frames_per_second
        seconds_analyzed = round(num_frames / analysis_frames_per_second)
        minutes_analyzed = seconds_analyzed // 60
        self.seconds_analyzed = seconds_analyzed
        self.minutes_analyzed = minutes_analyzed

    def update_stage(self, stage_name, status):
        """
        Updates the processing stage status.

        Args:
            stage_name (str): The stage being updated.
            status (str): New status ('Pending', 'In Progress', 'Complete').
        """
        if stage_name in self.processing_stages:
            self.processing_stages[stage_name] = status
            logger.info(f"Stage Updated: {stage_name} → {status}")
        else:
            logger.warning(f"Attempted to update an unknown stage: {stage_name}")

    async def process_video_pipeline(self, video_path, frame_rate=0.5, max_frames=None, batch_size=6, mode="timelapse"):
        """
        Process a video end-to-end, extracting frames, creating telemetry objects,
        analyzing them with OpenAI, and saving results.

        Args:
            video_path (str): Path to the video file.
            frame_rate (int): Frames per second to extract.
            max_frames (int): Maximum number of frames to extract.
            batch_size (int): Number of telemetry objects per AI analysis batch.

        Returns:
            list: Fully processed telemetry objects with analysis results.
        """
        
        self.mode = mode
        log_file = "pipeline_timing_log.txt"
        file_name = video_path
        
        # update the video path to pull from unprocessed_videos/ for Non-Greenway mode
        video_path = f"unprocessed_videos/{video_path}"
        #video_path = f"unprocessed_greenway_videos/{video_path}"

        with open(log_file, "w") as log:
            log.write("Stage Timing Log:\n")
        
        def log_timing(stage, start_time):
            duration = time.time() - start_time
            message = f"{stage} took {duration:.2f} seconds\n"
            logger.info(message.strip())
            with open(log_file, "a") as log:
                log.write(message)
            return duration
        
        try:
            self.update_stage("Metadata", "In Progress")
            total_start_time = time.time()

            # Step 0: Save settings to self
            stage_start = time.time()
            self.save_pipeline_settings(frame_rate=frame_rate, max_frames=max_frames, batch_size=batch_size)
            log_timing("Step 0: Save pipeline settings", stage_start)

            # Step 1: Validate the video file

            stage_start = time.time()
            logger.info("Step 1: Validate the video file")
            self.validate_video_file(video_path)
            log_timing("Step 1: Validate the video file", stage_start)

            # Step 2: Extract metadata and prepare GPX
            stage_start = time.time()
            logger.info("Step 2: Extract metadata and prepare GPX")
            self.extract_all_metadata(video_path)
            log_timing("Step 2: Extract metadata and prepare GPX", stage_start)

            self.update_stage("Metadata", "Complete")
            self.update_stage("Frame Extraction", "In Progress")

            # Step 3: Extract frames from the video
            
            stage_start = time.time()
            logger.info("Step 3: Extract frames from the video")
            if self.mode == "timelapse":
                extracted_frames = self.extract_all_frames_ffmpeg(
                    video_path=video_path,
                    output_folder="frames",
                    crop_top=360  # Crop top for GoPro videos
                )
            elif self.mode == "video":
                extracted_frames = self.extract_frames_ffmpeg(
                    video_path=video_path,
                    frame_rate=frame_rate,
                    max_frames=max_frames
                )
            log_timing("Step 3: Extract frames from the video", stage_start)

            self.update_stage("Frame Extraction", "Complete")
            self.update_stage("Analysis Prep", "In Progress")

            # Step 4: Create telemetry objects for extracted frames
            stage_start = time.time()
            logger.info("Step 4: Create telemetry objects for extracted frames")
            telemetry_objects = self.create_telemetry_objects(extracted_frames, video_path)
            log_timing("Step 4: Create telemetry objects", stage_start)

            # Step 5: Add GPS coordinates to telemetry objects
            stage_start = time.time()
            logger.info("Step 5: Add GPS coordinates to telemetry objects")
            self.telemetry_data = self.preprocess_gpx_file()
            telemetry_objects = self.add_coords_to_telemetry_objects(telemetry_objects)
            log_timing("Step 5: Add GPS coordinates", stage_start)

            self.update_stage("Analysis Prep", "Complete")
            self.update_stage("AI Analysis", "In Progress")

            # Step 6: Perform AI analysis on telemetry objects

            stage_start = time.time()
            logger.info("Step 6: Perform AI analysis on telemetry objects")
            telemetry_objects = self.get_ai_analyses(telemetry_objects, batch_size=batch_size)
            log_timing("Step 6: Analyze files with AI", stage_start)

            # Step 7: Save telemetry objects as individual JSON files
            stage_start = time.time()
            logger.info("Step 7: Save telemetry objects as individual JSON files")
            self.save_telemetry_objects(telemetry_objects)
            log_timing("Step 7: Save telemetry objects", stage_start)

            self.update_stage("AI Analysis", "Complete")
            self.update_stage("Finalization", "In Progress")

            # Step 8: Create and save an overview.json file
            stage_start = time.time()
            logger.info("Step 8: Create and save an overview.json file")
            self.save_overview_json(telemetry_objects)
            self.save_full_list(telemetry_objects=telemetry_objects)
            log_timing("Step 8: Create and save overview.json and all_frame_analyses.json", stage_start)

            # Step 9: Cleanup files and archive data in Box
            logger.info("Step 9: Cleanup files and archive data in Box")
            self.cleanup_temp_files(Processor.TEMP_GPX_FILE)
            await self.box.save_frames_to_long_term_storage(telemetry_objects=telemetry_objects, greenway_mode=False, video_path=video_path)


            # Finalize
            total_duration = time.time() - total_start_time
            logger.info("Video processing pipeline completed successfully.")
            self.calculate_video_coverage(telemetry_objects)
            logger.info(f"Analyzed {len(telemetry_objects)} frames, covering {self.minutes_analyzed} minutes of footage.")
            with open(log_file, "a") as log:
                log.write(f"Total pipeline duration: {total_duration:.2f} seconds\n")

            self.update_stage("Finalization", "Complete")
            
            return telemetry_objects

        except Exception as e:
            logger.error(f"Error in video processing pipeline: {e}")
            raise

class TelemetryObject:
    def __init__(self, filename: str=None, filepath: str=None, timestamp: str=None, lat: float=None, lon: float=None, source_video: str=None):
        self.filename = filename
        self.filepath = filepath
        self.timestamp = timestamp
        self.lat = lat # y
        self.lon = lon # x
        self.openai_file_id: str = None
        self.box_file_id: str = None
        self.box_file_url: str = None
        self.analysis_results: dict = {}
        self.source_video: str = source_video

    def to_dict(self):
        return {'filename': self.filename,
                'filepath': self.filepath,
                'source_video': self.source_video,
                'timestamp': self.timestamp,
                'lat': self.lat,
                'lon': self.lon,
                'openai_file_id': self.openai_file_id,
                'box_file_id': self.box_file_id,
                'box_file_url': self.box_file_url,
                'analysis_results': self.analysis_results
                }
    
    def to_metadata_dict(self):
        return {
            "filename": self.filename,
            "timestamp": f'{self.timestamp}',
            "lat1": f'{self.lat}',
            "lon1": f'{self.lon}',
            "pothole": [self.analysis_results['pothole'].capitalize()],  # must be a list
            "potholeConfidence": str(self.analysis_results['pothole_confidence']),
            "alligatorCracking": [self.analysis_results['alligator_cracking'].capitalize()],
            "alligatorCrackingConfidence": str(self.analysis_results['alligator_cracking_confidence']),
            "lineCracking": [self.analysis_results['line_cracking'].capitalize()],
            "lineCrackingConfidence": str(self.analysis_results['line_cracking_confidence']),
            "debris": [self.analysis_results['debris'].capitalize()],
            "summary": self.analysis_results['summary'],
            "roadHealthIndex": str(self.analysis_results['road_health_index'])
        }

    def add_openai_file_id(self, file_id):
        self.openai_file_id = file_id

    def add_analysis_results(self, analysis):
        self.analysis_results = analysis
    
    def add_box_file_id(self, file_id):
        self.box_file_id = file_id
    
    def add_box_file_url(self, url):
        self.box_file_url = url

    def to_geojson(self):
        """Convert telemetry object to a GeoJSON Feature."""
        if self.lon is None or self.lat is None:
            raise ValueError(f"Telemetry object {self.filename} is missing coordinates.")

        geojson_object = None
        geom = geojson.Point((self.lon, self.lat))
        
        # Flatten analysis_results into the properties
        props = {
            "filename": self.filename,
            "filepath": self.filepath,
            "source_video": self.source_video,
            "timestamp": self.timestamp,
            "openai_file_id": self.openai_file_id,
            "box_file_id": self.box_file_id,
            "box_file_url": self.box_file_url,
        }
        if self.analysis_results:
            props.update(self.analysis_results)  # Merge analysis_results into props

        geojson_object = geojson.Feature(
            geometry=geom,
            properties=props
        )

        return geojson_object

if __name__ == "__main__":
    # Example video file path
    video_file = "GX010229.MP4"
    photo_folder = "unprocessed_photos"

    # Initialize the Processor
    processor = Processor()
    processor.mode = "timelapse"

    # Execute the pipeline
    start_time = time.time()
    
    telem_objs = processor.process_video_pipeline(video_path=video_file, frame_rate=1, max_frames=10, batch_size=3)
    print(f'Telemetry objects: {telem_objs}')
 
    
    end_time = time.time()

    # Print execution time
    elapsed_time = end_time - start_time
    print(f"Pipeline completed in {elapsed_time:.2f} seconds.")