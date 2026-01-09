# LGPL v3 Compliance Guide

Sur5 Lite uses PySide6, which is licensed under the GNU Lesser General Public License v3 (LGPL v3).
This document explains your rights under LGPL v3 and how to exercise them.

---

## Your Rights

Under LGPL v3, you have the following rights regarding PySide6:

### 1. Right to Obtain Source Code
You may obtain the complete source code for PySide6:
- **Official Repository:** https://code.qt.io/cgit/pyside/pyside-setup.git/
- **GitHub Mirror:** https://github.com/pyside/pyside-setup
- **By Request:** Contact support@sur5ve.com for a copy

### 2. Right to Modify
You may modify PySide6 for any purpose, including:
- Bug fixes
- Security patches
- Feature additions
- Performance improvements

### 3. Right to Replace
You may replace the PySide6 library bundled with Sur5 Lite with your own modified version.

### 4. Right to Reverse Engineer
You may reverse engineer Sur5 Lite for the purpose of debugging your modifications to PySide6.

---

## How to Replace PySide6

### Method A: Running from Source (Recommended)

The simplest way to use a modified PySide6 is to run Sur5 Lite from source:

```bash
# 1. Clone the repository
git clone https://github.com/Sur5ve/Sur5-Lite.git
cd Sur5-Lite

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# 3. Install your modified PySide6
pip install /path/to/your/modified/pyside6

# 4. Install other dependencies
pip install -r requirements.txt

# 5. Run Sur5 Lite
python launch_sur5.py
```

### Method B: Windows Portable Distribution (--onedir)

If you're using the Windows portable distribution (`Sur5_Windows_Portable/`):

1. Navigate to the distribution folder
2. Locate the `PySide6` folder containing Qt DLLs
3. Replace the DLL files with your modified versions
4. Ensure ABI compatibility (same Qt version)

```
Sur5_Windows_Portable/
├── Sur5.exe
├── PySide6/                    ← Replace files here
│   ├── Qt6Core.dll
│   ├── Qt6Gui.dll
│   ├── Qt6Widgets.dll
│   └── ...
└── ...
```

### Method C: macOS Application Bundle

For macOS `.app` bundles:

1. Right-click `Sur5.app` → "Show Package Contents"
2. Navigate to `Contents/Frameworks/`
3. Replace the Qt frameworks with your modified versions

```
Sur5.app/
└── Contents/
    ├── MacOS/
    │   └── Sur5
    └── Frameworks/             ← Replace frameworks here
        ├── QtCore.framework/
        ├── QtGui.framework/
        ├── QtWidgets.framework/
        └── ...
```

### Method D: Linux AppImage or Distribution

For Linux installations:

```bash
# Option 1: Run from source (recommended)
python launch_sur5.py

# Option 2: Set PYTHONPATH to your modified PySide6
export PYTHONPATH=/path/to/modified/pyside6:$PYTHONPATH
./sur5
```

---

## PySide6 Version Information

Sur5 Lite is tested with PySide6 version 6.5.0 and later.

To check the bundled version:
```python
from PySide6 import __version__
print(__version__)
```

For compatibility, your replacement PySide6 should:
- Be version 6.5.0 or later
- Include QtCore, QtGui, and QtWidgets modules
- Be compiled for your platform architecture

---

## Building Modified PySide6

To build PySide6 from source:

```bash
# 1. Clone the repository
git clone https://code.qt.io/pyside/pyside-setup.git
cd pyside-setup

# 2. Install build dependencies
pip install sphinx numpy

# 3. Build (requires Qt 6.5+ installed)
python setup.py build

# 4. Install to your environment
pip install .
```

For detailed build instructions, see:
https://doc.qt.io/qtforpython/gettingstarted.html

---

## Technical Details

### Dynamic Linking Model

Sur5 Lite uses PySide6 via Python's standard import mechanism:

```python
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
```

This constitutes **dynamic linking** under LGPL v3 terminology because:
1. PySide6 is a separate, replaceable module
2. No PySide6 code is compiled into Sur5 Lite
3. Users can substitute any compatible PySide6 version

### No Modifications to PySide6

Sur5ve LLC has not modified PySide6. We use the unmodified, official releases
from PyPI (`pip install PySide6`).

---

## Frequently Asked Questions

### Q: Do I need to share my Sur5 Lite modifications?
**A:** No. Sur5 Lite's source code is MIT licensed. You can modify it however you want.
You only need to share modifications to PySide6 itself (if you distribute those modifications).

### Q: Can I use Sur5 Lite commercially?
**A:** Yes. Both the MIT license (Sur5 Lite) and LGPL v3 (PySide6) permit commercial use.

### Q: What if I can't get the replacement working?
**A:** Contact support@sur5ve.com and we'll help you exercise your LGPL rights.

### Q: Does the single-file Windows .exe comply with LGPL?
**A:** Yes. PyInstaller extracts bundled libraries to a temporary directory at runtime,
maintaining the dynamic linking model. We also provide a `--onedir` portable distribution
for easier library replacement.

---

## Contact

For questions about LGPL compliance or to request PySide6 source code:

- **Email:** support@sur5ve.com
- **Website:** https://sur5ve.com
- **GitHub:** https://github.com/Sur5ve

---

## References

- [LGPL v3 Full Text](https://www.gnu.org/licenses/lgpl-3.0.html)
- [Qt Licensing FAQ](https://www.qt.io/licensing/)
- [PySide6 Documentation](https://doc.qt.io/qtforpython/)
- [GNU LGPL FAQ](https://www.gnu.org/licenses/gpl-faq.html)

---

**© 2024-2026 Sur5ve LLC. Licensed under MIT License.**

**PySide6 is licensed under LGPL v3 by The Qt Company.**
