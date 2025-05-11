#box_watcher.py
import requests
from logging_config import logger
from box_sdk_gen import BoxClient, BoxDeveloperTokenAuth, BoxCCGAuth, CCGConfig, UploadFileAttributes, UploadFileAttributesParentField, CreateCollaborationItem, CreateCollaborationItemTypeField, CreateCollaborationAccessibleBy, CreateCollaborationAccessibleByTypeField, CreateCollaborationRole, AddShareLinkToFileSharedLink, AddShareLinkToFileSharedLinkAccessField, CreateFileMetadataByIdScope, GetMetadataTemplateScope
from boxsdk.config import API
import os
from dotenv import load_dotenv
import json
import base64
import hashlib
import io
import datetime
from utils import unprocessed_videos_path, box_archived_images_folder_id, box_archived_videos_folder_id, box_images_folder_id, box_videos_folder_id, box_work_order_images_folder_id, box_road_health_folder_id
import asyncio
from concurrent.futures import ThreadPoolExecutor
import geojson
import zipfile

# Load environment variables from .env file
load_dotenv()

# Access the Box credentials
BOX_DEV_TOKEN = os.getenv("BOX_DEV_TOKEN")
BOX_CLIENT_ID = os.getenv("BOX_CLIENT_ID")
BOX_CLIENT_SECRET = os.getenv("BOX_CLIENT_SECRET")
BOX_ENTERPRISE_ID = os.getenv("BOX_ENTERPRISE_ID")

class Box():
    def __init__(self, client_id=None, client_secret=None, enterprise_id=None):
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
        self.box_metadata_template_key = "folderWatcherMetadata"

        self.authenticate()
        print(f"{self.client = }")     
        
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
    
    def save_frames_to_long_term_storage(self, destination_folder_id='316117482557', source_normals_folder='frames', source_wos_folder='work_order_frames', telemetry_objects: list=None, greenway_mode=False, video_path: str=None):
        from processing import TelemetryObject

        telemetry_objects = telemetry_objects or []
        source_video_base = os.path.splitext(os.path.basename(video_path))[0]


        #FALSIFY GREENWAY_MODE TO RETURN TO STANDARD CONFIGURATION

        logger.info(f"Moving videos from the active folder to the archive...")
        # Get the videos from Box's Videos folder
        box_videos_folder_contents = self.list_items_in_folder(self.videos_folder_box_id)
        box_video_ids = [item['id'] for item in box_videos_folder_contents]
        # Move the videos to the 'Archived Videos' folder
        self.move_files(box_video_ids, self.box_archived_videos_folder_id)

        logger.info(f"Saving frames to long-term storage...")

        # Generate a timestamp for unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H_%M")

        if greenway_mode:

            # Convert telemetry objects to GeoJSON Features
            geojson_features = [telem_obj.to_geojson() for telem_obj in telemetry_objects]
            feature_collection = geojson.FeatureCollection(geojson_features)
            
            # Define the GeoJSON file path (local save location)
            geojson_filename = f"{source_video_base}_{timestamp}.geojson"
            geojson_filepath = os.path.join('greenway_geojsons', geojson_filename)

            # Debug: Check if filepath is valid
            print(f"Saving GeoJSON file to: {geojson_filepath}")

            # Save FeatureCollection as a GeoJSON file
            try:
                with open(geojson_filepath, "w") as geojson_file:
                    geojson.dump(feature_collection, geojson_file, indent=2)
            except Exception as e:
                logger.error(f"Failed to save GeoJSON file locally: {e}")
                return None

            # Debug: Check if file exists after writing
            if not os.path.exists(geojson_filepath):
                logger.error(f"GeoJSON file does not exist at expected path: {geojson_filepath}")
                return None

            # Upload the GeoJSON file to Box
            try:
                uploaded_geojson = self.upload_small_file_to_folder(geojson_filepath, destination_folder_id, geojson_filename)

                # Debug: Check if upload worked
                if uploaded_geojson and hasattr(uploaded_geojson, 'entries') and uploaded_geojson.entries:
                    geojson_box_file_id = uploaded_geojson.entries[0].id
                    geojson_box_file_url = self.get_direct_shared_link(geojson_box_file_id)
                else:
                    logger.error("GeoJSON upload failed. `uploaded_geojson` did not return expected structure.")
            except Exception as e:
                logger.error(f"Error uploading GeoJSON to Box: {e}")

            logger.info("Long-term storage process completed.")
            updated_telemetry_objects = telemetry_objects
            return updated_telemetry_objects
        
        # Use the new multithreaded upload function to save all frames to Box
        # REPLACED WITH THE GROUPED/ZIPPED PROCESS BELOW
        #updated_telemetry_objects = await self.upload_files_to_box_folder(destination_folder_id, prefix_timestamp=timestamp, telemetry_objects=telemetry_objects)

        # Bundle frames into per-video ZIPs and upload
        grouped = self.group_telem_objects_by_video(telemetry_objects)
        zip_paths = []
        for base, items in grouped.items():
            # extract file paths
            fps = [item['filepath'] for item in items]
            # strip any path components from base before building zip name
            safe_base = os.path.basename(base)
            zip_name = f"{safe_base}_{timestamp}"
            zip_path = self.create_zip_from_group(zip_name, fps)
            zip_paths.append(zip_path)
        # Upload all ZIP archives
        self.upload_zip_to_box(zip_paths, destination_folder_id)
        updated_telemetry_objects = telemetry_objects



        logger.info("Saving all telemetry into a single GeoJSON (timelapse mode)...")

        # Combine all telemetry objects into one FeatureCollection
        geojson_features = [telem_obj.to_geojson() for telem_obj in updated_telemetry_objects]
        feature_collection = geojson.FeatureCollection(geojson_features)

        # Build filename based on source video
        geojson_filename = f"{source_video_base}_{timestamp}_telemetry.geojson"
        geojson_filepath = os.path.join('road_geojsons', geojson_filename)

        # Save the FeatureCollection GeoJSON locally
        try:
            with open(geojson_filepath, "w") as geojson_file:
                geojson.dump(feature_collection, geojson_file, indent=2)
            logger.info(f"Saved combined GeoJSON: {geojson_filepath}")
        except Exception as e:
            logger.error(f"Error saving combined GeoJSON: {e}")

        # Upload the combined GeoJSON to Box
        try:
            uploaded_geojson = self.upload_small_file_to_folder(geojson_filepath, destination_folder_id, geojson_filename)
            if uploaded_geojson and hasattr(uploaded_geojson, 'entries') and uploaded_geojson.entries:
                geojson_box_file_id = uploaded_geojson.entries[0].id
            else:
                logger.error(f"GeoJSON upload failed for {geojson_filename}")
        except Exception as e:
            logger.error(f"Error uploading GeoJSON {geojson_filename}: {e}")

        

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

    '''def upload_files_to_box_folder(self, destination_folder_id, prefix_timestamp=None, max_workers=5, file_paths=None, telemetry_objects: list=None):
        """
        Uploads multiple small files (<50MB each) to a specified Box folder concurrently.

        Args:
            file_paths (list): A list of file paths to upload.
            destination_folder_id (str): The ID of the Box folder to upload files to.
            prefix_timestamp (str, optional): A timestamp prefix for filenames to avoid conflicts.
            max_workers (int, optional): The maximum number of threads to use for concurrent uploads.
        """
        updated_telemetry_objects = []
        logger.info(f"Uploading {len(telemetry_objects)} files to Box folder ID '{destination_folder_id}' using multithreading...")
        
        def upload_file(telem_obj):
            """Uploads a file and updates its Box file ID."""
            try:
                file_path = telem_obj.filepath
                new_file_name = f"{prefix_timestamp}_{os.path.basename(file_path)}" if prefix_timestamp else os.path.basename(file_path)

                # Upload the file to Box
                fake_file_obj = self.upload_small_file_to_folder(file_path, destination_folder_id, new_file_name)
                real_file_obj = fake_file_obj.entries[0]

                # Build metadata dict from telem_obj
                telem_metadata = telem_obj.to_metadata_dict()  # You define this method on your TelemetryObject

                # Attach metadata to file
                self.client.file_metadata.create_file_metadata_by_id(
                    real_file_obj.id,
                    CreateFileMetadataByIdScope.ENTERPRISE,
                    self.box_metadata_template_key,
                    telem_metadata
                )

                if real_file_obj:
                    box_file_id = real_file_obj.id
                    
                    box_file_url = self.get_direct_shared_link(box_file_id)  # Optional: Store Box direct URL
                    print(f'{box_file_id = }')
                    print(f'{box_file_url = }')
                    telem_obj.add_box_file_id(box_file_id)
                    telem_obj.add_box_file_url(box_file_url)
                    

                    updated_telemetry_objects.append(telem_obj)
            except Exception as e:
                logger.error(f"Failed to upload file '{telem_obj.filepath}': {e}")

        tasks = [upload_file(telem_obj) for telem_obj in telemetry_objects]

        # Execute the tasks concurrently
        await asyncio.gather(*tasks)

        logger.info("All files uploaded successfully.")
        return updated_telemetry_objects'''
    
    def group_telem_objects_by_video(self, telemetry_objects: list):
        from collections import defaultdict
        """
        Groups telemetry objects by their video file name.

        Args:
            telemetry_objects (list): A list of telemetry objects to group.

        Returns:
            dict: A dictionary where keys are video file names and values are lists of telemetry objects.
        """
        grouped_objects = defaultdict(list)

        for telem_obj in telemetry_objects:
            source_video = telem_obj.to_dict().get('source_video')
            if source_video:
                grouped_objects[source_video].append(telem_obj.to_dict())
        return dict(grouped_objects)
    
    def create_zip_from_group(self, group_name: str, file_list: list, output_dir: str = 'zipped_files') -> str:
        """
        Creates a zip file from a list of file paths for a specific group.

        Args:
            group_name (str): The name of the group to create a zip file for.
            file_list (list): A list of file paths to include in the zip file.
            output_dir (str): The directory to save the zip file in. Defaults to 'zipped_files'.

        Returns:
            str: The path to the created zip file.
        """
        import os
        import zipfile

        # Normalize file_list if user accidentally passed a dict
        if isinstance(file_list, dict):
            file_list = file_list.get(group_name, [])

        # If list elements are dicts with 'filepath', extract paths
        if file_list and isinstance(file_list[0], dict) and 'filepath' in file_list[0]:
            file_list = [item['filepath'] for item in file_list]


        os.makedirs(output_dir, exist_ok=True)
        zip_file_path = os.path.join(output_dir, f"{group_name}.zip")
        # ensure any nested directories in the zip path are created
        zip_dir = os.path.dirname(zip_file_path)
        if zip_dir:
            os.makedirs(zip_dir, exist_ok=True)

        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_list:
                if os.path.exists(file_path):
                    zipf.write(file_path, arcname=os.path.basename(file_path))
                else:
                    print(f"File {file_path} does not exist. Skipping.")
        
        return zip_file_path
    
    def upload_zip_to_box(self, zip_file_paths, destination_folder_id):
        """
        Uploads a zip file to a specified Box folder.

        Args:
            zip_file_path (str): The path to the zip file to upload.
            destination_folder_id (str): The ID of the Box folder to upload the zip file to.

        Returns:
            str: The ID of the uploaded zip file in Box.
        """

        # Ensure we have a list of paths
        if isinstance(zip_file_paths, str):
            zip_file_paths = [zip_file_paths]
        elif zip_file_paths is None:
            zip_file_paths = []

        uploaded_files = []

        def upload_file(zip_file_path):
            file_size = os.path.getsize(zip_file_path)
            file_name = os.path.basename(zip_file_path)

            try:

                if file_size > 50 * 1024 * 1024:
                    print('Uploading large file...')
                    file_metadata = self.upload_large_file_to_box(zip_file_path, file_name, destination_folder_id)

                else:
                    print('Uploading regular file...')
                    file_metadata = self.upload_small_file_to_folder(zip_file_path, destination_folder_id, file_name)

                uploaded_files.append(file_metadata)
            except Exception as e:
                logger.error(f"Failed to upload zip file '{zip_file_path}': {e}")

        for zip_file_path in zip_file_paths:
            upload_file(zip_file_path)

        return uploaded_files
            



def main():
    # Initialize the Box client
    box_client = Box(BOX_CLIENT_ID, BOX_CLIENT_SECRET, BOX_ENTERPRISE_ID)

    unprocessed_videos_folder = unprocessed_videos_path

    root_items = box_client.list_items_in_folder('0')
    print(f'{len(root_items) = }')

    

    '''
    client.metadata_templates.get_metadata_template(
    GetMetadataTemplateScope.ENTERPRISE, template.template_key
    )
    '''
    '''all_templates = box_client.client.metadata_templates.get_enterprise_metadata_templates()
    print(all_templates)

    test_metadata_key = 'folderWatcherMetadata'
    test_metadata = {
        "filename": "TestFile.mp4", 
        "timestamp": "2025/01/01T4:21:09",
        "lat1": "4", 
        "lon1": "10",
        "pothole": ["Yes"], 
        "potholeConfidence": "1",
        "alligatorCracking": ["No"], 
        "alligatorCrackingConfidence": "0.75",
        "lineCracking": ["Yes"], 
        "lineCrackingConfidence": "0.9",
        "debris": ["Yes"], 
        "summary": "This is a summary of a pothole, found on the top-right portion of the frame in question. Yada yada yada.",
        "roadHealthIndex": "52"
    }
    '''

    
    '''
    test_file_id = '1797090814848'
    #box_client.client.file_metadata.delete_file_metadata_by_id(test_file_id, CreateFileMetadataByIdScope.ENTERPRISE, test_metadata_key)
    metadataFull = box_client.client.file_metadata.create_file_metadata_by_id(test_file_id, CreateFileMetadataByIdScope.ENTERPRISE, test_metadata_key, test_metadata)
    #metadataFull = box_client.client.metadata_templates.get_metadata_template(GetMetadataTemplateScope.ENTERPRISE, test_metadata_key)
    print(f'{metadataFull = }')
    '''

# Run the async main function
if __name__ == '__main__':
    asyncio.run(main())

    #box_client.share_folder_with_user_by_email(videos_folder_id, 'connor.mckinnis@carync.gov', role='editor')

    #box_client.upload_large_file_to_box(file_name='GX010014.mp4', file_path='unprocessed_videos/GX010014.MP4', parent_folder_id=box_client.videos_folder_box_id)