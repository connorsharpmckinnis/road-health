#ai.py
import json
import dotenv
import os
from openai import OpenAI
import openai
from rich.console import Console
from rich.table import Table
from utils import assistant, batch_assistant, get_assistant, get_batch_assistant, set_batch_assistant, get_greenway_assistant, set_greenway_assistant, model, instructions, batch_response_format, response_format, greenway_instructions, greenway_response_format, greenway_user_message
from logging_config import logger
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
dotenv.load_dotenv()
import time
from datetime import datetime, timedelta, timezone
from openai.types import FileObject, FileDeleted
from web_ui import WebApp, StatusUpdate
import asyncio

AI_LOG_FILE = "logs/ai.log"
TOKEN_USAGE_LOG_FILE = "logs/token_usage.log"

# Create a new handler for AI logs
ai_file_handler = logging.FileHandler(AI_LOG_FILE)
ai_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
ai_file_handler.setLevel(15)  # AI custom level

# Create a filter to **only allow AI logs** in this handler
class AIFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == 15  # Only log AI messages

ai_file_handler.addFilter(AIFilter())  # Apply filter

# Attach handler to logger
logger.addHandler(ai_file_handler)


class AI():
    def __init__(self, api_key, web_app: WebApp=None):
        self.web_app = web_app
        self.api_key = api_key
        openai.api_key = self.api_key
        self.client = OpenAI()
        self.assistant = assistant
        self.batch_assistant = None
        self.assistant_id = get_assistant()
        self.batch_assistant_id = get_batch_assistant()
        self.model = model
        self.instructions = instructions
        self.batch_instructions = instructions
        self.current_assistant_id = None
        
        self.response_format = response_format
        self.batch_response_format = batch_response_format

        self.greenway_assistant = None
        self.greenway_assistant_id = get_greenway_assistant()
        self.greenway_instructions = greenway_instructions
        self.greenway_response_format = greenway_response_format
        self.greenway_user_message = greenway_user_message

        if self.greenway_assistant_id is None:
            greenway_assistant, greenway_assistant_id = self.create_assistant('greenway')
            self.greenway_assistant = greenway_assistant
            set_greenway_assistant(greenway_assistant_id)


    async def send_status_update_to_ui(self, type, level, status, message, details={}):
        """Send a status update to the UI using WebSockets."""
        if self.web_app:
            await self.web_app.send_status_update(
                source="AI",
                type=type,
                level=level,
                status=status,
                message=message,
                details=details
            )

    def create_assistant(self, type=None) -> tuple: #Tuple (self.assistant, self.assistant_id)
        """
        Create an Assistant dedicated to road health evaluations.
        """
        if type == 'batch':
            print("Creating batch-based assistant for road health evaluation...")
            self.batch_assistant = self.client.beta.assistants.create(
                name="Road Health Evaluator",
                description=("You evaluate road conditions based on image inputs. Your task is to analyze images of roads, "
                    "identify issues like potholes or alligator cracking, and provide actionable recommendations."
                ),
                model=self.model,
                instructions=self.instructions,
                response_format=self.batch_response_format
            )
            self.batch_assistant_id = self.batch_assistant.id
            print(f"Assistant created with ID: {self.batch_assistant_id}")

            return self.batch_assistant, self.batch_assistant_id
        
        if type == 'greenway':
            print("Creating greenway-based assistant for road health evaluation...")
            self.greenway_assistant = self.client.beta.assistants.create(
                name="Greenway Health Evaluator",
                description=("You evaluate pavement conditions based on image inputs. Your task is to analyze images of greenways, "
                    "identify issues like cracking or debris, and provide professional and consistent condition ratings."
                ),
                model=self.model,
                instructions=self.greenway_instructions,
                response_format=self.greenway_response_format
            )
            self.greenway_assistant_id = self.greenway_assistant.id
            print(f"Greenway-specific Assistant created with ID: {self.greenway_assistant_id}")

            return self.greenway_assistant, self.greenway_assistant_id

    def upload_image(self, filepath: str):
        """
        Upload a single image to OpenAI and return its file ID.

        Args:
            filepath (str): Path to the image file.

        Returns:
            str: OpenAI file ID.
        """
        # Upload file to OpenAI
        file = self.client.files.create(
            file=open(filepath, "rb"),
            purpose="vision"
            )
        
        logger.ai(f"Uploaded file with OpenAI File Id {file.id}\nobject: {file.object}\nbytes: {file.bytes}\ncreated_at: {file.created_at}\nfilename: {file.filename}\npurpose: {file.purpose}")
        return file

    def get_n_analyses_from_openai(self, telemetry_objects: list):
        """
        Analyze a batch of telemetry objects using OpenAI and return the populated objects.

        Args:
            telemetry_objects (list): List of telemetry objects.

        Returns:
            list: Telemetry objects with analysis results populated.
        """
        def _create_thread(telemetry_objects: list) -> str:
            """
            Create a thread with the prompt message referencing telemetry objects.

            Args:
                telemetry_objects (list): List of telemetry objects.

            Returns:
                str: Thread ID if successful, None otherwise.
            """
            # Extract filenames in order
            filenames = [obj.filename for obj in telemetry_objects]

            # Construct the user message content
            filenames_message = ', '.join([f'"{filename}"' for filename in filenames])
            intro_message = (
                f"In order of appearance, you will review {filenames_message}. "
                f"Refer to the files with these file_ids when responding."
            )

            user_message_content = [
                {"type": "text", "text": intro_message}
            ]

            # Add file references to the message
            for obj in telemetry_objects:
                user_message_content.append({
                    "type": "image_file",
                    "image_file": {"file_id": obj.openai_file_id}
                })

            user_message = {
                "role": "user",
                "content": user_message_content
            }

            try:
                thread = self.client.beta.threads.create(messages=[user_message])
                return thread.id
            except Exception as e:
                logger.ai(f"Failed to create thread: {e}")
                return None

        def _create_and_poll_run(thread_id: str):
            """
            Create and poll a run on the specified thread.

            Args:
                thread_id (str): ID of the thread to run.

            Returns:
                Run object if successful, None otherwise.
            """
            try:
                run = self.client.beta.threads.runs.create_and_poll(
                    thread_id=thread_id,
                    assistant_id=self.current_assistant_id
                )
                # Extract token usage if available
                total_tokens = run.usage.total_tokens if run.usage else 0
                
                # Log thread ID and token usage
                with open(TOKEN_USAGE_LOG_FILE, "a") as f:
                    f.write(f"{datetime.now(timezone.utc)} - Thread ID: {thread_id}, Tokens Used: {total_tokens}\n")

                logger.ai(f"Run completed for thread {thread_id} with {total_tokens} tokens used.")
                
                return run
            except Exception as e:
                logger.ai(f"Failed to create and poll run: {e}")
                return None

        def _process_analysis_results(thread_id: str, telemetry_objects: list):
            """
            Retrieve and match analysis results to telemetry objects.

            Args:
                thread_id (str): ID of the thread containing results.
                telemetry_objects (list): List of telemetry objects to populate with results.

            Returns:
                None
            """
            try:
                # Fetch all messages from the thread
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)

                # Find the assistant message containing the analysis results
                for message in messages.data:
                    if message.role == 'assistant':
                        # Extract JSON string from the content
                        for content_block in message.content:
                            if content_block.type == 'text':
                                analysis_data = json.loads(content_block.text.value)  # Parse the JSON

                                # Iterate over each analysis in the 'analyses' list
                                for analysis in analysis_data.get("analyses", []):
                                    file_id = analysis.get("file_id")
                                    # Match and populate telemetry objects based on file_id
                                    for obj in telemetry_objects:
                                        if obj.filepath == file_id or obj.filename == file_id:
                                            obj.analysis_results = analysis

                logger.ai(f"Successfully processed analysis results for thread {thread_id}.")
                return telemetry_objects
            except Exception as e:
                logger.ai(f"Failed to retrieve or process messages: {e}")
                return []

        # Step 1: Create a thread with the prompt message
        thread_id = _create_thread(telemetry_objects)
        if not thread_id:
            return telemetry_objects  # Return as is, without analysis

        # Step 2: Run the analysis and poll until completion
        run = _create_and_poll_run(thread_id)
        if not run or run.status != 'completed':
            logger.ai(f"Run did not complete successfully. Status: {run.status if run else 'unknown'}")
            return telemetry_objects  # Return as is, without analysis

        # Step 3: Retrieve and process the analysis results
        telemetry_objects = _process_analysis_results(thread_id, telemetry_objects)


        return telemetry_objects

    def upload_files_to_openai(self, telemetry_objects: list, multithreaded: bool):
        """
        Upload files to OpenAI and return a mapping of filenames to file IDs.

        Args:
            telemetry_objects (list): List of telemetry objects.
            multithreaded (bool): Whether to use multithreading.

        Returns:
            dict: Mapping of filenames to OpenAI file IDs.
        """
        def _upload_file_to_openai(telemetry_object):
            try:
                file = self.upload_image(telemetry_object.filepath)
                telemetry_object.openai_file_id = file.id
                return telemetry_object.filepath, file.id
            except Exception as e:
                logger.ai(f"Failed to upload {telemetry_object.filepath}: {e}")
                return telemetry_object.filepath, None

        if multithreaded:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=20) as executor:
                executor.map(_upload_file_to_openai, telemetry_objects)
        else:
            for telemetry_object in telemetry_objects:
                _upload_file_to_openai(telemetry_object)
    
    def run_all_analyses(self, telemetry_objects: list, batch_size: int, multithreaded: bool, assistant: str='batch'):
        """
        Run analyses on telemetry objects in batches.

        Args:
            telemetry_objects (list): List of telemetry objects with OpenAI file IDs.
            batch_size (int): Number of objects per batch.
            multithreaded (bool): Whether to use multithreading.

        Returns:
            list: List of telemetry objects with analysis results.
        """
        def _process_batch(batch):
            result = self.get_n_analyses_from_openai(batch)
            return result if result is not None else []

        # Create batches
        batches = [telemetry_objects[i:i + batch_size] for i in range(0, len(telemetry_objects), batch_size)]
        
        if assistant == 'batch':
            if not self.batch_assistant_id:
                self.create_assistant(type='batch')
            self.current_assistant_id = self.batch_assistant_id
        elif assistant == 'greenway': 
            if not self.greenway_assistant_id:
                self.create_assistant(type='greenway')
            self.current_assistant_id = self.greenway_assistant_id
        
        if multithreaded:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=20) as executor:
                results = executor.map(_process_batch, batches)
        else:
            results = map(_process_batch, batches)

        # Flatten results
        return [obj for batch_result in results for obj in batch_result]

    def analyze_images_with_ai(self, telemetry_objects: list, batch_size: int, multithreaded: bool=True):
        """
        Main function to analyze images using OpenAI.

        Args:
            telemetry_objects (list): List of telemetry objects.
            batch_size (int): Number of objects per analysis batch.
            multithreaded (bool): Whether to use multithreading.

        Returns:
            list: List of fully populated telemetry objects.
        """
        # Stage 1: Upload files to OpenAI
        start_time_6a = time.time()
        self.upload_files_to_openai(telemetry_objects, multithreaded)

        # Stage 2: Run all analyses
        start_time_6b = time.time()
        analyzed_telemetry_objects = self.run_all_analyses(telemetry_objects, batch_size, multithreaded, assistant='greenway')
        #ASSISTANT TYPE IS SELECTED HERE. CURRENTLY SET TO GREENWAY FOR GREENWAY DATA VALIDATION. CHANGE TO 'batch' FOR RETURN TO ROAD HEALTH EVALUATOR

        return analyzed_telemetry_objects, start_time_6a, start_time_6b
    
    def list_uploaded_files(self) -> list:
        """
        Retrieve a list of uploaded files from OpenAI.

        Returns:
            list: A list of FileObject instances.
        """
        try:
            files = self.client.files.list()
            return files.data  # List of FileObject
        except Exception as e:
            logger.ai(f"Failed to retrieve files: {e}")
            return []

    def filter_files_by_date(self, files: list, cutoff_date: datetime, older_than=True) -> list:
        """
        Filters files based on creation date.

        Args:
            files (list): List of FileObject instances.
            cutoff_date (datetime): The reference date to compare against.
            older_than (bool): If True, return files older than cutoff_date; otherwise, return newer ones.

        Returns:
            list: Filtered list of FileObject instances.
        """
        filtered_files = []
        for file in files:
            file_created_at = datetime.fromtimestamp(file.created_at, tz=timezone.utc)
            if (older_than and file_created_at < cutoff_date) or (not older_than and file_created_at >= cutoff_date):
                filtered_files.append(file)
        
        return filtered_files

    def delete_files(self, file_ids: list):
        """
        Deletes files from OpenAI using multithreading.

        Args:
            file_ids (list): List of file IDs to delete.

        Returns:
            dict: Dictionary mapping file IDs to deletion success status.
        """
        def _delete_file(file_id):
            try:
                result = self.client.files.delete(file_id)
                if isinstance(result, FileDeleted):
                    logger.ai(f"Deleted file {file_id}")
                    return file_id, True
                else:
                    logger.ai(f"Failed to delete file {file_id}")
                    return file_id, False
            except Exception as e:
                logger.ai(f"Error deleting file {file_id}: {e}")
                return file_id, False

        deletion_results = {}
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(_delete_file, file_ids)
            for file_id, success in results:
                deletion_results[file_id] = success

        return deletion_results
    
    def clear_old_files(self, days_ago_threshold: int=7):
        days_ago = datetime.now(timezone.utc) - timedelta(days=days_ago_threshold)
        uploaded_files = self.list_uploaded_files()
        old_files = self.filter_files_by_date(uploaded_files, days_ago, older_than=True)
        file_ids_to_delete = [file.id for file in old_files]
        logger.ai(f"Found {len(file_ids_to_delete)} files older than {days_ago_threshold} days.")
        if file_ids_to_delete:
            delete_results = self.delete_files(file_ids_to_delete)
            logger.ai(f"Deleted files: {len(delete_results.items())}")
        else:
            logger.ai("No old files to delete.")
    

if __name__ == '__main__':
    ai = AI(os.getenv("OPENAI_API_KEY"))
    ai.clear_old_files(0)