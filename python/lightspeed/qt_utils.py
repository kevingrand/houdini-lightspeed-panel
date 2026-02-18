"""
qt_utils.py
-------------
A compatibility shim between PySide2 (Houdini < 19.5/20) and PySide6 (Houdini >= 20).
This allows the same codebase to run across multiple Houdini versions.
"""

import sys

# Try importing PySide2 first (common in older/current stable pipelines)
# Then fall back to PySide6 (newer Houdini versions)

try:
    from PySide2 import QtWidgets, QtGui, QtCore
    BTC_PYSIDE_VERSION = 2
except ImportError:
    try:
        from PySide6 import QtWidgets, QtGui, QtCore
        BTC_PYSIDE_VERSION = 6
    except ImportError:
        raise ImportError("Could not import PySide2 or PySide6. Ensure you are running this in a standard Houdini environment.")

# Export these core modules so other scripts can import from here
__all__ = ["QtWidgets", "QtGui", "QtCore", "BTC_PYSIDE_VERSION"]
