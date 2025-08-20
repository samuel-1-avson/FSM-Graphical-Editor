# fsm_designer_project/plugins/api.py
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

class BsmPluginBase(ABC):
    """
    A common base for all FSM Designer plugins, providing optional lifecycle
    hooks and metadata.
    """

    @property
    def version(self) -> str:
        """
        The version of the plugin, e.g., "1.0.0".
        This can be used for compatibility checks in future versions of the
        application to ensure plugins remain compatible.

        Returns:
            A version string. Defaults to "1.0.0".
        """
        return "1.0.0"

    def setup(self, main_window: Any):
        """
        Optional method called once when the plugin is loaded by the PluginManager.
        
        This hook allows a plugin to perform initialization tasks, such as:
        - Adding custom menu items to the main window's menu bar.
        - Connecting to global signals via the `signal_bus`.
        - Setting up resources that the plugin might need.

        Args:
            main_window: A reference to the application's MainWindow instance. This
                         provides access to UI elements and core managers.
        """
        pass

    def teardown(self):
        """
        Optional method called once when the application is closing.
        
        Use this hook to perform any necessary cleanup, such as:
        - Disconnecting signals.
        - Closing files or network connections.
        - Releasing resources.
        """
        pass


class BsmExporterPlugin(BsmPluginBase):
    """
    Abstract Base Class for all FSM Designer Exporter plugins.
    
    To create a new exporter, create a new Python file in the 'plugins'
    directory and define a class that inherits from this one. The main
    application will automatically discover and load it.
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
        The file filter for the save dialog, defining the file types this
        exporter can create.
        Example: "SCXML Files (*.scxml);;XML Files (*.xml)"
        """
        pass

    @abstractmethod
    def export(self, diagram_data: Dict, **kwargs) -> Dict[str, str]:
        """
        The core export logic. This method takes the FSM diagram data
        as a dictionary and must return a dictionary mapping filenames
        to their string content.

        Args:
            diagram_data: A dictionary containing 'states', 'transitions', etc.
            **kwargs: Additional, exporter-specific arguments. A common one is
                      'base_filename', which the main application provides from
                      the save dialog.

        Returns:
            A dictionary where keys are suggested filenames (e.g., "fsm.c")
            and values are the file contents as strings. For single-file
            exporters, this dictionary will contain one entry.
        """
        pass


class BsmImporterPlugin(BsmPluginBase):
    """
    Abstract Base Class for all FSM Designer Importer plugins.

    To create a new importer, inherit from this class. The application will
    automatically discover and integrate it into the 'Open File' dialog.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The user-friendly name of the importer.
        Example: 'PlantUML Diagram'
        """
        pass

    @property
    @abstractmethod
    def file_filter(self) -> str:
        """
        The file filter for the open dialog. This determines which file
        extensions will trigger this importer.
        Example: 'PlantUML Files (*.puml *.plantuml)'
        """
        pass

    @abstractmethod
    def import_data(self, file_content: str) -> Optional[Dict]:
        """
        The core import logic. This method takes the file content as a string
        and must return a standard FSM diagram data dictionary, or None if
        the parsing fails.

        The returned dictionary should be in the same format as a .bsm file,
        containing 'states', 'transitions', and 'comments' keys.

        Args:
            file_content: A string containing the entire content of the file
                          to be imported.

        Returns:
            A dictionary with 'states', 'transitions', etc., or None if parsing fails.
            The calling ActionHandler will display an error to the user upon failure.
        """
        pass