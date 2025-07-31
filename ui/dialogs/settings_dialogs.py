# fsm_designer_project/ui/dialogs/settings_dialogs.py

import sys
# At the top of fsm_designer_project/ui/dialogs/settings_dialogs.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton, QSpinBox, QComboBox, QDialogButtonBox,
    QColorDialog, QHBoxLayout, QLabel, QGroupBox, QStyle, QFontComboBox, QDoubleSpinBox, QAction,
    QCheckBox, QTabWidget, QWidget, QGraphicsScene, QGraphicsView, QScrollArea, QLineEdit,
    QInputDialog, QMessageBox, QFileDialog, QGraphicsItem # <-- ADD THIS IMPORT
)
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter
from PyQt5.QtCore import Qt, QDir, pyqtSlot

from ...managers.settings_manager import SettingsManager
from ...utils.config import (
    APP_NAME, APP_FONT_SIZE_SMALL, COLOR_TEXT_PRIMARY, COLOR_TEXT_ON_ACCENT,
    COLOR_BACKGROUND_DIALOG, COLOR_BACKGROUND_LIGHT, COLOR_ACCENT_PRIMARY,
    COLOR_BORDER_MEDIUM, APP_FONT_FAMILY, COLOR_ACCENT_ERROR,
    DEFAULT_STATE_SHAPE, DEFAULT_STATE_BORDER_STYLE, DEFAULT_STATE_BORDER_WIDTH,
    DEFAULT_TRANSITION_LINE_STYLE, DEFAULT_TRANSITION_LINE_WIDTH, DEFAULT_TRANSITION_ARROWHEAD,
    COLOR_ACCENT_PRIMARY_LIGHT, COLOR_TEXT_SECONDARY, COLOR_ITEM_STATE_DEFAULT_BG,
    COLOR_ITEM_TRANSITION_DEFAULT
)
from ...utils import get_standard_icon
from ...core.matlab_integration import MatlabConnection
from ...managers.theme_manager import ThemeManager

import logging
logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    PREVIEW_WIDTH = 150
    PREVIEW_HEIGHT = 80
    PREVIEW_TRANSITION_HEIGHT = 60
    PREVIEW_COMMENT_HEIGHT = 60

    
    def __init__(self, settings_manager: SettingsManager, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.theme_manager = theme_manager
        self.setWindowTitle(f"{APP_NAME} - Preferences")
        self.setWindowIcon(get_standard_icon(QStyle.SP_FileDialogDetailedView, "Prefs"))
        self.setMinimumWidth(600)
        self.setStyleSheet(f"QDialog {{ background-color: {COLOR_BACKGROUND_DIALOG}; }} QLabel#RestartNote {{ color: {COLOR_ACCENT_ERROR}; font-style:italic; }} QGraphicsView.previewView {{ border: 1px solid {COLOR_BORDER_MEDIUM}; background-color: {QColor(COLOR_BACKGROUND_LIGHT).lighter(103).name()}; }}")

        self.original_settings_on_open = {}
        
        self._preview_state_item: 'GraphicsStateItem' | None = None
        self._preview_transition_item_start: 'GraphicsStateItem' | None = None
        self._preview_transition_item_end: 'GraphicsStateItem' | None = None
        self._preview_transition_item: 'GraphicsTransitionItem' | None = None
        self._preview_comment_item: 'GraphicsCommentItem' | None = None

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- VIEW TAB ---
        view_tab = QWidget()
        view_layout = QFormLayout(view_tab)
        view_layout.setSpacing(10); view_layout.setContentsMargins(10,10,10,10)
        self.show_grid_cb = QCheckBox("Show Diagram Grid")
        view_layout.addRow(self.show_grid_cb)
        self.snap_to_grid_cb = QCheckBox("Snap to Grid during Drag")
        view_layout.addRow(self.snap_to_grid_cb)
        self.snap_to_objects_cb = QCheckBox("Snap to Objects during Drag")
        view_layout.addRow(self.snap_to_objects_cb)
        self.show_snap_guidelines_cb = QCheckBox("Show Dynamic Snap Guidelines during Drag")
        view_layout.addRow(self.show_snap_guidelines_cb)
        self.tabs.addTab(view_tab, "View")
        
        # --- APPEARANCE TAB ---
        appearance_tab = QWidget()
        appearance_layout_main = QVBoxLayout(appearance_tab)
        appearance_layout_main.setSpacing(10); appearance_layout_main.setContentsMargins(10,10,10,10)

        theme_group = QGroupBox("Application Theme")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_selector_layout = QHBoxLayout()
        theme_selector_layout.addWidget(QLabel("Current Theme:"))
        self.theme_combo = QComboBox()
        theme_selector_layout.addWidget(self.theme_combo, 1)
        theme_layout.addLayout(theme_selector_layout)

        theme_btn_layout = QHBoxLayout()
        self.new_theme_btn = QPushButton("New...")
        self.edit_theme_btn = QPushButton("Edit...")
        self.delete_theme_btn = QPushButton("Delete")
        self.new_theme_btn.clicked.connect(self._on_new_theme)
        self.edit_theme_btn.clicked.connect(self._on_edit_theme)
        self.delete_theme_btn.clicked.connect(self._on_delete_theme)
        theme_btn_layout.addWidget(self.new_theme_btn)
        theme_btn_layout.addWidget(self.edit_theme_btn)
        theme_btn_layout.addStretch()
        theme_btn_layout.addWidget(self.delete_theme_btn)
        theme_layout.addLayout(theme_btn_layout)

        theme_restart_note = QLabel("<i>Application restart may be required for full theme change.</i>")
        theme_restart_note.setObjectName("RestartNote")
        theme_restart_note.setStyleSheet(f"font-size: {APP_FONT_SIZE_SMALL};")
        theme_layout.addWidget(theme_restart_note)

        appearance_layout_main.addWidget(theme_group)

        # Connect theme manager signals after UI creation
        self.theme_manager.themesChanged.connect(self._update_theme_list)
        # Populate initial theme list
        self._update_theme_list()
        
        canvas_colors_group = QGroupBox("Grid Colors")
        canvas_colors_layout = QFormLayout(canvas_colors_group)
        
        self.grid_minor_color_button = QPushButton("Minor Grid Color...")
        self.grid_minor_color_button.clicked.connect(lambda: self._pick_color_for_button(self.grid_minor_color_button, "canvas_grid_minor_color"))
        canvas_colors_layout.addRow(self.grid_minor_color_button)

        self.grid_major_color_button = QPushButton("Major Grid Color...")
        self.grid_major_color_button.clicked.connect(lambda: self._pick_color_for_button(self.grid_major_color_button, "canvas_grid_major_color"))
        canvas_colors_layout.addRow(self.grid_major_color_button)

        self.snap_guideline_color_button = QPushButton("Snap Guideline Color...")
        self.snap_guideline_color_button.clicked.connect(lambda: self._pick_color_for_button(self.snap_guideline_color_button, "canvas_snap_guideline_color"))
        canvas_colors_layout.addRow(self.snap_guideline_color_button)
        appearance_layout_main.addWidget(canvas_colors_group)
        
        appearance_layout_main.addStretch() 
        self.tabs.addTab(appearance_tab, "Appearance")

        item_visuals_tab = QWidget()
        item_visuals_layout = QVBoxLayout(item_visuals_tab)
        item_visuals_layout.setSpacing(10)
        item_visuals_layout.setContentsMargins(10,10,10,10)

        state_defaults_group = QGroupBox("Default State Visuals")
        state_defaults_outer_layout = QHBoxLayout(state_defaults_group) 
        state_defaults_form_layout = QFormLayout() 
        
        self.state_default_shape_combo = QComboBox(); self.state_default_shape_combo.addItems(["Rectangle", "Ellipse"])
        state_defaults_form_layout.addRow("Shape:", self.state_default_shape_combo)
        
        self.state_default_font_family_combo = QFontComboBox()
        state_defaults_form_layout.addRow("Font Family:", self.state_default_font_family_combo)
        self.state_default_font_size_spin = QSpinBox(); self.state_default_font_size_spin.setRange(6, 72)
        state_defaults_form_layout.addRow("Font Size:", self.state_default_font_size_spin)
        self.state_default_font_bold_cb = QCheckBox("Bold")
        self.state_default_font_italic_cb = QCheckBox("Italic")
        state_font_style_layout = QHBoxLayout(); state_font_style_layout.addWidget(self.state_default_font_bold_cb); state_font_style_layout.addWidget(self.state_default_font_italic_cb); state_font_style_layout.addStretch()
        state_defaults_form_layout.addRow("Font Style:", state_font_style_layout)

        self.state_default_border_style_combo = QComboBox(); self.state_default_border_style_combo.addItems(list(SettingsManager.STRING_TO_QT_PEN_STYLE.keys()))
        state_defaults_form_layout.addRow("Border Style:", self.state_default_border_style_combo)
        self.state_default_border_width_spin = QDoubleSpinBox(); self.state_default_border_width_spin.setRange(0.5, 10.0); self.state_default_border_width_spin.setSingleStep(0.1); self.state_default_border_width_spin.setDecimals(1)
        state_defaults_form_layout.addRow("Border Width:", self.state_default_border_width_spin)
        
        state_defaults_outer_layout.addLayout(state_defaults_form_layout, 2)
        self.state_preview_scene = QGraphicsScene(self)
        self.state_preview_view = QGraphicsView(self.state_preview_scene)
        self.state_preview_view.setFixedSize(self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT)
        self.state_preview_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.state_preview_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.state_preview_view.setRenderHint(QPainter.Antialiasing); self.state_preview_view.setObjectName("previewView")
        state_defaults_outer_layout.addWidget(self.state_preview_view, 1) 
        item_visuals_layout.addWidget(state_defaults_group)


        transition_defaults_group = QGroupBox("Default Transition Visuals")
        transition_defaults_outer_layout = QHBoxLayout(transition_defaults_group)
        transition_defaults_form_layout = QFormLayout()

        self.transition_default_line_style_combo = QComboBox(); self.transition_default_line_style_combo.addItems(list(SettingsManager.STRING_TO_QT_PEN_STYLE.keys()))
        transition_defaults_form_layout.addRow("Line Style:", self.transition_default_line_style_combo)
        self.transition_default_line_width_spin = QDoubleSpinBox(); self.transition_default_line_width_spin.setRange(0.5, 10.0); self.transition_default_line_width_spin.setSingleStep(0.1); self.transition_default_line_width_spin.setDecimals(1)
        transition_defaults_form_layout.addRow("Line Width:", self.transition_default_line_width_spin)
        self.transition_default_arrowhead_combo = QComboBox(); self.transition_default_arrowhead_combo.addItems(["Filled", "Open", "None"])
        transition_defaults_form_layout.addRow("Arrowhead:", self.transition_default_arrowhead_combo)
        
        self.transition_default_font_family_combo = QFontComboBox()
        transition_defaults_form_layout.addRow("Label Font Family:", self.transition_default_font_family_combo)
        self.transition_default_font_size_spin = QSpinBox(); self.transition_default_font_size_spin.setRange(6,24)
        transition_defaults_form_layout.addRow("Label Font Size:", self.transition_default_font_size_spin)
        
        transition_defaults_outer_layout.addLayout(transition_defaults_form_layout, 2)
        self.transition_preview_scene = QGraphicsScene(self)
        self.transition_preview_view = QGraphicsView(self.transition_preview_scene)
        self.transition_preview_view.setFixedSize(self.PREVIEW_WIDTH, self.PREVIEW_TRANSITION_HEIGHT)
        self.transition_preview_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.transition_preview_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.transition_preview_view.setRenderHint(QPainter.Antialiasing); self.transition_preview_view.setObjectName("previewView")
        transition_defaults_outer_layout.addWidget(self.transition_preview_view, 1)
        item_visuals_layout.addWidget(transition_defaults_group)


        comment_defaults_group = QGroupBox("Default Comment Visuals")
        comment_defaults_outer_layout = QHBoxLayout(comment_defaults_group)
        comment_defaults_form_layout = QFormLayout()
        self.comment_default_font_family_combo = QFontComboBox()
        comment_defaults_form_layout.addRow("Font Family:", self.comment_default_font_family_combo)
        self.comment_default_font_size_spin = QSpinBox(); self.comment_default_font_size_spin.setRange(6,48)
        comment_defaults_form_layout.addRow("Font Size:", self.comment_default_font_size_spin)
        self.comment_default_font_italic_cb = QCheckBox("Italic")
        comment_defaults_form_layout.addRow(self.comment_default_font_italic_cb)
        
        comment_defaults_outer_layout.addLayout(comment_defaults_form_layout, 2)
        self.comment_preview_scene = QGraphicsScene(self)
        self.comment_preview_view = QGraphicsView(self.comment_preview_scene)
        self.comment_preview_view.setFixedSize(self.PREVIEW_WIDTH, self.PREVIEW_COMMENT_HEIGHT)
        self.comment_preview_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.comment_preview_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.comment_preview_view.setRenderHint(QPainter.Antialiasing); self.comment_preview_view.setObjectName("previewView")
        comment_defaults_outer_layout.addWidget(self.comment_preview_view, 1)
        item_visuals_layout.addWidget(comment_defaults_group)

        item_visuals_layout.addStretch()
        self.tabs.addTab(item_visuals_tab, "Item Defaults")


        behavior_tab = QWidget()
        behavior_layout = QFormLayout(behavior_tab)
        behavior_layout.setSpacing(10); behavior_layout.setContentsMargins(10,10,10,10)
        self.resource_monitor_enabled_cb = QCheckBox("Enable Resource Monitor in Status Bar")
        self.resource_monitor_interval_spin = QSpinBox()
        self.resource_monitor_interval_spin.setRange(500, 60000); self.resource_monitor_interval_spin.setSingleStep(500); self.resource_monitor_interval_spin.setSuffix(" ms")
        behavior_layout.addRow(self.resource_monitor_enabled_cb)
        behavior_layout.addRow("Resource Monitor Update Interval:", self.resource_monitor_interval_spin)
        restart_note_bh = QLabel("<i>Some settings may require an application restart to take full effect.</i>")
        restart_note_bh.setObjectName("RestartNote"); restart_note_bh.setStyleSheet(f"font-size: {APP_FONT_SIZE_SMALL};")
        behavior_layout.addRow(restart_note_bh)
        self.tabs.addTab(behavior_tab, "Behavior")
        
        # --- NEW TAB: Integrations (for MATLAB) ---
        integrations_tab = QWidget()
        self._populate_matlab_settings_tab(integrations_tab)
        self.tabs.addTab(integrations_tab, "Integrations")
        # --- END NEW TAB ---
        
        main_layout.addWidget(self.tabs)

        button_layout = QHBoxLayout()
        self.reset_defaults_button = QPushButton("Reset to Defaults")
        self.reset_defaults_button.clicked.connect(self.on_reset_to_defaults)
        button_layout.addWidget(self.reset_defaults_button)
        button_layout.addStretch()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        self.button_box.button(QDialogButtonBox.Ok).setText("OK & Save")
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        self.button_box.accepted.connect(self.accept_settings); self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)
        main_layout.addLayout(button_layout)
        
        self._create_preview_items() 
        self.load_settings_to_ui() 
        self._connect_change_signals_for_apply_button()
        self._connect_preview_update_signals()

    def _populate_matlab_settings_tab(self, tab_widget: QWidget):
        """Creates and populates the MATLAB settings tab content."""
        main_layout = QVBoxLayout(tab_widget)
        main_layout.setSpacing(10); main_layout.setContentsMargins(10,10,10,10)

        path_group = QGroupBox("MATLAB Executable Path"); path_form_layout = QFormLayout()
        path_form_layout.setSpacing(6)
        self.matlab_path_edit = QLineEdit(self.parent().matlab_connection.matlab_path if self.parent() else "")
        self.matlab_path_edit.setPlaceholderText("e.g., C:\\...\\MATLAB\\R202Xy\\bin\\matlab.exe")
        path_form_layout.addRow("Path:", self.matlab_path_edit)

        btn_layout = QHBoxLayout(); btn_layout.setSpacing(6)
        auto_detect_btn = QPushButton(get_standard_icon(QStyle.SP_BrowserReload,"Det"), " Auto-detect")
        auto_detect_btn.clicked.connect(self._matlab_auto_detect)
        auto_detect_btn.setToolTip("Attempt to find MATLAB installations.")
        browse_btn = QPushButton(get_standard_icon(QStyle.SP_DirOpenIcon, "Brw"), " Browse...")
        browse_btn.clicked.connect(self._matlab_browse)
        browse_btn.setToolTip("Browse for MATLAB executable.")
        btn_layout.addWidget(auto_detect_btn); btn_layout.addWidget(browse_btn); btn_layout.addStretch()

        path_v_layout = QVBoxLayout(); path_v_layout.setSpacing(8)
        path_v_layout.addLayout(path_form_layout); path_v_layout.addLayout(btn_layout)
        path_group.setLayout(path_v_layout); main_layout.addWidget(path_group)

        test_group = QGroupBox("Connection Test"); test_layout = QVBoxLayout(); test_layout.setSpacing(8)
        self.matlab_test_status_label = QLabel("Status: Unknown"); self.matlab_test_status_label.setObjectName("TestStatusLabel")
        self.matlab_test_status_label.setWordWrap(True); self.matlab_test_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse); self.matlab_test_status_label.setMinimumHeight(30)
        test_btn = QPushButton(get_standard_icon(QStyle.SP_CommandLink,"Test"), " Test Connection")
        test_btn.clicked.connect(self._matlab_test_connection)
        test_btn.setToolTip("Test connection to the specified MATLAB path.")
        test_layout.addWidget(test_btn); test_layout.addWidget(self.matlab_test_status_label, 1)
        test_group.setLayout(test_layout); main_layout.addWidget(test_group)
        main_layout.addStretch()

        # Connect signals and set initial state
        if self.parent() and hasattr(self.parent(), 'matlab_connection'):
            matlab_conn = self.parent().matlab_connection
            matlab_conn.connectionStatusChanged.connect(self._matlab_update_test_label)
            if matlab_conn.matlab_path and matlab_conn.connected:
                 self._matlab_update_test_label(True, f"Connected: {matlab_conn.matlab_path}")
            elif matlab_conn.matlab_path:
                self._matlab_update_test_label(False, "Path set, but connection unconfirmed.")
            else:
                self._matlab_update_test_label(False, "Path not set.")

            # Also connect the line edit to the apply button
            self.matlab_path_edit.textChanged.connect(self._on_setting_ui_changed)

    def _update_theme_list(self):
        """Populates the theme combobox with available themes."""
        current_theme = self.theme_combo.currentText()
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItems(self.theme_manager.get_theme_names())

        if current_theme in self.theme_manager.get_theme_names():
            self.theme_combo.setCurrentText(current_theme)
        else:
            self.theme_combo.setCurrentText(self.settings_manager.get("appearance_theme"))
            
        self._on_theme_selection_changed()
        self.theme_combo.currentTextChanged.connect(self._on_theme_selection_changed)
        self.theme_combo.blockSignals(False)

    @pyqtSlot()
    def _on_theme_selection_changed(self):
        selected_theme = self.theme_combo.currentText()
        is_deletable = selected_theme not in ["Light", "Dark", "Crimson"]
        self.edit_theme_btn.setEnabled(True) # Always allow editing
        self.delete_theme_btn.setEnabled(is_deletable)

    def _on_new_theme(self):
        base_theme_name, ok = QInputDialog.getItem(self, "New Theme", "Create from:", self.theme_manager.get_theme_names(), 0, False)
        if not ok: return
        
        new_name, ok = QInputDialog.getText(self, "New Theme Name", "Enter name for the new theme:", QLineEdit.Normal, f"Custom {base_theme_name}")
        if not ok or not new_name.strip(): return
        
        if new_name in self.theme_manager.get_theme_names():
            QMessageBox.warning(self, "Name Exists", f"A theme named '{new_name}' already exists.")
            return

        base_data = self.theme_manager.get_theme_data(base_theme_name)
        if not base_data: return

        dialog = ThemeEditDialog(base_data, new_name, self)
        if dialog.exec_():
            new_theme_data = dialog.get_theme_data()
            if self.theme_manager.save_theme(new_name, new_theme_data):
                self.theme_combo.setCurrentText(new_name)
                # Apply change immediately
                self.settings_manager.set("appearance_theme", new_name)

    def _on_edit_theme(self):
        theme_name = self.theme_combo.currentText()
        theme_data = self.theme_manager.get_theme_data(theme_name)
        if not theme_data: return
        
        dialog = ThemeEditDialog(theme_data, theme_name, self)
        if dialog.exec_():
            updated_data = dialog.get_theme_data()
            if self.theme_manager.save_theme(theme_name, updated_data):
                self.settings_manager.set("appearance_theme", theme_name)
                # Manually trigger apply if user hits OK, because settings are complex
                self.apply_settings()

    def _on_delete_theme(self):
        theme_name = self.theme_combo.currentText()
        if theme_name in ["Light", "Dark", "Crimson"]: return

        reply = QMessageBox.question(self, "Delete Theme", f"Are you sure you want to delete the theme '{theme_name}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.theme_manager.delete_theme(theme_name):
                self.settings_manager.set("appearance_theme", "Light") # Fallback
                self.theme_combo.setCurrentText("Light")


    def _create_preview_items(self):
        # --- FIX: Move imports inside the method to break circular dependency ---
        from ..graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem

        # State Preview Item
        self._preview_state_item = GraphicsStateItem(0, 0, 100, 50, "State") # Dimensions are relative, fitInView handles scaling
        self._preview_state_item.setFlag(QGraphicsItem.ItemIsMovable, False); self._preview_state_item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.state_preview_scene.addItem(self._preview_state_item)
        self.state_preview_scene.setSceneRect(self._preview_state_item.boundingRect().adjusted(-10, -10, 10, 10))
        self.state_preview_view.fitInView(self.state_preview_scene.sceneRect(), Qt.KeepAspectRatio)


        # Transition Preview Items
        self._preview_transition_item_start = GraphicsStateItem(0, 0, 10, 10, "S"); self._preview_transition_item_start.setFlag(QGraphicsItem.ItemIsMovable, False)
        self._preview_transition_item_end = GraphicsStateItem(100, 0, 10, 10, "T"); self._preview_transition_item_end.setFlag(QGraphicsItem.ItemIsMovable, False)
        self._preview_transition_item = GraphicsTransitionItem(self._preview_transition_item_start, self._preview_transition_item_end, "Event")
        self._preview_transition_item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.transition_preview_scene.addItem(self._preview_transition_item_start); self.transition_preview_scene.addItem(self._preview_transition_item_end); self.transition_preview_scene.addItem(self._preview_transition_item)
        self.transition_preview_view.fitInView(self.transition_preview_scene.itemsBoundingRect().adjusted(-10,-20,10,20), Qt.KeepAspectRatio) # More vertical padding for label


        # Comment Preview Item
        self._preview_comment_item = GraphicsCommentItem(0, 0, "Comment...")
        self._preview_comment_item.setTextWidth(120) # A fixed width for predictable preview
        self._preview_comment_item.setFlag(QGraphicsItem.ItemIsMovable, False); self._preview_comment_item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.comment_preview_scene.addItem(self._preview_comment_item)
        self.comment_preview_scene.setSceneRect(self._preview_comment_item.boundingRect().adjusted(-10, -10, 10, 10))
        self.comment_preview_view.fitInView(self.comment_preview_scene.sceneRect(), Qt.KeepAspectRatio)


    def _update_default_item_previews(self):
        logger.debug("Updating default item previews in SettingsDialog.")
        # State Preview
        if self._preview_state_item:
            state_color_hex = self.settings_manager.get("item_default_state_color") if self.settings_manager else COLOR_ITEM_STATE_DEFAULT_BG # Fallback

            self._preview_state_item.set_properties(
                name="State", is_initial=False, is_final=False, 
                color_hex=state_color_hex, 
                shape_type_prop=self.state_default_shape_combo.currentText().lower(),
                font_family_prop=self.state_default_font_family_combo.currentFont().family(),
                font_size_prop=self.state_default_font_size_spin.value(),
                font_bold_prop=self.state_default_font_bold_cb.isChecked(),
                font_italic_prop=self.state_default_font_italic_cb.isChecked(),
                border_style_str_prop=self.state_default_border_style_combo.currentText(),
                border_width_prop=self.state_default_border_width_spin.value()
            )
            self.state_preview_view.fitInView(self.state_preview_scene.itemsBoundingRect().adjusted(-10, -10, 10, 10), Qt.KeepAspectRatio)


        # Transition Preview
        if self._preview_transition_item:
            trans_color_hex = self.settings_manager.get("item_default_transition_color") if self.settings_manager else COLOR_ITEM_TRANSITION_DEFAULT # Fallback
            
            self._preview_transition_item.set_properties(
                event_str="Event", 
                color_hex=trans_color_hex,
                line_style_str_prop=self.transition_default_line_style_combo.currentText(),
                line_width_prop=self.transition_default_line_width_spin.value(),
                arrowhead_style_prop=self.transition_default_arrowhead_combo.currentText().lower(),
                label_font_family_prop=self.transition_default_font_family_combo.currentFont().family(),
                label_font_size_prop=self.transition_default_font_size_spin.value()
            )
            self.transition_preview_view.fitInView(self.transition_preview_scene.itemsBoundingRect().adjusted(-10, -20, 10, 20), Qt.KeepAspectRatio)


        # Comment Preview
        if self._preview_comment_item:
            self._preview_comment_item.set_properties(
                text="Comment...", 
                font_family_prop=self.comment_default_font_family_combo.currentFont().family(),
                font_size_prop=self.comment_default_font_size_spin.value(),
                font_italic_prop=self.comment_default_font_italic_cb.isChecked()
            )
            self.comment_preview_view.fitInView(self.comment_preview_scene.itemsBoundingRect().adjusted(-10, -10, 10, 10), Qt.KeepAspectRatio)
        
        self._on_setting_ui_changed() 


    def _connect_preview_update_signals(self):
        # State defaults
        self.state_default_shape_combo.currentTextChanged.connect(self._update_default_item_previews)
        self.state_default_font_family_combo.currentFontChanged.connect(self._update_default_item_previews)
        self.state_default_font_size_spin.valueChanged.connect(self._update_default_item_previews)
        self.state_default_font_bold_cb.toggled.connect(self._update_default_item_previews)
        self.state_default_font_italic_cb.toggled.connect(self._update_default_item_previews)
        self.state_default_border_style_combo.currentTextChanged.connect(self._update_default_item_previews)
        self.state_default_border_width_spin.valueChanged.connect(self._update_default_item_previews)
        # Transition defaults
        self.transition_default_line_style_combo.currentTextChanged.connect(self._update_default_item_previews)
        self.transition_default_line_width_spin.valueChanged.connect(self._update_default_item_previews)
        self.transition_default_arrowhead_combo.currentTextChanged.connect(self._update_default_item_previews)
        self.transition_default_font_family_combo.currentFontChanged.connect(self._update_default_item_previews)
        self.transition_default_font_size_spin.valueChanged.connect(self._update_default_item_previews)
        # Comment defaults
        self.comment_default_font_family_combo.currentFontChanged.connect(self._update_default_item_previews)
        self.comment_default_font_size_spin.valueChanged.connect(self._update_default_item_previews)
        self.comment_default_font_italic_cb.toggled.connect(self._update_default_item_previews)


    def _connect_change_signals_for_apply_button(self):
        all_widgets_with_signals = [
            self.show_grid_cb, self.snap_to_grid_cb, self.snap_to_objects_cb, self.show_snap_guidelines_cb,
            self.theme_combo, 
            self.state_default_shape_combo, self.state_default_font_family_combo, self.state_default_font_size_spin,
            self.state_default_font_bold_cb, self.state_default_font_italic_cb, self.state_default_border_style_combo,
            self.state_default_border_width_spin,
            self.transition_default_line_style_combo, self.transition_default_line_width_spin,
            self.transition_default_arrowhead_combo, self.transition_default_font_family_combo,
            self.transition_default_font_size_spin,
            self.comment_default_font_family_combo, self.comment_default_font_size_spin,
            self.comment_default_font_italic_cb,
            self.resource_monitor_enabled_cb, self.resource_monitor_interval_spin
        ]
        for widget in all_widgets_with_signals:
            if isinstance(widget, QCheckBox): widget.toggled.connect(self._on_setting_ui_changed)
            elif isinstance(widget, QComboBox): widget.currentTextChanged.connect(self._on_setting_ui_changed)
            elif isinstance(widget, QSpinBox): widget.valueChanged.connect(self._on_setting_ui_changed)
            elif isinstance(widget, QDoubleSpinBox): widget.valueChanged.connect(self._on_setting_ui_changed)
            elif isinstance(widget, QFontComboBox): widget.currentFontChanged.connect(self._on_setting_ui_changed)


    def _on_setting_ui_changed(self, *args):
        self.button_box.button(QDialogButtonBox.Apply).setEnabled(True)


    def _pick_color_for_button(self, button: QPushButton, setting_key: str):
        current_color_hex = button.property("pendingColorHex") 
        if not current_color_hex: 
             current_color_hex = self.settings_manager.get(setting_key)
        initial_color = QColor(current_color_hex)
        
        dialog = QColorDialog(self)
        dialog.setCurrentColor(initial_color)
        if dialog.exec_():
            new_color = dialog.selectedColor()
            if new_color.isValid() and new_color.name() != initial_color.name(): 
                self._update_color_button_display(button, new_color)
                button.setProperty("pendingColorHex", new_color.name()) 
                self._on_setting_ui_changed() 
                # This doesn't directly update previews, maybe connect here or rely on the other signals
                # For a color button, we need an explicit update
                if setting_key == "item_default_state_color":
                    if self._preview_state_item:
                         self._preview_state_item.set_properties(name="State", is_initial=False, is_final=False, color_hex=new_color.name())
                elif setting_key == "item_default_transition_color":
                    if self._preview_transition_item:
                        self._preview_transition_item.set_properties(event_str="Event", color_hex=new_color.name())
                self.update()


    def _update_color_button_display(self, button: QPushButton, color: QColor):
        luminance = color.lightnessF()
        text_color_name = COLOR_TEXT_ON_ACCENT if luminance < 0.5 else COLOR_TEXT_PRIMARY
        button.setStyleSheet(f"background-color: {color.name()}; color: {text_color_name};")
        button.setText(color.name().upper())


    def load_settings_to_ui(self):
        self.original_settings_on_open.clear()

        all_widgets_with_signals = [
            self.show_grid_cb, self.snap_to_grid_cb, self.snap_to_objects_cb, self.show_snap_guidelines_cb,
            self.theme_combo, 
            self.state_default_shape_combo, self.state_default_font_family_combo, self.state_default_font_size_spin,
            self.state_default_font_bold_cb, self.state_default_font_italic_cb, self.state_default_border_style_combo,
            self.state_default_border_width_spin,
            self.transition_default_line_style_combo, self.transition_default_line_width_spin,
            self.transition_default_arrowhead_combo, self.transition_default_font_family_combo,
            self.transition_default_font_size_spin,
            self.comment_default_font_family_combo, self.comment_default_font_size_spin,
            self.comment_default_font_italic_cb,
            self.resource_monitor_enabled_cb, self.resource_monitor_interval_spin,
            self.grid_minor_color_button, self.grid_major_color_button, self.snap_guideline_color_button 
        ]
        for widget in all_widgets_with_signals: widget.blockSignals(True)
        
        self.show_grid_cb.setChecked(self.settings_manager.get("view_show_grid"))
        self.original_settings_on_open["view_show_grid"] = self.show_grid_cb.isChecked()
        self.snap_to_grid_cb.setChecked(self.settings_manager.get("view_snap_to_grid"))
        self.original_settings_on_open["view_snap_to_grid"] = self.snap_to_grid_cb.isChecked()
        self.snap_to_objects_cb.setChecked(self.settings_manager.get("view_snap_to_objects"))
        self.original_settings_on_open["view_snap_to_objects"] = self.snap_to_objects_cb.isChecked()
        self.show_snap_guidelines_cb.setChecked(self.settings_manager.get("view_show_snap_guidelines"))
        self.original_settings_on_open["view_show_snap_guidelines"] = self.show_snap_guidelines_cb.isChecked()

        self.theme_combo.setCurrentText(self.settings_manager.get("appearance_theme"))
        self.original_settings_on_open["appearance_theme"] = self.theme_combo.currentText()
        
        minor_grid_color_hex = self.settings_manager.get("canvas_grid_minor_color")
        self._update_color_button_display(self.grid_minor_color_button, QColor(minor_grid_color_hex))
        self.grid_minor_color_button.setProperty("pendingColorHex", minor_grid_color_hex) 
        self.original_settings_on_open["canvas_grid_minor_color"] = minor_grid_color_hex
        
        major_grid_color_hex = self.settings_manager.get("canvas_grid_major_color")
        self._update_color_button_display(self.grid_major_color_button, QColor(major_grid_color_hex))
        self.grid_major_color_button.setProperty("pendingColorHex", major_grid_color_hex)
        self.original_settings_on_open["canvas_grid_major_color"] = major_grid_color_hex

        snap_guide_color_hex = self.settings_manager.get("canvas_snap_guideline_color")
        self._update_color_button_display(self.snap_guideline_color_button, QColor(snap_guide_color_hex))
        self.snap_guideline_color_button.setProperty("pendingColorHex", snap_guide_color_hex)
        self.original_settings_on_open["canvas_snap_guideline_color"] = snap_guide_color_hex

        self.state_default_shape_combo.setCurrentText(self.settings_manager.get("state_default_shape").capitalize())
        self.original_settings_on_open["state_default_shape"] = self.settings_manager.get("state_default_shape")
        self.state_default_font_family_combo.setCurrentFont(QFont(self.settings_manager.get("state_default_font_family")))
        self.original_settings_on_open["state_default_font_family"] = self.settings_manager.get("state_default_font_family")
        self.state_default_font_size_spin.setValue(self.settings_manager.get("state_default_font_size"))
        self.original_settings_on_open["state_default_font_size"] = self.settings_manager.get("state_default_font_size")
        self.state_default_font_bold_cb.setChecked(self.settings_manager.get("state_default_font_bold"))
        self.original_settings_on_open["state_default_font_bold"] = self.settings_manager.get("state_default_font_bold")
        self.state_default_font_italic_cb.setChecked(self.settings_manager.get("state_default_font_italic"))
        self.original_settings_on_open["state_default_font_italic"] = self.settings_manager.get("state_default_font_italic")
        self.state_default_border_style_combo.setCurrentText(self.settings_manager.get("state_default_border_style_str"))
        self.original_settings_on_open["state_default_border_style_str"] = self.settings_manager.get("state_default_border_style_str")
        self.state_default_border_width_spin.setValue(self.settings_manager.get("state_default_border_width"))
        self.original_settings_on_open["state_default_border_width"] = self.settings_manager.get("state_default_border_width")

        self.transition_default_line_style_combo.setCurrentText(self.settings_manager.get("transition_default_line_style_str"))
        self.original_settings_on_open["transition_default_line_style_str"] = self.settings_manager.get("transition_default_line_style_str")
        self.transition_default_line_width_spin.setValue(self.settings_manager.get("transition_default_line_width"))
        self.original_settings_on_open["transition_default_line_width"] = self.settings_manager.get("transition_default_line_width")
        self.transition_default_arrowhead_combo.setCurrentText(self.settings_manager.get("transition_default_arrowhead_style").capitalize())
        self.original_settings_on_open["transition_default_arrowhead_style"] = self.settings_manager.get("transition_default_arrowhead_style")
        self.transition_default_font_family_combo.setCurrentFont(QFont(self.settings_manager.get("transition_default_font_family")))
        self.original_settings_on_open["transition_default_font_family"] = self.settings_manager.get("transition_default_font_family")
        self.transition_default_font_size_spin.setValue(self.settings_manager.get("transition_default_font_size"))
        self.original_settings_on_open["transition_default_font_size"] = self.settings_manager.get("transition_default_font_size")

        self.comment_default_font_family_combo.setCurrentFont(QFont(self.settings_manager.get("comment_default_font_family")))
        self.original_settings_on_open["comment_default_font_family"] = self.settings_manager.get("comment_default_font_family")
        self.comment_default_font_size_spin.setValue(self.settings_manager.get("comment_default_font_size"))
        self.original_settings_on_open["comment_default_font_size"] = self.settings_manager.get("comment_default_font_size")
        self.comment_default_font_italic_cb.setChecked(self.settings_manager.get("comment_default_font_italic"))
        self.original_settings_on_open["comment_default_font_italic"] = self.settings_manager.get("comment_default_font_italic")


        self.resource_monitor_enabled_cb.setChecked(self.settings_manager.get("resource_monitor_enabled"))
        self.original_settings_on_open["resource_monitor_enabled"] = self.resource_monitor_enabled_cb.isChecked()
        self.resource_monitor_interval_spin.setValue(self.settings_manager.get("resource_monitor_interval_ms"))
        self.original_settings_on_open["resource_monitor_interval_ms"] = self.resource_monitor_interval_spin.value()
        
        self._update_default_item_previews() 

        for widget in all_widgets_with_signals: widget.blockSignals(False)
        self.button_box.button(QDialogButtonBox.Apply).setEnabled(False) 


    def apply_settings(self):
        logger.info("Applying settings from Preferences dialog.")
        
        self.settings_manager.set("view_show_grid", self.show_grid_cb.isChecked(), save_immediately=False)
        self.settings_manager.set("view_snap_to_grid", self.snap_to_grid_cb.isChecked(), save_immediately=False)
        self.settings_manager.set("view_snap_to_objects", self.snap_to_objects_cb.isChecked(), save_immediately=False)
        self.settings_manager.set("view_show_snap_guidelines", self.show_snap_guidelines_cb.isChecked(), save_immediately=False)
        
        self.settings_manager.set("appearance_theme", self.theme_combo.currentText(), save_immediately=False)
        self.settings_manager.set("canvas_grid_minor_color", self.grid_minor_color_button.property("pendingColorHex"), save_immediately=False)
        self.settings_manager.set("canvas_grid_major_color", self.grid_major_color_button.property("pendingColorHex"), save_immediately=False)
        self.settings_manager.set("canvas_snap_guideline_color", self.snap_guideline_color_button.property("pendingColorHex"), save_immediately=False)
        
        self.settings_manager.set("state_default_shape", self.state_default_shape_combo.currentText().lower(), save_immediately=False)
        self.settings_manager.set("state_default_font_family", self.state_default_font_family_combo.currentFont().family(), save_immediately=False)
        self.settings_manager.set("state_default_font_size", self.state_default_font_size_spin.value(), save_immediately=False)
        self.settings_manager.set("state_default_font_bold", self.state_default_font_bold_cb.isChecked(), save_immediately=False)
        self.settings_manager.set("state_default_font_italic", self.state_default_font_italic_cb.isChecked(), save_immediately=False)
        self.settings_manager.set("state_default_border_style_str", self.state_default_border_style_combo.currentText(), save_immediately=False)
        self.settings_manager.set("state_default_border_width", self.state_default_border_width_spin.value(), save_immediately=False)
        
        self.settings_manager.set("transition_default_line_style_str", self.transition_default_line_style_combo.currentText(), save_immediately=False)
        self.settings_manager.set("transition_default_line_width", self.transition_default_line_width_spin.value(), save_immediately=False)
        self.settings_manager.set("transition_default_arrowhead_style", self.transition_default_arrowhead_combo.currentText().lower(), save_immediately=False)
        self.settings_manager.set("transition_default_font_family", self.transition_default_font_family_combo.currentFont().family(), save_immediately=False)
        self.settings_manager.set("transition_default_font_size", self.transition_default_font_size_spin.value(), save_immediately=False)

        self.settings_manager.set("comment_default_font_family", self.comment_default_font_family_combo.currentFont().family(), save_immediately=False)
        self.settings_manager.set("comment_default_font_size", self.comment_default_font_size_spin.value(), save_immediately=False)
        self.settings_manager.set("comment_default_font_italic", self.comment_default_font_italic_cb.isChecked(), save_immediately=False)

        self.settings_manager.set("resource_monitor_enabled", self.resource_monitor_enabled_cb.isChecked(), save_immediately=False)
        self.settings_manager.set("resource_monitor_interval_ms", self.resource_monitor_interval_spin.value(), save_immediately=False)

        # --- NEW: Apply MATLAB path setting ---
        if self.parent() and hasattr(self.parent(), 'matlab_connection'):
            matlab_conn = self.parent().matlab_connection
            new_path = self.matlab_path_edit.text().strip()
            if matlab_conn.matlab_path != new_path:
                matlab_conn.set_matlab_path(new_path)

        self.settings_manager.save_settings() 
        self.load_settings_to_ui() 
        QMessageBox.information(self, "Settings Applied", "Settings have been applied. Some changes may require an application restart.")


    def accept_settings(self):
        if self.button_box.button(QDialogButtonBox.Apply).isEnabled(): 
            self.apply_settings()
        self.accept()

    def on_reset_to_defaults(self):
        reply = QMessageBox.question(self, "Reset Settings",
                                     "Are you sure you want to reset all settings to their default values? "
                                     "This cannot be undone and may require an application restart.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_to_defaults()
            self.load_settings_to_ui() 
            QMessageBox.information(self, "Settings Reset", "All settings have been reset to defaults. Please restart the application if necessary.")

    def reject(self):
        if self.button_box.button(QDialogButtonBox.Apply).isEnabled():
            reply = QMessageBox.question(self, "Discard Changes?",
                                         "You have unsaved changes in the preferences. Discard them?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return 
        super().reject()
    
    # --- NEW METHODS for MATLAB settings tab ---
    def _matlab_auto_detect(self):
        if self.parent() and hasattr(self.parent(), 'matlab_connection'):
            self.matlab_test_status_label.setText("Status: Auto-detecting MATLAB, please wait...")
            self.matlab_test_status_label.setStyleSheet(f"font-style: italic; color: {COLOR_TEXT_SECONDARY}; background-color: {QColor(COLOR_ACCENT_PRIMARY_LIGHT).lighter(120).name()};")
            QApplication.processEvents()
            self.parent().matlab_connection.detect_matlab()

    def _matlab_browse(self):
        exe_filter = "MATLAB Executable (matlab.exe)" if sys.platform == 'win32' else "MATLAB Executable (matlab);;All Files (*)"
        start_dir = QDir.homePath()
        if self.matlab_path_edit.text() and QDir(QDir.toNativeSeparators(self.matlab_path_edit.text())).exists():
             path_obj = QDir(self.matlab_path_edit.text()); path_obj.cdUp(); start_dir = path_obj.absolutePath()
        path, _ = QFileDialog.getOpenFileName(self, "Select MATLAB Executable", start_dir, exe_filter)
        if path:
            self.matlab_path_edit.setText(path)
            self._matlab_update_test_label(False, "Path changed. Click 'Test Connection'.")

    def _matlab_test_connection(self):
        if self.parent() and hasattr(self.parent(), 'matlab_connection'):
            matlab_conn = self.parent().matlab_connection
            path = self.matlab_path_edit.text().strip()
            if not path:
                self._matlab_update_test_label(False, "Path is empty."); return
            self.matlab_test_status_label.setText("Status: Testing connection, please wait...")
            self.matlab_test_status_label.setStyleSheet(f"font-style: italic; color: {COLOR_TEXT_SECONDARY}; background-color: {QColor(COLOR_ACCENT_PRIMARY_LIGHT).lighter(120).name()};")
            QApplication.processEvents()
            if matlab_conn.set_matlab_path(path):
                matlab_conn.test_connection()

    def _matlab_update_test_label(self, success, message):
        status_prefix = "Status: "
        current_style = "font-weight: bold; padding: 5px; border-radius: 3px;"
        if success:
            current_style += f"color: {COLOR_ACCENT_SUCCESS}; background-color: {QColor(COLOR_ACCENT_SUCCESS).lighter(180).name()};"
        else:
            current_style += f"color: {COLOR_ACCENT_ERROR}; background-color: {QColor(COLOR_ACCENT_ERROR).lighter(180).name()};"
        self.matlab_test_status_label.setText(status_prefix + message)
        self.matlab_test_status_label.setStyleSheet(current_style)
        if success and self.parent().matlab_connection.matlab_path:
            self.matlab_path_edit.setText(self.parent().matlab_connection.matlab_path)
        
class ThemeEditDialog(QDialog):
    """A dialog to create or edit a theme's colors based on a core palette."""
    CORE_PALETTE_KEYS = {
        "COLOR_BACKGROUND_APP": "Main Background",
        "COLOR_TEXT_PRIMARY": "Primary Text",
        "COLOR_ACCENT_PRIMARY": "Primary Accent",
        "COLOR_ACCENT_SECONDARY": "Secondary Accent",
        "COLOR_ACCENT_SUCCESS": "Success/Green",
        "COLOR_ACCENT_WARNING": "Warning/Yellow",
        "COLOR_ACCENT_ERROR": "Error/Red",
        "COLOR_BACKGROUND_EDITOR_DARK": "Code Editor BG"
    }
    def __init__(self, theme_data: dict, theme_name: str, parent=None):
        super().__init__(parent)
        self.core_palette = {key: theme_data.get(key, "#ffffff") for key in self.CORE_PALETTE_KEYS}
        self.theme_manager = parent.theme_manager if hasattr(parent, 'theme_manager') else ThemeManager()

        self.setWindowTitle(f"Edit Theme: {theme_name}")
        self.setMinimumSize(500, 450)
        self.setWindowIcon(get_standard_icon(QStyle.SP_DesktopIcon, "Palette"))

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.color_editors = {}

        for key, label in self.CORE_PALETTE_KEYS.items():
            color_button = QPushButton(self.core_palette[key])
            color_button.setProperty("colorKey", key)
            self._update_color_button_style(color_button, QColor(self.core_palette[key]))
            color_button.clicked.connect(self._on_pick_color)
            self.color_editors[key] = color_button
            form_layout.addRow(label, color_button)
        
        layout.addLayout(form_layout)
        
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("Theme Preview (Example Text)")
        self.preview_label.setAutoFillBackground(True)
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_group)
        self._update_preview()

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_pick_color(self):
        button = self.sender()
        if not button: return

        key = button.property("colorKey")
        initial_color = QColor(self.core_palette[key])

        new_color = QColorDialog.getColor(initial_color, self, f"Select Color for {self.CORE_PALETTE_KEYS.get(key, key)}")
        if new_color.isValid() and new_color != initial_color:
            self.core_palette[key] = new_color.name()
            self._update_color_button_style(button, new_color)
            self._update_preview()
            
    
    def _update_preview(self):
        """Updates the live preview label based on the current core palette."""
        if not hasattr(self.theme_manager, 'derive_theme_from_palette'): # Guard
            logger.error("ThemeManager is missing 'derive_theme_from_palette' method.")
            return

        derived_theme = self.theme_manager.derive_theme_from_palette(self.core_palette)
        bg_color = derived_theme.get("COLOR_BACKGROUND_DIALOG", "#ffffff")
        text_color = derived_theme.get("COLOR_TEXT_PRIMARY", "#000000")
        accent_color = derived_theme.get("COLOR_ACCENT_PRIMARY", "#0000ff")
        
        palette = self.preview_label.palette()
        palette.setColor(QPalette.Window, QColor(bg_color))
        palette.setColor(QPalette.WindowText, QColor(text_color))
        self.preview_label.setPalette(palette)
        self.preview_label.setText(f"This is <b style='color:{accent_color};'>accented text.</b>")
    
            
    def _update_color_button_style(self, button: QPushButton, color: QColor):
        luminance = color.lightnessF()
        text_color = "#FFFFFF" if luminance < 0.5 else "#212121"
        button.setStyleSheet(f"background-color: {color.name()}; color: {text_color}; padding: 4px;")
        button.setText(color.name().upper())
        
    def get_theme_data(self) -> dict:
        """Returns the full, derived theme data from the core palette."""
        if not hasattr(self.theme_manager, 'derive_theme_from_palette'): # Guard
            logger.error("ThemeManager is missing 'derive_theme_from_palette' method. Returning core palette.")
            return self.core_palette
        return self.theme_manager.derive_theme_from_palette(self.core_palette)       