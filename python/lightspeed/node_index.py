"""
node_index.py
-------------
Session-wide index of every creatable node type in every network category.

Facts (measured on Houdini 21.0.596): the full visible index is ~4200 types
and builds in ~30 ms, so we build it lazily once per session and keep it in
memory. `refresh()` rebuilds (e.g. after installing an HDA/package).

Handles the things the old panel got wrong:
  * indexes ALL categories (Sop, Dop, Cop/Copernicus, Cop2, Lop, Top, Vop,
    Object, Driver, Chop, Shop, *Net managers) — not just the current one
  * version dedup: 'curve' vs 'curve::2.0' collapse to the preferred
    (highest) version, matching TAB-menu behaviour
  * namespaced tools (labs::, kinefx::, apex::) are kept and searchable by
    their base name
  * HDA-internal types containing '/' are skipped
"""

import hou

from . import fuzzy

# Categories that hold no user-creatable network nodes.
EXCLUDED_CATEGORIES = {"Data", "Director", "Manager"}


class NodeEntry(object):
    """One creatable node type. Plain attributes for speed. The lowercase /
    tokenized fields are precomputed once at index build so the fuzzy
    matcher never re-derives them on the per-keystroke path."""

    __slots__ = ("name", "label", "base", "category", "icon",
                 "min_inputs", "max_inputs", "max_outputs",
                 "name_l", "label_l", "base_l", "words", "acr")

    def __init__(self, name, label, base, category, icon,
                 min_inputs, max_inputs, max_outputs=1):
        self.name = name            # full type name used for createNode()
        self.label = label          # human label shown in the TAB menu
        self.base = base            # namespace/version-stripped core name
        self.category = category    # category name, e.g. 'Sop'
        self.icon = icon            # icon name for hou.qt
        self.min_inputs = min_inputs
        self.max_inputs = max_inputs
        self.max_outputs = max_outputs
        # Search-time fields (see fuzzy.rank)
        self.name_l = name.lower()
        self.label_l = label.lower()
        self.base_l = fuzzy.base_name(self.name_l)
        self.words = fuzzy.entry_words(self.name_l, self.label_l)
        self.acr = fuzzy.acronym(self.label_l)


def _version_key(version_string):
    """'2.0' -> (2, 0); '' -> (); tolerant of odd version strings."""
    parts = []
    for chunk in version_string.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _build_category(category):
    """Build deduped NodeEntry list for one hou.NodeTypeCategory."""
    # Group versions of the same tool: key = (scope, namespace, core)
    groups = {}
    for type_name, node_type in category.nodeTypes().items():
        try:
            if node_type.hidden() or node_type.deprecated():
                continue
            if "/" in type_name:
                continue  # HDA-internal (e.g. 'Sop/rbdmaterialfracture::...')
            scope, namespace, core, version = node_type.nameComponents()
        except hou.Error:
            continue
        key = (scope, namespace, core)
        current = groups.get(key)
        if current is None or _version_key(version) > current[0]:
            groups[key] = (_version_key(version), node_type)

    cat_name = category.name()
    entries = []
    for (_scope, _namespace, core), (_ver, node_type) in groups.items():
        try:
            entries.append(NodeEntry(
                name=node_type.name(),
                label=node_type.description() or core,
                base=core,
                category=cat_name,
                icon=node_type.icon(),
                min_inputs=node_type.minNumInputs(),
                max_inputs=node_type.maxNumInputs(),
                max_outputs=node_type.maxNumOutputs(),
            ))
        except hou.Error:
            continue
    entries.sort(key=lambda e: e.name)
    return entries


class NodeIndex(object):
    """Lazily-built index of all categories. Use NodeIndex.get()."""

    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._by_category = {}     # cat name -> [NodeEntry]
        self._lookup = {}          # cat name -> {full name -> NodeEntry}
        self._base_lookup = {}     # cat name -> {base name -> NodeEntry}
        self.build_seconds = 0.0
        self.refresh()

    def refresh(self):
        import time
        t0 = time.perf_counter()
        self._by_category.clear()
        self._lookup.clear()
        self._base_lookup.clear()
        for cat_name, category in hou.nodeTypeCategories().items():
            if cat_name in EXCLUDED_CATEGORIES:
                continue
            entries = _build_category(category)
            if not entries:
                continue
            self._by_category[cat_name] = entries
            self._lookup[cat_name] = {e.name: e for e in entries}
            # base lookup: prefer un-namespaced tools when bases collide
            # (e.g. plain 'null' beats 'somehda::null')
            base_map = {}
            for e in entries:
                existing = base_map.get(e.base)
                if existing is None or ("::" in existing.name and "::" not in e.name):
                    base_map[e.base] = e
            self._base_lookup[cat_name] = base_map
        self.build_seconds = time.perf_counter() - t0

    # -- queries --------------------------------------------------------

    def categories(self):
        return sorted(self._by_category)

    def entries(self, category_name):
        return self._by_category.get(category_name, [])

    def entry(self, category_name, type_name):
        """Look up by full name, falling back to base name."""
        entry = self._lookup.get(category_name, {}).get(type_name)
        if entry is None:
            entry = self._base_lookup.get(category_name, {}).get(
                fuzzy.base_name(type_name))
        return entry

    def has(self, category_name, type_name):
        return self.entry(category_name, type_name) is not None

    def base_entries(self, category_name):
        """{base name -> preferred NodeEntry} for a category."""
        return self._base_lookup.get(category_name, {})

    def total_count(self):
        return sum(len(v) for v in self._by_category.values())


# ---------------------------------------------------------------------------
# Context resolution
# ---------------------------------------------------------------------------

def find_network_editor(selection=None):
    """
    Locate the network editor the user is working in.
    Priority: pane under the mouse cursor > editor showing the selection's
    parent network > any visible network editor.
    """
    try:
        under = hou.ui.paneTabUnderCursor()
    except (AttributeError, hou.Error):
        under = None
    if isinstance(under, hou.NetworkEditor):
        return under

    try:
        editors = [p for p in hou.ui.paneTabs()
                   if isinstance(p, hou.NetworkEditor) and p.isCurrentTab()]
    except (AttributeError, hou.Error):
        # hou.ui doesn't exist headless (hython) — no editors to find
        return None
    if selection:
        parent_path = selection[0].parent().path()
        for editor in editors:
            if editor.pwd().path() == parent_path:
                return editor
    return editors[0] if editors else None


def category_for_editor(editor):
    """Category of nodes creatable inside the editor's current network."""
    if editor is None:
        return None
    try:
        return editor.pwd().childTypeCategory()
    except hou.Error:
        return None
