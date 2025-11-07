import logging
from datetime import datetime
from typing import Optional, Union
import base64

from smpclient import SMPClient
from smpclient.generics import success, error
from smpclient.requests.shell_management import Execute
from smpclient.requests.zephyr_management import EraseStorage
from smpclient.requests.os_management import DateTimeRead, DateTimeWrite, ResetWrite

from smartvns_cli.config import SysConfig, StimConfig
log = logging.getLogger("smp_routines")


def shell_ok(response: str) -> bool:
    return response.startswith("OK:")


async def routine_set_time(dev: SMPClient) -> bool:
    response = await dev.request(DateTimeRead())
    if success(response):
        log.debug(f"Current datetime on device: {response.datetime}")
    else:
        log.debug(f"Device has no datetime set")

    response = await dev.request(
        DateTimeWrite(datetime=datetime.now().isoformat(timespec='milliseconds')))
    if error(response):
        log.error(f"Failed to set datetime: {response}")

    response = await dev.request(DateTimeRead())
    if success(response):
        log.info(f"New datetime on device: {response.datetime}")

    return success(response)


async def routine_get_oob_key(dev: SMPClient) -> Optional[str]:
    response = await dev.request(Execute(
        argv=["bond", "get"]
    ))

    if success(response):
        output = response.o.strip()
        if shell_ok(output):
            log.info("Key received")
            return str.strip(output[4:])
        else:
            log.error(f"Failed to get key: {output}")
            return None


async def routine_set_oob_key(dev: SMPClient, key: str) -> bool:
    response = await dev.request(Execute(
        argv=["bond", "set", "vns", key]
    ))

    if error(response):
        log.error(f"Failed to set key: {response}")
        return False

    output = response.o.strip()
    if not shell_ok(output):
        log.error(f"Failed to set key: {output}")
        return False

    return True


async def routine_del_oob_key(dev: SMPClient) -> bool:
    response = await dev.request(Execute(
        argv=["bond", "del", "vns"]
    ))

    if error(response):
        log.error(f"Failed to delete key: {response}")
        return False

    output = response.o.strip()
    if not shell_ok(output):
        log.error(f"Failed to delete key: {output}")
        return False

    return True


async def routine_reboot(dev: SMPClient) -> bool:
    response = await dev.request(ResetWrite())
    if error(response):
        log.error(f"Failed to reset device: {response}")
        return False

    log.debug("Device reset command sent")
    return True


async def routine_factory_reset(dev: SMPClient) -> bool:
    response = await dev.request(EraseStorage())
    if error(response):
        log.error(f"Failed to erase storage: {response}")
        return False

    log.debug("Storage erase command sent")

    return await routine_reboot(dev)


async def routine_set_bootmode(dev: SMPClient) -> bool:
    response = await dev.request(Execute(
        argv=["dfu"]
    ))

    if error(response):
        log.error(f"Failed to send DFU command: {response}")
        return False

    log.debug("DFU command sent")

    return True


async def routine_upload_image(dev: SMPClient, image: bytes):
    it = dev.upload(
        image=image,
        slot=0,
    )

    try:
        import tqdm
        pbar = tqdm.tqdm(total=len(image), unit='B', unit_scale=True, desc="Uploading")
        async for offset in it:
            pbar.update(offset - pbar.n)
        pbar.close()
    except Exception:
        async for _ in it:
            pass


async def routine_get_config(dev: SMPClient, cfg_type: str = "sys") -> Optional[Union[SysConfig, StimConfig]]:
    # cfg_type is expected to be 'sys' or 'stim'
    response = await dev.request(Execute(
        argv=["cfg", "get", cfg_type]
    ))

    if error(response):
        log.error(f"Failed to get config: {response}")
        return None

    output = response.o.strip()
    if not shell_ok(output):
        log.error(f"Failed to get config: {output}")
        return None

    data = base64.b64decode(response.o.strip()[4:])
    if cfg_type == "sys":
        cfg = SysConfig()
    else:
        cfg = StimConfig()

    cfg.ParseFromString(data)
    return cfg


async def routine_set_config(dev: SMPClient, cfg_type: str, value: Union[SysConfig, StimConfig]) -> bool:
    """Send a configuration set command to device.

    The VALUE is expected to be a string that the device understands for the
    given cfg_type. This is a thin wrapper around the shell 'cfg set' command.
    """

    # Ensure we send a base64-encoded string payload to the device shell.
    serialized = value.SerializeToString()
    b64 = base64.b64encode(serialized).decode('ascii')
    response = await dev.request(Execute(
        argv=["cfg", "set", cfg_type, b64]
    ))

    if success(response):
        output = response.o.strip()
        if shell_ok(output):
            log.info(f"Config {cfg_type} set successfully")
            return True
        else:
            log.error(f"Failed to set config: {output}")
            return False
    else:
        log.error(f"Failed to send cfg set command: {response}")
        return False


async def routine_get_battery(dev: SMPClient) -> Optional[int]:
    response = await dev.request(Execute(
        argv=["batt"]
    ))

    if error(response):
        log.error(f"Failed to get battery: {response}")
        return None

    output = getattr(response, "o", "").strip()
    if shell_ok(output):
        return int(output[4:])


async def routine_get_version(dev: SMPClient) -> Optional[str]:
    response = await dev.request(Execute(
        argv=["version"]
    ))

    if error(response):
        log.error(f"Failed to get version: {response}")
        return None

    output = getattr(response, "o", "").strip()
    if shell_ok(output):
        return output[4:]
