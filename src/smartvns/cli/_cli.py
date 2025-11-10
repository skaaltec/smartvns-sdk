import asyncio
from pathlib import Path
from typing import List, Union, Annotated
from enum import Enum

import typer
import rich
from serial.tools import list_ports as lports
from google.protobuf.json_format import MessageToJson, MessageToDict, Parse

from smartvns.config import SysConfig, StimConfig
from . import routines

app = typer.Typer()

# create subcommand groups for get and set to organize device queries/commands
get_app = typer.Typer()
set_app = typer.Typer()

app.add_typer(get_app, name="get")
app.add_typer(set_app, name="set")

@app.command("list")
def list_ports():
    """List available serial ports."""
    ports = lports.comports()
    for port in ports:
        typer.echo(f"{port.device}: {port.description}")


@set_app.command("time")
def set_datetime(ports: Annotated[List[str], typer.Argument()]):
    """Set current system time on devices provided in PORTS.
    """
    asyncio.run(routines.set_time(ports))


@get_app.command("battery")
def get_battery(ports: Annotated[List[str], typer.Argument()]):
    """Get battery level from device."""
    b = asyncio.run(routines.get_battery(ports))
    rich.print(b)


@get_app.command("version")
def get_fw_version(ports: Annotated[List[str], typer.Argument()]):
    """Get firmware version from device."""
    v = asyncio.run(routines.get_version(ports))
    rich.print(v)


class ConfigType(str, Enum):
    sys = "sys"
    stim = "stim"

@get_app.command("config")
def get_config(cfg_type: ConfigType,
              port: Annotated[str, typer.Argument()],
              save: Annotated[Union[Path, None], typer.Option(help="If provided, save configuration to this file.")] = None):
    cfg = asyncio.run(routines.get_config(port, cfg_type.value))

    if cfg is None:
        rich.print(f"[red]Failed to get {cfg_type} configuration from device at {port}[/red]")
        raise typer.Exit(code=1)

    if save:
        with open(save, "w") as f:
            f.write(MessageToJson(cfg))
            rich.print(f"Configuration saved to {save}")

    cfg = MessageToDict(cfg)
    rich.print(cfg)


@set_app.command("config")
def set_config(cfg_type: ConfigType,
              port: Annotated[str, typer.Argument()],
              file: Annotated[Union[Path, None], typer.Option(help="If provided, save configuration to this file.")] = None):

    """Set configuration on device(s).

    cfg_type must be 'sys' or 'stim'. VALUE is a string representation of the
    configuration to set; this is a thin wrapper and currently calls a controller
    stub which will apply the value to the device(s).
    """

    if file:
        with open(file, "r") as f:
            data = f.read()
        if cfg_type == ConfigType.sys:
            value = SysConfig()
        else:
            value = StimConfig()
        value = Parse(data, value)


    asyncio.run(routines.set_config(port, cfg_type.value, value))


@app.command()
def reboot(ports: Annotated[List[str], typer.Argument()]):
    """Reset connected devices."""
    asyncio.run(routines.reboot(ports))


@app.command(name="factory-reset")
def factory_reset(ports: Annotated[List[str], typer.Argument()]):
    """Erase storage and reset devices (full factory reset)."""
    asyncio.run(routines.factory_reset(ports))


@app.command()
def dfu(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    ports: Annotated[List[str], typer.Argument()],
):
    """Reboot to bootloader on devices and upload image from PATH."""
    image = open(path, "rb").read()

    asyncio.run(routines.dfu(ports, image))


@app.command()
def pair(port1: str = typer.Argument(...), port2: str = typer.Argument(...)):
    """Exchange OOB keys to pair two connected devices."""
    asyncio.run(routines.pair(port1, port2))


@app.command()
def unpair(port1: str = typer.Argument(...), port2: str = typer.Argument(...)):
    """Clear pairing information from two connected devices."""
    asyncio.run(routines.unpair(port1, port2))
