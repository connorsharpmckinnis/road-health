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
    def __init__(self):
        """Initialize App with reference to WebApp."""
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
        self.box = Box()

    def startup_processor(self):
        self.frame_processor = Processor()

    def startup_work_order_creator(self):
        self.work_order_creator = WorkOrderCreator()

    def load_processed_videos(self):
        try:
            with open('processed_files.log', 'r') as f:
                self.processed_videos = set(f.read().splitlines())
        except FileNotFoundError:
            self.processed_videos = set()

    def load_downloaded_but_unprocessed_videos(self):
        self.downloaded_but_unprocessed = os.listdir("unprocessed_videos")

    
    def save_processed_videos(self):
        """Save processed files to a log to prevent reprocessing."""
        with open("processed_files.log", "w") as f:
            f.write("\n".join(sorted(self.processed_videos)))  # Sort for readability

    async def pipeline(self, new_files_to_download: list=None, greenway_mode=False, mode="timelapse"):
        self.greenway_mode = greenway_mode
        #FALSIFY GREENWAY_MODE TO RETURN TO NORMAL FUNCTIONALITY
        self.status = 'Running pipeline...'
        logger.info(f"Starting pipeline. Downloading files...")


        if not self.greenway_mode:
            download_files_result = await self.download_files(new_files_to_download)
            if download_files_result:
                logger.info(f"Downloaded {len(self.all_files)} files.\n Processing...")
        else:
            logger.info(f"Greenway Mode: Using local files without downloading.")

        
                #check if there are files to process in the appropriate unprocessed folder
        if self.greenway_mode:
            files_to_process = os.listdir("unprocessed_greenway_videos")
        else:
            files_to_process = os.listdir("unprocessed_videos")
            files_to_process = [f for f in files_to_process if f != '.DS_Store']

        #establish processing status for each file
        self.processing_status = {file: {"stage": "Queued", "status": "Waiting to Start"} for file in files_to_process}

        if not files_to_process:
            self.status = "Idle - No files to process."
            logger.info("No files to process. Exiting pipeline.")
            return

        
        for file in files_to_process:

            self.processing_status['file'] = {"stage": "Downloading", "status": f"Downloading {file}..."}
            logger.info(self.processing_status['file']["status"])

            self.processing_status['file'] = {"stage": "Processing", "status": f"Processing footage from {file}..."}
            logger.info(self.processing_status['file']["status"])

            telemetry_objects = await self.frame_processor.process_video_pipeline(video_path=file, frame_rate=0.5, mode=mode)
            #'video' VS 'timelapse' MODE SET HERE. TIMELAPSE MODE IGNORES FRAMERATE I THINK
            self.processed_videos.add(file)

            # MOVED THIS OVER TO PROCESSING.PY FOR PER-FILE UPLOAD AND CLEANUP. MIGHT WORK?
            #await self.box.save_frames_to_long_term_storage(telemetry_objects=telemetry_objects, greenway_mode=greenway_mode, video_path=file)

            self.processing_status[file] = {"stage": "Complete", "status": f"Processing complete for {file}."}
            logger.info(self.processing_status[file]["status"])

        #check if there are processed files in the frames folder. If so, we'll need to send the folder through the Salesforce script/processor to trigger any Work Orders that are needed
        self.status = "Processing Salesforce actions..."
        logger.info(self.status)

        self.status = "Saving images to Box..."
        logger.info(self.status)

        # MOVED SAVING TO A PER-FILE OPERATION TO HOPEFULLY MAKE GEOJSON FOR EACH VIDEO PROCESSED
        #telemetry_objects = await self.box.save_frames_to_long_term_storage(telemetry_objects = telemetry_objects, greenway_mode=greenway_mode)

        if not greenway_mode:
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
                
                continue

            logger.info(f"Downloading file: {file['name']}. Please wait...")
            self.box.download_file(file_id=file['id'], file_name=file['name'], folder_path=self.box.unprocessed_videos_folder)
            logger.info(f"Downloaded file: {file['name']}")

        return True

    def get_all_files(self):
        # all files from Box (specific callouts to be handled in box.py)
        files = self.box.download_files(self.box.videos_folder_box_id)
        logger.info(f"Downloaded {len(files)} files from Box. {files = }")
        return files
        
    def check_for_new_files(self) -> list:
        """Poll Box or Local Folder for new files and return ones not already handled."""
        logger.info("Checking for new files...")
        new_files_to_download = []
        self.load_processed_videos()

        if self.greenway_mode:
            # Greenway mode: check local folder
            local_folder = 'unprocessed_greenway_videos'
            files_in_local = os.listdir(local_folder)
            files_in_processed = set(os.listdir("processed_videos"))

            new_files = [
                {'name': file, 'id': None} for file in files_in_local
                if file not in self.processed_videos
                and file not in files_in_processed
                and file != '.DS_Store'
            ]

        else:
            # Normal Box mode
            box_folder_id = self.box.videos_folder_box_id
            files_in_box = self.box.list_items_in_folder(box_folder_id)

            files_in_processed = set(os.listdir("processed_videos"))

            new_files = [
                file for file in files_in_box
                if file['name'] not in self.processed_videos
                and file['name'] not in files_in_processed
                and file['name'] != '.DS_Store'
            ]

        if not new_files:
            logger.info("No new files to process.")
            return new_files_to_download

        logger.info(f"New files detected: {[file['name'] for file in new_files]}")

        for file in new_files:
            new_files_to_download.append(file)
            logger.info(f"Adding {file['name']} to to-download list")

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
                


    async def start_monitoring(self, interval=10, greenway_mode=False, mode="timelapse"):
        """Starts the monitoring loop without using threading.
        This function will block indefinitely.
        """
        print("Start_monitoring has begun!")
        self.monitoring_status = "Idle"
        if self.monitoring_active:
            logger.info("Monitoring is already running.")
            return
        
        self.greenway_mode=greenway_mode
        
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
                        return
                    
                    

                    self.time_to_check = i
                    self.monitoring_status = "Active"
                    await asyncio.sleep(1)
                    

                new_files_to_download = self.check_for_new_files()
                if len(new_files_to_download) > 0:
                    self.status = "Downloading"
                    logger.info(f"New files detected: {new_files_to_download}")
                    
                    await self.pipeline(new_files_to_download, greenway_mode=self.greenway_mode, mode=mode)
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
    app.start_monitoring(interval=5, greenway_mode=False, mode="timelapse")