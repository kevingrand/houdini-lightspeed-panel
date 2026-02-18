"""
favorites.py
------------
Handles loading and saving of context-specific node favorites.
Data is persisted to a JSON file in the user's Houdini preferences directory.
"""

import hou
import os
import json

class FavoritesManager:
    def __init__(self):
        # Resolve the path to the user's local preference directory
        # usually Documents/houdiniX.X/
        self.pref_dir = hou.homeHoudiniDirectory()
        self.file_path = os.path.join(self.pref_dir, "custom_tab_favorites.json")
        
        # Internal cache of favorites
        self.favorites = {}
        
        # Load immediately upon instantiation
        self.load()

    def load(self):
        """
        Loads the favorites from the JSON file.
        If file doesn't exist, initializes an empty dictionary.
        """
        if not os.path.exists(self.file_path):
            self.favorites = {}
            return

        try:
            with open(self.file_path, 'r') as f:
                self.favorites = json.load(f)
        except (ValueError, IOError) as e:
            print(f"Lightspeed Error loading favorites: {e}")
            self.favorites = {}

    def save(self):
        """
        Saves the current favorites to the JSON file.
        """
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.favorites, f, indent=4)
        except IOError as e:
            print(f"Lightspeed Error saving favorites: {e}")

    def get_favorites(self, context_name):
        """
        Returns a list of favorite node type names for the given context.
        Example context_name: 'Sop', 'Dop', 'Object'
        """
        return self.favorites.get(context_name, [])

    def add_favorite(self, context_name, node_type_name):
        """
        Adds a node type to the favorites for the given context.
        Saves immediately.
        """
        if context_name not in self.favorites:
            self.favorites[context_name] = []
            
        if node_type_name not in self.favorites[context_name]:
            self.favorites[context_name].append(node_type_name)
            self.save()

    def remove_favorite(self, context_name, node_type_name):
        """
        Removes a node type from the favorites for a given context.
        Saves immediately.
        """
        if context_name in self.favorites:
            if node_type_name in self.favorites[context_name]:
                self.favorites[context_name].remove(node_type_name)
                # Cleanup empty contexts if desired, though not strictly necessary
                if not self.favorites[context_name]:
                    del self.favorites[context_name]
                self.save()
    def update_favorites_order(self, context_name, new_list):
        """
        Updates the entire list for a context (e.g. after reordering).
        """
        if context_name in self.favorites:
            self.favorites[context_name] = new_list
            self.save()
