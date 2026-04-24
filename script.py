import asyncio
from pathlib import Path
from serial.tools import list_ports
from smartvns.cli.routines import dfu, get_version

# FIRMWARE_PATH = Path("/Users/reda/workspace/work/vnssdk/stim-zephyr.signed.bin")
# FIRMWARE_PATH = Path("/Users/reda/workspace/work/vnssdk/custom fw no pairing/original pairing/stimulator fw 1.0.6/zephyr.signed.bin")
# stim
FIRMWARE_PATH = Path("/Users/reda/workspace/work/west/ws_smartVNS/smartVNS/app/build_stim/app/zephyr/zephyr.signed.bin")
# tracker
# FIRMWARE_PATH = Path("/Users/reda/workspace/work/west/ws_smartVNS/smartVNS/app/build/app/zephyr/zephyr.signed.bin")
# storage erase all tracker
# FIRMWARE_PATH = Path("/Users/reda/workspace/work/vnssdk/storage_erase_all/tracker/zephyr.signed.bin")
# storage erase all stimulator
# FIRMWARE_PATH = Path("/Users/reda/workspace/work/vnssdk/storage_erase_all/stimulator/zephyr.signed.bin")


def detect_ports():
    # Auto-detect SmartVNS ports
    ports = [port.device for port in list_ports.comports()
             if port.description and "SmartVNS" in port.description]
    if not ports:
        print("Error: No SmartVNS devices detected")
        exit(1)

    print(f"Detected ports: {ports}")

    # Get firmware version
    versions = asyncio.run(get_version(ports))
    for port, version in zip(ports, versions):
        print(f"{port}: {version}")

def firmware_update():
    # Auto-detect SmartVNS ports
    ports = [port.device for port in list_ports.comports()
             if port.description and "SmartVNS" in port.description]
    if not ports:
        print("Error: No SmartVNS devices detected")
        exit(1)

    if not FIRMWARE_PATH.exists():
        print(f"Error: File not found: {FIRMWARE_PATH}")
        exit(1)
    
    print(f"Uploading firmware: {FIRMWARE_PATH}")
    image = FIRMWARE_PATH.read_bytes()
    asyncio.run(dfu(ports, image))

if __name__ == "__main__":
    # detect_ports()
    firmware_update()