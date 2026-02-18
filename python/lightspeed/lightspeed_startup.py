"""
lightspeed_startup.py
---------------
Minimal entry point for the Lightspeed Panel.
Call show_lightspeed() from a shelf tool, hotkey, or script.
"""

import hou
from . import qt_utils
from .gallery_ui import LightspeedGallery

QtWidgets = qt_utils.QtWidgets

# ---------------------------------------------------------------------------
#  Singleton window reference
# ---------------------------------------------------------------------------
_instance = None


def show_lightspeed():
    """Create (or re-create) the Lightspeed Panel dialog."""
    global _instance

    # Close any previous instance to avoid hidden zombie windows
    if _instance is not None:
        try:
            _instance.close()
            _instance.deleteLater()
        except RuntimeError:
            pass
        _instance = None

    _instance = LightspeedGallery(parent=hou.ui.mainQtWindow())
    _instance.show()
