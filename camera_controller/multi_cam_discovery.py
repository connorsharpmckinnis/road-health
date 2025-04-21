import sys
import os
import asyncio
import json
from open_gopro import WirelessGoPro

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTPUT_FILE = "discovered_camera_info.json"
SCAN_DURATION = 30  # seconds


async def scrape_camera_info(camera_id):
    info = {}

    try:
        async with WirelessGoPro(target=camera_id, wifi_interface=False, enable_wifi=False) as gopro:
            print(f"[+] Connected to {gopro.identifier}")

            statuses = await gopro.ble_command.get_camera_statuses()
            settings = await gopro.ble_command.get_camera_settings()

            ssid_resp = await gopro.ble_command.get_wifi_ssid()
            password_resp = await gopro.ble_command.get_wifi_password()
            ap_entries_resp = await gopro.ble_command.scan_wifi_networks()

            info = {
                "name": camera_id or "Unnamed",
                "identifier": gopro.identifier,
                "ssid": ssid_resp.data,
                "password": password_resp.data,
                "ap_entries": ap_entries_resp.data,
            }

            print(f"[✓] Scraped info from {info['identifier']}")

    except Exception as e:
        print(f"[!] Error scraping {camera_id}: {e}")
        return None

    return info


async def discover_cameras():
    """Quick scan for cameras during the time window."""
    found_cameras = set()

    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < SCAN_DURATION:
        try:
            async with WirelessGoPro(wifi_interface=False, enable_wifi=False) as gopro:
                if gopro.identifier:
                    name = gopro.identifier.split(":")[0].strip()

                if name not in found_cameras:
                    print(f"[~] Found Camera: {name}")
                    found_cameras.add(name)
        except Exception:
            # Ignore timeouts or failed connects
            pass

        await asyncio.sleep(1)  # Small wait between tries

    return list(found_cameras)


async def main():
    print("[~] Starting camera scan...")
    camera_ids = await discover_cameras()

    if not camera_ids:
        print("[!] No cameras found.")
        return

    print(f"[+] Discovered {len(camera_ids)} camera(s), collecting info...")

    # Launch concurrent scraping tasks
    print(f'{camera_ids = }')
    scrape_tasks = [asyncio.create_task(scrape_camera_info(cam_id)) for cam_id in camera_ids]
    results = await asyncio.gather(*scrape_tasks)

    # Filter out any None results (errors)
    all_infos = [r for r in results if r]

    if all_infos:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_infos, f, indent=2)
        print(f"[✓] Saved {len(all_infos)} camera(s) info to {OUTPUT_FILE}")
    else:
        print("[!] No camera info successfully scraped.")


if __name__ == "__main__":
    asyncio.run(main())