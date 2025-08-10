# fsm_designer_project/ui/widgets/global_search.py
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLineEdit, QGraphicsItem, QStyle
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QKeyEvent, QAction


logger = logging.getLogger(__name__)

class GlobalSearchHandler(QWidget):
    """Manages the logic and UI for the global search/command palette."""

    def __init__(self, main_window, search_bar: QLineEdit):
        super().__init__(main_window, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.mw = main_window
        self.search_bar = search_bar

        # Debounce timer to avoid searching on every single keystroke
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(150) # 150ms delay
        self.search_timer.timeout.connect(self._update_search_results)

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # --- DEFERRED IMPORTS to break circular dependency ---
        from ...codegen.config import COLOR_BACKGROUND_LIGHT, COLOR_ACCENT_PRIMARY_LIGHT, COLOR_TEXT_PRIMARY, COLOR_ACCENT_PRIMARY
        # --- END DEFERRED IMPORTS ---
        self.setFixedWidth(self.search_bar.width() + 150)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        self.results_list = QListWidget()
        self.results_list.setObjectName("GlobalSearchResults")
        self.results_list.setStyleSheet(f"""
            QListWidget#GlobalSearchResults {{
                border: 1px solid {COLOR_ACCENT_PRIMARY};
                background-color: {COLOR_BACKGROUND_LIGHT};
            }}
            QListWidget::item {{
                padding: 6px;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
                color: {COLOR_TEXT_PRIMARY};
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.results_list)

    def _connect_signals(self):
        self.search_bar.textChanged.connect(self.search_timer.start)
        self.search_bar.installEventFilter(self)
        self.results_list.itemActivated.connect(self._on_item_activated)

    def _gather_searchable_items(self) -> list:
        """Collects all items and commands that can be searched."""
        # --- DEFERRED IMPORTS to break circular dependency ---
        from ...ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        # --- END DEFERRED IMPORTS ---
        items = []
        editor = self.mw.current_editor()

        # 1. Diagram Items
        if editor:
            for item in editor.scene.items():
                if isinstance(item, GraphicsStateItem):
                    items.append({"type": "State", "text": f"State: {item.text_label}", "data": item})
                elif isinstance(item, GraphicsTransitionItem):
                    label = item._compose_label_string()
                    items.append({"type": "Transition", "text": f"Transition: {label}", "data": item})
                elif isinstance(item, GraphicsCommentItem):
                    text = item.toPlainText().split('\n')[0]
                    items.append({"type": "Comment", "text": f"Comment: {text[:40]}...", "data": item})
        
        # 2. Application Actions (Commands)
        all_actions = self.mw.findChildren(QAction)
        for action in all_actions:
            if action.text() and not action.menu() and action.isEnabled():
                items.append({"type": "Command", "text": f"Cmd: {action.text().replace('&', '')}", "data": action})

        return items
    
    def _update_search_results(self):
        search_text = self.search_bar.text().strip().lower()
        # --- DEFERRED IMPORTS to break circular dependency ---
        from ...codegen import get_standard_icon
        # --- END DEFERRED IMPORTS ---

        if not search_text:
            self.hide()
            return
            
        self.results_list.clear()
        all_items = self._gather_searchable_items()
        
        # Filter items
        filtered_items = [
            item for item in all_items if search_text in item["text"].lower()
        ]

        if not filtered_items:
            self.hide()
            return
            
        # Populate list
        for item in filtered_items:
            list_item = QListWidgetItem(item["text"])
            list_item.setData(Qt.ItemDataRole.UserRole, item) # Store the whole dictionary
            # Set icons based on type
            if item["type"] == "State": list_item.setIcon(get_standard_icon(QStyle.StandardPixmap.SP_FileDialogNewFolder, "St"))
            elif item["type"] == "Transition": list_item.setIcon(get_standard_icon(QStyle.StandardPixmap.SP_ArrowForward, "Tr"))
            elif item["type"] == "Command": list_item.setIcon(get_standard_icon(QStyle.StandardPixmap.SP_CommandLink, "Cmd"))
            self.results_list.addItem(list_item)
        
        # Position and show the popup
        pos = self.search_bar.mapToGlobal(self.search_bar.rect().bottomLeft())
        self.move(pos)
        self.results_list.setCurrentRow(0)
        self.show()

    def _on_item_activated(self, item: QListWidgetItem):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not item_data: return

        data_obj = item_data["data"]
        
        if isinstance(data_obj, QGraphicsItem):
            self.mw.focus_on_item(data_obj)
        elif isinstance(data_obj, QAction):
            data_obj.trigger()
            
        self.search_bar.clear()
        self.hide()

    def eventFilter(self, source, event: QEvent) -> bool:
        if source == self.search_bar and event.type() == QEvent.Type.KeyPress:
            key_event = QKeyEvent(event)
            key = key_event.key()
            
            if self.isVisible():
                if key == Qt.Key.Key_Down:
                    current = self.results_list.currentRow()
                    self.results_list.setCurrentRow((current + 1) % self.results_list.count())
                    return True
                elif key == Qt.Key.Key_Up:
                    current = self.results_list.currentRow()
                    self.results_list.setCurrentRow((current - 1 + self.results_list.count()) % self.results_list.count())
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