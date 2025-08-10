# fsm_designer_project/managers/ui_manager.py

import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QToolBox, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QPushButton, QListWidget, QMenu, QStyle,
    QToolButton, QGroupBox, QComboBox, QProgressBar, QFormLayout, QGraphicsView,
    QMessageBox, QInputDialog, QLineEdit, QSizePolicy, QTreeView, QSpinBox,
    QDoubleSpinBox, QCheckBox, QColorDialog, QScrollArea, QFrame
)
from PyQt6.QtGui import QIcon, QKeySequence, QPalette, QPainter, QColor, QFont, QActionGroup, QAction, QFileSystemModel
from PyQt6.QtCore import Qt, QSize, QObject, QPointF, pyqtSlot, QDir, QEvent

from ..utils import get_standard_icon
from ..utils.config import (
    COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL, COLOR_ACCENT_PRIMARY, COLOR_BORDER_LIGHT,
    COLOR_TEXT_ON_ACCENT, COLOR_TEXT_PRIMARY, COLOR_BACKGROUND_DIALOG, COLOR_BACKGROUND_LIGHT,
    COLOR_BORDER_MEDIUM
)
from ..assets.assets import FSM_TEMPLATES_BUILTIN
from ..assets.target_profiles import TARGET_PROFILES
from ..ui.widgets.code_editor import CodeEditor
from ..utils import config
from ..ui.widgets.custom_widgets import CollapsibleSection, DraggableToolButton
from ..undo_commands import EditItemPropertiesCommand
from .c_simulation_manager import CSimulationManager

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

    def setup_ui(self):
        """
        Calls the UIBuilder to construct the main window's UI.
        This method is kept for backward compatibility with the old initialization sequence in main.py.
        In the new architecture, UIBuilder is called directly from MainWindow's __init__.
        """
        # This is now a placeholder; the UIBuilder handles construction.
        pass

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
        text_color = COLOR_TEXT_ON_ACCENT if luminance < 0.5 else COLOR_TEXT_PRIMARY
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
                        section_title_matches = filter_text in section_widget.title_label.text().lower()
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
        self._commit_property_changes()
        selected_items = editor.scene.selectedItems() if editor else []
        self._current_edited_items = selected_items
        self._clear_properties_layout()
        if not selected_items:
            self._display_no_selection_view()
        elif len(selected_items) == 1:
            self._display_single_item_view(selected_items[0])
        else:
            self._display_multi_item_view(selected_items)

    def _clear_properties_layout(self):
        while self.mw.properties_editor_layout.count():
            child_item = self.mw.properties_editor_layout.takeAt(0)
            if widget := child_item.widget():
                widget.deleteLater()
        while self.mw.properties_multi_layout.count():
            child_item = self.mw.properties_multi_layout.takeAt(0)
            if widget := child_item.widget():
                widget.deleteLater()
        self._property_editors.clear()

    def _display_no_selection_view(self):
        self.mw.properties_dock.setWindowTitle("Properties")
        self.mw.properties_placeholder_label.setText(f"<i>No item selected.</i><br><span style='font-size:{APP_FONT_SIZE_SMALL}; color:{COLOR_TEXT_SECONDARY};'>Click an item or use tools to add elements.</span>")
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
        from ..ui.widgets.code_editor import CodeEditor
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
            
        editor_widget.installEventFilter(self)
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

    def eventFilter(self, obj, event):
        if obj in self._property_editors.values():
            if event.type() == QEvent.Type.FocusIn:
                if not self._props_pre_edit_data:
                    for item in self._current_edited_items:
                        self._props_pre_edit_data[item] = item.get_data()
                return False
            if event.type() == QEvent.Type.FocusOut:
                self._commit_property_changes()
                return False
        return super().eventFilter(obj, event)

    def _commit_property_changes(self):
        """
        Commits changes from the properties dock to the selected items using an undo command.
        """
        if not self._props_pre_edit_data or not self._current_edited_items:
            return
        old_props_list = []
        new_props_list = []
        for item in self._current_edited_items:
            old_props = self._props_pre_edit_data.get(item)
            if not old_props: continue
            current_props = item.get_data()
            new_props_for_item = old_props.copy()
            
            for key, editor_widget in self._property_editors.items():
                if not editor_widget.hasFocus() and not isinstance(editor_widget, QPushButton):
                     if isinstance(editor_widget, QLineEdit) and editor_widget.placeholderText() == "(Multiple Values)":
                         continue
                     if isinstance(editor_widget, QCheckBox) and editor_widget.checkState() == Qt.CheckState.PartiallyChecked:
                         continue
                     if isinstance(editor_widget, QComboBox) and editor_widget.currentIndex() == 0 and editor_widget.itemText(0) == "(Multiple Values)":
                         continue
                new_val = self._get_value_from_editor(editor_widget)
                
                if new_val is not None:
                    new_props_for_item[key] = new_val
            if new_props_for_item != old_props:
                old_props_list.append(old_props)
                new_props_list.append(new_props_for_item)
        if old_props_list and new_props_list:
            if editor := self.mw.current_editor():
                cmd = EditItemPropertiesCommand(self._current_edited_items, old_props_list, new_props_list, f"Edit Properties via Dock")
                editor.undo_stack.push(cmd)
        
        self._props_pre_edit_data.clear()

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
                if not self._props_pre_edit_data:
                     for item in self._current_edited_items:
                        self._props_pre_edit_data[item] = item.get_data()
                self._update_dock_color_button_style(color_button, new_color)
                color_button.setProperty("currentColorHex", new_color.name())
                for item in self._current_edited_items:
                    item.set_properties(color=new_color.name())
                self._commit_property_changes()