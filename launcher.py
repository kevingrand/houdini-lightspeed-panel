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

# -- Ensure the package is on sys.path --------------------------------------
try:
    _repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python")
except NameError:
    _repo = r"e:\DEV LOCAL\Houdini Lightspeed Panel\python"

if _repo not in sys.path:
    sys.path.insert(0, _repo)

# -- Clean up stale hooks from old hotkey approach --------------------------
try:
    import nodegraphhooks
    if hasattr(nodegraphhooks, 'createEventHandler'):
        fn = nodegraphhooks.createEventHandler
        if hasattr(fn, '_is_lightspeed_hook') or \
           (hasattr(fn, '__module__') and fn.__module__ and 'lightspeed' in fn.__module__):
            del nodegraphhooks.createEventHandler
except Exception:
    pass

# -- Launch ------------------------------------------------------------------
import importlib
import lightspeed.lightspeed_startup as _ls
importlib.reload(_ls)
_ls.show_lightspeed()
