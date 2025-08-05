# fsm_designer_project/managers/perspective_manager.py
"""
Manages the application's dock panel layouts, allowing users to switch between
predefined perspectives (like Design, Simulation, IDE focus) and save/load custom layouts.
"""

import logging
import os
import json
from PyQt5.QtCore import QObject, pyqtSlot, Qt, QDir, QUrl, QPointF, QRectF, QSizeF, QTimer, QMetaObject, Q_ARG
from PyQt5.QtGui import QIcon, QKeySequence, QCloseEvent, QPalette, QColor, QPen, QFont, QPainterPath, QLinearGradient, QRadialGradient, QPainter
from PyQt5.QtWidgets import (
    QMainWindow, QDockWidget, QAction, QToolBar, QVBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QFileDialog, QMessageBox, QInputDialog, QLineEdit, QColorDialog, QDialog, QFormLayout,
    QSpinBox, QComboBox, QDoubleSpinBox, QCheckBox, QTabWidget, QActionGroup, QStyle, QFrame, QHBoxLayout, QProgressBar, QSplitter, QScrollArea, QGraphicsItem, QGraphicsScene, QGraphicsView, QFileSystemModel, QTreeView
)

from ..utils import get_standard_icon
from ..utils.config import (
    APP_VERSION, APP_NAME,
    DYNAMIC_UPDATE_COLORS_FROM_THEME,
    COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL, COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_ERROR, COLOR_TEXT_PRIMARY, COLOR_BORDER_LIGHT,
    COLOR_BACKGROUND_LIGHT, COLOR_ACCENT_PRIMARY_LIGHT, COLOR_ACCENT_SECONDARY,
    COLOR_BACKGROUND_APP, COLOR_DRAGGABLE_BUTTON_BG, COLOR_DRAGGABLE_BUTTON_BORDER,
    COLOR_DRAGGABLE_BUTTON_HOVER_BG, COLOR_DRAGGABLE_BUTTON_HOVER_BORDER,
    COLOR_DRAGGABLE_BUTTON_PRESSED_BG
)
from ..assets.assets import FSM_TEMPLATES_BUILTIN
from ..assets.target_profiles import TARGET_PROFILES
from ..core.matlab_integration import MatlabConnection
from ..core.fsm_simulator import FSMSimulator, FSMError
from ..core.resource_estimator import ResourceEstimator
from ..core.snippet_manager import CustomSnippetManager
from ..utils import config
from ..ui.widgets.editor_widget import EditorWidget
from ..managers.project_manager import ProjectManager, PROJECT_FILE_FILTER, PROJECT_FILE_EXTENSION
from ..managers.matlab_simulation_manager import MatlabSimulationManager
from ..managers import MatlabSimulationManager, SettingsManager
from ..ui.widgets.custom_widgets import CollapsibleSection, DraggableToolButton
from ..ui.animation_manager import AnimationManager
from ..utils.logging_setup import setup_global_logging
from ..utils.python_code_generator import generate_python_fsm_code
from ..utils.c_code_generator import generate_c_code_content
from ..plugins.plantuml_exporter import generate_plantuml_text
from ..plugins.mermaid_exporter import generate_mermaid_text
from ..ui.widgets.code_editor import CodeEditor
from ..ui.simulation.ui_py_simulation_manager import PySimulationUIManager
from ..ui.simulation.ui_virtual_hardware_manager import VirtualHardwareUIManager
from ..ui.simulation.plot_widget import SimulationPlotWidget
from ..ui.graphics.graphics_scene import MinimapView

logger = logging.getLogger(__name__)

class PerspectiveManager(QObject):
    """
    Manages the application's dock panel layouts, allowing users to switch between
    predefined perspectives (like Design, Simulation, IDE focus) and save/load
    custom layouts.
    """
    
    def __init__(self, main_window: QMainWindow, settings_manager, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self.settings_manager = settings_manager

        # Action group for perspective radio buttons
        self.mw.perspectives_action_group = QActionGroup(self.mw)
        
        # Load the last used perspective name from settings
        self.current_perspective_name = self.settings_manager.get(
            "last_used_perspective", self.mw.PERSPECTIVE_DESIGN_FOCUS
        )
        
        # Populate the perspectives menu and apply the initial layout
        self.populate_menu()
        self.apply_perspective(self.current_perspective_name)

    @pyqtSlot()
    def populate_menu(self):
        """Populates the 'View > Perspectives' menu."""
        menu = self.mw.view_menu # Get the view menu from MainWindow
        if not menu:
            logger.error("Perspectives menu could not be created: MainWindow.view_menu is not set.")
            return
            
        # Clear existing perspective actions and group
        if hasattr(self.mw, 'perspectives_action_group'):
            for action in self.mw.perspectives_action_group.actions():
                self.mw.perspectives_action_group.removeAction(action)
        
        # Re-add the perspective menu entry if it was cleared (e.g., on a full menu reset)
        if not hasattr(self.mw, 'perspectives_menu') or not self.mw.perspectives_menu.actions():
            self.mw.perspectives_menu = menu.addMenu("Perspectives")
        
        self.mw.perspectives_menu.clear() # Ensure it's empty before repopulating

        # Add default perspectives
        default_names = self.mw.DEFAULT_PERSPECTIVES_ORDER
        for p_name in default_names:
            action = QAction(p_name, self.mw)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, name=p_name: self.apply_perspective(name))
            self.mw.perspectives_action_group.addAction(action)
            self.mw.perspectives_menu.addAction(action)

        self.mw.perspectives_menu.addSeparator()

        # Add user-defined perspectives
        user_perspective_names = self.settings_manager.get("user_perspective_names", [])
        if user_perspective_names:
            for p_name in sorted(user_perspective_names):
                action = QAction(p_name, self.mw)
                action.setCheckable(True)
                action.triggered.connect(lambda checked=False, name=p_name: self.apply_perspective(name))
                self.mw.perspectives_action_group.addAction(action)
            self.mw.perspectives_menu.addSeparator()
        
        # Add save/reset actions
        if hasattr(self.mw, 'save_perspective_action'):
            self.mw.save_perspective_action.triggered.connect(self.save_current_as)
            self.mw.perspectives_menu.addAction(self.mw.save_perspective_action)
        if hasattr(self.mw, 'reset_perspectives_action'):
            self.mw.reset_perspectives_action.triggered.connect(self.reset_all)
            self.mw.perspectives_menu.addAction(self.mw.reset_perspectives_action)
            
        self.update_current_check()

    @pyqtSlot()
    def update_current_check(self):
        """Updates the checked state of the perspective actions in the menu."""
        found_current = False
        for action in self.mw.perspectives_action_group.actions():
            if action.text() == self.current_perspective_name:
                action.setChecked(True)
                found_current = True
            else:
                action.setChecked(False)
        # If the current perspective somehow became invalid, default to Design Focus
        if not found_current and self.mw.perspectives_action_group.actions():
             default_action = next((a for a in self.mw.perspectives_action_group.actions() if a.text() == self.mw.PERSPECTIVE_DESIGN_FOCUS), None)
             if default_action:
                 default_action.setChecked(True)
                 self.current_perspective_name = self.mw.PERSPECTIVE_DESIGN_FOCUS
                 
    @pyqtSlot(str)
    def apply_perspective(self, perspective_name: str):
        """Applies a predefined or custom perspective layout."""
        if self.current_perspective_name == perspective_name:
            return # No change needed

        logger.info(f"Applying perspective: {perspective_name}")
        
        is_default_perspective = perspective_name in self.mw.DEFAULT_PERSPECTIVES_ORDER

        if is_default_perspective:
            # For default perspectives, ALWAYS apply the hardcoded layout to ensure they are clean.
            self._apply_default_layout(perspective_name)
        else:
            # For user-saved perspectives, try to restore from settings.
            saved_state_hex = self.settings_manager.get(f"perspective_{perspective_name}", None)
            applied = False
            if saved_state_hex and isinstance(saved_state_hex, str):
                try:
                    if self.mw.restoreState(bytes.fromhex(saved_state_hex)):
                        applied = True
                        logger.info(f"Successfully restored user perspective '{perspective_name}'.")
                except ValueError:
                    logger.error(f"Invalid hex string for perspective '{perspective_name}'.")

            if not applied:
                # Fallback if a user perspective fails to load or is invalid
                logger.warning(f"Could not restore user perspective '{perspective_name}'. Applying default layout: '{self.mw.PERSPECTIVE_DESIGN_FOCUS}'.")
                self._apply_default_layout(self.mw.PERSPECTIVE_DESIGN_FOCUS)

        # After applying any perspective, always re-evaluate the central widget.
        self.mw._update_central_widget()

        self.current_perspective_name = perspective_name
        self.settings_manager.set("last_used_perspective", perspective_name)
        self.update_current_check()
        
        # Ensure focus is given appropriately after layout changes
        if self.mw.current_editor():
            self.mw.current_editor().setFocus()

    def _apply_default_layout(self, name: str):
        """Applies a hardcoded layout for a default perspective."""
        
        all_docks = [
            self.mw.project_explorer_dock,
            self.mw.elements_palette_dock, self.mw.properties_dock, self.mw.log_dock,
            self.mw.problems_dock, self.mw.py_sim_dock, self.mw.ai_chatbot_dock, self.mw.ide_dock,
            self.mw.resource_estimation_dock, self.mw.live_preview_dock, self.mw.minimap_dock,
            self.mw.hardware_sim_dock, self.mw.serial_monitor_dock
        ]
        
        # Hide and un-float all docks to start from a clean slate
        for dock in all_docks:
            if dock:
                dock.setFloating(False)
                dock.setVisible(False)

        # 1. Place all docks in their primary areas. This prevents them from appearing floating.
        self.mw.addDockWidget(Qt.LeftDockWidgetArea, self.mw.project_explorer_dock)
        self.mw.addDockWidget(Qt.LeftDockWidgetArea, self.mw.elements_palette_dock)
        
        self.mw.addDockWidget(Qt.RightDockWidgetArea, self.mw.properties_dock)
        self.mw.addDockWidget(Qt.RightDockWidgetArea, self.mw.minimap_dock)
        self.mw.addDockWidget(Qt.RightDockWidgetArea, self.mw.py_sim_dock)
        self.mw.addDockWidget(Qt.RightDockWidgetArea, self.mw.hardware_sim_dock)
        self.mw.addDockWidget(Qt.RightDockWidgetArea, self.mw.ide_dock)
        self.mw.addDockWidget(Qt.RightDockWidgetArea, self.mw.ai_chatbot_dock)

        self.mw.addDockWidget(Qt.BottomDockWidgetArea, self.mw.log_dock)
        self.mw.addDockWidget(Qt.BottomDockWidgetArea, self.mw.problems_dock)
        self.mw.addDockWidget(Qt.BottomDockWidgetArea, self.mw.live_preview_dock)
        self.mw.addDockWidget(Qt.BottomDockWidgetArea, self.mw.resource_estimation_dock)
        self.mw.addDockWidget(Qt.BottomDockWidgetArea, self.mw.serial_monitor_dock)

        # 2. Configure visibility, tabbing, and splitting for the chosen perspective
        main_width = self.mw.width()
        main_height = self.mw.height()

        if name == self.mw.PERSPECTIVE_DESIGN_FOCUS:
            # Layout: Project/Elements on left, Properties/Minimap on right, Log/Problems on bottom.
            self.mw.project_explorer_dock.setVisible(True)
            self.mw.elements_palette_dock.setVisible(True)
            self.mw.properties_dock.setVisible(True)
            self.mw.log_dock.setVisible(True)
            
            self.mw.tabifyDockWidget(self.mw.project_explorer_dock, self.mw.elements_palette_dock)
            
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.minimap_dock)
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.problems_dock)
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.live_preview_dock)
            
            self.mw.project_explorer_dock.raise_()
            self.mw.properties_dock.raise_()
            self.mw.log_dock.raise_()
            
            # Set smaller relative sizes for the dock areas
            # Give ~15% to left dock, ~18% to right dock, leaving ~67% for the center.
            self.mw.resizeDocks([self.mw.project_explorer_dock, self.mw.properties_dock], 
                                [int(main_width * 0.15), int(main_width * 0.18)], 
                                Qt.Horizontal)
            # Give 25% of the remaining vertical space to the bottom dock
            self.mw.resizeDocks([self.mw.log_dock], [int(main_height * 0.25)], Qt.Vertical)

        elif name == self.mw.PERSPECTIVE_LOGIC_EDITING:
            # Layout: Large properties panel on the right, large code preview on the bottom.
            self.mw.properties_dock.setVisible(True)
            self.mw.live_preview_dock.setVisible(True)
            self.mw.log_dock.setVisible(True) # Tabbed with preview

            self.mw.tabifyDockWidget(self.mw.live_preview_dock, self.mw.log_dock)
            self.mw.tabifyDockWidget(self.mw.live_preview_dock, self.mw.problems_dock)

            self.mw.properties_dock.raise_()
            self.mw.live_preview_dock.raise_()

            # Give a large area to the properties panel and the code preview
            self.mw.resizeDocks([self.mw.properties_dock], [int(main_width * 0.35)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.live_preview_dock], [int(main_height * 0.35)], Qt.Vertical)

        elif name == self.mw.PERSPECTIVE_VALIDATION:
            # Layout: Problems list is prominent at the bottom, Properties are visible on the right.
            self.mw.problems_dock.setVisible(True)
            self.mw.properties_dock.setVisible(True)
            self.mw.minimap_dock.setVisible(True) # For navigation

            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.minimap_dock)
            self.mw.tabifyDockWidget(self.mw.problems_dock, self.mw.log_dock)

            self.mw.properties_dock.raise_()
            self.mw.problems_dock.raise_()
            
            self.mw.resizeDocks([self.mw.properties_dock], [int(main_width * 0.25)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.problems_dock], [int(main_height * 0.30)], Qt.Vertical)

        elif name == self.mw.PERSPECTIVE_SIMULATION_FOCUS:
            # Layout: Split right dock vertically. Top: Sim controls. Bottom: Properties.
            # Bottom dock shows Log for real-time feedback.
            self.mw.py_sim_dock.setVisible(True)
            self.mw.properties_dock.setVisible(True)
            self.mw.log_dock.setVisible(True)
            
            self.mw.splitDockWidget(self.mw.py_sim_dock, self.mw.properties_dock, Qt.Vertical)
            self.mw.tabifyDockWidget(self.mw.py_sim_dock, self.mw.hardware_sim_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.minimap_dock)
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.serial_monitor_dock)

            self.mw.py_sim_dock.raise_()
            self.mw.properties_dock.raise_()
            self.mw.log_dock.raise_()

            self.mw.resizeDocks([self.mw.py_sim_dock], [int(main_width * 0.25)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.log_dock], [int(main_height * 0.30)], Qt.Vertical)

        elif name == self.mw.PERSPECTIVE_PRESENTATION:
            # Layout: Zen mode. All docks are hidden by the initial loop.
            pass

        elif name == self.mw.PERSPECTIVE_IDE_FOCUS:
            # Layout: IDE takes up the right side, tabbed with AI Chat. Log visible at bottom.
            self.mw.ide_dock.setVisible(True)
            self.mw.log_dock.setVisible(True)

            self.mw.tabifyDockWidget(self.mw.ide_dock, self.mw.ai_chatbot_dock)
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.serial_monitor_dock)
            
            self.mw.ide_dock.raise_()
            self.mw.log_dock.raise_()

            self.mw.resizeDocks([self.mw.ide_dock], [int(main_width * 0.40)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.log_dock], [int(main_height * 0.25)], Qt.Vertical)

        elif name == self.mw.PERSPECTIVE_AI_FOCUS:
            # Layout: AI Chat prominent on the right, Log visible at the bottom.
            self.mw.ai_chatbot_dock.setVisible(True)
            self.mw.log_dock.setVisible(True)
            
            self.mw.tabifyDockWidget(self.mw.ai_chatbot_dock, self.mw.ide_dock)
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.serial_monitor_dock)
            
            self.mw.ai_chatbot_dock.raise_()
            self.mw.log_dock.raise_()

            self.mw.resizeDocks([self.mw.ai_chatbot_dock], [int(main_width * 0.30)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.log_dock], [int(main_height * 0.30)], Qt.Vertical)
        
        elif name == self.mw.PERSPECTIVE_DEVELOPER_VIEW:
            # Show everything in a logical tabbed layout
            self.mw.elements_palette_dock.setVisible(True)
            self.mw.properties_dock.setVisible(True)
            self.mw.log_dock.setVisible(True)
            
            # Tabify right-side docks
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.minimap_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.py_sim_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.hardware_sim_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.ide_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.ai_chatbot_dock)
            
            # Tabify bottom-side docks
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.problems_dock)
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.live_preview_dock)
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.resource_estimation_dock)
            self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.serial_monitor_dock)
            
            self.mw.properties_dock.raise_()
            self.mw.log_dock.raise_()
            
            self.mw.resizeDocks([self.mw.elements_palette_dock], [int(main_width * 0.15)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.properties_dock], [int(main_width * 0.25)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.log_dock], [int(main_height * 0.25)], Qt.Vertical)

        else: # Fallback to a safe default
            self._apply_default_layout(self.mw.PERSPECTIVE_DESIGN_FOCUS)
            
    @pyqtSlot()
    def save_current_as(self):
        """Saves the current layout as a new custom perspective."""
        name, ok = QInputDialog.getText(self.mw, "Save Perspective", "Enter name for this perspective:", QLineEdit.Normal, self.current_perspective_name)
        if not (ok and name.strip()): return
        
        name = name.strip()
        is_default = name in self.mw.DEFAULT_PERSPECTIVES_ORDER
        user_perspectives = self.settings_manager.get("user_perspective_names", [])
        
        if not is_default and name not in user_perspectives:
            user_perspectives.append(name)
            self.settings_manager.set("user_perspective_names", sorted(user_perspectives))
        
        # Save the current dock state
        state_hex = self.mw.saveState().toHex().data().decode('ascii')
        self.settings_manager.set(f"perspective_{name}", state_hex)
        
        self.populate_menu() # Refresh menu with new perspective
        self.apply_perspective(name) # Apply it immediately

    @pyqtSlot()
    def reset_all(self):
        """Resets all perspectives (deletes custom ones, restores defaults)."""
        reply = QMessageBox.question(self.mw, "Reset All Perspectives", "This will delete all custom saved layouts and reset perspectives to defaults. Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return
            
        all_names_to_clear = self.settings_manager.get("user_perspective_names", []) + self.mw.DEFAULT_PERSPECTIVES_ORDER
        
        for name in all_names_to_clear:
            self.settings_manager.remove_setting(f"perspective_{name}", save_immediately=False)
        
        self.settings_manager.set("user_perspective_names", []) # Clear user list
        self.settings_manager.save_settings() # Save the change
        
        self.populate_menu() # Refresh menu
        self.apply_perspective(self.mw.PERSPECTIVE_DESIGN_FOCUS) # Reset to default layout
        QMessageBox.information(self.mw, "Perspectives Reset", "All custom perspectives have been removed and defaults restored.")