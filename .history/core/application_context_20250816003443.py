# fsm_designer_project/core/application_context.py
"""
Defines the ApplicationContext which holds core, non-GUI services.
"""
from ..services import MatlabConnection
from ..managers import SettingsManager, ThemeManager, PluginManager, AssetManager

class ApplicationContext:
    """
    Holds all application-wide services and managers that do not directly
    depend on the main GUI window. This object serves as a service container
    that can be passed to the MainWindow or used in other contexts (e.g., testing).
    """
    def __init__(self, app_name: str):
        # These managers have no direct UI dependencies and can be created first.
        self.settings_manager = SettingsManager(app_name=app_name)
        self.theme_manager = ThemeManager(app_name=app_name)
        self.plugin_manager = PluginManager()
        self.asset_manager = AssetManager(app_name=app_name)
        
        # External services
        self.matlab_connection = MatlabConnection()
        
        # Placeholder for managers that will be created by MainWindow
        # but can be stored here for easy access by other services if needed.
        self.project_manager = None