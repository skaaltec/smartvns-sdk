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

## Controlling a SmartVNS Stimulator
```python
# Example 2: Connect and configure a stimulator,
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


## Receiving data from a device
Both SmartVNS devices transmit encoded binary data via notifications.
The data contained in a notification is guaranteed to contain one or more samples.
The device will not split a sample across notifications. However, notifications can be lost
due to poor signal quality. This must be accounted for in real-time use.

```python
# Example 3: Connect and stream data from a SmartVNS Tracker
import time
from smartvns.vnsconnect import Tracker

tracker = Tracker("AA:BB:CC:DD:EE:FF") # or BLEDevice from previous scan
tracker.connect()

# save the incoming data to a binary file
with open("rec.bin", "wb") as f:
  def handler(data: bytearray):
    print(f"Received data: {len(data)} bytes")
    f.write(data)

  tracker.start_notification(handler)

  time.sleep(10)

  tracker.stop_notification()

  tracker.disconnect()
  tracker.terminate()
```

In most of the cases, it is useful to work with decoded data instead.

```python
# Example 4: Decode data in real-time
import time
from smartvns.vnsconnect import Tracker

tracker = Tracker("AA:BB:CC:DD:EE:FF") # or BLEDevice from previous scan
tracker.connect()

from smartvns.utils import Decoder

decoder = Decoder()

def callback(data: bytearray):
    samples = decoder(data)
    for s in samples:
        print(s)

tracker.start_notification(callback)

time.sleep(10)

tracker.stop_notification()

tracker.disconnect()
tracker.terminate()
```

```output
MagSample(timestamp=10068798, mag_x=-2073, mag_y=134, mag_z=672)
IMUSample(timestamp=10068821, gyr_x=3909, gyr_y=1045, gyr_z=-7077, acc_x=2040, acc_y=595, acc_z=-6948)
IMUSample(timestamp=10068854, gyr_x=1000, gyr_y=1115, gyr_z=-49, acc_x=2165, acc_y=629, acc_z=-7409)
IMUSample(timestamp=10068888, gyr_x=-26, gyr_y=-41, gyr_z=25, acc_x=2168, acc_y=629, acc_z=-7411)
...
```

Custom pipelines for the data can be implemented directly in the handler.
Here, raw IMU and magnetometer data are scaled and saved to two different files.
Other file formats (tables/csv), sockets and other data sinks can be directly
implemented in the handler.

```python
#Example 5: define a custom data pipeline
import time
from smartvns.vnsconnect import Tracker

tracker = Tracker("AA:BB:CC:DD:EE:FF") # or BLEDevice from previous scan
tracker.connect()
cfg = tracker.get_sys_config()

from smartvns.utils import Decoder, UnitScaler, Filter, SampleType

decoder = Decoder()
mag_filt = Filter(types=[SampleType.MAG])
imu_filt = Filter(types=[SampleType.IMU])
scaler = UnitScaler(cfg)  # requires a cfg to scale data properly

with open("imu.log", "w") as f_imu, open("mag.log", "w") as f_mag:
    def callback(data: bytearray):
        samples = decoder(data)
        mag = mag_filt(samples) # select magnetometer samples
        imu = imu_filt(samples)
        # magnetometer samples are scaled and saved in mag.log
        for s in scaler(mag):
            f_mag.write(f"{s}\n")
        # imu samples are not scaled instead
        for s in imu:
            f_imu.write(f"{s}\n")

    tracker.start_notification(callback)

    time.sleep(10)

    tracker.stop_notification()

    time.sleep(1)

    tracker.disconnect()
    tracker.terminate()
```

Note: the code in the handler should be relatively fast to execute.
For compute-intesive tasks defer the computation to other threads/processes.
