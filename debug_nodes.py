
import hou

try:
    print("Fetching SOPs...")
    sop_category = hou.nodeTypeCategories().get('Sop')
    if sop_category:
        all_sops = sop_category.nodeTypes().values()
        
        # Filter for the problematic ones
        bad_nodes = [n for n in all_sops if 'rbdmaterialfracture' in n.name() or 'musclerig' in n.name()]
        
        print(f"Found {len(bad_nodes)} suspicious nodes.")
        
        for n in bad_nodes:
            print(f"--- Node: {n.name()} ---")
            print(f"  Hidden: {n.hidden()}")
            print(f"  Deprecated: {n.deprecated()}")
            print(f"  Category Name: {n.category().name()}")
            # Check if name contains namespace
            print(f"  Namespace: {n.nameWithCategory()}")
            
    else:
        print("Sop category not found.")

except Exception as e:
    print(f"Error: {e}")
