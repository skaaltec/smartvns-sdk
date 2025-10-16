This package contains helpers for working with the Sys and Stim protobuf
configurations used by smartvns devices.

How it finds the generated protobuf code

- If you keep the generated sources in `protobuf/generated/python` (as in the
  repository), ensure that the project root is on PYTHONPATH or that you run
  Python with the repository root as the working directory. The helpers will
  try to import `protobuf.generated.python.smartvns_pb2`.

- Alternatively, you can install the generated module into your environment so
  it is importable as `smartvns_pb2`.

Provided utilities

- `decode_sys_config_from_bytes(bytes) -> SysConfig message`
- `encode_sys_config_to_bytes(msg) -> bytes`
- `sys_config_to_dict(msg) -> dict`
- `dict_to_sys_config(dict) -> SysConfig message`

And the same helpers for Stim (`decode_stim_from_bytes`, `dict_to_stim`, etc.).

Next steps

- If you want, I can wire these helpers into the CLI so `get config` automatically
  decodes the returned payload and pretty-prints JSON.
- Add unit tests for encoding/decoding roundtrips.
