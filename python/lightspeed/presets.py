"""
presets.py
----------
Parameter presets ("recipes") backed by Houdini galleries.

A gallery entry stores a node type plus parameter values, channels, spare
parms — and, for subnets, the children too — so a preset can be anything
from "attribnoise, gentle drift" to a whole captured scatter rig.

Galleries are the HOM-supported preset mechanism (hou.galleries): entries
are listable per node type *without* creating a node first, unlike native
`oppreset` presets, and apply cleanly via GalleryEntry.applyToNode().

Lightspeed captures new presets into its own gallery file in
$HOUDINI_USER_PREF_DIR (lightspeed.gal), but *lists* entries from every
installed gallery, so presets saved through Houdini's Gallery Manager show
up here too.
"""

import os
import re
import traceback

import hou

from . import store

GALLERY_FILE = "lightspeed.gal"

_installed = False

# Per-category cache: the panel is recreated on every hotkey press, but the
# gallery only changes through capture()/remove() (or externally — the
# panel's ⟳ button passes force=True to pick that up).
_cache = {}


def invalidate_cache():
    _cache.clear()


class PresetItem(object):
    """A creatable preset: node type name + the gallery entry to apply."""

    __slots__ = ("entry", "name", "label", "type_name")

    def __init__(self, entry, name, label, type_name):
        self.entry = entry          # hou.GalleryEntry
        self.name = name            # entry name (unique-ish id)
        self.label = label          # human label shown in the panel
        self.type_name = type_name  # node type name to create


def _gallery_path():
    return store.path_for(GALLERY_FILE)


def _ensure_installed():
    """Make sure the Lightspeed gallery file is loaded in this session."""
    global _installed
    if _installed:
        return
    path = _gallery_path()
    if not os.path.exists(path):
        return
    try:
        hou.galleries.installGallery(path)
        _installed = True
    except (AttributeError, hou.Error):
        pass


def entries_for_category(category, force=False):
    """
    All gallery presets whose node type is creatable in `category`
    (a hou.NodeTypeCategory). Returns a list of PresetItem.
    Cached per category; pass force=True to re-read the gallery database.
    """
    if category is None:
        return []
    cache_key = category.name()
    if not force and cache_key in _cache:
        return _cache[cache_key]
    _ensure_installed()
    items = []
    try:
        entries = hou.galleries.galleryEntries(category=category)
    except (AttributeError, TypeError, hou.Error):
        return []
    for entry in entries:
        try:
            type_name = entry.nodeTypeName()
            if not type_name:
                continue
            # nodeTypeName may be table-qualified ("Sop/box") — strip it,
            # the panel creates inside a known category anyway.
            if "/" in type_name:
                type_name = type_name.split("/", 1)[1]
            label = entry.label() or entry.name()
            items.append(PresetItem(entry, entry.name(), label, type_name))
        except hou.Error:
            continue
    items.sort(key=lambda it: it.label.lower())
    _cache[cache_key] = items
    return items


def apply_to_node(item, node):
    """Apply a PresetItem's gallery entry to a freshly created node.
    Returns True on success; failures are printed, never swallowed."""
    try:
        item.entry.applyToNode(node)
        return True
    except (AttributeError, hou.Error):
        traceback.print_exc()
        return False


def capture(name, node, description=""):
    """
    Save `node` (parms, channels, spare parms; children when it's a subnet)
    as a preset in the Lightspeed gallery. `name` becomes the label; the
    internal entry name is sanitized (gallery entry names are identifiers).
    Returns the new hou.GalleryEntry, or raises hou.Error.
    """
    global _installed
    entry_name = re.sub(r"[^\w]+", "_", name).strip("_") or "preset"
    entry = hou.galleries.createGalleryEntry(_gallery_path(), entry_name, node)
    _installed = True
    invalidate_cache()
    try:
        entry.setLabel(name)
        if description:
            entry.setDescription(description)
    except (AttributeError, hou.Error):
        pass
    return entry


def remove(item):
    """Delete a preset from whatever gallery it lives in. A real deletion
    failure prints its traceback — it is never mistaken for a missing API."""
    for attempt in (
        lambda: hou.galleries.removeGalleryEntry(item.entry),
        lambda: item.entry.remove(),
    ):
        try:
            attempt()
            invalidate_cache()
            return True
        except (AttributeError, TypeError):
            continue          # this spelling doesn't exist in this build
        except hou.Error:
            traceback.print_exc()   # the API exists and the delete failed
            return False
    print("Lightspeed: no gallery-entry deletion API in this Houdini build "
          "— use Windows > Gallery Manager")
    return False
