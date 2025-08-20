# fsm_designer_project/managers/ui_manager.py

import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QToolBox, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QPushButton, QListWidget, QMenu, QStyle,
    QToolButton, QGroupBox, QComboBox, QProgressBar, QFormLayout, QGraphicsView,
    QMessageBox, QInputDialog, QLineEdit, QSizePolicy, QTreeView, QSpinBox,
    QDoubleSpinBox, QCheckBox, QColorDialog, QScrollArea, QFrame,
    QHeaderView
)
from PyQt6.QtGui import QIcon, QKeySequence, QPalette, QPainter, QColor, QFont, QActionGroup, QAction, QFileSystemModel
from PyQt6.QtCore import Qt, QSize, QObject, QPointF, pyqtSlot, QDir, QEvent

# --- MODIFIED: Import the signal bus ---
from .signal_bus import signal_bus

# --- MODIFIED: Import dialogs here ---
from ..ui.dialogs import AutoLayoutPreviewDialog, ImportFromTextDialog

from ..utils import get_standard_icon
from ..utils.theme_config import theme_config
from ..assets.assets import FSM_TEMPLATES_BUILTIN
from ..assets.target_profiles import TARGET_PROFILES
from ..ui.widgets.code_editor import CodeEditor
from ..utils import config
from ..ui.widgets.custom_widgets import CollapsibleSection, DraggableToolButton
from ..undo_commands import EditItemPropertiesCommand
from .c_simulation_manager import CSimulationManager
# --- FIX: Correct the import path for DataDictionaryWidget ---
from ..ui.simulation.data_dictionary_widget import DataDictionaryWidget

import logging
logger = logging.getLogger(__name__)


class UIManager(QObject):
    """
    Manages the dynamic state and interactions of the user interface after it has been constructed.
    This includes populating docks, handling property edits, and updating UI elements based on application state.
    """
    def __init__(self, main_window: QMainWindow):
        super().__init__(main_window)
        self.mw = main_window
        self._property_editors = {}
        self._current_edited_items = []
        self._props_pre_edit_data = {}
        self.global_search_handler = None
        self.c_sim_manager = CSimulationManager(main_window)

        # --- NEW: Connect to the signal bus ---
        signal_bus.dialog_requested.connect(self.handle_dialog_request)


    def setup_ui(self):
        """
        Calls the UIBuilder to construct the main window's UI.
        This method is kept for backward compatibility with the old initialization sequence in main.py.
        In the new architecture, UIBuilder is called directly from MainWindow's __init__.
        """
        # This is now a placeholder; the UIBuilder handles construction.
        pass

    # --- NEW METHOD to handle dialog requests from the signal bus ---
    @pyqtSlot(str, dict)
    def handle_dialog_request(self, dialog_name: str, data: dict):
        """
        Creates and shows dialogs based on requests emitted on the signal bus.
        This method acts as a central hub for dialog management.
        """
        logger.debug(f"Handling dialog request for '{dialog_name}'")
        editor = self.mw.current_editor()

        if dialog_name == "auto_layout_preview":
            pixmap = data.get("preview_pixmap")
            if not pixmap or not editor:
                logger.warning("Missing data for auto_layout_preview dialog.")
                return

            dialog = AutoLayoutPreviewDialog(pixmap, self.mw)
            if dialog.exec():
                # Logic moved from EditActionHandler to here
                editor.scene.apply_auto_layout()
                self.mw.log_message("INFO", "Auto-layout applied successfully.")
            else:
                self.mw.log_message("INFO", "Auto-layout was cancelled by the user.")

        elif dialog_name == "import_from_text":
            dialog = ImportFromTextDialog(self.mw)
            if dialog.exec():
                diagram_data = dialog.get_diagram_data()
                if diagram_data:
                    # Logic moved from FileActionHandler to here
                    new_editor = self.mw.add_new_editor_tab()
                    new_editor.scene.load_diagram_data(diagram_data)
                    new_editor.set_dirty(True)
                    # Use the view handler from the main action handler
                    if hasattr(self.mw, 'action_handler'):
                        self.mw.action_handler.view_handler.on_fit_diagram_in_view()   

    def populate_dynamic_docks(self):
        """Populates docks that require managers to be initialized first."""
        mw = self.mw
        if hasattr(mw, 'py_sim_ui_manager') and hasattr(mw, 'py_sim_dock'):
            py_sim_contents_widget = mw.py_sim_ui_manager.create_dock_widget_contents()
            mw.py_sim_dock.setWidget(py_sim_contents_widget)
        if hasattr(self, 'c_sim_manager') and hasattr(mw, 'c_sim_dock'):
            c_sim_contents_widget = self.c_sim_manager.create_dock_widget_contents()
            mw.c_sim_dock.setWidget(c_sim_contents_widget)
        if hasattr(mw, 'ai_chat_ui_manager') and hasattr(mw, 'ai_chatbot_dock'):
            ai_chat_contents_widget = mw.ai_chat_ui_manager.create_dock_widget_contents()
            mw.ai_chatbot_dock.setWidget(ai_chat_contents_widget)
        if hasattr(mw, 'hardware_sim_ui_manager') and hasattr(mw, 'hardware_sim_dock'):
            hardware_sim_contents_widget = mw.hardware_sim_ui_manager.create_dock_widget_contents()
            mw.hardware_sim_dock.setWidget(hardware_sim_contents_widget)
        self._populate_resource_estimation_dock()

    def _populate_quick_access_toolbar(self):
        """Clears and rebuilds the Quick Access Toolbar from settings."""
        self.mw.quick_toolbar.clear()
        
        command_texts = self.mw.settings_manager.get("quick_access_commands", [])
        all_actions = self.mw.findChildren(QAction)
        action_map = {action.text().replace('&', ''): action for action in all_actions}

        for text in command_texts:
            if action := action_map.get(text):
                self.mw.quick_toolbar.addAction(action)

        self.mw.quick_toolbar.addSeparator()
        self.mw.quick_toolbar.addAction(self.mw.host_action)

        customize_btn = QToolButton()
        customize_btn.setIcon(get_standard_icon(QStyle.StandardPixmap.SP_ToolBarVerticalExtensionButton, "Cust"))
        customize_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.mw); menu.addAction(self.mw.customize_quick_access_action); customize_btn.setMenu(menu)
        self.mw.quick_toolbar.addWidget(customize_btn)

    def _update_dock_color_button_style(self, button: QPushButton, color: QColor):
        if not color.isValid():
            return
        luminance = color.lightnessF()
        text_color = theme_config.COLOR_TEXT_ON_ACCENT if luminance < 0.5 else theme_config.COLOR_TEXT_PRIMARY
        button.setStyleSheet(f"""
            QPushButton#ColorButtonPropertiesDock {{
                background-color: {color.name()};
                color: {text_color};
            }}
        """)

    def _safe_get_style_enum(self, attr_name, fallback_attr_name=None):
        try:
            return getattr(QStyle.StandardPixmap, attr_name)
        except AttributeError:
            if fallback_attr_name:
                try:
                    return getattr(QStyle.StandardPixmap, fallback_attr_name)
                except AttributeError:
                    pass
            return QStyle.StandardPixmap.SP_CustomBase

    def _on_filter_properties_dock(self, text: str):
        filter_text = text.lower().strip()
        mw = self.mw
        for i in range(mw.properties_editor_layout.count()):
            section_widget = mw.properties_editor_layout.itemAt(i).widget()
            if not isinstance(section_widget, CollapsibleSection):
                continue
            section_visible_due_to_match = False
            content_layout = section_widget.content_widget.layout()
            if not content_layout:
                continue
            for row_index in range(content_layout.count()):
                row_item = content_layout.itemAt(row_index)
                if not row_item or not row_item.widget():
                    continue
                row_widget = row_item.widget()
                row_layout = row_widget.layout()
                if row_layout and row_layout.count() > 0:
                    label_widget = row_layout.itemAt(0).widget()
                    if isinstance(label_widget, QLabel):
                        label_matches = filter_text in label_widget.text().lower()
                        # --- FIX: Access the header QToolButton's text, not a non-existent attribute ---
                        section_title_matches = filter_text in section_widget.header.text().lower()
                        matches = not filter_text or label_matches or section_title_matches
                        row_widget.setVisible(matches)
                        if matches:
                            section_visible_due_to_match = True
                elif isinstance(row_widget, QCheckBox):
                    matches = not filter_text or filter_text in row_widget.text().lower()
                    row_widget.setVisible(matches)
                    if matches:
                        section_visible_due_to_match = True
            section_widget.setVisible(section_visible_due_to_match or not filter_text)

    @pyqtSlot()
    def on_advanced_edit_button_clicked(self):
        if self._current_edited_items and len(self._current_edited_items) == 1:
            self.mw.on_item_edit_requested(self._current_edited_items[0])

    def update_properties_dock_title_after_rename(self, new_name: str):
        from ..ui.graphics.graphics_items import GraphicsStateItem
        if self._current_edited_items and len(self._current_edited_items) == 1 and \
           isinstance(self._current_edited_items[0], GraphicsStateItem):
            self.mw.properties_dock.setWindowTitle(f"Properties: {new_name}")

    def update_properties_dock(self):
        editor = self.mw.current_editor()
        
        selected_items = editor.scene.selectedItems() if editor else []
        self._current_edited_items = selected_items
        
        self._props_pre_edit_data.clear()
        if selected_items:
            for item in selected_items:
                self._props_pre_edit_data[item] = item.get_data()

        self._clear_properties_layout()
        
        if not selected_items:
            self._display_no_selection_view()
        elif len(selected_items) == 1:
            self._display_single_item_view(selected_items[0])
        else:
            self._display_multi_item_view(selected_items)
            
        self.mw.properties_apply_button.setEnabled(False)
        self.mw.properties_revert_button.setEnabled(False)
        if hasattr(self.mw, 'properties_filter_edit'):
            self.mw.properties_filter_edit.clear()

    def _clear_properties_layout(self):
        if hasattr(self.mw, 'properties_editor_layout'):
            while self.mw.properties_editor_layout.count():
                child_item = self.mw.properties_editor_layout.takeAt(0)
                if widget := child_item.widget():
                    widget.deleteLater()
        if hasattr(self.mw, 'properties_multi_layout'):
            while self.mw.properties_multi_layout.count():
                child_item = self.mw.properties_multi_layout.takeAt(0)
                if widget := child_item.widget():
                    widget.deleteLater()
        self._property_editors.clear()

    def _display_no_selection_view(self):
        self.mw.properties_dock.setWindowTitle("Properties")
        self.mw.properties_placeholder_label.setText(f"<i>No item selected.</i><br><span style='font-size:{config.APP_FONT_SIZE_SMALL}; color:{theme_config.COLOR_TEXT_SECONDARY};'>Click an item or use tools to add elements.</span>")
        self.mw.properties_placeholder_label.show()
        self.mw.properties_editor_container.hide()
        self.mw.properties_multi_select_container.hide()
        self.mw.properties_edit_dialog_button.setEnabled(False)

    def _display_single_item_view(self, item):
        self._build_common_editors(item)
        self.mw.properties_multi_select_container.hide()
        self.mw.properties_edit_dialog_button.setEnabled(True)

    def _display_multi_item_view(self, items):
        self.mw.properties_multi_select_container.show()
        self._populate_alignment_tools()
        
        item_type = type(items[0])
        if all(isinstance(i, item_type) for i in items):
            self.mw.properties_dock.setWindowTitle(f"Properties ({len(items)} {item_type.__name__.replace('Graphics','').replace('Item','')+'s'})")
            multi_edit_schema = self._get_multi_edit_schema_for_item_type(item_type)
            self._build_common_editors(items, multi_edit_schema)
        else:
            self.mw.properties_dock.setWindowTitle(f"Properties ({len(items)} items)")
            self.mw.properties_placeholder_label.setText("<i>Multiple item types selected. Only alignment is available.</i>")
            self.mw.properties_placeholder_label.show()
            self.mw.properties_editor_container.hide()
            self.mw.properties_edit_dialog_button.setEnabled(False)

    def _get_property_schema_for_item(self, item):
        from ..ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        item_type = type(item)
        if item_type is GraphicsStateItem:
            return {
                "General": [
                    {'key': 'name', 'label': 'Name:', 'widget': QLineEdit},
                    {'key': 'description', 'label': 'Description:', 'widget': QTextEdit, 'config': {'setFixedHeight': 60}},
                ],
                "Behavior": [
                    {'key': 'is_initial', 'label': 'Is Initial State', 'widget': QCheckBox},
                    {'key': 'is_final', 'label': 'Is Final State', 'widget': QCheckBox},
                    {'key': 'is_superstate', 'label': 'Is Superstate', 'widget': QCheckBox},
                ],
                "Actions": [
                    {'key': 'entry_action', 'label': 'Entry Action:', 'widget': CodeEditor, 'config': {'setFixedHeight': 70}},
                    {'key': 'during_action', 'label': 'During Action:', 'widget': CodeEditor, 'config': {'setFixedHeight': 70}},
                    {'key': 'exit_action', 'label': 'Exit Action:', 'widget': CodeEditor, 'config': {'setFixedHeight': 70}},
                ],
                "Appearance": [
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                    {'key': 'font_size', 'label': 'Font Size:', 'widget': QSpinBox, 'config': {'setRange': (6, 72)}},
                    {'key': 'border_width', 'label': 'Border Width:', 'widget': QDoubleSpinBox, 'config': {'setRange': (0.5, 10.0), 'setSingleStep': 0.1, 'setDecimals': 1}},
                ]
            }
        elif item_type is GraphicsTransitionItem:
            return {
                "Logic": [
                    {'key': 'event', 'label': 'Event:', 'widget': QLineEdit},
                    {'key': 'condition', 'label': 'Condition:', 'widget': QLineEdit},
                    {'key': 'action', 'label': 'Action:', 'widget': CodeEditor, 'config': {'setFixedHeight': 70}},
                ],
                "Appearance": [
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                    {'key': 'control_offset_x', 'label': 'Curve Bend (Perp):', 'widget': QSpinBox, 'config': {'setRange': (-1000, 1000)}},
                    {'key': 'control_offset_y', 'label': 'Curve Shift (Tang):', 'widget': QSpinBox, 'config': {'setRange': (-1000, 1000)}},
                ]
            }
        elif item_type is GraphicsCommentItem:
             return {
                "Content": [
                    {'key': 'text', 'label': 'Text:', 'widget': QTextEdit, 'config': {'setFixedHeight': 80}},
                ]
             }
        return {}

    def _get_multi_edit_schema_for_item_type(self, item_type):
        """Returns a reduced schema of properties suitable for batch editing."""
        from ..ui.graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
        from .settings_manager import SettingsManager

        if item_type is GraphicsStateItem:
            return {
                "Appearance": [
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                    {'key': 'font_size', 'label': 'Font Size:', 'widget': QSpinBox, 'config': {'setRange': (6, 72)}},
                    {'key': 'border_width', 'label': 'Border Width:', 'widget': QDoubleSpinBox, 'config': {'setRange': (0.5, 10.0), 'setSingleStep': 0.1, 'setDecimals': 1}},
                ]
            }
        elif item_type is GraphicsTransitionItem:
            return {
                "Appearance": [
                    {'key': 'color', 'label': 'Color:', 'widget': QPushButton, 'is_color': True},
                    {'key': 'line_width', 'label': 'Line Width:', 'widget': QDoubleSpinBox, 'config': {'setRange': (0.5, 10.0), 'setSingleStep': 0.1, 'setDecimals': 1}},
                    {'key': 'line_style_str', 'label': 'Line Style:', 'widget': QComboBox, 'items': list(SettingsManager.STRING_TO_QT_PEN_STYLE.keys())},
                ]
            }
        elif item_type is GraphicsCommentItem:
            return {
                "Appearance": [
                    {'key': 'font_size', 'label': 'Font Size:', 'widget': QSpinBox, 'config': {'setRange': (6, 72)}},
                ]
            }
        return {}

    def _build_common_editors(self, items, schema=None):
        items_list = items if isinstance(items, list) else [items]
        is_multi_edit = len(items_list) > 1
        first_item = items_list[0]
        
        if schema is None:
            schema = self._get_property_schema_for_item(first_item)

        if not schema:
            self.mw.properties_placeholder_label.setText(f"<i>No editable properties for {type(first_item).__name__}.</i>")
            self.mw.properties_placeholder_label.show()
            self.mw.properties_editor_container.hide()
            return

        self.mw.properties_placeholder_label.hide()
        self.mw.properties_editor_container.show()
        
        for section_title, props in schema.items():
            section = CollapsibleSection(section_title, self.mw.properties_editor_container)
            self.mw.properties_editor_layout.addWidget(section)
            for prop_info in props:
                key = prop_info['key']
                first_value = first_item.get_data().get(key)
                all_same = True
                if is_multi_edit:
                    for other_item in items_list[1:]:
                        if other_item.get_data().get(key) != first_value:
                            all_same = False
                            break
                
                editor_widget = self._create_editor_widget(prop_info, first_value, all_same)

                if isinstance(editor_widget, QCheckBox):
                    section.add_widget(editor_widget)
                else:
                    section.add_row(prop_info['label'], editor_widget)
                self._property_editors[key] = editor_widget

    def _create_editor_widget(self, prop_info, value, all_same):
        WidgetClass = prop_info['widget']
        editor_widget = WidgetClass()
        
        if all_same:
            if isinstance(editor_widget, QLineEdit): editor_widget.setText(str(value or ''))
            elif isinstance(editor_widget, QTextEdit): editor_widget.setPlainText(str(value or ''))
            elif isinstance(editor_widget, QCheckBox): editor_widget.setChecked(bool(value))
            elif isinstance(editor_widget, QSpinBox): editor_widget.setValue(int(value or 0))
            elif isinstance(editor_widget, QDoubleSpinBox): editor_widget.setValue(float(value or 0.0))
            elif isinstance(editor_widget, QComboBox):
                if 'items' in prop_info:
                    editor_widget.addItems(prop_info['items'])
                editor_widget.setCurrentText(str(value).capitalize() if isinstance(value, str) else str(value))
        else:
            if isinstance(editor_widget, QLineEdit): editor_widget.setPlaceholderText("(Multiple Values)")
            elif isinstance(editor_widget, QCheckBox): editor_widget.setCheckState(Qt.CheckState.PartiallyChecked)
            elif isinstance(editor_widget, QComboBox):
                if 'items' in prop_info:
                    editor_widget.addItems(prop_info['items'])
                editor_widget.insertItem(0, "(Multiple Values)")
                editor_widget.setCurrentIndex(0)

        if 'config' in prop_info:
            for func_name, func_val in prop_info['config'].items():
                if func_name == "setRange" and isinstance(func_val, (list, tuple)):
                    getattr(editor_widget, func_name)(*func_val)
                else:
                    getattr(editor_widget, func_name)(func_val)
        
        if prop_info.get('is_color') and isinstance(editor_widget, QPushButton):
            color = QColor(value) if all_same and value else QColor(Qt.GlobalColor.gray)
            self._update_dock_color_button_style(editor_widget, color)
            editor_widget.setObjectName("ColorButtonPropertiesDock")
            editor_widget.setProperty("currentColorHex", color.name())
            editor_widget.clicked.connect(self._on_live_color_button_clicked)
            
        # Connect signals to enable Apply/Revert buttons
        if isinstance(editor_widget, (QLineEdit, QTextEdit, CodeEditor)):
            if hasattr(editor_widget, 'textChanged'): editor_widget.textChanged.connect(self._on_property_editor_changed)
        elif isinstance(editor_widget, (QCheckBox)):
            if hasattr(editor_widget, 'stateChanged'): editor_widget.stateChanged.connect(self._on_property_editor_changed)
        elif isinstance(editor_widget, (QComboBox, QSpinBox, QDoubleSpinBox)):
            if hasattr(editor_widget, 'valueChanged'): editor_widget.valueChanged.connect(self._on_property_editor_changed)
            if hasattr(editor_widget, 'currentTextChanged'): editor_widget.currentTextChanged.connect(self._on_property_editor_changed)
        
        return editor_widget

    def _populate_alignment_tools(self):
        self.mw.properties_multi_select_container.show()
        while self.mw.properties_multi_layout.count():
            child = self.mw.properties_multi_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.mw.properties_multi_layout.addWidget(QPushButton("Align Left", clicked=self.mw.align_left_action.trigger))
        self.mw.properties_multi_layout.addWidget(QPushButton("Align Center", clicked=self.mw.align_center_h_action.trigger))
        self.mw.properties_multi_layout.addStretch()

    @pyqtSlot()
    def _on_property_editor_changed(self):
        """Called when any editor in the properties dock is changed by the user."""
        self.mw.properties_apply_button.setEnabled(True)
        self.mw.properties_revert_button.setEnabled(True)

    @pyqtSlot()
    def _on_apply_dock_properties(self):
        """Applies changes from the dock to the selected items."""
        self._commit_property_changes()
        self.mw.properties_apply_button.setEnabled(False)
        self.mw.properties_revert_button.setEnabled(False)

    @pyqtSlot()
    def _on_revert_dock_properties(self):
        """Discards changes made in the dock by reloading the original properties."""
        self.update_properties_dock() # This rebuilds the UI from the item's current data
        self.mw.properties_apply_button.setEnabled(False)
        self.mw.properties_revert_button.setEnabled(False)
        
    def _commit_property_changes(self):
        """
        Commits changes from the properties dock to the selected items using an undo command.
        """
        if not self._props_pre_edit_data or not self._current_edited_items:
            return

        old_props_list = []
        new_props_list = []
        changed_items = []
        is_multi_edit = len(self._current_edited_items) > 1

        for item in self._current_edited_items:
            old_props = self._props_pre_edit_data.get(item)
            if not old_props: continue

            new_props_for_item = old_props.copy()
            item_has_changed = False
            
            for key, editor_widget in self._property_editors.items():
                if is_multi_edit:
                    if isinstance(editor_widget, QLineEdit) and editor_widget.placeholderText() == "(Multiple Values)": continue
                    if isinstance(editor_widget, QCheckBox) and editor_widget.checkState() == Qt.CheckState.PartiallyChecked: continue
                    if isinstance(editor_widget, QComboBox) and editor_widget.currentIndex() == 0 and editor_widget.itemText(0) == "(Multiple Values)": continue

                new_val = self._get_value_from_editor(editor_widget)
                
                if new_val is not None and new_props_for_item.get(key) != new_val:
                    new_props_for_item[key] = new_val
                    item_has_changed = True
            
            if item_has_changed:
                old_props_list.append(old_props)
                new_props_list.append(new_props_for_item)
                changed_items.append(item)
        
        if changed_items:
            if editor := self.mw.current_editor():
                cmd = EditItemPropertiesCommand(changed_items, old_props_list, new_props_list, f"Edit Properties via Dock")
                editor.undo_stack.push(cmd)
        
        self._props_pre_edit_data.clear()
        for item in self._current_edited_items:
            self._props_pre_edit_data[item] = item.get_data()

    def _get_value_from_editor(self, editor_widget):
        if isinstance(editor_widget, QLineEdit): return editor_widget.text().strip()
        elif isinstance(editor_widget, QTextEdit): return editor_widget.toPlainText().strip()
        elif isinstance(editor_widget, QCheckBox): return editor_widget.isChecked() if editor_widget.checkState() != Qt.CheckState.PartiallyChecked else None
        elif isinstance(editor_widget, QComboBox):
            if editor_widget.currentIndex() == 0 and editor_widget.itemText(0) == "(Multiple Values)":
                return None
            current_text = editor_widget.currentText()
            if "style" in editor_widget.objectName().lower() or "shape" in editor_widget.objectName().lower():
                return current_text.lower()
            return current_text
        elif isinstance(editor_widget, (QSpinBox, QDoubleSpinBox)): return editor_widget.value()
        elif isinstance(editor_widget, QPushButton) and editor_widget.property("currentColorHex"): return editor_widget.property("currentColorHex")
        return None

    def _on_live_color_button_clicked(self, *args):
        color_button = self.mw.sender()
        if not color_button: return
        current_color_hex = color_button.property("currentColorHex")
        initial_color = QColor(current_color_hex) if current_color_hex else QColor(Qt.GlobalColor.white)
        dialog = QColorDialog(self.mw)
        dialog.setCurrentColor(initial_color)
        if dialog.exec():
            new_color = dialog.selectedColor()
            if new_color.isValid() and new_color != initial_color:
                self._update_dock_color_button_style(color_button, new_color)
                color_button.setProperty("currentColorHex", new_color.name())
                self._on_property_editor_changed()

    def _populate_project_explorer_dock(self):
        mw = self.mw
        mw.project_fs_model = QFileSystemModel()
        mw.project_fs_model.setRootPath(QDir.homePath())
        mw.project_fs_model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files)

        mw.project_tree_view = QTreeView()
        mw.project_tree_view.setModel(mw.project_fs_model)
        mw.project_tree_view.setRootIndex(mw.project_fs_model.index(QDir.homePath()))
        mw.project_tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        mw.project_tree_view.setColumnHidden(1, True)
        mw.project_tree_view.setColumnHidden(2, True)
        mw.project_tree_view.setColumnHidden(3, True)
        mw.project_tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        mw.project_explorer_dock.setWidget(mw.project_tree_view)

    def _populate_data_dictionary_dock(self):
        mw = self.mw
        if not hasattr(mw, 'data_dictionary_manager'):
            logger.error("DataDictionaryManager not initialized before populating its dock.")
            return

        data_dict_widget = DataDictionaryWidget(mw.data_dictionary_manager)
        mw.data_dictionary_dock.setWidget(data_dict_widget)
        signal_bus.status_message_posted.connect(data_dict_widget.populate_table)


    def _populate_elements_palette_dock(self):
        mw = self.mw
        
        # --- NEW: Use CollapsibleSection instead of QToolBox ---
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 5, 0, 5)
        container_layout.setSpacing(8)

        # --- Standard Elements Section ---
        standard_section = CollapsibleSection("Standard Elements", container)
        standard_content = QWidget()
        standard_layout = QVBoxLayout(standard_content)
        standard_layout.setContentsMargins(5, 5, 5, 5)
        standard_layout.setSpacing(5)

        # --- FIX: Use more appropriate standard icons ---
        standard_layout.addWidget(DraggableToolButton("State", config.MIME_TYPE_BSM_ITEMS, "State", icon=get_standard_icon(QStyle.StandardPixmap.SP_FileDialogNewFolder, "State")))
        standard_layout.addWidget(DraggableToolButton("Initial State", config.MIME_TYPE_BSM_ITEMS, "Initial State", icon=get_standard_icon(QStyle.StandardPixmap.SP_MediaPlay)))
        standard_layout.addWidget(DraggableToolButton("Final State", config.MIME_TYPE_BSM_ITEMS, "Final State", icon=get_standard_icon(QStyle.StandardPixmap.SP_MediaStop)))
        standard_layout.addWidget(DraggableToolButton("Comment", config.MIME_TYPE_BSM_ITEMS, "Comment", icon=get_standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation)))
        standard_layout.addWidget(DraggableToolButton("Frame", config.MIME_TYPE_BSM_ITEMS, "Frame", icon=get_standard_icon(QStyle.StandardPixmap.SP_DirOpenIcon, "Frame")))
        # --- END FIX ---
        
        standard_layout.addStretch()
        standard_section.add_widget(standard_content)
        container_layout.addWidget(standard_section)

        # --- FSM Templates Section ---
        templates_section = CollapsibleSection("FSM Templates", container)
        
        # Use a scroll area for a potentially long list of templates
        templates_scroll_area = QScrollArea()
        templates_scroll_area.setWidgetResizable(True)
        templates_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        templates_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        mw.templates_widget = QWidget() # This widget goes inside the scroll area
        mw.templates_layout = QVBoxLayout(mw.templates_widget)
        mw.templates_layout.setContentsMargins(5, 5, 5, 5)
        mw.templates_layout.setSpacing(5)

        templates_scroll_area.setWidget(mw.templates_widget)
        templates_section.add_widget(templates_scroll_area)
        container_layout.addWidget(templates_section)

        self._load_and_display_templates()

        container_layout.addStretch()
        mw.elements_palette_dock.setWidget(container)

    def _load_and_display_templates(self):
        mw = self.mw
        while mw.templates_layout.count():
            child = mw.templates_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for name, data in FSM_TEMPLATES_BUILTIN.items():
            btn = DraggableToolButton(data.get('name', name), config.MIME_TYPE_BSM_TEMPLATE, json.dumps(data))
            btn.setToolTip(data.get('description', ''))
            mw.templates_layout.addWidget(btn)

        if mw.asset_manager:
            for name, data in mw.asset_manager.get_custom_templates().items():
                btn = DraggableToolButton(data.get('name', name), config.MIME_TYPE_BSM_TEMPLATE, json.dumps(data))
                btn.setToolTip(f"Custom: {data.get('description', '')}")
                mw.templates_layout.addWidget(btn)

        mw.templates_layout.addStretch()
        
    def _populate_live_preview_dock(self):
        mw = self.mw
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        toolbar = QToolBar("Live Preview Tools")
        toolbar.setIconSize(QSize(16, 16))
        mw.live_preview_combo = QComboBox()
        mw.live_preview_combo.addItems(["PlantUML", "Mermaid", "C Code", "Python FSM"])
        toolbar.addWidget(QLabel("Format:"))
        toolbar.addWidget(mw.live_preview_combo)
        toolbar.addSeparator()
        mw.scratchpad_sync_action = QAction("Sync from Scratchpad", mw)
        mw.scratchpad_sync_action.setToolTip("Parse the code below and replace the current diagram.")
        mw.scratchpad_sync_action.setIcon(get_standard_icon(QStyle.StandardPixmap.SP_ArrowLeft, "Sync"))
        mw.scratchpad_sync_action.setEnabled(False)
        mw.scratchpad_sync_action.triggered.connect(mw.action_handler.file_handler.on_sync_from_scratchpad)
        toolbar.addAction(mw.scratchpad_sync_action)
        layout.addWidget(toolbar)
        mw.live_preview_editor = CodeEditor()
        mw.live_preview_editor.setObjectName("LivePreviewEditor")
        mw.live_preview_editor.setReadOnly(False)
        mw.live_preview_editor.setPlaceholderText("Live code preview will appear here, or paste code to sync from.")
        layout.addWidget(mw.live_preview_editor)
        mw.live_preview_dock.setWidget(container)

    def _populate_serial_monitor_dock(self):
        mw = self.mw
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        mw.serial_monitor_output = QTextEdit()
        mw.serial_monitor_output.setReadOnly(True)
        mw.serial_monitor_output.setFont(QFont("Consolas", 9))
        mw.serial_monitor_output.setPlaceholderText("Serial data from connected hardware will appear here.")
        layout.addWidget(mw.serial_monitor_output)
        input_layout = QHBoxLayout()
        mw.serial_input_edit = QLineEdit()
        mw.serial_input_edit.setPlaceholderText("Send data to device...")
        mw.serial_send_button = QPushButton("Send")
        input_layout.addWidget(mw.serial_input_edit)
        input_layout.addWidget(mw.serial_send_button)
        layout.addLayout(input_layout)
        mw.serial_monitor_dock.setWidget(container)
        mw.serial_send_button.clicked.connect(mw.hardware_sim_ui_manager.on_send_serial_data)
        mw.serial_input_edit.returnPressed.connect(mw.hardware_sim_ui_manager.on_send_serial_data)
        
    def _populate_resource_estimation_dock(self):
        mw = self.mw
        container = QWidget()
        form_layout = QFormLayout(container)
        form_layout.setContentsMargins(10,10,10,10)
        form_layout.setSpacing(8)

        mw.target_device_combo = QComboBox()
        mw.target_device_combo.addItems(sorted(TARGET_PROFILES.keys()))
        form_layout.addRow("Target Device:", mw.target_device_combo)
        
        mw.sram_usage_bar = QProgressBar()
        mw.sram_usage_bar.setFormat("SRAM: ~0 / 0 B (0%)")
        form_layout.addRow("Est. SRAM Usage:", mw.sram_usage_bar)
        
        mw.flash_usage_bar = QProgressBar()
        mw.flash_usage_bar.setFormat("Flash: ~0.0 / 0 KB (0%)")
        form_layout.addRow("Est. Flash Usage:", mw.flash_usage_bar)
        
        mw.resource_estimation_dock.setWidget(container)