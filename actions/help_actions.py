# fsm_designer_project/actions/help_actions.py
import logging
from PyQt6.QtCore import QObject, pyqtSlot, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QMessageBox
from ..utils import _get_bundled_file_path

# --- MODIFIED IMPORTS ---
from ..utils import config
from ..ui.dialogs import SystemInfoDialog

logger = logging.getLogger(__name__)

class HelpActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    def on_show_quick_start(self):
        """Finds and opens the QUICK_START.html file in the default web browser."""
        quick_start_path = _get_bundled_file_path("QUICK_START.html", resource_prefix="docs")
        if quick_start_path:
            url = QUrl.fromLocalFile(quick_start_path)
            if not QDesktopServices.openUrl(url):
                QMessageBox.warning(self.mw, "Could Not Open Guide", f"Failed to open the Quick Start Guide in your browser:\n{quick_start_path}")
        else:
            QMessageBox.critical(self.mw, "File Not Found", "The Quick Start Guide (QUICK_START.html) could not be found.")
        
    @pyqtSlot()
    def on_about(self):
        # --- FIX: Implement the 'About' dialog logic here directly ---
        about_text = f"""
            <h2>{config.APP_NAME}</h2>
            <p>Version: {config.APP_VERSION}</p>
            <p>A graphical editor for designing, simulating, and generating code for Finite State Machines.</p>
            <p>Built with Python and PyQt6.</p>
            <p>&copy; 2024 BSM-Devs. All rights reserved.</p>
        """
        QMessageBox.about(self.mw, f"About {config.APP_NAME}", about_text)

    @pyqtSlot()
    def on_show_system_info(self):
        # --- FIX: Implement the 'System Info' dialog logic here directly ---
        dialog = SystemInfoDialog(self.mw)
        dialog.exec()
        
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