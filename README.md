# NetMotive IP Switcher

A lightweight cross-platform GUI tool to manage and switch between multiple static IP configurations.

## Features
- View and select active network adapters
- Create, edit, delete static IP profiles
- Apply profiles to interfaces (requires admin)
- Import/export from CSV
- Clean modern UI with application icon

## Build Instructions (Windows)
Install dependencies and build executable with icon:

```bash
pip install pyinstaller psutil
pyinstaller --onefile --windowed --icon=icon.ico netmotive_ip_switcher.py
```

## Usage
Launch the `.exe` as Administrator to apply adapter changes.