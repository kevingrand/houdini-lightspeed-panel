
"""
search_mappings.py
------------------
Maps terminology from other 3D software (Cinema 4D, Blender, Maya, 3ds Max)
to Houdini node types. This allows users to search using familiar terms
from their previous software and find the correct Houdini equivalent.

e.g. "Cube" → "Box", "Cloner" → "copytopoints", "Lattice" → "lattice"
"""

# Key = Search Term (lowercase)
# Value = List of Houdini Node Type Names (lowercase) to suggest

C4D_MAPPINGS = {

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
    "text":             ["font"],
    "motext":           ["font"],
    "formula spline":   ["curve"],

    # ─────────────────────────────────────────────────────────
    # MOGRAPH / INSTANCING / SCATTERING
    # ─────────────────────────────────────────────────────────
    "cloner":           ["copytopoints", "copyandtransform"],
    "clone":            ["copytopoints", "copyandtransform"],
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
    "effector":         ["attribwrangle", "attribrandomize"],
    "plain effector":   ["transform", "attribwrangle"],
    "random effector":  ["attribrandomize"],
    "shader effector":  ["attribfrommap"],
    "delay effector":   ["timeshift", "trail"],
    "formula effector": ["attribwrangle"],
    "step effector":    ["attribwrangle", "sort"],
    "target effector":  ["lookat"],
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
}


def get_mapped_nodes(search_query):
    """
    Returns a list of Houdini node types associated with the search query.
    Checking is case-insensitive.
    """
    query = search_query.lower().strip()
    return C4D_MAPPINGS.get(query, [])
