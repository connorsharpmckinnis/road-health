import asyncio
from camera_controller.discovery import connect_and_prepare, save_discovered_gopros
from camera_controller.media_handler import list_media, download_media, delete_media
from camera_controller.box_uploader import upload_videos_to_box

CAMERA_NAMES = [
    "GoPro 01", 
    "GoPro 02",
    "GoPro 03",
    "GoPro 04",
    "GoPro 05",
]

async def process_camera(camera_name):
    print(f"\n=== Processing {camera_name} ===")
    gopro = await connect_and_prepare(target_pattern=camera_name)
    if not gopro:
        print(f"[!] Failed to connect to {camera_name}")
        return

    try:
        media_entries = await list_media(gopro)
        if not media_entries:
            print(f"[~] No media found on {camera_name}")
        else:
            await download_media(gopro, media_entries)
            await delete_media(gopro, media_entries)

    except Exception as e:
        print(f"[!] Error processing {camera_name}: {e}")

    finally:
        await gopro.close()

    # Switch to ethernet manually or assume you're already on it here
    upload_videos_to_box()

async def main():
    # await save_discovered_gopros()
    for name in CAMERA_NAMES:
        await process_camera(name)

if __name__ == "__main__":
    asyncio.run(main())
