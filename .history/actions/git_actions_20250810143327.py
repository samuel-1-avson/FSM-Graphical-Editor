# fsm_designer_project/actions/git_actions.py
import logging
from PyQt6.QtCore import QObject, pyqtSlot

logger = logging.getLogger(__name__)

class GitActionHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window

    @pyqtSlot()
    def on_git_commit(self):
        self.mw.action_handler.file_handler.on_git_commit()

    @pyqtSlot()
    def on_git_push(self):
        self.mw.action_handler.file_handler.on_git_push()
        
    @pyqtSlot()
    def on_git_pull(self):
        self.mw.action_handler.file_handler.on_git_pull()
        
    @pyqtSlot()
    def on_git_show_changes(self):
        self.mw.action_handler.file_handler.on_git_show_changes()