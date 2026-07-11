"""
store.py
--------
Tiny JSON persistence helper for Lightspeed user data
(favorites, usage statistics, panel settings).

Files live in $HOUDINI_USER_PREF_DIR so they follow the user across projects.
Writes are atomic (temp file + replace) so a crash mid-save can never corrupt
existing data.
"""

import json
import os
import tempfile


def _pref_dir():
    import hou
    return hou.homeHoudiniDirectory()


def path_for(filename):
    return os.path.join(_pref_dir(), filename)


def load_json(filename, default=None):
    """Load JSON from the Houdini pref dir. Returns `default` on any failure."""
    path = path_for(filename)
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError) as e:
        print(f"Lightspeed: could not read {path}: {e}")
        return default if default is not None else {}


def save_json(filename, data):
    """Atomically write JSON to the Houdini pref dir."""
    path = path_for(filename)
    try:
        fd, tmp = tempfile.mkstemp(
            prefix=".lightspeed_", suffix=".tmp", dir=os.path.dirname(path)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
    except OSError as e:
        print(f"Lightspeed: could not save {path}: {e}")
