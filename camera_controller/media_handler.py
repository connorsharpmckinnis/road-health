# media_handler.py

import os
from pathlib import Path
import aiofiles
import aiohttp
from open_gopro import GoPro
import requests

async def list_media(gopro: GoPro):
    try:
        
        response = await gopro.wifi_command.get_media_list()
        if not response.success or not response.result:
            print("[!] No media found.")
            return []
        return response.result.media
    except Exception as e:
        print(f"[ERROR] Failed to list media: {e}")
        return []

async def download_media(gopro: GoPro, media_entries, download_dir="downloads"):
    os.makedirs(download_dir, exist_ok=True)
    base_url = "http://10.5.5.9:8080/videos/DCIM"

    async with aiohttp.ClientSession() as session:
        for entry in media_entries:
            filename = entry.filename
            folder = entry.directory
            url = f"{base_url}/{folder}/{filename}"
            local_path = Path(download_dir) / filename

            if local_path.exists():
                print(f"[~] Skipping already-downloaded file: {filename}")
                continue

            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(local_path, 'wb') as f:
                            await f.write(await resp.read())
                        print(f"[+] Downloaded: {filename}")
                    else:
                        print(f"[!] Failed to download {filename}, status {resp.status}")
            except Exception as e:
                print(f"[ERROR] Exception downloading {filename}: {e}")

async def delete_media(gopro: GoPro, media_entries):
    url = "http://10.5.5.9:8080/gopro/media/delete/file"

    for entry in media_entries:
        path = f"{entry.directory}/{entry.filename}"
        try:
            response = requests.get(url, params={"path": path})
            if response.status_code == 200:
                print(f"[x] Deleted: {path}")
            else:
                print(f"[!] Failed to delete {path}: {response.status_code} {response.text}")
        except Exception as e:
            print(f"[ERROR] Exception deleting {path}: {e}")