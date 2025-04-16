import asyncio
from open_gopro import GoPro

async def connect_and_prepare(target_pattern=None):
    gopro = GoPro(target=target_pattern)

    try:
        await gopro.open(timeout=20, retries=3)

        if not gopro.is_wifi_connected:
            print("[!] Failed to connect to GoPro Wi-Fi AP")
            return None

        print(f"[+] Connected to GoPro: {gopro.identifier}")
        return gopro

    except Exception as e:
        print(f"[ERROR] {e}")
        return None
    
async def connect_all_gopros(timeout_time):
    discovered = []
    start = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start) < timeout_time:
        try: 
            gopro = await connect_and_prepare()
            if gopro:
                discovered.append(gopro)
                print(f"[+] Discovered GoPro: {gopro.identifier}")
        except Exception as e:
            print(f"[!] Error discovering GoPro: {e}")
    return discovered


async def save_discovered_gopros(filepath="discovered_cameras.txt", timeout_time=60):
    discovered_gopros = await connect_all_gopros(timeout_time)
    print(f'{discovered_gopros = }')
    if len(discovered_gopros) >=1:
        return True
    else: 
        return False


if __name__ == "__main__":
    saved_gopros = save_discovered_gopros(filepath="discovered_cameras.txt", timeout_time=60)
    if saved_gopros:
        print("[+] Discovered GoPros saved successfully.")
    else:
        print("[!] No GoPros discovered.")

    result = asyncio.run(connect_and_prepare(target_pattern="GoPro 01"))
    print(f"Connected: {bool(result)}")