import asyncio
import logging
import time
from typing import List, Optional, Union

from smpclient import SMPClient
from smpclient.transport.serial import SMPSerialTransport

from smartvns_cli.config import SysConfig, Stim
from . import routines

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("smp_usb_controller")


async def pair(p1: str, p2: str):

    async with SMPClient(transport=SMPSerialTransport(), address=p1) as dev1, \
        SMPClient(transport=SMPSerialTransport(), address=p2) as dev2:

        keys = await asyncio.gather(
            routines.routine_get_oob_key(dev1),
            routines.routine_get_oob_key(dev2)
        )

        if keys[0] is None or keys[1] is None:
            log.error("Failed to get keys")
            return

        await asyncio.gather(
            routines.routine_set_oob_key(dev1, keys[1]),
            routines.routine_set_oob_key(dev2, keys[0])
        )


async def unpair(p1: str, p2: str):

    async with SMPClient(transport=SMPSerialTransport(), address=p1) as dev1, \
        SMPClient(transport=SMPSerialTransport(), address=p2) as dev2:

        await asyncio.gather(
            routines.routine_del_oob_key(dev1),
            routines.routine_del_oob_key(dev2)
        )


async def set_time(ports: List[str]):

    devs = [SMPClient(transport=SMPSerialTransport(), address=port) for port in ports]
    for dev in devs:
        await dev.connect()

    await asyncio.gather(*(routines.routine_set_time(dev) for dev in devs))


async def reboot(ports: List[str]):

    log.info(f"Operating on {len(ports)} devices: {ports}")

    devs = [SMPClient(transport=SMPSerialTransport(), address=port) for port in ports]
    for dev in devs:
        await dev.connect()

    await asyncio.gather(*(routines.routine_reboot(dev) for dev in devs))


async def factory_reset(ports: List[str]):
    log.info(f"Operating on {len(ports)} devices: {ports}")

    devs = [SMPClient(transport=SMPSerialTransport(), address=port) for port in ports]
    for dev in devs:
        await dev.connect()

    await asyncio.gather(*(routines.routine_factory_reset(dev) for dev in devs))


async def dfu(ports: List[str], image: bytes):
    log.info(f"Operating on {len(ports)} devices (boot->dfu): {ports}")

    devs = [SMPClient(transport=SMPSerialTransport(), address=port) for port in ports]

    await asyncio.gather(*[dev.connect() for dev in devs])
    await asyncio.gather(*(routines.routine_set_bootmode(dev) for dev in devs))
    await asyncio.gather(*(routines.routine_reboot(dev) for dev in devs))

    time.sleep(5)

    # Reconnect to bootloader and upload
    devs = [SMPClient(transport=SMPSerialTransport(), address=port) for port in ports]

    await asyncio.gather(*[dev.connect() for dev in devs])
    await asyncio.gather(*(routines.routine_upload_image(dev, image) for dev in devs))
    await asyncio.gather(*(routines.routine_reboot(dev) for dev in devs))


async def get_battery(ports: List[str]) -> List[Optional[int]]:
    log.info(f"Operating on {len(ports)} devices: {ports}")

    devs = [SMPClient(transport=SMPSerialTransport(), address=port) for port in ports]

    await asyncio.gather(*[dev.connect() for dev in devs])

    return await asyncio.gather(*(routines.routine_get_battery(dev) for dev in devs))


async def get_version(ports: List[str]) -> List[Optional[str]]:
    log.info(f"Operating on {len(ports)} devices: {ports}")

    devs = [SMPClient(transport=SMPSerialTransport(), address=port) for port in ports]

    await asyncio.gather(*[dev.connect() for dev in devs])

    return await asyncio.gather(*(routines.routine_get_version(dev) for dev in devs))


async def get_config(port: str, cfg_type: str = "sys") -> Optional[Union[SysConfig, Stim.Config]]:
    log.info(f"Operating on {port} (cfg_type={cfg_type})")

    async with SMPClient(transport=SMPSerialTransport(), address=port) as dev:
        return await routines.routine_get_config(dev, cfg_type)


async def set_config(port: str, cfg_type: str, cfg: Union[SysConfig, Stim.Config]):
    """Set configuration value on given ports.

    cfg_type: 'sys' or 'stim'
    cfg: configuration object to send to the device routine
    """
    log.info(f"Setting config {cfg_type} on {port}")

    async with SMPClient(transport=SMPSerialTransport(), address=port) as dev:
        await routines.routine_set_config(dev, cfg_type, cfg)
