# fsm_designer_project/actions/view_actions.py
import logging
from PyQt6.QtCore import QObject, pyqtSlot

logger = logging.getLogger(__name__)

class ViewActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    def on_zoom_in(self):
        if editor := self.mw.current_editor():
            editor.view.zoom_in()

    @pyqtSlot()
    def on_zoom_out(self):
        if editor := self.mw.current_editor():
            editor.view.zoom_out()

    @pyqtSlot()
    def on_reset_zoom(self):
        if editor := self.mw.current_editor():
            editor.view.reset_view_and_zoom()

    @pyqtSlot(str, bool)
    def on_toggle_view_setting(self, key: str, checked: bool):
        if self.mw.settings_manager:
            self.mw.settings_manager.set(key, checked)
        else:
            logger.error(f"Cannot toggle view setting '{key}': SettingsManager not available.")

    @pyqtSlot()
    def on_zoom_to_selection(self):
        if editor := self.mw.current_editor():
            if hasattr(editor.view, 'zoom_to_selection'):
                editor.view.zoom_to_selection()

    @pyqtSlot()
    def on_fit_diagram_in_view(self):
        if editor := self.mw.current_editor():
            if hasattr(editor.view, 'fit_diagram_in_view'):
                editor.view.fit_diagram_in_view()

    @pyqtSlot()
    def on_auto_layout_diagram(self):
        self.mw.action_handler.edit_handler.on_auto_layout_diagram()