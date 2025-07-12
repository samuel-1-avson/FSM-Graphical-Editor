# fsm_designer_project/ui_py_simulation_manager.py

import html
import re 
from PyQt5.QtWidgets import (
    QLabel, QTextEdit, QComboBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QAction, QMessageBox, QGroupBox, QHBoxLayout, QVBoxLayout,
    QToolButton, QHeaderView, QAbstractItemView, QWidget, QStyle, QSlider
)
from PyQt5.QtGui import QIcon, QColor, QPalette
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QSize, Qt, QTime, QTimer

from .fsm_simulator import FSMSimulator, FSMError
from .graphics_items import GraphicsStateItem, GraphicsTransitionItem
from .utils import get_standard_icon
from .config import (APP_FONT_SIZE_SMALL, COLOR_ACCENT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_PRIMARY,
                    COLOR_PY_SIM_STATE_ACTIVE, COLOR_ACCENT_ERROR, COLOR_ACCENT_SUCCESS, COLOR_ACCENT_WARNING,
                    COLOR_BACKGROUND_MEDIUM, COLOR_BORDER_LIGHT, COLOR_ACCENT_SECONDARY) 
from .animation_manager import AnimationManager

import logging
logger = logging.getLogger(__name__)

class PySimulationUIManager(QObject):
    simulationStateChanged = pyqtSignal(bool) 
    requestGlobalUIEnable = pyqtSignal(bool)  

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.mw = main_window 
        self.animation_manager = self.mw.animation_manager if hasattr(self.mw, 'animation_manager') else None

        # --- NEW: Real-time simulation timer and widgets ---
        self.real_time_timer = QTimer(self)
        self.real_time_timer.timeout.connect(lambda: self.on_step_py_simulation(internal=True))
        self.py_sim_run_pause_btn: QPushButton = None
        self.py_sim_speed_slider: QSlider = None
        self.py_sim_speed_label: QLabel = None
        
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
        self.py_sim_step_btn.clicked.connect(self.on_step_py_simulation)
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
        self.py_sim_trigger_event_btn.clicked.connect(self.on_trigger_py_event)
        event_layout.addWidget(self.py_sim_trigger_event_btn)
        py_sim_layout.addWidget(event_group)
        
        state_group = QGroupBox("Current Status"); state_layout = QVBoxLayout(state_group); self.py_sim_current_state_label = QLabel("<i>Not Initialized</i>"); state_layout.addWidget(self.py_sim_current_state_label); self.py_sim_current_tick_label = QLabel("Tick: 0"); state_layout.addWidget(self.py_sim_current_tick_label); py_sim_layout.addWidget(state_group)
        variables_group = QGroupBox("Variables"); variables_layout = QVBoxLayout(variables_group); self.py_sim_variables_table = QTableWidget(); self.py_sim_variables_table.setColumnCount(2); self.py_sim_variables_table.setHorizontalHeaderLabels(["Name", "Value"]); self.py_sim_variables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); variables_layout.addWidget(self.py_sim_variables_table); py_sim_layout.addWidget(variables_group)
        self.py_sim_variables_table.setSelectionMode(QAbstractItemView.SingleSelection); self.py_sim_variables_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed); self.py_sim_variables_table.itemChanged.connect(self.on_sim_variable_changed)
        log_group = QGroupBox("Action Log"); log_layout = QVBoxLayout(log_group); self.py_sim_action_log_output = QTextEdit(); self.py_sim_action_log_output.setReadOnly(True); self.py_sim_action_log_output.setObjectName("PySimActionLog"); log_layout.addWidget(self.py_sim_action_log_output); py_sim_layout.addWidget(log_group, 1)
        
        self._update_internal_controls_enabled_state() 
        return py_sim_widget
    
    def _update_internal_controls_enabled_state(self):
        is_matlab_op_running = False
        if hasattr(self.mw, 'progress_bar') and self.mw.progress_bar: 
            is_matlab_op_running = self.mw.progress_bar.isVisible()
            
        editor = self.mw.current_editor()
        sim_active = editor.py_sim_active if editor else False
        sim_controls_enabled = sim_active and not is_matlab_op_running
        
        # --- NEW: Consider paused_on_breakpoint state ---
        is_paused_at_bp = False
        if sim_active and editor and editor.py_fsm_engine:
            is_paused_at_bp = editor.py_fsm_engine.paused_on_breakpoint
        # --- END NEW ---

        if self.py_sim_start_btn: self.py_sim_start_btn.setEnabled(not sim_active and not is_matlab_op_running)
        if self.py_sim_stop_btn: self.py_sim_stop_btn.setEnabled(sim_active and not is_matlab_op_running) # Stop is always available if sim is active
        if self.py_sim_reset_btn: self.py_sim_reset_btn.setEnabled(sim_active and not is_matlab_op_running) # Reset is always available if sim is active
        
        # Step and Trigger are disabled if paused at a breakpoint
        if self.py_sim_step_btn: self.py_sim_step_btn.setEnabled(sim_controls_enabled and not is_paused_at_bp)
        if self.py_sim_event_name_edit: self.py_sim_event_name_edit.setEnabled(sim_controls_enabled and not is_paused_at_bp)
        if self.py_sim_trigger_event_btn: self.py_sim_trigger_event_btn.setEnabled(sim_controls_enabled and not is_paused_at_bp)
        if self.py_sim_event_combo: self.py_sim_event_combo.setEnabled(sim_controls_enabled and not is_paused_at_bp)

        # Continue button is only enabled if paused at a breakpoint
        if self.py_sim_continue_btn: self.py_sim_continue_btn.setEnabled(sim_controls_enabled and is_paused_at_bp)


    def _set_simulation_active_state(self, is_running: bool):
        editor = self.mw.current_editor()
        if editor:
            editor.py_sim_active = is_running
        self.simulationStateChanged.emit(is_running) 
        self.requestGlobalUIEnable.emit(not is_running) 
        self._update_internal_controls_enabled_state() 

    def _highlight_sim_active_state(self, state_name_to_highlight: str | None):
        editor = self.mw.current_editor()
        if not editor: return

        if self._py_sim_currently_highlighted_item:
            self._py_sim_currently_highlighted_item.set_py_sim_active_style(False)
            self._py_sim_currently_highlighted_item = None

        item_to_highlight = None
        if state_name_to_highlight and editor.py_fsm_engine: 
            top_level_active_state_id = None
            if editor.py_fsm_engine.sm and editor.py_fsm_engine.sm.current_state:
                top_level_active_state_id = editor.py_fsm_engine.sm.current_state.id
            
            if top_level_active_state_id:
                for item in editor.scene.items(): 
                    if isinstance(item, GraphicsStateItem) and item.text_label == top_level_active_state_id:
                        logger.debug("PySimUI: Highlighting top-level active state '%s' (full hierarchical: '%s')", top_level_active_state_id, state_name_to_highlight)
                        item.set_py_sim_active_style(True)
                        self._py_sim_currently_highlighted_item = item
                        item_to_highlight = item # Store for animation
                        if editor.view: 
                             if hasattr(editor.view, 'ensureVisible') and callable(editor.view.ensureVisible):
                                editor.view.ensureVisible(item, 50, 50) 
                             else: 
                                editor.view.centerOn(item)
                        break
        
        # --- NEW: Trigger state entry animation ---
        if item_to_highlight and self.animation_manager:
            self.animation_manager.animate_state_entry(item_to_highlight)

        editor.scene.update()

    def _clear_transition_highlight(self, transition_item: GraphicsTransitionItem | None): 
        if transition_item and transition_item == self._py_sim_currently_highlighted_transition:
            transition_item.set_py_sim_active_style(False)
            self._py_sim_currently_highlighted_transition = None
            logger.debug("PySimUI: Cleared highlight for transition: %s", transition_item._compose_label_string() if transition_item else "None")


    def _highlight_sim_taken_transition(self, source_state_name: str | None, target_state_name: str | None, event_name: str | None): 
        editor = self.mw.current_editor()
        if not editor: return

        # --- MODIFIED: Animate instead of highlight ---
        if self.animation_manager and source_state_name and target_state_name and event_name:
            source_item = editor.scene.get_state_by_name(source_state_name)
            target_item = editor.scene.get_state_by_name(target_state_name)
            if source_item and target_item:
                self.animation_manager.animate_transition(source_item, target_item, event_name)
        # --- END MODIFICATION ---
        
        editor.scene.update()

    def update_dock_ui_contents(self):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active: 
            if self.py_sim_current_state_label:
                self.py_sim_current_state_label.setText("<i>Not Running</i>")
                self.py_sim_current_state_label.setStyleSheet(f"font-size: 9pt; padding: 2px; color: {COLOR_TEXT_SECONDARY}; background-color: {COLOR_BACKGROUND_MEDIUM}; border-radius:3px;") # Reduced padding
            if self.py_sim_current_tick_label: self.py_sim_current_tick_label.setText("Tick: 0") 

            if self.py_sim_variables_table:
                self.py_sim_variables_table.setRowCount(0)
            self._highlight_sim_active_state(None)
            self._highlight_sim_taken_transition(None, None, None)
            if self.py_sim_event_combo: self.py_sim_event_combo.clear(); self.py_sim_event_combo.addItem("None (Internal Step)")
            self._update_internal_controls_enabled_state()
            # --- NEW: Also clear hardware panel when sim is not running ---
            if hasattr(self.mw, 'hardware_sim_ui_manager'):
                for led in self.mw.hardware_sim_ui_manager.virtual_leds.values():
                    led.setState(False)
            return
            
        hierarchical_state_name = editor.py_fsm_engine.get_current_state_name() if editor.py_fsm_engine else "N/A"
        if self.py_sim_current_state_label:
            display_state_name = (hierarchical_state_name[:30] + '...') if len(hierarchical_state_name) > 33 else hierarchical_state_name
            
            # --- NEW: Indicate Paused State ---
            paused_suffix = " <b style='color:orange;'>(Paused at Breakpoint)</b>" if editor.py_fsm_engine.paused_on_breakpoint else ""
            self.py_sim_current_state_label.setText(f"<b>{html.escape(display_state_name)}</b>{paused_suffix}")
            # --- END NEW ---

            active_color = COLOR_PY_SIM_STATE_ACTIVE
            active_bg_color = QColor(active_color).lighter(170).name()
            active_text_color_final = COLOR_TEXT_PRIMARY if QColor(active_bg_color).lightnessF() > 0.5 else QColor("white").name()
            self.py_sim_current_state_label.setStyleSheet(f"font-size: 9pt; padding: 2px; color: {active_text_color_final}; background-color: {active_bg_color}; border: 1px solid {active_color.name()}; border-radius:3px; font-weight:bold;") # Reduced padding

        if self.py_sim_current_tick_label and editor.py_fsm_engine:
            self.py_sim_current_tick_label.setText(f"Tick: {editor.py_fsm_engine.current_tick}")

        self._highlight_sim_active_state(hierarchical_state_name)
        
        all_vars = []
        if editor.py_fsm_engine:
            all_vars.extend([(k, str(v)) for k, v in sorted(editor.py_fsm_engine.get_variables().items())])
            if editor.py_fsm_engine.active_sub_simulator: 
                all_vars.extend([(f"[SUB] {k}", str(v)) for k, v in sorted(editor.py_fsm_engine.active_sub_simulator.get_variables().items())])
        
        if self.py_sim_variables_table:
            # Block signals while we programmatically update the table
            self.py_sim_variables_table.blockSignals(True)
            self.py_sim_variables_table.setRowCount(len(all_vars))
            for r, (name, val) in enumerate(all_vars):
                # Make variable names read-only
                name_item = QTableWidgetItem(name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.py_sim_variables_table.setItem(r, 0, name_item)
                self.py_sim_variables_table.setItem(r, 1, QTableWidgetItem(val))
            
            self.py_sim_variables_table.resizeColumnsToContents()
            # Re-enable signals
            self.py_sim_variables_table.blockSignals(False)

        if self.py_sim_event_combo and editor.py_fsm_engine:
            current_text = self.py_sim_event_combo.currentText()
            self.py_sim_event_combo.clear(); self.py_sim_event_combo.addItem("None (Internal Step)")
            
            possible_events_set = set()
            if editor.py_fsm_engine.active_sub_simulator and editor.py_fsm_engine.active_sub_simulator.sm:
                possible_events_set.update(editor.py_fsm_engine.active_sub_simulator.get_possible_events_from_current_state())
            
            possible_events_set.update(editor.py_fsm_engine.get_possible_events_from_current_state())
            
            possible_events = sorted(list(filter(None, possible_events_set))) 

            if possible_events: self.py_sim_event_combo.addItems(possible_events)
            
            idx = self.py_sim_event_combo.findText(current_text)
            self.py_sim_event_combo.setCurrentIndex(idx if idx != -1 else 0)
        # --- START: NEW SECTION - Update Virtual Hardware Panel ---
        
        # Check if the hardware manager exists
        if hasattr(self.mw, 'hardware_sim_ui_manager'):
            hw_mgr = self.mw.hardware_sim_ui_manager
            
            # 1. Gather all hardware mappings from the diagram
            output_mappings = {}  # { 'fsm_variable_name': 'ComponentKey' }
            for item in editor.scene.items():
                if isinstance(item, GraphicsStateItem):
                    data = item.get_data()
                    var_name = data.get('hw_output_variable')
                    comp_name = data.get('hw_component_map')
                    if var_name and comp_name and comp_name != "None":
                        normalized_comp_key = comp_name.replace("Virtual ", "").replace(" ", "")
                        output_mappings[var_name] = normalized_comp_key

            # 2. Get the current values of all variables from the simulator
            sim_variables = editor.py_fsm_engine.get_variables()

            # 3. Iterate through mappings and update the UI
            for var_name, comp_key in output_mappings.items():
                if var_name in sim_variables:
                    value = sim_variables[var_name]
                    
                    # Update LEDs
                    if comp_key in hw_mgr.virtual_leds:
                        led_widget = hw_mgr.virtual_leds[comp_key]
                        # Set LED state based on the variable's truthiness (0/False is off, anything else is on)
                        led_widget.setState(bool(value))
                    
                    # Update Sliders (This shows feedback, e.g., if an action changes the value)
                    elif comp_key in hw_mgr.virtual_sliders:
                        slider_widget = hw_mgr.virtual_sliders[comp_key]
                        # Block signals to prevent a feedback loop
                        slider_widget.blockSignals(True)
                        slider_widget.setValue(int(value))
                        slider_widget.blockSignals(False)
        
        # --- END: NEW SECTION ---
        self._update_internal_controls_enabled_state()

    def append_to_action_log(self, log_entries: list[str]):
        if not self.py_sim_action_log_output: return
        
        time_color = QColor(COLOR_TEXT_SECONDARY).darker(110).name()
        default_log_color = self.py_sim_action_log_output.palette().color(QPalette.Text).name()
        error_color = COLOR_ACCENT_ERROR.name() if isinstance(COLOR_ACCENT_ERROR, QColor) else COLOR_ACCENT_ERROR
        warning_color = QColor(COLOR_ACCENT_WARNING).darker(10).name() 
        highlight_color = COLOR_ACCENT_PRIMARY.name() if isinstance(COLOR_ACCENT_PRIMARY, QColor) else COLOR_ACCENT_PRIMARY
        success_color = QColor(COLOR_ACCENT_SUCCESS).darker(110).name()
        breakpoint_color = QColor(COLOR_ACCENT_WARNING).name() # For breakpoint messages

        last_source_state, last_target_state, last_event = None, None, None
        for entry in reversed(log_entries): 
            match = re.search(r"\[Tick \d+\] After transition on '([^']*)' from '([^']*)' to '([^']*)'", entry)
            if match:
                last_event, last_source_state, last_target_state = match.groups()
                break 
            else: 
                match_before = re.search(r"\[Tick \d+\] Before transition on '([^']*)' from '([^']*)' to '([^']*)'", entry)
                if match_before:
                    last_event, last_source_state, last_target_state = match_before.groups()
        
        if last_source_state and last_target_state and last_event is not None:
            self._highlight_sim_taken_transition(last_source_state, last_target_state, last_event)
        
        for entry in log_entries:
            timestamp = QTime.currentTime().toString('hh:mm:ss.zzz')
            
            tick_str = ""
            tick_match = re.match(r"(\[SUB\] )*\[Tick (\d+)\] (.*)", entry)
            if tick_match:
                sub_prefix = tick_match.group(1) or ""
                tick_val = tick_match.group(2)
                actual_entry_msg = tick_match.group(3)
                tick_str = f"<span style='color:{QColor(COLOR_TEXT_SECONDARY).lighter(110).name()}; font-size:7pt;'>{sub_prefix}Tick {tick_val}</span> "
            else:
                actual_entry_msg = entry

            cleaned_entry = html.escape(actual_entry_msg)
            current_color = default_log_color
            style_tags = ("", "")

            if "BREAKPOINT HIT" in entry or "Simulation PAUSED" in entry:
                current_color = breakpoint_color; style_tags = ("<b><i>", "</i></b>")
            elif "Continuing simulation" in entry:
                current_color = success_color; style_tags = ("<i>", "</i>")
            elif "[Condition Blocked]" in entry or "[Eval Error]" in entry or "ERROR" in entry.upper() or "SecurityError" in entry or "[HALTED]" in entry:
                current_color = error_color; style_tags = ("<b>", "</b>")
            elif "[Safety Check Failed]" in entry or "[Action Blocked]" in entry or "Warning:" in entry:
                current_color = warning_color; style_tags = ("<b>", "</b>")
            elif "Entering state:" in entry or "Exiting state:" in entry or "Transition on" in entry or "Before transition" in entry or "After transition" in entry:
                current_color = highlight_color; style_tags = ("<b>", "</b>")
            elif "Simulation started." in entry or "Simulation stopped." in entry or "Simulation Reset" in entry:
                 current_color = success_color; style_tags = ("<b><i>", "</i></b>")
            elif "No eligible transition" in entry or "event is not allowed" in entry:
                current_color = COLOR_TEXT_SECONDARY
            
            formatted_log_line = (f"<span style='color:{time_color}; font-size:7pt;'>[{timestamp}]</span> "
                                  f"{tick_str}"
                                  f"<span style='color:{current_color};'>{style_tags[0]}{cleaned_entry}{style_tags[1]}</span>")
            self.py_sim_action_log_output.append(formatted_log_line)
        
        self.py_sim_action_log_output.verticalScrollBar().setValue(self.py_sim_action_log_output.verticalScrollBar().maximum())
        
        if log_entries and any(kw in log_entries[-1] for kw in ["Transitioned", "ERROR", "Reset", "started", "stopped", "SecurityError", "HALTED", "Entering state", "Exiting state", "After transition", "BREAKPOINT", "PAUSED", "Continuing"]):
            logger.info("PySimUI Log: %s", log_entries[-1].split('\n')[0][:100]) 

    # --- NEW Slot to handle variable edits ---
    @pyqtSlot(QTableWidgetItem)
    def on_sim_variable_changed(self, item: QTableWidgetItem):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or item.column() != 1:
            return

        row = item.row()
        name_item = self.py_sim_variables_table.item(row, 0)
        var_name = name_item.text().strip()
        new_value_str = item.text().strip()
        
        # Determine if it's a sub-machine variable
        is_sub_var = var_name.startswith("[SUB] ")
        if is_sub_var:
            var_name = var_name.replace("[SUB] ", "")

        simulator_instance = editor.py_fsm_engine
        if is_sub_var and editor.py_fsm_engine.active_sub_simulator:
            simulator_instance = editor.py_fsm_engine.active_sub_simulator

        # Safely evaluate the new value
        try:
            # First, try to evaluate as int or float
            if '.' in new_value_str:
                new_value = float(new_value_str)
            else:
                new_value = int(new_value_str)
        except ValueError:
            # If that fails, treat as string or boolean
            if new_value_str.lower() == 'true':
                new_value = True
            elif new_value_str.lower() == 'false':
                new_value = False
            else:
                # Keep as string, remove quotes if user added them
                new_value = new_value_str.strip("'\"")

        # Update the simulator's variables
        if var_name in simulator_instance._variables:
            simulator_instance._variables[var_name] = new_value
            log_msg = f"Variable '{var_name}' set to: {new_value}"
            self.append_to_action_log([log_msg])
            logger.info(f"PySim Variable Edit: {log_msg}")
        else:
            logger.warning(f"Could not find variable '{var_name}' to update in simulator.")
            # Revert the table display to the old value
            self.update_dock_ui_contents()


    @pyqtSlot()
    def on_start_py_simulation(self):
        logger.info("PySimUI: on_start_py_simulation CALLED!")
        editor = self.mw.current_editor()
        if not editor:
            QMessageBox.warning(self.mw, "No Active Diagram", "Please select a diagram tab to start the simulation.")
            return

        if editor.py_sim_active:
            logger.warning("PySimUI: Simulation already active, returning.")
            QMessageBox.information(self.mw, "Simulation Active", "Python simulation is already running.")
            return
        
        if editor.scene.is_dirty():
            logger.debug("PySimUI: Diagram is dirty, prompting user.")
            reply = QMessageBox.question(self.mw, "Unsaved Changes", 
                                         "The diagram has unsaved changes. Start simulation anyway?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.No:
                logger.info("PySimUI: User chose not to start sim due to unsaved changes.")
                return
                
        diagram_data = editor.scene.get_diagram_data()
        logger.debug(f"PySimUI: Diagram data for simulation - States: {len(diagram_data.get('states', []))}, Transitions: {len(diagram_data.get('transitions', []))}")

        if not diagram_data.get('states'):
            logger.warning("PySimUI: No states found in diagram_data for simulation.")
            QMessageBox.warning(self.mw, "Empty Diagram", "Cannot start simulation: The diagram has no states.")
            return

        try:
            logger.info("PySimUI: Attempting to instantiate FSMSimulator...")
            editor.py_fsm_engine = FSMSimulator(diagram_data['states'], diagram_data['transitions'], halt_on_action_error=True)
            logger.info("PySimUI: FSMSimulator instantiated successfully.")
            self._set_simulation_active_state(True) 
            if self.py_sim_action_log_output: self.py_sim_action_log_output.clear(); self.py_sim_action_log_output.setHtml("<i>Simulation log will appear here...</i>")
            
            initial_log = ["Python FSM Simulation started."] + editor.py_fsm_engine.get_last_executed_actions_log()
            self.append_to_action_log(initial_log)
            self.update_dock_ui_contents()
        except FSMError as e:
            logger.error(f"PySimUI: FSMError during FSMSimulator instantiation: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "FSM Initialization Error", f"Failed to start Python FSM simulation:\n{e}")
            self.append_to_action_log([f"ERROR Starting Sim: {e}"])
            editor.py_fsm_engine = None; self._set_simulation_active_state(False)
        except Exception as e: 
            logger.error(f"PySimUI: Unexpected error during FSMSimulator instantiation: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "Simulation Start Error", f"An unexpected error occurred while starting the simulation:\n{type(e).__name__}: {e}")
            self.append_to_action_log([f"UNEXPECTED ERROR Starting Sim: {e}"])
            editor.py_fsm_engine = None; self._set_simulation_active_state(False)


    @pyqtSlot(bool)
    def on_stop_py_simulation(self, silent=False):
        editor = self.mw.current_editor()
        if not editor: return
        logger.info(f"PySimUI: on_stop_py_simulation CALLED (silent={silent}). Current sim_active: {editor.py_sim_active}")
        if not editor.py_sim_active: 
            logger.info("PySimUI: Stop called but simulation not active.")
            return 
        
        self._highlight_sim_active_state(None) 
        self._highlight_sim_taken_transition(None, None, None) 

        editor.py_fsm_engine = None 
        self._set_simulation_active_state(False) 
        
        self.update_dock_ui_contents() 
        if not silent:
            self.append_to_action_log(["Python FSM Simulation stopped."])
            logger.info("PySimUI: Simulation stopped by user.")


    @pyqtSlot()
    def on_reset_py_simulation(self):
        editor = self.mw.current_editor()
        if not editor: return
        logger.info("PySimUI: on_reset_py_simulation CALLED!")
        if not editor.py_fsm_engine or not editor.py_sim_active:
            logger.warning("PySimUI: Reset called but simulation not active or engine not available.")
            QMessageBox.warning(self.mw, "Simulation Not Active", "Python simulation is not running.")
            return
        try:
            editor.py_fsm_engine.reset()
            if self.py_sim_action_log_output: 
                self.py_sim_action_log_output.append("<hr style='border-color:" + COLOR_BORDER_LIGHT +"; margin: 5px 0;'><i style='color:" + COLOR_TEXT_SECONDARY +";'>Simulation Reset</i><hr style='border-color:" + COLOR_BORDER_LIGHT +"; margin: 5px 0;'>")
            
            self._highlight_sim_taken_transition(None, None, None) 
            self.append_to_action_log(editor.py_fsm_engine.get_last_executed_actions_log())
            self.update_dock_ui_contents() # Will update tick label to 0
        except FSMError as e:
            logger.error(f"PySimUI: FSMError during reset: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "FSM Reset Error", f"Failed to reset simulation:\n{e}")
            self.append_to_action_log([f"ERROR DURING RESET: {e}"])
        except Exception as e:
            logger.error(f"PySimUI: Unexpected error during reset: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "Reset Error", f"An unexpected error occurred during reset:\n{type(e).__name__}: {e}")
            self.append_to_action_log([f"UNEXPECTED ERROR DURING RESET: {e}"])


    @pyqtSlot()
    def on_step_py_simulation(self):
        editor = self.mw.current_editor()
        if not editor: return
        logger.debug("PySimUI: on_step_py_simulation CALLED!")
        if not editor.py_fsm_engine or not editor.py_sim_active:
            QMessageBox.warning(self.mw, "Simulation Not Active", "Python simulation is not running.")
            return
        try:
            self._highlight_sim_taken_transition(None, None, None) 
            _, log_entries = editor.py_fsm_engine.step(event_name=None) 
            self.append_to_action_log(log_entries) 
            self.update_dock_ui_contents()
            if editor.py_fsm_engine.simulation_halted_flag:
                self.append_to_action_log(["[HALTED] Simulation halted due to an error. Please Reset."]); QMessageBox.warning(self.mw, "Simulation Halted", "The simulation has been halted due to an FSM action error. Please reset.")
            elif editor.py_fsm_engine.paused_on_breakpoint:
                self.append_to_action_log(["[PAUSED] Simulation paused at breakpoint."]) # Update_dock_ui_contents will handle button states
        except FSMError as e: 
            QMessageBox.warning(self.mw, "Simulation Step Error", str(e))
            self.append_to_action_log([f"ERROR DURING STEP: {e}"]); logger.error("PySimUI: Step FSMError: %s", e, exc_info=True)
            if editor.py_fsm_engine and editor.py_fsm_engine.simulation_halted_flag: self.append_to_action_log(["[HALTED] Simulation halted. Please Reset."])
        except Exception as e:
            QMessageBox.critical(self.mw, "Simulation Step Error", f"An unexpected error occurred during step:\n{type(e).__name__}: {e}")
            self.append_to_action_log([f"UNEXPECTED ERROR DURING STEP: {e}"]); logger.error("PySimUI: Unexpected Step Error:", exc_info=True)

    @pyqtSlot()
    def on_trigger_py_event(self):
        editor = self.mw.current_editor()
        if not editor: return
        logger.debug("PySimUI: on_trigger_py_event CALLED!")
        if not editor.py_fsm_engine or not editor.py_sim_active:
            QMessageBox.warning(self.mw, "Simulation Not Active", "Python simulation is not running.")
            return
        
        event_name_combo = self.py_sim_event_combo.currentText() if self.py_sim_event_combo else ""
        event_name_edit = self.py_sim_event_name_edit.text().strip() if self.py_sim_event_name_edit else ""
        
        event_to_trigger = event_name_edit if event_name_edit else (event_name_combo if event_name_combo != "None (Internal Step)" else None)
        logger.debug(f"PySimUI: Event to trigger: '{event_to_trigger}' (from edit: '{event_name_edit}', from combo: '{event_name_combo}')")

        if not event_to_trigger:
            self.append_to_action_log(["Info: No specific event provided to trigger. Use 'Step (Internal/Tick)' for internal tick."])
            return
        
        self._highlight_sim_taken_transition(None, None, None) 
        self.append_to_action_log([f"--- Triggering event: '{html.escape(event_to_trigger)}' ---"])
        try:
            _, log_entries = editor.py_fsm_engine.step(event_name=event_to_trigger)
            self.append_to_action_log(log_entries)
            self.update_dock_ui_contents()
            if self.py_sim_event_name_edit: self.py_sim_event_name_edit.clear()
            
            if editor.py_fsm_engine.simulation_halted_flag:
                self.append_to_action_log(["[HALTED] Simulation halted due to an error. Please Reset."]); QMessageBox.warning(self.mw, "Simulation Halted", "The simulation has been halted due to an FSM action error. Please reset.")
            elif editor.py_fsm_engine.paused_on_breakpoint:
                 self.append_to_action_log(["[PAUSED] Simulation paused at breakpoint."])
        except FSMError as e:
            QMessageBox.warning(self.mw, "Simulation Event Error", str(e))
            self.append_to_action_log([f"ERROR EVENT '{html.escape(event_to_trigger)}': {e}"]); logger.error("PySimUI: Event FSMError for '%s': %s", event_to_trigger, e, exc_info=True)
            if editor.py_fsm_engine and editor.py_fsm_engine.simulation_halted_flag: self.append_to_action_log(["[HALTED] Simulation halted. Please Reset."])
        except Exception as e:
            QMessageBox.critical(self.mw, "Simulation Event Error", f"An unexpected error occurred on event '{html.escape(event_to_trigger)}':\n{type(e).__name__}: {e}")
            self.append_to_action_log([f"UNEXPECTED ERROR EVENT '{html.escape(event_to_trigger)}': {e}"]); logger.error("PySimUI: Unexpected Event Error for '%s':", event_to_trigger, exc_info=True)

    # --- NEW: Slot for Continue Button ---
    @pyqtSlot()
    def on_continue_py_simulation(self):
        editor = self.mw.current_editor()
        if not editor: return
        logger.debug("PySimUI: on_continue_py_simulation CALLED!")
        if editor.py_fsm_engine and editor.py_fsm_engine.paused_on_breakpoint:
            resumed = editor.py_fsm_engine.continue_simulation()
            if resumed:
                self.append_to_action_log(["Simulation Continued from breakpoint."])
                # After continuing, we might want to immediately process the "during" action of the current state
                # or simply update the UI and wait for the next user action (Step or Trigger Event).
                # Let's call step(None) to process during actions and advance one tick if not event-driven.
                # This provides immediate feedback for the state we paused in.
                self.on_step_py_simulation() 
            self.update_dock_ui_contents() # This will re-evaluate button states
        else:
            self.append_to_action_log(["Info: Continue clicked, but simulation not paused at a breakpoint."])
            logger.warning("PySimUI: Continue clicked, but not paused at breakpoint or engine not available.")