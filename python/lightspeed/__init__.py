"""
Lightspeed Panel — fast, keyboard-first node search & creation for Houdini.

Public API:
    from lightspeed import show_lightspeed
    show_lightspeed()
"""

__version__ = "2.1.0"


def show_lightspeed(editor=None):
    from .lightspeed_startup import show_lightspeed as _show
    return _show(editor=editor)
