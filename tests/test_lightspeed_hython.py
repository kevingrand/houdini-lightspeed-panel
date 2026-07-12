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
check("exact alias term is tier 0", hits["copytopoints"].tier == 0,
      hits["copytopoints"])
ranked = fuzzy.rank(idx.entries("Sop"), "cloner", alias_hits=hits)
names = [r["entry"].base for r in ranked]
check("rank alias cloner returns copytopoints", "copytopoints" in names, names[:5])
check("exact alias cloner ranks FIRST", ranked[0]["entry"].base == "copytopoints",
      names[:5])
alias_row = next(r for r in ranked if r["entry"].base == "copytopoints")
check("alias term attached", alias_row["alias"] == "cloner", alias_row["alias"])

# alias prefix + typo tolerance
hits_prefix = aliases.alias_hits_for_query("clon")
check("alias prefix clon matches", "copytopoints" in hits_prefix
      and hits_prefix["copytopoints"].tier == 1, hits_prefix.get("copytopoints"))
hits_typo = aliases.alias_hits_for_query("clner")
check("alias typo clner matches", "copytopoints" in hits_typo,
      hits_typo.get("copytopoints"))
ranked_typo = fuzzy.rank(idx.entries("Sop"), "clner", alias_hits=hits_typo)
check("typo alias still surfaces copytopoints",
      any(r["entry"].base == "copytopoints" for r in ranked_typo),
      [r["entry"].base for r in ranked_typo][:5])

# AE vocabulary
hits_ae = aliases.alias_hits_for_query("wiggle")
check("AE alias wiggle -> attribnoise", "attribnoise" in hits_ae, hits_ae)
ranked_ae = fuzzy.rank(idx.entries("Sop"), "wiggle", alias_hits=hits_ae)
check("wiggle surfaces attribnoise",
      any(r["entry"].base == "attribnoise" for r in ranked_ae),
      [r["entry"].base for r in ranked_ae][:5])

# case-insensitive alias resolution (namespaced HDA toolkits like MOPs)
class _FakeEntry(object):
    def __init__(self, name, label, base):
        self.name, self.label, self.base = name, label, base
_fake = [_FakeEntry("MOPs::Instancer", "MOPs Instancer", "Instancer")]
ranked_mops = fuzzy.rank(_fake, "cloner",
                         alias_hits=aliases.alias_hits_for_query("cloner"))
check("case-insensitive alias resolves MOPs::Instancer",
      len(ranked_mops) == 1 and ranked_mops[0]["alias"] == "cloner",
      ranked_mops)

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

# NodeEntry precomputed search fields exist and agree with fuzzy helpers
sample = idx.entries("Sop")[0]
check("entry precomputes lowercase fields",
      sample.name_l == sample.name.lower()
      and sample.base_l == fuzzy.base_name(sample.name_l)
      and sample.acr == fuzzy.acronym(sample.label_l)
      and sample.words == fuzzy.entry_words(sample.name_l, sample.label_l))

# fast path (precomputed) must equal the string path — real index data
class _Plain(object):
    def __init__(self, e):
        self.name, self.label, self.base = e.name, e.label, e.base

for q in ("box", "att", "plybvl", "copy points", "wrangle"):
    fast_res = [(r["entry"].name, round(r["score"], 6))
                for r in fuzzy.rank(idx.entries("Sop"), q)]
    slow_res = [(r["entry"].name, round(r["score"], 6))
                for r in fuzzy.rank([_Plain(e) for e in idx.entries("Sop")], q)]
    check("fast/slow rank parity '%s'" % q, fast_res == slow_res,
          {"fast": fast_res[:3], "slow": slow_res[:3]})

# per-keystroke ranking stays fast (precomputed fields)
_t0 = time.perf_counter()
for _ in range(50):
    fuzzy.rank(idx.entries("Sop"), "att")
_per_call_ms = (time.perf_counter() - _t0) / 50 * 1000
print(f"  rank('att') over {len(idx.entries('Sop'))} SOPs: {_per_call_ms:.2f} ms/call")
check("rank under 25ms/keystroke", _per_call_ms < 25.0, _per_call_ms)

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
check("H21 Cop seeds present", "flowsolver" in sug.CURATED["Cop"]
      and "scattershapes" in sug.POPULAR["Cop"])
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

# reset: per-category forget drops learned data but keeps curated seeds
# ("vignette" is deliberately NOT in the curated Cop 'blur' seeds)
engine2.record_creation("Cop", "blur", "vignette")
engine2.reset("Sop")
after = engine2.suggestions("Sop", "box")
check("reset(Sop) forgets learned scatter", after and after[0] == "xform",
      after[:4])
engine3 = sug.SuggestionEngine()
check("reset persisted to disk",
      engine3.suggestions("Sop", "box")[0] == "xform")
check("reset(Sop) spared other categories",
      engine3.suggestions("Cop", "blur")[0] == "vignette",
      engine3.suggestions("Cop", "blur")[:3])
engine3.reset(None)
engine4 = sug.SuggestionEngine()
check("reset(None) wipes everything",
      engine4.suggestions("Cop", "blur")[0] == "sharpen"     # curated again
      and engine4.frequent("Sop")[0] == sug.POPULAR["Sop"][0],
      engine4.suggestions("Cop", "blur")[:3])

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

# wire insertion: endpoint resolution + the REAL splice path
from lightspeed.panel import LightspeedPanel, splice_node_into

up_src = geo.createNode("box")
down_dst = geo.createNode("xform")
down_dst.setInput(0, up_src)
conn = down_dst.inputConnections()[0]
check("NodeConnection has isSelected", hasattr(conn, "isSelected"))
endpoints = LightspeedPanel._connection_endpoints(conn)
check("connection endpoints resolved", endpoints is not None)
if endpoints:
    up, oi, down, ii = endpoints
    check("endpoints orientation", up.path() == up_src.path()
          and down.path() == down_dst.path(),
          (up.path(), down.path()))
    spliced = geo.createNode("null")
    splice_node_into(spliced, endpoints)
    check("splice rewires chain",
          down_dst.inputs()[0] == spliced and spliced.inputs()[0] == up_src)
    mid_y = (up_src.position().y() + down_dst.position().y()) / 2.0
    check("spliced node placed at wire midpoint",
          abs(spliced.position().y() - mid_y) < 0.01,
          (spliced.position(), mid_y))

geo.destroy()

# ---------------------------------------------------------------- presets
from lightspeed import presets as ls_presets

check("presets: no category -> empty", ls_presets.entries_for_category(None) == [])

sop_cat = hou.nodeTypeCategories()["Sop"]
gal_path = os.path.join(SANDBOX, "lightspeed.gal")
if os.path.exists(gal_path):
    os.remove(gal_path)
ls_presets._installed = False
try:
    pgeo = hou.node("/obj").createNode("geo", "lightspeed_preset_test")
    noise = pgeo.createNode("attribnoise")
    entry = ls_presets.capture("gentle drift", noise)
    check("preset captured", entry is not None and os.path.exists(gal_path))
    items = ls_presets.entries_for_category(sop_cat)
    mine = [it for it in items if it.label == "gentle drift"]
    check("preset listed for Sop", len(mine) == 1,
          [it.label for it in items][:5])
    if mine:
        fresh = pgeo.createNode("attribnoise")
        check("preset applies to node", ls_presets.apply_to_node(mine[0], fresh))
    pgeo.destroy()
except hou.Error:
    traceback.print_exc()
    check("preset capture/apply", False)

# ---------------------------------------------------------------- nodegraph hook
import nodegraphhooks

check("hook ignores non-keyboard events",
      nodegraphhooks.createEventHandler(object(), []) == (None, False))
check("hook is off by default", not nodegraphhooks._tab_hook_enabled())

# ---------------------------------------------------------------- UI imports (no display)
try:
    import lightspeed.qt as lqt
    check("Qt shim imports (PySide%d)" % lqt.PYSIDE_VERSION, True)
    import lightspeed.panel  # noqa: F401  (module import only; no QDialog instantiation headless)
    check("panel module imports", True)

    # inline-name query parsing (pure logic, no widget needed)
    parse = lightspeed.panel.LightspeedPanel._parse_query
    check("parse: 'null OUT_TEXT' names node",
          parse(None, "null OUT_TEXT") == ("null", "OUT_TEXT"))
    check("parse: 'cam RENDER_CAM' names node",
          parse(None, "cam RENDER_CAM") == ("cam", "RENDER_CAM"))
    check("parse: 'copy points' untouched",
          parse(None, "copy points") == ("copy points", None))
    check("parse: 'Copy To Points' untouched",
          parse(None, "Copy To Points") == ("Copy To Points", None))
    check("parse: 'convert VDB' untouched (no underscore)",
          parse(None, "convert VDB") == ("convert VDB", None))
    check("parse: 'import USD' untouched",
          parse(None, "import USD") == ("import USD", None))
    check("parse: single token untouched",
          parse(None, "OUT_ALL") == ("OUT_ALL", None))

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
check("package version 2.1.0", lightspeed.__version__ == "2.1.0")

print()
if FAILURES:
    print(f"RESULT: {len(FAILURES)} FAILURES: {FAILURES}")
    sys.exit(1)
print("RESULT: ALL TESTS PASSED")
