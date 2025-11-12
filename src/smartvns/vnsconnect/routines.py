"""
Asynchronous routines for BLE communication with the SmartVNS device.

"""
# Bleak
from typing import Callable
from bleak import BleakClient

# Protobuffer
from smartvns.config import SysConfig, StimConfig
# private protosbuffers for stim ctrl
from ..config.proto.generated.python.smartvns_pb2 import Stim, Empty

import logging

log = logging.getLogger(__name__)


SYS_CHAR = "CE60014D-AE91-11e1-4496-9FC5DD4AFF01"  # UUID aus configure.py
STIM_CHAR = "CE60014E-AE91-11e1-4496-9FC5DD4AFF01"

DATA_UUID = "ce60014d-ae91-11e1-4495-9fc5dd4aff08"
BATTERY_UUID = "2a19"


# ASYNCHRONOUS FUNCTIONS

async def connect_async(
        client: BleakClient) -> None:
    """
    Connect the BLE client asynchronously if not already connected.
    Parameters
    ----------
    client :
        Client to connect.

    """
    return await client.connect()


async def disconnect_async(client: BleakClient) -> None:
    """
    Disconnect the BLE client asynchronously if currently connected.
    Parameters
    ----------
    client :
        ....

    Notes
    -----
    This method performs no retries. It is typically called internally
    by :meth:`stop` or :meth:`disconnect`.
    """
    await client.disconnect()


async def read_sys_config_async(
        client: BleakClient) -> SysConfig:
    """
    Asynchronously read and parse the system configuration message from the device.
    Parameters
    ----------
    client : BleakClient
        BleakClient of the connected device.

    Returns
    -------
    SysConfig
        The deserialized system configuration message received from the device. 
    Raises
    ------
    RuntimeError
        If message parsing fails or the characteristic cannot be read.      

    """

    data = await client.read_gatt_char(SYS_CHAR)

    cfg = SysConfig()
    cfg.ParseFromString(data)

    return cfg


async def write_sys_config_async(
        client: BleakClient,
        cfg: SysConfig) -> None:
    """
    Asynchronously write the system configuration message to the device.
    Parameters
    ----------
    client : BleakClient
        BleakClient of the connected device.
    cfg : SysConfig
        The system configuration message to be sent to the device.

    Raises
    ------
    RuntimeError
        If the characteristic cannot be written.
    """
    data = cfg.SerializeToString()
    await client.write_gatt_char(SYS_CHAR, data, response=True)


async def read_stim_config_async(
        client: BleakClient) -> StimConfig:
    """
    Asynchronously read and parse the stimulation configuration message from the device.

    Parameters
    ----------
    client : BleakClient
        BleakClient of the connected device.

    Returns
    -------
    StimConfig
        The deserialized stimulation configuration message received from the device.

    Raises
    ------
    RuntimeError
        If message parsing fails or the characteristic cannot be read.

    Notes
    -----
    This method assumes that the device characteristic contains only the
    serialized protobuf payload (no custom length prefix).
    """

    data = await client.read_gatt_char(STIM_CHAR)

    cfg = StimConfig()
    cfg.ParseFromString(data)
    return cfg


async def write_stim_config_async(
        client: BleakClient,
        cfg: StimConfig) -> None:
    """
    Asynchronously write the stimulation configuration message to the device.

    Parameters
    ----------
    client : BleakClient
        BleakClient of the connected device.
    cfg : StimConfig
        The stimulation configuration message to be sent to the device.


    Raises
    ------
    RuntimeError
        If the characteristic cannot be written.

    """
    cmd = Stim(config=cfg)
    data = cmd.SerializeToString()
    await client.write_gatt_char(STIM_CHAR, data, response=True)


async def increase_stim_intensity_async(
        client: BleakClient) -> None:
    """
    Asynchronously send a command to increase the stimulation intensity on the device.  

    Parameters
    ----------
    client : BleakClient
        BleakClient of the connected device.

    Raises
    ------
    RuntimeError
        If the characteristic cannot be written.

    """
    cmd = Stim(int_increase=Empty())
    data = cmd.SerializeToString()
    await client.write_gatt_char(STIM_CHAR, data, response=True)


async def decrease_stim_intensity_async(
        client: BleakClient) -> None:
    """
    Asynchronously send a command to decrease the stimulation intensity on the device.

    Parameters
    ----------
    client : BleakClient
        BleakClient of the connected device.

    Raises
    ------
    RuntimeError
        If the characteristic cannot be written.

    """
    cmd = Stim(int_decrease=Empty())
    data = cmd.SerializeToString()
    await client.write_gatt_char(STIM_CHAR, data, response=True)


async def start_notification_async(
        client: BleakClient,
        handler: Callable) -> None:
    """
    Start notifications on the data characteristic with a specified handler.

    Parameters
    ----------
    client : BleakClient
        BleakClient of the connected device.
    handler : Callable
        Handler function to process incoming notifications.

    Raises
    ------
    RuntimeError
        If notifications cannot be started.
    """
    await client.start_notify(DATA_UUID, handler)


async def stop_notification_async(
        client: BleakClient) -> None:
    """
    Stop notifications on the data characteristic.

    Parameters
    ----------
    client : BleakClient
        BleakClient of the connected device.

    Raises
    ------
    RuntimeError
        If notifications cannot be stopped.
    """
    await client.stop_notify(DATA_UUID)
