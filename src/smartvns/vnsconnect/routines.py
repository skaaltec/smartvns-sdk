"""Asynchronous routines for BLE communication with the SmartVNS device.

This module provides small :mod:`async` helper coroutines to read/write
configurations, control stimulation commands and manage notifications.
It is user's responsibility to use these functions with the correct device
client.
"""
from typing import Callable
from bleak import BleakClient

from smartvns.config import SysConfig, StimConfig
from ..config.proto.generated.python.smartvns_pb2 import Stim, Empty

SYS_CHAR = "CE60014D-AE91-11e1-4496-9FC5DD4AFF01"  # UUID aus configure.py
STIM_CHAR = "CE60014E-AE91-11e1-4496-9FC5DD4AFF01"

DATA_UUID = "ce60014d-ae91-11e1-4495-9fc5dd4aff08"
BATTERY_UUID = "2a19"


async def connect_async(client: BleakClient) -> None:
    """Connect the BLE client asynchronously.

    Args:
        client: BleakClient to connect.

    Returns:
        None
    """

    return await client.connect()


async def disconnect_async(client: BleakClient) -> None:
    """Disconnect the BLE client asynchronously if connected.

    Args:
        client: BleakClient to disconnect.

    Notes:
        This function performs no retries.
    """

    await client.disconnect()


async def read_sys_config_async(
        client: BleakClient) -> SysConfig:
    """Read and parse the system configuration message from the device.

    Args:
        client: BleakClient of the connected device.

    Returns:
        SysConfig: Deserialized system configuration message.
    """

    data = await client.read_gatt_char(SYS_CHAR)

    cfg = SysConfig()
    cfg.ParseFromString(data)

    return cfg


async def write_sys_config_async(
        client: BleakClient,
        cfg: SysConfig) -> None:
    """Write the system configuration message to the device.

    Args:
        client: BleakClient of the connected device.
        cfg: The system configuration message to be sent to the device.
    """

    data = cfg.SerializeToString()
    await client.write_gatt_char(SYS_CHAR, data, response=True)


async def read_stim_config_async(
        client: BleakClient) -> StimConfig:
    """Read and parse the stimulation configuration message from the device.

    Args:
        client: BleakClient of the connected device.

    Returns:
        StimConfig: Deserialized stimulation configuration message.
    """

    data = await client.read_gatt_char(STIM_CHAR)

    cfg = StimConfig()
    cfg.ParseFromString(data)
    return cfg


async def write_stim_config_async(
        client: BleakClient,
        cfg: StimConfig) -> None:
    """Write the stimulation configuration message to the device.

    Args:
        client: BleakClient of the connected device.
        cfg: The stimulation configuration message to be sent to the device.
    """

    cmd = Stim(config=cfg)
    data = cmd.SerializeToString()
    await client.write_gatt_char(STIM_CHAR, data, response=True)


async def increase_stim_intensity_async(
        client: BleakClient) -> None:
    """Send a command to increase the stimulation intensity on the device.

    Args:
        client: BleakClient of the connected device.
    """

    cmd = Stim(int_increase=Empty())
    data = cmd.SerializeToString()
    await client.write_gatt_char(STIM_CHAR, data, response=True)


async def decrease_stim_intensity_async(
        client: BleakClient) -> None:
    """Send a command to decrease the stimulation intensity on the device.

    Args:
        client: BleakClient of the connected device.
    """

    cmd = Stim(int_decrease=Empty())
    data = cmd.SerializeToString()
    await client.write_gatt_char(STIM_CHAR, data, response=True)


async def start_notification_async(
        client: BleakClient,
        handler: Callable) -> None:
    """Start notifications on the data characteristic with a handler.

    Args:
        client: BleakClient of the connected device.
        handler: Callable invoked for incoming notifications. Handler should
            accept the parameters provided by Bleak (sender, data).
    """

    await client.start_notify(DATA_UUID, handler)


async def stop_notification_async(
        client: BleakClient) -> None:
    """Stop notifications on the data characteristic.

    Args:
        client: BleakClient of the connected device.
    """

    await client.stop_notify(DATA_UUID)
