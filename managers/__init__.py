# fsm_designer_project/managers/__init__.py
"""
Initializes the 'managers' package and exposes its primary classes.

This allows for cleaner imports, e.g., 'from ..managers import SettingsManager'
instead of 'from ..managers.settings_manager import SettingsManager'.
"""

from .action_handlers import ActionHandler
from .ide_manager import IDEManager
from .perspective_manager import PerspectiveManager
from .plugin_manager import PluginManager
from .project_manager import ProjectManager
from .resource_monitor import ResourceMonitorManager
from .settings_manager import SettingsManager
from .theme_manager import ThemeManager
from .ui_manager import UIManager

__all__ = [
    "ActionHandler",
    "IDEManager",
    "PerspectiveManager",
    "PluginManager",
    "ProjectManager",
    "ResourceMonitorManager",
    "SettingsManager",
    "ThemeManager",
    "UIManager",
]