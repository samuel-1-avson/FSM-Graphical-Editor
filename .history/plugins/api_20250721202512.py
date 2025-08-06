# fsm_designer_project/plugins/api.py
from abc import ABC, abstractmethod
from typing import Dict, Optional

class BsmExporterPlugin(ABC):
    """
    Abstract Base Class for all FSM Designer Exporter plugins.
    
    To create a new exporter, create a new Python file in the 'plugins'
    directory and define a class that inherits from this one.
    The main application will automatically discover and load it.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The user-friendly name of the exporter to show in the menu.
        Example: "SCXML (State Chart XML)"
        """
        pass

    @property
    @abstractmethod
    def file_filter(self) -> str:
        """
        The file filter for the save dialog.
        Example: "SCXML Files (*.scxml);;XML Files (*.xml)"
        """
        pass

    @abstractmethod
    def export(self, diagram_data: Dict) -> str:
        """
        The core export logic. This method takes the FSM diagram data
        as a dictionary and must return the full file content as a string.

        Args:
            diagram_data: A dictionary containing 'states', 'transitions', etc.

        Returns:
            A string containing the content of the file to be saved.
        """
        pass

# --- NEW IMPORTER API CLASS ---
class BsmImporterPlugin(ABC):
    """
    Abstract Base Class for FSM Designer Importer plugins.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The user-friendly name of the importer. Example: 'PlantUML Diagram'"""
        pass

    @property
    @abstractmethod
    def file_filter(self) -> str:
        """The file filter for the open dialog. Example: 'PlantUML Files (*.puml *.plantuml)'"""
        pass

    @abstractmethod
    def import_data(self, file_content: str) -> Optional[Dict]:
        """
        The core import logic. Takes file content as a string and must return
        the standard FSM diagram data dictionary, or None on failure.

        Args:
            file_content: A string containing the content of the file to be imported.

        Returns:
            A dictionary with 'states', 'transitions', etc., or None if parsing fails.
        """
        pass
# --- END NEW ---