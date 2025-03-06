#box_watcher.py
import requests
from logging_config import logger
from box_sdk_gen import BoxClient, BoxDeveloperTokenAuth, BoxCCGAuth, CCGConfig, UploadFileAttributes, UploadFileAttributesParentField, CreateCollaborationItem, CreateCollaborationItemTypeField, CreateCollaborationAccessibleBy, CreateCollaborationAccessibleByTypeField, CreateCollaborationRole, AddShareLinkToFileSharedLink, AddShareLinkToFileSharedLinkAccessField
from boxsdk.config import API
import os
from dotenv import load_dotenv
import json
import base64
import hashlib
import io
import datetime
from utils import unprocessed_videos_path, box_archived_images_folder_id, box_archived_videos_folder_id, box_images_folder_id, box_videos_folder_id, box_work_order_images_folder_id, box_road_health_folder_id
from web_ui import WebApp, StatusUpdate
import asyncio
from concurrent.futures import ThreadPoolExecutor



# Load environment variables from .env file
load_dotenv()

# Access the Box credentials
BOX_DEV_TOKEN = os.getenv("BOX_DEV_TOKEN")
BOX_CLIENT_ID = os.getenv("BOX_CLIENT_ID")
BOX_CLIENT_SECRET = os.getenv("BOX_CLIENT_SECRET")
BOX_ENTERPRISE_ID = os.getenv("BOX_ENTERPRISE_ID")

class Box():
    def __init__(self, client_id=None, client_secret=None, enterprise_id=None, web_app: WebApp=None):
        self.web_app = web_app
        self.client_id = client_id or BOX_CLIENT_ID
        self.client_secret = client_secret or BOX_CLIENT_SECRET
        self.enterprise_id = enterprise_id or BOX_ENTERPRISE_ID
        self.client = None
        self.auth = None
        self.videos_folder_box_id = box_videos_folder_id
        self.archived_videos = None
        self.unprocessed_videos_folder = unprocessed_videos_path
        self.box_archived_images_folder_id = box_archived_images_folder_id
        self.box_archived_videos_folder_id = box_archived_videos_folder_id
        self.box_images_folder_id = box_images_folder_id
        self.box_work_order_images_folder_id = box_work_order_images_folder_id
        self.box_road_health_folder_id = box_road_health_folder_id

        self.authenticate()
        print(f"{self.client = }")     
        


    async def send_status_update_to_ui(self, type, level, status, message, details={}):
        """Send a status update to the UI using WebSockets."""
        if self.web_app:
            await self.web_app.send_status_update(
                source="Box",
                type=type,
                level=level,
                status=status,
                message=message,
                details=details
            )

    ## SECURITY AND AUTHENTICATION

    def authenticate(self):
        """
        Authenticates the client using the Client Credentials Grant (CCG) flow.
        """
        try:
            # Set up CCG-based authentication
            ccg_config = CCGConfig(
                client_id=self.client_id,
                client_secret=self.client_secret,
                enterprise_id=self.enterprise_id
            )
            self.auth = BoxCCGAuth(config=ccg_config)
            self.client = BoxClient(auth=self.auth)
            logger.info("Authentication successful. BoxClient initialized.")
        except Exception as e:
            logger.exception(f"Authentication failed: {e}")
            raise
        
    def test_connection(self):
        """
        Tests the connection by retrieving items from the root folder.
        """
        try:
            root_folder = self.client.folders.get_folder_by_id('0')
            logger.info(f"Connected to Box as: {self.client}")
            logger.info(f"Root folder name: {root_folder.name}")
            logger.info("Listing items in the root folder:")

            # Retrieve and log items in the root folder
            for item in root_folder.item_collection.entries:
                logger.info(f"- {item.type.capitalize()} | Name: {item.name} | ID: {item.id}")
        except Exception as e:
            logger.error(f"Error testing connection: {e}")

    def create_videos_folder(self, parent_folder_id='0'):
        """
        Checks if a folder named 'Videos' exists under the specified parent folder.
        If not, creates the folder and returns its ID.

        Args:
            parent_folder_id (str): The ID of the parent folder. Default is '0' (root folder).

        Returns:
            str: The ID of the 'Videos' folder.
        """
        folder_name = "Videos"
        try:
            # Check if the folder already exists
            folder_id = self.get_folder_id_by_name(folder_name, parent_folder_id)
            if folder_id:
                logger.info(f"Folder '{folder_name}' already exists with ID: {folder_id}")
                return folder_id
            else:
                logger.info(f"Folder '{folder_name}' does not exist. Creating...")
                folder_id = self.create_folder(folder_name, parent_folder_id)
                if folder_id:
                    return folder_id
                else:
                    logger.error(f"Failed to create folder '{folder_name}'.")
                    return None
        except Exception as e:
            logger.error(f"Error creating 'Videos' folder: {e}")
            return None
        
    def create_folder(self, folder_name, parent_folder_id='0'):
        """
        Creates a folder under the specified parent folder.
        """
        try:
            parent_folder = self.client.folders.get_folder_by_id(folder_id=parent_folder_id)
            new_folder = self.client.folders.create_folder(folder_name, parent_folder)
            logger.info(f"Folder '{folder_name}' created with ID: {new_folder.id}")
            return new_folder.id
        except Exception as e:
            logger.error(f"Error creating folder '{folder_name}': {e}")
            return None

    def get_folder_id_by_name(self, folder_name, parent_folder_id='0'):
        """
        Retrieves the folder ID for a given folder name under the specified parent folder.
        """
        try:
            parent_folder = self.client.folders.get_folder_by_id(folder_id=parent_folder_id)
            items = parent_folder.item_collection.entries
            for item in items:
                if item.name == folder_name and item.type == 'FolderBaseTypeField':
                    logger.info(f"Folder '{folder_name}' found with ID: {item.id}")
                    return item.id
            logger.warning(f"Folder '{folder_name}' not found under parent folder '{parent_folder_id}'.")
            return None
        except Exception as e:
            logger.error(f"Error retrieving folder ID: {e}")
            return None
        
    def list_items_in_folder(self, folder_id):
        """
        Lists all items in the specified folder.
        Args:
            folder_id (str): The ID of the folder to retrieve items from.
        Returns:
            list: A list of item details (name and ID) in the folder.
        """
        try:
            # Retrieve the folder and its items
            folder = self.client.folders.get_folder_by_id(folder_id)
            items = folder.item_collection.entries

            # Log and print the items in the folder
            item_list = []
            for item in items:
                item_list.append({"name": item.name, "id": item.id})
            return item_list
        except Exception as e:
            logger.error(f"Failed to list items in folder '{folder_id}': {e}")
            return []

    def upload_small_file_to_folder(self, file_path, folder_id="0", new_name=None):
        """
        Uploads a <50MB file to the specified folder.
        Args:
            file_path (str): The local path to the file to upload.
            folder_id (str): The ID of the folder to upload to.
        Returns:
            dict: Information about the uploaded file.
        """
        try:
            if not new_name:
                new_file_name = os.path.basename(file_path)
            else:
                new_file_name = new_name
            
            with open(file_path, "rb") as file:
                uploaded_file = self.client.uploads.upload_file(
                    UploadFileAttributes(
                        name=new_file_name, parent=UploadFileAttributesParentField(id=folder_id)
                    ),
                    file,
                )
        
                logger.info(f"File '{new_file_name}' uploaded successfully.")
                return uploaded_file
        except Exception as e:
            logger.error(f"Failed to upload file '{file_path}': {e}")
            return None
    
    def upload_large_file_to_box(self, file_path, file_name, parent_folder_id):
        """Uploads a large file using the Box Gen SDK's `upload_big_file()` method."""
        
        file_size = os.path.getsize(file_path)

        try:
            with open(file_path, 'rb') as file_stream:
                uploaded_file = self.client.chunked_uploads.upload_big_file(
                    file=file_stream,
                    file_name=file_name,
                    file_size=file_size,
                    parent_folder_id=parent_folder_id
                )

            logger.info(f'File "{uploaded_file.name}" uploaded successfully with file ID {uploaded_file.id}')
            return uploaded_file

        except Exception as e:
            logger.error(f"Error uploading file '{file_name}': {e}")
            return None
    
    def get_file_size(self, file_path):
        return os.path.getsize(file_path)
    
    def get_direct_shared_link(self, file_id) -> str: #returns the string URL of the shared link (direct edition) for use in Salesforce displays and elsewhere
        fileFull = self.client.shared_links_files.add_share_link_to_file(file_id,"shared_link",shared_link=AddShareLinkToFileSharedLink(
            access=AddShareLinkToFileSharedLinkAccessField.OPEN,),
        )
        fileDirectSharedLink = fileFull.shared_link.download_url
        print(f'{fileDirectSharedLink = }')
        return fileDirectSharedLink
    
    def download_file(self, file_id, file_name=None, folder_path=None):
        """
        Downloads a file from Box by its file ID and saves it locally.

        Args:
            file_id (str): The ID of the file to download.

        Returns:
            str: The local path to the downloaded file.
        """
        if folder_path is not None:
            path = folder_path
        else:
            path = os.path.join(os.getcwd(), file_name)
        
        if file_name:
            file_name = file_name
        else:
            file_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        path = os.path.join(folder_path, file_name)


        try:
            # Download the file content
            with open(path, 'wb') as file:
                self.client.downloads.download_file_to_output_stream(file_id, file)
                logger.info(f"File '{file_name}' downloaded successfully with ID: {file_id}")

            return file_name
        except Exception as e:
            logger.error(f"Failed to download file '{file_id}': {e}")
            return None

    def download_files(self, folder_id, destination_folder_path=None):
        if destination_folder_path is None:
            destination_folder_path = self.unprocessed_videos_folder
        files = self.list_items_in_folder(folder_id)
        downloaded_files = []

        for file in files:
            downloaded_file = self.download_file(file['id'], file_name=file['name'], folder_path=destination_folder_path)
            downloaded_files.append(downloaded_file)
                    
        return downloaded_files
    
    async def save_frames_to_long_term_storage(self, destination_folder_id='308059844499', source_normals_folder='frames', source_wos_folder='work_order_frames'):
        logger.info(f"Saving frames to long-term storage...")

        # Get all the image files and json in the local 'frames' folder
        frames_folder_contents = os.listdir(source_normals_folder)

        # Get the videos from Box's Videos folder
        box_videos_folder_contents = self.list_items_in_folder(self.videos_folder_box_id)
        box_video_ids = [item['id'] for item in box_videos_folder_contents]

        # Get all the image files in the local 'work_order_frames' folder
        work_order_frames_folder_contents = os.listdir(source_wos_folder)

        # Move the videos to the 'Archived Videos' folder
        self.move_files(box_video_ids, self.box_archived_videos_folder_id)

        # Generate a timestamp for unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H_%M")

        # Prepare file paths
        frames_folder_contents = os.listdir(source_normals_folder)
        file_paths = [os.path.join(source_normals_folder, file) for file in frames_folder_contents]

        # Use the new multithreaded upload function
        uploaded_file_objects = await self.upload_files_to_box_folder(file_paths, destination_folder_id, prefix_timestamp=timestamp)
        
        # Dictionary to track uploaded file IDs
        uploaded_wo_files = {}

        # Upload the work_order_frames files to Box's 'Images / Work Order Images' folder
        wo_file_paths = [os.path.join(source_wos_folder, file) for file in work_order_frames_folder_contents]
        uploaded_wo_file_objects = await self.upload_files_to_box_folder(wo_file_paths, self.box_work_order_images_folder_id, prefix_timestamp=timestamp)
        print(f'{uploaded_wo_file_objects = }')
        if uploaded_wo_file_objects:
            for file_obj in uploaded_wo_file_objects:
                if file_obj.entries and len(file_obj.entries) > 0:
                    file_entry = file_obj.entries[0]  # Extract the first entry
                    original_filename = file_entry.name.split("_", 2)[-1]  # Remove timestamp
                    uploaded_wo_files[original_filename] = file_entry.id  # Store filename -> file_id
                else:
                    logger.warning(f"No valid file entries found in response: {file_obj}")
        print(f'{uploaded_wo_files = }')

        logger.info("Long-term storage process completed.")

        return uploaded_wo_files
        

    def delete_file_by_id(self, file_id):
        """
        Deletes a file from Box by its file ID.

        Args:
            file_id (str): The ID of the file to delete.
        """
        try:
            self.client.files.delete_file_by_id(file_id)
            logger.info(f"File with ID '{file_id}' deleted successfully.")
        except Exception as e:
            logger.error(f"Failed to delete file '{file_id}': {e}")

    def get_user_by_email(self, user_email):
        """
        Retrieves a user by their email address.

        Args:
            user_email (str): The email address of the user to retrieve.

        Returns:
            dict: Information about the user.
        """
        try:
            user = self.client.users.get_users(filter_term=user_email)
            logger.info(f"User '{user_email}' found with ID: {user.id}")
            return user
        except Exception as e:
            logger.error(f"Failed to retrieve user '{user_email}': {e}")
            return None

    def share_folder_with_user_by_email(self, folder_id, user_email, role='viewer'):
        """
        Shares a folder with a user by their email address.

        Args:
            folder_id (str): The ID of the folder to share.
            user_email (str): The email address of the user to share with.
        """
        try:
            collaboration = self.client.user_collaborations.create_collaboration(
                item=CreateCollaborationItem(
                    type=CreateCollaborationItemTypeField.FOLDER,
                    id=folder_id
                ),
                accessible_by=CreateCollaborationAccessibleBy(
                    type=CreateCollaborationAccessibleByTypeField.USER,
                    login=user_email  # Use email directly instead of ID
                ),
                role=CreateCollaborationRole[role.upper()],  # Convert role string to enum
            )

            logger.info(f"Collaboration created: {user_email} → Folder {folder_id} as {role}")
            return collaboration

        except Exception as e:
            logger.error(f"Failed to create collaboration for {user_email}: {e}")
            return None

    def update_file(self, file_id, new_name=None, new_description=None, new_parent_folder_id=None):
        """
        Updates the metadata of a file, including renaming, updating the description,
        or moving it to a new parent folder using the Box Python SDK.

        Args:
            file_id (str): The ID of the file to update.
            new_name (str, optional): The new name for the file.
            new_description (str, optional): The new description for the file.
            new_parent_folder_id (str, optional): The ID of the new parent folder for the file.

        Returns:
            dict: Information about the updated file.
        """
        try:
            # Get the current file and its metadata
            current_file = self.client.files.get_file_by_id(
                file_id, fields=["name", "description", "parent"]
            )

            # Fallback to existing values if new values are not provided
            new_name = new_name or current_file.name
            new_description = new_description or current_file.description
            new_parent_folder_id = new_parent_folder_id or current_file.parent.id

            logger.info(f"Updating file '{file_id}' - "
                        f"Name: '{current_file.name}' -> '{new_name}', "
                        f"Description: '{current_file.description}' -> '{new_description}', "
                        f"Parent ID: '{current_file.parent.id}' -> '{new_parent_folder_id}'")

            # Prepare parameters for the update
            update_params = {}

            if new_name and new_name != current_file.name:
                update_params['name'] = new_name
            if new_description and new_description != current_file.description:
                update_params['description'] = new_description
            if new_parent_folder_id and new_parent_folder_id != current_file.parent.id:
                update_params['parent'] = {'id': new_parent_folder_id}

            if not update_params:
                logger.info(f"No updates needed for file '{file_id}'.")
                return current_file

            # Perform the update using the Box SDK
            updated_file = self.client.files.update_file_by_id(
                file_id=file_id,
                **update_params
            )

            logger.info(f"File '{updated_file.name}' updated successfully with ID: {updated_file.id}")
            return updated_file

        except Exception as e:
            logger.error(f"Failed to update file '{file_id}': {e}")
            return None
        
    def move_file(self, file_id, destination_folder_id):
        self.update_file(file_id=file_id, destination_folder_id=destination_folder_id)

    def move_files(self, file_ids, destination_folder_id):
        """
        Moves multiple files to a new folder.

        Args:
            file_ids (list): A list of file IDs to move.
            destination_folder_id (str): The ID of the destination folder.
        """
        try:
            for file_id in file_ids:
                self.update_file(file_id=file_id, new_parent_folder_id=destination_folder_id)
        except Exception as e:
            logger.error(f"Failed to move files: {e}")

    async def upload_files_to_box_folder(self, file_paths, destination_folder_id, prefix_timestamp=None, max_workers=5):
        """
        Uploads multiple small files (<50MB each) to a specified Box folder concurrently.

        Args:
            file_paths (list): A list of file paths to upload.
            destination_folder_id (str): The ID of the Box folder to upload files to.
            prefix_timestamp (str, optional): A timestamp prefix for filenames to avoid conflicts.
            max_workers (int, optional): The maximum number of threads to use for concurrent uploads.
        """
        logger.info(f"Uploading {len(file_paths)} files to Box folder ID '{destination_folder_id}' using multithreading...")
        uploaded_files = []

        async def upload_file(file_path):
            """Helper function to upload a single file asynchronously."""
            new_file_name = f"{prefix_timestamp}_{os.path.basename(file_path)}" if prefix_timestamp else os.path.basename(file_path)
            file_obj = await asyncio.to_thread(self.upload_small_file_to_folder, file_path, destination_folder_id, new_file_name)
            if file_obj:
                uploaded_files.append(file_obj)

        # Create upload tasks for each file
        tasks = [upload_file(file_path) for file_path in file_paths]

        # Execute the tasks concurrently
        await asyncio.gather(*tasks)
        logger.info("All files uploaded successfully.")
        return uploaded_files

async def main():
    # Initialize the Box client
    box_client = Box(BOX_CLIENT_ID, BOX_CLIENT_SECRET, BOX_ENTERPRISE_ID)

    unprocessed_videos_folder = unprocessed_videos_path

    root_items = box_client.list_items_in_folder('0')
    print(f'{len(root_items) = }')

    road_health_items = box_client.list_items_in_folder(box_client.box_road_health_folder_id)
    print(f'{len(road_health_items) = }')

    test_files = os.listdir('test_frames_folder')
    print(f'{test_files = }')

    # Run the async function properly
    uploaded_files = await box_client.save_frames_to_long_term_storage(source_wos_folder='test_frames_folder')

    print(f"Uploaded files: {uploaded_files}")

# Run the async main function
if __name__ == '__main__':
    asyncio.run(main())
   

    



    #box_client.share_folder_with_user_by_email(videos_folder_id, 'connor.mckinnis@carync.gov', role='editor')

    #box_client.upload_large_file_to_box(file_name='GX010014.mp4', file_path='unprocessed_videos/GX010014.MP4', parent_folder_id=box_client.videos_folder_box_id)

    