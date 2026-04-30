from dataclasses import asdict, is_dataclass
import queue
import threading
import time
from pathlib import Path
from typing import List, Union

from smartvns.utils import Sample


_SENTINEL = object()


class DataLogger:
    """Asynchronously log decoded samples (or raw bytes) to a file.

    The logger pushes incoming items onto an internal queue and a
    dedicated daemon thread drains the queue and writes to disk. This
    keeps disk I/O off the BLE notification thread so the callback
    returns quickly.

    Each call to the instance enqueues one or more items; the writer
    thread serializes them as one line per item.

    Args:
        path: Path to the log file. Opened in append mode by default.
        mode: File open mode (default: ``"a"`` to append).

    Example:
        ```
        decoder = Decoder()
        logger = DataLogger("log.txt")

        def callback(data: bytearray):
            samples = decoder(data)
            logger(samples)

        stim.start_notification(callback)
        ...
        logger.close()
        ```
    """

    def __init__(self, path: Union[str, Path], mode: str = "a"):
        self.path = Path(path)
        self._queue: queue.Queue = queue.Queue()
        self._file = open(self.path, mode, buffering=1)  # line-buffered
        self._thread = threading.Thread(target=self._writer, daemon=True)
        self._closed = threading.Event()
        self._thread.start()

    def __call__(self, item: Union[Sample, List[Sample], bytes, bytearray]) -> None:
        """Enqueue a sample, list of samples, or raw bytes for logging.

        The host-side timestamp is captured here (at enqueue time) so it
        reflects when the data arrived, not when the writer thread got to it.
        """
        if self._closed.is_set():
            raise RuntimeError("DataLogger is closed")
        now = time.time()
        if isinstance(item, list):
            for s in item:
                self._queue.put((now, s))
        else:
            self._queue.put((now, item))

    def _writer(self) -> None:
        while True:
            entry = self._queue.get()
            if entry is _SENTINEL:
                break
            ts, item = entry
            try:
                self._file.write(f"{ts:.6f}\t{self._format(item)}\n")
            except Exception as e:
                # don't crash the writer thread on a single bad record
                print(f"DataLogger write error: {e}")

    @staticmethod
    def _format(item) -> str:
        if is_dataclass(item):
            return f"{type(item).__name__}\t{asdict(item)}"
        return str(item)

    def close(self, timeout: float = 5.0) -> None:
        """Flush pending items, stop the writer thread, and close the file."""
        if self._closed.is_set():
            return
        self._closed.set()
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=timeout)
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
