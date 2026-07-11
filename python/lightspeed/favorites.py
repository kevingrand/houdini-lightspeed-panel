"""
favorites.py
------------
Context-specific node favorites, persisted to the same JSON file as previous
versions (custom_tab_favorites.json in $HOUDINI_USER_PREF_DIR) so existing
favorites survive the overhaul.
"""

from . import store

FAVORITES_FILE = "custom_tab_favorites.json"


class FavoritesManager(object):
    def __init__(self):
        data = store.load_json(FAVORITES_FILE, {})
        # Harden against hand-edited/corrupt files: keep only str->list[str]
        self.favorites = {}
        if isinstance(data, dict):
            for context, names in data.items():
                if isinstance(names, list):
                    self.favorites[str(context)] = [str(n) for n in names]

    def save(self):
        store.save_json(FAVORITES_FILE, self.favorites)

    def get_favorites(self, context_name):
        return list(self.favorites.get(context_name, []))

    def is_favorite(self, context_name, node_type_name):
        return node_type_name in self.favorites.get(context_name, [])

    def add_favorite(self, context_name, node_type_name):
        names = self.favorites.setdefault(context_name, [])
        if node_type_name not in names:
            names.append(node_type_name)
            self.save()

    def remove_favorite(self, context_name, node_type_name):
        names = self.favorites.get(context_name)
        if names and node_type_name in names:
            names.remove(node_type_name)
            if not names:
                del self.favorites[context_name]
            self.save()

    def toggle(self, context_name, node_type_name):
        """Returns True if the node is a favorite after the toggle."""
        if self.is_favorite(context_name, node_type_name):
            self.remove_favorite(context_name, node_type_name)
            return False
        self.add_favorite(context_name, node_type_name)
        return True

    def update_favorites_order(self, context_name, new_list):
        if new_list:
            self.favorites[context_name] = list(new_list)
        else:
            self.favorites.pop(context_name, None)
        self.save()
