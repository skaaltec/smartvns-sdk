# SmartVNS SDK

Some example usecases of the VNSConnect SDK used with the SmartVNS research devices.

## Finding a device nearby
```python
# Example 1: scan and print SmartVNS devices
import time
from smartvns.vnsconnect import Scanner

scanner = Scanner()
scanner.start()
time.sleep(5)
scanner.stop()

for address, (dev, adv) in scanner.devices.items():
  print(f"{address}: {dev.name} rssi: {adv.rssi} dBm")

scanner.terminate()
```

## Receiving data from a device
```python
# Example 2: Connect and stream data from a SmartVNS Tracker
import time
from smartvns.vnsconnect import Tracker

tracker = Tracker("AA:BB:CC:DD:EE:FF") # or BLEDevice from previous scan
tracker.connect()

def handler(data: bytearray):
  print(f"Received data: {len(data)} bytes")

tracker.start_notification(handler)
time.sleep(10)
tracker.stop_notification()
tracker.disconnect()
tracker.terminate()
```

## Controlling a SmartVNS Stimulator
```python
# Example 3: Connect and configure a stimulator,
# then increase intensity and trigger stimulation
import time
from smartvns.vnsconnect import Stimulator
from smartvns.config import StimConfig

stim = Stimulator("AA:BB:CC:DD:EE:FF")
stim.connect()

cfg = StimConfig(**{
    "retain_cfg": False,
    "trigger_ms": 1000,
    "forward_us": 250,
    "deadband_us": 100,
    "period_us": 40000,
    "intensity_uA": 100,
})

stim.set_stim_config(cfg)

for _ in range(3):
  stim.increase_intensity()
  stim.trigger(duration_ms=1000)
  time.sleep(2)

stim.disconnect()
stim.terminate()
```
