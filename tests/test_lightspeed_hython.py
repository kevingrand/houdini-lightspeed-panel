"""
Headless verification of the Lightspeed Panel against the REAL hou module.
Run with hython (any Houdini 20.5+/21 install):

    "C:/Program Files/Side Effects Software/Houdini 21.0.596/bin/hython.exe" tests/test_lightspeed_hython.py

Tests everything except the visible Qt UI. User preference files are
sandboxed to a temp directory — your real favorites/usage are untouched.
"""
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

# Redirect user-pref writes away from the real prefs during tests
import hou

FAILURES = []


def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}" + (f"  -> {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(label)


# ---------------------------------------------------------------- fuzzy
from lightspeed import fuzzy

check("base_name plain", fuzzy.base_name("box") == "box")
check("base_name version", fuzzy.base_name("curve::2.0") == "curve")
check("base_name namespace", fuzzy.base_name("kinefx::rigdoctor") == "rigdoctor")
check("base_name ns+ver", fuzzy.base_name("labs::edge_damage::2.0") == "edge_damage")

s, _ = fuzzy.score("box", "box", "Box")
check("exact match scores 0", s == 0.0, s)
s_prefix, _ = fuzzy.score("po", "polyextrude", "PolyExtrude")
s_contains, _ = fuzzy.score("extrude", "polyextrude", "PolyExtrude")
check("prefix beats contains", s_prefix < s_contains, (s_prefix, s_contains))
s_ctp, _ = fuzzy.score("ctp", "copytopoints", "Copy to Points")
check("acronym ctp matches", s_ctp is not None, s_ctp)
s_none, _ = fuzzy.score("zzzzqqq", "box", "Box")
check("garbage doesn't match", s_none is None)
s_multi, _ = fuzzy.score("copy points", "copytopoints", "Copy to Points")
check("multi-token matches", s_multi is not None)
s_subseq, _ = fuzzy.score("plybvl", "polybevel", "PolyBevel")
check("subsequence plybvl->polybevel", s_subseq is not None)

# ---------------------------------------------------------------- index
from lightspeed import node_index

t0 = time.perf_counter()
idx = node_index.NodeIndex.get()
build_t = time.perf_counter() - t0
print(f"  index: {idx.total_count()} entries in {idx.build_seconds*1000:.0f} ms")
check("index has >3000 entries", idx.total_count() > 3000, idx.total_count())
check("index build under 2s", build_t < 2.0, build_t)
check("Sop indexed", len(idx.entries("Sop")) > 800, len(idx.entries("Sop")))
check("Copernicus (Cop) indexed", len(idx.entries("Cop")) > 200, len(idx.entries("Cop")))
check("Dop indexed", len(idx.entries("Dop")) > 300, len(idx.entries("Dop")))
check("Lop indexed", len(idx.entries("Lop")) > 150, len(idx.entries("Lop")))
check("Top indexed", len(idx.entries("Top")) > 100, len(idx.entries("Top")))
check("Vop indexed", len(idx.entries("Vop")) > 500, len(idx.entries("Vop")))

sop_names = {e.name for e in idx.entries("Sop")}
check("version dedup: curve::2.0 kept", "curve::2.0" in sop_names)
check("version dedup: old curve dropped", "curve" not in sop_names)
check("no HDA-internal slashes", not any("/" in n for n in sop_names))
labs = [n for n in sop_names if n.lower().startswith("labs::")]
check("labs tools indexed", len(labs) > 50, len(labs))

entry = idx.entry("Sop", "curve")
check("entry() base-name fallback", entry is not None and entry.name == "curve::2.0",
      entry.name if entry else None)
check("has() works", idx.has("Sop", "merge") and idx.has("Lop", "merge")
      and idx.has("Cop", "blur"))

# no hidden/deprecated leaked
sop_cat = hou.nodeTypeCategories()["Sop"]
leaked = [e.name for e in idx.entries("Sop")
          if sop_cat.nodeTypes().get(e.name)
          and (sop_cat.nodeTypes()[e.name].hidden()
               or sop_cat.nodeTypes()[e.name].deprecated())]
check("no hidden/deprecated leaked", not leaked, leaked[:5])

# ---------------------------------------------------------------- rank
ranked = fuzzy.rank(idx.entries("Sop"), "box")
check("rank 'box' -> box first", ranked and ranked[0]["entry"].name == "box",
      ranked[0]["entry"].name if ranked else None)

from lightspeed import aliases
hits = aliases.alias_hits_for_query("cloner")
check("alias cloner -> copytopoints", "copytopoints" in hits, hits)
ranked = fuzzy.rank(idx.entries("Sop"), "cloner", alias_hits=hits)
names = [r["entry"].base for r in ranked]
check("rank alias cloner returns copytopoints", "copytopoints" in names, names[:5])
alias_row = next(r for r in ranked if r["entry"].base == "copytopoints")
check("alias term attached", alias_row["alias"] == "cloner", alias_row["alias"])

ranked = fuzzy.rank(idx.entries("Cop"), "keyer",
                    alias_hits=aliases.alias_hits_for_query("keyer"))
check("COP alias keyer -> chromakey",
      any(r["entry"].base == "chromakey" for r in ranked),
      [r["entry"].name for r in ranked][:5])

ranked = fuzzy.rank(idx.entries("Sop"), "wrangle")
check("rank 'wrangle' includes attribwrangle",
      any(r["entry"].name == "attribwrangle" for r in ranked[:5]),
      [r["entry"].name for r in ranked[:5]])

# suggestion boost ordering
ranked = fuzzy.rank(idx.entries("Sop"), "no", suggested={"normal"})
# just ensure no crash and results exist
check("rank with suggested set works", len(ranked) > 0)

# ---------------------------------------------------------------- store/suggestions
# Point pref dir writes at a temp sandbox by monkeypatching store._pref_dir
from lightspeed import store as ls_store
SANDBOX = os.path.join(os.environ.get("TMP", "/tmp"), "lightspeed_test_prefs")
os.makedirs(SANDBOX, exist_ok=True)
ls_store._pref_dir = lambda: SANDBOX

usage_path = os.path.join(SANDBOX, "lightspeed_usage.json")
if os.path.exists(usage_path):
    os.remove(usage_path)

from lightspeed import suggestions as sug

engine = sug.SuggestionEngine()
cold = engine.suggestions("Sop", "box")
check("curated: box -> xform first", cold and cold[0] == "xform", cold[:4])
cop_cold = engine.suggestions("Cop", "fractalnoise")
check("curated COP: fractalnoise -> remap", "remap" in cop_cold[:4], cop_cold[:4])
lop_cold = engine.suggestions("Lop", "sopimport")
check("curated LOP: sopimport -> materiallibrary",
      "materiallibrary" in lop_cold[:3], lop_cold[:3])

# learning: create scatter after box 3x -> should outrank curated
for _ in range(3):
    engine.record_creation("Sop", "box", "scatter")
engine2 = sug.SuggestionEngine()  # fresh load from disk proves persistence
warm = engine2.suggestions("Sop", "box")
check("learned bigram persists + ranks first", warm and warm[0] == "scatter", warm[:4])
check("curated still follows learned", "xform" in warm[:5], warm[:5])

freq = engine2.frequent("Sop")
check("frecency includes scatter", "scatter" in freq[:3], freq[:5])

# namespaced upstream resolves via base name
ns_sug = engine2.suggestions("Sop", "curve::2.0")
check("versioned upstream uses curve seeds", "resample" in ns_sug[:4], ns_sug[:4])

# empty upstream falls back to popular
none_sug = engine2.suggestions("Sop", None)
check("no-upstream falls back to frequent/popular", len(none_sug) > 3, none_sug)

# ---------------------------------------------------------------- favorites
fav_path = os.path.join(SANDBOX, "custom_tab_favorites.json")
if os.path.exists(fav_path):
    os.remove(fav_path)
from lightspeed import favorites as fav_mod

fm = fav_mod.FavoritesManager()
fm.add_favorite("Sop", "attribwrangle")
fm.add_favorite("Sop", "null")
fm2 = fav_mod.FavoritesManager()
check("favorites persist", fm2.get_favorites("Sop") == ["attribwrangle", "null"],
      fm2.get_favorites("Sop"))
check("toggle off", fm2.toggle("Sop", "null") is False)
check("toggle on", fm2.toggle("Sop", "vdbfrompolygons") is True)
fm2.update_favorites_order("Sop", ["vdbfrompolygons", "attribwrangle"])
fm3 = fav_mod.FavoritesManager()
check("reorder persists",
      fm3.get_favorites("Sop") == ["vdbfrompolygons", "attribwrangle"],
      fm3.get_favorites("Sop"))

# corrupt file tolerated
with open(fav_path, "w") as f:
    f.write("{not json!!")
fm4 = fav_mod.FavoritesManager()
check("corrupt favorites tolerated", fm4.get_favorites("Sop") == [])

# ---------------------------------------------------------------- node creation (real hou, headless)
geo = hou.node("/obj").createNode("geo", "lightspeed_test")
box = geo.createNode("box")
sphere = geo.createNode("sphere")

# leaf detection
box2 = geo.createNode("box")
merge = geo.createNode("merge")
merge.setInput(0, box2)
check("leaf_type_name single", sug.leaf_type_name([box]) == "box")
check("leaf_type_name chain", sug.leaf_type_name([box2, merge]) == "merge")
check("leaf_type_name ambiguous", sug.leaf_type_name([box, sphere]) is None)

# wiring guard logic mirror (panel isn't constructible headless; test the rule)
entry = idx.entry("Sop", "xform")
check("xform max inputs is 1", entry.max_inputs == 1, entry.max_inputs)
entry_m = idx.entry("Sop", "merge")
check("merge accepts many inputs", entry_m.max_inputs > 100, entry_m.max_inputs)

# creating preferred version by full name works
node = geo.createNode(idx.entry("Sop", "curve").name)
check("createNode with deduped name", node.type().name() == "curve::2.0",
      node.type().name())

# undo group + creation smoke (mirrors panel.create_node core path)
with hou.undos.group("Lightspeed test create"):
    n = geo.createNode("attribwrangle")
    n.setInput(0, box)
    n.moveToGoodPosition()
check("undo-grouped create+wire works", n.inputs()[0] == box)

geo.destroy()

# ---------------------------------------------------------------- UI imports (no display)
try:
    import lightspeed.qt as lqt
    check("Qt shim imports (PySide%d)" % lqt.PYSIDE_VERSION, True)
    import lightspeed.panel  # noqa: F401  (module import only; no QDialog instantiation headless)
    check("panel module imports", True)
    import lightspeed.gallery_ui as gui
    check("gallery_ui compat alias", gui.LightspeedGallery is lightspeed.panel.LightspeedPanel)
    import lightspeed.smart_suggestions as sm
    check("smart_suggestions compat shim", callable(sm.get_smart_context))
    import lightspeed.qt_utils as qtu
    check("qt_utils compat shim", qtu.BTC_PYSIDE_VERSION in (2, 6))
except Exception:
    traceback.print_exc()
    check("UI module imports", False)

import lightspeed
check("package version 2.0.0", lightspeed.__version__ == "2.0.0")

print()
if FAILURES:
    print(f"RESULT: {len(FAILURES)} FAILURES: {FAILURES}")
    sys.exit(1)
print("RESULT: ALL TESTS PASSED")
