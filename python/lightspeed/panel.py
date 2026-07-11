"""
panel.py
--------
The Lightspeed Panel: a fast, keyboard-first node search/creation popup.

Key behaviours
  * indexes every category (SOPs, DOPs, Copernicus COPs, LOPs, TOPs, ...)
    via node_index.NodeIndex — the right nodes in every context
  * fuzzy search (prefix/acronym/subsequence) + cross-DCC aliases
  * suggestions: learned from your own creation history + curated seeds
  * keyboard: type to search, Up/Down to choose, Enter to create,
    Ctrl+Enter to create and keep the panel open (rapid chaining),
    Ctrl+F to toggle favorite, Esc to dismiss
  * favorites as clickable chips, drag to reorder, right-click to remove
  * every action is undo-grouped and reports failures instead of
    swallowing them
"""

import traceback

import hou

from . import qt
from . import node_index
from . import fuzzy
from . import aliases
from . import suggestions
from . import favorites
from . import store

QtWidgets = qt.QtWidgets
QtCore = qt.QtCore
QtGui = qt.QtGui

SETTINGS_FILE = "lightspeed_settings.json"

# Item data roles
ROLE_KIND = QtCore.Qt.UserRole            # 'node' | 'header' | 'info'
ROLE_NAME = QtCore.Qt.UserRole + 1        # full type name (createNode arg)
ROLE_LABEL = QtCore.Qt.UserRole + 2       # human label
ROLE_ALIAS = QtCore.Qt.UserRole + 3       # alias term or None
ROLE_SUGGESTED = QtCore.Qt.UserRole + 4   # bool
ROLE_FAVORITE = QtCore.Qt.UserRole + 5    # bool

ACCENT = "#d65d00"          # lightspeed orange
SUGGEST_ACCENT = "#4a90d9"  # suggestion blue
ALIAS_COLOR = "#e6b44f"     # alias gold

_icon_cache = {}


def get_icon(icon_name):
    """Cached hou icon -> QIcon. Never raises."""
    if not icon_name:
        return QtGui.QIcon()
    icon = _icon_cache.get(icon_name)
    if icon is None:
        icon = QtGui.QIcon()
        try:
            factory = getattr(hou.qt, "Icon", None) or getattr(hou.qt, "createIcon", None)
            if factory is not None:
                icon = factory(icon_name)
        except Exception:
            icon = QtGui.QIcon()
        _icon_cache[icon_name] = icon
    return icon


class ResultDelegate(QtWidgets.QStyledItemDelegate):
    """Rich row rendering: icon, label, dim type name with match highlight,
    suggestion accent bar, favorite star, alias origin."""

    NODE_HEIGHT = 30
    HEADER_HEIGHT = 22

    def sizeHint(self, option, index):
        kind = index.data(ROLE_KIND)
        if kind == "header":
            return QtCore.QSize(option.rect.width(), self.HEADER_HEIGHT)
        if kind == "info":
            return QtCore.QSize(option.rect.width(), 20)
        return QtCore.QSize(option.rect.width(), self.NODE_HEIGHT)

    def paint(self, painter, option, index):
        kind = index.data(ROLE_KIND)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = option.rect

        if kind == "header":
            painter.setPen(QtGui.QColor("#7a7a7a"))
            font = painter.font()
            font.setPointSizeF(7.5)
            font.setBold(True)
            font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 1.2)
            painter.setFont(font)
            painter.drawText(rect.adjusted(10, 0, -8, -3),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom,
                             index.data(QtCore.Qt.DisplayRole) or "")
            painter.setPen(QtGui.QColor("#3a3a3a"))
            painter.drawLine(rect.left() + 8, rect.bottom(),
                             rect.right() - 8, rect.bottom())
            painter.restore()
            return

        if kind == "info":
            painter.setPen(QtGui.QColor("#666666"))
            painter.drawText(rect.adjusted(12, 0, -8, 0),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                             index.data(QtCore.Qt.DisplayRole) or "")
            painter.restore()
            return

        # --- node row ---
        selected = bool(option.state & QtWidgets.QStyle.State_Selected)
        hovered = bool(option.state & QtWidgets.QStyle.State_MouseOver)

        if selected:
            painter.setBrush(QtGui.QColor(ACCENT))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(rect.adjusted(4, 1, -4, -1), 4, 4)
        elif hovered:
            painter.setBrush(QtGui.QColor("#383838"))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(rect.adjusted(4, 1, -4, -1), 4, 4)

        x = rect.left() + 8
        if index.data(ROLE_SUGGESTED):
            painter.setBrush(QtGui.QColor(SUGGEST_ACCENT))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(
                QtCore.QRectF(x - 2, rect.top() + 6, 3, rect.height() - 12), 1.5, 1.5)
        x += 6

        icon = index.data(QtCore.Qt.DecorationRole)
        if isinstance(icon, QtGui.QIcon) and not icon.isNull():
            icon.paint(painter, x, rect.top() + (rect.height() - 20) // 2, 20, 20)
        x += 26

        label = index.data(ROLE_LABEL) or ""
        name = index.data(ROLE_NAME) or ""
        alias = index.data(ROLE_ALIAS)
        is_fav = bool(index.data(ROLE_FAVORITE))

        right = rect.right() - 10
        if is_fav:
            painter.setPen(QtGui.QColor("#f0c040" if not selected else "#ffffff"))
            star_rect = QtCore.QRect(right - 12, rect.top(), 12, rect.height())
            painter.drawText(star_rect, QtCore.Qt.AlignCenter, "★")
            right -= 18

        font = painter.font()
        font.setPointSizeF(9.0)
        font.setBold(False)
        painter.setFont(font)
        fm = QtGui.QFontMetrics(font)

        label_color = "#ffffff" if selected else "#e6e6e6"
        name_color = "#ffd9b8" if selected else "#8f8f8f"

        text_rect = QtCore.QRect(x, rect.top(), max(10, right - x), rect.height())
        label_text = fm.elidedText(label, QtCore.Qt.ElideRight, text_rect.width())
        painter.setPen(QtGui.QColor(label_color))
        painter.drawText(text_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, label_text)
        label_w = fm.horizontalAdvance(label_text) + 8

        remaining = text_rect.width() - label_w
        if remaining > 30:
            extra = "(%s)" % name
            if alias:
                extra += "  ≈ %s" % alias
            small = painter.font()
            small.setPointSizeF(8.0)
            painter.setFont(small)
            sfm = QtGui.QFontMetrics(small)
            extra = sfm.elidedText(extra, QtCore.Qt.ElideMiddle, remaining)
            painter.setPen(QtGui.QColor(ALIAS_COLOR if alias and not selected else name_color))
            painter.drawText(
                QtCore.QRect(x + label_w, rect.top(), remaining, rect.height()),
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, extra)

        painter.restore()


class LightspeedPanel(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(LightspeedPanel, self).__init__(parent)

        # --- context ---
        self.selected_nodes = []
        self.network_editor = None
        self.cursor_pos = None            # hou.Vector2 in network coords, or None
        self.category = None              # hou.NodeTypeCategory
        self.category_name = None
        self._capture_context()

        # --- data ---
        self.index = node_index.NodeIndex.get()
        self.fav_manager = favorites.FavoritesManager()
        self.engine = suggestions.SuggestionEngine()
        self.settings = store.load_json(SETTINGS_FILE, {})
        self._recompute_suggestions()

        # --- window ---
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        self.setSizeGripEnabled(False)

        self._build_ui()
        self._populate_favorites()
        self._update_results("")
        self._restore_size()
        self._move_to_cursor()

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def _capture_context(self):
        try:
            selection = list(hou.selectedNodes())
        except hou.Error:
            selection = []

        self.network_editor = node_index.find_network_editor(selection)
        self.category = node_index.category_for_editor(self.network_editor)
        self.category_name = self.category.name() if self.category else None

        # Only keep selected nodes that live in the network we will create in,
        # so wiring never crosses networks.
        if self.network_editor is not None:
            try:
                pwd_path = self.network_editor.pwd().path()
                selection = [n for n in selection
                             if n.parent() and n.parent().path() == pwd_path]
            except hou.Error:
                selection = []
        self.selected_nodes = selection

        if self.network_editor is not None:
            try:
                self.cursor_pos = self.network_editor.cursorPosition()
            except hou.Error:
                self.cursor_pos = None

    def _recompute_suggestions(self):
        self.upstream_type = suggestions.leaf_type_name(self.selected_nodes)
        if self.category_name:
            self.suggested_bases = self.engine.suggestions(
                self.category_name, self.upstream_type, limit=10)
        else:
            self.suggested_bases = []

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                border: 1px solid #4a4a4a;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 7px 9px;
                font-size: 13px;
                selection-background-color: %(accent)s;
            }
            QLineEdit:focus { border-color: %(accent)s; }
            QListWidget {
                background-color: #242424;
                border: 1px solid #333;
                border-radius: 5px;
                outline: 0;
            }
            QLabel#sectionLabel {
                color: #7a7a7a; font-weight: bold; font-size: 10px;
                letter-spacing: 1px; margin-top: 4px;
            }
            QLabel#contextBadge {
                color: #ffffff; background-color: #3a3a3a;
                border-radius: 4px; padding: 2px 8px;
                font-size: 11px; font-weight: bold;
            }
            QLabel#countLabel, QLabel#hintLabel { color: #6f6f6f; font-size: 10px; }
            QLabel#errorLabel { color: #ff7a66; font-size: 10px; }
            QPushButton#quickBtn {
                background-color: #383838; border: 1px solid #555;
                border-radius: 4px; padding: 4px 10px;
                font-weight: bold; font-size: 10px; color: #ddd;
            }
            QPushButton#quickBtn:hover { background-color: #444; border-color: %(accent)s; }
            QPushButton#quickBtn:disabled { color: #666; border-color: #3a3a3a; }
            QPushButton#dangerBtn {
                background-color: #383838; border: 1px solid #555;
                border-radius: 4px; padding: 4px 10px;
                font-weight: bold; font-size: 10px; color: #ddd;
            }
            QPushButton#dangerBtn:hover {
                background-color: #4a2020; border-color: #cc3333; color: #ff6666;
            }
            QToolButton#refreshBtn {
                background: transparent; border: none; color: #8a8a8a;
                font-size: 13px;
            }
            QToolButton#refreshBtn:hover { color: %(accent)s; }
        """ % {"accent": ACCENT})

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 6)
        layout.setSpacing(6)

        # --- header: context badge + count + refresh ---
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(6)

        cat_label = self.category.label() if self.category else "No network"
        badge = QtWidgets.QLabel(
            "%s" % (cat_label or self.category_name or "Unknown"))
        badge.setObjectName("contextBadge")
        badge.setToolTip("Node context detected under your cursor / selection")
        header.addWidget(badge)

        if self.upstream_type:
            up = QtWidgets.QLabel("after %s" % fuzzy.base_name(self.upstream_type))
            up.setObjectName("countLabel")
            header.addWidget(up)

        header.addStretch()

        self.count_label = QtWidgets.QLabel("")
        self.count_label.setObjectName("countLabel")
        header.addWidget(self.count_label)

        refresh = QtWidgets.QToolButton()
        refresh.setObjectName("refreshBtn")
        refresh.setText("⟳")
        refresh.setToolTip("Re-scan installed node types (after installing HDAs)")
        refresh.clicked.connect(self._on_refresh_index)
        header.addWidget(refresh)
        layout.addLayout(header)

        # --- quick actions ---
        self._build_quick_actions(layout)

        # --- search ---
        self.search_bar = QtWidgets.QLineEdit()
        placeholder = "Search %s nodes..." % (
            self.category.label() if self.category else "")
        self.search_bar.setPlaceholderText(placeholder)
        self.search_bar.textChanged.connect(self._on_text_changed)
        self.search_bar.installEventFilter(self)
        layout.addWidget(self.search_bar)

        self._debounce = QtCore.QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(80)
        self._debounce.timeout.connect(
            lambda: self._update_results(self.search_bar.text()))

        # --- favorites chips ---
        self.fav_list = None
        if self.category_name:
            fav_label = QtWidgets.QLabel("FAVORITES")
            fav_label.setObjectName("sectionLabel")
            layout.addWidget(fav_label)

            self.fav_list = QtWidgets.QListWidget()
            self.fav_list.setViewMode(QtWidgets.QListWidget.IconMode)
            self.fav_list.setResizeMode(QtWidgets.QListWidget.Adjust)
            self.fav_list.setMovement(QtWidgets.QListView.Snap)
            self.fav_list.setWordWrap(False)
            self.fav_list.setSpacing(3)
            self.fav_list.setFixedHeight(58)
            self.fav_list.setIconSize(QtCore.QSize(24, 24))
            self.fav_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
            self.fav_list.setDefaultDropAction(QtCore.Qt.MoveAction)
            self.fav_list.itemClicked.connect(self._on_favorite_clicked)
            self.fav_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.fav_list.customContextMenuRequested.connect(self._fav_context_menu)
            self.fav_list.model().rowsMoved.connect(self._on_favorites_reordered)
            layout.addWidget(self.fav_list)

        # --- results ---
        self.results = QtWidgets.QListWidget()
        self.results.setIconSize(QtCore.QSize(20, 20))
        self.results.setMouseTracking(True)
        self.results.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.results.setItemDelegate(ResultDelegate(self.results))
        self.results.itemDoubleClicked.connect(self._on_result_activated)
        self.results.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self._result_context_menu)
        layout.addWidget(self.results, 1)

        # --- footer: hints + error + size grip ---
        footer = QtWidgets.QHBoxLayout()
        footer.setContentsMargins(2, 0, 0, 0)
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setVisible(False)
        footer.addWidget(self.error_label, 1)

        hints = QtWidgets.QLabel(
            "↵ create    Ctrl+↵ chain    Ctrl+F ★    Esc close")
        hints.setObjectName("hintLabel")
        footer.addWidget(hints)

        grip = QtWidgets.QSizeGrip(self)
        grip.setFixedSize(14, 14)
        footer.addWidget(grip, 0, QtCore.Qt.AlignBottom)
        layout.addLayout(footer)

        self.resize(380, 560)

    def _build_quick_actions(self, layout):
        if self.network_editor is None:
            return
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(5)
        has_sel = bool(self.selected_nodes)

        def add_btn(text, tooltip, slot, enabled=True, danger=False):
            btn = QtWidgets.QPushButton(text)
            btn.setObjectName("dangerBtn" if danger else "quickBtn")
            btn.setToolTip(tooltip)
            btn.setEnabled(enabled)
            btn.clicked.connect(slot)
            row.addWidget(btn)
            return btn

        cat = self.category_name
        if cat and self.index.has(cat, "merge"):
            add_btn("MERGE", "Merge all selected nodes",
                    self._quick_merge, has_sel and len(self.selected_nodes) >= 2)
        if cat and self.index.has(cat, "null"):
            add_btn("NULL OUT", "Create a display OUT null after the selection",
                    self._quick_null, has_sel)
        add_btn("LAYOUT", "Auto-layout selected nodes (or all when none selected)",
                self._quick_layout)
        add_btn("DELETE", "Delete selected node(s)",
                self._quick_delete, has_sel, danger=True)
        row.addStretch()
        layout.addLayout(row)

    # ------------------------------------------------------------------
    # Keyboard handling
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self.search_bar and event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()

            if key in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Up):
                self._move_selection(1 if key == QtCore.Qt.Key_Down else -1)
                return True
            if key == QtCore.Qt.Key_PageDown:
                self._move_selection(8)
                return True
            if key == QtCore.Qt.Key_PageUp:
                self._move_selection(-8)
                return True
            if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                # Flush a pending debounce so Enter acts on the current query
                if self._debounce.isActive():
                    self._debounce.stop()
                    self._update_results(self.search_bar.text())
                keep_open = bool(mods & QtCore.Qt.ControlModifier)
                item = self.results.currentItem() or self._first_node_item()
                if item is not None and item.data(ROLE_KIND) == "node":
                    self.create_node(item.data(ROLE_NAME), keep_open=keep_open)
                return True
            if key == QtCore.Qt.Key_F and (mods & QtCore.Qt.ControlModifier):
                item = self.results.currentItem()
                if item is not None and item.data(ROLE_KIND) == "node":
                    self._toggle_favorite(item.data(ROLE_NAME))
                return True
        return super(LightspeedPanel, self).eventFilter(obj, event)

    def _first_node_item(self):
        for i in range(self.results.count()):
            if self.results.item(i).data(ROLE_KIND) == "node":
                return self.results.item(i)
        return None

    def _move_selection(self, delta):
        rows = [i for i in range(self.results.count())
                if self.results.item(i).data(ROLE_KIND) == "node"]
        if not rows:
            return
        current = self.results.currentRow()
        if current in rows:
            pos = rows.index(current)
            pos = max(0, min(len(rows) - 1, pos + delta))
        else:
            pos = 0 if delta >= 0 else len(rows) - 1
        self.results.setCurrentRow(rows[pos])
        self.results.scrollToItem(self.results.item(rows[pos]),
                                  QtWidgets.QAbstractItemView.EnsureVisible)

    def showEvent(self, event):
        super(LightspeedPanel, self).showEvent(event)
        self.search_bar.setFocus()

    def closeEvent(self, event):
        self._save_size()
        super(LightspeedPanel, self).closeEvent(event)

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------

    def _on_text_changed(self, _text):
        self._debounce.start()

    def _entries(self):
        if not self.category_name:
            return []
        return self.index.entries(self.category_name)

    def _favorite_names(self):
        if not self.category_name:
            return set()
        return set(self.fav_manager.get_favorites(self.category_name))

    def _add_header(self, text):
        item = QtWidgets.QListWidgetItem(text)
        item.setData(ROLE_KIND, "header")
        item.setFlags(QtCore.Qt.NoItemFlags)
        self.results.addItem(item)

    def _add_info(self, text):
        item = QtWidgets.QListWidgetItem(text)
        item.setData(ROLE_KIND, "info")
        item.setFlags(QtCore.Qt.NoItemFlags)
        self.results.addItem(item)

    def _add_node_item(self, entry, alias=None, suggested=False):
        item = QtWidgets.QListWidgetItem()
        item.setData(ROLE_KIND, "node")
        item.setData(ROLE_NAME, entry.name)
        item.setData(ROLE_LABEL, entry.label)
        item.setData(ROLE_ALIAS, alias)
        item.setData(ROLE_SUGGESTED, suggested)
        item.setData(ROLE_FAVORITE, entry.name in self._fav_cache)
        item.setData(QtCore.Qt.DecorationRole, get_icon(entry.icon))
        tooltip = "%s  (%s)" % (entry.label, entry.name)
        if suggested:
            tooltip += "\nSuggested next node"
        if alias:
            tooltip += "\nMatches '%s'" % alias
        item.setToolTip(tooltip)
        self.results.addItem(item)

    def _update_results(self, text):
        self.results.clear()
        self._fav_cache = self._favorite_names()
        entries = self._entries()

        if not entries:
            self._add_info("No creatable nodes here — dive into a network.")
            self.count_label.setText("")
            return

        query = text.strip()
        suggested_set = set(self.suggested_bases)

        if not query:
            self._populate_browse_view(entries, suggested_set)
        else:
            self._populate_search_view(entries, query, suggested_set)

        first = self._first_node_item()
        if first is not None:
            self.results.setCurrentItem(first)

    def _populate_browse_view(self, entries, suggested_set):
        by_base = self.index.base_entries(self.category_name)

        shown = set()
        sug_entries = []
        for base in self.suggested_bases:
            e = by_base.get(base)
            if e is not None and e.name not in shown:
                sug_entries.append(e)
                shown.add(e.name)

        if sug_entries:
            self._add_header("SUGGESTED" + (
                "  —  after %s" % fuzzy.base_name(self.upstream_type)
                if self.upstream_type else ""))
            for e in sug_entries[:8]:
                self._add_node_item(e, suggested=True)

        frequent = []
        for base in self.engine.frequent(self.category_name, 14):
            e = by_base.get(base)
            if e is not None and e.name not in shown:
                frequent.append(e)
                shown.add(e.name)
        if frequent:
            self._add_header("FREQUENT")
            for e in frequent[:10]:
                self._add_node_item(e, suggested=e.base in suggested_set)

        self._add_header("ALL  —  %d NODES" % len(entries))
        remaining = [e for e in entries if e.name not in shown]
        for e in remaining[:120]:
            self._add_node_item(e, suggested=e.base in suggested_set)
        if len(remaining) > 120:
            self._add_info("… %d more — start typing to filter"
                           % (len(remaining) - 120))
        self.count_label.setText("%d nodes" % len(entries))

    def _populate_search_view(self, entries, query, suggested_set):
        alias_hits = aliases.alias_hits_for_query(query)
        ranked = fuzzy.rank(
            entries, query,
            alias_hits=alias_hits,
            suggested=suggested_set,
            favorites=self._fav_cache,
            limit=60,
        )
        if not ranked:
            self._add_info("No matches for '%s'" % query)
            self.count_label.setText("0 matches")
            return
        for r in ranked:
            entry = r["entry"]
            self._add_node_item(entry, alias=r["alias"],
                                suggested=entry.base in suggested_set)
        self.count_label.setText("%d match%s" % (
            len(ranked), "" if len(ranked) == 1 else "es"))

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------

    def _populate_favorites(self):
        if self.fav_list is None or not self.category_name:
            return
        self.fav_list.clear()
        for name in self.fav_manager.get_favorites(self.category_name):
            entry = self.index.entry(self.category_name, name)
            label = entry.label if entry else name
            display = label if len(label) <= 14 else label[:13] + "…"
            icon = get_icon(entry.icon) if entry else QtGui.QIcon()
            item = QtWidgets.QListWidgetItem(icon, display)
            item.setData(ROLE_NAME, entry.name if entry else name)
            item.setToolTip("%s  (%s)\nClick to create • right-click to remove"
                            % (label, name))
            self.fav_list.addItem(item)

    def _on_favorite_clicked(self, item):
        name = item.data(ROLE_NAME)
        if name:
            self.create_node(name)

    def _on_favorites_reordered(self, *args):
        if not self.category_name or self.fav_list is None:
            return
        order = []
        for i in range(self.fav_list.count()):
            name = self.fav_list.item(i).data(ROLE_NAME)
            if name:
                order.append(name)
        self.fav_manager.update_favorites_order(self.category_name, order)

    def _toggle_favorite(self, name):
        if not self.category_name:
            return
        self.fav_manager.toggle(self.category_name, name)
        self._populate_favorites()
        # refresh star badges without recomputing the query
        self._fav_cache = self._favorite_names()
        for i in range(self.results.count()):
            item = self.results.item(i)
            if item.data(ROLE_KIND) == "node":
                item.setData(ROLE_FAVORITE, item.data(ROLE_NAME) in self._fav_cache)
        self.results.viewport().update()

    def _fav_context_menu(self, pos):
        item = self.fav_list.itemAt(pos)
        if not item:
            return
        name = item.data(ROLE_NAME)
        menu = QtWidgets.QMenu(self)
        act = menu.addAction("Remove from Favorites")
        act.triggered.connect(lambda: self._toggle_favorite(name))
        qt.exec_menu(menu, self.fav_list.mapToGlobal(pos))

    def _result_context_menu(self, pos):
        item = self.results.itemAt(pos)
        if not item or item.data(ROLE_KIND) != "node":
            return
        name = item.data(ROLE_NAME)
        menu = QtWidgets.QMenu(self)
        if name in self._favorite_names():
            act = menu.addAction("Remove from Favorites")
        else:
            act = menu.addAction("Add to Favorites")
        act.triggered.connect(lambda: self._toggle_favorite(name))
        create_keep = menu.addAction("Create && Keep Panel Open")
        create_keep.triggered.connect(
            lambda: self.create_node(name, keep_open=True))
        qt.exec_menu(menu, self.results.mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Node creation
    # ------------------------------------------------------------------

    def _on_result_activated(self, item):
        if item.data(ROLE_KIND) == "node":
            mods = QtWidgets.QApplication.keyboardModifiers()
            keep = bool(mods & QtCore.Qt.ControlModifier)
            self.create_node(item.data(ROLE_NAME), keep_open=keep)

    def create_node(self, type_name, keep_open=False):
        if self.network_editor is None:
            self._show_error("No network editor found — nowhere to create.")
            return

        entry = self.index.entry(self.category_name, type_name)
        label = entry.label if entry else type_name
        upstream = self.upstream_type

        try:
            with hou.undos.group("Lightspeed: create %s" % label):
                parent = self.network_editor.pwd()
                new_node = parent.createNode(type_name)

                wired = 0
                max_in = entry.max_inputs if entry else 9999
                for i, anchor in enumerate(self.selected_nodes):
                    if 0 <= max_in <= i:
                        break
                    try:
                        new_node.setInput(i, anchor)
                        wired += 1
                    except hou.Error:
                        break

                self._place_node(new_node, wired)

                new_node.setSelected(True, clear_all_selected=True)
                try:
                    self.network_editor.setCurrentNode(new_node)
                except hou.Error:
                    pass
                for flag_setter in ("setDisplayFlag", "setRenderFlag"):
                    fn = getattr(new_node, flag_setter, None)
                    if fn is not None:
                        try:
                            fn(True)
                        except hou.Error:
                            pass
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Couldn't create %s: %s"
                             % (label, str(exc).strip() or type(exc).__name__))
            return

        # Learn from this creation
        try:
            self.engine.record_creation(self.category_name, upstream, type_name)
        except Exception:
            traceback.print_exc()

        try:
            self.network_editor.flashMessage(None, "%s created" % label, 1.2)
        except (AttributeError, hou.Error):
            pass

        if keep_open:
            # Chain mode: the new node becomes the anchor for the next create.
            self.selected_nodes = [new_node]
            self._recompute_suggestions()
            self.search_bar.clear()
            self._update_results("")
            self.search_bar.setFocus()
        else:
            self.close()

    def _place_node(self, new_node, wired):
        try:
            if wired and self.selected_nodes:
                low_y = min(n.position().y() for n in self.selected_nodes)
                avg_x = (sum(n.position().x() for n in self.selected_nodes)
                         / len(self.selected_nodes))
                new_node.setPosition(hou.Vector2(avg_x, low_y - 1.2))
            elif self.selected_nodes:
                anchor = self.selected_nodes[-1].position()
                new_node.setPosition(anchor + hou.Vector2(2.5, 0))
            elif self.cursor_pos is not None:
                new_node.setPosition(self.cursor_pos)
            else:
                new_node.moveToGoodPosition()
        except hou.Error:
            try:
                new_node.moveToGoodPosition()
            except hou.Error:
                pass

    # ------------------------------------------------------------------
    # Quick actions
    # ------------------------------------------------------------------

    def _quick_merge(self):
        sel = self.selected_nodes
        if not sel or self.network_editor is None:
            return
        try:
            with hou.undos.group("Lightspeed: merge selection"):
                parent = self.network_editor.pwd()
                merge = parent.createNode("merge")
                merge.setName("merge_selected", unique_name=True)
                for i, node in enumerate(sel):
                    merge.setInput(i, node)
                self.selected_nodes = sel
                self._place_node(merge, wired=len(sel))
                merge.setSelected(True, clear_all_selected=True)
                self.network_editor.setCurrentNode(merge)
                for fn_name in ("setDisplayFlag", "setRenderFlag"):
                    fn = getattr(merge, fn_name, None)
                    if fn:
                        try:
                            fn(True)
                        except hou.Error:
                            pass
            self.close()
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Merge failed: %s" % exc)

    def _quick_null(self):
        sel = self.selected_nodes
        if not sel or self.network_editor is None:
            return
        source = sel[-1]
        try:
            with hou.undos.group("Lightspeed: OUT null"):
                parent = self.network_editor.pwd()
                null = parent.createNode("null")
                null.setName("%s_OUT" % source.name().upper(), unique_name=True)
                try:
                    null.setColor(hou.Color((0, 0, 0)))
                except hou.Error:
                    pass
                null.setInput(0, source)
                null.setPosition(source.position() + hou.Vector2(0, -1.2))
                null.setSelected(True, clear_all_selected=True)
                self.network_editor.setCurrentNode(null)
                for fn_name in ("setDisplayFlag", "setRenderFlag"):
                    fn = getattr(null, fn_name, None)
                    if fn:
                        try:
                            fn(True)
                        except hou.Error:
                            pass
            self.close()
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Null OUT failed: %s" % exc)

    def _quick_layout(self):
        if self.network_editor is None:
            return
        try:
            with hou.undos.group("Lightspeed: layout"):
                parent = self.network_editor.pwd()
                if self.selected_nodes:
                    parent.layoutChildren(items=self.selected_nodes)
                else:
                    parent.layoutChildren()
            self.close()
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Layout failed: %s" % exc)

    def _quick_delete(self):
        sel = self.selected_nodes
        if not sel:
            self.close()
            return
        try:
            with hou.undos.group("Lightspeed: delete selection"):
                for node in sel:
                    node.destroy()
            self.close()
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Delete failed: %s" % exc)

    def _on_refresh_index(self):
        self.index.refresh()
        self._update_results(self.search_bar.text())
        self._populate_favorites()

    # ------------------------------------------------------------------
    # Window placement / persistence / errors
    # ------------------------------------------------------------------

    def _show_error(self, message):
        print("Lightspeed: %s" % message)
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        try:
            hou.ui.setStatusMessage("Lightspeed: %s" % message,
                                    severity=hou.severityType.Warning)
        except (AttributeError, hou.Error):
            pass

    def _restore_size(self):
        size = self.settings.get("size")
        if (isinstance(size, list) and len(size) == 2
                and all(isinstance(v, int) for v in size)):
            self.resize(max(320, size[0]), max(380, size[1]))

    def _save_size(self):
        self.settings["size"] = [self.width(), self.height()]
        store.save_json(SETTINGS_FILE, self.settings)

    def _move_to_cursor(self):
        cursor = QtGui.QCursor.pos()
        screen_geo = None
        for screen in QtWidgets.QApplication.screens():
            if screen.geometry().contains(cursor):
                screen_geo = screen.availableGeometry()
                break
        if screen_geo is None:
            screen_geo = QtWidgets.QApplication.primaryScreen().availableGeometry()

        x = cursor.x() - 24
        y = cursor.y() - 12
        x = min(x, screen_geo.right() - self.width())
        y = min(y, screen_geo.bottom() - self.height() - 10)
        x = max(x, screen_geo.left())
        y = max(y, screen_geo.top())
        self.move(x, y)
