import asyncio
from pathlib import Path
from typing import List, Union, Annotated
from enum import Enum

import typer
import rich
from serial.tools import list_ports
from google.protobuf.json_format import MessageToJson, MessageToDict, Parse

from smartvns_cli.config import SysConfig, Stim
from . import controller

app = typer.Typer()

# create subcommand groups for get and set to organize device queries/commands
get_app = typer.Typer()
set_app = typer.Typer()

app.add_typer(get_app, name="get")
app.add_typer(set_app, name="set")

@app.command("list")
def lports():
    """List available serial ports."""
    ports = list_ports.comports()
    for port in ports:
        typer.echo(f"{port.device}: {port.description}")


@set_app.command("time")
def settime(ports: Annotated[List[str], typer.Argument()]):
    """Set current system time on devices provided in PORTS.
    """
    asyncio.run(controller.set_time(ports))


@get_app.command("battery")
def getbatt(ports: Annotated[List[str], typer.Argument()]):
    """Get battery level from device."""
    b = asyncio.run(controller.get_battery(ports))
    rich.print(b)


@get_app.command("version")
def getversion(ports: Annotated[List[str], typer.Argument()]):
    """Get firmware version from device."""
    v = asyncio.run(controller.get_version(ports))
    rich.print(v)


class ConfigType(str, Enum):
    sys = "sys"
    stim = "stim"

@get_app.command("config")
def getconfig(cfg_type: ConfigType,
              port: Annotated[str, typer.Argument()],
              save: Annotated[Union[Path, None], typer.Option(help="If provided, save configuration to this file.")] = None):
    cfg = asyncio.run(controller.get_config(port, cfg_type.value))

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
def setconfig(cfg_type: ConfigType,
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
            value = Stim().config
        value = Parse(data, value)


    asyncio.run(controller.set_config(port, cfg_type.value, value))


@app.command()
def reboot(ports: Annotated[List[str], typer.Argument()]):
    """Reset connected devices."""
    asyncio.run(controller.reboot(ports))


@app.command(name="factory-reset")
def factory_reset(ports: Annotated[List[str], typer.Argument()]):
    """Erase storage and reset devices (full factory reset)."""
    asyncio.run(controller.factory_reset(ports))


@app.command()
def dfu(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    ports: Annotated[List[str], typer.Argument()],
):
    """Reboot to bootloader on devices and upload image from PATH."""
    image = open(path, "rb").read()

    asyncio.run(controller.dfu(ports, image))


@app.command()
def pair(port1: str = typer.Argument(...), port2: str = typer.Argument(...)):
    """Exchange OOB keys to pair two connected devices."""
    asyncio.run(controller.pair(port1, port2))


@app.command()
def unpair(port1: str = typer.Argument(...), port2: str = typer.Argument(...)):
    """Clear pairing information from two connected devices."""
    asyncio.run(controller.unpair(port1, port2))
