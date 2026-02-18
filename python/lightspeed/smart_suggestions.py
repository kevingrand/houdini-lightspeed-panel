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
    "box": ["transform", "groupcreate", "color", "null", "labs::axis_align", "matchsize", "polyextrude", "polybevel"],
    "sphere": ["transform", "null", "matchsize", "polybevel"],
    "tube": ["transform", "polycap", "polybevel"],
    "grid": ["mountain", "polyextrude", "uvptexture"],
    "torus": ["transform"],
    
    # Curves
    "curve": ["resample", "sweep", "carve", "polywire", "labs::curve_branches"],
    "line": ["resample", "sweep", "copytopoints"],
    "drawcurve": ["resample", "sweep"],
    
    # Attributes/VEX
    "attribwrangle": ["attribpromote", "attribcopy", "blast", "grouppromote", "null"],
    "attribcreate": ["attribwrangle", "null"],
    
    # Volumes
    "vdbfrompolygons": ["vdbreshape", "vdbsmooth", "vdbcombine", "convertvdb"],
    "isooffset": ["convert", "vdbfrompolygons"],
    
    # Common SOPs
    "transform": ["null", "merge", "copytopoints"],
    "merge": ["null", "output"],
    "file": ["null", "unpack", "convert"],
    "object_merge": ["transform", "null"],
    "null": ["merge", "output"]
}

def get_suggestions(node_type_name):
    """
    Returns a list of suggested node type names for a given input node type.
    """
    if not node_type_name:
        return []
    return SMART_MAP.get(node_type_name.lower(), [])

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
