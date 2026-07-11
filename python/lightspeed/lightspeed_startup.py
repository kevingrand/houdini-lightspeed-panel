"""
lightspeed_startup.py
---------------------
Entry point for the Lightspeed Panel.
Call show_lightspeed() from a shelf tool, hotkey, or script.
(Module name kept from v1 so existing shelf tools keep working.)
"""

from .panel import LightspeedPanel

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

    import hou
    _instance = LightspeedPanel(parent=hou.ui.mainQtWindow())
    _instance.show()
    return _instance
