# Lightspeed Panel Overhaul — Design

Date: 2026-07-11
Target: Houdini 21.0 (verified against 21.0.596, Python 3.11.7, PySide6 6.5.3)

## 1. Evaluation of the existing plugin

### Indexing (the "never indexed everything" problem)
- `_init_node_data()` indexed only **one** category — resolved from the first
  selected node or `pwd().childTypeCategory()` — and silently returned an empty
  list when resolution failed (bare `except: pass`), leaving the panel blank in
  COPs/DOPs/LOPs edge cases.
- No handling of **versioned node types**. H21's SOP category has 1628 types,
  676 of them namespaced (`curve` vs `curve::2.0`, `labs::…`, `apex::…`).
  Both versions of a node appeared as duplicate rows; the TAB menu shows only
  the preferred one.
- Copernicus (`Cop`, 262 types — the modern H20.5+/H21 context) was never
  special-cased or tested; the legacy `Cop2` compositing category still exists
  alongside it and the two were indistinguishable in the UI.
- Category resolution defaulted to `"Object"` on failure — wrong context,
  wrong nodes.

### Suggestions
- A static, hand-written map of ~40 SOP node types only. Nothing for COPs,
  DOPs, LOPs, TOPs, OBJ. No learning from what the user actually does, so the
  "recommend the next node" promise could never generalize.

### Search
- Substring-only matching (no fuzzy, no acronym, no multi-token).
- Alias table (C4D/Blender/Maya/Max) is good content but only consulted on raw
  substring overlap of the alias key.

### UI / usability
- No keyboard navigation: focus stays in the search field; ↑/↓ do nothing;
  Enter always creates the *first* result.
- Favorites labels truncated to 4 characters ("sphe..").
- Fixed 350×550 size, not resizable, size not persisted.
- Single click creates a node — accidental creations.
- Blanket `except: pass` around node creation and quick actions — failures are
  invisible (the "stability" complaint: it doesn't crash, it silently does
  nothing).
- No undo grouping; a create+wire+flags operation is several undo steps.
- Icons fetched via `hou.qt.createIcon` per item per keystroke with no cache.
- PySide2 imported *first* even though H21 ships only PySide6.

### Measured facts (hython 21.0.596)
- Full visible index across ALL categories: **4211 types, builds in 29 ms** —
  no disk cache needed; a per-session in-memory index is enough.
- `hou.NodeType` provides `nameComponents()`, `namespaceOrder()`, `hidden()`,
  `deprecated()`, `minNumInputs()`, `maxNumInputs()` — everything needed for
  dedup and connection-aware ranking.
- `hou.NetworkEditor.flashMessage()` exists → non-blocking creation feedback.
- `hou.Node.moveToGoodPosition()` exists → placement fallback.

## 2. Architecture

```
python/lightspeed/
  __init__.py            version + public entry
  qt.py                  PySide6-first Qt shim (PySide2 fallback)
  store.py               tiny JSON persistence helper (atomic write)
  node_index.py          NodeIndex: all categories, version dedup, per-session cache
  fuzzy.py               pure-python fuzzy matcher (no hou import; unit-testable)
  aliases.py             cross-DCC term → houdini node names (extended)
  suggestions.py         SuggestionEngine: learned bigrams + curated seeds + frecency
  favorites.py           FavoritesManager (same JSON file, hardened)
  panel.py               LightspeedPanel UI (delegate rendering, keyboard-first)
  lightspeed_startup.py  show_lightspeed() singleton (name kept for shelf compat)
launcher.py              deep-reloads the whole package, then shows the panel
```

### node_index.py
- `NodeIndex.get()` module singleton; builds once per session (~30 ms), with
  `refresh()`. Entries per category, each: `name, label, base (core name from
  nameComponents), category, icon, min_inputs, max_inputs, haystack tokens`.
- Skips: `hidden()`, `deprecated()`, names containing `/` (HDA-internal),
  empty/internal categories (`Data`, `Director`, `Manager`).
- **Version dedup**: group by `(scope, namespace, core)`; keep only the highest
  version (numeric-aware compare) — matches TAB menu behaviour.
- Category resolution helper `category_for_editor(editor, selection)` with the
  full fallback chain and no silent default to Object.

### fuzzy.py (pure python — unit-tested in hython AND plain python)
Scoring tiers (lower = better): exact → prefix → word-boundary prefix →
acronym (first letters of label words / underscore tokens) → subsequence with
gap penalty → substring in label. Multi-word queries: every token must match
name or label. Returns `(score, matched_positions)` for highlight rendering.

### suggestions.py
Three merged sources, ranked: (1) **learned bigrams** — every creation records
`(category, upstream type) → created type` with counts + exponential decay in
`lightspeed_usage.json`; (2) **curated seeds** — expanded static maps now
covering Sop, Cop (Copernicus), Lop, Dop, Obj, Top, Driver, grounded in real
H21 node names; (3) **frecency** — most created types for the category, used
to order the empty-query view. Upstream type resolved from selection leaf
(kept from old logic, hardened).

### panel.py
- Keyboard-first: search field keeps focus; ↑/↓/PgUp/PgDn/Home/End forwarded
  to the results list; Enter creates highlighted row; Ctrl+Enter creates and
  keeps the panel open (rapid multi-create); Esc closes; Ctrl+F toggles
  favorite on highlighted row; single-click selects, **double-click creates**
  (click-to-create kept for favorites chips only).
- Custom `QStyledItemDelegate`: icon + label + dim node name + match highlight
  + badges (★ favorite, ▍suggested accent, "≈ cloner" alias origin).
- Sections when query is empty: SUGGESTED / RECENT / ALL; while typing: one
  ranked list.
- Debounced (80 ms) re-query; results capped at 60 rows; icon QIcon cache.
- Header: context badge ("Geometry — SOP"), result count, refresh-index button.
- Quick actions (Merge / Null OUT / Layout / Delete) shown only if the type
  exists in the current category; each wrapped in an undo group with visible
  error reporting.
- Resizable (size grip) with size persisted per category to settings JSON.
- Creation path: undo group, wire selected nodes to sequential inputs guarded
  by `maxNumInputs()`, placement below selection centroid else at network
  cursor else `moveToGoodPosition()`, display/render flags where supported,
  `flashMessage` confirmation, usage recorded, errors surfaced via status bar +
  message in the panel (never swallowed).

### Error handling policy
No bare `except: pass`. All user-triggered operations route through a helper
that catches `hou.Error`/`Exception`, prints a full traceback to the console,
and shows a one-line message via `hou.ui.setStatusMessage` (guarded).

## 3. Out of scope
- Replacing the native TAB menu / nodegraph hooks.
- Wire-insertion (dropping a node onto an existing connection).
- Cloud/telemetry anything. All data stays in `$HOUDINI_USER_PREF_DIR`.

## 4. Verification plan
- `py_compile` every module (system Python).
- hython headless test script: build full index (assert >4000 entries, assert
  `Cop` present, assert version dedup removed `curve` in favor of
  `curve::2.0`), fuzzy matcher cases, suggestion engine record/query round-trip,
  favorites round-trip.
- Manual: user opens panel in SOP/COP/DOP/LOP nets via shelf tool.
