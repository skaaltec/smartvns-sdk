"""
vnsconnect_c.py
===============

SmartVNS Python SDK (Tracker / Stimulator)
------------------------------------------

This module provides a **modular and extensible Python SDK** for SmartVNS BLE devices,
including both the *Tracker* and *Stimulator* units. It offers a high-level API
for BLE communication, configuration handling via Protocol Buffers, and
real-time data streaming through flexible callback-based notification handling.

Architecture
------------
The SDK is built on top of the **Bleak** library for cross-platform BLE communication.
It manages all asynchronous I/O internally through a dedicated background event loop
running in its own thread, allowing users to interact synchronously from standard
Python code without blocking BLE operations.

Key Design Features
-------------------
**Encapsulation and Inheritance:**
    The `VNSDevice` base class encapsulates all shared BLE communication logic,
    including connection handling, configuration read/write, and notification management.
`VNSTracker` and `VNSStimulator` extend `VNSDevice` with device-specific logic:
    `VNSTracker` for sensor streaming, and `VNSStimulator` for stimulation control.

**Threaded Event Loop:**
    Each device runs an internal `asyncio` event loop in a background thread.
    This ensures non-blocking BLE communication even in synchronous scripts.

**Flexible Notification Callbacks (NEW):**
    Notification handling is now callback-based. The user can pass a custom callback
    function to `start_notification(callback=...)` to process incoming BLE data
    in any desired way (e.g., logging, visualization, or data buffering).

If no callback is provided, the SDK defaults to printing decoded data via
the internal `notification_callback()` method.

    Example:
        ```python
        def custom_callback(name, sender, data):
            print(f"[{name}] Received:", decode_data(data))

        stim = VNSStimulator("SmartVNS Stimulator")
        stim.start_notification(callback=custom_callback)
        ```

**Automatic Device Discovery and Connection:**
    The `VNSScanner` class provides asynchronous BLE scanning and filters for
    recognized SmartVNS devices ("SmartVNS Tracker", "SmartVNS Stimulator", "Zephyr").

**Protocol Buffer Configuration Management:**
    System and stimulation parameters are serialized using Protobuf messages
    (`SysConfig` and `Stim`) for consistent communication with the embedded firmware.

Class Hierarchy
---------------
VNSScanner
    Handles BLE scanning and discovery of SmartVNS devices.

VNSDevice
    Base class implementing connection management, configuration exchange,
    background event loop handling, and notification subscription.

VNSTracker(VNSDevice)
    Adds IMU, MAG, and QUAT sensor configuration creation and streaming support.

VNSStimulator(VNSTracker)
    Extends tracker functionality with stimulation control logic (intensity,
    pulse timing, deadband configuration, and runtime intensity stepping).

Dependencies
------------
**bleak**: Asynchronous BLE communication

**protobuf**: Serialization of configuration messages

**asyncio + threading**: Concurrent event-loop execution

**google.protobuf.message**: Parsing of binary Protobuf payloads

Change Log (v2.0 – Callback Update)
-----------------------------------
Introduced `callback` parameter in `start_notification()`:
Users can now inject a custom callback to handle BLE data.
The callback signature is:
    ```python
    def callback(device_name: str, sender: Any, data: bytearray) -> None:
        ...
    ```

The internal event handler wraps this callback inside `_start_notification_async()`
and falls back to the built-in `notification_callback()` if no callback is given.

Improved class encapsulation:
    `_user_callback` stored as instance variable
    Shared BLE I/O methods remain encapsulated within `VNSDevice`
    Derived classes only implement device-specific extensions

Backwards compatible:
    Existing code that relied on automatic printing still works without modification.

Summary
-------
This SDK now follows a more scalable, modular, and user-extensible architecture.
Developers can connect to multiple devices simultaneously, assign independent
callbacks to each, and manage both configuration and live data streams
from synchronous Python applications without concurrency conflicts.
"""

# Bleak
from bleak.backends.device import BLEDevice
from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData

# Protobuffer
from smartvns_cli.config import SysConfig, StimConfig

import asyncio
import threading
import concurrent.futures
from typing import Union, Coroutine
import logging

from smartvns_cli.ble.vnsconnect_async import *

log = logging.getLogger(__name__)


class LoopRunner():
    def __init__(self, timeout: float = 2):
        self.timeout = timeout
        self._loop = asyncio.new_event_loop()
        self._thread  =threading.Thread(
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


class VNSScanner(LoopRunner):
    def __init__(self):
        super().__init__()

        self.devices = dict()
        self.scanner = BleakScanner()

    def start(self) -> None:
        self.run(
            self.scanner.start(),
        )

    def stop(self):
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


class VNSTracker(VNSDevice):
    def __init__(self, device: Union[str, BLEDevice]):
        super().__init__(device)

    def get_sys_config(self, timeout: float = 5.0) -> SysConfig:
        return self.run(
            read_sys_config_async(self._client),
            timeout=timeout
        )

    def set_sys_config(self,
                        cfg: SysConfig,
                        timeout: float = 5.0) -> None:
        return self.run(
            write_sys_config_async(self._client, cfg),
            timeout=timeout
        )

    # todo: notifications


class VNSStimulator(VNSTracker):
    def __init__(self, device: Union[str, BLEDevice]):
        super().__init__(device)

    def get_stim_config(self, timeout: float = 5.0) -> StimConfig:
        return self.run(
            read_stim_config_async(self._client),
            timeout=timeout
        )

    def set_stim_config(self,
                        cfg: StimConfig,
                        timeout: float = 5.0) -> None:
        return self.run(
            write_stim_config_async(self._client, cfg),
            timeout=timeout
        )

    def increase_intensity(self, timeout: float = 5.0) -> None:
        return self.run(
            increase_stim_intensity_async(self._client),
            timeout=timeout
        )

    def decrease_intensity(self, timeout: float = 5.0) -> None:
        return self.run(
            decrease_stim_intensity_async(self._client),
            timeout=timeout
        )

    def trigger(self, duration_ms: int,
                timeout: float = 5.0) -> None:
        cfg = self.get_stim_config()
        cfg.trigger_ms = duration_ms
        return self.set_stim_config(cfg, timeout=timeout)
