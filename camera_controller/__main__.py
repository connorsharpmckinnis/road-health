# __main__.py

import sys
import os
import asyncio
import json
from open_gopro import WirelessGoPro

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Optional: Predefined names if you want to target specific cameras
CAMERA_NAMES = [
    "cary3 gopro",
    "GP50339799"
]

OUTPUT_FILE = "discovered_camera_info.json"


async def scrape_camera_info(name=None):
    info = {}

    try:
        if name:
            async with WirelessGoPro(target=name, wifi_interface=False, enable_wifi=False) as gopro:
                print(f'Connected to {gopro.identifier}')
                statuses = await gopro.ble_command.get_camera_statuses()
                settings = await gopro.ble_command.get_camera_settings()
                print(f"Statuses: {statuses}")
                print(f"Settings: {settings}")
        else:
            async with WirelessGoPro(wifi_interface=False, enable_wifi=False) as gopro:
                print(f'Connected to {gopro.identifier}')
                statuses = await gopro.ble_command.get_camera_statuses()
                settings = await gopro.ble_command.get_camera_settings()
                print(f"Statuses: {statuses}")
                print(f"Settings: {settings}")
                ssid = await gopro.ble_command.get_wifi_ssid()
                ssid = ssid.data
                wifi_password = await gopro.ble_command.get_wifi_password()
                wifi_password = wifi_password.data
                ap_entries = await gopro.ble_command.scan_wifi_networks()
                ap_entries = ap_entries.data
                id = gopro.identifier


        info = {
            "name": name if name else "Unnamed",
            "identifier": id,
            "ssid": ssid,
            "password": wifi_password,
            "ap_entries": ap_entries
        }

        print(f"[+] Scraped info from {info['name']} ({info['identifier']})")

    except Exception as e:
        print(f"[!] Error scraping {name or 'Unnamed'}: {e}")
        return None

    finally:
        await gopro.close()

    return info


async def main(named_mode=True):
    all_infos = []

    if named_mode:
        for name in CAMERA_NAMES:
            camera_info = await scrape_camera_info(name)
            if camera_info:
                all_infos.append(camera_info)
    else:
        # Attempt to discover cameras nearby without specifying names
        print("[~] Scanning for nearby cameras...")
        camera_info = await scrape_camera_info(name=None)
        if camera_info:
            all_infos.append(camera_info)
        await asyncio.sleep(2)

    if all_infos:
        print(f'{all_infos = }')
        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_infos, f, indent=2)

        print(f"[✓] Saved {len(all_infos)} camera(s) info to {OUTPUT_FILE}")
    else:
        print("[!] No cameras discovered.")


if __name__ == "__main__":
    # Set named_mode to True if you want to target specific cameras
    asyncio.run(main(named_mode=False))