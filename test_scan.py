
# Example 1: scan and print SmartVNS devices

from smartvns import vnsconnect
import asyncio


async def scanner():
    scanner = vnsconnect.Scanner()
    scanner.start()
    await asyncio.sleep(5)  # Scan for 5 seconds
    scanner.stop()
    print("Scan complete. Found devices:")
    print(scanner.devices)
    if not scanner.devices:
        print("No VNS devices found. Exiting.")
        return
    else:
        for addr, (dev, adv) in scanner.devices.items():
            print(
                f"- {adv.local_name or dev.name} ({addr}) with RSSI {adv.rssi} dB")

    scanner.terminate()

if __name__ == "__main__":
    asyncio.run(scanner())