# discovery.py

import asyncio
from open_gopro import WirelessGoPro

async def discover_gopros(timeout=60, name_pattern=None):
    discovered_gopros = []
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            gopro = WirelessGoPro(target=name_pattern, wifi_interface=False)
            await gopro._open_ble(timeout=10, retries=1)

            if gopro.is_open:
                print(f"[+] Connected to GoPro: {gopro.identifier}")
                discovered_gopros.append(gopro)
            else:
                await gopro.close()

        except Exception as e:
            print(f"[!] Error discovering GoPro: {e}")
            if "no suitable interface" in str(e).lower():
                print("[X] Critical: No Wifi interface available. Stopping discovery.")
                break  # <-- 💥 STOP the loop immediately

        await asyncio.sleep(1)  # Small sleep to prevent hammering

    return discovered_gopros

async def save_discovered_gopros(filepath="discovered_cameras.txt", timeout=60):
    gopros = await discover_gopros(timeout)
    if not gopros:
        print("[!] No GoPros discovered.")
        return False

    with open(filepath, "w") as f:
        for gopro in gopros:
            info = f"ID: {gopro.identifier}, SSID: {gopro.ssid}, Password: {gopro.password}\n"
            f.write(info)
    
    print(f"[+] Saved {len(gopros)} GoPros to {filepath}")

    # Make sure to close all the cameras cleanly
    for gopro in gopros:
        await gopro.close()

    return True

async def main():
    await save_discovered_gopros()

if __name__ == "__main__":
    asyncio.run(main())