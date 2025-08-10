# fsm_designer_project/actions/help_actions.py
import logging
from PyQt6.QtCore import QObject, pyqtSlot

logger = logging.getLogger(__name__)

class HelpActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    def on_show_quick_start(self):
        self.mw.action_handler.file_handler.on_show_quick_start()
        
    @pyqtSlot()
    def on_about(self):
        self.mw.action_handler.file_handler.on_about()

    @pyqtSlot()
    def on_show_system_info(self):
        self.mw.action_handler.file_handler.on_show_system_info()
        
    @pyqtSlot()
    def on_customize_quick_access(self):
        from ..ui.dialogs import QuickAccessSettingsDialog
        dialog = QuickAccessSettingsDialog(self.mw, self.mw.settings_manager, self.mw)
        if dialog.exec():
            new_command_list = dialog.get_new_command_list()
            self.mw.settings_manager.set("quick_access_commands", new_command_list)
            if hasattr(self.mw, 'ui_manager') and hasattr(self.mw.ui_manager, '_populate_quick_access_toolbar'):
                self.mw.ui_manager._populate_quick_access_toolbar()
            self.mw.log_message("INFO", "Quick Access Toolbar updated.")