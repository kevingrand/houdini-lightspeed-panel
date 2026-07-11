"""
qt.py
-----
Qt compatibility shim. Houdini 21 ships PySide6 only, so try that first;
fall back to PySide2 for older installs (H19.x/20.0).
"""

try:
    from PySide6 import QtWidgets, QtGui, QtCore
    PYSIDE_VERSION = 6
except ImportError:
    try:
        from PySide2 import QtWidgets, QtGui, QtCore
        PYSIDE_VERSION = 2
    except ImportError:
        raise ImportError(
            "Lightspeed: could not import PySide6 or PySide2. "
            "Run this inside a Houdini session."
        )


def exec_menu(menu, pos):
    """Version-safe QMenu.exec (exec_ is deprecated in PySide6)."""
    fn = getattr(menu, "exec", None) or getattr(menu, "exec_")
    return fn(pos)


__all__ = ["QtWidgets", "QtGui", "QtCore", "PYSIDE_VERSION", "exec_menu"]
