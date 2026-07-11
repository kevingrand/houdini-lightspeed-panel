"""
qt_utils.py
-----------
Backwards-compatibility shim. The Qt import logic moved to `qt.py`
(PySide6-first for Houdini 21). Import from `lightspeed.qt` in new code.
"""

from .qt import QtWidgets, QtGui, QtCore, PYSIDE_VERSION

# Old name kept for any external scripts that referenced it
BTC_PYSIDE_VERSION = PYSIDE_VERSION

__all__ = ["QtWidgets", "QtGui", "QtCore", "BTC_PYSIDE_VERSION", "PYSIDE_VERSION"]
