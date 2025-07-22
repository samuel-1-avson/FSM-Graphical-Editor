# fsm_designer_project/plugins/api.py
from abc import ABC, abstractmethod
from typing import Dict

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