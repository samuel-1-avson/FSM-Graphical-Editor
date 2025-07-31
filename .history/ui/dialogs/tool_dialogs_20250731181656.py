# fsm_designer_project/ui/dialogs/tool_dialogs.py

import sys
import platform
import psutil
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton, QDialogButtonBox,
    QHBoxLayout, QLabel, QStyle, QListWidget, QListWidgetItem,
    QGraphicsItem, QLineEdit, QComboBox, QTextEdit, QGraphicsScene, QGraphicsView, QMessageBox, QAction,
    QTabWidget, QWidget, QTextBrowser
)
from PyQt5.QtGui import QIcon, QKeyEvent, QPixmap, QPainter, QDesktopServices
from PyQt5.QtCore import Qt, pyqtSignal, QVariant, QStandardPaths, QUrl

from ..widgets.code_editor import CodeEditor
from ...utils import get_standard_icon
from ...core.snippet_manager import CustomSnippetManager
from ...utils.fsm_importer import parse_plantuml, parse_mermaid
from ...assets.assets import MECHATRONICS_SNIPPETS
from ...utils.config import APP_NAME, APP_VERSION, COLOR_BACKGROUND_DIALOG, COLOR_ACCENT_PRIMARY, COLOR_TEXT_PRIMARY, COLOR_BORDER_LIGHT, COLOR_BACKGROUND_LIGHT

import logging
logger = logging.getLogger(__name__)


class FindItemDialog(QDialog):
    item_selected_for_focus = pyqtSignal(QGraphicsItem)

    def __init__(self, parent=None, scene_ref: 'DiagramScene' = None):
        super().__init__(parent)
        self.scene_ref = scene_ref
        self.setWindowTitle("Find Item")
        self.setWindowIcon(get_standard_icon(QStyle.SP_FileDialogContentsView, "Find"))
        self.setWindowFlags((self.windowFlags() & ~Qt.WindowContextHelpButtonHint) | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(350)
        self.setStyleSheet(f"QDialog {{ background-color: {COLOR_BACKGROUND_DIALOG}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,10,10,10); layout.setSpacing(8)
        self.search_label = QLabel("Search for FSM Element (Text in Name, Event, Action, Comment, etc.):")
        layout.addWidget(self.search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Start typing to search...")
        self.search_input.textChanged.connect(self._update_results_list)
        self.search_input.returnPressed.connect(self._on_return_pressed)
        layout.addWidget(self.search_input)
        self.results_list = QListWidget()
        self.results_list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self.results_list)
        self._populate_initial_list()
        self.search_input.setFocus()

    def _get_item_display_text(self, item: QGraphicsItem) -> str:
        from ..graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        if isinstance(item, GraphicsStateItem): return f"State: {item.text_label}"
        elif isinstance(item, GraphicsTransitionItem):
            label = item._compose_label_string()
            return f"Transition: {item.start_item.text_label if item.start_item else '?'} -> {item.end_item.text_label if item.end_item else '?'} ({label if label else 'No event'})"
        elif isinstance(item, GraphicsCommentItem):
            text = item.toPlainText().split('\n')[0]
            return f"Comment: {text[:30] + '...' if len(text) > 30 else text}"
        return "Unknown Item"

    def _populate_initial_list(self):
        self.results_list.clear()
        if not self.scene_ref: return
        all_items_with_text = []
        for item in self.scene_ref.items():
            if hasattr(item, 'get_data'): # Filter for our custom items
                list_item = QListWidgetItem(self._get_item_display_text(item))
                list_item.setData(Qt.UserRole, QVariant(item))
                all_items_with_text.append(list_item)
        all_items_with_text.sort(key=lambda x: x.text())
        for list_item_widget in all_items_with_text:
            self.results_list.addItem(list_item_widget)

    def _update_results_list(self):
        from ..graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        search_term = self.search_input.text().lower()
        self.results_list.clear()
        if not self.scene_ref: return
        if not search_term: self._populate_initial_list(); return
        matching_list_items = []
        for item in self.scene_ref.items():
            item_matches = False; searchable_text = ""
            if isinstance(item, GraphicsStateItem):
                props = item.get_data()
                searchable_text = (f"{props.get('name','')} {props.get('entry_action','')} {props.get('during_action','')} {props.get('exit_action','')} {props.get('description','')}").lower()
            elif isinstance(item, GraphicsTransitionItem):
                props = item.get_data()
                searchable_text = (f"{props.get('event','')} {props.get('condition','')} {props.get('action','')} {props.get('description','')}").lower()
            elif isinstance(item, GraphicsCommentItem):
                searchable_text = item.toPlainText().lower()
            if search_term in searchable_text: item_matches = True
            if item_matches:
                list_item = QListWidgetItem(self._get_item_display_text(item))
                list_item.setData(Qt.UserRole, QVariant(item))
                matching_list_items.append(list_item)
        matching_list_items.sort(key=lambda x: x.text())
        for list_item_widget in matching_list_items:
            self.results_list.addItem(list_item_widget)

    def _on_item_activated(self, list_item_widget: QListWidgetItem):
        if list_item_widget:
            stored_item_variant = list_item_widget.data(Qt.UserRole)
            if stored_item_variant is not None:
                actual_item = stored_item_variant
                if actual_item: self.item_selected_for_focus.emit(actual_item)

    def _on_return_pressed(self):
        if self.results_list.count() > 0:
            current_or_first_item = self.results_list.currentItem() if self.results_list.currentItem() else self.results_list.item(0)
            if current_or_first_item: self._on_item_activated(current_or_first_item)

    def refresh_list(self): self._update_results_list()
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape: self.reject()
        elif event.key() in (Qt.Key_Up, Qt.Key_Down) and self.results_list.count() > 0:
            self.results_list.setFocus()
            if self.results_list.currentRow() == -1:
                self.results_list.setCurrentRow(0 if event.key() == Qt.Key_Down else self.results_list.count() - 1)
        else: super().keyPressEvent(event)


class SnippetManagerDialog(QDialog):
    """Main dialog to manage all custom code snippets."""
    def __init__(self, snippet_manager: CustomSnippetManager, parent=None):
        super().__init__(parent)
        self.snippet_manager = snippet_manager
        self.setWindowTitle("Custom Asset Manager")
        self.setWindowIcon(get_standard_icon(QStyle.SP_ToolBarHorizontalExtensionButton, "SnipMgr"))
        self.setMinimumSize(700, 500)

        main_layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Snippets Tab
        snippet_widget = self._create_snippet_tab()
        self.tabs.addTab(snippet_widget, "Code Snippets")

        # Templates Tab
        template_widget = self._create_template_tab()
        self.tabs.addTab(template_widget, "FSM Templates")
        
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        self.on_selection_changed()
        self.on_template_selection_changed()

    def _create_snippet_tab(self):
        """Creates the widget for the Code Snippets tab."""
        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.setSpacing(10)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(200)

        left_layout.addWidget(QLabel("<b>Language:</b>"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(sorted(list(MECHATRONICS_SNIPPETS.keys())))
        left_layout.addWidget(self.lang_combo)

        left_layout.addWidget(QLabel("<b>Category:</b>"))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["actions", "conditions", "events"])
        left_layout.addWidget(self.cat_combo)

        left_layout.addSpacing(15)

        self.snippet_list_widget = QListWidget()
        left_layout.addWidget(QLabel("<b>Custom Snippets:</b>"))
        left_layout.addWidget(self.snippet_list_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton(get_standard_icon(QStyle.SP_DialogApplyButton, "Add"), "Add New...")
        self.edit_button = QPushButton(get_standard_icon(QStyle.SP_FileLinkIcon, "Edit"), "Edit...")
        self.delete_button = QPushButton(get_standard_icon(QStyle.SP_TrashIcon, "Del"), "Delete")
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addStretch()
        button_layout.addWidget(self.delete_button)
        right_layout.addLayout(button_layout)

        self.code_preview = CodeEditor()
        self.code_preview.setReadOnly(True)
        self.code_preview.setPlaceholderText("Select a snippet to view its code.")
        right_layout.addWidget(self.code_preview)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

        self.lang_combo.currentTextChanged.connect(self.on_selection_changed)
        self.cat_combo.currentTextChanged.connect(self.on_selection_changed)
        self.snippet_list_widget.currentItemChanged.connect(self.on_snippet_selected)
        
        self.add_button.clicked.connect(self.on_add_snippet)
        self.edit_button.clicked.connect(self.on_edit_snippet)
        self.delete_button.clicked.connect(self.on_delete_snippet)
        
        return container

    def _create_template_tab(self):
        """Creates the widget for the FSM Templates tab."""
        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.setSpacing(10)
        
        self.template_list_widget = QListWidget()
        self.template_list_widget.setFixedWidth(200)
        
        # --- START OF FIX ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel) # This layout now belongs to right_panel
        
        self.delete_template_button = QPushButton(get_standard_icon(QStyle.SP_TrashIcon, "Del"), "Delete Selected Template")
        self.delete_template_button.clicked.connect(self.on_delete_template)
        
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setPlaceholderText("Select a template to view its description.")
        
        right_layout.addWidget(self.delete_template_button, 0, Qt.AlignRight)
        right_layout.addWidget(self.template_preview)
        
        main_layout.addWidget(self.template_list_widget)
        # We add the WIDGET, not the LAYOUT
        main_layout.addWidget(right_panel, 1)
        # --- END OF FIX ---
        
        self.template_list_widget.currentItemChanged.connect(self.on_template_selection_changed)
        # Refresh the template list when this tab is first created
        self.on_template_selection_changed() # We can call this to populate the list initially
        
        return container


    def on_selection_changed(self):
        language = self.lang_combo.currentText()
        category = self.cat_combo.currentText()
        self.snippet_list_widget.clear()
        self.code_preview.clear()
        self.code_preview.set_language(language)
        snippet_names = self.snippet_manager.get_snippet_names_for_language_category(language, category)
        self.snippet_list_widget.addItems(snippet_names)
        self.on_snippet_selected(None, None)

    def on_snippet_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem = None):
        is_item_selected = current_item is not None
        self.edit_button.setEnabled(is_item_selected)
        self.delete_button.setEnabled(is_item_selected)
        if is_item_selected:
            name = current_item.text()
            language = self.lang_combo.currentText()
            category = self.cat_combo.currentText()
            code = self.snippet_manager.get_snippet_code(language, category, name)
            self.code_preview.setPlainText(code or "")
        else:
            self.code_preview.clear()

    def on_add_snippet(self):
        language = self.lang_combo.currentText()
        category = self.cat_combo.currentText()
        dialog = SnippetEditDialog(self, language, category)
        if dialog.exec_():
            data = dialog.get_snippet_data()
            if self.snippet_manager.add_custom_snippet(language, category, data["name"], data["code"]):
                self.on_selection_changed()
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save the new snippet.")

    def on_edit_snippet(self):
        current_item = self.snippet_list_widget.currentItem()
        if not current_item: return
        old_name = current_item.text()
        language = self.lang_combo.currentText()
        category = self.cat_combo.currentText()
        old_code = self.snippet_manager.get_snippet_code(language, category, old_name)
        dialog = SnippetEditDialog(self, language, category, old_name, old_code)
        if dialog.exec_():
            data = dialog.get_snippet_data()
            if self.snippet_manager.edit_custom_snippet(language, category, old_name, data["name"], data["code"]):
                self.on_selection_changed()
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save the edited snippet.")

    def on_delete_snippet(self):
        current_item = self.snippet_list_widget.currentItem()
        if not current_item: return
        name = current_item.text()
        language = self.lang_combo.currentText()
        category = self.cat_combo.currentText()
        reply = QMessageBox.question(self, "Delete Snippet", f"Are you sure you want to delete the snippet '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.snippet_manager.delete_custom_snippet(language, category, name):
                self.on_selection_changed()
            else:
                 QMessageBox.critical(self, "Delete Error", "Failed to delete the snippet.")
                 
    def on_template_selection_changed(self):
        self.template_list_widget.clear()
        templates = self.snippet_manager.get_custom_templates()
        self.template_list_widget.addItems(sorted(templates.keys()))
        
        current_item = self.template_list_widget.currentItem()
        is_item_selected = current_item is not None
        self.delete_template_button.setEnabled(is_item_selected)
        
        if is_item_selected:
            name = current_item.text()
            template_data = templates.get(name, {})
            desc = template_data.get('description', 'No description available.')
            num_states = len(template_data.get('states', []))
            num_trans = len(template_data.get('transitions', []))
            self.template_preview.setText(f"<b>{name}</b><hr>{desc}<br><br><i>Contains {num_states} states and {num_trans} transitions.</i>")
        else:
            self.template_preview.clear()

    def on_delete_template(self):
        current_item = self.template_list_widget.currentItem()
        if not current_item: return
        name = current_item.text()
        reply = QMessageBox.question(self, "Delete Template", f"Are you sure you want to delete the FSM template '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.snippet_manager.delete_custom_template(name):
                self.on_template_selection_changed()
            else:
                QMessageBox.critical(self, "Delete Error", "Failed to delete the template.")


class SnippetEditDialog(QDialog):
    """A dialog to add or edit a single code snippet."""
    def __init__(self, parent=None, language="", category="", snippet_name="", snippet_code=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Snippet" if snippet_name else "Add Snippet")
        self.setWindowIcon(get_standard_icon(QStyle.SP_DialogApplyButton, "SnipEdit"))
        self.setMinimumWidth(500)

        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.language_label = QLabel(f"<b>{language}</b>")
        layout.addRow("Language:", self.language_label)
        self.category_label = QLabel(f"<b>{category.capitalize()}</b>")
        layout.addRow("Category:", self.category_label)
        
        self.name_edit = QLineEdit(snippet_name)
        self.name_edit.setPlaceholderText("e.g., Turn On LED")
        layout.addRow("Snippet Name:", self.name_edit)

        self.code_edit = CodeEditor()
        self.code_edit.set_language(language)
        self.code_edit.setPlainText(snippet_code)
        self.code_edit.setMinimumHeight(120)
        layout.addRow("Snippet Code:", self.code_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)
        
        self.name_edit.setFocus()

    def on_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Invalid Name", "Snippet name cannot be empty.")
            return
        self.accept()
        
    def get_snippet_data(self) -> dict:
        return {"name": self.name_edit.text().strip(), "code": self.code_edit.toPlainText()}


class AutoLayoutPreviewDialog(QDialog):
    def __init__(self, preview_pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Layout Preview")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        scene = QGraphicsScene(self)
        scene.addPixmap(preview_pixmap)
        view = QGraphicsView(scene)
        view.setRenderHint(QPainter.Antialiasing)
        view.setDragMode(QGraphicsView.ScrollHandDrag)
        layout.addWidget(view)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        if ok_button: ok_button.setText("Apply")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class ImportFromTextDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import FSM from Text")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PlantUML", "Mermaid"])
        
        form_layout = QFormLayout()
        form_layout.addRow("Format:", self.format_combo)
        layout.addLayout(form_layout)
        
        self.text_editor = CodeEditor()
        self.text_editor.setPlaceholderText("Paste your PlantUML or Mermaid state diagram code here...")
        layout.addWidget(self.text_editor)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Import")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_diagram_data(self) -> dict | None:
        text = self.text_editor.toPlainText()
        format_type = self.format_combo.currentText()
        if not text.strip(): return None
        try:
            if format_type == "PlantUML": return parse_plantuml(text)
            elif format_type == "Mermaid": return parse_mermaid(text)
        except Exception as e:
            QMessageBox.critical(self, "Parsing Error", f"Failed to parse the diagram text: {e}")
            logger.error(f"Error parsing imported FSM text: {e}", exc_info=True)
        return None


class SystemInfoDialog(QDialog):
    """A dialog to display system and application information."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Information")
        self.setWindowIcon(get_standard_icon(QStyle.SP_ComputerIcon, "HostInfo"))
        self.setMinimumSize(550, 450)

        layout = QVBoxLayout(self)
        self.info_browser = QTextBrowser()
        self.info_browser.setOpenExternalLinks(False) # Handle links manually if needed
        layout.addWidget(self.info_browser)

        button_layout = QHBoxLayout()
        self.open_dir_button = QPushButton("Open Log/Config Directory")
        self.open_dir_button.clicked.connect(self._on_open_config_dir)
        button_layout.addWidget(self.open_dir_button)
        button_layout.addStretch()

        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)
        layout.addLayout(button_layout)

        self.info_browser.setHtml(self._gather_info_as_html())

    def _get_config_path(self) -> str:
        """Helper to get the config path, consistent with other managers."""
        path = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        if not path:
            path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        return path or "Not Found"

    def _on_open_config_dir(self):
        path = self._get_config_path()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "Directory Not Found", f"The configuration directory could not be found:\n{path}")

    def _gather_info_as_html(self) -> str:
        """Gathers system information and formats it as an HTML string."""
        try:
            mem = psutil.virtual_memory()
            total_mem_gb = mem.total / (1024 ** 3)
            
            info = {
                "Application": {
                    "Name": APP_NAME,
                    "Version": APP_VERSION,
                    "Config Path": self._get_config_path(),
                },
                "Python Environment": {
                    "Version": sys.version.split('\n')[0],
                    "Executable": sys.executable
                },
                "Operating System": {
                    "System": f"{platform.system()} {platform.release()}",
                    "Architecture": platform.machine(),
                    "Version": platform.version()
                },
                "Hardware Resources": {
                    "CPU Cores": f"{psutil.cpu_count(logical=True)} (logical), {psutil.cpu_count(logical=False)} (physical)",
                    "Total RAM": f"{total_mem_gb:.2f} GB"
                }
            }

            html = f"""
            <style>
                body {{ font-family: Segoe UI, sans-serif; background-color: {COLOR_BACKGROUND_LIGHT}; color: {COLOR_TEXT_PRIMARY}; }}
                h2 {{ color: {COLOR_ACCENT_PRIMARY}; border-bottom: 1px solid {COLOR_BORDER_LIGHT}; padding-bottom: 4px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 6px; text-align: left; vertical-align: top; }}
                th {{ font-weight: bold; width: 150px; }}
            </style>
            """

            for category, data in info.items():
                html += f"<h2>{category}</h2><table>"
                for key, value in data.items():
                    html += f"<tr><th>{key}:</th><td>{value}</td></tr>"
                html += "</table><br>"
            
            return html

        except Exception as e:
            logger.error(f"Error gathering system info: {e}", exc_info=True)
            return f"<h2>Error</h2><p>Could not gather system information: {e}</p>"


class QuickAccessSettingsDialog(QDialog):
    """Dialog to customize the Quick Access Toolbar."""
    def __init__(self, main_window, settings_manager, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self.settings_manager = settings_manager

        self.setWindowTitle("Customize Quick Access Toolbar")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        main_hbox = QHBoxLayout()

        # Left side: Available commands
        left_vbox = QVBoxLayout()
        left_vbox.addWidget(QLabel("<b>Available Commands:</b>"))
        self.available_list = QListWidget()
        left_vbox.addWidget(self.available_list)

        # Center: Add/Remove buttons
        center_vbox = QVBoxLayout()
        center_vbox.addStretch()
        self.add_button = QPushButton("Add >>")
        self.remove_button = QPushButton("<< Remove")
        center_vbox.addWidget(self.add_button)
        center_vbox.addWidget(self.remove_button)
        center_vbox.addStretch()

        # Right side: Current commands
        right_vbox = QVBoxLayout()
        right_vbox.addWidget(QLabel("<b>Toolbar Commands:</b>"))
        self.current_list = QListWidget()
        right_vbox.addWidget(self.current_list)

        main_hbox.addLayout(left_vbox)
        main_hbox.addLayout(center_vbox)
        main_hbox.addLayout(right_vbox)
        layout.addLayout(main_hbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Connect signals
        self.add_button.clicked.connect(self._add_item)
        self.remove_button.clicked.connect(self._remove_item)

        self._populate_lists()

    def _populate_lists(self):
        # Find all user-facing actions in the main window
        all_actions = self.mw.findChildren(QAction)
        self.all_actions_map = {
            action.text().replace('&', ''): action
            for action in all_actions if action.text() and not action.menu()
        }

        current_command_texts = self.settings_manager.get("quick_access_commands", [])
        
        # Populate current list
        for text in current_command_texts:
            if text in self.all_actions_map:
                self.current_list.addItem(text)

        # Populate available list (all actions minus current ones)
        available_texts = sorted(list(self.all_actions_map.keys()))
        for text in available_texts:
            if text not in current_command_texts:
                self.available_list.addItem(text)

    def _add_item(self):
        selected = self.available_list.selectedItems()
        if not selected: return
        item = self.available_list.takeItem(self.available_list.row(selected[0]))
        self.current_list.addItem(item)

    def _remove_item(self):
        selected = self.current_list.selectedItems()
        if not selected: return
        item = self.current_list.takeItem(self.current_list.row(selected[0]))
        self.available_list.addItem(item)
        self.available_list.sortItems()

    def get_new_command_list(self) -> list[str]:
        return [self.current_list.item(i).text() for i in range(self.current_list.count())]