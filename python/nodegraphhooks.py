"""
nodegraphhooks.py — Lightspeed TAB hook (opt-in)
------------------------------------------------
Houdini's network editor sends every UI event to
`nodegraphhooks.createEventHandler()` before handling it itself (see
"Extending the network editor" in the HOM docs). This module lives in the
Lightspeed repo's `python/` directory; the launcher shelf tool makes sure
it is the active hook (chaining to any pre-existing hook module).

The hook is OFF by default. Toggle it from the panel's ⚙ menu
("Open Lightspeed with TAB"); the flag lives in lightspeed_settings.json.
While enabled, pressing TAB in any network editor opens Lightspeed instead
of the native TAB menu. Shift+Tab always opens the native menu, so nothing
is ever lost.

This function runs for EVERY network-editor UI event, including the mouse
move stream — everything before the Tab-key check must stay allocation-free
and cheap.
"""

import traceback

# Depending on build, the tab-menu key can arrive as a plain 'keyhit' or as
# the dedicated 'menukeyhit' event type — accept both.
_TAB_EVENT_TYPES = ("keyhit", "menukeyhit")

_KeyboardEvent = None   # resolved lazily, once


def _keyboard_event_class():
    global _KeyboardEvent
    if _KeyboardEvent is None:
        from canvaseventtypes import KeyboardEvent
        _KeyboardEvent = KeyboardEvent
    return _KeyboardEvent


def _tab_hook_enabled():
    """Read the toggle. Only called on an actual Tab press — at most once
    per panel-open — so reading the settings file fresh keeps the ⚙ toggle
    instant (no stale-cache window)."""
    try:
        from lightspeed import store
        return bool(store.load_json(store.SETTINGS_FILE, {}).get("tab_hook"))
    except Exception:
        return False


def createEventHandler(uievent, pending_actions):
    """Intercept TAB in network editors and open Lightspeed instead.

    Returns (handler, handled): (None, True) swallows the event, and
    (None, False) lets Houdini process it normally.
    """
    # Cheap rejects first: this is the mouse-move hot path.
    if getattr(uievent, "eventtype", None) not in _TAB_EVENT_TYPES:
        return None, False
    if getattr(uievent, "key", None) != "Tab":
        return None, False

    try:
        if not isinstance(uievent, _keyboard_event_class()):
            return None, False
        if not _tab_hook_enabled():
            return None, False
        from lightspeed.lightspeed_startup import show_lightspeed
        show_lightspeed(editor=getattr(uievent, "editor", None))
        return None, True
    except Exception:
        # Never break the network editor: log and fall through to Houdini.
        traceback.print_exc()
    return None, False
