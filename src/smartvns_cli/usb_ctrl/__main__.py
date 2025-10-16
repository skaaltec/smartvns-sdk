"""Execute the usb_ctrl Typer app when the package is run with -m.

This allows: python -m smartvns_cli.usb_ctrl --help
"""
from .cli import app

def main():
    app()

if __name__ == "__main__":
    main()
