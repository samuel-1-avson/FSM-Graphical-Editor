# fsm_designer_project/ui/simulation/ui_py_simulation_manager.py
import html
import re
import os
from PyQt5.QtWidgets import (
    QLabel, QTextEdit, QComboBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QAction, QMessageBox, QGroupBox, QHBoxLayout, QVBoxLayout,
    QToolButton, QHeaderView, QAbstractItemView, QWidget, QStyle, QSlider,
    QGraphicsItem, QFrame, QSplitter, QScrollArea, QGridLayout, QSizePolicy,
    QSpacerItem, QTabWidget, QProgressBar, QMainWindow, QDoubleSpinBox, QFormLayout,
    QSpinBox
)
from PyQt5.QtGui import QIcon, QColor, QPalette, QFont, QPainter, QLinearGradient
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QSize, Qt, QTime, QTimer, QPropertyAnimation, QEasingCurve

from ...core.fsm_simulator import FSMSimulator, FSMError
from ..graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem, GraphicsDisplayItem
from ...utils import get_standard_icon
from ...utils.config import APP_FONT_SIZE_SMALL, COLOR_ACCENT_WARNING, COLOR_ACCENT_PRIMARY, COLOR_TEXT_PRIMARY
from ..animation_manager import AnimationManager
from ..widgets.virtual_hardware_widgets import VirtualLedWidget, VirtualSliderWidget, VirtualGaugeWidget
from ...managers.matlab_simulation_manager import MatlabSimulationManager, SimulationState, SimulationData
from ...managers.action_handlers import ActionHandler
from ...core.simulation_logger import SimulationDataLogger
from .plot_widget import SimulationPlotWidget
from ...utils import config

import logging
logger = logging.getLogger(__name__)

# --- STYLED WIDGETS (NOW THEME-AWARE) ---
class ModernGroupBox(QGroupBox):
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        # Styling is now handled by the main application stylesheet for consistency

class StatusIndicator(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(32)
        # Styling is now handled by the main application stylesheet

class ModernButton(QPushButton):
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, parent)
        if icon:
            self.setIcon(icon)
        # Styling is now handled by the main application stylesheet

class ModernSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        # Styling is now handled by the main application stylesheet
# --- END STYLED WIDGETS ---

class PySimulationUIManager(QObject):
    simulationStateChanged = pyqtSignal(bool)
    requestGlobalUIEnable = pyqtSignal(bool)

    def __init__(self, action_handler: ActionHandler, animation_manager: AnimationManager, matlab_sim_manager: MatlabSimulationManager, parent: QMainWindow = None):
        super().__init__(parent)
        self.action_handler = action_handler
        self.animation_manager = animation_manager
        self.matlab_sim_manager = matlab_sim_manager
        
        self.data_logger = SimulationDataLogger(self)
        
        self.matlab_sim_manager.simulation_state_changed.connect(self._on_matlab_sim_state_changed)
        self.matlab_sim_manager.simulation_data_updated.connect(self.on_matlab_state_update)
        self.matlab_sim_manager.error_occurred.connect(self.on_matlab_sim_error)

        self.real_time_timer = QTimer(self)
        self.real_time_timer.timeout.connect(lambda: self.on_step_py_simulation(internal=True))
        self.py_sim_run_pause_btn: ModernButton = None
        self.py_sim_speed_slider: ModernSlider = None
        self.py_sim_speed_label: QLabel = None
        
        self.py_sim_start_btn: QToolButton = None
        self.py_sim_stop_btn: QToolButton = None
        self.py_sim_reset_btn: QToolButton = None
        self.py_sim_step_btn: ModernButton = None
        self.py_sim_continue_btn: ModernButton = None
        self.py_sim_event_combo: QComboBox = None
        self.py_sim_trigger_event_btn: ModernButton = None
        self.py_sim_current_state_label: StatusIndicator = None
        self.py_sim_current_tick_label: QLabel = None
        self.py_sim_variables_table: QTableWidget = None
        self.py_sim_action_log_output: QTextEdit = None
        self._py_sim_currently_highlighted_item: GraphicsStateItem | None = None
        self._py_sim_currently_highlighted_transition: GraphicsTransitionItem | None = None
        
        main_window = self.parent()
        if main_window and hasattr(main_window, 'hardware_sim_ui_manager') and main_window.hardware_sim_ui_manager:
            main_window.hardware_sim_ui_manager.hardware_link_manager.hardwareLinkLost.connect(self.on_hardware_link_lost)

        self.requestGlobalUIEnable.connect(self._set_global_ui_enabled_state)

    @pyqtSlot(SimulationState, str)
    def _on_matlab_sim_state_changed(self, state, message):
        if state == SimulationState.RUNNING:
            self.on_matlab_sim_started()
        elif state in [SimulationState.COMPLETED, SimulationState.ERROR, SimulationState.IDLE]:
            self.on_matlab_sim_stopped(message)

    @pyqtSlot(bool)
    def _set_global_ui_enabled_state(self, enable: bool):
        main_window = self.parent()
        if not main_window: return

        logger.debug(f"PySimUI: Setting global UI enabled state to: {enable}")
        
        self.action_handler.set_editing_actions_enabled(enable)

        if hasattr(main_window, 'elements_palette_dock'):
            main_window.elements_palette_dock.setEnabled(enable)
        
        if hasattr(main_window, 'properties_edit_dialog_button'):
            is_item_selected = False
            editor = main_window.current_editor()
            if editor and editor.scene.selectedItems():
                is_item_selected = True
            main_window.properties_edit_dialog_button.setEnabled(enable and is_item_selected)

        editor = main_window.current_editor()
        if editor:
            for item in editor.scene.items():
                if isinstance(item, (GraphicsStateItem, GraphicsCommentItem)):
                    item.setFlag(QGraphicsItem.ItemIsMovable, enable and editor.scene.current_mode == "select")
            
            if not enable and editor.scene.current_mode != "select":
                editor.scene.set_mode("select")
        
        main_window._update_matlab_actions_enabled_state()

    def create_dock_widget_contents(self) -> QWidget:
        main_window = self.parent()
        main_container = QWidget()
        
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)
        
        # --- NEW: Scroll Area for the top controls ---
        top_scroll_area = QScrollArea()
        top_scroll_area.setWidgetResizable(True)
        top_scroll_area.setFrameShape(QFrame.NoFrame)
        top_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        top_widget = QWidget()
        top_scroll_area.setWidget(top_widget)
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(8, 8, 8, 4)
        top_layout.setSpacing(10)

        controls_group = ModernGroupBox("Simulation Control")
        controls_layout = QGridLayout(controls_group)
        controls_layout.setSpacing(8)
        
        self.py_sim_start_btn = QToolButton()
        if hasattr(main_window, 'start_py_sim_action'):
            self.py_sim_start_btn.setDefaultAction(main_window.start_py_sim_action)
        self.py_sim_start_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        main_window.start_py_sim_action.setText("Initialize")
        main_window.start_py_sim_action.setToolTip("Initialize the Python simulator engine with the current diagram")

        self.py_sim_stop_btn = QToolButton()
        if hasattr(main_window, 'stop_py_sim_action'):
            self.py_sim_stop_btn.setDefaultAction(main_window.stop_py_sim_action)
        self.py_sim_stop_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.py_sim_reset_btn = QToolButton()
        if hasattr(main_window, 'reset_py_sim_action'):
            self.py_sim_reset_btn.setDefaultAction(main_window.reset_py_sim_action)
        self.py_sim_reset_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        self.matlab_sim_start_stop_btn = ModernButton("Run Live Simulink", get_standard_icon(QStyle.SP_ComputerIcon, "Simulink"))
        self.matlab_sim_start_stop_btn.setCheckable(True)
        self.matlab_sim_start_stop_btn.setToolTip("Run the exported Simulink model with live feedback on the canvas")
        self.matlab_sim_start_stop_btn.clicked.connect(self.on_toggle_matlab_simulation)

        controls_layout.addWidget(self.py_sim_start_btn, 0, 0)
        controls_layout.addWidget(self.py_sim_stop_btn, 0, 1)
        controls_layout.addWidget(self.py_sim_reset_btn, 0, 2)
        controls_layout.addWidget(self.matlab_sim_start_stop_btn, 1, 0, 1, 3)
        
        top_layout.addWidget(controls_group)

        params_group = ModernGroupBox("Simulation Parameters")
        params_layout = QFormLayout(params_group)
        
        self.py_sim_stop_tick_spin = QSpinBox()
        self.py_sim_stop_tick_spin.setRange(1, 1000000)
        self.py_sim_stop_tick_spin.setValue(1000)
        self.py_sim_stop_tick_spin.setSuffix(" ticks")
        self.py_sim_stop_tick_spin.setToolTip("Automatically stop the real-time simulation after this many ticks")
        params_layout.addRow("Max Ticks:", self.py_sim_stop_tick_spin)

        self.py_sim_tick_duration_spin = QDoubleSpinBox()
        self.py_sim_tick_duration_spin.setRange(0.01, 10.0)
        self.py_sim_tick_duration_spin.setValue(1.0)
        self.py_sim_tick_duration_spin.setSingleStep(0.1)
        self.py_sim_tick_duration_spin.setSuffix(" s")
        self.py_sim_tick_duration_spin.setToolTip("Conceptual duration of one tick, for displaying total simulation time")
        self.py_sim_tick_duration_spin.valueChanged.connect(self.update_dock_ui_contents)
        params_layout.addRow("Tick Time (s):", self.py_sim_tick_duration_spin)

        top_layout.addWidget(params_group)

        execution_group = ModernGroupBox("Execution Control")
        execution_layout = QVBoxLayout(execution_group)
        
        exec_row1 = QHBoxLayout()
        self.py_sim_run_pause_btn = ModernButton("Run", get_standard_icon(QStyle.SP_MediaPlay, "Run"))
        self.py_sim_run_pause_btn.clicked.connect(self.on_toggle_real_time_simulation)
        exec_row1.addWidget(self.py_sim_run_pause_btn)
        
        self.py_sim_step_btn = ModernButton("Step", get_standard_icon(QStyle.SP_MediaSeekForward, "Step"))
        self.py_sim_step_btn.clicked.connect(lambda: self.on_step_py_simulation(internal=False))
        exec_row1.addWidget(self.py_sim_step_btn)

        self.py_sim_continue_btn = ModernButton("Continue", get_standard_icon(QStyle.SP_MediaSkipForward, "Cont"))
        self.py_sim_continue_btn.setToolTip("Continue execution from breakpoint")
        self.py_sim_continue_btn.clicked.connect(self.on_continue_py_simulation)
        exec_row1.addWidget(self.py_sim_continue_btn)
        execution_layout.addLayout(exec_row1)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        
        self.py_sim_speed_slider = ModernSlider(Qt.Horizontal)
        self.py_sim_speed_slider.setRange(100, 2000)
        self.py_sim_speed_slider.setValue(1000)
        self.py_sim_speed_slider.setInvertedAppearance(True)
        self.py_sim_speed_slider.valueChanged.connect(self.on_speed_slider_changed)
        speed_layout.addWidget(self.py_sim_speed_slider, 1)
        
        self.py_sim_speed_label = QLabel("1000 ms/step")
        self.py_sim_speed_label.setMinimumWidth(80)
        speed_layout.addWidget(self.py_sim_speed_label)
        execution_layout.addLayout(speed_layout)
        top_layout.addWidget(execution_group)

        status_group = ModernGroupBox("Current Status")
        status_layout = QVBoxLayout(status_group)
        
        self.py_sim_current_state_label = StatusIndicator()
        self.py_sim_current_state_label.setText("Not Initialized")
        status_layout.addWidget(self.py_sim_current_state_label)
        
        self.py_sim_current_tick_label = QLabel("Tick: 0")
        status_layout.addWidget(self.py_sim_current_tick_label)
        
        top_layout.addWidget(status_group)

        event_group = ModernGroupBox("Manual Event Trigger")
        event_layout = QHBoxLayout(event_group)
        
        self.py_sim_event_combo = QComboBox()
        self.py_sim_event_combo.setEditable(True)
        self.py_sim_event_combo.lineEdit().setPlaceholderText("Select or enter event")
        event_layout.addWidget(self.py_sim_event_combo)
        
        self.py_sim_trigger_event_btn = ModernButton("Trigger", get_standard_icon(QStyle.SP_ArrowRight, "Trg"))
        self.py_sim_trigger_event_btn.clicked.connect(self._on_trigger_button_clicked)
        event_layout.addWidget(self.py_sim_trigger_event_btn)
        
        top_layout.addWidget(event_group)
        top_layout.addStretch()

        main_splitter.addWidget(top_scroll_area) # Add scroll area to splitter

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        data_tabs = QTabWidget()
        
        variables_widget = QWidget()
        variables_layout = QVBoxLayout(variables_widget)
        
        self.py_sim_variables_table = QTableWidget()
        self.py_sim_variables_table.setColumnCount(2)
        self.py_sim_variables_table.setHorizontalHeaderLabels(["Variable", "Value"])
        self.py_sim_variables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.py_sim_variables_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.py_sim_variables_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed)
        self.py_sim_variables_table.itemChanged.connect(self.on_sim_variable_changed)
        self.py_sim_variables_table.setAlternatingRowColors(True)
        variables_layout.addWidget(self.py_sim_variables_table)
        data_tabs.addTab(variables_widget, "Variables")

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        self.py_sim_action_log_output = QTextEdit()
        self.py_sim_action_log_output.setReadOnly(True)
        self.py_sim_action_log_output.setObjectName("PySimActionLog")
        log_layout.addWidget(self.py_sim_action_log_output)
        data_tabs.addTab(log_widget, "Action Log")

        self.plot_widget = SimulationPlotWidget(self.data_logger)
        data_tabs.addTab(self.plot_widget, "Scope")

        bottom_layout.addWidget(data_tabs)
        main_splitter.addWidget(bottom_widget)

        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_splitter)
        
        self._update_internal_controls_enabled_state()
        return main_container

    def _update_canvas_displays(self):
        editor = self.parent().current_editor() if self.parent() else None
        if not editor or not editor.scene:
            return
            
        is_sim_active = editor.py_fsm_engine is not None and editor.py_sim_active
        
        if not is_sim_active:
            for item in editor.scene.items():
                if isinstance(item, GraphicsDisplayItem):
                    item.setPlainText(f"{item.variable_name}\n(sim inactive)")
            return

        sim_vars = editor.py_fsm_engine.get_variables()
        for item in editor.scene.items():
            if isinstance(item, GraphicsDisplayItem):
                value = sim_vars.get(item.variable_name, "N/A")
                item.update_value(value)

    @pyqtSlot(bool)
    def on_toggle_matlab_simulation(self, checked):
        main_window = self.parent()
        if checked:
            if not main_window.last_generated_model_path or not os.path.exists(main_window.last_generated_model_path):
                QMessageBox.warning(main_window, "No Simulink Model", "Please export the diagram to a Simulink model first using the 'Code Export' tab.")
                self.matlab_sim_start_stop_btn.setChecked(False)
                return

            editor = main_window.current_editor()
            if editor and editor.py_sim_active:
                QMessageBox.warning(main_window, "Simulation Active", "Please stop the internal Python simulation before starting the Simulink simulation.")
                self.matlab_sim_start_stop_btn.setChecked(False)
                return
            
            self.matlab_sim_manager.start_simulation()
            self.matlab_sim_start_stop_btn.setText("Connecting...")
            self.matlab_sim_start_stop_btn.setEnabled(False)
        else:
            self.matlab_sim_manager.stop_simulation()
            self.matlab_sim_start_stop_btn.setText("Stopping...")
            self.matlab_sim_start_stop_btn.setEnabled(False)

    @pyqtSlot()
    def on_matlab_sim_started(self):
        self.append_to_action_log(["Simulink live simulation started"])
        self.matlab_sim_start_stop_btn.setText("Stop Live Simulink")
        self.matlab_sim_start_stop_btn.setEnabled(True)
        self.requestGlobalUIEnable.emit(False)

    @pyqtSlot(str)
    def on_matlab_sim_stopped(self, reason):
        self.append_to_action_log([f"Simulink live simulation stopped: {reason}"])
        self.matlab_sim_start_stop_btn.setChecked(False)
        self.matlab_sim_start_stop_btn.setText("Run Live Simulink")
        self.matlab_sim_start_stop_btn.setEnabled(True)
        self._highlight_sim_active_state(None)
        self.requestGlobalUIEnable.emit(True)

    @pyqtSlot(str)
    def on_matlab_sim_error(self, error_message):
        main_window = self.parent()
        self.append_to_action_log([f"Simulink Error: {error_message}"])
        self.on_matlab_sim_stopped("Error")
        QMessageBox.critical(main_window, "Simulink Simulation Error", error_message)

    @pyqtSlot(SimulationData)
    def on_matlab_state_update(self, data):
        state_name = data.active_state
        tick = data.tick
        self.py_sim_current_state_label.setText(state_name)
        self.py_sim_current_tick_label.setText(f"Tick: {tick}")
        self._highlight_sim_active_state(state_name)
        
        # Check if the scene is set before animating
        if self.animation_manager and self.animation_manager.graphics_scene:
            self.animation_manager.animate_state_entry(state_name)

    @pyqtSlot(int)
    def on_speed_slider_changed(self, value):
        if self.py_sim_speed_label:
            self.py_sim_speed_label.setText(f"{value} ms/step")
        if self.real_time_timer.isActive():
            self.real_time_timer.setInterval(value)

    @pyqtSlot()
    def on_toggle_real_time_simulation(self):
        editor = self.parent().current_editor()
        if not editor or not editor.py_sim_active:
            return

        if self.real_time_timer.isActive():
            self.real_time_timer.stop()
            self.append_to_action_log(["Real-time simulation paused"])
        else:
            interval = self.py_sim_speed_slider.value()
            self.real_time_timer.setInterval(interval)
            self.real_time_timer.start()
            self.append_to_action_log([f"Real-time simulation started ({interval} ms/step)"])
        self._update_internal_controls_enabled_state()

    def _update_internal_controls_enabled_state(self):
        editor = self.parent().current_editor() if self.parent() else None
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
            self.py_sim_run_pause_btn.setText("Pause")
            self.py_sim_run_pause_btn.setIcon(get_standard_icon(QStyle.SP_MediaPause, "Pause"))
        else:
            self.py_sim_run_pause_btn.setText("Run")
            self.py_sim_run_pause_btn.setIcon(get_standard_icon(QStyle.SP_MediaPlay, "Run"))
            
        manual_controls_enabled = sim_active and not is_running_real_time and not is_paused_at_bp
        self.py_sim_step_btn.setEnabled(manual_controls_enabled)
        self.py_sim_event_combo.setEnabled(manual_controls_enabled)
        self.py_sim_trigger_event_btn.setEnabled(manual_controls_enabled)
        
        self.py_sim_continue_btn.setEnabled(sim_active and is_paused_at_bp)

    def _set_simulation_active_state(self, is_running: bool):
        if not is_running:
            self.real_time_timer.stop()
        
        editor = self.parent().current_editor() if self.parent() else None
        if editor:
            editor.py_sim_active = is_running
        self.simulationStateChanged.emit(is_running)
        self.requestGlobalUIEnable.emit(not is_running)
        self._update_internal_controls_enabled_state()

    def _highlight_sim_active_state(self, state_name_to_highlight: str | None):
        editor = self.parent().current_editor() if self.parent() else None
        if not editor:
            return
            
        if self._py_sim_currently_highlighted_item:
            self._py_sim_currently_highlighted_item.set_py_sim_active_style(False)
            self._py_sim_currently_highlighted_item = None

        if state_name_to_highlight and editor.py_fsm_engine:
            leaf_state = editor.py_fsm_engine.get_current_leaf_state_name()
            for item in editor.scene.items():
                if isinstance(item, GraphicsStateItem) and item.text_label == leaf_state:
                    item.set_py_sim_active_style(True)
                    self._py_sim_currently_highlighted_item = item
                    if editor.view:
                        editor.view.ensureVisible(item, 50, 50)
                    break
        
        editor.scene.update()

    def update_dock_ui_contents(self):
        main_window = self.parent()
        editor = main_window.current_editor() if main_window else None
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active:
            if self.py_sim_current_state_label:
                self.py_sim_current_state_label.setText("Not Initialized")
            
            if self.py_sim_current_tick_label:
                self.py_sim_current_tick_label.setText("Tick: 0")
            if self.py_sim_variables_table:
                self.py_sim_variables_table.setRowCount(0)
            
            self._highlight_sim_active_state(None)
            
            if self.py_sim_event_combo:
                self.py_sim_event_combo.clear()
                self.py_sim_event_combo.addItem("None (Internal Step)")
            
            if hasattr(main_window, 'hardware_sim_ui_manager'):
                hw_mgr = main_window.hardware_sim_ui_manager
                for led in hw_mgr.virtual_leds.values():
                    led.setState(False)
                for gauge in hw_mgr.virtual_gauges.values():
                    gauge.setValue(0)
                if hw_mgr.hardware_link_manager.is_connected:
                    for i in range(4):
                        hw_mgr.hardware_link_manager.send_command(f"CMD:LED{i}:0")
                    for i in range(2):
                        hw_mgr.hardware_link_manager.send_command(f"CMD:Slider{i}:0")
                    for i in range(2):
                        hw_mgr.hardware_link_manager.send_command(f"CMD:Gauge{i}:0")

            self._update_internal_controls_enabled_state()
            self._update_canvas_displays()
            return
        
        hierarchical_state_name = editor.py_fsm_engine.get_current_state_name()
        display_state_name = (hierarchical_state_name[:30] + '...') if len(hierarchical_state_name) > 33 else hierarchical_state_name
        
        paused_suffix = f" <span style='color:{config.COLOR_ACCENT_WARNING}; font-weight:bold;'>(Paused)</span>" if editor.py_fsm_engine.paused_on_breakpoint else ""
        
        status_text = f"<span style='font-weight:600; font-size:10pt;'>{html.escape(display_state_name)}</span>{paused_suffix}"
        self.py_sim_current_state_label.setText(status_text)

        tick_count = editor.py_fsm_engine.current_tick
        tick_duration_s = self.py_sim_tick_duration_spin.value()
        sim_time_s = tick_count * tick_duration_s
        self.py_sim_current_tick_label.setText(f"Tick: {tick_count:,}  (Time: {sim_time_s:.2f} s)")

        self._highlight_sim_active_state(hierarchical_state_name)
        
        all_vars = sorted(editor.py_fsm_engine.get_variables().items())
        
        self.py_sim_variables_table.blockSignals(True)
        self.py_sim_variables_table.setRowCount(len(all_vars))
        
        for r, (name, val) in enumerate(all_vars):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.py_sim_variables_table.setItem(r, 0, name_item)
            
            val_item = QTableWidgetItem(str(val))
            self.py_sim_variables_table.setItem(r, 1, val_item)
        
        self.py_sim_variables_table.blockSignals(False)

        current_event_text = self.py_sim_event_combo.currentText()
        possible_events = sorted(list(filter(None, editor.py_fsm_engine.get_possible_events_from_current_state())))
        
        self.py_sim_event_combo.clear()
        self.py_sim_event_combo.addItems(["None (Internal Step)"] + possible_events)
        
        idx = self.py_sim_event_combo.findText(current_event_text)
        if idx != -1:
            self.py_sim_event_combo.setCurrentIndex(idx)

        if hasattr(main_window, 'hardware_sim_ui_manager'):
            hw_mgr = main_window.hardware_sim_ui_manager
            output_mappings = {
                d.get('hw_output_variable'): d.get('hw_component_map')
                for item in editor.scene.items()
                if isinstance(item, GraphicsStateItem)
                and (d := item.get_data())
                and d.get('hw_output_variable')
                and d.get('hw_component_map') != "None"
            }
            
            sim_variables = editor.py_fsm_engine.get_variables()
            all_components = {**hw_mgr.virtual_leds, **hw_mgr.virtual_sliders, **hw_mgr.virtual_gauges}
            
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
                
                elif isinstance(comp_widget, VirtualGaugeWidget):
                    gauge_val = 0
                    try:
                        gauge_val = int(new_value)
                    except (ValueError, TypeError):
                        pass
                    
                    comp_widget.setValue(gauge_val)
                    if hw_mgr.hardware_link_manager.is_connected:
                        hw_mgr.hardware_link_manager.send_command(f"CMD:{comp_key}:{gauge_val}")

                elif isinstance(comp_widget, VirtualSliderWidget):
                    slider_val = int(new_value) if new_value is not None else 0
                    comp_widget.blockSignals(True)
                    comp_widget.setValue(slider_val)
                    comp_widget.blockSignals(False)
        
        all_vars_dict = editor.py_fsm_engine.get_variables()
        self.plot_widget.update_variable_list(all_vars_dict)
        self._update_canvas_displays()

        self._update_internal_controls_enabled_state()

    def append_to_action_log(self, log_entries: list[str]):
        if not self.py_sim_action_log_output:
            return
            
        for entry in log_entries:
            timestamp = QTime.currentTime().toString('hh:mm:ss.zzz')
            tick_str = ""
            
            tick_match = re.match(r"(\[SUB\] )*\[Tick (\d+)\] (.*)", entry)
            actual_entry_msg = tick_match.group(3) if tick_match else entry
            
            if tick_match:
                tick_num = int(tick_match.group(2))
                sub_prefix = tick_match.group(1) or ''
                tick_str = f"<span style='color:{config.COLOR_TEXT_SECONDARY}; font-size:8pt;'>[{sub_prefix}Tick {tick_num:,}]</span> "
            
            cleaned_entry = html.escape(actual_entry_msg)
            log_html = f"""
            <div style='margin:1px 0; padding:2px 4px;'>
                <span style='color:{config.COLOR_TEXT_SECONDARY}; font-size:8pt; font-family:monospace;'>[{timestamp}]</span>
                {tick_str}
                <span style='color:{config.COLOR_TEXT_PRIMARY};'>{cleaned_entry}</span>
            </div>
            """
            if "ERROR" in entry.upper():
                log_html = log_html.replace(f"color:{config.COLOR_TEXT_PRIMARY};", f"color:{config.COLOR_ACCENT_ERROR}; font-weight:bold;")
            
            self.py_sim_action_log_output.append(log_html)
        
        self.py_sim_action_log_output.verticalScrollBar().setValue(
            self.py_sim_action_log_output.verticalScrollBar().maximum()
        )

    @pyqtSlot(QTableWidgetItem)
    def on_sim_variable_changed(self, item: QTableWidgetItem):
        editor = self.parent().current_editor() if self.parent() else None
        if not editor or not editor.py_fsm_engine or item.column() != 1:
            return
            
        row = item.row()
        var_name_item = self.py_sim_variables_table.item(row, 0)
        if not var_name_item:
            return
            
        var_name = var_name_item.text().strip()
        new_value_str = item.text().strip()
        simulator_instance = editor.py_fsm_engine
        
        try:
            if new_value_str.lower() in ('true', 'false'):
                new_value = new_value_str.lower() == 'true'
            elif '.' in new_value_str:
                new_value = float(new_value_str)
            else:
                try:
                    new_value = int(new_value_str)
                except ValueError:
                    new_value = new_value_str.strip("'\"")
        except ValueError:
            new_value = new_value_str.strip("'\"")
        
        if var_name in simulator_instance._variables:
            old_value = simulator_instance._variables[var_name]
            simulator_instance._variables[var_name] = new_value
            self.append_to_action_log([f"Variable '{var_name}' changed: {old_value} → {new_value}"])
        else:
            self.update_dock_ui_contents()

    @pyqtSlot()
    def on_start_py_simulation(self):
        main_window = self.parent()
        editor = main_window.current_editor() if main_window else None
        if not editor:
            QMessageBox.warning(main_window, "No Active Diagram", "Please select a diagram tab to initialize.")
            return
            
        if editor.py_sim_active:
            QMessageBox.information(self.parent(), "Simulation Already Active", "Python simulation is already initialized for this tab.")
            return
            
        if editor.scene.is_dirty():
            reply = QMessageBox.question(
                main_window,
                "Unsaved Changes",
                "The diagram has unsaved changes. Initialize simulation anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.No:
                return
        
        diagram_data = editor.scene.get_diagram_data()
        if not diagram_data.get('states'):
            QMessageBox.warning(main_window, "Empty Diagram", "Cannot initialize simulation: The diagram has no states.")
            return
        
        try:
            if self.animation_manager:
                self.animation_manager.graphics_scene = editor.scene
                state_items_map = {
                    item.text_label: item
                    for item in editor.scene.items()
                    if isinstance(item, GraphicsStateItem)
                }
                transition_items_map = {
                    (t.start_item.text_label, t.end_item.text_label, t.event_str): t
                    for t in editor.scene.items()
                    if isinstance(t, GraphicsTransitionItem) and t.start_item and t.end_item
                }
                self.animation_manager.register_graphics_items(state_items_map, transition_items_map)
                logger.info("Registered scene items with AnimationManager for simulation.")

            editor.py_fsm_engine = FSMSimulator(
                diagram_data['states'],
                diagram_data['transitions'],
                halt_on_action_error=True
            )
            
            stop_tick_value = self.py_sim_stop_tick_spin.value()
            editor.py_fsm_engine.set_stop_tick(stop_tick_value)
            editor.py_fsm_engine.tick_processed.connect(self.data_logger.on_tick_processed)
            editor.py_fsm_engine.tick_processed.connect(self.plot_widget.update_plot_data)
            self.data_logger.start_logging()

            self._set_simulation_active_state(True)
            
            if self.py_sim_action_log_output:
                self.py_sim_action_log_output.clear()
                
            initial_log = ["Python FSM Simulation initialized successfully"] + editor.py_fsm_engine.get_last_executed_actions_log()
            self.append_to_action_log(initial_log)
            self.update_dock_ui_contents()
            
        except (FSMError, Exception) as e:
            QMessageBox.critical(main_window, "FSM Initialization Error", f"Failed to initialize Python FSM simulation:\n{e}")
            self.append_to_action_log([f"ERROR Initializing Simulation: {e}"])
            editor.py_fsm_engine = None
            self._set_simulation_active_state(False)

    @pyqtSlot(bool)
    def on_stop_py_simulation(self, silent=False):
        editor = self.parent().current_editor() if self.parent() else None
        if not editor or not editor.py_sim_active:
            return

        self.data_logger.stop_logging()
            
        self.real_time_timer.stop()
        self._highlight_sim_active_state(None)
        
        editor.py_fsm_engine = None
        self._set_simulation_active_state(False)
        self.update_dock_ui_contents()
        
        if not silent:
            self.append_to_action_log(["Python FSM Simulation stopped"])
        if self.animation_manager:
            self.animation_manager.clear_animations()
            self.animation_manager.graphics_scene = None

    @pyqtSlot()
    def _on_trigger_button_clicked(self):
        self.on_trigger_py_event()

    @pyqtSlot()
    def on_reset_py_simulation(self):
        editor = self.parent().current_editor() if self.parent() else None
        if not editor or not editor.py_fsm_engine:
            return
            
        self.data_logger.start_logging()
        self.plot_widget.clear_all_plots()

        self.real_time_timer.stop()
        if self.animation_manager:
            self.animation_manager.clear_animations()
            
        try:
            editor.py_fsm_engine.reset()
            if self.py_sim_action_log_output:
                self.py_sim_action_log_output.append(
                    "<div style='text-align:center; padding:8px; background:#F5F5F5; margin:4px 0; border-radius:4px;'>"
                    "<i style='color:#666666; font-size:9pt;'>=== Simulation Reset ===</i>"
                    "</div>"
                )
            self.append_to_action_log(editor.py_fsm_engine.get_last_executed_actions_log())
            self.update_dock_ui_contents()
        except (FSMError, Exception) as e:
            QMessageBox.critical(self.parent(), "FSM Reset Error", f"Failed to reset simulation:\n{e}")

    @pyqtSlot(bool)
    def on_step_py_simulation(self, internal=False):
        main_window = self.parent()
        editor = main_window.current_editor() if main_window else None
        if not editor or not editor.py_fsm_engine:
            if not internal:
                QMessageBox.warning(main_window, "Not Initialized", "Please initialize the simulation first.")
            return
            
        try:
            _, log_entries = editor.py_fsm_engine.step(event_name=None)
            self.append_to_action_log(log_entries)
            self.update_dock_ui_contents()
            
            if editor.py_fsm_engine.simulation_halted_flag or editor.py_fsm_engine.paused_on_breakpoint:
                self.real_time_timer.stop()
                if not internal:
                    msg = "Simulation has paused due to a breakpoint" if editor.py_fsm_engine.paused_on_breakpoint else "Simulation has halted"
                    QMessageBox.information(main_window, "Simulation Paused/Halted", msg)
        except (FSMError, Exception) as e:
            self.real_time_timer.stop()
            QMessageBox.critical(main_window, "Step Error", f"An error occurred: {e}")
        
        self._update_internal_controls_enabled_state()
        
    @pyqtSlot(str)
    def on_trigger_py_event(self, external_event_name: str = None):
        main_window = self.parent()
        editor = main_window.current_editor() if main_window else None
        if not editor or not editor.py_fsm_engine:
            return
            
        event_to_trigger = external_event_name or self.py_sim_event_combo.currentText().strip()
        
        if not event_to_trigger or event_to_trigger == "None (Internal Step)":
            self.on_step_py_simulation()
            return
        
        self.append_to_action_log([f"Triggering event: '{html.escape(event_to_trigger)}'"])
        
        try:
            _, log_entries = editor.py_fsm_engine.step(event_name=event_to_trigger)
            self.append_to_action_log(log_entries)
            self.update_dock_ui_contents()
            self.py_sim_event_combo.setCurrentText("")
        except (FSMError, Exception) as e:
            QMessageBox.critical(main_window, "Event Error", f"An error occurred: {e}")

    @pyqtSlot()
    def on_continue_py_simulation(self):
        editor = self.parent().current_editor() if self.parent() else None
        if not editor or not (editor.py_fsm_engine and editor.py_fsm_engine.paused_on_breakpoint):
            return
            
        if editor.py_fsm_engine.continue_simulation():
            self.append_to_action_log(["Continuing simulation from breakpoint"])
            self.on_step_py_simulation(internal=True)
            self.update_dock_ui_contents()
            
    @pyqtSlot()
    def on_hardware_link_lost(self):
        main_window = self.parent()
        editor = main_window.current_editor() if main_window else None
        if not editor or not editor.py_sim_active:
            return

        if self.real_time_timer.isActive():
            self.real_time_timer.stop()
            self._update_internal_controls_enabled_state()
            self.append_to_action_log([
                "HARDWARE LINK LOST. Real-time simulation paused"
            ])
            QMessageBox.warning(
                main_window,
                "Hardware Link Lost",
                "The connection to the hardware was lost. The simulation has been paused."
            )