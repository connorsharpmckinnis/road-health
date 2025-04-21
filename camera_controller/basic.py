import asyncio
from open_gopro import WirelessGoPro

async def main() -> None:
    # Put our code here
    async with WirelessGoPro() as gopro:
        print('Success!')

        if gopro.is_ready:
            print('Ready to receive commands!')
        if gopro.is_open:
            print('Open!')

        print('Closing...')
        await gopro.close()
        print('Closed!')
        return

if __name__ == "__main__":
    asyncio.run(main())