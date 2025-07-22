# fsm_designer_project/ui/dialogs/property_dialogs.py

import json
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QCheckBox, QPushButton, QTextEdit,
    QSpinBox, QComboBox, QDialogButtonBox, QColorDialog, QHBoxLayout,
    QLabel, QGroupBox, QStyle, QMainWindow, QFontComboBox, QDoubleSpinBox,
    QGraphicsScene, QUndoStack, QToolBar, QActionGroup, QApplication,
    QMessageBox
)
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QSize, QPointF

# --- NOTE: Relative import paths are adjusted (e.g., from ..dialogs import becomes from .) ---
from ...settings_manager import SettingsManager
from ..graphics.graphics_items import GraphicsStateItem
from ...utils.config import (
    COLOR_ITEM_STATE_DEFAULT_BG, COLOR_ITEM_TRANSITION_DEFAULT, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_ON_ACCENT, MECHATRONICS_SNIPPETS, DEFAULT_EXECUTION_ENV,
    APP_FONT_SIZE_SMALL, COLOR_TEXT_SECONDARY, COLOR_BACKGROUND_DIALOG, COLOR_BACKGROUND_LIGHT,
    COLOR_BORDER_MEDIUM, APP_FONT_FAMILY, DEFAULT_STATE_SHAPE,
    DEFAULT_STATE_BORDER_STYLE, DEFAULT_STATE_BORDER_WIDTH,
    COLOR_ACCENT_ERROR
)
from ...core.snippet_manager import CustomSnippetManager
from ...utils import get_standard_icon
from ..widgets.code_editor import CodeEditor

try:
    from ..graphics.graphics_scene import DiagramScene, ZoomableView
    IMPORTS_SUCCESSFUL = True
except ImportError:
    IMPORTS_SUCCESSFUL = False
    DiagramScene, ZoomableView = None, None

import logging
logger = logging.getLogger(__name__)


class StatePropertiesDialog(QDialog):
    def __init__(self, settings_manager, custom_snippet_manager, parent=None, current_properties=None, is_new_state=False, scene_ref=None):
        super().__init__(parent)
        self.setWindowTitle("State Properties")
        self.setWindowIcon(get_standard_icon(QStyle.SP_DialogApplyButton, "Props"))
        self.setMinimumWidth(650) 
        self.setStyleSheet(f"QDialog {{ background-color: {COLOR_BACKGROUND_DIALOG}; }} QLabel#SafetyNote, QLabel#HardwareHintLabel {{ font-size: {APP_FONT_SIZE_SMALL}; color: {COLOR_TEXT_SECONDARY}; }} QGroupBox {{ background-color: {QColor(COLOR_BACKGROUND_LIGHT).lighter(102).name()}; }}")
        
        # --- DEPENDENCY INJECTION ---
        self.settings_manager = settings_manager
        self.custom_snippet_manager = custom_snippet_manager
        # --- END DI ---
        
        self.parent_window_ref = parent
        self.scene_ref = scene_ref
        p = current_properties or {}

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12,12,12,12)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        general_layout.setSpacing(8)

        self.name_edit = QLineEdit(p.get('name', "StateName"))
        general_layout.addRow("Name:", self.name_edit)

        self.is_initial_cb = QCheckBox("Is Initial State"); self.is_initial_cb.setChecked(p.get('is_initial', False))
        self.is_final_cb = QCheckBox("Is Final State"); self.is_final_cb.setChecked(p.get('is_final', False))
        cb_layout = QHBoxLayout(); cb_layout.addWidget(self.is_initial_cb); cb_layout.addSpacing(15); cb_layout.addWidget(self.is_final_cb); cb_layout.addStretch()
        general_layout.addRow("", cb_layout)

        self.is_superstate_cb = QCheckBox("Is Superstate (Composite State)")
        self.is_superstate_cb.setChecked(p.get('is_superstate', False))
        self.is_superstate_cb.toggled.connect(self._on_superstate_toggled)
        self.edit_sub_fsm_button = QPushButton(get_standard_icon(QStyle.SP_FileDialogDetailedView, "Sub"), "Edit Sub-Machine...")
        self.edit_sub_fsm_button.clicked.connect(self._on_edit_sub_fsm)
        self.edit_sub_fsm_button.setEnabled(self.is_superstate_cb.isChecked())
        cb_layout_super = QHBoxLayout(); cb_layout_super.addWidget(self.is_superstate_cb); cb_layout_super.addSpacing(8); cb_layout_super.addWidget(self.edit_sub_fsm_button); cb_layout_super.addStretch()
        general_layout.addRow("Hierarchy:", cb_layout_super)
        
        self.description_edit = QTextEdit(p.get('description', "")); self.description_edit.setFixedHeight(60)
        general_layout.addRow("Description:", self.description_edit)
        
        tabs.addTab(general_tab, "General")

        raw_sub_fsm_data = p.get('sub_fsm_data', {})
        if isinstance(raw_sub_fsm_data, dict) and \
           all(k in raw_sub_fsm_data for k in ['states', 'transitions', 'comments']) and \
           isinstance(raw_sub_fsm_data.get('states'), list) and \
           isinstance(raw_sub_fsm_data.get('transitions'), list) and \
           isinstance(raw_sub_fsm_data.get('comments'), list):
            self.current_sub_fsm_data = raw_sub_fsm_data
        else:
            self.current_sub_fsm_data = {'states': [], 'transitions': [], 'comments': []}
            if raw_sub_fsm_data:
                logger.warning(f"State '{p.get('name', 'Unknown')}' had invalid sub_fsm_data, reset to empty.")

        appearance_tab = QWidget()
        appearance_layout = QFormLayout(appearance_tab)
        appearance_layout.setSpacing(8)

        self.color_button = QPushButton("Choose Color..."); self.color_button.setObjectName("ColorButton")
        self.current_color = QColor(p.get('color', COLOR_ITEM_STATE_DEFAULT_BG)); self._update_color_button_style()
        self.color_button.clicked.connect(self._choose_color)
        appearance_layout.addRow("Display Color:", self.color_button)

        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Rectangle", "Ellipse"])
        self.shape_combo.setCurrentText(p.get('shape_type', DEFAULT_STATE_SHAPE).capitalize())
        appearance_layout.addRow("Shape:", self.shape_combo)

        font_group = QGroupBox("Label Font")
        font_layout = QFormLayout(font_group)
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setCurrentFont(QFont(p.get('font_family', APP_FONT_FAMILY)))
        font_layout.addRow("Family:", self.font_family_combo)
        self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(6, 72); self.font_size_spin.setValue(p.get('font_size', 10))
        font_layout.addRow("Size:", self.font_size_spin)
        self.font_bold_cb = QCheckBox("Bold"); self.font_bold_cb.setChecked(p.get('font_bold', True))
        self.font_italic_cb = QCheckBox("Italic"); self.font_italic_cb.setChecked(p.get('font_italic', False))
        font_style_layout = QHBoxLayout(); font_style_layout.addWidget(self.font_bold_cb); font_style_layout.addWidget(self.font_italic_cb); font_style_layout.addStretch()
        font_layout.addRow("Style:", font_style_layout)
        appearance_layout.addWidget(font_group)

        border_group = QGroupBox("Border Style")
        border_layout = QFormLayout(border_group)
        self.border_style_combo = QComboBox()
        self.border_style_combo.addItems(list(SettingsManager.STRING_TO_QT_PEN_STYLE.keys()))
        default_border_style_str = p.get('border_style_str', SettingsManager.QT_PEN_STYLE_TO_STRING.get(DEFAULT_STATE_BORDER_STYLE, "Solid"))
        self.border_style_combo.setCurrentText(default_border_style_str)
        border_layout.addRow("Style:", self.border_style_combo)
        self.border_width_spin = QDoubleSpinBox(); self.border_width_spin.setRange(0.5, 10.0); self.border_width_spin.setSingleStep(0.1); self.border_width_spin.setValue(p.get('border_width', DEFAULT_STATE_BORDER_WIDTH)); self.border_width_spin.setDecimals(1)
        border_layout.addRow("Width:", self.border_width_spin)
        appearance_layout.addWidget(border_group)
        
        icon_group = QGroupBox("Custom Icon (Optional)")
        icon_layout = QFormLayout(icon_group)
        self.icon_path_edit = QLineEdit(p.get('icon_path', ''))
        self.icon_path_edit.setPlaceholderText("Path to icon image (e.g., .png, .svg)")
        self.icon_browse_button = QPushButton(get_standard_icon(QStyle.SP_DirOpenIcon), "Browse...")
        self.icon_browse_button.clicked.connect(self._browse_for_icon)
        icon_file_layout = QHBoxLayout(); icon_file_layout.addWidget(self.icon_path_edit, 1); icon_file_layout.addWidget(self.icon_browse_button)
        icon_layout.addRow("Icon File:", icon_file_layout)
        self.icon_preview_label = QLabel("<i>No icon selected</i>")
        self.icon_preview_label.setFixedSize(32,32); self.icon_preview_label.setAlignment(Qt.AlignCenter)
        self.icon_preview_label.setStyleSheet(f"border: 1px solid {COLOR_BORDER_MEDIUM}; background-color: {QColor(COLOR_BACKGROUND_LIGHT).lighter(105).name()};")
        self._update_icon_preview(p.get('icon_path', ''))
        self.icon_path_edit.textChanged.connect(self._update_icon_preview)
        appearance_layout.addWidget(icon_group)

        tabs.addTab(appearance_tab, "Appearance")

        actions_tab = QWidget()
        actions_layout_outer = QVBoxLayout(actions_tab)
        
        actions_group = QGroupBox("State Actions")
        actions_layout = QFormLayout(actions_group)
        actions_layout.setSpacing(8)

        self.action_language_combo = QComboBox()
        self.action_language_combo.addItems(list(MECHATRONICS_SNIPPETS.keys()))
        self.action_language_combo.setCurrentText(p.get('action_language', DEFAULT_EXECUTION_ENV))
        actions_layout.addRow("Action Language:", self.action_language_combo)

        self.entry_action_edit = CodeEditor(); self.entry_action_edit.setPlainText(p.get('entry_action', "")); self.entry_action_edit.setFixedHeight(80); self.entry_action_edit.setObjectName("ActionCodeEditor")
        self.during_action_edit = CodeEditor(); self.during_action_edit.setPlainText(p.get('during_action', "")); self.during_action_edit.setFixedHeight(80); self.during_action_edit.setObjectName("ActionCodeEditor")
        self.exit_action_edit = CodeEditor(); self.exit_action_edit.setPlainText(p.get('exit_action', "")); self.exit_action_edit.setFixedHeight(80); self.exit_action_edit.setObjectName("ActionCodeEditor")

        self.entry_action_snippet_btn = self._create_insert_snippet_button(self.entry_action_edit, "actions", " Action")
        self.during_action_snippet_btn = self._create_insert_snippet_button(self.during_action_edit, "actions", " Action")
        self.exit_action_snippet_btn = self._create_insert_snippet_button(self.exit_action_edit, "actions", " Action")
        
        
        # --- FIX: Moved AI Helper Button creation to after their target widgets are created ---
        self.entry_action_ai_btn = self._create_ai_helper_button(self.entry_action_edit, "action")
        self.during_action_ai_btn = self._create_ai_helper_button(self.during_action_edit, "action")
        self.exit_action_ai_btn = self._create_ai_helper_button(self.exit_action_edit, "action")

        self.action_language_combo.currentTextChanged.connect(self._on_action_language_changed)
        self._on_action_language_changed(self.action_language_combo.currentText())

        def add_field_with_note_and_hw_hint(form_layout, label_text, code_editor_widget, snippet_button, ai_button):
            h_editor_btn_layout = QHBoxLayout()
            h_editor_btn_layout.addWidget(code_editor_widget, 1)
            v_btn_container = QVBoxLayout()
            
            # --- MODIFIED: Add AI button to the button row ---
            btn_row = QHBoxLayout()
            btn_row.addWidget(snippet_button)
            btn_row.addWidget(ai_button) # Add the AI button here
            btn_row.addStretch()
            v_btn_container.addLayout(btn_row)
            
            hw_hint_label = QLabel("<small><i>E.g., for Arduino: `digitalWrite(LED_PIN, HIGH);`</i></small>")
            hw_hint_label.setObjectName("HardwareHintLabel"); hw_hint_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-style: italic; font-size: 7.5pt;")
            hw_hint_label.setToolTip("Consider actions that interact with hardware signals.\nThese can be simulated as variable changes or later mapped to real hardware in code generation.")
            v_btn_container.addWidget(hw_hint_label)
            safety_note_label = QLabel("<small><i>Note: Code safety depends on target environment.</i></small>")
            safety_note_label.setObjectName("SafetyNote")
            safety_note_label.setToolTip("For 'Python (Generic Simulation)', code is checked for common unsafe operations.\nFor other environments (Arduino, C, etc.), this editor provides text input; \nsafety and correctness are the responsibility of the external compiler/interpreter.")
            v_btn_container.addWidget(safety_note_label)
            v_btn_container.addStretch(1)
            h_editor_btn_layout.addLayout(v_btn_container)
            form_layout.addRow(label_text, h_editor_btn_layout)

        add_field_with_note_and_hw_hint(actions_layout, "Entry Action:", self.entry_action_edit, self.entry_action_snippet_btn, self.entry_action_ai_btn)
        add_field_with_note_and_hw_hint(actions_layout, "During Action:", self.during_action_edit, self.during_action_snippet_btn, self.during_action_ai_btn)
        add_field_with_note_and_hw_hint(actions_layout, "Exit Action:", self.exit_action_edit, self.exit_action_snippet_btn, self.exit_action_ai_btn)
        
        actions_layout_outer.addWidget(actions_group)
        tabs.addTab(actions_tab, "Actions")

        
        # --- START: NEW HARDWARE MAPPING TAB ---
        hardware_tab = QWidget()
        hardware_layout = QFormLayout(hardware_tab)
        hardware_layout.setSpacing(8)

        hw_group = QGroupBox("Hardware Output Mapping (Optional)")
        hw_form = QFormLayout(hw_group)

        # 1. Textbox for the variable name in the FSM
        self.hw_output_variable_edit = QLineEdit(p.get('hw_output_variable', ''))
        self.hw_output_variable_edit.setPlaceholderText("e.g., led_state or motor_speed")
        hw_form.addRow("FSM Variable Name:", self.hw_output_variable_edit)
        
        # 2. ComboBox to select the virtual component
        self.hw_component_combo = QComboBox()
        
        # Populate the combo box with available hardware components
        # This requires access to the main window's hardware manager
        available_components = ["None"]
        if hasattr(parent, 'hardware_sim_ui_manager'):
            hw_mgr = parent.hardware_sim_ui_manager
            available_components.extend(sorted(hw_mgr.virtual_leds.keys()))
            available_components.extend(sorted(hw_mgr.virtual_sliders.keys()))
        
        self.hw_component_combo.addItems(available_components)
        self.hw_component_combo.setCurrentText(p.get('hw_component_map', 'None'))
        hw_form.addRow("Map to Virtual Component:", self.hw_component_combo)

        hint_label = QLabel("<i>When this state is active, the value of the FSM variable above will be mapped to the selected component.</i>")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {APP_FONT_SIZE_SMALL};")
        hw_form.addRow(hint_label)

        hardware_layout.addWidget(hw_group)
        tabs.addTab(hardware_tab, "Hardware Mapping")
        # --- END: NEW HARDWARE MAPPING TAB ---

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        main_layout.addWidget(btns)

        if is_new_state: self.name_edit.selectAll(); self.name_edit.setFocus()

    # --- FIX: Fix double signal connection and duplicate return ---
    def _create_ai_helper_button(self, target_widget, code_type="action"):
        button = QPushButton()
        button.setIcon(get_standard_icon(QStyle.SP_MessageBoxQuestion, "AI"))
        button.setToolTip(f"Generate {code_type} code with AI")
        button.clicked.connect(lambda: self._on_ai_helper_clicked(target_widget, code_type))
        return button

    def _on_ai_helper_clicked(self, target_widget, code_type):
        description, ok = QInputDialog.getText(self, f"Generate {code_type.capitalize()} Code", f"Describe the {code_type} you want to create:")
        if not (ok and description.strip()):
            return
        
        # Find the main window to access its AI managers
        main_win = self.parent_window_ref
        while main_win and not isinstance(main_win, QMainWindow):
            main_win = main_win.parent()
        
        if not main_win or not hasattr(main_win, 'ai_chat_ui_manager'):
            QMessageBox.warning(self, "AI Not Available", "The AI assistant UI manager could not be found.")
            return
            
        language = self.action_language_combo.currentText()
        prompt = f"Generate a code snippet for this {code_type} in {language}: '{description}'. Respond with only the code, no explanations."
        
        # Call the handler in AIChatUIManager, passing the prompt and the target widget
        main_win.ai_chat_ui_manager.handle_inline_ai_request(prompt, language, target_widget)



    def _browse_for_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Icon File", QDir.homePath(), "Images (*.png *.jpg *.jpeg *.svg *.ico)")
        if file_path:
            self.icon_path_edit.setText(file_path)

    def _update_icon_preview(self, path_text: str):
        if path_text and os.path.exists(path_text):
            pixmap = QPixmap(path_text)
            if not pixmap.isNull():
                self.icon_preview_label.setPixmap(pixmap.scaled(32,32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.icon_preview_label.setText("<i>Invalid</i>")
        else:
            self.icon_preview_label.setText("<i>No icon</i>")

    def _update_snippet_button_menu(self, button: QPushButton, target_widget: CodeEditor, language_mode: str, snippet_category: str):
        menu = button.menu()
        menu.clear()
        menu.setStyleSheet("QMenu { font-size: 9pt; } QMenu::item { padding: 5px 20px; }")
        
        built_in_snippets = MECHATRONICS_SNIPPETS.get(language_mode, {}).get(snippet_category, {})
        custom_snippets_dict = {}
        if self.custom_snippet_manager: 
            custom_snippets_dict = self.custom_snippet_manager.get_custom_snippets(language_mode, snippet_category)

        if not built_in_snippets and not custom_snippets_dict:
            action = QAction(f"(No '{snippet_category}' snippets for {language_mode})", self)
            action.setEnabled(False)
            menu.addAction(action)
            button.setEnabled(False)
            return

        button.setEnabled(True)
        if built_in_snippets:
            built_in_header = QAction("Built-in Snippets", self); built_in_header.setEnabled(False)
            menu.addAction(built_in_header)
            for name, snippet in built_in_snippets.items():
                action = QAction(name, self)
                action.triggered.connect(lambda checked=False, text_edit=target_widget, s=snippet: text_edit.insertPlainText(s + "\n"))
                menu.addAction(action)
        
        if custom_snippets_dict:
            if built_in_snippets: menu.addSeparator()
            custom_header = QAction("Custom Snippets", self); custom_header.setEnabled(False)
            menu.addAction(custom_header)
            for name, snippet_code in custom_snippets_dict.items():
                action = QAction(f"{name}", self)
                action.triggered.connect(lambda checked=False, text_edit=target_widget, s=snippet_code: text_edit.insertPlainText(s + "\n"))
                menu.addAction(action)

    def _on_action_language_changed(self, language_mode: str):
        self.entry_action_edit.set_language(language_mode)
        self.during_action_edit.set_language(language_mode)
        self.exit_action_edit.set_language(language_mode)
        self._update_snippet_button_menu(self.entry_action_snippet_btn, self.entry_action_edit, language_mode, "actions")
        self._update_snippet_button_menu(self.during_action_snippet_btn, self.during_action_edit, language_mode, "actions")
        self._update_snippet_button_menu(self.exit_action_snippet_btn, self.exit_action_edit, language_mode, "actions")

    def _create_insert_snippet_button(self, target_widget: CodeEditor, snippet_category: str, button_text="Insert...", icon_size_px=16):
        button = QPushButton(button_text); button.setObjectName("SnippetButton")
        button.setToolTip(f"Insert common {snippet_category[:-1] if snippet_category.endswith('s') else snippet_category} snippets");
        button.setIcon(get_standard_icon(QStyle.SP_FileDialogContentsView, "InsSnip"))
        button.setIconSize(QSize(icon_size_px, icon_size_px))
        button.setMenu(QMenu(self))
        return button
    
    
    def _on_superstate_toggled(self, checked):
        self.edit_sub_fsm_button.setEnabled(checked)
        if not checked:
            if self.current_sub_fsm_data and \
               (self.current_sub_fsm_data.get('states') or self.current_sub_fsm_data.get('transitions')):
                reply = QMessageBox.question(self, "Discard Sub-Machine?",
                                             "Unchecking 'Is Superstate' will clear its internal diagram data. Continue?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.current_sub_fsm_data = {'states': [], 'transitions': [], 'comments': []}
                else:
                    self.is_superstate_cb.blockSignals(True)
                    self.is_superstate_cb.setChecked(True)
                    self.is_superstate_cb.blockSignals(False)
                    self.edit_sub_fsm_button.setEnabled(True)


    def _on_edit_sub_fsm(self):
        parent_state_name = self.name_edit.text().strip() or "Unnamed Superstate"
        dialog_parent = self.parent()
        while dialog_parent and not isinstance(dialog_parent, QMainWindow) and hasattr(dialog_parent, 'parent') and callable(dialog_parent.parent):
            if dialog_parent.parent() == dialog_parent: break
            dialog_parent = dialog_parent.parent()
        if not dialog_parent: dialog_parent = self
        sub_editor_dialog = SubFSMEditorDialog(self.current_sub_fsm_data, parent_state_name, dialog_parent)
        if sub_editor_dialog.exec() == QDialog.Accepted:
            updated_data = sub_editor_dialog.get_updated_sub_fsm_data()
            self.current_sub_fsm_data = updated_data
            QMessageBox.information(self, "Sub-Machine Updated", "Sub-machine data has been updated in this dialog. Click OK to save these changes to the state.")

    def _choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Select State Color")
        if color.isValid(): self.current_color = color; self._update_color_button_style()

    def _update_color_button_style(self):
        luminance = self.current_color.lightnessF()
        text_color_name = COLOR_TEXT_ON_ACCENT if luminance < 0.5 else COLOR_TEXT_PRIMARY
        self.color_button.setStyleSheet(f"background-color: {self.current_color.name()}; color: {text_color_name}; border: 1px solid {self.current_color.darker(130).name()};")

    def get_properties(self):
        sub_data_to_return = {'states': [], 'transitions': [], 'comments': []}
        if self.is_superstate_cb.isChecked():
            sub_data_to_return = self.current_sub_fsm_data
        
        props = {
            'name': self.name_edit.text().strip(), 'is_initial': self.is_initial_cb.isChecked(),
            'is_final': self.is_final_cb.isChecked(), 'color': self.current_color.name(),
            'action_language': self.action_language_combo.currentText(),
            'entry_action': self.entry_action_edit.toPlainText().strip(),
            'during_action': self.during_action_edit.toPlainText().strip(),
            'exit_action': self.exit_action_edit.toPlainText().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'is_superstate': self.is_superstate_cb.isChecked(), 'sub_fsm_data': sub_data_to_return,
            'shape_type': self.shape_combo.currentText().lower(),
            'font_family': self.font_family_combo.currentFont().family(),
            'font_size': self.font_size_spin.value(),
            'font_bold': self.font_bold_cb.isChecked(),
            'font_italic': self.font_italic_cb.isChecked(),
            'border_style_str': self.border_style_combo.currentText(),
            'border_width': self.border_width_spin.value(),
            'icon_path': self.icon_path_edit.text().strip(),
            # --- NEW: Add hardware mapping properties ---
            'hw_output_variable': self.hw_output_variable_edit.text().strip(),
            'hw_component_map': self.hw_component_combo.currentText()
        }
        return props

class TransitionPropertiesDialog(QDialog):
    def __init__(self, custom_snippet_manager: CustomSnippetManager, parent=None, current_properties=None, is_new_transition=False):
        super().__init__(parent)
        self.setWindowTitle("Transition Properties")
        self.setWindowIcon(get_standard_icon(QStyle.SP_FileDialogInfoView, "Props"))
        self.setMinimumWidth(600)
        self.setStyleSheet(f"QDialog {{ background-color: {COLOR_BACKGROUND_DIALOG}; }} QLabel#SafetyNote, QLabel#HardwareHintLabel {{ font-size: {APP_FONT_SIZE_SMALL}; color: {COLOR_TEXT_SECONDARY}; }} QGroupBox {{ background-color: {QColor(COLOR_BACKGROUND_LIGHT).lighter(102).name()}; }}")
        
        self.custom_snippet_manager = custom_snippet_manager
        self.parent_window_ref = parent # Store reference for AI helper
        main_layout = QVBoxLayout(self)
        
        main_layout.setSpacing(10) 
        main_layout.setContentsMargins(12,12,12,12) 
        p = current_properties or {}

        tabs = QTabWidget() 
        main_layout.addWidget(tabs)

        logic_tab = QWidget()
        logic_layout_outer = QVBoxLayout(logic_tab)

        logic_group = QGroupBox("Identification & Logic")
        logic_layout = QFormLayout(logic_group)
        logic_layout.setSpacing(8) 

        self.event_edit = QLineEdit(p.get('event', ""))
        self.condition_edit = QLineEdit(p.get('condition', ""))

        self.event_snippet_btn = self._create_insert_snippet_button_lineedit(self.event_edit, "events", " Event")
        self.condition_snippet_btn = self._create_insert_snippet_button_lineedit(self.condition_edit, "conditions", " Condition")
        
        # --- NEW: AI Helper buttons for transition ---
        self.condition_ai_btn = self._create_ai_helper_button(self.condition_edit, "condition")

        def add_lineedit_with_snippet(form_layout, label_text, edit_widget, snippet_button, ai_button=None, is_code_field=True):
            h_editor_btn_layout = QHBoxLayout(); h_editor_btn_layout.setSpacing(6)
            h_editor_btn_layout.addWidget(edit_widget, 1)
            v_btn_container = QVBoxLayout()
            
            btn_row = QHBoxLayout()
            btn_row.addWidget(snippet_button)
            if ai_button:
                btn_row.addWidget(ai_button)
            btn_row.addStretch()
            v_btn_container.addLayout(btn_row)

            if is_code_field:
                v_btn_container.addStretch() 
            h_editor_btn_layout.addLayout(v_btn_container)
            
            field_v_layout = QVBoxLayout(); field_v_layout.setSpacing(3) 
            field_v_layout.addLayout(h_editor_btn_layout)
            if is_code_field: 
                safety_note_label = QLabel("<small><i>Note: Guard conditions are evaluated. Python syntax for sim.</i></small>")
                safety_note_label.setObjectName("SafetyNote")
                safety_note_label.setToolTip("Conditions are evaluated as Python expressions in the simulator.\nEnsure syntax is valid for the target language during code generation.")
                field_v_layout.addWidget(safety_note_label)
            form_layout.addRow(label_text, field_v_layout)

        add_lineedit_with_snippet(logic_layout, "Event Trigger:", self.event_edit, self.event_snippet_btn, is_code_field=False)
        add_lineedit_with_snippet(logic_layout, "Condition (Guard):", self.condition_edit, self.condition_snippet_btn, self.condition_ai_btn, is_code_field=True)
        logic_layout_outer.addWidget(logic_group)
        
        action_group = QGroupBox("Transition Action")
        action_form_layout = QFormLayout(action_group)
        action_form_layout.setSpacing(8) 

        self.action_language_combo = QComboBox()
        self.action_language_combo.addItems(list(MECHATRONICS_SNIPPETS.keys()))
        self.action_language_combo.setCurrentText(p.get('action_language', DEFAULT_EXECUTION_ENV))
        action_form_layout.addRow("Action Language:", self.action_language_combo)

        self.action_edit = CodeEditor(); self.action_edit.setPlainText(p.get('action', "")); self.action_edit.setFixedHeight(80); self.action_edit.setObjectName("ActionCodeEditor") 
        self.action_snippet_btn = self._create_insert_snippet_button_codeeditor(self.action_edit, "actions", " Action")
        self.action_ai_btn = self._create_ai_helper_button(self.action_edit, "action") # New AI button

        def add_codeeditor_with_snippet_and_hw_hint(form_layout, label_text, code_editor_widget, snippet_button, ai_button):
            h_editor_btn_layout = QHBoxLayout(); h_editor_btn_layout.setSpacing(6)
            h_editor_btn_layout.addWidget(code_editor_widget, 1)
            v_btn_container = QVBoxLayout(); v_btn_container.setSpacing(3)
            
            btn_row = QHBoxLayout(); btn_row.addWidget(snippet_button); btn_row.addWidget(ai_button); btn_row.addStretch()
            v_btn_container.addLayout(btn_row)

            hw_hint_label = QLabel("<small><i>E.g., `motor_speed = 100;` or `valve_open();`</i></small>")
            hw_hint_label.setObjectName("HardwareHintLabel"); hw_hint_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-style: italic; font-size: 7.5pt;")
            hw_hint_label.setToolTip("Consider actions that set hardware outputs or call control functions.")
            v_btn_container.addWidget(hw_hint_label)
            safety_note_label = QLabel("<small><i>Note: Code safety depends on target. Generic Python checked.</i></small>")
            safety_note_label.setObjectName("SafetyNote")
            v_btn_container.addWidget(safety_note_label)
            v_btn_container.addStretch(1)
            h_editor_btn_layout.addLayout(v_btn_container)
            form_layout.addRow(label_text, h_editor_btn_layout)
        add_codeeditor_with_snippet_and_hw_hint(action_form_layout, "Action:", self.action_edit, self.action_snippet_btn, self.action_ai_btn)
        logic_layout_outer.addWidget(action_group)
        tabs.addTab(logic_tab, "Logic & Action")


        self.action_language_combo.currentTextChanged.connect(self._on_action_language_changed)
        self._on_action_language_changed(self.action_language_combo.currentText()) 

        appearance_tab = QWidget()
        appearance_layout = QFormLayout(appearance_tab)
        appearance_layout.setSpacing(8)

        self.color_button = QPushButton("Choose Color..."); self.color_button.setObjectName("ColorButton")
        self.current_color = QColor(p.get('color', COLOR_ITEM_TRANSITION_DEFAULT)); self._update_color_button_style()
        self.color_button.clicked.connect(self._choose_color)
        appearance_layout.addRow("Display Color:", self.color_button)
        
        self.offset_perp_spin = QSpinBox(); self.offset_perp_spin.setRange(-1000, 1000); self.offset_perp_spin.setValue(int(p.get('control_offset_x', 0))); self.offset_perp_spin.setSuffix(" px")
        self.offset_tang_spin = QSpinBox(); self.offset_tang_spin.setRange(-1000, 1000); self.offset_tang_spin.setValue(int(p.get('control_offset_y', 0))); self.offset_tang_spin.setSuffix(" px")
        curve_layout = QHBoxLayout()
        curve_layout.addWidget(QLabel("Bend (Perp):")); curve_layout.addWidget(self.offset_perp_spin,1); curve_layout.addSpacing(15)
        curve_layout.addWidget(QLabel("Mid Shift (Tang):")); curve_layout.addWidget(self.offset_tang_spin,1); curve_layout.addStretch()
        appearance_layout.addRow("Curve Shape:", curve_layout)
        
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(list(SettingsManager.STRING_TO_QT_PEN_STYLE.keys()))
        self.line_style_combo.setCurrentText(p.get('line_style_str', SettingsManager.QT_PEN_STYLE_TO_STRING.get(DEFAULT_TRANSITION_LINE_STYLE, "Solid")))
        appearance_layout.addRow("Line Style:", self.line_style_combo)

        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.5, 10.0); self.line_width_spin.setSingleStep(0.1)
        self.line_width_spin.setValue(p.get('line_width', DEFAULT_TRANSITION_LINE_WIDTH)); self.line_width_spin.setDecimals(1)
        appearance_layout.addRow("Line Width:", self.line_width_spin)

        self.arrowhead_style_combo = QComboBox()
        self.arrowhead_style_combo.addItems(["Filled", "Open", "None"]) 
        self.arrowhead_style_combo.setCurrentText(p.get('arrowhead_style', DEFAULT_TRANSITION_ARROWHEAD).capitalize())
        appearance_layout.addRow("Arrowhead:", self.arrowhead_style_combo)

        label_font_group = QGroupBox("Label Font")
        label_font_layout = QFormLayout(label_font_group)
        self.label_font_family_combo = QFontComboBox()
        self.label_font_family_combo.setCurrentFont(QFont(p.get('label_font_family', APP_FONT_FAMILY)))
        label_font_layout.addRow("Family:", self.label_font_family_combo)
        self.label_font_size_spin = QSpinBox(); self.label_font_size_spin.setRange(6, 24)
        self.label_font_size_spin.setValue(p.get('label_font_size', 8))
        label_font_layout.addRow("Size:", self.label_font_size_spin)
        appearance_layout.addWidget(label_font_group)

        self.description_edit = QTextEdit(p.get('description', "")); self.description_edit.setFixedHeight(60) 
        appearance_layout.addRow("Description:", self.description_edit)
        tabs.addTab(appearance_tab, "Appearance & Description")


        # --- START: NEW HARDWARE MAPPING TAB ---
        hardware_tab = QWidget()
        hardware_layout = QFormLayout(hardware_tab)
        hardware_layout.setSpacing(8)

        hw_group = QGroupBox("Hardware Input Mapping (Optional)")
        hw_form = QFormLayout(hw_group)

        # 1. ComboBox to select the virtual input component
        self.hw_input_component_combo = QComboBox()
        
        # Populate with available input components
        available_inputs = ["None"]
        if hasattr(parent, 'hardware_sim_ui_manager'):
            hw_mgr = parent.hardware_sim_ui_manager
            available_inputs.extend(sorted(hw_mgr.virtual_buttons.keys()))
            
        self.hw_input_component_combo.addItems(available_inputs)
        self.hw_input_component_combo.setCurrentText(p.get('hw_input_map', 'None'))
        hw_form.addRow("Triggered by Component:", self.hw_input_component_combo)

        hint_label = QLabel("<i>When the selected component is activated (e.g., button clicked), it will trigger this transition's <b>Event</b>.</i>")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {APP_FONT_SIZE_SMALL};")
        hw_form.addRow(hint_label)

        hardware_layout.addWidget(hw_group)
        tabs.addTab(hardware_tab, "Hardware Mapping")
        # --- END: NEW HARDWARE MAPPING TAB ---
        
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        if is_new_transition: self.event_edit.setFocus()

    # --- FIX: Fix double signal connection and duplicate return ---
    def _create_ai_helper_button(self, target_widget, code_type="action"):
        button = QPushButton()
        button.setIcon(get_standard_icon(QStyle.SP_MessageBoxQuestion, "AI"))
        button.setToolTip(f"Generate {code_type} code with AI")
        button.clicked.connect(lambda: self._on_ai_helper_clicked(target_widget, code_type))
        return button

    def _on_ai_helper_clicked(self, target_widget, code_type):
        description, ok = QInputDialog.getText(self, f"Generate {code_type.capitalize()} Code", f"Describe the {code_type} you want to create:")
        if not (ok and description):
            return

        main_win = self.parent_window_ref
        while main_win and not isinstance(main_win, QMainWindow):
            main_win = main_win.parent()

        if not main_win or not hasattr(main_win, 'ai_chat_ui_manager'):
            QMessageBox.warning(self, "AI Not Available", "The AI assistant manager could not be found.")
            return

        language = self.action_language_combo.currentText()
        prompt = f"Generate a code snippet for this {code_type} in {language}: '{description}'. Respond with only the code, no explanations."
        
        # MODIFIED: Call the handler with the target_widget
        main_win.ai_chat_ui_manager.handle_inline_ai_request(prompt, language, target_widget)

    def get_properties(self):
        return {
            'event': self.event_edit.text().strip(),
            'condition': self.condition_edit.text().strip(),
            'action_language': self.action_language_combo.currentText(),
            'action': self.action_edit.toPlainText().strip(),
            'color': self.current_color.name(),
            'control_offset_x': self.offset_perp_spin.value(),
            'control_offset_y': self.offset_tang_spin.value(),
            'description': self.description_edit.toPlainText().strip(),
            'line_style_str': self.line_style_combo.currentText(),
            'line_width': self.line_width_spin.value(),
            'arrowhead_style': self.arrowhead_style_combo.currentText().lower(),
            'label_font_family': self.label_font_family_combo.currentFont().family(),
            'label_font_size': self.label_font_size_spin.value(),
            # --- NEW: Add hardware mapping property ---
            'hw_input_map': self.hw_input_component_combo.currentText()
        }
    def _update_snippet_button_menu(self, button: QPushButton, target_widget, language_mode: str, snippet_category: str):
        menu = button.menu()
        menu.clear()
        menu.setStyleSheet("QMenu { font-size: 9pt; } QMenu::item { padding: 5px 20px; }")

        built_in_snippets = MECHATRONICS_SNIPPETS.get(language_mode, {}).get(snippet_category, {})
        custom_snippets_dict = {}
        if self.custom_snippet_manager:
            custom_snippets_dict = self.custom_snippet_manager.get_custom_snippets(language_mode, snippet_category)

        if not built_in_snippets and not custom_snippets_dict:
            action = QAction(f"(No '{snippet_category}' snippets for {language_mode})", self)
            action.setEnabled(False)
            menu.addAction(action)
            button.setEnabled(False)
            return

        button.setEnabled(True)
        if built_in_snippets:
            built_in_header = QAction("Built-in Snippets", self); built_in_header.setEnabled(False) 
            menu.addAction(built_in_header)
            for name, snippet in built_in_snippets.items():
                action = QAction(name, self)
                self._connect_snippet_action(action, target_widget, snippet)
                menu.addAction(action)
        
        if custom_snippets_dict:
            if built_in_snippets: menu.addSeparator()
            custom_header = QAction("Custom Snippets", self); custom_header.setEnabled(False) 
            menu.addAction(custom_header)
            for name, snippet_code in custom_snippets_dict.items():
                action = QAction(f"{name}", self) 
                self._connect_snippet_action(action, target_widget, snippet_code)
                menu.addAction(action)
    def _connect_snippet_action(self, action: QAction, target_widget, snippet: str):
        if isinstance(target_widget, QLineEdit):
            def insert_logic_lineedit(checked=False, line_edit=target_widget, s=snippet):
                current_text = line_edit.text(); cursor_pos = line_edit.cursorPosition()
                new_text = current_text[:cursor_pos] + s + current_text[cursor_pos:]
                line_edit.setText(new_text); line_edit.setCursorPosition(cursor_pos + len(s))
            action.triggered.connect(insert_logic_lineedit)
        elif isinstance(target_widget, CodeEditor) or isinstance(target_widget, QTextEdit):
            action.triggered.connect(lambda checked=False, text_edit=target_widget, s=snippet: text_edit.insertPlainText(s + "\n"))
    def _on_action_language_changed(self, language_mode: str):
        self.action_edit.set_language(language_mode)
        self._update_snippet_button_menu(self.event_snippet_btn, self.event_edit, language_mode, "events")
        self._update_snippet_button_menu(self.condition_snippet_btn, self.condition_edit, language_mode, "conditions")
        self._update_snippet_button_menu(self.action_snippet_btn, self.action_edit, language_mode, "actions")
    def _create_insert_snippet_button_lineedit(self, target_line_edit: QLineEdit, snippet_category: str, button_text="Insert..."):
        button = QPushButton(button_text); button.setObjectName("SnippetButton")
        button.setIcon(get_standard_icon(QStyle.SP_FileDialogContentsView,"InsSnip")); button.setIconSize(QSize(16,16))
        button.setToolTip(f"Insert common {snippet_category} snippets."); button.setMenu(QMenu(self))
        return button
    def _create_insert_snippet_button_codeeditor(self, target_code_editor: CodeEditor, snippet_category: str, button_text="Insert..."):
        button = QPushButton(button_text); button.setObjectName("SnippetButton")
        button.setIcon(get_standard_icon(QStyle.SP_FileDialogContentsView,"InsSnip")); button.setIconSize(QSize(16,16))
        button.setToolTip(f"Insert common {snippet_category} code snippets."); button.setMenu(QMenu(self))
        return button
    def _choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Select Transition Color")
        if color.isValid(): self.current_color = color; self._update_color_button_style()
    def _update_color_button_style(self):
        luminance = self.current_color.lightnessF()
        text_color_name = COLOR_TEXT_ON_ACCENT if luminance < 0.5 else COLOR_TEXT_PRIMARY
        self.color_button.setStyleSheet(f"background-color: {self.current_color.name()}; color: {text_color_name}; border: 1px solid {self.current_color.darker(130).name()};")

class CommentPropertiesDialog(QDialog):
    def __init__(self, parent=None, current_properties=None):
        super().__init__(parent)
        self.setWindowTitle("Comment Properties")
        self.setWindowIcon(get_standard_icon(QStyle.SP_MessageBoxInformation, "Cmt"))
        self.setStyleSheet(f"QDialog {{ background-color: {COLOR_BACKGROUND_DIALOG}; }}")
        p = current_properties or {}; layout = QVBoxLayout(self)
        layout.setSpacing(8); layout.setContentsMargins(12,12,12,12)
        
        self.text_edit = QTextEdit(p.get('text', "Comment"))
        self.text_edit.setMinimumHeight(100); self.text_edit.setPlaceholderText("Enter your comment or note here.")
        
        current_font = QFont(p.get('font_family', APP_FONT_FAMILY), p.get('font_size', 9))
        if p.get('font_italic', True): current_font.setItalic(True)
        self.text_edit.setCurrentFont(current_font) 
        
        layout.addWidget(QLabel("Comment Text:")); layout.addWidget(self.text_edit)

        font_group = QGroupBox("Font Style")
        font_layout = QFormLayout(font_group)
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setCurrentFont(current_font)
        font_layout.addRow("Family:", self.font_family_combo)
        self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(6, 48); self.font_size_spin.setValue(current_font.pointSize())
        font_layout.addRow("Size:", self.font_size_spin)
        self.font_italic_cb = QCheckBox("Italic"); self.font_italic_cb.setChecked(current_font.italic())
        font_layout.addRow(self.font_italic_cb)
        layout.addWidget(font_group)

        self.font_family_combo.currentFontChanged.connect(lambda f: self.text_edit.setFontFamily(f.family()))
        self.font_size_spin.valueChanged.connect(lambda s: self.text_edit.setFontPointSize(s))
        self.font_italic_cb.toggled.connect(lambda i: self.text_edit.setFontItalic(i))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setMinimumWidth(350); self.text_edit.setFocus(); self.text_edit.selectAll()
        
    def get_properties(self):
        return {
            'text': self.text_edit.toPlainText(),
            'font_family': self.font_family_combo.currentFont().family(),
            'font_size': self.font_size_spin.value(),
            'font_italic': self.font_italic_cb.isChecked()
        }

class SubFSMEditorDialog(QDialog):
    def __init__(self, sub_fsm_data_initial: dict, parent_state_name: str, parent_window_ref=None):
        super().__init__(parent_window_ref)
        self.parent_window_ref = parent_window_ref
        self.setWindowTitle(f"Sub-Machine Editor: {parent_state_name}")
        self.setWindowIcon(get_standard_icon(QStyle.SP_FileDialogDetailedView, "SubEdit"))
        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"QDialog {{ background-color: {COLOR_BACKGROUND_DIALOG}; }} QLabel#ErrorLabel {{ color: {COLOR_ACCENT_ERROR}; font-weight: bold; }}")


        self.current_sub_fsm_data = sub_fsm_data_initial if isinstance(sub_fsm_data_initial, dict) else \
                                    {'states': [], 'transitions': [], 'comments': []}


        layout = QVBoxLayout(self)

        if IMPORTS_SUCCESSFUL: 
            self.sub_undo_stack = QUndoStack(self)
            self.sub_scene = DiagramScene(self.sub_undo_stack, parent_window=self)
            self.sub_view = ZoomableView(self.sub_scene, self)
            toolbar = QToolBar("Sub-Editor Tools")
            toolbar.setIconSize(QSize(18,18)) 
            toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly) 
            self.sub_mode_action_group = QActionGroup(self)
            self.sub_mode_action_group.setExclusive(True)
            actions_data = [
                ("select", "Select/Move", QStyle.SP_ArrowRight, "SelSub"),
                ("state", "Add State", QStyle.SP_FileDialogNewFolder, "StSub"),
                ("transition", "Add Transition", QStyle.SP_ArrowForward, "TrSub"),
                ("comment", "Add Comment", QStyle.SP_MessageBoxInformation, "CmSub")
            ]
            for mode, text, icon_enum, icon_alt in actions_data:
                action = QAction(get_standard_icon(icon_enum, icon_alt), text, self)
                action.setToolTip(text) 
                action.setCheckable(True)
                action.triggered.connect(lambda checked=False, m=mode: self.sub_scene.set_mode(m))
                toolbar.addAction(action)
                self.sub_mode_action_group.addAction(action)
                setattr(self, f"sub_{mode}_action", action)

            toolbar.addSeparator()
            self.sub_undo_action = self.sub_undo_stack.createUndoAction(self, "Undo")
            self.sub_undo_action.setIcon(get_standard_icon(QStyle.SP_ArrowBack, "UnSub"))
            self.sub_undo_action.setToolTip("Undo")
            toolbar.addAction(self.sub_undo_action)
            self.sub_redo_action = self.sub_undo_stack.createRedoAction(self, "Redo")
            self.sub_redo_action.setIcon(get_standard_icon(QStyle.SP_ArrowForward, "ReSub"))
            self.sub_redo_action.setToolTip("Redo")
            toolbar.addAction(self.sub_redo_action)

            layout.addWidget(toolbar)
            layout.addWidget(self.sub_view, 1)
            self.sub_scene.load_diagram_data(self.current_sub_fsm_data)
            self.sub_undo_stack.clear()
            self.sub_scene.set_dirty(False) 
            if hasattr(self, 'sub_select_action'): self.sub_select_action.setChecked(True)
            self.sub_scene.set_mode("select")
            self.status_label = QLabel("Visually edit the sub-machine. Click OK to save changes to the parent state.")
            self.status_label.setStyleSheet(f"font-size: {APP_FONT_SIZE_SMALL}; color: {COLOR_TEXT_SECONDARY};")
        else: 
            self.json_edit_label = QLabel("<b>Visual Sub-Editor Failed to Load. Editing as JSON:</b>")
            self.json_edit_label.setObjectName("ErrorLabel") 
            layout.addWidget(self.json_edit_label)

            error_detail_label = QLabel(
                "<small><i>This might be due to missing optional dependencies (e.g., for graphical rendering) "
                "or an unexpected error. Check the application console/logs for specific import errors. "
                "You can still edit the sub-machine's raw JSON data below. Ensure the JSON structure is valid.</i></small>"
            )
            error_detail_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; margin-bottom: 5px;")
            error_detail_label.setWordWrap(True)
            layout.addWidget(error_detail_label)

            self.json_text_edit = CodeEditor() 
            self.json_text_edit.setPlainText(json.dumps(self.current_sub_fsm_data, indent=2, ensure_ascii=False))
            self.json_text_edit.setLineWrapMode(CodeEditor.NoWrap) 
            try:
                self.json_text_edit.set_language("JSON") 
            except Exception: 
                logger.warning("JSON language not available in CodeEditor, falling back to Text for SubFSM JSON.")
                self.json_text_edit.set_language("Text") 
            self.json_text_edit.setObjectName("SubFSMJsonEditor") 

            layout.addWidget(self.json_text_edit, 1)
            self.status_label = QLabel("Edit the JSON data for the sub-machine. Click OK to save changes.")


        layout.addWidget(self.status_label)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_changes); button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept_changes(self):
        if IMPORTS_SUCCESSFUL and hasattr(self, 'sub_scene'): 
            updated_data = self.sub_scene.get_diagram_data()
            if isinstance(updated_data, dict) and \
               all(k in updated_data for k in ['states', 'transitions', 'comments']) and \
               isinstance(updated_data.get('states'), list) and \
               isinstance(updated_data.get('transitions'), list) and \
               isinstance(updated_data.get('comments'), list):

                sub_states_list = updated_data.get('states', [])
                if sub_states_list:
                    has_initial = any(s.get('is_initial', False) for s in sub_states_list)
                    if not has_initial:
                        msg_box = QMessageBox(self)
                        msg_box.setIcon(QMessageBox.Warning)
                        msg_box.setWindowTitle("No Initial Sub-State")
                        msg_box.setText("The sub-machine does not have an initial state defined. "
                                        "It's recommended to define one for predictable behavior.")
                        save_anyway_btn = msg_box.addButton("Save Anyway", QMessageBox.AcceptRole)
                        set_first_btn = msg_box.addButton("Set First as Initial & Save", QMessageBox.YesRole)
                        cancel_btn = msg_box.addButton(QMessageBox.Cancel)
                        msg_box.setDefaultButton(cancel_btn)
                        msg_box.exec_()

                        reply = msg_box.clickedButton()

                        if reply == cancel_btn: return
                        if reply == set_first_btn:
                            if sub_states_list:
                                sub_states_list[0]['is_initial'] = True
                                self.log_message("INFO", f"Set state '{sub_states_list[0].get('name', 'Unnamed')}' as initial in sub-machine.")
                self.current_sub_fsm_data = updated_data
                self.accept()
            else:
                QMessageBox.warning(self, "Invalid Sub-Machine Structure", "Unexpected sub-machine editor data structure.")
                logger.error("SubFSMEditorDialog: Invalid data structure from sub_scene.get_diagram_data().")

        elif hasattr(self, 'json_text_edit'): 
            try:
                parsed_new_data = json.loads(self.json_text_edit.toPlainText())
                if isinstance(parsed_new_data, dict) and all(k in parsed_new_data for k in ['states', 'transitions', 'comments']):

                    sub_states_list_json = parsed_new_data.get('states', [])
                    if sub_states_list_json:
                        has_initial_json = any(s.get('is_initial', False) for s in sub_states_list_json)
                        if not has_initial_json:
                            msg_box = QMessageBox(self)
                            msg_box.setIcon(QMessageBox.Warning)
                            msg_box.setWindowTitle("No Initial Sub-State")
                            msg_box.setText("The sub-machine (JSON data) does not have an initial state defined. "
                                            "It's recommended to define one.")
                            save_anyway_btn = msg_box.addButton("Save Anyway", QMessageBox.AcceptRole)
                            set_first_btn = msg_box.addButton("Set First as Initial & Save", QMessageBox.YesRole)
                            cancel_btn = msg_box.addButton(QMessageBox.Cancel)
                            msg_box.setDefaultButton(cancel_btn)
                            msg_box.exec_()

                            reply = msg_box.clickedButton()
                            if reply == cancel_btn: return
                            if reply == set_first_btn:
                                if sub_states_list_json:
                                    sub_states_list_json[0]['is_initial'] = True 
                                    self.log_message("INFO", f"Set state '{sub_states_list_json[0].get('name', 'Unnamed')}' as initial in sub-machine (JSON).")
                                    self.json_text_edit.setPlainText(json.dumps(parsed_new_data, indent=2, ensure_ascii=False)) 
                    
                    self.current_sub_fsm_data = parsed_new_data 
                    self.accept()
                else:
                    QMessageBox.warning(self, "Invalid JSON Structure", "JSON needs 'states', 'transitions', 'comments' lists at the root.")
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "JSON Parse Error", f"Could not parse JSON: {e}")
        else:
            logger.error("SubFSMEditorDialog: Neither visual scene nor JSON editor found on accept_changes.")
            self.reject() 


    def get_updated_sub_fsm_data(self) -> dict:
        return self.current_sub_fsm_data

    def log_message(self, level, message):
        print(f"SubFSMEditor Log ({level}): {message}")
        if self.parent_window_ref and hasattr(self.parent_window_ref, 'log_message') and callable(self.parent_window_ref.log_message):
             self.parent_window_ref.log_message(level.upper(), f"[SubEditor] {message}")