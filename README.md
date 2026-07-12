# Lightspeed Panel

A fast, keyboard-first node search & creation popup for **Houdini 21**
(works back to any PySide6/PySide2 Houdini). Think of it as a smarter TAB
menu: fuzzy search, cross-DCC vocabulary, favorites, presets, wire
insertion, quick actions, and suggestions that **learn from how you
actually work**.

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
- **Cross-DCC aliases** — search in Cinema 4D / **After Effects** / Blender /
  Maya / 3ds Max / Nuke vocabulary: `cloner` → *Copy to Points*, `wiggle` →
  *Attribute Noise*, `turbosmooth` → *Subdivide*, `echo` → *Trail*. An exact
  alias term ranks **first** (it's your word for the node), matching is
  case-insensitive and typo-tolerant (`clner` still finds it), and hits are
  labeled with `≈ term`. When the [MOPs](https://www.motionoperators.com/)
  toolkit is installed, C4D terms also resolve to MOPs tools (`cloner` →
  *MOPs Instancer*, `random effector` → *MOPs Randomize*).
- **Wire insertion** — select a wire, open the panel, create: the node is
  **spliced into that connection** (upstream → new → downstream) at the
  wire's midpoint, as a single undo. The header shows
  `insert: a → b` so you always know the mode.
- **Presets** — gallery-backed parameter presets ("recipes") appear as
  creatable rows marked `◆ preset`, searched by their name too. The
  **★ PRESET** quick action saves the selected node's parameters (children
  too, for subnets — capture a whole scatter rig) into
  `$HOUDINI_USER_PREF_DIR/lightspeed.gal`. Presets saved via Houdini's
  Gallery Manager show up as well.
- **Inline naming** — `null OUT_TEXT` creates a null named *OUT_TEXT*. A
  trailing token containing an underscore is treated as the node name
  (`copy points` and `convert VDB` stay plain fuzzy queries).
- **Suggestions that learn** — every node you create through the panel
  records "(this node) usually comes after (that node)" with a 30-day decay.
  Learned patterns outrank the built-in curated maps, which cover SOPs,
  Copernicus (including H21's Flow solver / Scatter Shapes / Reaction
  Diffusion era nodes), LOPs, DOPs, OBJ, TOPs and ROPs out of the box.
- **Cross-context hints** — searching for a node that lives elsewhere
  (e.g. `flow solver` while in SOPs) shows *"Flow Solver — in Copernicus"*
  instead of a dead-end "no matches".
- **Keyboard-first** — type to search, `↑/↓`/`Tab` to choose (wraps around),
  `Enter` to create, **`Ctrl+Enter` or middle-click to create and keep the
  panel open** (chain nodes rapidly — each new node becomes the next wiring
  anchor), **`Alt+Enter` to create loose** (no auto-wiring, display flag
  untouched), **`Ctrl+1…9` to create a numbered result instantly** (the
  first nine rows show their number), `Ctrl+Home/End` to jump, `Ctrl+F` to
  toggle favorite, `F1` for node help, `Ctrl+/` for the shortcut cheat
  sheet, `Esc` clears the query first, then dismisses.
- **Open with TAB (opt-in)** — flip *"Open Lightspeed with TAB"* in the ⚙
  menu and pressing TAB in any network editor opens Lightspeed instead of
  the native menu (via the documented `nodegraphhooks` mechanism; the hook
  ships in `python/nodegraphhooks.py` and loads when the shelf tool runs).
- **Dockable panel (optional)** — `python_panels/lightspeed.pypanel` embeds
  the same UI as a persistent pane tab: Esc clears instead of closing,
  creations keep the pane open, and the context re-anchors to whatever
  network you were last in.
- **Favorites** — per-context chips at the top; click to create, drag to
  reorder, right-click to remove. Stored in the same JSON file as v1, so
  existing favorites carry over.
- **Quick actions** — MERGE / NULL OUT / LAYOUT / ★ PRESET / DELETE for the
  current selection, shown only where they apply.
- **Stable & honest** — every operation is a single undo group; failures
  print a traceback and show up in the panel and the status bar instead of
  being silently swallowed.
- Resizable (drag the grip, size is remembered), auto-positions at your
  cursor and stays on-screen, index refresh button (`⟳`) after installing
  HDAs.

## Install

**Recommended — Houdini package (auto-loads everything).** Clone/copy this
folder anywhere, then save this as
`$HOUDINI_USER_PREF_DIR/packages/lightspeed.json` (e.g.
`~/houdini21.0/packages/`), adjusting the path:

```json
{
    "env": [
        { "LIGHTSPEED": "E:/DEV LOCAL/Houdini Lightspeed Panel" },
        { "HOUDINI_PATH": { "value": "$LIGHTSPEED/houdini", "method": "append" } },
        { "HOUDINI_PYTHONPATH": { "value": "$LIGHTSPEED/python", "method": "append" } },
        { "HOUDINI_PYTHON_PANEL_PATH": { "value": "$LIGHTSPEED/python_panels", "method": "append" } }
    ]
}
```

Restart Houdini. The `lightspeed` package and the TAB hook are importable
from startup (via `houdini/python3.11libs/pythonrc.py`), and the
*Lightspeed* pane tab appears under **pane-tab menu → Misc**. To open the
popup, make a shelf tool (step 2 below) or enable the TAB hook from the ⚙
menu.

**Shelf tool / hotkey (the popup).**

1. In Houdini: right-click the shelf → **New Tool…**, paste the contents of
   [launcher.py](launcher.py) into the *Script* tab (it also hot-reloads
   the package after you pull updates, and works without the package
   install by adding `python/` to `sys.path` itself).
2. Optionally bind the tool to a hotkey (Edit → Hotkeys, e.g. `Shift+C`)
   and press it with the mouse over a Network Editor — or just enable
   *"Open Lightspeed with TAB"* in the panel's ⚙ menu.
3. Without the package install, the dockable pane needs a manual step:
   **Windows → Python Panel Editor → File → Load File…** and pick
   `python_panels/lightspeed.pypanel`, then add a *Lightspeed* pane tab via
   the pane-tab menu.

> The TAB hook is loaded when the shelf tool runs (once per session) and
> does nothing unless the ⚙ toggle is on. `Shift+Tab`-opened menus and
> everything else in the network editor are untouched. If your studio
> ships its own `nodegraphhooks.py` and it loaded first, the launcher
> chains to it: Lightspeed's handler runs first, and events it doesn't
> claim fall through to the studio hook unchanged.

## How context is detected

The panel looks at the network editor **under your mouse cursor** first,
then the editor showing your selection, then any visible network editor.
Whatever network that editor is diving into determines the node category —
so the same hotkey gives you Copernicus nodes in a COP net, DOP nodes in a
dopnet, USD/LOP nodes in Solaris, etc. When opened via the TAB hook, the
editor that received the keypress wins outright.

## Data files (all in `$HOUDINI_USER_PREF_DIR`)

| File | Contents |
|---|---|
| `custom_tab_favorites.json` | favorites per context (same file as v1) |
| `lightspeed_usage.json` | learned creation bigrams + frequency (decayed) |
| `lightspeed_settings.json` | panel size, TAB-hook toggle |
| `lightspeed.gal` | captured presets (standard Houdini gallery file) |

Delete any of them to reset — or use the ⚙ menu's *Forget Learned
Suggestions* (per context or everything) without touching files.
Nothing ever leaves your machine.

## Tests

Headless test suite runs against the real `hou` module:

```
hython tests/test_lightspeed_hython.py
```

~80 checks: index coverage per context, version dedup, fuzzy matcher, alias
tiers/typo-tolerance/case-insensitivity, suggestion learning/persistence,
favorites round-trip, preset capture/apply, wire-splice endpoint
resolution, the TAB hook contract, and real node creation/wiring in a
throwaway `/obj` network.

The pure-python parts (fuzzy matcher + alias system) also run without
Houdini:

```
python3 tests/test_pure_python.py
```

## Package layout

```
python/lightspeed/
  node_index.py   session index of all creatable types, version dedup
  fuzzy.py        pure-python fuzzy matcher + ranker (no hou import)
  aliases.py      cross-DCC search vocabulary (C4D/AE/Blender/Maya/Max/Nuke)
  suggestions.py  learned bigrams + curated seeds + frecency
  presets.py      gallery-backed parameter presets (hou.galleries)
  favorites.py    per-context favorites
  panel.py        the Qt panel (popup + embedded modes)
  store.py        atomic JSON persistence
  qt.py           PySide6-first Qt shim
  lightspeed_startup.py  show_lightspeed() / create_embedded_panel()
python/nodegraphhooks.py   opt-in TAB interception hook
python_panels/lightspeed.pypanel   dockable pane definition
```

`gallery_ui.py`, `smart_suggestions.py`, `search_mappings`→`aliases`, and
`qt_utils.py` remain as thin compatibility shims for any external scripts.
