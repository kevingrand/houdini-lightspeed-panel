# Lightspeed Panel

A fast, keyboard-first node search & creation popup for **Houdini 21**
(works back to any PySide6/PySide2 Houdini). Think of it as a smarter TAB
menu: fuzzy search, cross-DCC vocabulary, favorites, quick actions, and
suggestions that **learn from how you actually work**.

![context: works in SOPs, DOPs, Copernicus COPs, LOPs, TOPs, VOPs, OBJ, ROPs, CHOPs]

## Features

- **Every context indexed** — SOPs, DOPs, **Copernicus (COPs)**, LOPs, TOPs,
  VOPs, OBJ, ROPs, CHOPs, legacy COP2… all ~3700 creatable node types,
  built in ~45 ms per session. Versioned tools (`curve` vs `curve::2.0`)
  are deduped to the preferred version exactly like the TAB menu;
  `labs::`/`kinefx::`/`apex::` tools are searchable by their base name.
- **Fuzzy search** — prefix, word-boundary, acronym (`ctp` → *Copy to
  Points*), and subsequence (`plybvl` → *PolyBevel*) matching, plus
  multi-word queries matched against both name and label.
- **Cross-DCC aliases** — search in Cinema 4D / Blender / Maya / 3ds Max /
  Nuke vocabulary: `cloner` → *copytopoints*, `keyer` → *chromakey*,
  `turbosmooth` → *subdivide*. Alias hits are labeled with `≈ term`.
- **Suggestions that learn** — every node you create through the panel
  records "(this node) usually comes after (that node)" with a 30-day decay.
  Learned patterns outrank the built-in curated maps, which now cover SOPs,
  Copernicus, LOPs, DOPs, OBJ, TOPs and ROPs out of the box.
- **Keyboard-first** — type to search, `↑/↓` to choose, `Enter` to create,
  **`Ctrl+Enter` to create and keep the panel open** (chain nodes rapidly —
  each new node becomes the next wiring anchor), `Ctrl+F` to toggle
  favorite, `Esc` to dismiss.
- **Favorites** — per-context chips at the top; click to create, drag to
  reorder, right-click to remove. Stored in the same JSON file as v1, so
  existing favorites carry over.
- **Quick actions** — MERGE / NULL OUT / LAYOUT / DELETE for the current
  selection, shown only where they apply.
- **Stable & honest** — every operation is a single undo group; failures
  print a traceback and show up in the panel and the status bar instead of
  being silently swallowed.
- Resizable (drag the grip, size is remembered), auto-positions at your
  cursor and stays on-screen, index refresh button (`⟳`) after installing
  HDAs.

## Install

1. Clone/copy this folder anywhere.
2. In Houdini: right-click the shelf → **New Tool…**, paste the contents of
   [launcher.py](launcher.py) into the *Script* tab (it adds `python/` to
   `sys.path`, hot-reloads the package, and opens the panel).
3. Optionally bind the tool to a hotkey (Edit → Hotkeys, e.g. `Shift+C`)
   and press it with the mouse over a Network Editor.

## How context is detected

The panel looks at the network editor **under your mouse cursor** first,
then the editor showing your selection, then any visible network editor.
Whatever network that editor is diving into determines the node category —
so the same hotkey gives you Copernicus nodes in a COP net, DOP nodes in a
dopnet, USD/LOP nodes in Solaris, etc.

## Data files (all in `$HOUDINI_USER_PREF_DIR`)

| File | Contents |
|---|---|
| `custom_tab_favorites.json` | favorites per context (same file as v1) |
| `lightspeed_usage.json` | learned creation bigrams + frequency (decayed) |
| `lightspeed_settings.json` | panel size |

Delete any of them to reset. Nothing ever leaves your machine.

## Tests

Headless test suite runs against the real `hou` module:

```
hython tests/test_lightspeed_hython.py
```

59 checks: index coverage per context, version dedup, fuzzy matcher, alias
resolution, suggestion learning/persistence, favorites round-trip, and real
node creation/wiring in a throwaway `/obj` network.

## Package layout

```
python/lightspeed/
  node_index.py   session index of all creatable types, version dedup
  fuzzy.py        pure-python fuzzy matcher + ranker (no hou import)
  aliases.py      cross-DCC search vocabulary
  suggestions.py  learned bigrams + curated seeds + frecency
  favorites.py    per-context favorites
  panel.py        the Qt panel
  store.py        atomic JSON persistence
  qt.py           PySide6-first Qt shim
  lightspeed_startup.py  show_lightspeed() entry point
```

`gallery_ui.py`, `smart_suggestions.py`, `search_mappings`→`aliases`, and
`qt_utils.py` remain as thin compatibility shims for any external scripts.
