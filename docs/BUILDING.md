# Building Sur5 Lite

This guide covers building Sur5 Lite for distribution on Windows, macOS, and Linux.

---

## Prerequisites

### All Platforms
- Python 3.11+
- pip (Python package manager)
- Git

### Windows
- Visual Studio Build Tools (for llama-cpp-python compilation)
- PowerShell 5.1+

### macOS
- Xcode Command Line Tools (`xcode-select --install`)
- Homebrew (recommended)

### Linux
- GCC/G++ compiler
- Development headers (`python3-dev`, `build-essential`)

---

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Sur5ve/Sur5-Lite.git
cd Sur5-Lite/App

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Building Executables

Sur5 Lite uses PyInstaller for creating standalone executables.

### Windows

```powershell
cd App/scripts/build
.\build_windows.ps1
```

The output will be in `Sur5_Windows_Distribution/Sur5.exe`.

### macOS

```bash
cd App/scripts/build
chmod +x build_macos.sh
./build_macos.sh
```

The output will be in `Sur5_macOS_Distribution/Sur5.app`.

### Linux

```bash
cd App/scripts/build
chmod +x build_linux.sh
./build_linux.sh
```

The output will be in `dist/Sur5`.

---

## Build Options

### PyInstaller Spec File

The `config/Sur5_CrossPlatform.spec` file controls the build process:

```python
# Key options:
APP_NAME = 'Sur5'
CONSOLE_MODE = False    # No console window (set via env var)
icon = 'Images/sur5_icon.ico'  # Application icon
```

### Including Models

To bundle a default model with the build:

1. Place your `.gguf` model in `models/`
2. Add to the spec file's `datas`:
   ```python
   datas=[('models/*.gguf', 'models'), ...]
   ```

---

## Portable/USB Distribution

To create a portable package for USB drives:

```powershell
# Windows
.\scripts\package_for_usb.ps1
```

This creates a self-contained folder with:
- Sur5 Lite executable
- Python runtime (embedded)
- Default model
- Portable settings

---

## Troubleshooting Builds

### Windows: "Microsoft Visual C++ required"

Install Visual Studio Build Tools:
```powershell
winget install Microsoft.VisualStudio.2022.BuildTools
```

### macOS: Code signing issues

For local testing, use ad-hoc signing:
```bash
codesign --force --deep -s - dist/Sur5.app
```

### Linux: Missing libraries

Install required dependencies:
```bash
sudo apt install python3-dev build-essential libgl1-mesa-glx
```

---

## Next Steps

- [Configuration Guide](CONFIGURATION.md) — Customize Sur5 Lite settings
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues and solutions
