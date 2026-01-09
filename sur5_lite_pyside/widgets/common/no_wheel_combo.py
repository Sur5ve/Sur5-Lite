#!/usr/bin/env python3
from PySide6.QtWidgets import QComboBox


class NoWheelComboBox(QComboBox):
    """A QComboBox that ignores wheel events unless the popup is open.

    This prevents accidental selection changes when users scroll the sidebar
    with a touchpad while hovering over the combobox.
    """

    def wheelEvent(self, event):  # noqa: N802 (Qt signature)
        try:
            view = self.view()
            if view.isVisible():
                return super().wheelEvent(event)
        except Exception:
            pass
        event.ignore()






