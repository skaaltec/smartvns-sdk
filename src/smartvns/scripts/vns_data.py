
import os
import asyncio
import threading
import struct
from typing import Optional, Union, Any, List

from ..config.proto.generated.python.smartvns_pb2 import FS_500DPS, FS_4G, SysConfig, StimConfig, IMUConf, GyroFS, AccFS, MAGConf, Dispatcher


from ..vnsconnect import Scanner, Stimulator, Tracker

STIM_ADDRESS = 'D621DCF4-0DC0-A927-B760-87775265E17F'
TRACKER_ADDRESS = 'D911EECA-DD7A-6A64-406B-A5CB4F88D677'
STIM_CONFIG = StimConfig(
    trigger_ms=1000,
    forward_us=500,
    deadband_us=200,
    period_us=10000,
    intensity_uA=200,
    retain_cfg=False
)
SYS_CONFIG = SysConfig(
    retain_cfg=True,
    imu=IMUConf(gyro_fs=FS_500DPS, acc_fs=FS_4G, odr=30),
    mag=MAGConf(odr=10),
    dispatch=Dispatcher(
        to_ble=Dispatcher.Stream(
            imu=True,
            mag=True,
            quat=True,
            log=False,
            vnsdata=True
        ),
        to_mem=Dispatcher.Stream(
            imu=False,
            mag=False,
            quat=False,
            log=False,
            vnsdata=False
        )
    )
)


def stim_callback(data):
    decoded = decode_data(data)
    # print(f"Received unparsed data from Stimulator:", data)
    # print(f"Len data: {len(data)}")
    # print(f"Received from Stimulator:", decoded)
    # see if VNS data is present
    if any(line[14] is not None for line in decoded):
        print("VNS Data received in Stimulator callback:")
        for line in decoded:
            if line[14] is not None:
                voltage = line[14]
                current = line[15]
                src_voltage = line[16]
                voltage_dif = src_voltage - voltage
                impedance = voltage_dif / \
                    current if current != 0 else float('inf')
                print(
                    f"Voltage: {voltage} mV, Current: {current} uA, Source Voltage: {src_voltage} V, Impedance: {impedance} Ohm")
                #
                print(line)


def tracker_callback(data):
    decoded = decode_data(data)
    # print(f"Received unparsed data from Tracker:", data)
    # print(f"Received from Tracker:", decoded)


async def async_worker():
    scanner = Scanner()
    scanner.start()

    await asyncio.sleep(3)
    scanner.stop()
    devices = scanner.devices
    if not devices:
        print("No VNS devices found. Exiting.")
        return
    else:
        for addr, (dev, adv) in devices.items():
            print(
                f"- {adv.local_name or dev.name} ({addr}) with RSSI {adv.rssi} dB")

    stim = Stimulator(STIM_ADDRESS)
    tracker = Tracker(TRACKER_ADDRESS)

    stim.connect()
    tracker.connect()
    print("Connected to Stimulator and Tracker.")

    stim.set_sys_config(SYS_CONFIG)
    stim.set_stim_config(STIM_CONFIG)

    tracker.set_sys_config(SYS_CONFIG)

    stim_cfg_stim = stim.get_stim_config()
    tracker_cfg = tracker.get_sys_config()
    stim_cfg = stim.get_sys_config()
    print("Stimulator Config:", stim_cfg_stim)
    print("Tracker Config:", tracker_cfg)
    print("Stimulator Sys Config:", stim_cfg)

    stim.start_notification(stim_callback)
    tracker.start_notification(tracker_callback)
    print("Started notifications from Stimulator and Tracker.")

    try:
        while True:
            await asyncio.sleep(1)
            stim_cfg = stim.get_sys_config()
            stim.set_stim_config(stim_cfg_stim)
            print("Set a stimulation")
            # print("Stimulator Sys Config Check:", stim_cfg)
            # config_tracker = tracker.get_sys_config()
            # print("Tracker configuration check:")
            # print(written_config_tracker)

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Exiting...")
    finally:
        stim.stop_notification()
        tracker.stop_notification()
        stim.disconnect()
        tracker.disconnect()
        print("Disconnected from devices.")


def decode_data(
        data: bytearray) -> List[List[Any]]:
    """
    Decode binary notification data into structured sensor samples.

    Parameters
    ----------
    data : bytearray
        Raw BLE notification payload.

    Returns
    -------
    list[list[Any]]
        Parsed data records representing IMU, MAG, QUAT, or VNS data samples.

    Raises
    ------
    struct.error
        If incoming data cannot be unpacked properly.
    """
    # Decode
    parser_imu = struct.Struct('<I6h')
    parser_mag = struct.Struct('<I3h')
    parser_quat = struct.Struct('<I4h')
    parser_vns_data = struct.Struct('<I4h')
    parser_imu_quat = struct.Struct('<I6h4h')
    parser_text_preamble = struct.Struct('<I')

    d = []
    try:
        while len(data) > 0:
            line = [None]*18  # 6 imu, 4 quat, 3 mag, 1 timestamp, 4 vns
            line[0] = 0

            sample_type = data[0]
            data = data[1:]
            if sample_type == 0:
                sample_len = parser_imu.size
                sample = parser_imu.unpack(data[:sample_len])
                line[0:7] = sample
            elif sample_type == 1:
                sample_len = parser_quat.size
                sample = parser_quat.unpack(data[:sample_len])
                line[0] = sample[0]
                line[7:11] = map(lambda x: x / 32768.0, sample[1:])
            elif sample_type == 2:
                sample_len = parser_mag.size
                sample = parser_mag.unpack(data[:sample_len])
                line[0] = sample[0]
                line[11:14] = sample[1:]
            elif sample_type == 3:
                sample_len = parser_vns_data.size
                sample = parser_vns_data.unpack(data[:sample_len])
                ts, a, b, c, e = sample

                # print("\n===== VNS DATA RECEIVED =====")
                # print(f"Timestamp: {ts}")
                # print(f"Field1: {a}")
                # print(f"Field2: {b}")
                # print(f"Field3: {c}")
                # print(f"Field4: {e}")
                # print("==============================\n")

                line[0] = ts
                line[14:] = sample[1:]

            elif sample_type == 4:
                sample_len = parser_imu_quat.size
                sample = parser_imu_quat.unpack(data[:sample_len])
                line[0:7] = sample[0:7]
                # Convert quaternion to float
                line[7:11] = map(lambda x: x / 32768.0, sample[7:11])

            # elif sample_type == 4:
            #     # Inspect payload length to decide on IMU+Quat vs VNS-Data
            #     remaining = len(data)

            #     if remaining >= parser_imu_quat.size:
            #         # IMU + QUAT packet
            #         sample_len = parser_imu_quat.size
            #         sample = parser_imu_quat.unpack(data[:sample_len])

            #         line[0:7] = sample[0:7]                 # IMU
            #         line[7:11] = [x / 32768.0 for x in sample[7:11]]  # Quat

            #         print("Decoded IMU+QUAT packet")

            #     elif remaining >= parser_vns_data.size:
            #         # VNS stimulation packet
            #         sample_len = parser_vns_data.size
            #         ts, a, b, c, d = parser_vns_data.unpack(data[:sample_len])

            #         line[0] = ts
            #         line[14:] = (a, b, c, d)

            #         print("Decoded VNSDATA packet")

            elif sample_type == 66:
                sample_len = data[0]
                string = data[1:1+sample_len].decode('utf-8')
            d.append(line)
            data = data[sample_len:]
    except struct.error as e:
        print(f"Error unpacking data: {e}")
        print(f"Remaining data length: {len(data)}")
        if len(data) > 0:
            print(f"First few bytes of remaining data: {data[:10]}")
    finally:
        return d


if __name__ == "__main__":
    # Example usage: Scan for devices and print their addresses

    threading.Thread(target=asyncio.run, args=(async_worker(),)).start()
