"""
suggestions.py
--------------
Predicts useful "next nodes" for the current selection.

Three ranked sources, merged best-first:

1. LEARNED  — every node the user creates through Lightspeed records a bigram
              (category, upstream base type) -> (created base type). Counts
              decay with a 30-day half-life so recommendations track how the
              user works *now*. Stored in lightspeed_usage.json.
2. CURATED  — hand-tuned per-category seed maps (below), grounded in real
              Houdini 21 node names, so the panel is smart out of the box.
3. POPULAR  — the user's most-created nodes in this category ("frecency"),
              used to fill remaining slots and to order the empty-search view.

All keys/values are *base* names (namespace/version stripped); the panel
resolves them to concrete creatable types via the NodeIndex.
"""

import time

from . import store
from .fuzzy import base_name

USAGE_FILE = "lightspeed_usage.json"
HALF_LIFE_DAYS = 30.0
_DAY = 86400.0


# ---------------------------------------------------------------------------
# Curated seed maps  (category -> upstream base -> suggested bases)
# ---------------------------------------------------------------------------

CURATED = {
    "Sop": {
        # Base geo
        "geo": ["file", "object_merge", "null"],
        "box": ["xform", "polybevel", "polyextrude", "boolean", "mirror", "remesh", "matchsize", "null"],
        "sphere": ["xform", "polybevel", "clip", "mirror", "remesh", "normal", "matchsize", "null"],
        "tube": ["xform", "polycap", "polybevel", "clip", "mirror", "remesh", "null"],
        "grid": ["xform", "mountain", "polyextrude", "scatter", "attribnoise", "null"],
        "torus": ["xform", "polybevel", "null"],
        "testgeometry_rubbertoy": ["xform", "remesh", "scatter", "null"],
        "font": ["polyextrude", "polybevel", "remesh", "xform", "null"],

        # Curves
        "curve": ["resample", "sweep", "carve", "polywire", "copytopoints", "xform", "null"],
        "line": ["resample", "sweep", "copytopoints", "xform", "null"],
        "drawcurve": ["resample", "sweep", "xform", "null"],
        "circle": ["sweep", "polyextrude", "copytopoints", "resample", "null"],
        "resample": ["sweep", "copytopoints", "attribwrangle", "polywire", "null"],
        "sweep": ["uvunwrap", "normal", "polybevel", "null"],

        # Attributes / VEX
        "attribwrangle": ["attribwrangle", "attribpromote", "blast", "grouppromote", "null", "filecache"],
        "attribcreate": ["attribwrangle", "null"],
        "attribnoise": ["attribwrangle", "copytopoints", "null"],
        "attribrandomize": ["copytopoints", "attribwrangle", "null"],
        "attribvop": ["null", "attribpromote", "filecache"],

        # Scatter / copy
        "scatter": ["copytopoints", "attribrandomize", "attribnoise", "null"],
        "copytopoints": ["merge", "filecache", "null"],
        "copyandtransform": ["merge", "null"],

        # Volumes
        "vdbfrompolygons": ["vdbsmoothsdf", "vdbcombine", "vdbreshapesdf", "convertvdb", "filecache"],
        "isooffset": ["convert", "vdbfrompolygons", "filecache"],
        "volumerasterizeattributes": ["vdbconvert", "filecache", "null"],

        # Common flow
        "xform": ["null", "merge", "copytopoints", "mirror", "clip"],
        "merge": ["null", "output", "filecache", "groupcreate"],
        "file": ["unpack", "convert", "xform", "matchsize", "null"],
        "object_merge": ["xform", "blast", "null"],
        "null": ["merge", "output", "xform"],
        "blast": ["null", "merge", "attribwrangle"],
        "boolean": ["polybevel", "remesh", "normal", "null"],
        "polyextrude": ["polybevel", "normal", "subdivide", "null"],
        "polybevel": ["normal", "subdivide", "null"],
        "remesh": ["attribnoise", "smooth", "null"],
        "subdivide": ["normal", "null"],
        "groupcreate": ["blast", "polyextrude", "attribwrangle", "null"],
        "filecache": ["null", "unpack"],
        "switch": ["null", "merge"],

        # Sim
        "dopnet": ["dopimport", "filecache", "null"],
        "popnet": ["filecache", "null"],
        "vellumsolver": ["vellumpostprocess", "filecache", "null"],
        "rbdmaterialfracture": ["rbdbulletsolver", "rbdconfigure", "filecache"],
        "rbdbulletsolver": ["rbdexplodedview", "filecache", "null"],
        "pyrosolver": ["pyropostprocess", "pyrobakevolume", "filecache"],
        "flipsolver": ["particlefluidsurface", "filecache", "null"],
        "particlefluidsurface": ["filecache", "null"],

        # KineFX / rigging
        "rigdoctor": ["rigpose", "skeletonblend", "ikchains", "bonedeform"],
        "skeleton": ["rigdoctor", "rigpose", "skeletonblend"],
        "ikchains": ["rigpose", "skeletonblend", "null"],
        "rigpose": ["bonedeform", "skeletonblend", "null"],
        "bonedeform": ["deltamush", "null"],
        "capturepacked": ["bonedeform", "null"],
    },

    # Copernicus (H20.5+ imaging context)
    "Cop": {
        "file": ["colorcorrect", "blur", "xform2d", "layer", "null"],
        "sopimport": ["rasterizesetup", "rasterizegeo", "heighttonormal", "null"],
        "rasterizesetup": ["rasterizegeo", "rasterizelayer", "null"],
        "rasterizegeo": ["heighttonormal", "blur", "layer", "null"],
        "fractalnoise": ["remap", "blur", "colorcorrect", "heighttonormal", "layer"],
        "worleynoise": ["remap", "colorcorrect", "layer"],
        "phasornoise": ["remap", "colorcorrect", "layer"],
        "checkerboard": ["xform2d", "layer"],
        "ramp": ["remap", "layer"],
        "constant": ["layer", "blend"],
        "blur": ["sharpen", "layer", "colorcorrect", "null"],
        "colorcorrect": ["layer", "ociotransform", "null", "rop_image"],
        "layer": ["colorcorrect", "blur", "rop_image", "null"],
        "blend": ["colorcorrect", "rop_image", "null"],
        "chromakey": ["dilateerode", "blur", "layer"],
        "heighttonormal": ["previewmaterial", "layer", "null"],
        "heighttoambientocclusion": ["layer", "previewmaterial"],
        "wrangle": ["layer", "colorcorrect", "null"],
        "onnx": ["colorcorrect", "layer", "null"],
        "null": ["rop_image", "layer", "output"],
        "cryptomatte": ["idtomask", "layer"],
        "idtomask": ["dilateerode", "layer"],
    },

    # Solaris
    "Lop": {
        "sopimport": ["materiallibrary", "assignmaterial", "xform", "merge", "null"],
        "sceneimport": ["materiallibrary", "graftstages", "null"],
        "sopcreate": ["materiallibrary", "assignmaterial", "merge", "null"],
        "reference": ["xform", "merge", "editproperties", "null"],
        "assetreference": ["xform", "merge", "null"],
        "materiallibrary": ["assignmaterial", "null"],
        "assignmaterial": ["karmarendersettings", "merge", "null"],
        "camera": ["karmarendersettings", "null"],
        "domelight": ["karmarendersettings", "lightmixer", "null"],
        "distantlight": ["karmarendersettings", "lightmixer", "null"],
        "light": ["lightmixer", "karmarendersettings", "null"],
        "karmarendersettings": ["usdrender_rop", "karmarenderproducts", "null"],
        "rendersettings": ["usdrender_rop", "null"],
        "merge": ["null", "karmarendersettings", "usd_rop"],
        "xform": ["merge", "null"],
        "instancer": ["xform", "merge", "null"],
        "componentgeometry": ["componentmaterial", "componentoutput"],
        "componentmaterial": ["componentoutput"],
        "componentoutput": ["null", "merge"],
        "null": ["merge", "usd_rop", "usdrender_rop"],
    },

    # Dynamics
    "Dop": {
        "rigidbodysolver": ["gravity", "groundplane", "merge"],
        "bulletrbdsolver": ["gravity", "groundplane", "merge"],
        "vellumsolver": ["gravity", "vellumsource", "merge"],
        "vellumobject": ["vellumsolver", "gravity"],
        "flipsolver": ["gravity", "volumesource", "merge"],
        "pyrosolver": ["volumesource", "gravity", "merge"],
        "smokesolver": ["volumesource", "gravity", "merge"],
        "popsolver": ["popsource", "gravity", "popforce"],
        "popobject": ["popsolver", "popsource"],
        "popsource": ["popforce", "popdrag", "popwind"],
        "rbdpackedobject": ["bulletrbdsolver", "gravity", "groundplane"],
        "groundplane": ["merge", "gravity"],
        "gravity": ["merge", "output"],
        "merge": ["output", "null"],
    },

    # Objects
    "Object": {
        "geo": ["geo", "cam", "hlight", "envlight", "null"],
        "cam": ["hlight", "envlight", "null"],
        "hlight": ["hlight", "envlight", "cam"],
        "envlight": ["cam", "hlight"],
        "null": ["geo", "cam"],
        "subnet": ["geo", "null"],
    },

    # TOPs / PDG
    "Top": {
        "filepattern": ["ropfetch", "partitionbyframe", "genericgenerator"],
        "wedge": ["ropfetch", "ropgeometry", "ropkarma"],
        "ropfetch": ["partitionbyframe", "waitforall", "ffmpegencodevideo"],
        "ropgeometry": ["waitforall", "ropkarma", "partitionbyframe"],
        "ropkarma": ["waitforall", "ffmpegencodevideo"],
        "ropmantra": ["waitforall", "ffmpegencodevideo"],
        "waitforall": ["ffmpegencodevideo", "pythonscript", "output"],
        "ffmpegencodevideo": ["output", "null"],
        "localscheduler": ["ropfetch", "wedge"],
        "pythonscript": ["waitforall", "output", "null"],
        "genericgenerator": ["pythonscript", "attributecreate"],
    },

    # ROPs
    "Driver": {
        "geometry": ["merge", "batch", "null"],
        "karma": ["merge", "batch", "null"],
        "ifd": ["merge", "batch", "null"],
        "opengl": ["merge", "null"],
        "comp": ["merge", "null"],
        "alembic": ["merge", "null"],
        "usd": ["merge", "null"],
    },
}

# Fallback "popular nodes" per category for cold-start empty-query ordering.
POPULAR = {
    "Sop": ["attribwrangle", "null", "merge", "xform", "blast", "scatter",
            "copytopoints", "box", "grid", "sphere", "filecache", "groupcreate",
            "polyextrude", "remesh", "resample", "boolean"],
    "Cop": ["file", "sopimport", "blur", "colorcorrect", "layer", "fractalnoise",
            "remap", "xform2d", "heighttonormal", "wrangle", "rop_image", "null"],
    "Lop": ["sopimport", "materiallibrary", "assignmaterial", "camera",
            "domelight", "karmarendersettings", "usdrender_rop", "merge",
            "xform", "reference", "null"],
    "Dop": ["gravity", "groundplane", "merge", "bulletrbdsolver", "vellumsolver",
            "popsolver", "popsource", "volumesource", "null"],
    "Object": ["geo", "cam", "hlight", "envlight", "null", "subnet"],
    "Top": ["filepattern", "ropfetch", "wedge", "waitforall", "localscheduler",
            "pythonscript", "ffmpegencodevideo"],
    "Driver": ["karma", "geometry", "usd", "batch", "merge"],
    "Vop": ["parameter", "bind", "constant", "multiply", "add", "fit", "ramp"],
    "Chop": ["channel", "wave", "noise", "math", "lag", "export"],
    "Cop2": ["file", "color", "over", "composite", "blur", "null"],
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class SuggestionEngine(object):
    """Merges learned usage with curated seeds. One instance per panel open
    is fine — data loads once and saves on each recorded creation."""

    def __init__(self):
        data = store.load_json(USAGE_FILE, {})
        self._bigrams = data.get("bigrams", {})   # cat -> up -> created -> [count, ts]
        self._counts = data.get("counts", {})     # cat -> created -> [count, ts]

    # -- recording ------------------------------------------------------

    def record_creation(self, category_name, upstream_type_name, created_type_name):
        now = time.time()
        created = base_name(created_type_name)
        cat_counts = self._counts.setdefault(category_name, {})
        self._bump(cat_counts, created, now)

        if upstream_type_name:
            upstream = base_name(upstream_type_name)
            cat_bigrams = self._bigrams.setdefault(category_name, {})
            self._bump(cat_bigrams.setdefault(upstream, {}), created, now)

        store.save_json(USAGE_FILE, {
            "bigrams": self._bigrams,
            "counts": self._counts,
        })

    @staticmethod
    def _bump(bucket, key, now):
        count, ts = bucket.get(key, [0.0, now])
        # Fold the old count through decay before incrementing, so counts
        # stay comparable no matter when they were last touched.
        count = _decayed(count, ts, now) + 1.0
        bucket[key] = [count, now]

    # -- queries --------------------------------------------------------

    def suggestions(self, category_name, upstream_type_name, limit=10):
        """
        Ranked base-name suggestions for "what comes after `upstream` here".
        Learned bigrams first, then curated seeds, then popular fill.
        """
        now = time.time()
        ordered = []
        seen = set()

        def take(names):
            for n in names:
                if n not in seen:
                    seen.add(n)
                    ordered.append(n)

        if upstream_type_name:
            upstream = base_name(upstream_type_name)

            learned = self._bigrams.get(category_name, {}).get(upstream, {})
            take([k for k, (c, ts) in
                  sorted(learned.items(),
                         key=lambda kv: -_decayed(kv[1][0], kv[1][1], now))
                  if _decayed(c, ts, now) >= 0.5])

            take(CURATED.get(category_name, {}).get(upstream, []))

        if len(ordered) < limit:
            take(self.frequent(category_name, limit))

        return ordered[:limit]

    def frequent(self, category_name, limit=16):
        """User's most-created base names in this category (decayed),
        padded with the static POPULAR list."""
        now = time.time()
        counts = self._counts.get(category_name, {})
        mine = [k for k, (c, ts) in
                sorted(counts.items(),
                       key=lambda kv: -_decayed(kv[1][0], kv[1][1], now))
                if _decayed(c, ts, now) >= 0.25]
        out = []
        seen = set()
        for name in mine + POPULAR.get(category_name, []):
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out[:limit]


def _decayed(count, timestamp, now):
    age_days = max(0.0, (now - timestamp) / _DAY)
    return count * (0.5 ** (age_days / HALF_LIFE_DAYS))


# ---------------------------------------------------------------------------
# Upstream ("leaf") resolution from a selection — kept from the original
# design, hardened.
# ---------------------------------------------------------------------------

def leaf_type_name(selected_nodes):
    """
    The node type whose output the user is likely extending.
    Single selection -> that node. Multi-selection -> the unique node that
    doesn't feed any other selected node; None when ambiguous.
    """
    if not selected_nodes:
        return None
    if len(selected_nodes) == 1:
        return selected_nodes[0].type().name()

    sel_set = set(selected_nodes)
    leaves = []
    for node in selected_nodes:
        try:
            outputs = node.outputs()
        except Exception:
            outputs = ()
        if not any(out in sel_set for out in outputs):
            leaves.append(node)
    if len(leaves) == 1:
        return leaves[0].type().name()
    return None
