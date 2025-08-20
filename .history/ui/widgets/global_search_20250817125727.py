# fsm_designer_project/ui/widgets/global_search.py
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                             QLineEdit, QGraphicsItem, QStyle, QLabel, QHBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QEvent, QTimer, QSize
from PyQt6.QtGui import QKeyEvent, QAction, QColor, QPalette, QIcon

from ...utils.theme_config import theme_config

logger = logging.getLogger(__name__)


class SearchResultItemWidget(QWidget):
    """A custom widget for displaying a single search result with icon, title, and subtitle."""

    def __init__(self, icon, text, subtitle, parent=None):
        super().__init__(parent)
        from ...utils.config import APP_FONT_SIZE_SMALL

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(QSize(16, 16)))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(text)
        self.title_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_PRIMARY}; font-weight: 500;")
        text_layout.addWidget(self.title_label)

        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setStyleSheet(f"color: {theme_config.COLOR_TEXT_SECONDARY}; font-size: {APP_FONT_SIZE_SMALL};")
            text_layout.addWidget(self.subtitle_label)

        layout.addLayout(text_layout)
        layout.addStretch()


class GlobalSearchHandler(QWidget):
    """Manages the logic and UI for the global search/command palette."""

    def __init__(self, main_window, search_bar: QLineEdit):
        super().__init__(main_window, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.mw = main_window
        self.search_bar = search_bar

        # Debounce timer to avoid searching on every single keystroke
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(150)  # 150ms delay
        self.search_timer.timeout.connect(self._update_search_results)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setFixedWidth(self.search_bar.width() + 200)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Add a subtle shadow for a modern look
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        self.results_list = QListWidget()
        self.results_list.setObjectName("GlobalSearchResults")
        self.results_list.setStyleSheet(f"""
            QListWidget#GlobalSearchResults {{
                border: 1px solid {theme_config.COLOR_BORDER_MEDIUM};
                border-radius: 5px;
                background-color: {theme_config.COLOR_BACKGROUND_LIGHT};
                outline: none;
            }}
            QListWidget::item {{
                padding: 0px;
                margin: 1px 2px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {theme_config.COLOR_ACCENT_PRIMARY_LIGHT};
                border: 1px solid {theme_config.COLOR_ACCENT_PRIMARY};
            }}
        """)
        layout.addWidget(self.results_list)

    def _connect_signals(self):
        self.search_bar.textChanged.connect(self.search_timer.start)
        self.search_bar.installEventFilter(self)
        self.results_list.itemActivated.connect(self._on_item_activated)

    def _gather_searchable_items(self) -> list:
        """Collects all items and commands that can be searched."""
        from ...ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        items = []
        editor = self.mw.current_editor()

        # 1. Diagram Items
        if editor:
            for item in editor.scene.items():
                if isinstance(item, GraphicsStateItem):
                    items.append({"type": "State", "text": item.text_label, "subtitle": item.description, "data": item})
                elif isinstance(item, GraphicsTransitionItem):
                    label = item._compose_label_string()
                    items.append({"type": "Transition", "text": label, "subtitle": f"From '{item.start_item.text_label}' to '{item.end_item.text_label}'", "data": item})
                elif isinstance(item, GraphicsCommentItem):
                    text = item.toPlainText().replace('\n', ' ')
                    items.append({"type": "Comment", "text": f"{text[:40]}...", "subtitle": "Comment Item", "data": item})

        # 2. Application Actions (Commands)
        all_actions = self.mw.findChildren(QAction)
        for action in all_actions:
            text = action.text().replace('&', '')
            if text and not action.menu() and action.isEnabled():
                items.append({"type": "Command", "text": text, "subtitle": action.statusTip() or "Application Command", "data": action})

        return items

    def _update_search_results(self):
        search_text = self.search_bar.text().strip().lower()
        from ...utils import get_standard_icon

        if not search_text:
            self.hide()
            return

        self.results_list.clear()
        all_items = self._gather_searchable_items()

        # Filter items based on text and subtitle
        filtered_items = [
            item for item in all_items if search_text in item["text"].lower() or (item.get("subtitle") and search_text in item["subtitle"].lower())
        ]

        if not filtered_items:
            self.hide()
            return

        # Group by type for better presentation
        grouped_items = {}
        for item in filtered_items:
            type_key = item["type"]
            if type_key not in grouped_items:
                grouped_items[type_key] = []
            grouped_items[type_key].append(item)

        # Populate list with categories
        category_order = ["Command", "State", "Transition", "Comment"]
        for category in category_order:
            if category in grouped_items:
                # Add category header
                header_item = QListWidgetItem(f"  {category.upper()}")
                header_item.setFlags(header_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                font = header_item.font()
                font.setBold(True)
                font.setPointSize(font.pointSize() - 1)
                header_item.setFont(font)
                self.results_list.addItem(header_item)

                # Add items for this category
                for item in grouped_items[category]:
                    list_item = QListWidgetItem()
                    list_item.setData(Qt.ItemDataRole.UserRole, item)  # Store the whole dictionary

                    icon = self._get_icon_for_item_type(item["type"])
                    item_widget = SearchResultItemWidget(icon, item["text"], item.get("subtitle", ""))
                    
                    list_item.setSizeHint(item_widget.sizeHint())
                    self.results_list.addItem(list_item)
                    self.results_list.setItemWidget(list_item, item_widget)

        # Position and show the popup
        pos = self.search_bar.mapToGlobal(self.search_bar.rect().bottomLeft())
        self.move(pos.x(), pos.y() + 2) # Add a small gap
        self.results_list.setCurrentRow(1) # Select first actual item
        self.show()

    def _get_icon_for_item_type(self, item_type: str) -> QIcon:
        """Returns a standard icon based on the item type string."""
        from ...utils import get_standard_icon
        icon_map = {
            "State": (QStyle.StandardPixmap.SP_FileIcon, "St"),
            "Transition": (QStyle.StandardPixmap.SP_ArrowForward, "Tr"),
            "Comment": (QStyle.StandardPixmap.SP_MessageBoxInformation, "Cm"),
            "Command": (QStyle.StandardPixmap.SP_CommandLink, "Cmd"),
        }
        icon_enum, alt = icon_map.get(item_type, (QStyle.StandardPixmap.SP_CustomBase, ""))
        return get_standard_icon(icon_enum, alt)

    def _on_item_activated(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        data_obj = item_data["data"]

        if isinstance(data_obj, QGraphicsItem):
            self.mw.focus_on_item(data_obj)
        elif isinstance(data_obj, QAction):
            data_obj.trigger()

        self.search_bar.clear()
        self.hide()

    def eventFilter(self, source, event: QEvent) -> bool:
        if source == self.search_bar and event.type() == QEvent.Type.KeyPress:
            # --- FIX: The 'event' object is already a QKeyEvent, no need to create a new one. ---
            key_event = event
            key = key_event.key()

            if self.isVisible():
                if key == Qt.Key.Key_Down:
                    current = self.results_list.currentRow()
                    next_row = (current + 1) % self.results_list.count()
                    while self.results_list.item(next_row).flags() & Qt.ItemFlag.ItemIsSelectable == Qt.ItemFlag.NoItemFlags:
                        next_row = (next_row + 1) % self.results_list.count()
                    self.results_list.setCurrentRow(next_row)
                    return True
                elif key == Qt.Key.Key_Up:
                    current = self.results_list.currentRow()
                    next_row = (current - 1 + self.results_list.count()) % self.results_list.count()
                    while self.results_list.item(next_row).flags() & Qt.ItemFlag.ItemIsSelectable == Qt.ItemFlag.NoItemFlags:
                        next_row = (next_row - 1 + self.results_list.count()) % self.results_list.count()
                    self.results_list.setCurrentRow(next_row)
                    return True
                elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    if item := self.results_list.currentItem():
                        self._on_item_activated(item)
                    return True
                elif key == Qt.Key.Key_Escape:
                    self.search_bar.clear()
                    self.hide()
                    return True

        return super().eventFilter(source, event)