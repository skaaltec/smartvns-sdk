# SmartVNS SDK

Some example usecases of the VNSConnect SDK used with the SmartVNS research devices.

## Finding a device nearby
```python
# Example 1: scan and print SmartVNS devices

from smartvns import vnsconnect
import asyncio


async def scanner():
    scanner = vnsconnect.Scanner()
    scanner.start()
    await asyncio.sleep(5)  # Scan for 5 seconds
    scanner.stop()
    print("Scan complete. Found devices:")
    print(scanner.devices)
    if not scanner.devices:
        print("No VNS devices found. Exiting.")
        return
    else:
        for addr, (dev, adv) in scanner.devices.items():
            print(
                f"- {adv.local_name or dev.name} ({addr}) with RSSI {adv.rssi} dB")

    scanner.terminate()

if __name__ == "__main__":
    asyncio.run(scanner())

```

## Controlling a SmartVNS Stimulator with Configuration
```python
# Example 2: Connect and configure a stimulator,
# then increase intensity and trigger stimulation
# At the end, it disconnect from the devices
#IMPORTANT: you need to be in an async loop 

from smartvns.vnsconnect import Stimulator
from smartvns.config import StimConfig
import asyncio
"""
Options to connect to SmartVNS devices:

Options:
1. Connect via knon device alias 
  stim = Stimulator("AA:BB:CC:DD:EE:FF")
2. Run Scanner function 
    scanner = vnsconnect.Scanner()
    scanner.start()
    await asyncio.sleep(5)  # Scan for 5 seconds
    scanner.stop()


"""
async def connect():

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
    await asyncio.sleep(2)

  stim.disconnect()
  stim.terminate()

if __name__ == "__main__":
    asyncio.run(connect())
```
## Controlling a SmartVNS Stimulator with Configuration
This example shows, that a SmartVNS Stimulator is controllable via the Stimulator itself and the SDK commands as well.
Intensity can be controlled with the device, while this configuration is then used to trigger stimulations directly via the script.
```python
#Example 3: 

# Trigger Stimulation via 'Enter Command' in Terminal
# Press 'q' to quit.

# This is just a test script to verify that stimulation can be triggerd via USB and also via Stimulator directly.

# The code works that way, to configure the right intensity directly via the stimulator and then trigger the stimulation via the terminal command. This way we can test both the configuration and the triggering separately.


from smartvns.vnsconnect import Stimulator
from smartvns.config import StimConfig
import asyncio
import sys

"""
Options to connect to SmartVNS devices:

Options:
1. Connect via knon device alias 
  stim = Stimulator("AA:BB:CC:DD:EE:FF")
2. Run Scanner function 
    scanner = vnsconnect.Scanner()
    scanner.start()
    await asyncio.sleep(5)  # Scan for 5 seconds
    scanner.stop()


"""

async def connect():

    stim = Stimulator("AA:BB:CC:DD:EE:FF")
    stim.connect()
    print("Connected to stimulator.")

    current_config = stim.get_stim_config()
    print("\nCurrent stimulation configuration:")
    print(f"   Intensity: {current_config.intensity_uA} µA")

    try:
        while True:

            key = input()

            if key == "":  # Spacebar pressed
                print("Stimulation triggered!")
                stim.trigger(duration_ms=1000)
                print(
                    f"   Current intensity: {stim.get_stim_config().intensity_uA} µA")

            elif key.lower() == "q":  # Quit
                print("\nExiting...")
                break
            else:
                print(
                    f"Unknown input: '{key}' (press SPACE to trigger or 'q' to quit)")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    finally:
        print("Disconnecting...")
        stim.disconnect()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(connect())

```


## Receiving data from a device
Both SmartVNS devices transmit encoded binary data via notifications.
The data contained in a notification is guaranteed to contain one or more samples.
The device will not split a sample across notifications. However, notifications can be lost
due to poor signal quality. This must be accounted for in real-time use.

```python
# Example 3: Connect and stream data from a SmartVNS Tracker
#IMPORTANT: you need to be in an async loop (as in connect and scanner) 
from smartvns.vnsconnect import Tracker
import asyncio

tracker = Tracker("AA:BB:CC:DD:EE:FF") # or BLEDevice from previous scan
tracker.connect()

# save the incoming data to a binary file
with open("rec.bin", "wb") as f:
  def handler(data: bytearray):
    print(f"Received data: {len(data)} bytes")
    f.write(data)

  tracker.start_notification(handler)

  await asyncio.sleep(10)

  tracker.stop_notification()

  tracker.disconnect()
  tracker.terminate()
```

In most of the cases, it is useful to work with decoded data instead.

```python
# Example 4: Decode data in real-time
#IMPORTANT: you need to be in an async loop (as in connect and scanner) 
import asyncio
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

await asyncio.sleep(10)

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
#IMPORTANT: you need to be in an async loop (as in connect and scanner) 
import asyncio
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

    await asyncio.sleep(10)

    tracker.stop_notification()

    await asyncio.sleep(1)

    tracker.disconnect()
    tracker.terminate()
```

Note: the code in the handler should be relatively fast to execute.
For compute-intesive tasks defer the computation to other threads/processes.
