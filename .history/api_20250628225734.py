# In a new plugins/api.py
from abc import ABC, abstractmethod

class BsmExporterPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the exporter to show in the menu."""
        pass

    @property
    @abstractmethod
    def file_filter(self) -> str:
        """The file filter for the save dialog, e.g., 'VHDL Files (*.vhd)'."""
        pass

    @abstractmethod
    def export(self, diagram_data: dict) -> str:
        """Takes diagram data and returns the file content as a string."""
        pass