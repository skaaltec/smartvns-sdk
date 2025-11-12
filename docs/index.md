# SmartVNS — Python tools and SDK

SmartVNS is a small hardware + software system for vagus nerve stimulation
research and prototyping. This repository contains a Python SDK and a
command-line toolkit to interact with SmartVNS devices over two transport
layers:

- Wireless BLE (Tracker / Stimulator) using the `vnsconnect` Python module.
- Wired USB / serial interactions and utility commands via the CLI tools.

## Quick links

- [Installation guide](installation.md) — how to set up the Python
  environment, dependencies and tools.
- [Getting started & samples](vnsconnect.md) — short, copy-pasteable examples
  that show scanner usage, notification callbacks, and simple stimulation
  workflows.
- [vnsconnect module reference](vnsconnect.md) — API docs for the wireless
  BLE interface (Scanner, Tracker, Stimulator).
- [CLI reference](cli.md) — documentation for the command-line utilities that
  operate over a wired USB/serial connection.

## What you'll find in these docs

Installation
:
  Step-by-step instructions to create the virtual environment used by the
  project and install the packages required to run the SDK and CLI tools.

Getting started & samples
:
  Minimal, runnable examples demonstrating common tasks:
  - Discovering nearby SmartVNS devices with the `Scanner`.
  - Connecting to a `Tracker` and receiving notifications.
  - Configuring and driving a `Stimulator` (set config, increase intensity,
    trigger pulses).

vnsconnect (wireless)
:
  The `vnsconnect` module provides a high-level Python API for communicating
  with SmartVNS Tracker and Stimulator devices over BLE. It exposes:
  - `Scanner` — advertise discovery and filtering for SmartVNS devices.
  - `Tracker` — read/write system configuration and register notification
    callbacks for sensor data.
  - `Stimulator` — read/write stimulation configuration and control
    stimulation (increase/decrease intensity, trigger pulses).

CLI (wired / USB serial)
:
  The CLI tools are designed for workflows where devices are connected over a
  serial link (USB). They provide utility commands for flashing, logging,
  and interacting with devices when a direct wired connection is preferred.

## Next steps

1. Open the [installation guide](installation.md) and follow the environment
   setup steps.
2. Try the short examples under [Getting started & samples](vnsconnect.md) to
   confirm you can discover and connect to a device.
3. Browse the API reference pages for details on configuration objects and
   available operations.
