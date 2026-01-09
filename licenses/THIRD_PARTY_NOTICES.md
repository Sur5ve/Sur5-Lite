# Third-Party Notices

Sur5 Lite includes or depends on the following third-party software:

## Core Dependencies

### PySide6
- **License:** LGPL v3 / Commercial
- **Website:** https://www.qt.io/qt-for-python
- **Usage:** Cross-platform UI framework
- **Source Code:** Available at:
  - https://code.qt.io/cgit/pyside/pyside-setup.git/
  - https://github.com/pyside/pyside-setup
- **LGPL Compliance:** Sur5 Lite uses PySide6 via dynamic linking (Python imports). 
  Per LGPL v3, you have the right to modify and replace the PySide6 library.
  See [LGPL_COMPLIANCE.md](../docs/LGPL_COMPLIANCE.md) for detailed instructions.

### llama-cpp-python
- **License:** MIT
- **Website:** https://github.com/abetlen/llama-cpp-python
- **Usage:** Python bindings for llama.cpp LLM inference

### llama.cpp
- **License:** MIT
- **Website:** https://github.com/ggerganov/llama.cpp
- **Usage:** Backend LLM inference engine

## Build Tools

### PyInstaller
- **License:** GPL v2 (with special exception for bundled apps)
- **Website:** https://pyinstaller.org
- **Usage:** Creating standalone executables
- **Note:** The GPL exception allows distribution of applications built with PyInstaller without requiring the application to be GPL-licensed.

## Python Libraries

### nltk
- **License:** Apache 2.0
- **Website:** https://www.nltk.org
- **Usage:** Natural language processing utilities

### markdown
- **License:** BSD 3-Clause
- **Website:** https://python-markdown.github.io
- **Usage:** Markdown rendering

### psutil
- **License:** BSD 3-Clause
- **Website:** https://github.com/giampaolo/psutil
- **Usage:** System monitoring and resource detection

### tqdm
- **License:** MIT / MPL 2.0
- **Website:** https://github.com/tqdm/tqdm
- **Usage:** Progress bar utilities

### huggingface_hub
- **License:** Apache 2.0
- **Website:** https://github.com/huggingface/huggingface_hub
- **Usage:** Model downloading (optional)

## Bundled Model

### IBM Granite 4.0-h-1b
- **License:** Apache 2.0
- **Website:** https://huggingface.co/ibm-granite/granite-4.0-h-1b-GGUF
- **Usage:** Default AI model for chat inference
- **Copyright:** IBM Corporation

## Bundled Fonts

### IBM Plex Sans
- **License:** SIL Open Font License 1.1 (OFL)
- **Website:** https://github.com/IBM/plex
- **Usage:** Primary UI font
- **Copyright:** IBM Corp.
- **OFL Compliance:** Font may be bundled and redistributed with software per OFL 1.1.
  See `fonts/OFL.txt` for full license text.

---

## Full License Texts

For the complete license texts, please refer to:
- **Sur5 Lite:** [MIT License](../LICENSE)
- **PySide6 (LGPL v3):** https://www.gnu.org/licenses/lgpl-3.0.html
- **MIT License:** https://opensource.org/licenses/MIT
- **Apache 2.0:** https://www.apache.org/licenses/LICENSE-2.0
- **BSD 3-Clause:** https://opensource.org/licenses/BSD-3-Clause
- **SIL OFL 1.1:** https://scripts.sil.org/OFL

---

## Your Rights Under LGPL v3

Per the GNU Lesser General Public License v3, you have the following rights regarding
the PySide6 library used by Sur5 Lite:

1. **Right to Modify:** You may modify PySide6 and use your modified version with Sur5 Lite.
2. **Right to Replace:** You may replace the bundled PySide6 with a different version.
3. **Source Code Access:** PySide6 source code is freely available (links above).
4. **Reverse Engineering:** You may reverse engineer Sur5 Lite for debugging modifications to PySide6.

For detailed instructions on exercising these rights, see [LGPL_COMPLIANCE.md](../docs/LGPL_COMPLIANCE.md).

---

*This file was last updated: January 2026*
