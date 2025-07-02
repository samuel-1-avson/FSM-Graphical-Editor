# fsm_designer_project/settings_manager.py

import json
import os
import logging
from PyQt5.QtCore import QObject, QStandardPaths, pyqtSignal, QDir, Qt, QSettings
from PyQt5.QtGui import QColor

logger = logging.getLogger(__name__)

class SettingsManager(QObject):
    settingChanged = pyqtSignal(str, object)

    DEFAULTS = {
        # View settings
        "view_show_grid": True,
        "view_snap_to_grid": True,
        "view_snap_to_objects": True,
        "view_show_snap_guidelines": True,
        "grid_size": 20,

        # Behavior settings
        "resource_monitor_enabled": True,
        "resource_monitor_interval_ms": 2000,
        "autosave_enabled": False,
        "autosave_interval_minutes": 5,
        "recent_files": [],

        # Appearance settings
        "appearance_theme": "Dark", # CHANGED: "Light" -> "Dark"
        "canvas_grid_minor_color": "#455A64", # Updated to match dark theme default
        "canvas_grid_major_color": "#546E7A", # Updated to match dark theme default
        "canvas_snap_guideline_color": "#E57373", # Updated to a visible color on dark theme

        # Default Item Visuals (These are user preferences, separate from themes)
        "state_default_shape": "rectangle",
        "state_default_font_family": "Segoe UI, Arial, sans-serif",
        "state_default_font_size": 10,
        "state_default_font_