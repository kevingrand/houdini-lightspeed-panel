"""
gallery_ui.py
-------------
The main entry point for the Lightspeed Panel UI.
Creates a frameless, floating dialog that allows searching and creating nodes.
"""

import hou
from . import qt_utils
from . import favorites

from . import smart_suggestions
from . import search_mappings

# Unpack Qt modules for easy access
QtWidgets = qt_utils.QtWidgets
QtCore = qt_utils.QtCore
QtGui = qt_utils.QtGui

class LightspeedGallery(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(LightspeedGallery, self).__init__(parent)
        
        # 1. Capture Context & Position & Selection
        self.network_editor = None
        self.cursor_pos = hou.Vector2(0, 0)
        self.current_context_name = None
        self.selected_nodes = []
        
        self._capture_context()
        
        # 2. Window Flags (Frameless + Popup)
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        
        # 3. Data Initialization
        self.fav_manager = favorites.FavoritesManager()
        self.all_node_types = [] 
        self._init_node_data()
        
        # 3b. Smart Suggestions calculation
        self.smart_type = smart_suggestions.get_smart_context(self.selected_nodes)
        self.suggestions = smart_suggestions.get_suggestions(self.smart_type)
        

        
        # 4. UI Build
        self.init_ui()
        
        # 5. Populate
        self.populate_favorites()
        self.update_results("") 
        
        # 6. Position and Focus
        self.move_to_cursor()
        
    def showEvent(self, event):
        super(LightspeedGallery, self).showEvent(event)
        self.search_bar.setFocus()
        
    def _capture_context(self):
        global_selection = hou.selectedNodes()
        
        self.network_editor = None
        self.cursor_pos = hou.Vector2(0, 0)
        
        # STRATEGY A: We have selected nodes. Use them to drive Context.
        if global_selection:
            self.selected_nodes = global_selection
            # context from first node (e.g. 'Sop', 'Object')
            self.current_context_name = self.selected_nodes[0].type().category().name()
            
            # Now find a Network Editor that is looking at this location
            # so we can get a valid cursor position for creation.
            parent_path = self.selected_nodes[0].parent().path()
            
            for pane in hou.ui.paneTabs():
                if isinstance(pane, hou.NetworkEditor) and pane.isCurrentTab():
                    if pane.pwd().path() == parent_path:
                        self.network_editor = pane
                        break
            
            # If we didn't find the exact pane, just grab any network editor
            if not self.network_editor:
                candidates = [p for p in hou.ui.paneTabs() if isinstance(p, hou.NetworkEditor) and p.isCurrentTab()]
                if candidates:
                    self.network_editor = candidates[0]

        # STRATEGY B: No selection. Rely on Cursor / Active Pane.
        else:
            self.selected_nodes = []
            
            # 1. Try Cursor
            pane = hou.ui.paneTabUnderCursor()
            
            # 2. Fallback Search
            if not pane or not isinstance(pane, hou.NetworkEditor):
                candidates = [p for p in hou.ui.paneTabs() if isinstance(p, hou.NetworkEditor) and p.isCurrentTab()]
                if candidates:
                    pane = candidates[0]
            
            self.network_editor = pane
            if self.network_editor:
                try:
                    self.current_context_name = self.network_editor.pwd().childTypeCategory().name()
                except:
                    self.current_context_name = None

        # FINAL: Get Cursor Position from the identified editor
        if self.network_editor:
            try:
                self.cursor_pos = self.network_editor.cursorPosition()
            except:
                pass
        else:
             # Last ditch: Default context if everything fails (e.g. Object)
             if not self.current_context_name:
                 self.current_context_name = "Object"

    def _init_node_data(self):
        if not self.current_context_name:
            return
        try:
            category = hou.nodeTypeCategories().get(self.current_context_name)
            if category:
                # Filter out hidden and deprecated nodes
                valid_types = []
                for n in category.nodeTypes().values():
                    if n.hidden():
                        continue
                    if n.deprecated():
                        continue
                    # Phase 9 Fix: Filter out internal/namespaced nodes containing "/"
                    # e.g. "Sop/rbdmaterialfracture..." or "Object/musclerig..."
                    if "/" in n.name():
                        continue
                        
                    valid_types.append(n)
                
                self.all_node_types = sorted(valid_types, key=lambda n: n.name())
        except Exception as e:
            pass


        
    def init_ui(self):
        # --- STYLESHEET (Dark Mode) ---
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                border: 2px solid #444;
                border-radius: 6px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
                selection-background-color: #d65d00;
            }
            QLabel {
                color: #888;
                font-weight: bold;
                font-size: 11px;
                margin-top: 8px;
                margin-bottom: 4px;
            }
            QListWidget {
                background-color: #232323;
                border: 1px solid #333;
                border-radius: 4px;
                outline: 0;
            }
            QListWidget::item {
                color: #cccccc;
                padding: 6px;
                border-radius: 3px;
                border-bottom: 1px solid #2a2a2a; 
            }
            QListWidget::item:selected {
                background-color: #d65d00;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #383838;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # --- QUICK ACTIONS (Phase 9) ---
        self.init_quick_actions(layout)
        
        # --- SEARCH BAR ---
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText(f"Search {self.current_context_name or 'Nodes'}...")
        self.search_bar.textChanged.connect(self.update_results)
        self.search_bar.returnPressed.connect(self.on_return_pressed)
        layout.addWidget(self.search_bar)
        
        # --- FAVORITES AREA ---
        if self.current_context_name:
            lbl_fav = QtWidgets.QLabel("FAVORITES")
            layout.addWidget(lbl_fav)
            
            self.fav_list = QtWidgets.QListWidget()
            self.fav_list.setViewMode(QtWidgets.QListWidget.IconMode)
            self.fav_list.setResizeMode(QtWidgets.QListWidget.Adjust)
            self.fav_list.setWordWrap(True)
            self.fav_list.setSpacing(4)
            self.fav_list.setFixedHeight(85)
            self.fav_list.setIconSize(QtCore.QSize(32, 32))
            
            # Drag & Drop Reordering
            self.fav_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
            self.fav_list.setDefaultDropAction(QtCore.Qt.MoveAction)
            
            # Interaction
            self.fav_list.itemClicked.connect(self.on_item_clicked)
            
            # Context Menu (Remove)
            self.fav_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.fav_list.customContextMenuRequested.connect(self.show_fav_context_menu)
            
            # Connect reorder signal (PySide6)
            self.fav_list.model().rowsMoved.connect(self.on_favorites_reordered)
            
            layout.addWidget(self.fav_list)
        else:
            self.fav_list = None

        # --- RESULTS AREA ---
        lbl_res = QtWidgets.QLabel("NODES")
        layout.addWidget(lbl_res)
        
        self.results_list = QtWidgets.QListWidget()
        self.results_list.setIconSize(QtCore.QSize(24, 24)) 
        
        # Interaction & Context Menu
        self.results_list.itemClicked.connect(self.on_item_clicked)
        self.results_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.results_list)
        
        self.setLayout(layout)
        self.resize(350, 550) # Taller to show more results

    # --- POPULATION METHODS ---

    def populate_favorites(self):
        if not self.fav_list or not self.current_context_name:
            return
            
        self.fav_list.clear() # Clears items (and safe deletion handled by Qt)
        fav_names = self.fav_manager.get_favorites(self.current_context_name)
        
        type_map = {t.name(): t for t in self.all_node_types}
        
        for name in fav_names:
            node_type = type_map.get(name)
            
            # Truncate label if > 4 chars (e.g. "sphere" -> "sphe..")
            # The full name is shown in the tooltip.
            display_name = name
            if len(name) > 4:
                display_name = name[:4] + ".."
            
            if node_type:
                icon = self._get_qt_icon(node_type)
                item = QtWidgets.QListWidgetItem(icon, display_name)
                item.setToolTip(name)
                # Ensure we store the cleanup name just in case
                item.setData(QtCore.Qt.UserRole, name)
                self.fav_list.addItem(item)
            else:
                item = QtWidgets.QListWidgetItem(display_name)
                item.setToolTip(name)
                item.setData(QtCore.Qt.UserRole, name)
                self.fav_list.addItem(item)

    def update_results(self, text):
        self.results_list.clear()
        search_term = text.lower().strip()
        
        # Helper to strip namespaces (e.g. kinefx::rigdoctor -> rigdoctor, curve::2.0 -> curve)
        def get_base_name(full_name):
            if "::" in full_name:
                parts = full_name.split("::")
                # If last part is version, take 2nd to last, else take last
                if parts[-1].replace('.', '').isdigit() and len(parts) > 1:
                    return parts[-2]
                return parts[-1] 
            return full_name

        # 1. Standard Filtering (Name AND Label/Description)
        # We collect tuples of (node_type, match_type_score)
        # Scores: 0=Exact, 1=StartsWith, 2=Contains
        matches = []
        matched_names = set()
        
        for node_type in self.all_node_types:
            name = node_type.name()
            label = node_type.description()
            base_name = get_base_name(name)
            
            name_lower = name.lower()
            label_lower = label.lower()
            
            score = 100 # Default no match
            
            if not search_term:
                score = 5 # Just show everything
            elif search_term == name_lower or search_term == label_lower or search_term == base_name.lower():
                score = 0 # Exact Match
            elif name_lower.startswith(search_term) or label_lower.startswith(search_term) or base_name.lower().startswith(search_term):
                score = 1 # Starts With
            elif search_term in name_lower or search_term in label_lower:
                score = 2 # Contains
            
            if score < 100:
                matches.append((node_type, score))
                matched_names.add(name)
        
        # 2. Alias / Mapping Lookup (C4D -> Houdini terms)
        alias_source = {}  # maps houdini_name -> c4d_term
        if search_term:
            type_map = {t.name(): t for t in self.all_node_types}
            for alias_key, houdini_names in search_mappings.C4D_MAPPINGS.items():
                if search_term in alias_key or alias_key in search_term:
                    for mname in houdini_names:
                        if mname not in matched_names and mname in type_map:
                            matches.append((type_map[mname], 3)) # Score 3 for Alias
                            matched_names.add(mname)
                            alias_source[mname] = alias_key
        
        # 3. Sorting Logic
        # Suggestions get a boost. 
        # But EXACT matches should usually beat suggestions? 
        # Actually user wants "Line" to show up first if they type "Line".
        # So Exact Match > Suggestion ? Or Suggestion > Exact Match?
        # If I type "Line", and "Line" is a suggestion, it wins double.
        # If I type "Line", and "Line" is NOT a suggestion, it should still be top.
        
        suggested_set = set(self.suggestions) if self.suggestions else set()
        
        def sort_key(item):
            node_type, score = item
            name = node_type.name()
            base_name = get_base_name(name)
            
            # Check if suggested (robustly)
            is_suggested = (name in suggested_set) or (base_name in suggested_set)
            
            # Primary Sort: Score (Exact=0, StartsWith=1, Contains=2, Alias=3)
            # Secondary Sort: Suggestion (-1 if suggested, 0 if not) - gives boost within same score tier? 
            # actually, if we want suggestions to float to top when NO search, 
            # but Exact Match to win when SEARCHING.
            
            # If searching:
            if search_term:
                # Priority: 
                # 1. Exact Match (Score 0)
                # 2. Starts With (Score 1) + Suggested
                # 3. Starts With (Score 1)
                # 4. Alias (Score 3)
                # 5. Contains (Score 2) - wait alias is better than arbitrary contains? Unsure.
                
                # Let's simple tuple sort:
                # (Score, NotSuggested, NameLength)
                # Lower score is better. 
                # If tied on score, Suggested (True) is better than NotSuggested (False).
                
                return (score, not is_suggested, len(name), name)
            else:
                # If NOT searching (empty text):
                # Suggestions FIRST.
                return (not is_suggested, name)

        matches.sort(key=sort_key)

        # 4. Populate List (limit to top 100)
        displayed_matches = matches[:100]
        
        for node_type, score in displayed_matches:
            name = node_type.name()
            base_name = get_base_name(name)
            is_suggested = (name in suggested_set) or (base_name in suggested_set)
            
            # Label
            text = f"{node_type.description()} ({name})"
            
            # Icon
            try:
                icon = hou.qt.createIcon(node_type.icon())
            except:
                icon = QtGui.QIcon()
            
            item_widget = QtWidgets.QListWidgetItem(icon, text)
            item_widget.setData(QtCore.Qt.UserRole, node_type.name())
            
            # Highlight Suggestions
            if is_suggested:
                # Blue-ish bold text for suggestions
                font = item_widget.font()
                font.setBold(True)
                item_widget.setFont(font)
                item_widget.setBackground(QtGui.QBrush(QtGui.QColor("#2d4052"))) 
                item_widget.setForeground(QtGui.QBrush(QtGui.QColor("#ffffff")))
                item_widget.setToolTip(f"{name} (Suggested)")
            
            # Show Alias source if applicable
            if score == 3 and name in alias_source:
                original_term = alias_source[name]
                item_widget.setText(f"{text}  [Matches '{original_term}']")
                item_widget.setForeground(QtGui.QBrush(QtGui.QColor("#e6b44f"))) # Gold
                item_widget.setToolTip(f"{name} matches '{original_term}'")
                
            self.results_list.addItem(item_widget)
            
        if len(matches) > 100:
            info = QtWidgets.QListWidgetItem(f"... and {len(matches) - 100} more")
            info.setFlags(QtCore.Qt.NoItemFlags)
            self.results_list.addItem(info)

    def _get_qt_icon(self, node_type):
        try:
            return hou.qt.createIcon(node_type.icon())
        except:
            return QtGui.QIcon()

    def init_quick_actions(self, parent_layout):
        """Phase 9: Top row of quick action buttons"""
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setSpacing(6)
        
        # Helper to create styled buttons
        def make_btn(label, slot, tooltip):
            btn = QtWidgets.QPushButton(label)
            btn.setToolTip(tooltip)
            btn.clicked.connect(slot)
            # Make them look distinct (e.g. slightly darker/smaller)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #383838;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 4px 10px;
                    font-weight: bold;
                    color: #ddd;
                }
                QPushButton:hover {
                    background-color: #444;
                    border-color: #d65d00;
                }
            """)
            h_layout.addWidget(btn)
            return btn

        make_btn("MERGE", self.on_quick_merge, "Merge all selected nodes")
        make_btn("NULL OUT", self.on_quick_null, "Create OUT Null from last selected")
        make_btn("LAYOUT", self.on_quick_layout, "Auto-layout selected nodes")
        
        # Delete button — red accent on hover
        del_btn = make_btn("DELETE", self.on_quick_delete, "Delete selected node(s)")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #383838;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px 10px;
                font-weight: bold;
                color: #ddd;
            }
            QPushButton:hover {
                background-color: #4a2020;
                border-color: #cc3333;
                color: #ff6666;
            }
        """)
        
        h_layout.addStretch() # Push to left (or remove to center expand)
        parent_layout.addLayout(h_layout)

    def on_quick_merge(self):
        if not self.network_editor: return
        parent = self.network_editor.pwd()
        sel = self.selected_nodes
        if not sel: return

        try:
            merge = parent.createNode("merge")
            merge.setName("merge_selected", unique_name=True)
            
            # Wire ALL
            for i, node in enumerate(sel):
                merge.setInput(i, node)
                
            # Place below centroid
            sum_pos = hou.Vector2(0, 0)
            for n in sel: sum_pos += n.position()
            avg_pos = sum_pos / len(sel)
            merge.setPosition(avg_pos + hou.Vector2(0, -1.5))
            
            merge.setSelected(True, clear_all_selected=True)
            if self.network_editor is not None:
                self.network_editor.setCurrentNode(merge)
            merge.setDisplayFlag(True)
            merge.setRenderFlag(True)
            self.close()
        except Exception as e:
            pass

    def on_quick_null(self):
        if not self.network_editor: return
        parent = self.network_editor.pwd()
        sel = self.selected_nodes
        if not sel: return
        
        # Use LAST selected as the source
        source = sel[-1]
        
        try:
            null = parent.createNode("null")
            base_name = source.name().upper()
            # If name ends with digits, maybe strip them? Or just append.
            # User request: "last selected thing plus _OUT"
            null.setName(f"{base_name}_OUT", unique_name=True)
            
            # Color Black (0,0,0)
            null.setColor(hou.Color((0, 0, 0)))
            
            # Wire
            null.setInput(0, source)
            
            # Place
            null.setPosition(source.position() + hou.Vector2(0, -1.2))
            
            null.setSelected(True, clear_all_selected=True)
            if self.network_editor is not None:
                self.network_editor.setCurrentNode(null)
            # Usually OUT nulls are for display/export
            null.setDisplayFlag(True)
            null.setRenderFlag(True)
            
            self.close()
        except Exception as e:
            pass

    def on_quick_layout(self):
        if not self.network_editor: return
        parent = self.network_editor.pwd()
        
        # Layout SELECTED if implementation allows, else all?
        # hou.Node.layoutChildren(items=...) exists in newer Houdini?
        # Check docs or try/except. 
        # Usually it's parent.layoutChildren(self.selected_nodes)
        
        try:
            if self.selected_nodes:
                parent.layoutChildren(self.selected_nodes)
            else:
                # If nothing selected, layout everything? Or do nothing?
                # Safer to only do selection or prompt.
                # Let's do nothing if empty to be safe, or layout all?
                pass
                
            self.close() # Close after action?
        except Exception as e:
            pass

    def on_quick_delete(self):
        """Delete all selected nodes."""
        sel = self.selected_nodes
        if not sel:
            self.close()
            return

        try:
            for node in sel:
                node.destroy()
        except Exception as e:
            pass

        self.close()

    # --- INTERACTION & CREATION ---

    def on_favorites_reordered(self, parent, start, end, destination, row):
        # Gather new list from UI
        new_order = []
        for i in range(self.fav_list.count()):
            item = self.fav_list.item(i)
            name = item.data(QtCore.Qt.UserRole)
            if name:
                new_order.append(name)
        
        # Save to manager
        if self.current_context_name:
            self.fav_manager.update_favorites_order(self.current_context_name, new_order)
            
    def show_fav_context_menu(self, pos):
        item = self.fav_list.itemAt(pos)
        if not item: return
        
        node_name = item.data(QtCore.Qt.UserRole)
        
        menu = QtWidgets.QMenu(self)
        action = menu.addAction("Remove from Favorites")
        action.triggered.connect(lambda: self.toggle_favorite(node_name, remove=True))
        
        menu.exec_(self.fav_list.mapToGlobal(pos))

    def show_context_menu(self, pos):
        item = self.results_list.itemAt(pos)
        if not item:
            return
            
        node_name = item.data(QtCore.Qt.UserRole)
        if not node_name:
            return

        menu = QtWidgets.QMenu(self)
        
        # Check if already favorite
        current_favs = self.fav_manager.get_favorites(self.current_context_name)
        
        if node_name in current_favs:
            action = menu.addAction("Remove from Favorites")
            action.triggered.connect(lambda: self.toggle_favorite(node_name, remove=True))
        else:
            action = menu.addAction("Add to Favorites")
            action.triggered.connect(lambda: self.toggle_favorite(node_name, remove=False))
            
        menu.exec_(self.results_list.mapToGlobal(pos))

    def toggle_favorite(self, node_name, remove):
        if remove:
            self.fav_manager.remove_favorite(self.current_context_name, node_name)
        else:
            self.fav_manager.add_favorite(self.current_context_name, node_name)
        
        self.populate_favorites()

    def on_item_clicked(self, item):
        node_name = item.data(QtCore.Qt.UserRole)
        if node_name:
            self.create_node(node_name)

    def on_return_pressed(self):
        # If result list has items, pick the top one
        if self.results_list.count() > 0:
            item = self.results_list.item(0)
            node_name = item.data(QtCore.Qt.UserRole)
            if node_name:
                self.create_node(node_name)

    def create_node(self, node_type_name):
        """
        Creates the node in the network editor.
        Handles robust auto-wiring (single & multi) and smart placement.
        """
        if not self.network_editor:
            self.close()
            return

        try:
            parent = self.network_editor.pwd()
            new_node = parent.createNode(node_type_name)
            
            # --- WIRING & PLACEMENT ---
            wired_count = 0
            
            # Use cached selection
            sel_nodes = self.selected_nodes
            
            target_pos = self.cursor_pos # Default
            
            if sel_nodes:
                # 1. Calculate Centroid for Placement
                sum_pos = hou.Vector2(0, 0)
                for n in sel_nodes:
                    sum_pos += n.position()
                avg_pos = sum_pos / len(sel_nodes)
                
                # Check if we can wire ANY of them
                # We attempt to wire all selected nodes to sequential inputs (0, 1, 2...)
                # This works perfectly for "Merge" (accepts many) and "Transform" (accepts 1, rejects others)
                
                for i, anchor in enumerate(sel_nodes):
                    try:
                        # Attempt to connect to input 'i'
                        # For a Transform: i=0 works. i=1 throws exception (caught).
                        # For a Merge: i=0 works. i=1 works...
                        new_node.setInput(i, anchor)
                        wired_count += 1
                    except Exception:
                        # Index out of range or connection invalid (e.g. max inputs reached)
                        pass
                
                # 2. Smart Placement
                if wired_count > 0:
                    # Place DIRECTLY BELOW Centroid
                    # Offset slightly more if multiple inputs to make room? -1.5 is good.
                    target_pos = avg_pos + hou.Vector2(0, -1.5)
                else:
                    # Connection failed (e.g. wrong type) -> Place to RIGHT of last selected
                    target_pos = sel_nodes[-1].position() + hou.Vector2(2.5, 0)
            
            new_node.setPosition(target_pos)
            
            # --- SELECTION & FLAGS ---
            new_node.setSelected(True, clear_all_selected=True)
            
            # Drive the Parameter Editor to show the new node
            if self.network_editor is not None:
                self.network_editor.setCurrentNode(new_node)
            
            if hasattr(new_node, "setDisplayFlag"):
                new_node.setDisplayFlag(True)
            
            if hasattr(new_node, "setRenderFlag"):
                new_node.setRenderFlag(True)
            

            
        except Exception as e:
            pass
        
        self.close()
            


    def move_to_cursor(self):
        """
        Moves the dialog to the mouse cursor, ensuring it stays within screen bounds.
        """
        cursor_pos = QtGui.QCursor.pos()
        screen_geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        
        # Try to find the screen containing the cursor (Multi-monitor support)
        # Note: In PySide6 usage might differ slightly, but this is generally safe
        for screen in QtWidgets.QApplication.screens():
            if screen.geometry().contains(cursor_pos):
                screen_geo = screen.availableGeometry()
                break
        
        # Dimensions
        win_w = self.width()
        win_h = self.height()
        
        # Default Position: Top-Left of window at Cursor
        # Offset slightly (20px left, 10px up) for better feel
        pos_x = cursor_pos.x() - 20
        pos_y = cursor_pos.y() - 10
        
        # Check Right Edge
        if pos_x + win_w > screen_geo.right():
            pos_x = screen_geo.right() - win_w
            
        # Check Bottom Edge (The user's specific request)
        # If the window goes below the screen, flip it to appear ABOVE the cursor logic?
        # Or just slide it up?
        # User said: "automatically places itself enough above to avoid the cut off"
        if pos_y + win_h > screen_geo.bottom():
            # Slide up so the bottom aligns with screen bottom (minus padding)
            pos_y = screen_geo.bottom() - win_h - 10
            
            # If sliding up covers the cursor too much, we might want to flip it?
            # But "Sliding/Clamping" is usually safer for keeping it near the mouse context.
            
        # Ensure it didn't slide off the top
        if pos_y < screen_geo.top():
            pos_y = screen_geo.top()

        self.move(pos_x, pos_y)

    def focusOutEvent(self, event):
        self.close()
        super(LightspeedGallery, self).focusOutEvent(event)
