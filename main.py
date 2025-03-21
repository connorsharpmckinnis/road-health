from flask import Flask, request, jsonify
from ai import AI
from box import Box
from salesforce import WorkOrderCreator
from processing import Processor
import utils
import dotenv
import os
from logging_config import logger
import time
import shutil
import threading
from web_ui import StatusUpdate, WebApp
import asyncio
import json


dotenv.load_dotenv()


flask_app = Flask(__name__)

class App():
    def __init__(self, web_app: WebApp):
        """Initialize App with reference to WebApp."""
        self.web_app = web_app  # ✅ Store WebApp instance
        self.status = "Monitoring Inactive"
        self.monitoring_active = False
        self.monitoring_status = "Idle"
        self.box = None
        self.processor = None
        self.work_order_creator = None
        self.processed_videos = set()
        self.all_files = []
        self.telemetry_objects = None
        self.downloaded_but_unprocessed = []
        self.time_to_check = None
        self.processing_status = {}

    async def initialize(self):
        """Run initialization logic and send status updates."""
        
        print("Initalizing")

        # ✅ Start up core services (ensure async methods are awaited)
        self.startup_box_client()
        self.startup_processor()
        self.startup_work_order_creator()
        self.load_processed_videos()


    def startup_box_client(self):
        self.box = Box(web_app=self.web_app)

    def startup_processor(self):
        self.frame_processor = Processor(web_app=self.web_app)

    def startup_work_order_creator(self):
        self.work_order_creator = WorkOrderCreator(web_app=self.web_app)

    def load_processed_videos(self):
        try:
            with open('processed_files.log', 'r') as f:
                self.processed_videos = set(f.read().splitlines())
        except FileNotFoundError:
            self.processed_videos = set()

    def load_downloaded_but_unprocessed_videos(self):
        self.downloaded_but_unprocessed = os.listdir("unprocessed_videos")

    async def send_status_update_to_ui(self, source, type, level, status, message, details={}):
        """Send a status update to the UI properly using WebSockets."""
        if self.web_app:
            await self.web_app.send_status_update(
                source=source,
                type=type,
                level=level,
                status=status,
                message=message,
                details=details
            )
    
    def save_processed_videos(self):
        """Save processed files to a log to prevent reprocessing."""
        with open("processed_files.log", "w") as f:
            f.write("\n".join(sorted(self.processed_videos)))  # Sort for readability

    async def pipeline(self, new_files_to_download: list=None):
        self.status = 'Running pipeline...'
        logger.info(f"Starting pipeline. Downloading files...")
        
        # 📣 Send program status update with countdown
        await self.send_status_update_to_ui(
            source='App.pipeline()',
            level='Section',
            type='Video',
            status="Downloading Files",
            message=f"Downloading {len(new_files_to_download)} files."
        )

        for file in new_files_to_download:
            # 📣 Send video card status update with downloading
            await self.send_status_update_to_ui(
                source='App.pipeline()',
                level='Card',
                type='Video',
                status="In Progress",
                message=f"Downloading file",
                details={
                    "video_file": file['name'],
                    "progress": "20%",
                    "stage": "Downloading"
                }
            )
        
        download_files_result = await self.download_files(new_files_to_download)
        if download_files_result:
            logger.info(f"Downloaded {len(self.all_files)} files.\n Processing...")

        for file in new_files_to_download:
            # 📣 Send video card status update with waiting
            await self.send_status_update_to_ui(
                source='App.pipeline()',
                level='Card',
                type='Video',
                status="Inactive",
                message=f"Waiting patiently for its turn",
                details={
                    "video_file": file['name'],
                    "progress": "0%"
                }
            )
        
        #check if there are files to process in the unprocessed_videos folder
        files_to_process = os.listdir("unprocessed_videos")
        self.processed_videos = set()

        #establish processing status for each file
        self.processing_status = {file: {"stage": "Queued", "status": "Waiting to Start"} for file in files_to_process}

        if not files_to_process:
            self.status = "Idle - No files to process."
            logger.info("No files to process. Exiting pipeline.")
            return

        # 📣 Send program status update with countdown
        await self.send_status_update_to_ui(
            source='App.pipeline()',
            level='Section',
            type='Video',
            status="In Progress",
            message=f"Processing {len(new_files_to_download)} files."
        )
        for file in files_to_process:
            # 📣 Send video card status update with initial processing
            await self.send_status_update_to_ui(
                source='App.pipeline()',
                level='Card',
                type='Video',
                status="In Progress",
                message=f"Processing {file}.",
                details={
                    "video_file": file,
                    "progress": "20%",
                    "stage": "Downloading"
                }
            )

            self.processing_status['file'] = {"stage": "Downloading", "status": f"Downloading {file}..."}
            logger.info(self.processing_status['file']["status"])

            self.processing_status['file'] = {"stage": "Processing", "status": f"Processing footage from {file}..."}
            logger.info(self.processing_status['file']["status"])

            #ASYNCIFY VIDEO PROCESSING IN PROCESSING.PY
            telemetry_objects = self.frame_processor.process_video_pipeline(video_path=file, frame_rate=0.5, mode="timelapse")
            self.processed_videos.add(file)

            self.processing_status[file] = {"stage": "Complete", "status": f"Processing complete for {file}."}
            logger.info(self.processing_status[file]["status"])

        #check if there are processed files in the frames folder. If so, we'll need to send the folder through the Salesforce script/processor to trigger any Work Orders that are needed
        self.status = "Processing Salesforce actions..."
        logger.info(self.status)

        self.status = "Saving images to Box..."
        logger.info(self.status)

        #ASYNCIFY BOX ARCHIVE IN BOX.PY
        telemetry_objects = await self.box.save_frames_to_long_term_storage(telemetry_objects = telemetry_objects)

        work_orders_created = await self.work_order_creator.work_order_engine(box_client=self.box, telemetry_objects=telemetry_objects)
        logger.info(f"Work Orders created: {work_orders_created}")

        self.save_processed_videos()        

        #Now that all the actions are done, we can clear out the frames and unprocessed_videos folder.
        #For unprocessed_videos, make sure to only delete the files that are also in the processed_files list
        self.status = "Cleaning up processed files..."
        logger.info(self.status)
        self.clear_folders()

        self.status = "Idle - Waiting for next check"
    
    async def download_files(self, files_to_download: list = None) -> bool:
        for file in files_to_download:
            file_path = os.path.join(self.box.unprocessed_videos_folder, file['name'])
            if os.path.exists(file_path):
                logger.info(f"File already exists: {file['name']}. Skipping download.")
                
                # Simulate download status for the UI
                await self.send_status_update_to_ui(
                    source='App.download_files()',
                    level='Card',
                    type='Video',
                    status="Already Downloaded",
                    message=f"File {file['name']} already exists. Skipping download.",
                    details={
                        "video_file": file['name'],
                        "progress": "30%",
                        "stage": "Downloading"
                    }
                )
                continue

            logger.info(f"Downloading file: {file['name']}. Please wait...")
            self.box.download_file(file_id=file['id'], file_name=file['name'], folder_path=self.box.unprocessed_videos_folder)
            logger.info(f"Downloaded file: {file['name']}")

            # Send status update to UI after successful download
            await self.send_status_update_to_ui(
                source='App.download_files()',
                level='Card',
                type='Video',
                status="Download Complete",
                message=f"File {file['name']} downloaded successfully.",
                details={
                    "video_file": file['name'],
                    "progress": "30%",
                    "stage": "Downloading"
                }
            )
        return True

    def get_all_files(self):
        # all files from Box (specific callouts to be handled in box.py)
        files = self.box.download_files(self.box.videos_folder_box_id)
        logger.info(f"Downloaded {len(files)} files from Box. {files = }")
        return files
        
    def check_for_new_files(self) -> list:
        """Poll Box for new files and return the names of any that aren't already handled."""
        logger.info("Checking for new files...")
        new_files_to_download = []
        self.load_processed_videos()

        box_folder_id = self.box.videos_folder_box_id
        files_in_box = self.box.list_items_in_folder(box_folder_id)  # List files in Box
        
        # Get filenames of downloaded but unprocessed files
        files_in_unprocessed_folder = set(os.listdir("unprocessed_videos"))

        #get filenames of downloaded and processed files
        files_in_processed_videos_folder = set(os.listdir("processed_videos"))

        # Exclude files already processed OR already downloaded
        new_files = [
            file for file in files_in_box 
            if file['name'] not in self.processed_videos  # Not processed
            #and file['name'] not in files_in_unprocessed_folder  # Not already downloaded # De-comment when pre-downloaded files are removed
            and file['name'] not in files_in_processed_videos_folder # Not already dwnldld and processed
        ]

        if not new_files:
            logger.info("No new files to process.")
            return new_files_to_download

        logger.info(f"New files detected: {[file['name'] for file in new_files]}")

        for file in new_files:
            new_files_to_download.append(file)
            logger.info(f"Adding {file['name']} to to-download: (Id {file['id']})")

        return new_files_to_download

    def clear_folders(self):
        # Move processed videos
        processed_videos_folder = "processed_videos"
        os.makedirs(processed_videos_folder, exist_ok=True)  # Ensure folder exists

        unprocessed_files = os.listdir("unprocessed_videos")
        for file in unprocessed_files:
            if file in self.processed_videos:
                shutil.move(f"unprocessed_videos/{file}", f"{processed_videos_folder}/{file}")
                logger.info(f"Moved {file} to {processed_videos_folder}")

        #clear out the frames folder
        frames = os.listdir("frames")
        for frame in frames:
            os.remove(f"frames/{frame}")

        os.remove(f"temp_metadata.bin")
        os.remove(f"temp_metadata.gpx")
        os.remove(f"temp_metadata.kml")

    async def start_monitoring(self, interval=10):
        """Starts the monitoring loop without using threading.
        This function will block indefinitely.
        """
        print("Start_monitoring has begun!")
        self.monitoring_status = "Idle"
        if self.monitoring_active:
            logger.info("Monitoring is already running.")
            return
        
        self.monitoring_active = True
        self.status = "Active"  # ✅ Set status to Active
        self.monitoring_status = "Active"  
        logger.info("Monitoring started.")
        self.status = "Monitoring"

        # The monitoring loop runs synchronously now.
        try:
            while self.monitoring_active:
                for i in range(interval, 0, -1):
                    if not self.monitoring_active:
                        logger.info("Monitoring loop interrupted.")
                        self.status = "Idle"
                        self.monitoring_status = "Idle"
                        await self.send_status_update_to_ui(
                            source='App.start_monitoring()',
                            level='Info',
                            type='Program',
                            status="Stopped",
                            message="Monitoring has been stopped by the user.",
                        )
                        return
                    
                    

                    self.time_to_check = i
                    self.monitoring_status = "Active"
                    await asyncio.sleep(1)
                    
                    # 📣 Send program status update with countdown
                    await self.send_status_update_to_ui(
                        source='App.start_monitoring()',
                        level='Info',
                        type='Program',
                        status="Active",
                        message=f"Next check in {i} seconds",
                        details={
                            "countdown": i
                        }
                    )
                # 📣 Send temp box check
                await self.send_status_update_to_ui(
                    source='App.start_monitoring()',
                    level='Info',
                    type='Temp',
                    status="Checking Box for new files...",
                    message=f"Checking Box for new files...",
                )

                new_files_to_download = self.check_for_new_files()
                if len(new_files_to_download) > 0:
                    self.status = "Downloading"
                    
                    # 📣 Send video status alert for new processing of videos
                    await self.send_status_update_to_ui(
                        source='App.start_monitoring()',
                        level='Info',
                        type='Program',
                        status="Processing",
                        message=f"Processing {len(new_files_to_download)} files."
                    )
                    await self.pipeline(new_files_to_download)
                else:
                    self.status = "Monitoring"
                    logger.info(self.status)
        except Exception as e:
            self.status = f"Errored"
            self.monitoring_status = "Error"
            logger.error(f"Monitoring loop error: {e}")
            self.monitoring_active = False

if __name__ == "__main__":
    app = App()
    app.start_monitoring(interval=5)