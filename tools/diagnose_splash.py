#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Splash Screen Diagnostic Tool
Traces every widget creation, method call, and rendering event to find the doubled text issue
"""

import sys
import os
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path for imports
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPaintEvent

# Monkey-patch to trace widget creation and method calls
original_init = QWidget.__init__
original_show = QWidget.show
original_setStyleSheet = QWidget.setStyleSheet
original_paint = QWidget.paintEvent
original_label_init = QLabel.__init__
original_label_setText = QLabel.setText

widget_counter = {}
call_log = []

def traced_widget_init(self, parent=None):
    class_name = self.__class__.__name__
    widget_counter[class_name] = widget_counter.get(class_name, 0) + 1
    count = widget_counter[class_name]
    
    log_entry = f"[WIDGET CREATE] {class_name} #{count} (parent={parent.__class__.__name__ if parent else 'None'})"
    print(log_entry)
    call_log.append(log_entry)
    
    original_init(self, parent)

def traced_show(self):
    class_name = self.__class__.__name__
    log_entry = f"[SHOW] {class_name} at {id(self)}"
    print(log_entry)
    call_log.append(log_entry)
    
    original_show(self)

def traced_setStyleSheet(self, stylesheet):
    class_name = self.__class__.__name__
    log_entry = f"[STYLESHEET] {class_name} - {stylesheet[:100]}"
    print(log_entry)
    call_log.append(log_entry)
    
    original_setStyleSheet(self, stylesheet)

def traced_paint(self, event):
    class_name = self.__class__.__name__
    log_entry = f"[PAINT] {class_name} at {id(self)}"
    # Don't print paint events as they happen too frequently
    call_log.append(log_entry)
    
    if original_paint:
        original_paint(self, event)

def traced_label_init(self, text="", parent=None):
    log_entry = f"[LABEL CREATE] text='{text}' parent={parent.__class__.__name__ if parent else 'None'}"
    print(log_entry)
    call_log.append(log_entry)
    
    original_label_init(self, text, parent)

def traced_label_setText(self, text):
    log_entry = f"[LABEL setText] {id(self)} -> '{text}'"
    print(log_entry)
    call_log.append(log_entry)
    
    original_label_setText(self, text)

# Apply monkey patches
QWidget.__init__ = traced_widget_init
QWidget.show = traced_show
QWidget.setStyleSheet = traced_setStyleSheet
QWidget.paintEvent = traced_paint
QLabel.__init__ = traced_label_init
QLabel.setText = traced_label_setText

print("\n" + "="*80)
print("SPLASH SCREEN DIAGNOSTIC MODE")
print("="*80 + "\n")

# Now import and create splash screen
from sur5_lite_pyside.widgets.splash_screen import SplashScreen

app = QApplication(sys.argv)

print("\n" + "="*80)
print("CREATING SPLASH SCREEN")
print("="*80 + "\n")

splash = SplashScreen()

print("\n" + "="*80)
print("SPLASH SCREEN CREATED - ANALYZING WIDGET TREE")
print("="*80 + "\n")

# Analyze the widget tree
def print_widget_tree(widget, indent=0):
    prefix = "  " * indent
    class_name = widget.__class__.__name__
    obj_id = id(widget)
    
    # Check if it's a QLabel and get its text
    text_info = ""
    if isinstance(widget, QLabel):
        text = widget.text()
        if text:
            text_info = f" [text='{text}']"
    
    print(f"{prefix}├─ {class_name} (id={obj_id}){text_info}")
    
    # Print children
    for child in widget.children():
        if isinstance(child, QWidget):
            print_widget_tree(child, indent + 1)

print("Widget Tree:")
print_widget_tree(splash)

print("\n" + "="*80)
print("CHECKING FOR DUPLICATE WIDGETS")
print("="*80 + "\n")

# Find all labels with same text
labels_by_text = {}
def collect_labels(widget):
    if isinstance(widget, QLabel):
        text = widget.text()
        if text:
            if text not in labels_by_text:
                labels_by_text[text] = []
            labels_by_text[text].append((id(widget), widget))
    
    for child in widget.children():
        if isinstance(child, QWidget):
            collect_labels(child)

collect_labels(splash)

print("Labels by text content:")
for text, labels in labels_by_text.items():
    print(f"  '{text}': {len(labels)} instance(s)")
    if len(labels) > 1:
        print(f"    ⚠️ WARNING: DUPLICATE TEXT FOUND!")
        for widget_id, label in labels:
            print(f"       - Label id={widget_id}, parent={label.parent().__class__.__name__ if label.parent() else 'None'}")
            print(f"         geometry={label.geometry()}, visible={label.isVisible()}")

print("\n" + "="*80)
print("LAYOUT ANALYSIS")
print("="*80 + "\n")

layout = splash.layout()
if layout:
    print(f"Layout type: {layout.__class__.__name__}")
    print(f"Layout item count: {layout.count()}")
    print("\nLayout items:")
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item:
            widget = item.widget()
            if widget:
                class_name = widget.__class__.__name__
                if isinstance(widget, QLabel):
                    text = widget.text()
                    print(f"  [{i}] {class_name} - '{text}'")
                else:
                    print(f"  [{i}] {class_name}")
            else:
                print(f"  [{i}] Spacer/Stretch")
else:
    print("⚠️ WARNING: No layout found!")

print("\n" + "="*80)
print("SHOWING SPLASH SCREEN")
print("="*80 + "\n")

splash.show()
app.processEvents()

print("\n" + "="*80)
print("DIAGNOSTIC COMPLETE")
print("="*80 + "\n")

print("\nWidget creation summary:")
for widget_type, count in sorted(widget_counter.items()):
    print(f"  {widget_type}: {count}")

# Keep splash visible for inspection
print("\nSplash screen is now visible.")
print("The window will close in 10 seconds...")

QTimer.singleShot(10000, app.quit)

sys.exit(app.exec())

