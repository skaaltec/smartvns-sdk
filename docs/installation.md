# Installation

This project is distributed as a pure-Python package. The primary distribution
method for the current release is a pre-built wheel artifact that you can
download from the GitHub Releases page for the project.

This page shows a few supported installation methods and quick verification
and troubleshooting tips. Commands are shown for PowerShell on Windows; on
other platforms the commands are the same but you may need to adapt path
syntax and virtual environment activation commands.

## Requirements

- Python 3.8 or later (3.9 is known to be used in the development environment).
- Device with support for Bluetooth 4.2 or newer, and Bluetooth device enabled.

## Install from a release (recommended)

1. Download the wheel file from the project's GitHub Releases page.
	 The filename will look like ``smartvns-<version>-py3-none-any.whl``.

2. [optional] create a virtual environment (conda, venv, uv):

Notes:
- You can also install the wheel directly from a GitHub release URL if you
	prefer, for example:

```powershell
python -m pip install "https://github.com/skaaltec/smartvns-cli/releases/download/v<version>/smartvns-<version>-py3-none-any.whl"
```

Replace the URL and filenames with the actual release tag and wheel name.

## Install from source (editable / developer install)

If you want to install from a local checkout (for development or to run the
CLI from the checked-out code), clone the repository and install in editable
mode:

```powershell
# clone repository
git clone https://github.com/skaaltec/smartvns-cli.git
cd smartvns-cli

# create + activate a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install in editable mode (will install runtime dependencies)
python -m pip install -e .
```

This installs the package in editable mode so changes to the source are
reflected immediately when you import the package.

<!-- ## Install from PyPI (future / optional)

If the package is published to PyPI in the future you can install it via:

```powershell
python -m pip install smartvns
``` -->

### Uninstall

To remove the package installed with pip:

```powershell
python -m pip uninstall smartvns
```
