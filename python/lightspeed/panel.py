"""
panel.py
--------
The Lightspeed Panel: a fast, keyboard-first node search/creation popup.

Key behaviours
  * indexes every category (SOPs, DOPs, Copernicus COPs, LOPs, TOPs, ...)
    via node_index.NodeIndex — the right nodes in every context
  * fuzzy search (prefix/acronym/subsequence) + cross-DCC aliases
    (C4D / After Effects / Blender / Maya / Max / Nuke vocabulary)
  * wire insertion: select a wire first and the created node is spliced
    into that connection
  * presets: gallery-backed parameter presets appear as creatable rows;
    ★ PRESET captures the selected node's parms as a new one
  * inline naming: "null OUT_TEXT" creates a null named OUT_TEXT
  * suggestions: learned from your own creation history + curated seeds
  * keyboard: type to search, Up/Down to choose, Enter to create,
    Ctrl+Enter to create and keep the panel open (rapid chaining),
    Ctrl+1..9 to create the Nth result, Ctrl+F to toggle favorite,
    F1 node help, Ctrl+/ shortcut cheat sheet, Esc to dismiss
  * favorites as clickable chips, drag to reorder, right-click to remove
  * embedded mode (python_panels/lightspeed.pypanel) turns the popup into
    a persistent dockable pane
  * every action is undo-grouped and reports failures instead of
    swallowing them
"""

import re
import traceback

import hou

from . import qt
from . import node_index
from . import fuzzy
from . import aliases
from . import suggestions
from . import favorites
from . import presets
from . import store

QtWidgets = qt.QtWidgets
QtCore = qt.QtCore
QtGui = qt.QtGui

SETTINGS_FILE = store.SETTINGS_FILE

# Item data roles
ROLE_KIND = QtCore.Qt.UserRole            # 'node' | 'preset' | 'header' | 'info'
ROLE_NAME = QtCore.Qt.UserRole + 1        # full type name (createNode arg)
ROLE_LABEL = QtCore.Qt.UserRole + 2       # human label
ROLE_ALIAS = QtCore.Qt.UserRole + 3       # alias term or None
ROLE_SUGGESTED = QtCore.Qt.UserRole + 4   # bool
ROLE_FAVORITE = QtCore.Qt.UserRole + 5    # bool
ROLE_PRESET = QtCore.Qt.UserRole + 6      # presets.PresetItem, or None
ROLE_ORDINAL = QtCore.Qt.UserRole + 7     # 1..9 -> row reachable via Ctrl+N

# Wire-detection is skipped in giant networks: scanning every child's input
# connections would delay panel-open, and a selected wire there is rare.
MAX_WIRE_SCAN_CHILDREN = 2500

ACCENT = "#d65d00"          # lightspeed orange
SUGGEST_ACCENT = "#4a90d9"  # suggestion blue
ALIAS_COLOR = "#e6b44f"     # alias gold
PRESET_COLOR = "#7ec98f"    # preset green

# Rows the keyboard/mouse can create
CREATABLE_KINDS = ("node", "preset")

# Favorites chip grid (uniform cells: predictable drag-snap + clean rows)
FAV_GRID_W = 74
FAV_GRID_H = 46
FAV_MAX_ROWS = 2

# Trailing query token that names the new node: "null OUT_TEXT".
# The token must contain an underscore — search vocabulary like
# "convert VDB" or "import USD" must never be eaten as a name.
NAME_TOKEN_RE = re.compile(r"^[A-Za-z]\w*_\w*$")

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


def steal_downstream(sel_node, new_node, out_idx=0):
    """
    Chain insertion: rewire everything `sel_node` feeds FROM output
    `out_idx` so it is fed by `new_node` instead — the new node slots into
    the chain rather than dangling off it as a branch.

    Only connections from `out_idx` move (a multi-output node like Split
    keeps its other output wires). Each downstream keeps its exact input
    index, so a Boolean fed on input 1 stays fed on input 1. Returns the
    list of rewired downstream nodes. Module-level so the headless test
    suite exercises the real rewiring path.
    """
    try:
        conns = sel_node.outputConnections()
    except hou.Error:
        return []
    # Snapshot before rewiring — setInput invalidates connection objects.
    targets = []
    for conn in conns:
        try:
            if conn.outputIndex() != out_idx:
                continue
            down = conn.outputNode()
            if down is None or down == new_node:
                continue
            targets.append((down, conn.inputIndex()))
        except (AttributeError, hou.Error):
            continue
    stolen = []
    for down, in_idx in targets:
        try:
            down.setInput(in_idx, new_node, 0)
            stolen.append(down)
        except hou.Error:
            continue   # incompatible port: that wire stays on the old node
    return stolen


def place_between(new_node, up_node, down_nodes):
    """Position new_node between up_node and the nodes it now feeds, and
    nudge any downstream node sitting too close down to keep the chain
    readable."""
    try:
        up = up_node.position()
        if not down_nodes:
            new_node.setPosition(up + hou.Vector2(0, -1.2))
            return
        avg = hou.Vector2(0, 0)
        for d in down_nodes:
            avg += d.position()
        avg = avg / len(down_nodes)
        mid = (up + avg) / 2.0
        new_node.setPosition(mid)
        for d in down_nodes:
            if mid.y() - d.position().y() < 0.9:
                d.setPosition(hou.Vector2(d.position().x(), mid.y() - 1.0))
    except hou.Error:
        try:
            new_node.moveToGoodPosition()
        except hou.Error:
            pass


def splice_node_into(new_node, endpoints):
    """Insert new_node into an existing wire:
    upstream ──▶ new_node ──▶ downstream, placed at the wire midpoint.
    endpoints is (upstream, output_index, downstream, input_index) from
    LightspeedPanel._connection_endpoints. Module-level so the headless
    test suite exercises the real splice path."""
    up, out_idx, down, in_idx = endpoints
    new_node.setInput(0, up, out_idx)
    down.setInput(in_idx, new_node, 0)
    try:
        mid = (up.position() + down.position()) / 2.0
        new_node.setPosition(mid)
    except hou.Error:
        new_node.moveToGoodPosition()


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
        ordinal = index.data(ROLE_ORDINAL)
        if ordinal:
            # Ctrl+1..9 discoverability: a whisper-quiet number at the edge
            num_font = painter.font()
            num_font.setPointSizeF(7.0)
            painter.setFont(num_font)
            painter.setPen(QtGui.QColor("#e8b48a" if selected else "#565656"))
            num_rect = QtCore.QRect(right - 10, rect.top(), 10, rect.height())
            painter.drawText(num_rect, QtCore.Qt.AlignCenter, str(ordinal))
            right -= 14
        if is_fav:
            star_font = painter.font()
            star_font.setPointSizeF(9.0)
            painter.setFont(star_font)
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

        is_preset = index.data(ROLE_PRESET) is not None

        remaining = text_rect.width() - label_w
        if remaining > 30:
            extra = "(%s)" % name
            if is_preset:
                extra += "  ◆ preset"
            if alias:
                extra += "  ≈ %s" % alias
            small = painter.font()
            small.setPointSizeF(8.0)
            painter.setFont(small)
            sfm = QtGui.QFontMetrics(small)
            extra = sfm.elidedText(extra, QtCore.Qt.ElideMiddle, remaining)
            if selected:
                extra_color = name_color
            elif is_preset:
                extra_color = PRESET_COLOR
            elif alias:
                extra_color = ALIAS_COLOR
            else:
                extra_color = name_color
            painter.setPen(QtGui.QColor(extra_color))
            painter.drawText(
                QtCore.QRect(x + label_w, rect.top(), remaining, rect.height()),
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, extra)

        painter.restore()


class LightspeedPanel(QtWidgets.QDialog):
    def __init__(self, parent=None, editor=None, embedded=False):
        """
        editor   : hou.NetworkEditor to anchor to (e.g. from a nodegraph
                   hook); falls back to cursor/selection detection.
        embedded : True when hosted inside a Python Panel pane — the panel
                   becomes persistent: no popup flags, Esc clears instead of
                   closing, creations keep the panel open, and the network
                   context is re-captured when focus returns.
        """
        super(LightspeedPanel, self).__init__(parent)
        self.embedded = bool(embedded)

        # --- context ---
        self.selected_nodes = []
        self.network_editor = None
        self.cursor_pos = None            # hou.Vector2 in network coords, or None
        self.category = None              # hou.NodeTypeCategory
        self.category_name = None
        self.insert_connection = None     # hou.NodeConnection to splice into
        self.pending_name = None          # node name parsed from the query
        self._capture_context(editor)

        # --- data ---
        self.index = node_index.NodeIndex.get()
        self.fav_manager = favorites.FavoritesManager()
        self.engine = suggestions.SuggestionEngine()
        self.settings = store.load_json(SETTINGS_FILE, {})
        self._presets = self._load_presets()
        self._recompute_suggestions()

        # --- window ---
        if not self.embedded:
            self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        self.setSizeGripEnabled(False)

        self._build_ui()
        self._populate_favorites()
        self._update_results("")
        if not self.embedded:
            self._restore_size()
            self._move_to_cursor()

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def _capture_context(self, editor=None):
        try:
            selection = list(hou.selectedNodes())
        except hou.Error:
            selection = []

        if isinstance(editor, hou.NetworkEditor):
            self.network_editor = editor
        else:
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

        # Wire-insertion mode: exactly one selected wire in this network
        # means "splice the new node into that connection".
        self.insert_connection = self._find_selected_connection()

    def _find_selected_connection(self):
        """The single selected NodeConnection in the current network, if any."""
        if self.network_editor is None:
            return None
        try:
            parent = self.network_editor.pwd()
        except hou.Error:
            return None
        found = []
        try:
            children = parent.children()
            if len(children) > MAX_WIRE_SCAN_CHILDREN:
                return None   # keep panel-open instant in giant networks
            for child in children:
                for conn in child.inputConnections():
                    try:
                        if conn.isSelected():
                            found.append(conn)
                            if len(found) > 1:
                                return None   # ambiguous — stay in normal mode
                    except AttributeError:
                        return None           # very old builds: no isSelected
        except hou.Error:
            return None
        if len(found) != 1:
            return None
        # Only offer insert mode for wires whose two ends are plain nodes —
        # subnet indirect inputs can't be spliced.
        try:
            if self._connection_endpoints(found[0]) is None:
                return None
        except (AttributeError, hou.Error):
            return None
        return found[0]

    @staticmethod
    def _connection_endpoints(conn):
        """
        (upstream_node, output_index, downstream_node, input_index) for a
        wire, or None when either end isn't a plain node (e.g. a subnet
        indirect input). Direction is verified against actual connectivity
        where possible; when the check is inconclusive the documented
        NodeConnection semantics (inputNode = upstream) are trusted.
        """
        a = conn.inputNode()
        b = conn.outputNode()
        if a is None or b is None:
            return None
        up, down = a, b
        try:
            if any(inp is not None and inp.path() == b.path()
                   for inp in a.inputs()):
                up, down = b, a
        except hou.Error:
            pass
        # inputIndex is by definition the input connector (downstream side),
        # outputIndex the output connector (upstream side).
        return up, conn.outputIndex(), down, conn.inputIndex()

    def _recompute_suggestions(self):
        self.upstream_type = suggestions.leaf_type_name(self.selected_nodes)
        if self.category_name:
            self.suggested_bases = self.engine.suggestions(
                self.category_name, self.upstream_type, limit=10)
        else:
            self.suggested_bases = []

    def _load_presets(self, force=False):
        try:
            return presets.entries_for_category(self.category, force=force)
        except Exception:
            traceback.print_exc()
            return []

    def refresh_context(self, editor=None):
        """Re-detect network/selection/category (embedded panels call this
        when focus returns; popups capture once at open)."""
        old_category = self.category_name
        self._capture_context(editor)
        self._recompute_suggestions()
        if self.category_name != old_category:
            self._presets = self._load_presets()
            self._populate_favorites()
            self._update_results(self.search_bar.text())
        elif not self.search_bar.text().strip():
            # Browse view shows suggestions — keep it current. A typed
            # query is left alone so focus changes never disrupt a search.
            self._update_results("")
        self._refresh_dynamic_ui()

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
            QLabel#insertBadge {
                color: #ffffff; background-color: #7a3fa0;
                border-radius: 4px; padding: 2px 8px;
                font-size: 11px; font-weight: bold;
            }
            QLabel#cheatSheet {
                color: #d8d8d8; background-color: #1c1c1cee;
                border: 1px solid #4a4a4a; border-radius: 6px;
                padding: 10px 14px; font-size: 11px;
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

        self._context_badge = QtWidgets.QLabel("")
        self._context_badge.setObjectName("contextBadge")
        self._context_badge.setToolTip(
            "Node context detected under your cursor / selection")
        header.addWidget(self._context_badge)

        self._insert_badge = QtWidgets.QLabel("")
        self._insert_badge.setObjectName("insertBadge")
        self._insert_badge.setToolTip("A wire is selected — the new node "
                                      "will be spliced into it")
        self._insert_badge.setVisible(False)
        header.addWidget(self._insert_badge)

        self._upstream_label = QtWidgets.QLabel("")
        self._upstream_label.setObjectName("countLabel")
        self._upstream_label.setVisible(False)
        header.addWidget(self._upstream_label)

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

        gear = QtWidgets.QToolButton()
        gear.setObjectName("refreshBtn")
        gear.setText("⚙")
        gear.setToolTip("Lightspeed settings")
        gear.clicked.connect(self._show_settings_menu)
        header.addWidget(gear)
        self._gear_btn = gear
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
        if self.category_name or self.embedded:
            fav_label = QtWidgets.QLabel("FAVORITES")
            fav_label.setObjectName("sectionLabel")
            layout.addWidget(fav_label)

            self.fav_list = QtWidgets.QListWidget()
            self.fav_list.setViewMode(QtWidgets.QListWidget.IconMode)
            self.fav_list.setFlow(QtWidgets.QListView.LeftToRight)
            self.fav_list.setWrapping(True)
            self.fav_list.setResizeMode(QtWidgets.QListWidget.Adjust)
            self.fav_list.setMovement(QtWidgets.QListView.Snap)
            self.fav_list.setWordWrap(False)
            self.fav_list.setSpacing(2)
            self.fav_list.setIconSize(QtCore.QSize(24, 24))
            # Uniform cells: chips land on a predictable grid when dragged
            # and rows stay aligned no matter how long the labels are.
            self.fav_list.setGridSize(QtCore.QSize(FAV_GRID_W, FAV_GRID_H))
            self.fav_list.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOff)   # wrap instead — never pan
            self.fav_list.setVerticalScrollBarPolicy(
                QtCore.Qt.ScrollBarAsNeeded)
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
        self.results.viewport().installEventFilter(self)  # middle-click create
        layout.addWidget(self.results, 1)

        # --- footer: hints + error + size grip ---
        footer = QtWidgets.QHBoxLayout()
        footer.setContentsMargins(2, 0, 0, 0)
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setVisible(False)
        footer.addWidget(self.error_label, 1)

        hints = QtWidgets.QLabel(
            "↵ create    Ctrl+↵ chain    Alt+↵ loose    Ctrl+/ keys")
        hints.setObjectName("hintLabel")
        footer.addWidget(hints)

        grip = QtWidgets.QSizeGrip(self)
        grip.setFixedSize(14, 14)
        footer.addWidget(grip, 0, QtCore.Qt.AlignBottom)
        layout.addLayout(footer)

        self.resize(380, 560)
        self._refresh_dynamic_ui()

    def _refresh_dynamic_ui(self):
        """Sync context-dependent widgets (badges, quick-action enabled
        states, placeholder) with the currently captured context. Called
        after _build_ui and from refresh_context in embedded mode."""
        cat_label = self.category.label() if self.category else "No network"
        self._context_badge.setText(cat_label or self.category_name or "Unknown")

        insert_text = (self._insert_badge_text()
                       if self.insert_connection is not None else "")
        self._insert_badge.setText(insert_text or "")
        self._insert_badge.setVisible(bool(insert_text))

        show_upstream = bool(self.upstream_type) and not insert_text
        if show_upstream:
            self._upstream_label.setText(
                "after %s" % fuzzy.base_name(self.upstream_type))
        self._upstream_label.setVisible(show_upstream)

        self.search_bar.setPlaceholderText("Search %s nodes..." % (
            self.category.label() if self.category else ""))

        for btn, predicate in self._quick_buttons:
            try:
                btn.setEnabled(bool(predicate()))
            except Exception:
                btn.setEnabled(False)

    def _build_quick_actions(self, layout):
        # Popups are context-snapshotted at open; embedded panels build the
        # row regardless and re-evaluate it in _refresh_dynamic_ui().
        self._quick_buttons = []
        if self.network_editor is None and not self.embedded:
            return
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(5)

        def add_btn(text, tooltip, slot, predicate, danger=False):
            btn = QtWidgets.QPushButton(text)
            btn.setObjectName("dangerBtn" if danger else "quickBtn")
            btn.setToolTip(tooltip)
            btn.clicked.connect(slot)
            row.addWidget(btn)
            self._quick_buttons.append((btn, predicate))
            return btn

        add_btn("MERGE", "Merge all selected nodes", self._quick_merge,
                lambda: (len(self.selected_nodes) >= 2
                         and self.index.has(self.category_name, "merge")))
        add_btn("NULL OUT", "Create a display OUT null after the selection",
                self._quick_null,
                lambda: (bool(self.selected_nodes)
                         and self.index.has(self.category_name, "null")))
        add_btn("LAYOUT", "Auto-layout selected nodes (or all when none selected)",
                self._quick_layout,
                lambda: self.network_editor is not None)
        add_btn("★ PRESET", "Save the selected node's parameters (children too, "
                "for subnets) as a reusable preset",
                self._quick_save_preset,
                lambda: len(self.selected_nodes) == 1)
        add_btn("DELETE", "Delete selected node(s)", self._quick_delete,
                lambda: bool(self.selected_nodes), danger=True)
        row.addStretch()
        layout.addLayout(row)

    # ------------------------------------------------------------------
    # Keyboard handling
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self.search_bar and event.type() == QtCore.QEvent.FocusIn:
            # Embedded panels live across context switches — re-anchor to
            # whatever network the user is in when they come back.
            if self.embedded:
                self.refresh_context()
        # Middle-click a result = create & keep the panel open.
        # (getattr: the search bar receives events while _build_ui is still
        # constructing, before self.results exists.)
        results = getattr(self, "results", None)
        if (results is not None and obj is results.viewport()
                and event.type() == QtCore.QEvent.MouseButtonRelease
                and event.button() == QtCore.Qt.MiddleButton):
            pos = (event.position().toPoint() if hasattr(event, "position")
                   else event.pos())
            item = self.results.itemAt(pos)
            if item is not None and item.data(ROLE_KIND) in CREATABLE_KINDS:
                self._activate_item(item, keep_open=True)
                return True
        if (obj is self.search_bar and results is not None
                and event.type() == QtCore.QEvent.KeyPress):
            key = event.key()
            mods = event.modifiers()

            if key in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Up):
                self._move_selection(1 if key == QtCore.Qt.Key_Down else -1)
                return True
            # Tab/Shift+Tab: same as Down/Up — in a search palette nobody
            # wants focus cycling.
            if key == QtCore.Qt.Key_Tab:
                self._move_selection(1)
                return True
            if key == QtCore.Qt.Key_Backtab:
                self._move_selection(-1)
                return True
            if key == QtCore.Qt.Key_PageDown:
                self._move_selection(8)
                return True
            if key == QtCore.Qt.Key_PageUp:
                self._move_selection(-8)
                return True
            # Plain Home/End keep their text-cursor meaning in the field;
            # Ctrl+Home/End jump the result list.
            if key == QtCore.Qt.Key_Home and (mods & QtCore.Qt.ControlModifier):
                self._move_selection_to_edge(first=True)
                return True
            if key == QtCore.Qt.Key_End and (mods & QtCore.Qt.ControlModifier):
                self._move_selection_to_edge(first=False)
                return True
            if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self._flush_debounce()
                keep_open = bool(mods & QtCore.Qt.ControlModifier)
                wire = not bool(mods & QtCore.Qt.AltModifier)
                item = self.results.currentItem() or self._first_node_item()
                if item is not None and item.data(ROLE_KIND) in CREATABLE_KINDS:
                    self._activate_item(item, keep_open=keep_open, wire=wire)
                return True
            # Ctrl+1..9: create the Nth visible result instantly
            if (mods & QtCore.Qt.ControlModifier
                    and QtCore.Qt.Key_1 <= key <= QtCore.Qt.Key_9):
                self._flush_debounce()
                nth = key - QtCore.Qt.Key_1
                rows = self._creatable_rows()
                if nth < len(rows):
                    self._activate_item(self.results.item(rows[nth]))
                return True
            if key == QtCore.Qt.Key_F and (mods & QtCore.Qt.ControlModifier):
                item = self.results.currentItem()
                if item is not None and item.data(ROLE_KIND) == "node":
                    self._toggle_favorite(item.data(ROLE_NAME))
                return True
            if key == QtCore.Qt.Key_F1:
                self._show_help_for_current()
                return True
            if key == QtCore.Qt.Key_Slash and (mods & QtCore.Qt.ControlModifier):
                self._toggle_cheat_sheet()
                return True
        return super(LightspeedPanel, self).eventFilter(obj, event)

    def reject(self):
        """QDialog Esc handling — reached from ANY focused child. Embedded
        panels must never hide (the pane would go permanently blank), and a
        popup with a typed query clears it first — second Esc closes."""
        if self.embedded or self.search_bar.text():
            self.search_bar.clear()
            self.search_bar.setFocus()
            return
        super(LightspeedPanel, self).reject()

    def _dismiss(self):
        """Close after an action — no-op shell reset in embedded mode."""
        if self.embedded:
            self.search_bar.clear()
            self.search_bar.setFocus()
        else:
            self.close()

    def _flush_debounce(self):
        """Apply a pending re-query so shortcuts act on the current text."""
        if self._debounce.isActive():
            self._debounce.stop()
            self._update_results(self.search_bar.text())

    def _creatable_rows(self):
        return [i for i in range(self.results.count())
                if self.results.item(i).data(ROLE_KIND) in CREATABLE_KINDS]

    def _activate_item(self, item, keep_open=False, wire=True):
        """Create from a result row (node or preset). This is the only
        creation path driven by the typed query, so only here does the
        parsed inline name apply — favorite chips and quick actions
        must never inherit it."""
        self.create_node(item.data(ROLE_NAME), keep_open=keep_open,
                         preset_item=item.data(ROLE_PRESET),
                         node_name=self.pending_name, wire=wire)

    def _first_node_item(self):
        for i in range(self.results.count()):
            if self.results.item(i).data(ROLE_KIND) in CREATABLE_KINDS:
                return self.results.item(i)
        return None

    def _move_selection(self, delta):
        rows = self._creatable_rows()
        if not rows:
            return
        current = self.results.currentRow()
        if current in rows:
            pos = rows.index(current)
            if abs(delta) == 1:
                pos = (pos + delta) % len(rows)   # single steps wrap around
            else:
                pos = max(0, min(len(rows) - 1, pos + delta))
        else:
            pos = 0 if delta >= 0 else len(rows) - 1
        self.results.setCurrentRow(rows[pos])
        self.results.scrollToItem(self.results.item(rows[pos]),
                                  QtWidgets.QAbstractItemView.EnsureVisible)

    def _move_selection_to_edge(self, first):
        rows = self._creatable_rows()
        if not rows:
            return
        row = rows[0] if first else rows[-1]
        self.results.setCurrentRow(row)
        self.results.scrollToItem(self.results.item(row),
                                  QtWidgets.QAbstractItemView.EnsureVisible)

    def showEvent(self, event):
        super(LightspeedPanel, self).showEvent(event)
        self.search_bar.setFocus()

    def closeEvent(self, event):
        if not self.embedded:
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
        tooltip += "\nF1 for node help"
        item.setToolTip(tooltip)
        self.results.addItem(item)

    def _add_preset_item(self, preset):
        entry = self.index.entry(self.category_name, preset.type_name)
        item = QtWidgets.QListWidgetItem()
        item.setData(ROLE_KIND, "preset")
        item.setData(ROLE_NAME, entry.name if entry else preset.type_name)
        item.setData(ROLE_LABEL, preset.label)
        # The PresetItem itself rides on the row — no index into a parallel
        # list that could go stale between refreshes.
        item.setData(ROLE_PRESET, preset)
        item.setData(ROLE_SUGGESTED, False)
        item.setData(ROLE_FAVORITE, False)
        if entry:
            item.setData(QtCore.Qt.DecorationRole, get_icon(entry.icon))
        item.setToolTip("%s\nCreates a %s with saved parameters"
                        % (preset.label, preset.type_name))
        self.results.addItem(item)

    def _parse_query(self, text):
        """
        Split '<search> <NAME>' into (search, name). The trailing token only
        counts as a node name when it contains an underscore
        ('null OUT_TEXT', 'cam RENDER_CAM'), so fuzzy multi-word queries
        ('copy points') and uppercase vocabulary ('convert VDB',
        'import USD') are never eaten.
        """
        tokens = text.strip().split()
        if len(tokens) >= 2:
            candidate = tokens[-1]
            if NAME_TOKEN_RE.match(candidate):
                return " ".join(tokens[:-1]), candidate
        return text.strip(), None

    def _update_results(self, text):
        self.results.clear()
        self._clear_error()
        self._fav_cache = self._favorite_names()
        entries = self._entries()

        if not entries:
            self._add_info("No creatable nodes here — dive into a network.")
            self.count_label.setText("")
            return

        query, self.pending_name = self._parse_query(text)
        suggested_set = set(self.suggested_bases)

        if not query:
            self._populate_browse_view(entries, suggested_set)
        else:
            self._populate_search_view(entries, query, suggested_set)

        if self.pending_name:
            self.count_label.setText("%s   →  name: %s" % (
                self.count_label.text(), self.pending_name))

        # Ctrl+1..9 badges on the first nine creatable rows
        for n, row in enumerate(self._creatable_rows()[:9], start=1):
            self.results.item(row).setData(ROLE_ORDINAL, n)

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

        # After SUGGESTED/FREQUENT so a bare Enter still creates a plain
        # node, never a preset the user didn't aim at.
        if self._presets:
            self._add_header("PRESETS")
            for p in self._presets[:6]:
                self._add_preset_item(p)
            if len(self._presets) > 6:
                self._add_info("… %d more presets — type to filter"
                               % (len(self._presets) - 6))

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

        # Presets matched by label or node type, merged into the same
        # ranked list (slightly boosted — a named preset is a strong hit).
        preset_rows = []
        for p in self._presets:
            s, _ = fuzzy.score(query, p.type_name, p.label)
            if s is not None:
                preset_rows.append((max(0.0, s - 0.1), p))

        if not ranked and not preset_rows:
            self._add_info("No matches for '%s'" % query)
            self._add_cross_context_hints(query, alias_hits)
            self.count_label.setText("0 matches")
            return

        merged = ([(r["score"], "node", r) for r in ranked]
                  + [(s, "preset", p) for s, p in preset_rows])
        merged.sort(key=lambda t: t[0])

        for _score, kind, payload in merged:
            if kind == "node":
                entry = payload["entry"]
                self._add_node_item(entry, alias=payload["alias"],
                                    suggested=entry.base in suggested_set)
            else:
                self._add_preset_item(payload)

        n = len(merged)
        self.count_label.setText("%d match%s" % (n, "" if n == 1 else "es"))

    def _add_cross_context_hints(self, query, alias_hits=None):
        """On a dead-end search, say where else the node lives
        ('Flow Solver — Copernicus'). Discovery rows, not creatable.
        Only runs on ZERO matches — it ranks every other category's
        entries, too costly for the per-keystroke path otherwise."""
        hits = []
        try:
            if alias_hits is None:
                alias_hits = aliases.alias_hits_for_query(query)
            for cat_name in self.index.categories():
                if cat_name == self.category_name:
                    continue
                ranked = fuzzy.rank(self.index.entries(cat_name), query,
                                    alias_hits=alias_hits, limit=1)
                # Only strong matches — noise here is worse than nothing
                if ranked and ranked[0]["score"] <= 4.0:
                    hits.append((ranked[0]["score"], cat_name,
                                 ranked[0]["entry"]))
        except Exception:
            traceback.print_exc()
            return
        if not hits:
            return
        hits.sort(key=lambda h: h[0])
        self._add_header("IN OTHER CONTEXTS")
        try:
            cats = hou.nodeTypeCategories()
        except hou.Error:
            cats = {}
        for _s, cat_name, entry in hits[:3]:
            cat = cats.get(cat_name)
            cat_label = cat.label() if cat else cat_name
            self._add_info("%s  (%s)  —  in %s"
                           % (entry.label, entry.name, cat_label))

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------

    def _populate_favorites(self):
        if self.fav_list is None:
            return
        self.fav_list.clear()
        names = (self.fav_manager.get_favorites(self.category_name)
                 if self.category_name else [])
        fm = QtGui.QFontMetrics(self.fav_list.font())
        for name in names:
            entry = self.index.entry(self.category_name, name)
            label = entry.label if entry else name
            display = fm.elidedText(label, QtCore.Qt.ElideRight, FAV_GRID_W - 6)
            icon = get_icon(entry.icon) if entry else QtGui.QIcon()
            item = QtWidgets.QListWidgetItem(icon, display)
            item.setData(ROLE_NAME, entry.name if entry else name)
            item.setToolTip("%s  (%s)\nClick to create • right-click to remove"
                            % (label, name))
            self.fav_list.addItem(item)
        if not names:
            hint = QtWidgets.QListWidgetItem(
                "right-click a result to add favorites")
            hint.setFlags(QtCore.Qt.NoItemFlags)
            self.fav_list.addItem(hint)
        self._sync_favorites_height()

    def _sync_favorites_height(self):
        """Fit the chip area to its content: one row when it fits, up to
        FAV_MAX_ROWS before scrolling vertically (never horizontally)."""
        if self.fav_list is None:
            return
        count = max(1, self.fav_list.count())
        width = self.fav_list.viewport().width()
        if width < FAV_GRID_W:            # not laid out yet — estimate
            width = max(self.width() - 40, FAV_GRID_W)
        per_row = max(1, width // (FAV_GRID_W + 2))
        rows = min(FAV_MAX_ROWS, (count + per_row - 1) // per_row)
        self.fav_list.setFixedHeight(rows * (FAV_GRID_H + 2) + 6)

    def resizeEvent(self, event):
        super(LightspeedPanel, self).resizeEvent(event)
        # Chips-per-row changes with width; keep the row count honest
        if getattr(self, "fav_list", None) is not None:
            self._sync_favorites_height()

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
        # Icon-mode drops leave the dragged chip wherever it landed;
        # rebuild once the drop finishes so the grid is clean again.
        QtCore.QTimer.singleShot(0, self._populate_favorites)

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
        if not item:
            return
        kind = item.data(ROLE_KIND)
        if kind == "preset":
            preset = item.data(ROLE_PRESET)
            menu = QtWidgets.QMenu(self)
            create = menu.addAction("Create with Preset")
            create.triggered.connect(lambda: self._activate_item(item))
            delete = menu.addAction("Delete Preset")
            delete.triggered.connect(lambda: self._delete_preset(preset))
            qt.exec_menu(menu, self.results.mapToGlobal(pos))
            return
        if kind != "node":
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
        help_act = menu.addAction("Node Help  (F1)")
        help_act.triggered.connect(lambda: self._show_node_help(name))
        qt.exec_menu(menu, self.results.mapToGlobal(pos))

    def _delete_preset(self, preset):
        if preset is None:
            return
        if presets.remove(preset):
            self._presets = self._load_presets()
            self._update_results(self.search_bar.text())
        else:
            self._show_error("Couldn't delete preset — see console.")

    # ------------------------------------------------------------------
    # Node creation
    # ------------------------------------------------------------------

    def _on_result_activated(self, item):
        if item.data(ROLE_KIND) in CREATABLE_KINDS:
            mods = QtWidgets.QApplication.keyboardModifiers()
            keep = bool(mods & QtCore.Qt.ControlModifier)
            wire = not bool(mods & QtCore.Qt.AltModifier)
            self._activate_item(item, keep_open=keep, wire=wire)

    def create_node(self, type_name, keep_open=False, preset_item=None,
                    node_name=None, wire=True):
        """wire=False (Alt+Enter) drops the node loose: no auto-wiring, no
        wire splice, and the display/render flags stay where they are."""
        # A docked panel outlives the context it captured — re-anchor to
        # the network/selection/wire as they are right now.
        if self.embedded:
            self._capture_context()
            self._refresh_dynamic_ui()

        if self.network_editor is None:
            self._show_error("No network editor found — nowhere to create.")
            return
        self._clear_error()

        entry = self.index.entry(self.category_name, type_name)
        label = entry.label if entry else type_name
        if preset_item is not None:
            label = "%s (%s)" % (preset_item.label, label)
        upstream = self.upstream_type
        insert_into = self.insert_connection if wire else None

        # Resolve the wire BEFORE creating anything: a failure here must
        # not leave an orphaned node behind.
        endpoints = None
        if insert_into is not None:
            if entry and entry.max_inputs == 0:
                self._show_error(
                    "%s has no inputs — can't splice it into a wire." % label)
                return
            try:
                endpoints = self._connection_endpoints(insert_into)
            except (AttributeError, hou.Error):
                endpoints = None
            if endpoints is None:
                self._show_error("Selected wire can't be spliced "
                                 "(was it rewired or deleted?)")
                self.insert_connection = None
                return
            # The wire's upstream node is the true "previous node" for the
            # learning engine — a selected wire means no selected node.
            try:
                upstream = endpoints[0].type().name()
            except hou.Error:
                pass

        preset_ok = True
        stolen = []
        try:
            with hou.undos.group("Lightspeed: create %s" % label):
                parent = self.network_editor.pwd()
                new_node = parent.createNode(type_name)

                if node_name:
                    try:
                        new_node.setName(node_name, unique_name=True)
                    except hou.Error:
                        pass

                if preset_item is not None:
                    preset_ok = presets.apply_to_node(preset_item, new_node)

                if endpoints is not None:
                    splice_node_into(new_node, endpoints)
                elif wire:
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
                    # Chain insertion: a single selected node with nodes
                    # after it means "put the new node BETWEEN them", not
                    # "branch off". Needs the new node to pass data through
                    # (an output and the wiring above succeeded).
                    if (wired == 1 and len(self.selected_nodes) == 1
                            and (entry is None or entry.max_outputs != 0)):
                        stolen = steal_downstream(
                            self.selected_nodes[0], new_node)
                    if stolen:
                        place_between(new_node, self.selected_nodes[0], stolen)
                    else:
                        self._place_node(new_node, wired)
                else:
                    # Loose create (Alt+Enter): drop at the network cursor
                    self._place_node(new_node, wired=0, prefer_cursor=True)

                new_node.setSelected(True, clear_all_selected=True)
                try:
                    self.network_editor.setCurrentNode(new_node)
                except hou.Error:
                    pass
                # When splicing into a wire, inserting mid-chain, or
                # dropping a loose node, leave the display/render flags
                # where they are.
                if insert_into is None and wire and not stolen:
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

        # An inserted wire is consumed; don't splice the next chain-create
        # into a connection that no longer exists.
        self.insert_connection = None

        if not preset_ok:
            self._show_error("%s created, but the preset failed to apply "
                             "— see console." % label)

        # Learn from this creation
        try:
            self.engine.record_creation(self.category_name, upstream, type_name)
        except Exception:
            traceback.print_exc()

        if endpoints is not None or stolen:
            flash = "%s inserted" % label
        else:
            flash = "%s created" % label
        self._flash(flash)

        if keep_open or self.embedded:
            # Chain mode: the new node becomes the anchor for the next create.
            self.selected_nodes = [new_node]
            self._recompute_suggestions()
            self._refresh_dynamic_ui()   # keep the "after <node>" badge live
            self.search_bar.clear()
            self._update_results("")
            self.search_bar.setFocus()
        else:
            self.close()

    def _insert_badge_text(self):
        try:
            endpoints = self._connection_endpoints(self.insert_connection)
        except (AttributeError, hou.Error):
            endpoints = None
        if endpoints is None:
            return "insert into wire"
        up, _oi, down, _ii = endpoints
        return "insert: %s → %s" % (up.name(), down.name())

    def _flash(self, message, seconds=1.2):
        """Non-blocking confirmation in the network editor, best-effort."""
        try:
            self.network_editor.flashMessage(None, message, seconds)
        except (AttributeError, hou.Error):
            pass

    def _place_node(self, new_node, wired, prefer_cursor=False):
        try:
            if prefer_cursor and self.cursor_pos is not None:
                new_node.setPosition(self.cursor_pos)
            elif wired and self.selected_nodes:
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

    def _refresh_for_action(self):
        """Docked panels act on the LIVE selection, not the one captured at
        the last focus change — quick actions like DELETE must never hit
        stale nodes."""
        if self.embedded:
            self._capture_context()
            self._refresh_dynamic_ui()

    def _quick_merge(self):
        self._refresh_for_action()
        sel = self.selected_nodes
        if len(sel) < 2 or self.network_editor is None:
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
            self._dismiss()
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Merge failed: %s" % exc)

    def _quick_null(self):
        self._refresh_for_action()
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
            self._dismiss()
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Null OUT failed: %s" % exc)

    def _quick_layout(self):
        self._refresh_for_action()
        if self.network_editor is None:
            return
        try:
            with hou.undos.group("Lightspeed: layout"):
                parent = self.network_editor.pwd()
                if self.selected_nodes:
                    parent.layoutChildren(items=self.selected_nodes)
                else:
                    parent.layoutChildren()
            self._dismiss()
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Layout failed: %s" % exc)

    def _quick_delete(self):
        self._refresh_for_action()
        sel = self.selected_nodes
        if not sel:
            self._dismiss()
            return
        try:
            with hou.undos.group("Lightspeed: delete selection"):
                for node in sel:
                    node.destroy()
            self.selected_nodes = []
            self._dismiss()
        except hou.Error as exc:
            traceback.print_exc()
            self._show_error("Delete failed: %s" % exc)

    def _on_refresh_index(self):
        self.index.refresh()
        self._presets = self._load_presets(force=True)
        self._update_results(self.search_bar.text())
        self._populate_favorites()

    def _quick_save_preset(self):
        self._refresh_for_action()
        if len(self.selected_nodes) != 1:
            return
        node = self.selected_nodes[0]
        default = "%s preset" % node.type().description()
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Preset",
            "Preset name for %s:" % node.path(), text=default)
        name = (name or "").strip()
        if not ok or not name:
            return
        try:
            presets.capture(name, node)
        except (AttributeError, hou.Error) as exc:
            traceback.print_exc()
            self._show_error("Couldn't save preset: %s" % exc)
            return
        self._presets = self._load_presets()
        self._update_results(self.search_bar.text())
        self._flash("Preset '%s' saved" % name)

    # ------------------------------------------------------------------
    # Settings / help
    # ------------------------------------------------------------------

    def _show_settings_menu(self):
        menu = QtWidgets.QMenu(self)
        tab_act = menu.addAction("Open Lightspeed with TAB (replaces TAB menu)")
        tab_act.setCheckable(True)
        tab_act.setChecked(bool(self.settings.get("tab_hook")))
        tab_act.toggled.connect(self._set_tab_hook)
        menu.addSeparator()
        if self.category_name:
            cat_label = self.category.label() if self.category else self.category_name
            forget_here = menu.addAction(
                "Forget Learned Suggestions in %s" % cat_label)
            forget_here.triggered.connect(
                lambda: self._forget_learned(self.category_name))
        forget_all = menu.addAction("Forget All Learned Suggestions…")
        forget_all.triggered.connect(lambda: self._forget_learned(None))
        menu.addSeparator()
        keys_act = menu.addAction("Keyboard Shortcuts   (Ctrl+/)")
        keys_act.triggered.connect(self._toggle_cheat_sheet)
        qt.exec_menu(menu, self._gear_btn.mapToGlobal(
            QtCore.QPoint(0, self._gear_btn.height())))

    def _forget_learned(self, category_name):
        """Reset the usage-learned suggestion data (curated seeds stay)."""
        if category_name is None:
            # Wiping every context is the one destructive settings action —
            # confirm it. Per-context resets are cheap to re-learn.
            box = QtWidgets.QMessageBox(self)
            box.setWindowTitle("Lightspeed")
            box.setText("Forget everything Lightspeed has learned about "
                        "your node habits, in all contexts?")
            box.setStandardButtons(QtWidgets.QMessageBox.Yes
                                   | QtWidgets.QMessageBox.No)
            box.setDefaultButton(QtWidgets.QMessageBox.No)
            exec_fn = getattr(box, "exec", None) or box.exec_
            if exec_fn() != QtWidgets.QMessageBox.Yes:
                return
        try:
            self.engine.reset(category_name)
        except Exception as exc:
            traceback.print_exc()
            self._show_error("Couldn't reset suggestions: %s" % exc)
            return
        self._recompute_suggestions()
        self._update_results(self.search_bar.text())
        self._flash("Learned suggestions cleared")

    def _set_tab_hook(self, enabled):
        self.settings["tab_hook"] = bool(enabled)
        store.save_json(SETTINGS_FILE, self.settings)
        msg = ("TAB now opens Lightspeed in network editors "
               "(run the shelf tool once per session so the hook is loaded)"
               if enabled else "TAB restored to the native menu")
        try:
            hou.ui.setStatusMessage("Lightspeed: %s" % msg)
        except (AttributeError, hou.Error):
            pass

    CHEAT_SHEET = (
        "<b>Lightspeed shortcuts</b><br>"
        "<table cellspacing='4'>"
        "<tr><td><code>↵</code></td><td>create highlighted</td></tr>"
        "<tr><td><code>Ctrl+↵</code> / middle-click</td><td>create &amp; keep open (chain)</td></tr>"
        "<tr><td><code>Alt+↵</code></td><td>create loose (no wiring)</td></tr>"
        "<tr><td><code>Ctrl+1…9</code></td><td>create numbered result</td></tr>"
        "<tr><td><code>↑ ↓ Tab PgUp PgDn</code></td><td>choose result (wraps)</td></tr>"
        "<tr><td><code>Ctrl+Home/End</code></td><td>first / last result</td></tr>"
        "<tr><td><code>Ctrl+F</code></td><td>toggle favorite ★</td></tr>"
        "<tr><td><code>F1</code></td><td>node help</td></tr>"
        "<tr><td><code>Ctrl+/</code></td><td>this cheat sheet</td></tr>"
        "<tr><td><code>Esc</code></td><td>clear query, then close</td></tr>"
        "</table><br>"
        "<b>Tricks</b><br>"
        "• <code>null OUT_TEXT</code> — a trailing token with an "
        "underscore names the node<br>"
        "• create after a mid-chain node — it's inserted INTO the chain "
        "(downstream rewired); <code>Alt+↵</code> if you wanted it loose<br>"
        "• select a wire first — the new node is spliced into it<br>"
        "• search in C4D/AE/Blender/Maya words: <i>cloner, wiggle, "
        "turbosmooth…</i><br>"
        "• <code>★ PRESET</code> saves the selected node's parms as a "
        "reusable preset"
    )

    def _toggle_cheat_sheet(self):
        sheet = getattr(self, "_cheat_sheet", None)
        if sheet is None:
            sheet = QtWidgets.QLabel(self.CHEAT_SHEET, self)
            sheet.setObjectName("cheatSheet")
            sheet.setTextFormat(QtCore.Qt.RichText)
            sheet.setWordWrap(True)
            self._cheat_sheet = sheet
        if sheet.isVisible():
            sheet.hide()
            return
        sheet.adjustSize()
        w = min(sheet.width(), self.width() - 24)
        sheet.resize(w, sheet.heightForWidth(w) or sheet.height())
        sheet.move((self.width() - sheet.width()) // 2,
                   (self.height() - sheet.height()) // 2)
        sheet.raise_()
        sheet.show()

    def _show_help_for_current(self):
        item = self.results.currentItem()
        if item is not None and item.data(ROLE_KIND) in CREATABLE_KINDS:
            self._show_node_help(item.data(ROLE_NAME))

    def _show_node_help(self, type_name):
        if self.category is None:
            return
        try:
            node_type = hou.nodeType(self.category, type_name)
        except hou.Error:
            node_type = None
        if node_type is None:
            entry = self.index.entry(self.category_name, type_name)
            if entry is not None:
                try:
                    node_type = hou.nodeType(self.category, entry.name)
                except hou.Error:
                    node_type = None
        if node_type is None:
            self._show_error("No help found for %s" % type_name)
            return
        shown = False
        display_help = getattr(hou.ui, "displayNodeHelp", None)
        if display_help is not None:
            try:
                display_help(node_type)
                shown = True
            except hou.Error:
                pass
        if not shown:
            # Fallback: open the docs page in the desktop help browser
            try:
                hou.ui.curDesktop().displayHelpPath(node_type.defaultHelpUrl())
                shown = True
            except (AttributeError, hou.Error):
                pass
        if not shown:
            self._show_error("Couldn't open help for %s" % type_name)

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

    def _clear_error(self):
        """Errors describe the LAST action — clear on the next query or
        successful create so a stale message can't outlive its cause."""
        if self.error_label.isVisible():
            self.error_label.setText("")
            self.error_label.setVisible(False)

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
