
import hou

def print_selection_type():
    sel = hou.selectedNodes()
    if not sel:
        print("No selection")
        return
    
    for node in sel:
        print(f"Node: {node.name()}")
        print(f"Type Name: {node.type().name()}")
        print(f"Type Category: {node.type().category().name()}")
        print("-" * 20)

print_selection_type()
