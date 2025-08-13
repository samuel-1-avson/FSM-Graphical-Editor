# fsm_designer_project/managers/plugin_manager.py
import os
import importlib
import inspect
import logging
# --- MODIFIED IMPORT ---
from ..plugins.api import BsmExporterPlugin, BsmImporterPlugin

logger = logging.getLogger(__name__)
PLUGIN_SUBDIR = "plugins"

class PluginManager:
    def __init__(self):
        self.exporter_plugins = []
        self.importer_plugins = [] # --- ADD THIS LINE ---
        self._discover_plugins()

    def _discover_plugins(self):
        """Dynamically discovers and loads all plugins."""
        self.exporter_plugins.clear()
        self.importer_plugins.clear() # --- ADD THIS LINE ---
        
        plugins_path = os.path.join(os.path.dirname(__file__), '..', PLUGIN_SUBDIR)
        if not os.path.isdir(plugins_path):
            logger.warning(f"Plugin directory not found at '{plugins_path}'. No plugins will be loaded.")
            return

        for filename in os.listdir(plugins_path):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f"..{PLUGIN_SUBDIR}.{module_name}", package="fsm_designer_project.managers")
                    
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # --- FIX: Add discovery logic for importer plugins ---
                        # Check for Exporter plugins
                        if issubclass(obj, BsmExporterPlugin) and obj is not BsmExporterPlugin:
                            try:
                                plugin_instance = obj()
                                self.exporter_plugins.append(plugin_instance)
                                logger.info(f"Successfully loaded exporter plugin: '{plugin_instance.name}'")
                            except Exception as e:
                                logger.error(f"Failed to instantiate exporter plugin '{name}': {e}", exc_info=True)

                        # Check for Importer plugins
                        if issubclass(obj, BsmImporterPlugin) and obj is not BsmImporterPlugin:
                            try:
                                plugin_instance = obj()
                                self.importer_plugins.append(plugin_instance)
                                logger.info(f"Successfully loaded importer plugin: '{plugin_instance.name}'")
                            except Exception as e:
                                logger.error(f"Failed to instantiate importer plugin '{name}': {e}", exc_info=True)
                        # --- END FIX ---

                except ImportError as e:
                    logger.error(f"Failed to import plugin module '{module_name}': {e}", exc_info=True)
        
        self.exporter_plugins.sort(key=lambda p: p.name)
        self.importer_plugins.sort(key=lambda p: p.name) # --- ADD THIS LINE ---