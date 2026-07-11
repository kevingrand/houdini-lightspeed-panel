"""
lightspeed_startup.py
---------------------
Entry point for the Lightspeed Panel.
Call show_lightspeed() from a shelf tool, hotkey, script, or the
nodegraphhooks TAB hook. (Module name kept from v1 so existing shelf
tools keep working.)
"""

from .panel import LightspeedPanel

# ---------------------------------------------------------------------------
#  Singleton window reference
# ---------------------------------------------------------------------------
_instance = None


def show_lightspeed(editor=None):
    """Create (or re-create) the Lightspeed Panel popup.

    editor: optional hou.NetworkEditor to anchor context to (the TAB hook
    passes the editor the keypress happened in); otherwise the panel
    detects the editor under the mouse cursor.
    """
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
    _instance = LightspeedPanel(parent=hou.ui.mainQtWindow(), editor=editor)
    _instance.show()
    return _instance


def create_embedded_panel():
    """A persistent (non-popup) panel widget for a Python Panel pane.
    Used by python_panels/lightspeed.pypanel — returns the widget, the
    pane owns its lifetime."""
    return LightspeedPanel(embedded=True)
