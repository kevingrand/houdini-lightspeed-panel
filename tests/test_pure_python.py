"""
Houdini-free checks for the pure-python modules (fuzzy matcher + alias
system). Runs with any Python 3:

    python3 tests/test_pure_python.py

The full suite (index, suggestions, presets, node creation) needs hython —
see test_lightspeed_hython.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

from lightspeed import fuzzy, aliases  # noqa: E402

FAILURES = []


def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}" + (f"  -> {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(label)


class E(object):
    def __init__(self, name, label, base=None):
        self.name, self.label, self.base = name, label, base or name


ENTRIES = [
    E("copytopoints", "Copy to Points"),
    E("copyandtransform", "Copy and Transform"),
    E("clothdeformer", "Cloth Deformer"),
    E("colornormal", "Color Normal"),
    E("polybevel", "PolyBevel"),
    E("attribnoise", "Attribute Noise"),
    E("MOPs::Instancer", "MOPs Instancer", base="Instancer"),
    E("box", "Box"),
]

# --- fuzzy basics (unchanged behaviour) ---
s, _ = fuzzy.score("box", "box", "Box")
check("exact scores 0", s == 0.0, s)
s, _ = fuzzy.score("plybvl", "polybevel", "PolyBevel")
check("subsequence matches", s is not None)

# --- alias tiers ---
hits = aliases.alias_hits_for_query("cloner")
check("cloner hits copytopoints", "copytopoints" in hits, hits)
check("exact term is tier 0", hits["copytopoints"].tier == 0)
check("cloner hits instancer (MOPs)", "instancer" in hits, hits)

hits = aliases.alias_hits_for_query("clon")
check("prefix is tier 1", hits["copytopoints"].tier == 1, hits)

hits = aliases.alias_hits_for_query("clner")
check("typo subsequence is tier 3", hits["copytopoints"].tier == 3, hits)

hits = aliases.alias_hits_for_query("effector")
check("word-boundary prefix (plain effector)", "transform" in hits, hits)

# --- ranking: exact alias beats subsequence noise ---
ranked = fuzzy.rank(ENTRIES, "cloner",
                    alias_hits=aliases.alias_hits_for_query("cloner"))
check("cloner ranks copytopoints first",
      ranked and ranked[0]["entry"].name == "copytopoints",
      [(r["entry"].name, r["score"]) for r in ranked[:3]])
check("alias term attached", ranked[0]["alias"] == "cloner")

# --- case-insensitive resolution (MOPs::Instancer, base 'Instancer') ---
check("MOPs entry resolves via lowercase alias key",
      any(r["entry"].name == "MOPs::Instancer" for r in ranked),
      [r["entry"].name for r in ranked])

# --- direct match keeps its (better) score when it's also an alias hit ---
ranked = fuzzy.rank(ENTRIES, "box",
                    alias_hits=aliases.alias_hits_for_query("box"))
check("direct exact still first for 'box'",
      ranked and ranked[0]["entry"].name == "box",
      [r["entry"].name for r in ranked[:3]])

# --- AE vocabulary ---
hits = aliases.alias_hits_for_query("wiggle")
check("wiggle -> attribnoise", "attribnoise" in hits, hits)
ranked = fuzzy.rank(ENTRIES, "wiggle", alias_hits=hits)
check("wiggle surfaces attribnoise",
      any(r["entry"].name == "attribnoise" for r in ranked),
      [r["entry"].name for r in ranked])

# --- H21 Copernicus vocabulary present ---
for term in ("flow", "reaction diffusion", "grunge", "phasor", "cables"):
    check("H21 term '%s' known" % term, term in aliases.ALIASES)

# --- legacy API kept ---
check("get_mapped_nodes compat",
      "copytopoints" in aliases.get_mapped_nodes("Cloner"))
check("C4D_MAPPINGS compat", aliases.C4D_MAPPINGS is aliases.ALIASES)


# --- fast path (precomputed entry fields) must score identically ---
class FastE(object):
    """Mimics node_index.NodeEntry's precomputed search fields."""
    def __init__(self, name, label, base=None):
        self.name, self.label, self.base = name, label, base or name
        self.name_l = name.lower()
        self.label_l = label.lower()
        self.base_l = fuzzy.base_name(self.name_l)
        self.words = fuzzy.entry_words(self.name_l, self.label_l)
        self.acr = fuzzy.acronym(self.label_l)


FAST_ENTRIES = [FastE(e.name, e.label, e.base) for e in ENTRIES]
for q in ("box", "ctp", "plybvl", "copy points", "cloner", "att",
          "colnorm", "no such thing xyz"):
    hits = aliases.alias_hits_for_query(q)
    slow = [(r["entry"].name, round(r["score"], 6))
            for r in fuzzy.rank(ENTRIES, q, alias_hits=hits)]
    fast = [(r["entry"].name, round(r["score"], 6))
            for r in fuzzy.rank(FAST_ENTRIES, q, alias_hits=hits)]
    check("fast path parity for '%s'" % q, slow == fast,
          {"slow": slow[:4], "fast": fast[:4]})

print()
if FAILURES:
    print(f"RESULT: {len(FAILURES)} FAILURES: {FAILURES}")
    sys.exit(1)
print("RESULT: ALL TESTS PASSED")
