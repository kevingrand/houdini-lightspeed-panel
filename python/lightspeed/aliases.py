"""
aliases.py
----------
Maps terminology from other 3D software (Cinema 4D, Blender, Maya, 3ds Max)
and common VFX vocabulary to Houdini node types, so users can search with
familiar terms and find the Houdini equivalent.

e.g. "Cube" → "Box", "Cloner" → "copytopoints", "Keyer" → "chromakey"

Values are *base* node names (namespace/version stripped). The panel resolves
them against whatever category it is currently showing, so "wrangle" maps to
attribwrangle in SOPs and to the Copernicus wrangle in COPs when present.
"""

# Key = Search Term (lowercase)
# Value = List of Houdini base node names (lowercase) to suggest

ALIASES = {

    # ─────────────────────────────────────────────────────────
    # PRIMITIVES & GENERATORS
    # ─────────────────────────────────────────────────────────
    "cube":             ["box"],
    "plane":            ["grid"],
    "quad":             ["grid"],
    "disc":             ["circle"],
    "disk":             ["circle"],
    "cylinder":         ["tube"],
    "cone":             ["tube"],
    "capsule":          ["tube"],
    "pyramid":          ["tube"],
    "torus":            ["torus"],
    "sphere":           ["sphere"],
    "icosphere":        ["platonic"],
    "geosphere":        ["platonic"],
    "platonic solid":   ["platonic"],
    "teapot":           ["testgeometry_rubbertoy"],
    "landscape":        ["heightfield_noise", "mountain"],
    "terrain":          ["heightfield_noise", "heightfield"],
    "figure":           ["testgeometry_rubbertoy"],
    "oil tank":         ["tube"],
    "helix":            ["spiral"],

    # ─────────────────────────────────────────────────────────
    # SPLINES & CURVES
    # ─────────────────────────────────────────────────────────
    "spline":           ["curve", "line", "drawcurve"],
    "path":             ["curve", "line"],
    "bezier":           ["curve", "drawcurve"],
    "nurbs curve":      ["curve"],
    "nurbs":            ["curve"],
    "arc":              ["circle"],
    "star":             ["circle"],     # circle SOP has star divisions
    "flower":           ["circle"],
    "n-side":           ["circle"],
    "cogwheel":         ["circle"],
    "rectangle":        ["curve"],
    "text":             ["font", "text"],
    "motext":           ["font", "text"],
    "formula spline":   ["curve"],

    # ─────────────────────────────────────────────────────────
    # MOGRAPH / INSTANCING / SCATTERING
    # ─────────────────────────────────────────────────────────
    "cloner":           ["copytopoints", "copyandtransform", "instancer"],
    "clone":            ["copytopoints", "copyandtransform", "instancer"],
    "mograph":          ["copytopoints", "scatter", "instancer"],
    "instance":         ["instance", "copytopoints"],
    "array":            ["copyandtransform"],
    "linear array":     ["copyandtransform"],
    "radial array":     ["copyandtransform"],
    "atom array":       ["wireframe", "ends"],
    "matrix object":    ["scatter", "copytopoints"],
    "scatter":          ["scatter"],
    "distribute":       ["scatter"],
    "fracture object":  ["voronoifracture", "rbdmaterialfracture"],
    "polyfx":           ["assemble", "explodedview"],
    "mospline":         ["resample", "carve"],
    "tracer":           ["trail", "add"],

    # ─────────────────────────────────────────────────────────
    # MOGRAPH EFFECTORS
    # ─────────────────────────────────────────────────────────
    # MOPs base names (instancer, falloff, transform_modifier, …) are listed
    # alongside the vanilla-Houdini answer; they only resolve — and only show
    # up — when the MOPs toolkit is actually installed.
    "effector":         ["attribwrangle", "attribrandomize", "falloff"],
    "plain effector":   ["transform", "attribwrangle", "transform_modifier"],
    "random effector":  ["attribrandomize", "randomize_modifier", "randomize"],
    "shader effector":  ["attribfrommap", "falloff_from_texture"],
    "delay effector":   ["timeshift", "trail", "delay_modifier"],
    "falloff":          ["falloff_from_shape", "falloff_from_texture",
                         "falloff", "attribpaint"],
    "formula effector": ["attribwrangle"],
    "step effector":    ["attribwrangle", "sort"],
    "target effector":  ["lookat", "aim_modifier"],
    "spline effector":  ["pathdeform"],
    "sound effector":   ["chop", "chopnet"],
    "time effector":    ["attribwrangle"],
    "push apart":       ["particlefluidsurface", "attribwrangle"],
    "inheritance effector": ["attribtransfer"],
    "volume effector":  ["volumewrangle"],
    "group effector":   ["attribwrangle"],

    # ─────────────────────────────────────────────────────────
    # GENERATORS / NURBS / MESH GENERATORS
    # ─────────────────────────────────────────────────────────
    "extrude":          ["polyextrude"],
    "extrude object":   ["polyextrude"],
    "extrude nurbs":    ["polyextrude"],
    "inner extrude":    ["polyextrude"],
    "sweep":            ["sweep"],
    "sweep nurbs":      ["sweep"],
    "loft":             ["skin", "loft"],
    "loft nurbs":       ["skin", "loft"],
    "lathe":            ["revolve"],
    "lathe nurbs":      ["revolve"],
    "revolve":          ["revolve"],
    "thicken":          ["polyextrude"],
    "cloth surface":    ["subdivide"],
    "subdivision surface": ["subdivide"],
    "subd":             ["subdivide"],
    "sds":              ["subdivide"],
    "hypernurbs":       ["subdivide"],
    "smoothing":        ["subdivide", "smooth"],
    "smooth":           ["smooth", "subdivide"],
    "catmull clark":    ["subdivide"],

    # ─────────────────────────────────────────────────────────
    # MODELING / POLYGON OPERATIONS
    # ─────────────────────────────────────────────────────────
    "boolean":          ["boolean"],
    "boole":            ["boolean"],
    "bevel":            ["polybevel"],
    "chamfer":          ["polybevel"],
    "fillet":           ["polybevel"],
    "knife":            ["polysplit", "polycut", "clip"],
    "cut":              ["polysplit", "polycut"],
    "slice":            ["clip", "polysplit"],
    "loop cut":         ["polysplit", "edgeloop"],
    "bridge":           ["polybridge"],
    "close polygon hole": ["polyfill"],
    "fill hole":        ["polyfill"],
    "cap":              ["polyfill", "polycap"],
    "stitch":           ["fuse"],
    "weld":             ["fuse"],
    "merge points":     ["fuse"],
    "connect":          ["fuse", "merge"],
    "optimize":         ["fuse", "facet", "clean"],
    "collapse":         ["fuse", "dissolve"],
    "iron":             ["smooth"],
    "set flow":         ["edgeloop"],
    "inset":            ["polyextrude"],
    "poke":             ["divide"],
    "triangulate":      ["divide"],
    "untriangulate":    ["divide"],
    "quadrangulate":    ["remesh"],
    "retriangulate":    ["divide"],
    "flip normals":     ["reverse"],
    "reverse normals":  ["reverse"],
    "align normals":    ["facet"],
    "normal tag":       ["normal", "facet"],
    "phong tag":        ["facet"],

    # ─────────────────────────────────────────────────────────
    # DEFORMERS
    # ─────────────────────────────────────────────────────────
    "bend":             ["bend"],
    "twist":            ["twist"],
    "taper":            ["twist"],      # twist SOP does taper
    "shear":            ["twist"],      # twist SOP does shear
    "bulge":            ["softpeak", "peak"],
    "squash and stretch": ["squashstretch", "bend"],
    "squash stretch":   ["squashstretch", "bend"],
    "displacer":        ["mountain", "attribnoise"],
    "noise deformer":   ["mountain", "attribnoise"],
    "ffd":              ["lattice"],
    "lattice":          ["lattice"],
    "warp":             ["lattice"],
    "mesh deform":      ["lattice"],
    "wrap":             ["lattice"],
    "spline wrap":      ["pathdeform"],
    "spline deformer":  ["pathdeform"],
    "path deform":      ["pathdeform"],
    "formula deformer": ["pointwrangle", "attribwrangle"],
    "spherify":         ["magnet"],
    "wind":             ["ripple", "mountain"],
    "jiggle":           ["spring", "trail"],
    "collision deformer": ["solidconform"],
    "shrink wrap":      ["ray"],
    "surface deformer": ["rivettransform"],
    "morph":            ["blendshapes"],
    "pose morph":       ["blendshapes"],
    "correction deformer": ["blendshapes", "sculpt"],
    "smoothing deformer": ["smooth"],
    "delta mush":       ["deltamush"],
    "melt":             ["mountain", "attribnoise"],
    "explosion":        ["explodedview"],
    "explosion fx":     ["explodedview", "voronoifracture"],
    "shatter":          ["voronoifracture", "rbdmaterialfracture"],
    "polygon reduction": ["polyreduce"],
    "reduction":        ["polyreduce"],
    "remesh":           ["remesh", "polyreduce"],

    # ─────────────────────────────────────────────────────────
    # TAGS / ATTRIBUTES / PROPERTIES
    # ─────────────────────────────────────────────────────────
    "target tag":       ["lookat"],
    "constraint":       ["lookat", "rivet", "parentconstraint"],
    "look at":          ["lookat"],
    "aim":              ["lookat"],
    "vibrate tag":      ["transform", "chop", "attribnoise"],
    "protection tag":   ["null"],
    "material tag":     ["material"],
    "material":         ["materiallibrary", "material"],
    "texture tag":      ["uvproject", "uvtransform"],
    "uv tag":           ["uvproject", "uvunwrap", "uvflatten"],
    "vertex map":       ["attribpaint", "attribcreate"],
    "vertex color":     ["attribpaint", "color"],
    "color map":        ["attribpaint", "color"],
    "selection":        ["group", "groupcreate"],
    "selection tag":    ["group", "groupcreate"],
    "tag":              ["attribcreate", "group"],
    "compositing tag":  ["null"],
    "cache tag":        ["filecache"],

    # ─────────────────────────────────────────────────────────
    # DYNAMICS / SIMULATION
    # ─────────────────────────────────────────────────────────
    "rigid body":       ["rbdpackedobject", "rbdbulletsolver"],
    "dynamics":         ["rbdbulletsolver", "vellumsolver"],
    "cloth":            ["vellumcloth", "vellumsolver"],
    "soft body":        ["vellumsoftbody", "vellumsolver"],
    "hair":             ["hairgen", "guidegroom"],
    "fur":              ["hairgen", "guidegroom"],
    "particles":        ["popnet", "popsource"],
    "particle emitter": ["popsource"],
    "emitter":          ["popsource", "popnet"],
    "force":            ["popforce", "popwind"],
    "gravity":          ["gravity", "popforce"],
    "turbulence":       ["popturbulence", "popforce"],
    "attractor":        ["popattract"],
    "fluid":            ["flipsource", "fluidsource"],
    "fire":             ["pyrosource", "pyrosolver"],
    "smoke":            ["pyrosource", "pyrosolver"],
    "pyro":             ["pyrosource", "pyrosolver"],
    "ocean":            ["oceanspectrum", "oceanevaluate"],
    "fracture":         ["rbdmaterialfracture", "voronoifracture"],
    "voronoi":          ["voronoifracture"],

    # ─────────────────────────────────────────────────────────
    # SCENE / HIERARCHY / ORGANIZATION
    # ─────────────────────────────────────────────────────────
    "null":             ["null"],
    "null object":      ["null"],
    "folder":           ["null"],
    "group":            ["null", "subnet"],
    "locator":          ["null"],
    "empty":            ["null"],       # Blender term
    "dummy":            ["null"],       # 3ds Max term
    "xref":             ["objectmerge"],
    "reference":        ["objectmerge"],
    "object merge":     ["objectmerge"],
    "stage":            ["subnet"],
    "shim":             ["null"],
    "annotation":       ["null", "sticky"],
    "sticky":           ["sticky"],
    "backdrop":         ["networkbox"],
    "container":        ["subnet", "networkbox"],
    "subnet":           ["subnet"],
    "digital asset":    ["subnet"],
    "otl":              ["subnet"],
    "hda":              ["subnet"],

    # ─────────────────────────────────────────────────────────
    # DATA / ATTRIBUTES / WRANGLING
    # ─────────────────────────────────────────────────────────
    "xpresso":          ["attribwrangle", "voppnet"],
    "user data":        ["attribcreate"],
    "expression":       ["attribwrangle"],
    "python":           ["pythonsop"],
    "vex":              ["attribwrangle"],
    "wrangle":          ["attribwrangle"],
    "formula":          ["attribwrangle"],
    "calculate":        ["attribwrangle"],
    "measure":          ["measure"],
    "distance":         ["measure", "proximity"],
    "random":           ["attribrandomize"],
    "randomize":        ["attribrandomize"],

    # ─────────────────────────────────────────────────────────
    # UV / TEXTURING
    # ─────────────────────────────────────────────────────────
    "uv unwrap":        ["uvunwrap", "uvflatten"],
    "uv project":       ["uvproject"],
    "uv edit":          ["uvedit"],
    "uv map":           ["uvproject", "uvtransform"],
    "uv relax":         ["uvflatten"],
    "uv pack":          ["uvlayout"],
    "uv transform":     ["uvtransform"],
    "projection":       ["uvproject"],
    "planar mapping":   ["uvproject"],
    "cylindrical mapping": ["uvproject"],
    "spherical mapping": ["uvproject"],
    "box mapping":      ["uvproject"],
    "frontal mapping":  ["uvproject"],

    # ─────────────────────────────────────────────────────────
    # LIGHTS / CAMERAS
    # ─────────────────────────────────────────────────────────
    "light":            ["hlight"],
    "area light":       ["hlight"],
    "point light":      ["hlight"],
    "spot light":       ["hlight"],
    "directional light": ["hlight"],
    "sun":              ["hlight", "envlight"],
    "dome light":       ["envlight"],
    "environment":      ["envlight"],
    "hdri":             ["envlight"],
    "sky":              ["envlight"],
    "camera":           ["cam"],
    "physical camera":  ["cam"],
    "render camera":    ["cam"],

    # ─────────────────────────────────────────────────────────
    # RENDERING / OUTPUT
    # ─────────────────────────────────────────────────────────
    "render":           ["ropnet"],
    "render settings":  ["ropnet"],
    "output":           ["ropnet", "null"],
    "compositing":      ["copnet"],
    "post effect":      ["copnet"],
    "takes":            ["null"],
    "render layer":     ["null"],

    # ─────────────────────────────────────────────────────────
    # IMPORT / EXPORT / CACHING
    # ─────────────────────────────────────────────────────────
    "alembic":          ["alembic"],
    "abc":              ["alembic"],
    "fbx":              ["file"],
    "obj file":         ["file"],
    "file":             ["file"],
    "cache":            ["filecache"],
    "file cache":       ["filecache"],
    "bake":             ["filecache"],

    # ─────────────────────────────────────────────────────────
    # COMMON OPERATIONS (cross-DCC terms)
    # ─────────────────────────────────────────────────────────
    "mirror":           ["mirror"],
    "symmetry":         ["mirror", "clip"],
    "delete":           ["blast", "delete"],
    "blast":            ["blast"],
    "remove":           ["blast", "delete"],
    "separate":         ["blast", "split"],
    "split":            ["split", "blast"],
    "combine":          ["merge"],
    "join":             ["merge", "join"],
    "attach":           ["merge", "join"],
    "sort":             ["sort"],
    "reorder":          ["sort"],
    "measure size":     ["measure", "matchsize"],
    "match size":       ["matchsize"],
    "fit":              ["matchsize"],
    "switch":           ["switch"],
    "toggle":           ["switch"],
    "timeshift":        ["timeshift"],
    "freeze":           ["timeshift"],
    "carve":            ["carve"],
    "clip":             ["clip"],
    "trim":             ["carve", "clip"],
    "scatter points":   ["scatter"],
    "point cloud":      ["scatter"],

    # ─────────────────────────────────────────────────────────
    # BLENDER TERMS
    # ─────────────────────────────────────────────────────────
    "mesh":             ["box"],
    "ico sphere":       ["platonic"],
    "monkey":           ["testgeometry_rubbertoy"],
    "suzanne":          ["testgeometry_rubbertoy"],
    "solidify":         ["polyextrude"],
    "array modifier":   ["copyandtransform"],
    "bevel modifier":   ["polybevel"],
    "mirror modifier":  ["mirror"],
    "decimate":         ["polyreduce"],
    "wireframe modifier": ["wireframe"],
    "screw":            ["revolve"],
    "skin modifier":    ["skin"],
    "wave":             ["ripple"],
    "simple deform":    ["bend", "twist"],
    "proportional editing": ["softpeak"],
    "collection":       ["null"],
    "geometry nodes":   ["attribwrangle", "subnet"],

    # ─────────────────────────────────────────────────────────
    # MAYA TERMS
    # ─────────────────────────────────────────────────────────
    "polycube":         ["box"],
    "polysphere":       ["sphere"],
    "polycylinder":     ["tube"],
    "polyplane":        ["grid"],
    "polytorus":        ["torus"],
    "polycone":         ["tube"],
    "nurbssphere":      ["sphere"],
    "nurbscube":        ["box"],
    "deform":           ["bend", "twist", "lattice"],
    "nonlinear":        ["bend", "twist"],
    "cluster":          ["softpeak"],
    "wrap deformer":    ["lattice"],
    "blend shape":      ["blendshapes"],
    "mash":             ["copytopoints", "scatter"],
    "duplicator":       ["copytopoints"],
    "paint effects":    ["attribpaint"],
    "nparticles":       ["popnet"],
    "ncloth":           ["vellumcloth"],
    "bifrost":          ["flipsource"],
    "groupid":          ["group"],
    "sets":             ["group"],

    # ─────────────────────────────────────────────────────────
    # 3DS MAX TERMS
    # ─────────────────────────────────────────────────────────
    "editable poly":    ["box"],
    "editable mesh":    ["box"],
    "edit poly":        ["box"],
    "chamfer modifier": ["polybevel"],
    "turbosmooth":      ["subdivide"],
    "meshsmooth":       ["subdivide"],
    "shell":            ["polyextrude"],
    "symmetry modifier": ["mirror"],
    "noise modifier":   ["mountain", "attribnoise"],
    "particle flow":    ["popnet"],
    "pflow":            ["popnet"],
    "tyflow":           ["popnet"],
    "thinking particles": ["popnet"],
    "phoenixfd":        ["pyrosolver", "flipsource"],
    "space warp":       ["popforce"],
    "scatter modifier": ["scatter"],
    "boolean modifier": ["boolean"],
    "proboolean":       ["boolean"],
    "slice modifier":   ["clip"],
    "xform":            ["transform"],
    "gizmo":            ["transform", "null"],
    "transform":        ["xform", "transform"], # Standard Houdini name mapping
    "geometry":         ["geo"],                # Standard Houdini name mapping
    "geo":              ["geo"],
    "copernicus":       ["copnet", "cop2net"],  # H21 features

    # ─────────────────────────────────────────────────────────
    # COMPOSITING / COPERNICUS TERMS (Nuke, AE, Substance)
    # ─────────────────────────────────────────────────────────
    "keyer":            ["chromakey"],
    "keying":           ["chromakey"],
    "green screen":     ["chromakey"],
    "levels":           ["colorcorrect", "equalize"],
    "curves tool":      ["colorcorrect", "remap"],
    "color correction": ["colorcorrect"],
    "grade":            ["colorcorrect", "bright", "contrast"],
    "exposure":         ["bright"],
    "saturation":       ["hsv", "colorcorrect"],
    "hue":              ["hsv"],
    "denoise":          ["denoiseai", "denoisetvd"],
    "roto":             ["maskfromcurves", "rasterizecurves"],
    "matte":            ["idtomask", "chromakey"],
    "grain":            ["fractalnoise", "randommono"],
    "noise texture":    ["fractalnoise", "worleynoise", "phasornoise"],
    "voronoi noise":    ["worleynoise"],
    "cellular noise":   ["worleynoise"],
    "transform 2d":     ["xform2d", "xform"],
    "corner pin":       ["cornerpin"],
    "lens blur":        ["bokeh", "defocus"],
    "motion blur":      ["streakblur"],
    "unpremult":        ["premult"],
    "merge comp":       ["layer", "blend"],
    "over":             ["layer", "blend"],
    "screen blend":     ["layer", "blend"],
    "normal map":       ["heighttonormal", "convertnormal"],
    "ambient occlusion": ["heighttoambientocclusion"],
    "height map":       ["heighttonormal", "heightfield"],
    "sdf":              ["sdfshape", "monotosdf", "idtosdf"],
    "machine learning": ["onnx", "denoiseai"],
    "ml":               ["onnx"],

    # ─────────────────────────────────────────────────────────
    # AFTER EFFECTS TERMS (motion design vocabulary)
    # ─────────────────────────────────────────────────────────
    "fractal noise":    ["fractalnoise", "phasornoise", "attribnoise"],
    "turbulent noise":  ["fractalnoise", "phasornoise"],
    "turbulent displace": ["distort", "displace", "mountain"],
    "displacement map": ["displace", "distort", "heighttonormal"],
    "wiggle":           ["attribnoise", "noise", "jitter"],
    "echo":             ["trail", "timeblend"],
    "glow":             ["bloom", "glow"],
    "tint":             ["tint", "colorcorrect", "hueshift"],
    "curves":           ["remap", "colorcorrect"],
    "hue saturation":   ["hsv", "colorcorrect"],
    "drop shadow":      ["dropshadow", "shadow"],
    "gaussian blur":    ["blur"],
    "directional blur": ["streakblur", "blur"],
    "radial blur":      ["radialblur", "streakblur"],
    "vignette":         ["vignette"],
    "chromatic aberration": ["chromaticaberration", "lensdistort"],
    "lens distortion":  ["lensdistort"],
    "posterize":        ["quantize", "posterize"],
    "threshold":        ["threshold", "clamp"],
    "invert":           ["invert", "reverse"],
    "solid":            ["constant", "color"],
    "adjustment layer": ["colorcorrect"],
    "precomp":          ["subnet", "null"],
    "time remap":       ["timeshift", "retime"],
    "speed ramp":       ["retime", "timeshift"],
    "luma key":         ["lumakey", "chromakey"],
    "track matte":      ["layer", "premult", "idtomask"],
    "stroke":           ["trace", "rasterizecurves", "polywire"],

    # ─────────────────────────────────────────────────────────
    # HOUDINI 21 COPERNICUS / MOGRAPH TERMS
    # ─────────────────────────────────────────────────────────
    "flow":             ["flowsolver", "flow"],
    "fluid 2d":         ["flowsolver"],
    "smoke 2d":         ["flowsolver", "pyrosolver"],
    "reaction diffusion": ["reactiondiffusion"],
    "scatter stamps":   ["scattershapes"],
    "stamp":            ["scattershapes", "copytopoints"],
    "grunge":           ["grungemap", "grunge"],
    "live video":       ["video", "livevideo", "webcam"],
    "phasor":           ["phasornoise"],
    "bubble noise":     ["bubblenoise"],
    "cables":           ["cables"],
    "braid":            ["cables"],

    # ─────────────────────────────────────────────────────────
    # SOLARIS / USD TERMS
    # ─────────────────────────────────────────────────────────
    "usd import":       ["sceneimport", "sopimport", "reference"],
    "usd export":       ["usd_rop", "usdrender_rop"],
    "render settings usd": ["karmarendersettings", "rendersettings"],
    "look dev":         ["materiallibrary", "assignmaterial"],
    "shot":             ["shotload", "shotoutput"],
}

# Backwards-compatible name (pre-overhaul scripts imported C4D_MAPPINGS)
C4D_MAPPINGS = ALIASES


class AliasHit(object):
    """One alias match: the term that matched and how well it matched.

    tier: 0 = exact term ("cloner" == "cloner")
          1 = prefix / word-boundary prefix ("clon", "plain eff")
          2 = containment either way
          3 = ordered subsequence (typo tolerance, e.g. "clner")
    """

    __slots__ = ("term", "tier")

    def __init__(self, term, tier):
        self.term = term
        self.tier = tier

    def __repr__(self):
        return "AliasHit(%r, %d)" % (self.term, self.tier)


def get_mapped_nodes(search_query):
    """
    Returns a list of Houdini base node names for an exact alias term.
    Checking is case-insensitive.
    """
    query = search_query.lower().strip()
    return ALIASES.get(query, [])


def _match_tier(term, query):
    """How well does an alias term match the query? None when it doesn't."""
    if term == query:
        return 0
    if term.startswith(query):
        return 1
    # word-boundary prefix: "effector" matches "plain effector"
    if any(word.startswith(query) for word in term.split()):
        return 1
    if len(query) >= 3 and query in term:
        return 2
    if len(term) >= 3 and term in query:
        return 2
    # Typo tolerance: ordered subsequence for queries of 5+ chars
    # ("clner" -> "cloner"), gap-limited so it stays meaningful. Short
    # queries are excluded: "cone" is a subsequence of "cloner" and must
    # NOT drag clone nodes into a primitive search.
    if len(query) >= 5:
        from . import fuzzy
        sub = fuzzy.subsequence_positions(query, term)
        if sub is not None and sub[1] <= 2:
            return 3
    return None


def alias_hits_for_query(query):
    """
    Fuzzy alias lookup for the search panel.

    Returns {base_node_name: AliasHit} for every alias term matching the
    query. When several terms map to the same node, the best tier wins.
    """
    query = query.lower().strip()
    if len(query) < 2:
        return {}

    hits = {}
    for term, node_names in ALIASES.items():
        tier = _match_tier(term, query)
        if tier is None:
            continue
        for node_name in node_names:
            current = hits.get(node_name)
            if current is None or tier < current.tier:
                hits[node_name] = AliasHit(term, tier)
    return hits
