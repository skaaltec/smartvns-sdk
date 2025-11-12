"""
Utilities for encoding/decoding Sys and Stim configurations (protobuf).

"""
try:
    # Prefer the in-repo generated package path
    from .proto.generated.python.smartvns_pb2 import  (
        SysConfig,
        StimConfig,
        IMUConf,
        MAGConf,
        AccFS,
        GyroFS,
        Dispatcher,
    )
except Exception:
    raise ImportError(
        "Could not import generated protobuf symbols for smartvns.\n"
        "Ensure the generated Python sources from protobuf/generated/python are on PYTHONPATH,\n"
        "or install the generated module so it is importable as `smartvns_pb2`."
    )

__all__ = [
    "SysConfig",
    "StimConfig",
    "IMUConf",
    "MAGConf",
    "AccFS",
    "GyroFS",
    "Dispatcher",
]


# Attach Google-style docstrings to the imported protobuf message classes so
# Sphinx/autodoc and IDEs show helpful documentation. These do not change
# runtime behavior of the generated classes; they only provide human-readable
# docs at runtime.
SysConfig.__doc__ = """System configuration for SmartVNS devices.

The message contains settings for the IMU, magnetometer
and dispatcher streams.

Args:
    retain_cfg (bool): Persist configuration on device when written.
    imu (IMUConf): IMU configuration (gyro and accelerometer full-scale and ODR).
    mag (MAGConf): Magnetometer configuration (ODR).
    dispatch (Dispatcher): Define which data to stream to BLE and/or memory.


Initialization examples (set all fields):

1) Construct and set fields manually::

    cfg = SysConfig()
    cfg.retain_cfg = False
    cfg.imu.gyro_fs = GyroFS.FS_500DPS
    cfg.imu.acc_fs = AccFS.FS_4G
    cfg.imu.odr = 60    # in Hz
    cfg.mag.odr = 10    # in Hz

    # Explicitly set all dispatcher stream flags for both destinations
    cfg.dispatch.to_ble.imu = True
    cfg.dispatch.to_ble.mag = True
    cfg.dispatch.to_ble.quat = False
    cfg.dispatch.to_ble.log = False
    cfg.dispatch.to_ble.vnsdata = False

    cfg.dispatch.to_mem.imu = True
    cfg.dispatch.to_mem.mag = True
    cfg.dispatch.to_mem.quat = False
    cfg.dispatch.to_mem.log = False
    cfg.dispatch.to_mem.vnsdata = False

2) Build from a Python dict using ``google.protobuf.json_format.ParseDict``::

    from google.protobuf.json_format import ParseDict

    d = {
        "retain_cfg": True,
        "imu": {"gyro_fs": "FS_500DPS", "acc_fs": "FS_4G", "odr": 60},
        "mag": {"odr": 10},
        "dispatch": {
            "to_ble": {"imu": True, "mag": True, "quat": False, "log": False, "vnsdata": False},
            "to_mem": {"imu": True, "mag": True, "quat": False, "log": False, "vnsdata": False}
        }
    }

    cfg = SysConfig(**d)

Notes:
    - When using ``ParseDict`` enum fields may be provided as their symbolic
      names (e.g. ``"FS_500DPS"``) or numeric values.
"""


StimConfig.__doc__ = """Stimulation configuration for SmartVNS Stimulator devices.

Fields:
    retain_cfg (bool): Persist configuration on device when written.
    trigger_ms (int): Stimulation pulse duration in milliseconds.
    forward_us (int): Forward delay in microseconds.
    deadband_us (int): Deadband duration in microseconds.
    period_us (int): Overall stimulation period in microseconds.
    intensity_uA (int): Stimulation intensity in microamperes.

Note: All fields are required by the proto schema; explicitly initialize all
fields before use.

Initialization examples (set all fields):

    # Manual construction - set each required field
    s = StimConfig()
    s.retain_cfg = False
    s.trigger_ms = 1000
    s.forward_us = 250
    s.deadband_us = 100
    s.period_us = 40000
    s.intensity_uA = 150

    # From a dict using json_format.ParseDict - include all fields
    from google.protobuf.json_format import ParseDict
    d = {
        "retain_cfg": False,
        "trigger_ms": 1000,
        "forward_us": 250,
        "deadband_us": 100,
        "period_us": 40000,
        "intensity_uA": 100,
    }
    stim_cfg = StimConfig(**d)
"""


Dispatcher.__doc__ = """Dispatcher configuration controlling streamed outputs.

The ``Dispatcher`` message contains an embedded ``Stream`` message with
boolean flags indicating which data streams are routed to the BLE interface
(``to_ble``) and which are stored to memory (``to_mem``).

Stream fields (inside ``Dispatcher.Stream``):
    imu (bool): Include IMU data stream.
    mag (bool): Include magnetometer stream.
    quat (bool): Include quaternion stream.
    log (bool): Include device logs.
    vnsdata (bool): Include SmartVNS-specific data.

Example (dict-style construction using ``ParseDict``)::

    # Provide all stream flags for both destinations
    "d": {
        "to_ble": {"imu": True, "mag": True, "quat": False, "log": False, "vnsdata": False},
        "to_mem": {"imu": True, "mag": True, "quat": False, "log": False, "vnsdata": False}
    }
    from google.protobuf.json_format import ParseDict
    disp = Dispatcher()
    ParseDict(d, disp)
"""
