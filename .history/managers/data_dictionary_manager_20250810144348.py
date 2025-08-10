# fsm_designer_project/managers/data_dictionary_manager.py

import logging
import os
import json
from PyQt6.QtCore import QObject
# --- MODIFIED: Import the signal bus ---
from .signal_bus import signal_bus
from .project_manager import ProjectManager

logger = logging.getLogger(__name__)
DATA_DICT_FILENAME = "data_dictionary.json"

class DataDictionaryManager(QObject):
    """
    Manages the data dictionary for a project. This includes loading, saving,
    and providing access to the project-specific variables.
    """
    # --- REMOVED: Signal is now on the bus ---
    # dictionary_changed = pyqtSignal()

    def __init__(self, project_manager: ProjectManager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.variables = {}
        
        # --- MODIFIED: Listen to the signal bus ---
        signal_bus.project_loaded.connect(self.load)
        signal_bus.project_closed.connect(self.clear)

    def _get_dictionary_path(self) -> str | None:
        if not self.project_manager.is_project_open():
            return None
        return os.path.join(os.path.dirname(self.project_manager.current_project_path), DATA_DICT_FILENAME)
        
    def load(self):
        """Loads the data dictionary from the project directory."""
        path = self._get_dictionary_path()
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.variables = json.load(f)
                logger.info(f"Data dictionary loaded from {path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading data dictionary: {e}")
                self.variables = {}
        else:
            self.variables = {}
        # --- MODIFIED: Emit signal on the bus ---
        signal_bus.status_message_posted.emit("INFO", "Data Dictionary updated.")

    def save(self):
        """Saves the data dictionary to the project directory."""
        path = self._get_dictionary_path()
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.variables, f, indent=4)
            logger.info(f"Data dictionary saved to {path}")
            # --- MODIFIED: Emit signal on the bus ---
            signal_bus.status_message_posted.emit("INFO", "Data Dictionary saved.")
        except IOError as e:
            logger.error(f"Error saving data dictionary: {e}")

    def clear(self):
        """Clears the current data dictionary."""
        self.variables = {}
        # --- MODIFIED: Emit signal on the bus ---
        signal_bus.status_message_posted.emit("INFO", "Data Dictionary cleared.")