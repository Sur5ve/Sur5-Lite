#!/usr/bin/env python3
"""
Branding Constants - Central location for all Sur5ve branding

Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com

================================================================================
TRADEMARK NOTICE
================================================================================
SUR5VE is a trademark of Sur5ve LLC.
Sur5 is a related mark protected under trademark law.

The "Sur5", "Sur5ve", and "Sur5 Lite" names, as well as all associated logos,
are trademarks of Sur5ve LLC and are NOT covered by the MIT License.

If you fork or redistribute this software, you MUST:
  1. Replace all branding constants below with your own
  2. Remove all Sur5/Sur5ve logos from the Images/ directory
  3. Create your own distinct visual identity

Unauthorized use of Sur5ve trademarks may result in legal action.
See TRADEMARK.md for complete policy.
================================================================================
"""

# =============================================================================
# Product Naming
# =============================================================================

APP_NAME = "Sur5 Lite"
APP_DISPLAY_NAME = "Sur5 Lite"
APP_TAGLINE = "Open Source Edge AI — Offline, Portable, No Cloud"
APP_SUBTITLE = "Sur5 Lite"
COMPANY_NAME = "Sur5ve LLC"
COMPANY_WEBSITE = "https://sur5ve.com"
CHAT_ASSISTANT_NAME = "Sur5 Lite"

# =============================================================================
# Version Information
# =============================================================================

VERSION = "2.0.0"
VERSION_CODENAME = "Open Source Release"

# =============================================================================
# License Information
# =============================================================================

LICENSE_NAME = "MIT License"
LICENSE_URL = "https://opensource.org/licenses/MIT"

# =============================================================================
# UI Text Strings
# =============================================================================

ASSISTANT_LABEL = "Sur5 Lite"
PROCESSING_TEXT = "Sur5 Lite is thinking..."
READY_TEXT = "Sur5 Lite is ready"
ERROR_PREFIX = "Sur5 Lite encountered an issue"
WELCOME_MESSAGE = "Hello! I'm Sur5 Lite, your open source Edge AI assistant. How can I help you today?"

# =============================================================================
# About Dialog
# =============================================================================

ABOUT_TEXT = f"""
<h2>{APP_NAME}</h2>
<p><b>Version {VERSION}</b> — {VERSION_CODENAME}</p>
<p>Open Source Edge AI</p>
<p>An Edge AI assistant that runs entirely on your device.</p>
<p>No cloud, no API keys, complete privacy.</p>
<br>
<p><b>Created by {COMPANY_NAME}</b></p>
<p><a href="{COMPANY_WEBSITE}">{COMPANY_WEBSITE}</a></p>
<br>
<p><i>Licensed under {LICENSE_NAME}</i></p>
"""

ABOUT_TEXT_PLAIN = f"""
{APP_NAME}
Version {VERSION} — {VERSION_CODENAME}

Open Source Edge AI
An Edge AI assistant that runs entirely on your device.
No cloud, no API keys, complete privacy.

Created by {COMPANY_NAME}
{COMPANY_WEBSITE}

Licensed under {LICENSE_NAME}
"""

# =============================================================================
# Credits
# =============================================================================

CREDITS_TEXT = """
<h3>Powered By</h3>
<ul>
<li><a href="https://github.com/ggerganov/llama.cpp">llama.cpp</a> - Fast LLM inference</li>
<li><a href="https://github.com/microsoft/BitNet">BitNet.cpp</a> - 1-bit LLM inference</li>
<li><a href="https://www.qt.io/qt-for-python">PySide6</a> - Cross-platform UI</li>
</ul>
"""

# =============================================================================
# Export all constants
# =============================================================================

__all__ = [
    # Product
    "APP_NAME",
    "APP_DISPLAY_NAME",
    "APP_TAGLINE",
    "APP_SUBTITLE",
    "COMPANY_NAME",
    "COMPANY_WEBSITE",
    "CHAT_ASSISTANT_NAME",
    # Version
    "VERSION",
    "VERSION_CODENAME",
    # License
    "LICENSE_NAME",
    "LICENSE_URL",
    # UI Text
    "ASSISTANT_LABEL",
    "PROCESSING_TEXT",
    "READY_TEXT",
    "ERROR_PREFIX",
    "WELCOME_MESSAGE",
    # About
    "ABOUT_TEXT",
    "ABOUT_TEXT_PLAIN",
    "CREDITS_TEXT",
]
