"""
launcher.py
-----------
A helper script to run the Lightspeed Panel from the Houdini Python Source Editor or a Shelf Tool.
"""
import sys
import os
import hou

# 1. Ensure the package is in sys.path
# CHANGE THIS PATH to matches where you cloned the repo/saved the files
REPO_PATH = r"e:\DEV LOCAL\Houdini Lightspeed Panel\python"

if REPO_PATH not in sys.path:
    sys.path.append(REPO_PATH)

# 2. Import the module
import lightspeed.qt_utils as lqt
import lightspeed.favorites as lfav
import lightspeed.smart_suggestions as lsmart
import lightspeed.gallery_ui as lg
import importlib

# 3. Reload for development (so you can edit code and re-run without restarting Houdini)
importlib.reload(lqt)
importlib.reload(lfav)
importlib.reload(lsmart)
importlib.reload(lg)

# 4. Create and show the dialog
# Passing hou.ui.mainQtWindow() ensures it stays on top of Houdini properly
# 4. Create and show the dialog
# Passing hou.ui.mainQtWindow() ensures it stays on top of Houdini properly
def run():
    # TEST FAVORITES (Phase 2)
    import lightspeed.favorites as lf
    importlib.reload(lf)
    
    fav_mgr = lf.FavoritesManager()
    print(f"Lightspeed Favorites Path: {fav_mgr.file_path}")
    
    # Add a dummy favorite to test basic logic
    fav_mgr.add_favorite("Sop", "box")
    fav_mgr.add_favorite("Sop", "sphere")
    print(f"Current SOP Favorites: {fav_mgr.get_favorites('Sop')}")
    
    # Use global to prevent garbage collection
    global lightspeed_dlg 
    
    lightspeed_dlg = lg.LightspeedGallery(parent=hou.ui.mainQtWindow())
    lightspeed_dlg.show()

run()
