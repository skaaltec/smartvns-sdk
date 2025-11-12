"""
vnsconnect_c.py
===============

SmartVNS Python SDK (Tracker / Stimulator)
------------------------------------------

This SDK provides a modular Python API for SmartVNS BLE devices (*Tracker* and *Stimulator*), enabling BLE communication, Protobuf-based configuration, and real-time data streaming with callback-based notifications.

Architecture
------------
- **Bleak-based BLE Communication**: Cross-platform BLE support with asynchronous I/O.
- **Threaded Event Loop**: Background `asyncio` loop ensures non-blocking BLE operations.
- **Encapsulation and Inheritance**: `VNSDevice` handles shared BLE logic, extended by `VNSTracker` (sensor streaming) and `VNSStimulator` (stimulation control).
- **Flexible Callbacks**: Customizable notification handling via `start_notification(callback=...)`.

Key Features
------------
- **Device Discovery**: `VNSScanner` scans and filters SmartVNS devices.
- **Protobuf Configuration**: System and stimulation parameters serialized via Protobuf.
- **Custom Callbacks**: Users can define callbacks for BLE data processing.

Example:
```python
def custom_callback(name, sender, data):
    print(f"[{name}] Received:", decode_data(data))



stim = VNSStimulator("SmartVNS Stimulator")
stim.start_notification(callback=custom_callback)
"""

# Bleak
from bleak.backends.device import BLEDevice
from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData

# Protobuffer
from smartvns.config import SysConfig, StimConfig

import asyncio
import threading
import concurrent.futures
from typing import Union, Coroutine, Callable
import logging

from smartvns.vnsconnect.routines import *

log = logging.getLogger(__name__)


class LoopRunner():
    def __init__(self, timeout: float = 2):
        self.timeout = timeout
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._runner,
            daemon=True
        )
        self._ready = threading.Event()
        self._thread.start()

        # ready event used to sync startup
        if not self._ready.wait(timeout=timeout):
            raise RuntimeError("LoopRunner thread failed to start")

    def _runner(self):
        asyncio.set_event_loop(self._loop)
        # schedule to run when loop starts
        self._loop.call_soon_threadsafe(self._ready.set)
        self._loop.run_forever()

        # after loop stops,
        self._loop.close()

    def terminate(self):
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=self.timeout)

    def run(self, coro: Coroutine, timeout: float = 5):
        if not self._loop.is_running():
            raise RuntimeError("Event loop is not running")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError()


class Scanner(LoopRunner):
    """
    Scanner class to discover SmartVNS devices via BLE.
    """

    def __init__(self):
        super().__init__()

        self.devices = dict()
        self.scanner = BleakScanner()

    def start(self) -> None:
        """
        Start scanning for BLE devices.
        """
        self.run(
            self.scanner.start(),
        )

    def stop(self):
        """
        Stop scanning for BLE devices and filter for SmartVNS devices.
        """
        self.run(
            self.scanner.stop(),
        )

        self.devices = self._filter_devices(
            self.scanner.discovered_devices_and_advertisement_data
        )

    @staticmethod
    def _filter_devices(devices: dict[str, tuple[BLEDevice, AdvertisementData]]) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        filtered: dict[str, tuple[BLEDevice, AdvertisementData]] = {k: v for k, v in devices.items()
                                                                    if v[0].name and "SmartVNS" in v[0].name}
        return filtered


class VNSDevice(LoopRunner):
    def __init__(self, device: Union[str, BLEDevice]):
        super().__init__()

        self.device = device
        self._client = BleakClient(device)

    def connect(self,
                retries: int = 3,
                timeout: float = 5.0) -> None:

        run_timeout = timeout * retries + 1
        for _ in range(retries):
            self.run(
                connect_async(self._client),
                timeout=run_timeout
            )

    def disconnect(self, timeout: float = 5.0) -> None:
        self.run(
            disconnect_async(self._client),
            timeout=timeout
        )


class Tracker(VNSDevice):
    """
    Tracker class to handle SmartVNS Tracker specific operations.
    """

    def __init__(self, device: Union[str, BLEDevice]):
        super().__init__(device)

    def get_sys_config(self, timeout: float = 5.0) -> SysConfig:
        """
        Retrieve the system configuration from the device.

        Parameters
        ----------
        timeout : float
            Timeout for the operation in seconds.

        Returns
        -------
        SysConfig
            The system configuration retrieved from the device.


        """
        return self.run(
            read_sys_config_async(self._client),
            timeout=timeout
        )

    def set_sys_config(self,
                       cfg: SysConfig,
                       timeout: float = 5.0) -> None:
        """
        Set the system configuration on the device.

        Parameters
        ----------
        cfg : SysConfig
            The system configuration to set on the device.
        timeout : float
            Timeout for the operation in seconds.


        Returns
        -------
        None
            None

        """
        return self.run(
            write_sys_config_async(self._client, cfg),
            timeout=timeout
        )

    def start_notification(self,
                           handler: Callable[[bytearray], None],
                           timeout: float = 5.0) -> None:
        """
        Start notifications from the device with a custom handler.


        Parameters
        ----------
        handler : Callable[[bytearray], None]
            A callback function to handle incoming notification data.
        timeout : float
            Timeout for the operation in seconds.

        Returns
        -------
        None
            None       
        """

        # sender is known, no need to expose to user
        def _handler(_, data):
            handler(data)

        return self.run(
            start_notification_async(self._client, _handler),
            timeout=timeout
        )

    def stop_notification(self,
                          timeout: float = 5.0) -> None:
        """
        Stop notifications from the device.

        Parameters
        ----------
        timeout : float
            Timeout for the operation in seconds.

        Returns
        -------
        None
            None
        """

        return self.run(
            stop_notification_async(self._client),
            timeout=timeout
        )


class Stimulator(Tracker):

    """
    Stimulator class to handle SmartVNS Stimulator specific operations.
    """

    def __init__(self, device: Union[str, BLEDevice]):
        super().__init__(device)

    def get_stim_config(self, timeout: float = 5.0) -> StimConfig:
        """
        Retrieve the stimulation configuration from the device.

        Parameters
        ----------
        timeout : float
            Timeout for the operation in seconds.

        Returns
        -------
        StimConfig
            The stimulation configuration retrieved from the device.
        """
        return self.run(
            read_stim_config_async(self._client),
            timeout=timeout
        )

    def set_stim_config(self,
                        cfg: StimConfig,
                        timeout: float = 5.0) -> None:
        """
        Set the stimulation configuration on the device.

        Parameters
        ----------
        cfg : StimConfig
            The stimulation configuration to set on the device.
        timeout : float
            Timeout for the operation in seconds.

        Returns
        -------
        None
            None

        """
        return self.run(
            write_stim_config_async(self._client, cfg),
            timeout=timeout
        )

    def increase_intensity(self, timeout: float = 5.0) -> None:
        """
        Increase the stimulation intensity on the device.


        Parameters
        ----------
        timeout : float
            Timeout for the operation in seconds.

        Returns
        -------
        None
            None
        """
        return self.run(
            increase_stim_intensity_async(self._client),
            timeout=timeout
        )

    def decrease_intensity(self, timeout: float = 5.0) -> None:
        """
        Decrease the stimulation intensity on the device.

        Parameters
        ----------
        timeout : float
            Timeout for the operation in seconds.

        Returns
        -------
        None
            None
        """
        return self.run(
            decrease_stim_intensity_async(self._client),
            timeout=timeout
        )

    def trigger(self, duration_ms: int,
                timeout: float = 5.0) -> None:
        """
        Trigger a stimulation pulse for a specified duration.

        Parameters
        ----------
        duration_ms : int
            Duration of the stimulation pulse in milliseconds.
        timeout : float
            Timeout for the operation in seconds.

        Returns
        -------
        None
            None
        """
        cfg = self.get_stim_config()
        cfg.trigger_ms = duration_ms
        return self.set_stim_config(cfg, timeout=timeout)
