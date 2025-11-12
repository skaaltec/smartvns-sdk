import asyncio
import threading
import concurrent.futures
from typing import Union, Coroutine, Callable

from bleak.backends.device import BLEDevice
from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData

from smartvns.config import SysConfig, StimConfig
from smartvns.vnsconnect.routines import *


class LoopRunner():
    """Run asyncio coroutines in a dedicated background thread.

    LoopRunner creates a private :class:`asyncio` event loop running in a
    daemon thread. Callers can schedule coroutines to run on that loop using
    :meth:`run`. The helper is intended to make it straightforward to invoke
    async Bleak operations from synchronous code.

    Attributes:
        timeout (float): Default timeout used for thread startup and joins.
        _loop (asyncio.AbstractEventLoop): The event loop running in the
            background thread.
        _thread (threading.Thread): Daemon thread running ``_runner``.
        _ready (threading.Event): Event set once the background loop is ready.
    """

    def __init__(self, timeout: float = 2.0):
        """Create and start the background asyncio loop thread.

        Args:
            timeout: Seconds to wait for the background loop to signal
                readiness. If the loop thread fails to start within this
                period a :class:`RuntimeError` is raised.
        """
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
        """Internal thread target: set up and run the event loop.

        This method is executed in the background thread. It sets the loop
        for the thread, signals readiness by setting ``_ready``, then runs the
        loop until :meth:`terminate` requests a stop. After the loop stops
        the loop object is closed.
        """
        asyncio.set_event_loop(self._loop)
        # schedule to run when loop starts
        self._loop.call_soon_threadsafe(self._ready.set)
        self._loop.run_forever()

        # after loop stops,
        self._loop.close()

    def terminate(self):
        """Gracefully stop the background event loop and terminate the associated thread.
        """
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=self.timeout)

    def run(self, coro: Coroutine, timeout: float = 5):
        """Schedule a coroutine to run on the background event loop and wait.

        Args:
            coro: The coroutine object to execute on the runner's event loop.
            timeout: Maximum seconds to wait for the coroutine to complete.

        Returns:
            The value returned by the coroutine.

        Raises:
            RuntimeError: If the runner's event loop is not running.
            TimeoutError: If the coroutine does not complete within ``timeout``.
        """
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

    # annotation of instance attributes
    devices: dict[str, tuple[BLEDevice, AdvertisementData]]
    scanner: BleakScanner

    def __init__(self):
        """Initialize the scanner and start the background event loop.

        Attributes:
            devices (dict): Mapping of device identifier to a tuple of
                ``(BLEDevice, AdvertisementData)`` containing discovered
                devices that match the SmartVNS naming filter. Initially an
                empty dict until ``stop()`` is called.
            scanner (BleakScanner): Bleak scanner instance used to perform
                BLE discovery.
        """

        super().__init__()

        self.devices = dict()
        self.scanner = BleakScanner()

    def start(self) -> None:
        """
        Start scanning for BLE devices.
        This method returns immediately after scheduling and will raise RuntimeError
        if the background loop is not available.

        Returns:
            None

        Raises:
            RuntimeError: If the internal event loop is not running.
        """
        self.run(
            self.scanner.start(),
        )

    def stop(self) -> None:
        """Stop the Bleak scanner and update ``self.devices``.

        The resulting scanned SmartVNS devices are stored in the `devices`
        attribute.

        Returns:
            None
        """

        self.run(
            self.scanner.stop(),
        )

        self.devices = self._filter_devices(
            self.scanner.discovered_devices_and_advertisement_data
        )

    @staticmethod
    def _filter_devices(devices: dict[str, tuple[BLEDevice, AdvertisementData]]) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        """Filter discovered BLE devices for SmartVNS devices.

        Args:
            devices: Mapping returned by BleakScanner containing device id
                keys and values as ``(BLEDevice, AdvertisementData)`` tuples.

        Returns:
            A new dict containing only the items where the BLEDevice has a
            non-empty ``name`` and the substring ``"SmartVNS"`` appears in
            that name.
        """

        filtered: dict[str, tuple[BLEDevice, AdvertisementData]] = {k: v for k, v in devices.items()
                                    if v[0].name and "SmartVNS" in v[0].name}
        return filtered


class VNSDevice(LoopRunner):
    """Base class for SmartVNS BLE devices.

    This class provides a thread-backed asyncio event loop (via
    :class:`LoopRunner`) and an associated :class:`BleakClient` instance used
    to perform BLE operations. Concrete device classes (for example,
    ``Tracker`` and ``Stimulator``) inherit from this class.

    Attributes:
        device (str | BLEDevice): Address string or BleakDevice instance used
            to construct the underlying BleakClient.
        _client (BleakClient): Bleak client bound to ``device`` used for
            asynchronous BLE operations.
    """

    def __init__(self, device: Union[str, BLEDevice]):
        """Initialize the event loop runner and Bleak client.

        Args:
            device: A device identifier (address string) or a
                :class:`BLEDevice` instance. The value is passed to
                :class:`BleakClient` to create a client bound to the
                target device.
        """
        super().__init__()

        self.device = device
        self._client = BleakClient(device)

    def connect(self,
                retries: int = 3,
                timeout: float = 5.0) -> None:
        """Connect to the target device, retrying on failure.

        This method schedules the asynchronous ``connect_async`` routine on
        the background event loop and will attempt the connection up to
        ``retries`` times. A conservative per-call timeout is computed from
        ``timeout`` and ``retries`` to give the async routine sufficient time
        to complete across attempts.

        Args:
            retries: Number of connection attempts (default: 3).
            timeout: Timeout in seconds for each attempt (default: 5.0).

        Raises:
            TimeoutError: If the underlying asyncio call times out.
            RuntimeError: If the event loop is not running (propagated from
                :meth:`LoopRunner.run`).
        """

        run_timeout = timeout * retries + 1
        for _ in range(retries):
            self.run(
                connect_async(self._client),
                timeout=run_timeout
            )

    def disconnect(self, timeout: float = 5.0) -> None:
        """Disconnect the Bleak client from the device.

        Args:
            timeout: Timeout in seconds for the disconnect operation.

        Raises:
            TimeoutError: If the underlying asyncio call times out.
        """
        self.run(
            disconnect_async(self._client),
            timeout=timeout
        )


class Tracker(VNSDevice):
    """
    Tracker device class to handle SmartVNS Tracker specific operations.
    """

    def __init__(self, device: Union[str, BLEDevice]):
        super().__init__(device)

    def get_sys_config(self, timeout: float = 5.0) -> SysConfig:
        """Retrieve the system configuration from the device.

        Args:
            timeout (float): Timeout for the operation in seconds.

        Returns:
            SysConfig: The system configuration retrieved from the device.
        """
        return self.run(
            read_sys_config_async(self._client),
            timeout=timeout
        )

    def set_sys_config(self,
                       cfg: SysConfig,
                       timeout: float = 5.0) -> None:
        """Set the system configuration on the device.

        Args:
            cfg (SysConfig): The system configuration to set on the device.
            timeout (float): Timeout for the operation in seconds.

        Returns:
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
        The handler function signature should be:
            handler(data: bytearray) -> None

        If this method is called with different handlers, all handlers will
        be called when a notification is received.

        Args:
            handler (Callable[[bytearray], None]): A callback function to
                handle incoming notification data.
            timeout (float): Timeout for the operation in seconds.

        Returns:
            None
        """

        if handler is None:
            raise ValueError("Handler function must be provided")

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
        Stop notifications from the device and unregister all handlers.

        Args:
            timeout (float): Timeout for the operation in seconds.

        Returns:
            None
        """

        return self.run(
            stop_notification_async(self._client),
            timeout=timeout
        )


class Stimulator(Tracker):

    """
    Stimulator class to handle SmartVNS Stimulator specific operations.
    This device extends the Tracker class, meaning providing the same access
    to System Configuration and Notification handling as the Tracker device.
    """

    def __init__(self, device: Union[str, BLEDevice]):
        super().__init__(device)

    def get_stim_config(self, timeout: float = 5.0) -> StimConfig:
        """
        Retrieve the stimulation configuration from the device.

        Args:
            timeout (float): Timeout for the operation in seconds.

        Returns:
            StimConfig: The stimulation configuration retrieved from the device.
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

        Args:
            cfg (StimConfig): The stimulation configuration to set on the device.
            timeout (float): Timeout for the operation in seconds.

        Returns:
            None
        """
        return self.run(
            write_stim_config_async(self._client, cfg),
            timeout=timeout
        )

    def increase_intensity(self, timeout: float = 5.0) -> None:
        """
        Increase the stimulation intensity on the device.

        Args:
            timeout (float): Timeout for the operation in seconds.

        Returns:
            None
        """
        return self.run(
            increase_stim_intensity_async(self._client),
            timeout=timeout
        )

    def decrease_intensity(self, timeout: float = 5.0) -> None:
        """
        Decrease the stimulation intensity on the device.

        Args:
            timeout (float): Timeout for the operation in seconds.

        Returns:
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

        Args:
            duration_ms (int): Duration of the stimulation pulse in milliseconds.
            timeout (float): Timeout for the operation in seconds.

        Returns:
            None
        """
        cfg = self.get_stim_config()
        cfg.trigger_ms = duration_ms
        return self.set_stim_config(cfg, timeout=timeout)
