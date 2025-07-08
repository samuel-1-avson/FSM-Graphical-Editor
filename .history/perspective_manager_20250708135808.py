# fsm_designer_project/perspective_manager.py
import logging
from PyQt5.QtCore import QObject, pyqtSlot, Qt
from PyQt5.QtWidgets import QActionGroup, QMessageBox, QInputDialog, QLineEdit, QMainWindow

logger = logging.getLogger(__name__)

class PerspectiveManager(QObject):
    def __init__(self, main_window: QMainWindow, settings_manager, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self.settings_manager = settings_manager

        self.mw.perspectives_action_group = QActionGroup(self.mw)
        
        self.current_perspective_name = self.settings_manager.get(
            "last_used_perspective", self.mw.PERSPECTIVE_DESIGN_FOCUS
        )
        self.populate_menu()

    @pyqtSlot()
    def populate_menu(self):
        menu = self.mw.perspectives_menu
        if not menu:
            logger.error("Perspectives menu not found in MainWindow.")
            return
            
        menu.clear()
        for action in self.mw.perspectives_action_group.actions():
            self.mw.perspectives_action_group.removeAction(action)
            
        for p_name in self.mw.DEFAULT_PERSPECTIVES_ORDER:
            action = menu.addAction(p_name)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, name=p_name: self.apply_perspective(name))
            self.mw.perspectives_action_group.addAction(action)

        menu.addSeparator()

        user_perspective_names = self.settings_manager.get("user_perspective_names", [])
        if user_perspective_names:
            for p_name in sorted(user_perspective_names):
                action = menu.addAction(p_name)
                action.setCheckable(True)
                action.triggered.connect(lambda checked=False, name=p_name: self.apply_perspective(name))
                self.mw.perspectives_action_group.addAction(action)
            menu.addSeparator()

        menu.addAction(self.mw.save_perspective_action)
        menu.addAction(self.mw.reset_perspectives_action)
        self.update_current_check()
        
    def update_current_check(self):
        found_current = False
        for action in self.mw.perspectives_action_group.actions():
            if action.text() == self.current_perspective_name:
                action.setChecked(True)
                found_current = True
            else:
                action.setChecked(False)
        if not found_current and self.mw.perspectives_action_group.actions():
             pass 

    @pyqtSlot(str)
    def apply_perspective(self, perspective_name: str):
        logger.info(f"Applying perspective: {perspective_name}")
        saved_state_hex = self.settings_manager.get(f"perspective_{perspective_name}", None)

        applied = False
        if saved_state_hex and isinstance(saved_state_hex, str):
            try:
                if self.mw.restoreState(bytes.fromhex(saved_state_hex)):
                    applied = True
            except ValueError:
                logger.error(f"Invalid hex string for perspective '{perspective_name}'.")

        if not applied:
            self._apply_default_layout(perspective_name)

        self.current_perspective_name = perspective_name
        self.settings_manager.set("last_used_perspective", perspective_name)
        self.update_current_check()

    def _apply_default_layout(self, name: str):
        logger.info(f"Applying default programmatic layout for perspective: '{name}'")

        all_docks = [
            self.mw.elements_palette_dock, self.mw.properties_dock, self.mw.log_dock,
            self.mw.problems_dock, self.mw.py_sim_dock, self.mw.ai_chatbot_dock, self.mw.ide_dock,
            self.mw.resource_estimation_dock, self.mw.live_preview_dock, self.mw.minimap_dock,
            self.mw.hardware_sim_dock
        ]
        
        # Hide and un-float all docks to start from a clean slate
        for dock in all_docks:
            if dock:
                dock.setFloating(False)
                dock.setVisible(False)

        # --- REWORKED LOGIC ---
        # Add all docks to their preferred areas first, then control visibility and tabbing
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

        # Common setup: Tabify all bottom docks, with Log being the default visible
        self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.problems_dock)
        self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.live_preview_dock)
        self.mw.tabifyDockWidget(self.mw.log_dock, self.mw.resource_estimation_dock)
        self.mw.log_dock.setVisible(True)
        self.mw.log_dock.raise_()

        main_width = self.mw.width()

        # Configure visibility and tabbing for each perspective
        if name == self.mw.PERSPECTIVE_DESIGN_FOCUS:
            self.mw.elements_palette_dock.setVisible(True)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.minimap_dock)
            self.mw.properties_dock.setVisible(True)
            self.mw.properties_dock.raise_()
            self.mw.resizeDocks([self.mw.elements_palette_dock], [int(main_width * 0.15)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.properties_dock], [int(main_width * 0.20)], Qt.Horizontal)

        elif name == self.mw.PERSPECTIVE_SIMULATION_FOCUS:
            self.mw.tabifyDockWidget(self.mw.py_sim_dock, self.mw.properties_dock)
            self.mw.tabifyDockWidget(self.mw.py_sim_dock, self.mw.minimap_dock)
            self.mw.tabifyDockWidget(self.mw.py_sim_dock, self.mw.hardware_sim_dock)
            self.mw.py_sim_dock.setVisible(True)
            self.mw.py_sim_dock.raise_()
            self.mw.resizeDocks([self.mw.py_sim_dock], [int(main_width * 0.30)], Qt.Horizontal)

        elif name == self.mw.PERSPECTIVE_IDE_FOCUS:
            self.mw.tabifyDockWidget(self.mw.ide_dock, self.mw.ai_chatbot_dock)
            self.mw.tabifyDockWidget(self.mw.ide_dock, self.mw.properties_dock)
            self.mw.ide_dock.setVisible(True)
            self.mw.ide_dock.raise_()
            self.mw.resizeDocks([self.mw.ide_dock], [int(main_width * 0.45)], Qt.Horizontal)

        elif name == self.mw.PERSPECTIVE_AI_FOCUS:
            self.mw.tabifyDockWidget(self.mw.ai_chatbot_dock, self.mw.properties_dock)
            self.mw.ai_chatbot_dock.setVisible(True)
            self.mw.ai_chatbot_dock.raise_()
            self.mw.resizeDocks([self.mw.ai_chatbot_dock], [int(main_width * 0.35)], Qt.Horizontal)
        
        elif name == self.mw.PERSPECTIVE_DEVELOPER_VIEW:
            # Show everything in a logical tabbed layout
            self.mw.elements_palette_dock.setVisible(True)
            self.mw.properties_dock.setVisible(True)
            
            # Tabify right-side docks
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.minimap_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.py_sim_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.hardware_sim_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.ide_dock)
            self.mw.tabifyDockWidget(self.mw.properties_dock, self.mw.ai_chatbot_dock)
            
            self.mw.properties_dock.raise_()
            self.mw.resizeDocks([self.mw.elements_palette_dock], [int(main_width * 0.15)], Qt.Horizontal)
            self.mw.resizeDocks([self.mw.properties_dock], [int(main_width * 0.30)], Qt.Horizontal)

        else: # Fallback to a safe default
            self._apply_default_layout(self.mw.PERSPECTIVE_DESIGN_FOCUS)
            
    @pyqtSlot()
    def save_current_as(self):
        name, ok = QInputDialog.getText(self.mw, "Save Perspective", "Enter name:", QLineEdit.Normal, self.current_perspective_name)
        if not (ok and name): return
        
        is_default = name in self.mw.DEFAULT_PERSPECTIVES_ORDER
        user_perspectives = self.settings_manager.get("user_perspective_names", [])
        
        if not is_default and name not in user_perspectives:
            user_perspectives.append(name)
            self.settings_manager.set("user_perspective_names", sorted(user_perspectives))
        
        state_hex = self.mw.saveState().toHex().data().decode('ascii')
        self.settings_manager.set(f"perspective_{name}", state_hex)
        self.populate_menu()
        self.apply_perspective(name)
    
    @pyqtSlot()
    def reset_all(self):
        reply = QMessageBox.question(self.mw, "Reset All Perspectives", "This will delete all custom layouts and reset default ones. Are you sure?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes: return
            
        all_names = self.settings_manager.get("user_perspective_names", []) + self.mw.DEFAULT_PERSPECTIVES_ORDER
        for name in all_names:
            self.settings_manager.remove_setting(f"perspective_{name}", save_immediately=False)
        self.settings_manager.set("user_perspective_names", [])
        
        self.populate_menu()
        self.apply_perspective(self.mw.PERSPECTIVE_DESIGN_FOCUS)
        QMessageBox.information(self.mw, "Perspectives Reset", "All layouts have been reset.")