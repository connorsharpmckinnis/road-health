# box_uploader.py

import os
from dotenv import load_dotenv
from box_sdk_gen import CCGConfig, BoxCCGAuth, BoxClient

load_dotenv()

BOX_CLIENT_ID = os.getenv("BOX_CLIENT_ID")
BOX_CLIENT_SECRET = os.getenv("BOX_CLIENT_SECRET")
BOX_ENTERPRISE_ID = os.getenv("BOX_ENTERPRISE_ID")
BOX_VIDEOS_FOLDER_ID = os.getenv("BOX_VIDEOS_FOLDER_ID")  # You should define this in your .env

def authenticate_box_client():
    ccg_config = CCGConfig(
        client_id=BOX_CLIENT_ID,
        client_secret=BOX_CLIENT_SECRET,
        enterprise_id=BOX_ENTERPRISE_ID
    )
    auth = BoxCCGAuth(config=ccg_config)
    return BoxClient(auth)

def upload_videos_to_box(download_dir="downloads"):
    client = authenticate_box_client()
    folder = client.folders.get_folder_by_id(BOX_VIDEOS_FOLDER_ID)
    for filename in os.listdir(download_dir):
        if filename.lower().endswith(".mp4"):
            file_path = os.path.join(download_dir, filename)
            try:
                print(f"[↑] Uploading {filename}...")
                folder.upload(file_path, file_name=filename)
                print(f"[✓] Uploaded: {filename}")
            except Exception as e:
                print(f"[!] Failed to upload {filename}: {e}")
