# fsm_designer_project/ui/simulation/ui_py_simulation_manager.py

import html
import re 
from PyQt5.QtWidgets import (
    QLabel, QTextEdit, QComboBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QAction, QMessageBox, QGroupBox, QHBoxLayout, QVBoxLayout,
    QToolButton, QHeaderView, QAbstractItemView, QWidget, QStyle, QSlider,
    QGraphicsItem # Import QGraphicsItem
)
from PyQt5.QtGui import QIcon, QColor, QPalette
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QSize, Qt, QTime, QTimer

from ...core.fsm_simulator import FSMSimulator, FSMError
from ..graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem # Import GraphicsCommentItem
from ...utils import get_standard_icon
from ...utils.config import (APP_FONT_SIZE_SMALL, COLOR_ACCENT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_PRIMARY,
                    COLOR_PY_SIM_STATE_ACTIVE, COLOR_ACCENT_ERROR, COLOR_ACCENT_SUCCESS, COLOR_ACCENT_WARNING,
                    COLOR_BACKGROUND_MEDIUM, COLOR_BORDER_LIGHT, COLOR_ACCENT_SECONDARY) 
from ..animation_manager import AnimationManager
from ..widgets.virtual_hardware_widgets import VirtualLedWidget, VirtualSliderWidget

import logging
logger = logging.getLogger(__name__)

class PySimulationUIManager(QObject):
    simulationStateChanged = pyqtSignal(bool) 
    requestGlobalUIEnable = pyqtSignal(bool)  

    def __init__(self, main_window, action_handler, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self.action_handler = action_handler # Store the injected dependency
        self.animation_manager = self.mw.animation_manager if hasattr(self.mw, 'animation_manager') else None

        # --- Real-time simulation timer and widgets ---
        self.real_time_timer = QTimer(self)
        self.real_time_timer.timeout.connect(lambda: self.on_step_py_simulation(internal=True))
        self.py_sim_run_pause_btn: QPushButton = None
        self.py_sim_speed_slider: QSlider = None
        self.py_sim_speed_label: QLabel = None
        
        # --- UI Widget References ---
        self.py_sim_start_btn: QToolButton = None
        self.py_sim_stop_btn: QToolButton = None
        self.py_sim_reset_btn: QToolButton = None
        self.py_sim_step_btn: QPushButton = None
        self.py_sim_continue_btn: QPushButton = None
        self.py_sim_event_combo: QComboBox = None
        self.py_sim_event_name_edit: QLineEdit = None
        self.py_sim_trigger_event_btn: QPushButton = None
        self.py_sim_current_state_label: QLabel = None
        self.py_sim_current_tick_label: QLabel = None 
        self.py_sim_variables_table: QTableWidget = None
        self.py_sim_action_log_output: QTextEdit = None
        self._py_sim_currently_highlighted_item: GraphicsStateItem | None = None
        self._py_sim_currently_highlighted_transition: GraphicsTransitionItem | None = None 
        
        self._connect_actions_to_manager_slots()

        # --- Connect to the hardwareLinkLost signal ---
        if hasattr(self.mw, 'hardware_sim_ui_manager') and self.mw.hardware_sim_ui_manager:
            self.mw.hardware_sim_ui_manager.hardware_link_manager.hardwareLinkLost.connect(self.on_hardware_link_lost)
        
        # --- NEW: Direct connection for UI control ---
        self.requestGlobalUIEnable.connect(self._set_global_ui_enabled_state)

    # --- NEW: Slot to handle UI enabling/disabling ---
    @pyqtSlot(bool)
    def _set_global_ui_enabled_state(self, enable: bool):
        """
        Directly enables or disables diagram editing UI elements.
        This logic was moved from MainWindow for better encapsulation.
        """
        logger.debug(f"PySimUI: Setting global UI enabled state to: {enable}")
        
        # 1. Use the injected action_handler to control all editing actions
        self.action_handler.set_editing_actions_enabled(enable)

        # 2. Control other UI elements not managed by ActionHandler
        if hasattr(self.mw, 'elements_palette_dock'):
            self.mw.elements_palette_dock.setEnabled(enable)
        
        if hasattr(self.mw, 'properties_edit_dialog_button'):
            is_item_selected = False
            editor = self.mw.current_editor()
            if editor and editor.scene.selectedItems():
                is_item_selected = True
            self.mw.properties_edit_dialog_button.setEnabled(enable and is_item_selected)

        # 3. Control scene-level item interactivity
        editor = self.mw.current_editor()
        if editor:
            for item in editor.scene.items():
                if isinstance(item, (GraphicsStateItem, GraphicsCommentItem)):
                    # Only allow moving in 'select' mode
                    item.setFlag(QGraphicsItem.ItemIsMovable, enable and editor.scene.current_mode == "select")
            
            # Force scene back to select mode when simulation starts
            if not enable and editor.scene.current_mode != "select":
                editor.scene.set_mode("select")
        
        # 4. Also update other manager states that depend on simulation state
        self.mw._update_matlab_actions_enabled_state()
    # --- END NEW ---

    def _connect_actions_to_manager_slots(self):
        logger.debug("PySimUI: Connecting actions to manager slots...")
        if hasattr(self.mw, 'start_py_sim_action'):
            self.mw.start_py_sim_action.triggered.connect(self.on_start_py_simulation)
        if hasattr(self.mw, 'stop_py_sim_action'):
            self.mw.stop_py_sim_action.triggered.connect(lambda: self.on_stop_py_simulation(silent=False))
        if hasattr(self.mw, 'reset_py_sim_action'):
            self.mw.reset_py_sim_action.triggered.connect(self.on_reset_py_simulation)


    def create_dock_widget_contents(self) -> QWidget:
        py_sim_widget = QWidget()
        py_sim_layout = QVBoxLayout(py_sim_widget)
        py_sim_layout.setContentsMargins(4, 4, 4, 4)
        py_sim_layout.setSpacing(4)

        controls_group = QGroupBox("Simulation")
        controls_layout = QHBoxLayout(controls_group)
        controls_layout.setSpacing(4)
        
        icon_size = QSize(18,18)

        self.py_sim_start_btn = QToolButton()
        if hasattr(self.mw, 'start_py_sim_action'): self.py_sim_start_btn.setDefaultAction(self.mw.start_py_sim_action)
        self.py_sim_start_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.mw.start_py_sim_action.setText("Initialize")
        self.mw.start_py_sim_action.setToolTip("Initialize the Python simulator engine with the current diagram")

        self.py_sim_stop_btn = QToolButton()
        if hasattr(self.mw, 'stop_py_sim_action'): self.py_sim_stop_btn.setDefaultAction(self.mw.stop_py_sim_action)
        self.py_sim_stop_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.py_sim_reset_btn = QToolButton()
        if hasattr(self.mw, 'reset_py_sim_action'): self.py_sim_reset_btn.setDefaultAction(self.mw.reset_py_sim_action)
        self.py_sim_reset_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        for btn in [self.py_sim_start_btn, self.py_sim_stop_btn, self.py_sim_reset_btn]:
            btn.setIconSize(icon_size)
            controls_layout.addWidget(btn)
        
        controls_layout.addStretch()
        py_sim_layout.addWidget(controls_group)

        run_group = QGroupBox("Execution")
        run_layout = QHBoxLayout(run_group)
        run_layout.setSpacing(6)

        self.py_sim_run_pause_btn = QPushButton("Run")
        self.py_sim_run_pause_btn.setIcon(get_standard_icon(QStyle.SP_MediaPlay, "Run"))
        self.py_sim_run_pause_btn.clicked.connect(self.on_toggle_real_time_simulation)
        run_layout.addWidget(self.py_sim_run_pause_btn)
        
        self.py_sim_step_btn = QPushButton("Step")
        self.py_sim_step_btn.setIcon(get_standard_icon(QStyle.SP_MediaSeekForward, "Step"))
        self.py_sim_step_btn.clicked.connect(lambda: self.on_step_py_simulation(internal=False))
        run_layout.addWidget(self.py_sim_step_btn)

        self.py_sim_continue_btn = QPushButton("Continue")
        self.py_sim_continue_btn.setIcon(get_standard_icon(QStyle.SP_MediaSkipForward, "Cont"))
        self.py_sim_continue_btn.setToolTip("Continue execution from breakpoint")
        self.py_sim_continue_btn.clicked.connect(self.on_continue_py_simulation)
        run_layout.addWidget(self.py_sim_continue_btn)

        run_layout.addStretch()

        run_layout.addWidget(QLabel("Speed:"))
        self.py_sim_speed_slider = QSlider(Qt.Horizontal)
        self.py_sim_speed_slider.setRange(100, 2000)
        self.py_sim_speed_slider.setValue(1000)
        self.py_sim_speed_slider.setInvertedAppearance(True)
        self.py_sim_speed_slider.valueChanged.connect(self.on_speed_slider_changed)
        run_layout.addWidget(self.py_sim_speed_slider)
        self.py_sim_speed_label = QLabel("1000 ms/step")
        self.py_sim_speed_label.setMinimumWidth(80)
        run_layout.addWidget(self.py_sim_speed_label)
        
        py_sim_layout.addWidget(run_group)

        event_group = QGroupBox("Manual Event Trigger")
        event_layout = QHBoxLayout(event_group)
        self.py_sim_event_combo = QComboBox(); self.py_sim_event_combo.setEditable(False)
        event_layout.addWidget(self.py_sim_event_combo, 1)
        self.py_sim_event_name_edit = QLineEdit(); self.py_sim_event_name_edit.setPlaceholderText("Custom event name")
        event_layout.addWidget(self.py_sim_event_name_edit, 1)
        self.py_sim_trigger_event_btn = QPushButton("Trigger")
        self.py_sim_trigger_event_btn.setIcon(get_standard_icon(QStyle.SP_ArrowRight, "Trg"))
        self.py_sim_trigger_event_btn.clicked.connect(self._on_trigger_button_clicked)
        event_layout.addWidget(self.py_sim_trigger_event_btn)
        py_sim_layout.addWidget(event_group)
        
        state_group = QGroupBox("Current Status"); state_layout = QVBoxLayout(state_group); state_layout.setContentsMargins(5,5,5,5); state_layout.setSpacing(2); self.py_sim_current_state_label = QLabel("<i>Not Initialized</i>"); self.py_sim_current_state_label.setStyleSheet(f"font-size: 9pt; padding: 2px;"); state_layout.addWidget(self.py_sim_current_state_label); self.py_sim_current_tick_label = QLabel("Tick: 0"); self.py_sim_current_tick_label.setStyleSheet(f"font-size: {APP_FONT_SIZE_SMALL}; color: {COLOR_TEXT_SECONDARY}; padding: 1px 2px;"); state_layout.addWidget(self.py_sim_current_tick_label); py_sim_layout.addWidget(state_group)
        variables_group = QGroupBox("Variables"); variables_layout = QVBoxLayout(variables_group); self.py_sim_variables_table = QTableWidget(); self.py_sim_variables_table.setColumnCount(2); self.py_sim_variables_table.setHorizontalHeaderLabels(["Name", "Value"]); self.py_sim_variables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); variables_layout.addWidget(self.py_sim_variables_table); py_sim_layout.addWidget(variables_group)
        self.py_sim_variables_table.setSelectionMode(QAbstractItemView.SingleSelection); self.py_sim_variables_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed); self.py_sim_variables_table.itemChanged.connect(self.on_sim_variable_changed)
        log_group = QGroupBox("Action Log"); log_layout = QVBoxLayout(log_group); self.py_sim_action_log_output = QTextEdit(); self.py_sim_action_log_output.setReadOnly(True); self.py_sim_action_log_output.setObjectName("PySimActionLog"); log_layout.addWidget(self.py_sim_action_log_output); py_sim_layout.addWidget(log_group, 1)
        
        self._update_internal_controls_enabled_state() 
        return py_sim_widget

    @pyqtSlot(int)
    def on_speed_slider_changed(self, value):
        if self.py_sim_speed_label: self.py_sim_speed_label.setText(f"{value} ms/step")
        if self.real_time_timer.isActive():
            self.real_time_timer.setInterval(value)

    @pyqtSlot()
    def on_toggle_real_time_simulation(self):
        editor = self.mw.current_editor()
        if not editor or not editor.py_sim_active:
            return

        if self.real_time_timer.isActive():
            self.real_time_timer.stop()
            self.append_to_action_log(["Real-time simulation paused."])
        else:
            interval = self.py_sim_speed_slider.value()
            self.real_time_timer.setInterval(interval)
            self.real_time_timer.start()
            self.append_to_action_log([f"Real-time simulation started ({interval} ms/step)."])
        self._update_internal_controls_enabled_state()

    def _update_internal_controls_enabled_state(self):
        editor = self.mw.current_editor()
        sim_active = editor.py_sim_active if editor else False
        is_running_real_time = self.real_time_timer.isActive()
        is_paused_at_bp = sim_active and editor and editor.py_fsm_engine and editor.py_fsm_engine.paused_on_breakpoint
        
        self.py_sim_start_btn.setEnabled(not sim_active)
        self.py_sim_stop_btn.setEnabled(sim_active)
        self.py_sim_reset_btn.setEnabled(sim_active)

        run_controls_enabled = sim_active and not is_paused_at_bp
        self.py_sim_run_pause_btn.setEnabled(run_controls_enabled)
        self.py_sim_speed_slider.setEnabled(run_controls_enabled)
        
        if is_running_real_time:
            self.py_sim_run_pause_btn.setText("Pause"); self.py_sim_run_pause_btn.setIcon(get_standard_icon(QStyle.SP_MediaPause, "Pause"))
        else:
            self.py_sim_run_pause_btn.setText("Run"); self.py_sim_run_pause_btn.setIcon(get_standard_icon(QStyle.SP_MediaPlay, "Run"))
            
        manual_controls_enabled = sim_active and not is_running_real_time and not is_paused_at_bp
        self.py_sim_step_btn.setEnabled(manual_controls_enabled); self.py_sim_event_combo.setEnabled(manual_controls_enabled); self.py_sim_event_name_edit.setEnabled(manual_controls_enabled); self.py_sim_trigger_event_btn.setEnabled(manual_controls_enabled)
        
        self.py_sim_continue_btn.setEnabled(sim_active and is_paused_at_bp)

    def _set_simulation_active_state(self, is_running: bool):
        if not is_running:
            self.real_time_timer.stop()
        
        editor = self.mw.current_editor()
        if editor:
            editor.py_sim_active = is_running
        self.simulationStateChanged.emit(is_running) 
        self.requestGlobalUIEnable.emit(not is_running) 
        self._update_internal_controls_enabled_state()

    def _highlight_sim_active_state(self, state_name_to_highlight: str | None):
        editor = self.mw.current_editor();
        if not editor: return
        if self._py_sim_currently_highlighted_item:
            self._py_sim_currently_highlighted_item.set_py_sim_active_style(False)
            self._py_sim_currently_highlighted_item = None

        if state_name_to_highlight and editor.py_fsm_engine: 
            leaf_state = editor.py_fsm_engine.get_current_leaf_state_name()
            for item in editor.scene.items(): 
                if isinstance(item, GraphicsStateItem) and item.text_label == leaf_state:
                    item.set_py_sim_active_style(True); self._py_sim_currently_highlighted_item = item;
                    if editor.view: editor.view.ensureVisible(item, 50, 50);
                    break
        
        editor.scene.update()


    def update_dock_ui_contents(self):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active: 
            if self.py_sim_current_state_label: self.py_sim_current_state_label.setText("<i>Not Initialized</i>"); self.py_sim_current_state_label.setStyleSheet("")
            if self.py_sim_current_tick_label: self.py_sim_current_tick_label.setText("Tick: 0") 
            if self.py_sim_variables_table: self.py_sim_variables_table.setRowCount(0)
            self._highlight_sim_active_state(None)
            if self.py_sim_event_combo: self.py_sim_event_combo.clear(); self.py_sim_event_combo.addItem("None (Internal Step)")
            
            if hasattr(self.mw, 'hardware_sim_ui_manager'):
                hw_mgr = self.mw.hardware_sim_ui_manager
                for led in hw_mgr.virtual_leds.values(): led.setState(False)
                if hw_mgr.hardware_link_manager.is_connected:
                    for i in range(4): hw_mgr.hardware_link_manager.send_command(f"CMD:LED{i}:0")
                    for i in range(2): hw_mgr.hardware_link_manager.send_command(f"CMD:Slider{i}:0")

            self._update_internal_controls_enabled_state()
            return
        
        hierarchical_state_name = editor.py_fsm_engine.get_current_state_name()
        display_state_name = (hierarchical_state_name[:30] + '...') if len(hierarchical_state_name) > 33 else hierarchical_state_name
        
        paused_suffix = " <b style='color:orange;'>(Paused)</b>" if editor.py_fsm_engine.paused_on_breakpoint else ""
        self.py_sim_current_state_label.setText(f"<b>{html.escape(display_state_name)}</b>{paused_suffix}")

        active_color = COLOR_PY_SIM_STATE_ACTIVE; active_bg_color = QColor(active_color).lighter(170).name(); text_color = COLOR_TEXT_PRIMARY if QColor(active_bg_color).lightnessF() > 0.5 else "white"
        self.py_sim_current_state_label.setStyleSheet(f"font-size: 9pt; padding: 2px; color: {text_color}; background-color: {active_bg_color}; border: 1px solid {active_color.name()}; border-radius:3px; font-weight:bold;")

        self.py_sim_current_tick_label.setText(f"Tick: {editor.py_fsm_engine.current_tick}")

        self._highlight_sim_active_state(hierarchical_state_name)
        
        all_vars = sorted(editor.py_fsm_engine.get_variables().items())
        
        self.py_sim_variables_table.blockSignals(True)
        self.py_sim_variables_table.setRowCount(len(all_vars))
        for r, (name, val) in enumerate(all_vars):
            name_item = QTableWidgetItem(name); name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.py_sim_variables_table.setItem(r, 0, name_item)
            self.py_sim_variables_table.setItem(r, 1, QTableWidgetItem(str(val)))
        self.py_sim_variables_table.resizeColumnsToContents()
        self.py_sim_variables_table.blockSignals(False)

        current_event_text = self.py_sim_event_combo.currentText()
        possible_events = sorted(list(filter(None, editor.py_fsm_engine.get_possible_events_from_current_state())))
        self.py_sim_event_combo.clear(); self.py_sim_event_combo.addItems(["None (Internal Step)"] + possible_events)
        idx = self.py_sim_event_combo.findText(current_event_text)
        if idx != -1: self.py_sim_event_combo.setCurrentIndex(idx)

        if hasattr(self.mw, 'hardware_sim_ui_manager'):
            hw_mgr = self.mw.hardware_sim_ui_manager
            output_mappings = {d.get('hw_output_variable'): d.get('hw_component_map') for item in editor.scene.items() if isinstance(item, GraphicsStateItem) and (d := item.get_data()) and d.get('hw_output_variable') and d.get('hw_component_map') != "None"}
            sim_variables = editor.py_fsm_engine.get_variables()
            all_components = {**hw_mgr.virtual_leds, **hw_mgr.virtual_sliders}
            
            for comp_key, comp_widget in all_components.items():
                mapped_var_name = None
                for var, comp in output_mappings.items():
                    if comp == comp_key:
                        mapped_var_name = var
                        break
                
                new_value = 0
                if mapped_var_name and mapped_var_name in sim_variables:
                    new_value = sim_variables[mapped_var_name]

                if isinstance(comp_widget, VirtualLedWidget):
                    is_on = bool(new_value)
                    comp_widget.setState(is_on)
                    if hw_mgr.hardware_link_manager.is_connected:
                        hw_mgr.hardware_link_manager.send_command(f"CMD:{comp_key}:{1 if is_on else 0}")
                
                elif isinstance(comp_widget, VirtualSliderWidget):
                    slider_val = int(new_value) if new_value is not None else 0
                    comp_widget.blockSignals(True)
                    comp_widget.setValue(slider_val)
                    comp_widget.blockSignals(False)
                    if hw_mgr.hardware_link_manager.is_connected:
                        hw_mgr.hardware_link_manager.send_command(f"CMD:{comp_key}:{slider_val}")

        self._update_internal_controls_enabled_state()

    def append_to_action_log(self, log_entries: list[str]):
        if not self.py_sim_action_log_output: return
        time_color, default_log_color = QColor(COLOR_TEXT_SECONDARY).darker(110).name(), self.py_sim_action_log_output.palette().color(QPalette.Text).name()
        error_color, warning_color = QColor(COLOR_ACCENT_ERROR).name(), QColor(COLOR_ACCENT_WARNING).darker(10).name()
        highlight_color, success_color = QColor(COLOR_ACCENT_PRIMARY).name(), QColor(COLOR_ACCENT_SUCCESS).darker(110).name()
        breakpoint_color = QColor(COLOR_ACCENT_WARNING).name()
        
        editor = self.mw.current_editor()

        if editor and self.animation_manager:
            for entry in log_entries:
                match_trans = re.search(r"After transition on '([^']*)' from '([^']*)' to '([^']*)'", entry)
                if match_trans:
                    event, source, target = match_trans.groups()
                    self.animation_manager.animate_state_exit(source)
                    self.animation_manager.animate_transition(source, target, event)

                match_entry = re.search(r"Entering state: ([^\s(]+)", entry)
                if match_entry:
                    state_name = match_entry.group(1)
                    self.animation_manager.animate_state_entry(state_name)

        for entry in log_entries:
            timestamp = QTime.currentTime().toString('hh:mm:ss.zzz'); tick_str = ""
            tick_match = re.match(r"(\[SUB\] )*\[Tick (\d+)\] (.*)", entry); actual_entry_msg = tick_match.group(3) if tick_match else entry
            if tick_match: tick_str = f"<span style='color:{QColor(COLOR_TEXT_SECONDARY).lighter(110).name()}; font-size:7pt;'>{tick_match.group(1) or ''}Tick {tick_match.group(2)}</span> "
            cleaned_entry, current_color, style_tags = html.escape(actual_entry_msg), default_log_color, ("", "")
            if "[HALT]" in entry or "BREAKPOINT" in entry or "PAUSED" in entry: current_color, style_tags = breakpoint_color, ("<b><i>", "</i></b>")
            elif "Continuing" in entry: current_color, style_tags = success_color, ("<i>", "</i>")
            elif any(kw in entry.upper() for kw in ["[EVAL ERROR]", "[HALTED]", "SECURITYERROR", "[CODE ERROR]"]): current_color, style_tags = error_color, ("<b>", "</b>")
            elif any(kw in entry for kw in ["[SAFETY CHECK", "[ACTION BLOCKED]", "Warning:"]): current_color, style_tags = warning_color, ("<b>", "</b>")
            elif any(kw in entry for kw in ["Entering state:", "Exiting state:", "After transition"]): current_color, style_tags = highlight_color, ("<b>", "</b>")
            elif any(kw in entry for kw in ["initialized", "started.", "stopped.", "Reset"]): current_color, style_tags = success_color, ("<b><i>", "</i></b>")
            self.py_sim_action_log_output.append(f"<span style='color:{time_color}; font-size:7pt;'>[{timestamp}]</span> {tick_str}<span style='color:{current_color};'>{style_tags[0]}{cleaned_entry}{style_tags[1]}</span>")
        self.py_sim_action_log_output.verticalScrollBar().setValue(self.py_sim_action_log_output.verticalScrollBar().maximum())

    @pyqtSlot(QTableWidgetItem)
    def on_sim_variable_changed(self, item: QTableWidgetItem):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or item.column() != 1: return
        row = item.row(); var_name = self.py_sim_variables_table.item(row, 0).text().strip(); new_value_str = item.text().strip(); simulator_instance = editor.py_fsm_engine
        try: new_value = float(new_value_str) if '.' in new_value_str else int(new_value_str)
        except ValueError: new_value = True if new_value_str.lower() == 'true' else (False if new_value_str.lower() == 'false' else new_value_str.strip("'\""))
        if var_name in simulator_instance._variables: simulator_instance._variables[var_name] = new_value; self.append_to_action_log([f"Variable '{var_name}' set to: {new_value}"])
        else: self.update_dock_ui_contents()

    @pyqtSlot()
    def on_start_py_simulation(self):
        editor = self.mw.current_editor();
        if not editor: QMessageBox.warning(self.mw, "No Active Diagram", "Please select a diagram tab to initialize."); return
        if editor.py_sim_active: QMessageBox.information(self.mw, "Simulation Initialized", "Python simulation is already initialized for this tab."); return
        if editor.scene.is_dirty():
            if QMessageBox.question(self.mw, "Unsaved Changes", "The diagram has unsaved changes. Initialize simulation anyway?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.No: return
        diagram_data = editor.scene.get_diagram_data()
        if not diagram_data.get('states'): QMessageBox.warning(self.mw, "Empty Diagram", "Cannot initialize simulation: The diagram has no states."); return
        try:
            # --- FIX: Register graphics items with the animation manager ---
            if self.animation_manager:
                state_items_map = {item.text_label: item for item in editor.scene.items() if isinstance(item, GraphicsStateItem)}
                transition_items_map = {
                    (t.start_item.text_label, t.end_item.text_label, t.event_str): t 
                    for t in editor.scene.items() 
                    if isinstance(t, GraphicsTransitionItem) and t.start_item and t.end_item
                }
                self.animation_manager.register_graphics_items(state_items_map, transition_items_map)
                logger.info("Registered scene items with AnimationManager for simulation.")
            # --- END FIX ---

            editor.py_fsm_engine = FSMSimulator(diagram_data['states'], diagram_data['transitions'], halt_on_action_error=True)
            self._set_simulation_active_state(True); 
            if self.py_sim_action_log_output: self.py_sim_action_log_output.clear();
            initial_log = ["Python FSM Simulation initialized."] + editor.py_fsm_engine.get_last_executed_actions_log();
            self.append_to_action_log(initial_log); self.update_dock_ui_contents()
        except (FSMError, Exception) as e:
            QMessageBox.critical(self.mw, "FSM Initialization Error", f"Failed to initialize Python FSM simulation:\n{e}")
            self.append_to_action_log([f"ERROR Initializing Sim: {e}"]); editor.py_fsm_engine = None; self._set_simulation_active_state(False)

    @pyqtSlot(bool)
    def on_stop_py_simulation(self, silent=False):
        editor = self.mw.current_editor();
        if not editor or not editor.py_sim_active: return
        self.real_time_timer.stop()
        self._highlight_sim_active_state(None); 
        editor.py_fsm_engine = None; self._set_simulation_active_state(False) 
        self.update_dock_ui_contents()
        if not silent: self.append_to_action_log(["Python FSM Simulation stopped."])
        if self.animation_manager: self.animation_manager.clear_animations()

    @pyqtSlot()
    def _on_trigger_button_clicked(self):
        """Slot to handle the button click, which then calls the main logic.
        This acts as an adapter for the clicked(bool) signal."""
        self.on_trigger_py_event()

    @pyqtSlot()
    def on_reset_py_simulation(self):
        editor = self.mw.current_editor();
        if not editor or not editor.py_fsm_engine: return
        self.real_time_timer.stop()
        if self.animation_manager: self.animation_manager.clear_animations()
        try:
            editor.py_fsm_engine.reset()
            if self.py_sim_action_log_output: self.py_sim_action_log_output.append("<hr><i style='color:grey'>Simulation Reset</i><hr>")
            self.append_to_action_log(editor.py_fsm_engine.get_last_executed_actions_log()); self.update_dock_ui_contents()
        except (FSMError, Exception) as e: QMessageBox.critical(self.mw, "FSM Reset Error", f"Failed to reset simulation:\n{e}")

    @pyqtSlot(bool)
    def on_step_py_simulation(self, internal=False):
        editor = self.mw.current_editor();
        if not editor or not editor.py_fsm_engine:
            if not internal: QMessageBox.warning(self.mw, "Not Initialized", "Please initialize the simulation first.");
            return
        try:
            _, log_entries = editor.py_fsm_engine.step(event_name=None); self.append_to_action_log(log_entries); self.update_dock_ui_contents()
            if editor.py_fsm_engine.simulation_halted_flag or editor.py_fsm_engine.paused_on_breakpoint:
                self.real_time_timer.stop()
                if not internal: QMessageBox.information(self.mw, "Simulation Paused", "Simulation has paused due to a breakpoint or error.")
        except (FSMError, Exception) as e: self.real_time_timer.stop(); QMessageBox.critical(self.mw, "Step Error", f"An error occurred: {e}")
        self._update_internal_controls_enabled_state()
        
    @pyqtSlot(str)
    def on_trigger_py_event(self, external_event_name: str = None):
        editor = self.mw.current_editor();
        if not editor or not editor.py_fsm_engine: return
        event_to_trigger = external_event_name or self.py_sim_event_name_edit.text().strip() or (self.py_sim_event_combo.currentText() if self.py_sim_event_combo.currentText() != "None (Internal Step)" else None)
        if not event_to_trigger: self.on_step_py_simulation(); return
        self.append_to_action_log([f"--- Triggering event: '{html.escape(event_to_trigger)}' ---"])
        try:
            _, log_entries = editor.py_fsm_engine.step(event_name=event_to_trigger); self.append_to_action_log(log_entries); self.update_dock_ui_contents(); self.py_sim_event_name_edit.clear()
        except (FSMError, Exception) as e: QMessageBox.critical(self.mw, "Event Error", f"An error occurred: {e}")

    @pyqtSlot()
    def on_continue_py_simulation(self):
        editor = self.mw.current_editor()
        if not editor or not (editor.py_fsm_engine and editor.py_fsm_engine.paused_on_breakpoint): return
        if editor.py_fsm_engine.continue_simulation():
            self.append_to_action_log(["Simulation Continued..."]); self.on_step_py_simulation(internal=True); self.update_dock_ui_contents()
            
    # --- NEW: Slot for handling unexpected disconnects ---
    @pyqtSlot()
    def on_hardware_link_lost(self):
        """Pauses the simulation when the hardware connection is unexpectedly lost."""
        editor = self.mw.current_editor()
        if not editor or not editor.py_sim_active:
            return

        if self.real_time_timer.isActive():
            self.real_time_timer.stop()
            self._update_internal_controls_enabled_state()
            self.append_to_action_log([
                "[HALT] HARDWARE LINK LOST. Real-time simulation paused."
            ])
            QMessageBox.warning(self.mw, "Hardware Link Lost",
                                "The connection to the hardware was lost. The simulation has been paused.")