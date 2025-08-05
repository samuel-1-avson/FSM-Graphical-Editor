# fsm_designer_project/managers/project_manager.py
# (This file is being moved from core/ to managers/)
import os
import json
import logging
from PyQt5.QtCore import QObject, pyqtSignal
from ..utils.config import PROJECT_FILE_EXTENSION, PROJECT_FILE_FILTER

logger = logging.getLogger(__name__)

class ProjectManager(QObject):
    """Manages the creation, loading, and saving of project files."""

    project_loaded = pyqtSignal(str, dict)  # path, project_data
    project_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project_path: str | None = None
        self.project_data: dict = {}

    def is_project_open(self) -> bool:
        return self.current_project_path is not None

    def create_new_project(self, project_path: str, project_name: str, main_diagram_filename: str) -> bool:
        """Creates the .bsmproj file and its initial structure."""
        if not project_path.endswith(PROJECT_FILE_EXTENSION):
            project_path += PROJECT_FILE_EXTENSION

        project_dir = os.path.dirname(project_path)
        
        try:
            os.makedirs(project_dir, exist_ok=True)
            
            # Create a default empty diagram file
            main_diagram_path = os.path.join(project_dir, main_diagram_filename)
            if not os.path.exists(main_diagram_path):
                with open(main_diagram_path, 'w', encoding='utf-8') as f:
                    json.dump({"states": [], "transitions": [], "comments": []}, f, indent=4)

            self.project_data = {
                "version": "1.0",
                "name": project_name,
                "main_diagram": main_diagram_filename,
                # Future additions: list of other files, project settings, etc.
            }

            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, indent=4)
            
            self.current_project_path = project_path
            logger.info(f"Successfully created new project at: {project_path}")
            self.project_loaded.emit(project_path, self.project_data)
            return True

        except (IOError, OSError) as e:
            logger.error(f"Error creating new project at '{project_path}': {e}", exc_info=True)
            self.close_project()
            return False

    def load_project(self, project_path: str) -> bool:
        """Loads a project from a .bsmproj file."""
        if not os.path.exists(project_path):
            logger.error(f"Project file not found: {project_path}")
            return False
        try:
            with open(project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Basic validation
            if "name" not in data or "main_diagram" not in data:
                logger.error("Invalid project file: missing 'name' or 'main_diagram' key.")
                return False

            self.project_data = data
            self.current_project_path = project_path
            logger.info(f"Successfully loaded project: {data['name']}")
            self.project_loaded.emit(project_path, self.project_data)
            return True

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading project file '{project_path}': {e}", exc_info=True)
            self.close_project()
            return False

    # Add this new method inside the ProjectManager class
    def save_project(self) -> bool:
        """Saves the current project data to its file path."""
        if not self.is_project_open():
            logger.warning("Attempted to save project, but no project is open.")
            return False
        
        try:
            with open(self.current_project_path, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, indent=4)
            logger.info(f"Project saved successfully to: {self.current_project_path}")
            return True
        except (IOError, TypeError) as e:
            logger.error(f"Error saving project to '{self.current_project_path}': {e}", exc_info=True)
            return False


    def close_project(self):
        """Closes the current project."""
        if self.is_project_open():
            logger.info(f"Closing project: {self.project_data.get('name')}")
            self.current_project_path = None
            self.project_data = {}
            self.project_closed.emit()