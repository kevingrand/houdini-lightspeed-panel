"""
launcher.py  —  Lightspeed Panel
---------------------------------
Paste this into a Houdini Shelf Tool, the Python Source Editor,
or bind it to a hotkey via Edit > Hotkeys.

SHELF TOOL SETUP (one-time)
----------------------------
1.  Right-click the shelf bar  >  New Shelf...  >  name it "Lightspeed"
2.  Right-click the new shelf  >  New Tool...
3.  Set Label to "Lightspeed Panel"
4.  Paste the code below (lines after this docstring) into the Script tab
5.  Click Accept
6.  Dock the shelf tab near your Network Editor

HOTKEY SETUP (optional)
------------------------
1.  Edit > Hotkeys
2.  Search for "Lightspeed Panel" (your shelf tool name)
3.  Assign Shift+C (or any key you prefer)
"""

import sys
import os
import importlib

# -- Ensure the package is on sys.path --------------------------------------
try:
    _repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python")
except NameError:
    _repo = r"e:\DEV LOCAL\Houdini Lightspeed Panel\python"

# Front of sys.path, even if it was already present further back — the
# lightspeed package and the nodegraphhooks shadow both rely on winning
# import resolution.
if _repo in sys.path:
    sys.path.remove(_repo)
sys.path.insert(0, _repo)

# -- Node-graph TAB hook -----------------------------------------------------
# The repo ships python/nodegraphhooks.py (opt-in TAB interception, toggled
# from the panel's gear menu). Two cases:
#   * `import nodegraphhooks` resolves to our file (nothing else was
#     imported first): just reload it so edits take effect.
#   * some other nodegraphhooks (studio / $HHP) was imported first:
#     Houdini's nodegraph code keeps a live reference to that module
#     OBJECT, so evicting it from sys.modules would do nothing. Instead
#     mutate it in place — our handler runs first and chains to the
#     original, so existing studio hooks keep working.
try:
    import nodegraphhooks
    _hook_path = os.path.join(_repo, "nodegraphhooks.py")
    _current = os.path.abspath(getattr(nodegraphhooks, "__file__", "") or "")
    if _current == os.path.abspath(_hook_path):
        importlib.reload(nodegraphhooks)
    else:
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "lightspeed_tab_hook", _hook_path)
        _ls_hooks = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_ls_hooks)
        # Stash the foreign handler once (re-running the shelf tool must
        # not chain to our own wrapper). A stale pre-overhaul lightspeed
        # hook is replaced rather than chained to.
        if not hasattr(nodegraphhooks, "_lightspeed_original_handler"):
            _orig = getattr(nodegraphhooks, "createEventHandler", None)
            if _orig is not None and (
                    hasattr(_orig, "_is_lightspeed_hook")
                    or "lightspeed" in (getattr(_orig, "__module__", "") or "")):
                _orig = None
            nodegraphhooks._lightspeed_original_handler = _orig

        def _lightspeed_chained_handler(uievent, pending_actions,
                                        _ls=_ls_hooks,
                                        _orig=nodegraphhooks._lightspeed_original_handler):
            handler, handled = _ls.createEventHandler(uievent, pending_actions)
            if handled or handler is not None or _orig is None:
                return handler, handled
            return _orig(uievent, pending_actions)

        _lightspeed_chained_handler._is_lightspeed_hook = True
        nodegraphhooks.createEventHandler = _lightspeed_chained_handler
except Exception:
    pass

# -- Reload the whole package (dependency order) so edits take effect -------
import lightspeed
import lightspeed.qt
import lightspeed.store
import lightspeed.fuzzy
import lightspeed.aliases
import lightspeed.node_index
import lightspeed.suggestions
import lightspeed.favorites
import lightspeed.presets
import lightspeed.panel
import lightspeed.lightspeed_startup

for _mod in (lightspeed.qt, lightspeed.store, lightspeed.fuzzy,
             lightspeed.aliases, lightspeed.node_index, lightspeed.suggestions,
             lightspeed.favorites, lightspeed.presets, lightspeed.panel,
             lightspeed.lightspeed_startup, lightspeed):
    importlib.reload(_mod)

# Reloading node_index resets the class attribute, so the index rebuilds
# lazily on next open — that's intended (picks up newly installed HDAs).

# -- Launch ------------------------------------------------------------------
lightspeed.lightspeed_startup.show_lightspeed()
