"""smartvns_cli.config

Utilities for encoding/decoding Sys and Stim configurations (protobuf).

"""
try:
    # Prefer the in-repo generated package path
    from .proto.generated.python.smartvns_pb2 import  (
        SysConfig,
        Stim,
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
    "Stim",
    "IMUConf",
    "MAGConf",
    "AccFS",
    "GyroFS",
    "Dispatcher",
]
