"""
Lightspeed bootstrap — runs automatically at Houdini startup.

The lightspeed.json package puts <repo>/houdini on HOUDINI_PATH; Houdini
executes any python3.11libs/pythonrc.py it finds there. All we do is make
the actual code importable (repo/python holds the lightspeed package and
the nodegraphhooks TAB hook).

Houdini execs this file without __file__ defined, so the repo root comes
from the $LIGHTSPEED variable the package sets.
"""

import os
import sys


def _lightspeed_repo_python():
    root = os.environ.get("LIGHTSPEED", "")
    if root:
        return os.path.join(root, "python")
    # Fallback: find our houdini/ dir on HOUDINI_PATH and step out of it
    for entry in os.environ.get("HOUDINI_PATH", "").split(";"):
        candidate = os.path.join(entry, "python3.11libs", "pythonrc.py")
        if entry and entry != "&" and os.path.exists(candidate):
            sibling = os.path.join(os.path.dirname(entry), "python")
            if os.path.isdir(os.path.join(sibling, "lightspeed")):
                return sibling
    return ""


_repo_python = _lightspeed_repo_python()
if _repo_python and os.path.isdir(_repo_python) and _repo_python not in sys.path:
    sys.path.insert(0, _repo_python)
