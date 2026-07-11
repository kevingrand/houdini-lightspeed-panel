"""
smart_suggestions.py
--------------------
Backwards-compatibility shim. Suggestion logic moved to `suggestions.py`,
which adds learned (usage-based) recommendations on top of curated maps
covering SOPs, COPs (Copernicus), LOPs, DOPs, OBJ, TOPs and ROPs.
"""

from .suggestions import SuggestionEngine, leaf_type_name, CURATED

# Old API names
get_smart_context = leaf_type_name


def get_suggestions(node_type_name, category_name="Sop"):
    """Old signature: suggestions for a node type (SOP-centric)."""
    engine = SuggestionEngine()
    return engine.suggestions(category_name, node_type_name)


SMART_MAP = CURATED.get("Sop", {})
