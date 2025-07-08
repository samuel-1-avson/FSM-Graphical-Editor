# fsm_designer_project/plugin_manager.py
import os
import importlib
import inspect
import logging
from .plugins.api import BsmExporterPlugin

logger = logging.getLogger(__name__)
PLUGIN_SUBDIR = "plugins"

class PluginManager:
    def __init__(self):
        self.exporter_plugins = []
        self._discover_plugins()

    def _discover_plugins(self):
        """Dynamically discovers and loads exporter plugins."""
        self.exporter_plugins.clear()
        
        # Get the path to the plugins subdirectory
        plugins_path = os.path.join(os.path.dirname(__file__), PLUGIN_SUBDIR)
        if not os.path.isdir(plugins_path):
            logger.warning(f"Plugin directory not found at '{plugins_path}'. No plugins will be loaded.")
            return

        for filename in os.listdir(plugins_path):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                try:
                    # Dynamically import the module
                    module = importlib.import_module(f".{PLUGIN_SUBDIR}.{module_name}", package="fsm_designer_project")
                    
                    # Find all classes in the module that are subclasses of our plugin API
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BsmExporterPlugin) and obj is not BsmExporterPlugin:
                            try:
                                plugin_instance = obj() # Create an instance of the plugin
                                self.exporter_plugins.append(plugin_instance)
                                logger.info(f"Successfully loaded exporter plugin: '{plugin_instance.name}'")
                            except Exception as e:
                                logger.error(f"Failed to instantiate plugin '{name}' from module '{module_name}': {e}", exc_info=True)

                except ImportError as e:
                    logger.error(f"Failed to import plugin module '{module_name}': {e}", exc_info=True)
        
        # Sort plugins alphabetically by name for a consistent menu order
        self.exporter_plugins.sort(key=lambda p: p.name)