"""
smart_suggestions.py
--------------------
Handles logic for predicting useful next nodes based on current selection.
"""

import hou

# Dictionary mapping node type names to list of suggested next nodes
# Keys should be all lowercase
SMART_MAP = {
    # Base Geo
    "geo": ["file", "object_merge", "null"],
    "box": ["xform", "polybevel", "polyextrude", "clip", "mirror", "remesh", "normal", "null", "matchsize", "labs::axis_align"],
    "sphere": ["xform", "polybevel", "clip", "mirror", "remesh", "normal", "null", "matchsize"],
    "tube": ["xform", "polycap", "polybevel", "clip", "mirror", "remesh", "normal", "null"],
    "grid": ["xform", "mountain", "polyextrude", "uvptexture", "scatter", "null"],
    "torus": ["xform", "polybevel", "null"],
    
    # Curves
    "curve": ["resample", "sweep", "carve", "polywire", "labs::curve_branches", "xform", "null", "rigdoctor"],
    "line": ["resample", "sweep", "copytopoints", "xform", "null", "rigdoctor"],
    "drawcurve": ["resample", "sweep", "xform", "null", "rigdoctor"],
    
    # Attributes/VEX
    "attribwrangle": ["attribpromote", "attribcopy", "blast", "grouppromote", "null", "filecache"],
    "attribcreate": ["attribwrangle", "null"],
    "attribrandomize": ["copytopoints", "null"],
    "scatter": ["copytopoints", "attribrandomize", "attribnoise", "null"],
    "copytopoints": ["filecache", "null", "merge"],
    
    # Volumes
    "vdbfrompolygons": ["vdbreshape", "vdbsmooth", "vdbcombine", "convertvdb", "filecache"],
    "isooffset": ["convert", "vdbfrompolygons", "filecache"],
    
    # Common SOPs
    "xform": ["null", "merge", "copytopoints", "mirror", "clip"],
    "transform": ["null", "merge", "copytopoints"], # Keep just in case
    "merge": ["null", "output", "filecache"],
    "file": ["null", "unpack", "convert", "xform"],
    "object_merge": ["xform", "null", "blast"],
    "null": ["merge", "output", "xform"],
    "boolean": ["remesh", "normal", "null"],
    
    # Simulation
    "dopnet": ["filecache", "null"],
    "popnet": ["filecache", "null"],
    "vellumsolver": ["filecache", "null"],

    # KineFX / Rigging / APEX
    "resample": ["rigdoctor", "orientjoints", "rigvisualize", "null"],
    "rigdoctor": ["rigpose", "skeletonblend", "ikchains", "kinefx::fbik", "jointcapturebiharmonic", "visualize"],
    "skeleton": ["rigdoctor", "rigpose", "apex::packcharacter", "apex::autorigcomponent"],
    
    # IK & Constraints
    "ikchains": ["rigpose", "skeletonblend", "null"],
    "kinefx::fbik": ["rigpose", "null"],
    "configurejoints": ["kinefx::fbik", "null"],
    
    # Skinning
    "jointcapturebiharmonic": ["bonedeform", "deltamush", "null"],
    "capturegeoproximity": ["bonedeform", "null"],
    "bonedeform": ["null"],
    "rigpose": ["jointcapturebiharmonic", "bonedeform", "kinefx::motionmixer", "skeletonblend"],
    
    # APEX (H21)
    "apex::autorigcomponent": ["apex::sceneanimate", "null"],
    "apex::sceneanimate": ["null"],
}

def get_suggestions(node_type_name):
    """
    Returns a list of suggested node type names for a given input node type.
    Handles versioned/namespaced nodes (e.g. 'curve::2.0' -> 'curve').
    """
    if not node_type_name:
        return []
    
    name = node_type_name.lower()
    
    # 1. Try exact match first
    suggestions = SMART_MAP.get(name)
    if suggestions:
        return suggestions
        
    # 2. Robust Namespace/Version Stripping
    if "::" in name:
        parts = name.split("::")
        
        # Common patterns:
        # "node::2.0" -> parts=["node", "2.0"] -> want "node"
        # "namespace::node" -> parts=["namespace", "node"] -> want "node"
        # "namespace::node::2.0" -> parts=["namespace", "node", "2.0"] -> want "node"
        
        potential_keys = []
        
        # A) Last part (if not version)
        if not parts[-1].replace('.', '').isdigit():
            potential_keys.append(parts[-1])
            
        # B) Second to last part (if last is version)
        if len(parts) > 1:
            # If last part IS a version, take the one before it
            if parts[-1].replace('.', '').isdigit():
                potential_keys.append(parts[-2])
                
        # C) First part (fallback for "curve::2.0")
        potential_keys.append(parts[0])
        
        # Try all potential keys in order
        for key in potential_keys:
            suggestions = SMART_MAP.get(key)
            if suggestions:
                return suggestions

    return []

def get_smart_context(selected_nodes):
    """
    Analyzes the selected nodes to determine the 'leaf' node type 
    that should drive the suggestions.
    
    Args:
        selected_nodes (tuple/list of hou.Node): The current selection.
        
    Returns:
        str or None: The node type name of the leaf node, or None if context is ambiguous.
    """
    if not selected_nodes:
        return None
        
    # Case 1: Single Node
    if len(selected_nodes) == 1:
        return selected_nodes[0].type().name()
        
    # Case 2: Multi-Node Chain Logic
    # We want to find the node(s) in the selection that do NOT output to 
    # any other node IN THE SELECTION.
    
    sel_set = set(selected_nodes)
    leaves = []
    
    for node in selected_nodes:
        is_leaf = True
        # Check all outputs of this node
        for output_node in node.outputs():
            if output_node in sel_set:
                # This node feeds into another selected node, so it's not the leaf
                is_leaf = False
                break
        
        if is_leaf:
            leaves.append(node)
            
    # Logic:
    # If exactly 1 leaf, we have a clear "end of chain".
    # If > 1 leaf, we have disconnected, parallel chains (e.g. two separate boxes selected).
    # The user requested to return None in parallel/ambiguous cases.
    
    if len(leaves) == 1:
        return leaves[0].type().name()
    
    return None
