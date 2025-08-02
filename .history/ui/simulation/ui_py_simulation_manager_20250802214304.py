# fsm_designer_project/ui/simulation/ui_py_simulation_manager.py

import html
import re 
from PyQt5.QtWidgets import (
    QLabel, QTextEdit, QComboBox, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QAction, QMessageBox, QGroupBox, QHBoxLayout, QVBoxLayout,
    QToolButton, QHeaderView, QAbstractItemView, QWidget, QStyle, QSlider,
    QGraphicsItem, QFrame, QSplitter, QScrollArea, QGridLayout, QSizePolicy,
    QSpacerItem, QTabWidget, QProgressBar, QMainWindow
)
from PyQt5.QtGui import QIcon, QColor, QPalette, QFont, QPainter, QLinearGradient
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QSize, Qt, QTime, QTimer, QPropertyAnimation, QEasingCurve

from ...core.fsm_simulator import FSMSimulator, FSMError
from ..graphics.graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
from ...utils import get_standard_icon
from ...utils.config import (APP_FONT_SIZE_SMALL, COLOR_ACCENT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_PRIMARY,
                    COLOR_PY_SIM_STATE_ACTIVE, COLOR_ACCENT_ERROR, COLOR_ACCENT_SUCCESS, COLOR_ACCENT_WARNING,
                    COLOR_BACKGROUND_MEDIUM, COLOR_BORDER_LIGHT, COLOR_ACCENT_SECONDARY) 
from ..animation_manager import AnimationManager
from ..widgets.virtual_hardware_widgets import VirtualLedWidget, VirtualSliderWidget, VirtualGaugeWidget
from ...managers.matlab_simulation_manager import MatlabSimulationManager, SimulationState, SimulationData
from ...managers.action_handlers import ActionHandler

import logging
logger = logging.getLogger(__name__)

class ModernGroupBox(QGroupBox):
    """Enhanced GroupBox with modern styling"""
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setStyleSheet(f"""
            QGroupBox {{
                font-weight: 600;
                font-size: 10pt;
                color: {COLOR_TEXT_PRIMARY};
                border: 2px solid {COLOR_BORDER_LIGHT};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: {COLOR_BACKGROUND_MEDIUM};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                background-color: {COLOR_ACCENT_PRIMARY};
                color: white;
                border-radius: 4px;
                margin-left: 8px;
                margin-top: -2px;
            }}
        """)

class StatusIndicator(QLabel):
    """Modern status indicator with color coding"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(32)
        self.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 500;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)

class ModernButton(QPushButton):
    """Enhanced button with modern styling and hover effects"""
    def __init__(self, text="", icon=None, style_type="primary", parent=None):
        super().__init__(text, parent)
        if icon:
            self.setIcon(icon)
        
        colors = {
            "primary": (COLOR_ACCENT_PRIMARY, "#ffffff"),
            "success": (COLOR_ACCENT_SUCCESS, "#ffffff"),
            "warning": (COLOR_ACCENT_WARNING, "#ffffff"),
            "secondary": (COLOR_ACCENT_SECONDARY, COLOR_TEXT_PRIMARY),
            "danger": (COLOR_ACCENT_ERROR, "#ffffff")
        }
        
        bg_color, text_color = colors.get(style_type, colors["primary"])
        hover_color = QColor(bg_color).lighter(110).name()
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 9pt;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background-color: {QColor(bg_color).darker(110).name()};
                transform: translateY(0px);
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #999999;
            }}
        """)
        
        # Add subtle animation
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

class ModernSlider(QSlider):
    """Enhanced slider with modern styling"""
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {COLOR_BORDER_LIGHT};
                height: 6px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f1f3f4, stop:1 #e8eaed);
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLOR_ACCENT_PRIMARY};
                border: 2px solid white;
                width: 18px;
                height: 18px;
                border-radius: 10px;
                margin: -7px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background: {QColor(COLOR_ACCENT_PRIMARY).lighter(110).name()};
                transform: scale(1.1);
            }}
            QSlider::sub-page:horizontal {{
                background: {COLOR_ACCENT_PRIMARY};
                border-radius: 3px;
            }}
        """)

class PySimulationUIManager(QObject):
    simulationStateChanged = pyqtSignal(bool) 
    requestGlobalUIEnable = pyqtSignal(bool)  

    def __init__(self, main_window, action_handler, parent=None):
        super().__init__(parent)
        self.mw = main_window 
        self.action_handler = action_handler
        self.animation_manager = self.mw.animation_manager if hasattr(self.mw, 'animation_manager') else None
        
        self.matlab_sim_manager = MatlabSimulationManager(self.mw)
        # --- FIXED: Corrected signal connections ---
        self.matlab_sim_manager.simulation_state_changed.connect(self._on_matlab_sim_state_changed)
        self.matlab_sim_manager.simulation_data_updated.connect(self.on_matlab_state_update)
        self.matlab_sim_manager.error_occurred.connect(self.on_matlab_sim_error)
        # --- END FIX ---

        # --- Real-time simulation timer and widgets ---
        self.real_time_timer = QTimer(self)
        self.real_time_timer.timeout.connect(lambda: self.on_step_py_simulation(internal=True))
        self.py_sim_run_pause_btn: ModernButton = None
        self.py_sim_speed_slider: ModernSlider = None
        self.py_sim_speed_label: QLabel = None
        
        # --- UI Widget References ---
        self.py_sim_start_btn: QToolButton = None
        self.py_sim_stop_btn: QToolButton = None
        self.py_sim_reset_btn: QToolButton = None
        self.py_sim_step_btn: ModernButton = None
        self.py_sim_continue_btn: ModernButton = None
        self.py_sim_event_combo: QComboBox = None
        self.py_sim_event_name_edit: QLineEdit = None
        self.py_sim_trigger_event_btn: ModernButton = None
        self.py_sim_current_state_label: StatusIndicator = None
        self.py_sim_current_tick_label: QLabel = None 
        self.py_sim_variables_table: QTableWidget = None
        self.py_sim_action_log_output: QTextEdit = None
        self._py_sim_currently_highlighted_item: GraphicsStateItem | None = None
        self._py_sim_currently_highlighted_transition: GraphicsTransitionItem | None = None 
        
        # Connect to the hardwareLinkLost signal
        if hasattr(self.mw, 'hardware_sim_ui_manager') and self.mw.hardware_sim_ui_manager:
            self.mw.hardware_sim_ui_manager.hardware_link_manager.hardwareLinkLost.connect(self.on_hardware_link_lost)

        self.requestGlobalUIEnable.connect(self._set_global_ui_enabled_state)

    # --- NEW: Handler for simulation state changes ---
    @pyqtSlot(SimulationState, str)
    def _on_matlab_sim_state_changed(self, state, message):
        """Handles the state change signal from the MATLAB simulation manager."""
        if state == SimulationState.RUNNING:
            self.on_matlab_sim_started()
        elif state in [SimulationState.COMPLETED, SimulationState.ERROR, SimulationState.IDLE]:
            self.on_matlab_sim_stopped(message)
    # --- END NEW ---

    @pyqtSlot(bool)
    def _set_global_ui_enabled_state(self, enable: bool):
        """
        Directly enables or disables diagram editing UI elements.
        This logic was moved from MainWindow for better encapsulation.
        """
        logger.debug(f"PySimUI: Setting global UI enabled state to: {enable}")
        
        self.action_handler.set_editing_actions_enabled(enable)

        if hasattr(self.mw, 'elements_palette_dock'):
            self.mw.elements_palette_dock.setEnabled(enable)
        
        if hasattr(self.mw, 'properties_edit_dialog_button'):
            is_item_selected = False
            editor = self.mw.current_editor()
            if editor and editor.scene.selectedItems():
                is_item_selected = True
            self.mw.properties_edit_dialog_button.setEnabled(enable and is_item_selected)

        editor = self.mw.current_editor()
        if editor:
            for item in editor.scene.items():
                if isinstance(item, (GraphicsStateItem, GraphicsCommentItem)):
                    item.setFlag(QGraphicsItem.ItemIsMovable, enable and editor.scene.current_mode == "select")
            
            if not enable and editor.scene.current_mode != "select":
                editor.scene.set_mode("select")
        
        self.mw._update_matlab_actions_enabled_state()

    def create_dock_widget_contents(self) -> QWidget:
        # Main container with modern styling
        main_container = QWidget()
        main_container.setStyleSheet(f"""
            QWidget {{
                background-color: #fafbfc;
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        
        # Use splitter for better space management
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)
        
        # Top section: Controls and Status
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(8, 8, 8, 4)
        top_layout.setSpacing(8)

        # Simulation Control Section
        controls_group = ModernGroupBox("🎮 Simulation Control")
        controls_layout = QGridLayout(controls_group)
        controls_layout.setSpacing(8)
        controls_layout.setContentsMargins(12, 20, 12, 12)
        
        # Enhanced control buttons
        self.py_sim_start_btn = QToolButton()
        if hasattr(self.mw, 'start_py_sim_action'): 
            self.py_sim_start_btn.setDefaultAction(self.mw.start_py_sim_action)
        self.py_sim_start_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.py_sim_start_btn.setMinimumHeight(36)
        self.py_sim_start_btn.setStyleSheet(f"""
            QToolButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_ACCENT_SUCCESS}, stop:1 {QColor(COLOR_ACCENT_SUCCESS).darker(110).name()});
                color: white;
                border: 1px solid {QColor(COLOR_ACCENT_SUCCESS).darker(120).name()};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QToolButton:hover {{
                background: {QColor(COLOR_ACCENT_SUCCESS).lighter(110).name()};
            }}
        """)
        self.mw.start_py_sim_action.setText("Initialize")
        self.mw.start_py_sim_action.setToolTip("Initialize the Python simulator engine with the current diagram")

        self.py_sim_stop_btn = QToolButton()
        if hasattr(self.mw, 'stop_py_sim_action'): 
            self.py_sim_stop_btn.setDefaultAction(self.mw.stop_py_sim_action)
        self.py_sim_stop_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.py_sim_stop_btn.setMinimumHeight(36)
        self.py_sim_stop_btn.setStyleSheet(f"""
            QToolButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_ACCENT_ERROR}, stop:1 {QColor(COLOR_ACCENT_ERROR).darker(110).name()});
                color: white;
                border: 1px solid {QColor(COLOR_ACCENT_ERROR).darker(120).name()};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QToolButton:hover {{
                background: {QColor(COLOR_ACCENT_ERROR).lighter(110).name()};
            }}
        """)

        self.py_sim_reset_btn = QToolButton()
        if hasattr(self.mw, 'reset_py_sim_action'): 
            self.py_sim_reset_btn.setDefaultAction(self.mw.reset_py_sim_action)
        self.py_sim_reset_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.py_sim_reset_btn.setMinimumHeight(36)
        self.py_sim_reset_btn.setStyleSheet(f"""
            QToolButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_ACCENT_WARNING}, stop:1 {QColor(COLOR_ACCENT_WARNING).darker(110).name()});
                color: white;
                border: 1px solid {QColor(COLOR_ACCENT_WARNING).darker(120).name()};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QToolButton:hover {{
                background: {QColor(COLOR_ACCENT_WARNING).lighter(110).name()};
            }}
        """)
        
        self.matlab_sim_start_stop_btn = ModernButton("Run Live Simulink", get_standard_icon(QStyle.SP_ComputerIcon, "Simulink"), "primary")
        self.matlab_sim_start_stop_btn.setCheckable(True)
        self.matlab_sim_start_stop_btn.setToolTip("Run the exported Simulink model with live feedback on the canvas")
        self.matlab_sim_start_stop_btn.clicked.connect(self.on_toggle_matlab_simulation)

        # Arrange control buttons in grid
        controls_layout.addWidget(self.py_sim_start_btn, 0, 0)
        controls_layout.addWidget(self.py_sim_stop_btn, 0, 1)
        controls_layout.addWidget(self.py_sim_reset_btn, 0, 2)
        controls_layout.addWidget(self.matlab_sim_start_stop_btn, 1, 0, 1, 3)
        
        top_layout.addWidget(controls_group)

        # Execution Control Section
        execution_group = ModernGroupBox("⚡ Execution Control")
        execution_layout = QVBoxLayout(execution_group)
        execution_layout.setContentsMargins(12, 20, 12, 12)
        execution_layout.setSpacing(8)

        # First row: Run/Pause and manual controls
        exec_row1 = QHBoxLayout()
        exec_row1.setSpacing(8)

        self.py_sim_run_pause_btn = ModernButton("Run", get_standard_icon(QStyle.SP_MediaPlay, "Run"), "success")
        self.py_sim_run_pause_btn.clicked.connect(self.on_toggle_real_time_simulation)
        self.py_sim_run_pause_btn.setMinimumHeight(36)
        exec_row1.addWidget(self.py_sim_run_pause_btn)
        
        exec_row1.addWidget(QFrame())  # Spacer

        self.py_sim_step_btn = ModernButton("Step", get_standard_icon(QStyle.SP_MediaSeekForward, "Step"), "primary")
        self.py_sim_step_btn.clicked.connect(lambda: self.on_step_py_simulation(internal=False))
        exec_row1.addWidget(self.py_sim_step_btn)

        self.py_sim_continue_btn = ModernButton("Continue", get_standard_icon(QStyle.SP_MediaSkipForward, "Cont"), "warning")
        self.py_sim_continue_btn.setToolTip("Continue execution from breakpoint")
        self.py_sim_continue_btn.clicked.connect(self.on_continue_py_simulation)
        exec_row1.addWidget(self.py_sim_continue_btn)

        execution_layout.addLayout(exec_row1)

        # Second row: Speed control
        speed_frame = QFrame()
        speed_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.7);
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        speed_layout = QHBoxLayout(speed_frame)
        speed_layout.setContentsMargins(8, 8, 8, 8)

        speed_icon = QLabel("🏃")
        speed_icon.setFont(QFont("Arial", 12))
        speed_layout.addWidget(speed_icon)
        speed_layout.addWidget(QLabel("Speed:"))
        
        self.py_sim_speed_slider = ModernSlider(Qt.Horizontal)
        self.py_sim_speed_slider.setRange(100, 2000)
        self.py_sim_speed_slider.setValue(1000)
        self.py_sim_speed_slider.setInvertedAppearance(True)
        self.py_sim_speed_slider.valueChanged.connect(self.on_speed_slider_changed)
        speed_layout.addWidget(self.py_sim_speed_slider, 1)
        
        self.py_sim_speed_label = QLabel("1000 ms/step")
        self.py_sim_speed_label.setMinimumWidth(80)
        self.py_sim_speed_label.setStyleSheet(f"font-weight: 500; color: {COLOR_TEXT_SECONDARY};")
        speed_layout.addWidget(self.py_sim_speed_label)
        
        execution_layout.addWidget(speed_frame)
        top_layout.addWidget(execution_group)

        # Status Section
        status_group = ModernGroupBox("📊 Current Status")
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(12, 20, 12, 12)
        status_layout.setSpacing(8)
        
        self.py_sim_current_state_label = StatusIndicator()
        self.py_sim_current_state_label.setText("Not Initialized")
        status_layout.addWidget(self.py_sim_current_state_label)
        
        self.py_sim_current_tick_label = QLabel("Tick: 0")
        self.py_sim_current_tick_label.setStyleSheet(f"""
            font-size: {APP_FONT_SIZE_SMALL}px; 
            color: {COLOR_TEXT_SECONDARY}; 
            padding: 4px 8px;
            background-color: rgba(255, 255, 255, 0.5);
            border-radius: 4px;
            font-weight: 500;
        """)
        status_layout.addWidget(self.py_sim_current_tick_label)
        
        top_layout.addWidget(status_group)

        # Event Trigger Section
        event_group = ModernGroupBox("🎯 Manual Event Trigger")
        event_layout = QGridLayout(event_group)
        event_layout.setContentsMargins(12, 20, 12, 12)
        event_layout.setSpacing(8)
        
        self.py_sim_event_combo = QComboBox()
        self.py_sim_event_combo.setEditable(False)
        self.py_sim_event_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px 12px;
                border: 2px solid {COLOR_BORDER_LIGHT};
                border-radius: 6px;
                background-color: white;
                font-size: 9pt;
                min-height: 20px;
            }}
            QComboBox:focus {{
                border-color: {COLOR_ACCENT_PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        event_layout.addWidget(self.py_sim_event_combo, 0, 0)
        
        self.py_sim_event_name_edit = QLineEdit()
        self.py_sim_event_name_edit.setPlaceholderText("Custom event name")
        self.py_sim_event_name_edit.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px 12px;
                border: 2px solid {COLOR_BORDER_LIGHT};
                border-radius: 6px;
                background-color: white;
                font-size: 9pt;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border-color: {COLOR_ACCENT_PRIMARY};
                background-color: #fafffe;
            }}
        """)
        event_layout.addWidget(self.py_sim_event_name_edit, 0, 1)
        
        self.py_sim_trigger_event_btn = ModernButton("Trigger", get_standard_icon(QStyle.SP_ArrowRight, "Trg"), "primary")
        self.py_sim_trigger_event_btn.clicked.connect(self._on_trigger_button_clicked)
        self.py_sim_trigger_event_btn.setMinimumHeight(36)
        event_layout.addWidget(self.py_sim_trigger_event_btn, 0, 2)
        
        top_layout.addWidget(event_group)

        main_splitter.addWidget(top_widget)

        # Bottom section: Data tables and logs
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(8, 4, 8, 8)
        
        # Create tabbed interface for better organization
        data_tabs = QTabWidget()
        data_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 2px solid {COLOR_BORDER_LIGHT};
                border-radius: 8px;
                background-color: white;
            }}
            QTabBar::tab {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e9ecef, stop:1 #dee2e6);
                border: 1px solid {COLOR_BORDER_LIGHT};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background: white;
                border-bottom-color: white;
                color: {COLOR_ACCENT_PRIMARY};
                font-weight: 600;
            }}
            QTabBar::tab:hover {{
                background: {QColor(COLOR_ACCENT_PRIMARY).lighter(180).name()};
            }}
        """)

        # Variables tab
        variables_widget = QWidget()
        variables_layout = QVBoxLayout(variables_widget)
        variables_layout.setContentsMargins(8, 8, 8, 8)
        
        self.py_sim_variables_table = QTableWidget()
        self.py_sim_variables_table.setColumnCount(2)
        self.py_sim_variables_table.setHorizontalHeaderLabels(["Variable", "Value"])
        self.py_sim_variables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.py_sim_variables_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.py_sim_variables_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed)
        self.py_sim_variables_table.itemChanged.connect(self.on_sim_variable_changed)
        self.py_sim_variables_table.setAlternatingRowColors(True)
        self.py_sim_variables_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 6px;
                background-color: white;
                gridline-color: {COLOR_BORDER_LIGHT};
                font-size: 9pt;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            }}
            QTableWidget::item:selected {{
                background-color: {QColor(COLOR_ACCENT_PRIMARY).lighter(180).name()};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_ACCENT_PRIMARY}, stop:1 {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()});
                color: white;
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
        """)
        variables_layout.addWidget(self.py_sim_variables_table)
        data_tabs.addTab(variables_widget, "📋 Variables")

        # Action Log tab
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(8, 8, 8, 8)
        
        self.py_sim_action_log_output = QTextEdit()
        self.py_sim_action_log_output.setReadOnly(True)
        self.py_sim_action_log_output.setObjectName("PySimActionLog")
        self.py_sim_action_log_output.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 6px;
                background-color: #fafafa;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 8pt;
                line-height: 1.4;
                padding: 8px;
            }}
        """)
        log_layout.addWidget(self.py_sim_action_log_output)
        data_tabs.addTab(log_widget, "📝 Action Log")

        bottom_layout.addWidget(data_tabs)
        main_splitter.addWidget(bottom_widget)

        # Set splitter proportions
        main_splitter.setStretchFactor(0, 0)  # Top section fixed
        main_splitter.setStretchFactor(1, 1)  # Bottom section expandable
        
        # Final layout
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_splitter)
        
        self._update_internal_controls_enabled_state() 
        return main_container

    @pyqtSlot(bool)
    def on_toggle_matlab_simulation(self, checked):
        if checked:
            if not self.mw.last_generated_model_path or not os.path.exists(self.mw.last_generated_model_path):
                QMessageBox.warning(self.mw, "No Simulink Model", "Please export the diagram to a Simulink model first using the 'Code Export' tab.")
                self.matlab_sim_start_stop_btn.setChecked(False)
                return

            if self.mw.current_editor() and self.mw.current_editor().py_sim_active:
                QMessageBox.warning(self.mw, "Simulation Active", "Please stop the internal Python simulation before starting the Simulink simulation.")
                self.matlab_sim_start_stop_btn.setChecked(False)
                return
            
            self.matlab_sim_manager.start(self.mw.last_generated_model_path)
            self.matlab_sim_start_stop_btn.setText("Connecting...")
            self.matlab_sim_start_stop_btn.setEnabled(False) # Disable until connected/failed
        else:
            self.matlab_sim_manager.stop()
            self.matlab_sim_start_stop_btn.setText("Stopping...")
            self.matlab_sim_start_stop_btn.setEnabled(False) # Disable until stopped

    @pyqtSlot()
    def on_matlab_sim_started(self):
        self.append_to_action_log(["🚀 Simulink live simulation started."])
        self.matlab_sim_start_stop_btn.setText("Stop Live Simulink")
        self.matlab_sim_start_stop_btn.setEnabled(True)
        self.requestGlobalUIEnable.emit(False) # Lock editing UI

    @pyqtSlot(str)
    def on_matlab_sim_stopped(self, reason):
        self.append_to_action_log([f"🛑 Simulink live simulation stopped: {reason}"])
        self.matlab_sim_start_stop_btn.setChecked(False)
        self.matlab_sim_start_stop_btn.setText("Run Live Simulink")
        self.matlab_sim_start_stop_btn.setEnabled(True)
        self._highlight_sim_active_state(None) # Clear highlighting
        self.requestGlobalUIEnable.emit(True) # Unlock editing UI

    @pyqtSlot(str)
    def on_matlab_sim_error(self, error_message):
        self.append_to_action_log([f"❌ Simulink Error: {error_message}"])
        self.on_matlab_sim_stopped("Error") # Trigger UI reset
        QMessageBox.critical(self.mw, "Simulink Simulation Error", error_message)

    # --- FIXED: Corrected method signature ---
    @pyqtSlot(SimulationData)
    def on_matlab_state_update(self, data):
        # This is where the live feedback happens
        state_name = data.active_state
        tick = data.tick
        self.py_sim_current_state_label.setText(state_name)
        self.py_sim_current_tick_label.setText(f"Tick: {tick}")
        self._highlight_sim_active_state(state_name)
        
        # Trigger animations
        if self.animation_manager:
            # We don't know the previous state directly, so we just animate the entry
            self.animation_manager.animate_state_entry(state_name)
    # --- END FIX ---

    @pyqtSlot(int)
    def on_speed_slider_changed(self, value):
        if self.py_sim_speed_label: 
            self.py_sim_speed_label.setText(f"{value} ms/step")
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
            self.py_sim_run_pause_btn.setText("Pause")
            self.py_sim_run_pause_btn.setIcon(get_standard_icon(QStyle.SP_MediaPause, "Pause"))
        else:
            self.py_sim_run_pause_btn.setText("Run")
            self.py_sim_run_pause_btn.setIcon(get_standard_icon(QStyle.SP_MediaPlay, "Run"))
            
        manual_controls_enabled = sim_active and not is_running_real_time and not is_paused_at_bp
        self.py_sim_step_btn.setEnabled(manual_controls_enabled)
        self.py_sim_event_combo.setEnabled(manual_controls_enabled)
        self.py_sim_event_name_edit.setEnabled(manual_controls_enabled)
        self.py_sim_trigger_event_btn.setEnabled(manual_controls_enabled)
        
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
        editor = self.mw.current_editor()
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
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or not editor.py_sim_active: 
            # Reset UI to inactive state
            if self.py_sim_current_state_label: 
                self.py_sim_current_state_label.setText("Not Initialized")
                self.py_sim_current_state_label.setStyleSheet(f"""
                    QLabel {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #f8f9fa, stop:1 #e9ecef);
                        border: 1px solid {COLOR_BORDER_LIGHT};
                        border-radius: 6px;
                        padding: 8px 12px;
                        font-weight: 500;
                        color: {COLOR_TEXT_SECONDARY};
                    }}
                """)
            
            if self.py_sim_current_tick_label: 
                self.py_sim_current_tick_label.setText("Tick: 0") 
            if self.py_sim_variables_table: 
                self.py_sim_variables_table.setRowCount(0)
            
            self._highlight_sim_active_state(None)
            
            if self.py_sim_event_combo: 
                self.py_sim_event_combo.clear()
                self.py_sim_event_combo.addItem("None (Internal Step)")
            
            # Reset hardware widgets
            if hasattr(self.mw, 'hardware_sim_ui_manager'):
                hw_mgr = self.mw.hardware_sim_ui_manager
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
            return
        
        # Update active simulation state
        hierarchical_state_name = editor.py_fsm_engine.get_current_state_name()
        display_state_name = (hierarchical_state_name[:30] + '...') if len(hierarchical_state_name) > 33 else hierarchical_state_name
        
        paused_suffix = " <span style='color:orange; font-weight:bold;'>(⏸ Paused)</span>" if editor.py_fsm_engine.paused_on_breakpoint else ""
        
        # Enhanced status display with better visual feedback
        status_text = f"<span style='font-weight:600; font-size:10pt;'>🎯 {html.escape(display_state_name)}</span>{paused_suffix}"
        self.py_sim_current_state_label.setText(status_text)

        # Dynamic status styling based on simulation state
        if editor.py_fsm_engine.paused_on_breakpoint:
            status_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff3cd, stop:1 #ffeaa7)"
            border_color = COLOR_ACCENT_WARNING
        else:
            status_bg = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {QColor(COLOR_PY_SIM_STATE_ACTIVE).lighter(150).name()}, stop:1 {QColor(COLOR_PY_SIM_STATE_ACTIVE).lighter(120).name()})"
            border_color = COLOR_PY_SIM_STATE_ACTIVE

        self.py_sim_current_state_label.setStyleSheet(f"""
            QLabel {{
                background: {status_bg};
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 12px 16px;
                font-weight: 500;
                color: {COLOR_TEXT_PRIMARY};
                min-height: 20px;
            }}
        """)

        # Enhanced tick display
        tick_count = editor.py_fsm_engine.current_tick
        self.py_sim_current_tick_label.setText(f"⏱ Tick: {tick_count:,}")

        self._highlight_sim_active_state(hierarchical_state_name)
        
        # Update variables table with enhanced styling
        all_vars = sorted(editor.py_fsm_engine.get_variables().items())
        
        self.py_sim_variables_table.blockSignals(True)
        self.py_sim_variables_table.setRowCount(len(all_vars))
        
        for r, (name, val) in enumerate(all_vars):
            # Variable name (read-only)
            name_item = QTableWidgetItem(f"📊 {name}")
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setFont(QFont("Arial", 9, QFont.Bold))
            self.py_sim_variables_table.setItem(r, 0, name_item)
            
            # Variable value (editable)
            val_item = QTableWidgetItem(str(val))
            val_item.setFont(QFont("Consolas", 9))
            
            # Color-code values by type
            if isinstance(val, bool):
                val_item.setBackground(QColor("#e8f5e8" if val else "#ffeaea"))
            elif isinstance(val, (int, float)):
                val_item.setBackground(QColor("#e8f0ff"))
            else:
                val_item.setBackground(QColor("#fff8e1"))
                
            self.py_sim_variables_table.setItem(r, 1, val_item)
        
        self.py_sim_variables_table.resizeColumnsToContents()
        self.py_sim_variables_table.blockSignals(False)

        # Update event combo with enhanced styling
        current_event_text = self.py_sim_event_combo.currentText()
        possible_events = sorted(list(filter(None, editor.py_fsm_engine.get_possible_events_from_current_state())))
        
        self.py_sim_event_combo.clear()
        self.py_sim_event_combo.addItems(["🔄 None (Internal Step)"] + [f"⚡ {event}" for event in possible_events])
        
        idx = self.py_sim_event_combo.findText(current_event_text)
        if idx != -1: 
            self.py_sim_event_combo.setCurrentIndex(idx)

        # Update hardware widgets with enhanced feedback
        if hasattr(self.mw, 'hardware_sim_ui_manager'):
            hw_mgr = self.mw.hardware_sim_ui_manager
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

        self._update_internal_controls_enabled_state()

    def append_to_action_log(self, log_entries: list[str]):
        if not self.py_sim_action_log_output: 
            return
            
        # Enhanced color scheme for better readability
        time_color = QColor(COLOR_TEXT_SECONDARY).darker(110).name()
        default_log_color = "#2c3e50"
        error_color = QColor(COLOR_ACCENT_ERROR).name()
        warning_color = QColor(COLOR_ACCENT_WARNING).darker(10).name()
        highlight_color = QColor(COLOR_ACCENT_PRIMARY).name()
        success_color = QColor(COLOR_ACCENT_SUCCESS).darker(110).name()
        breakpoint_color = QColor(COLOR_ACCENT_WARNING).name()
        
        editor = self.mw.current_editor()

        # Animation integration
        for entry in log_entries:
            # Look for transition log entries to trigger the pulse animation
            # Example log: "[Tick 1] Transition on 'toggle' from 'Off' to 'On'"
            transition_match = re.search(r"Transition on '([^']*)' from '([^']*)' to '([^']*)'", entry)
            if transition_match and editor:
                event, source_name, target_name = transition_match.groups()
                # Find the corresponding graphics item in the scene
                for item in editor.scene.items():
                    if isinstance(item, GraphicsTransitionItem):
                        if item.start_item and item.start_item.text_label == source_name and \
                           item.end_item and item.end_item.text_label == target_name and \
                           item.event_str == event:
                            item.start_pulse_animation()
                            break
            
            if self.animation_manager:
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
            timestamp = QTime.currentTime().toString('hh:mm:ss.zzz')
            tick_str = ""
            
            # Enhanced tick parsing
            tick_match = re.match(r"(\[SUB\] )*\[Tick (\d+)\] (.*)", entry)
            actual_entry_msg = tick_match.group(3) if tick_match else entry
            
            if tick_match: 
                tick_num = int(tick_match.group(2))
                sub_prefix = tick_match.group(1) or ''
                tick_str = f"<span style='color:{QColor(COLOR_TEXT_SECONDARY).lighter(110).name()}; font-size:7pt; background:rgba(0,0,0,0.05); padding:2px 4px; border-radius:2px;'>{sub_prefix}🎯 Tick {tick_num:,}</span> "
            
            cleaned_entry = html.escape(actual_entry_msg)
            current_color = default_log_color
            style_tags = ("", "")
            icon = ""
            
            # Enhanced message categorization with icons
            if "[HALT]" in entry or "BREAKPOINT" in entry or "PAUSED" in entry: 
                current_color, style_tags, icon = breakpoint_color, ("<b><i>", "</i></b>"), "⏸️"
            elif "Continuing" in entry: 
                current_color, style_tags, icon = success_color, ("<i>", "</i>"), "▶️"
            elif any(kw in entry.upper() for kw in ["[EVAL ERROR]", "[HALTED]", "SECURITYERROR", "[CODE ERROR]"]): 
                current_color, style_tags, icon = error_color, ("<b>", "</b>"), "❌"
            elif any(kw in entry for kw in ["[SAFETY CHECK", "[ACTION BLOCKED]", "Warning:"]): 
                current_color, style_tags, icon = warning_color, ("<b>", "</b>"), "⚠️"
            elif any(kw in entry for kw in ["Entering state:", "Exiting state:", "After transition"]): 
                current_color, style_tags, icon = highlight_color, ("<b>", "</b>"), "🔄"
            elif any(kw in entry for kw in ["initialized", "started.", "stopped.", "Reset"]): 
                current_color, style_tags, icon = success_color, ("<b><i>", "</i></b>"), "✅"
            elif "Real-time simulation" in entry:
                if "started" in entry:
                    current_color, style_tags, icon = success_color, ("<b>", "</b>"), "🚀"
                else:
                    current_color, style_tags, icon = warning_color, ("<b>", "</b>"), "⏸️"
            elif "Triggering event" in entry:
                current_color, style_tags, icon = highlight_color, ("<b>", "</b>"), "⚡"
            
            # Construct enhanced log entry
            log_html = f"""
            <div style='margin:2px 0; padding:4px 8px; border-left:3px solid {current_color}; background:rgba(255,255,255,0.7); border-radius:0 4px 4px 0;'>
                <span style='color:{time_color}; font-size:7pt; font-family:monospace;'>[{timestamp}]</span> 
                {tick_str}
                <span style='color:{current_color}; font-weight:500;'>{icon} {style_tags[0]}{cleaned_entry}{style_tags[1]}</span>
            </div>
            """
            
            self.py_sim_action_log_output.append(log_html)
        
        # Auto-scroll to bottom
        self.py_sim_action_log_output.verticalScrollBar().setValue(
            self.py_sim_action_log_output.verticalScrollBar().maximum()
        )

    @pyqtSlot(QTableWidgetItem)
    def on_sim_variable_changed(self, item: QTableWidgetItem):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine or item.column() != 1: 
            return
            
        row = item.row()
        var_name_item = self.py_sim_variables_table.item(row, 0)
        if not var_name_item:
            return
            
        # Extract variable name (remove icon prefix)
        var_name = var_name_item.text().replace("📊 ", "").strip()
        new_value_str = item.text().strip()
        simulator_instance = editor.py_fsm_engine
        
        try: 
            # Enhanced value parsing
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
            
            # Update the item's background color based on new value type
            if isinstance(new_value, bool):
                item.setBackground(QColor("#e8f5e8" if new_value else "#ffeaea"))
            elif isinstance(new_value, (int, float)):
                item.setBackground(QColor("#e8f0ff"))
            else:
                item.setBackground(QColor("#fff8e1"))
        else: 
            self.update_dock_ui_contents()

    @pyqtSlot()
    def on_start_py_simulation(self):
        editor = self.mw.current_editor()
        if not editor: 
            QMessageBox.warning(self.mw, "No Active Diagram", "Please select a diagram tab to initialize.")
            return
            
        if editor.py_sim_active: 
            QMessageBox.information(self, "Simulation Already Active", "Python simulation is already initialized for this tab.")
            return
            
        if editor.scene.is_dirty():
            reply = QMessageBox.question(
                self.mw, 
                "Unsaved Changes", 
                "The diagram has unsaved changes. Initialize simulation anyway?", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.Yes
            )
            if reply == QMessageBox.No: 
                return
        
        diagram_data = editor.scene.get_diagram_data()
        if not diagram_data.get('states'): 
            QMessageBox.warning(self.mw, "Empty Diagram", "Cannot initialize simulation: The diagram has no states.")
            return
        
        try:
            # Animation manager integration
            if self.animation_manager:
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

            # Initialize FSM engine
            editor.py_fsm_engine = FSMSimulator(
                diagram_data['states'], 
                diagram_data['transitions'], 
                halt_on_action_error=True
            )
            
            self._set_simulation_active_state(True)
            
            # Clear and initialize log
            if self.py_sim_action_log_output: 
                self.py_sim_action_log_output.clear()
                
            initial_log = ["🚀 Python FSM Simulation initialized successfully!"] + editor.py_fsm_engine.get_last_executed_actions_log()
            self.append_to_action_log(initial_log)
            self.update_dock_ui_contents()
            
        except (FSMError, Exception) as e:
            QMessageBox.critical(self.mw, "FSM Initialization Error", f"Failed to initialize Python FSM simulation:\n{e}")
            self.append_to_action_log([f"❌ ERROR Initializing Simulation: {e}"])
            editor.py_fsm_engine = None
            self._set_simulation_active_state(False)

    @pyqtSlot(bool)
    def on_stop_py_simulation(self, silent=False):
        editor = self.mw.current_editor()
        if not editor or not editor.py_sim_active: 
            return
            
        self.real_time_timer.stop()
        self._highlight_sim_active_state(None)
        
        editor.py_fsm_engine = None
        self._set_simulation_active_state(False) 
        self.update_dock_ui_contents()
        
        if not silent: 
            self.append_to_action_log(["🛑 Python FSM Simulation stopped."])
        if self.animation_manager: 
            self.animation_manager.clear_animations()

    @pyqtSlot()
    def _on_trigger_button_clicked(self):
        """Slot to handle the button click, which then calls the main logic."""
        self.on_trigger_py_event()

    @pyqtSlot()
    def on_reset_py_simulation(self):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine: 
            return
            
        self.real_time_timer.stop()
        if self.animation_manager: 
            self.animation_manager.clear_animations()
            
        try:
            editor.py_fsm_engine.reset()
            if self.py_sim_action_log_output: 
                self.py_sim_action_log_output.append(
                    "<div style='text-align:center; padding:8px; background:rgba(0,0,0,0.1); margin:4px 0; border-radius:4px;'>"
                    "<i style='color:#666; font-size:9pt;'>🔄 === Simulation Reset === 🔄</i>"
                    "</div>"
                )
            self.append_to_action_log(editor.py_fsm_engine.get_last_executed_actions_log())
            self.update_dock_ui_contents()
        except (FSMError, Exception) as e: 
            QMessageBox.critical(self.mw, "FSM Reset Error", f"Failed to reset simulation:\n{e}")

    @pyqtSlot(bool)
    def on_step_py_simulation(self, internal=False):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine:
            if not internal: 
                QMessageBox.warning(self.mw, "Not Initialized", "Please initialize the simulation first.")
            return
            
        try:
            _, log_entries = editor.py_fsm_engine.step(event_name=None)
            self.append_to_action_log(log_entries)
            self.update_dock_ui_contents()
            
            if editor.py_fsm_engine.simulation_halted_flag or editor.py_fsm_engine.paused_on_breakpoint:
                self.real_time_timer.stop()
                if not internal: 
                    QMessageBox.information(self, "Simulation Paused", "Simulation has paused due to a breakpoint or error.")
        except (FSMError, Exception) as e: 
            self.real_time_timer.stop()
            QMessageBox.critical(self.mw, "Step Error", f"An error occurred: {e}")
        
        self._update_internal_controls_enabled_state()
        
    @pyqtSlot(str)
    def on_trigger_py_event(self, external_event_name: str = None):
        editor = self.mw.current_editor()
        if not editor or not editor.py_fsm_engine: 
            return
            
        # Enhanced event name processing
        event_to_trigger = external_event_name or self.py_sim_event_name_edit.text().strip()
        
        if not event_to_trigger:
            combo_text = self.py_sim_event_combo.currentText()
            if combo_text and combo_text != "🔄 None (Internal Step)":
                event_to_trigger = combo_text.replace("⚡ ", "")
        
        if not event_to_trigger: 
            self.on_step_py_simulation()
            return
        
        self.append_to_action_log([f"⚡ Triggering event: '{html.escape(event_to_trigger)}'"])
        
        try:
            _, log_entries = editor.py_fsm_engine.step(event_name=event_to_trigger)
            self.append_to_action_log(log_entries)
            self.update_dock_ui_contents()
            self.py_sim_event_name_edit.clear()
        except (FSMError, Exception) as e: 
            QMessageBox.critical(self, "Event Error", f"An error occurred: {e}")

    @pyqtSlot()
    def on_continue_py_simulation(self):
        editor = self.mw.current_editor()
        if not editor or not (editor.py_fsm_engine and editor.py_fsm_engine.paused_on_breakpoint): 
            return
            
        if editor.py_fsm_engine.continue_simulation():
            self.append_to_action_log(["▶️ Continuing simulation from breakpoint..."])
            self.on_step_py_simulation(internal=True)
            self.update_dock_ui_contents()
            
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
                "⚠️ [HALT] HARDWARE LINK LOST. Real-time simulation paused."
            ])
            QMessageBox.warning(
                self.mw, 
                "Hardware Link Lost",
                "The connection to the hardware was lost. The simulation has been paused."
            )