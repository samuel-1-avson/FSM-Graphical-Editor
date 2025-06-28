# bsm_designer_project/settings_manager.py

import json
import os
import logging
from PyQt5.QtCore import QObject, QStandardPaths, pyqtSignal, QDir, Qt, QSettings
from PyQt5.QtGui import QColor
from .config import (
    DEFAULT_STATE_SHAPE, DEFAULT_STATE_BORDER_STYLE, DEFAULT_STATE_BORDER_WIDTH,
    DEFAULT_TRANSITION_LINE_STYLE, DEFAULT_TRANSITION_LINE_WIDTH, DEFAULT_TRANSITION_ARROWHEAD,
    APP_FONT_FAMILY,
    COLOR_GRID_MINOR_LIGHT, COLOR_GRID_MAJOR_LIGHT, COLOR_SNAP_GUIDELINE
)

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
        "recent_files": [], # <-- NEW: For recent files menu

        # Appearance settings
        "appearance_theme": "Light",
        "canvas_grid_minor_color": COLOR_GRID_MINOR_LIGHT,
        "canvas_grid_major_color": COLOR_GRID_MAJOR_LIGHT,
        "canvas_snap_guideline_color": QColor(COLOR_SNAP_GUIDELINE).name(),

        # Default Item Visuals
        "state_default_shape": DEFAULT_STATE_SHAPE,
        "state_default_font_family": APP_FONT_FAMILY,
        "state_default_font_size": 10,
        "state_default_font_bold": True,
        "state_default_font_italic": False,
        "state_default_border_style_str": "Solid",
        "state_default_border_width": DEFAULT_STATE_BORDER_WIDTH,

        "transition_default_line_style_str": "Solid",
        "transition_default_line_width": DEFAULT_TRANSITION_LINE_WIDTH,
        "transition_default_arrowhead_style": DEFAULT_TRANSITION_ARROWHEAD,
        "transition_default_font_family": APP_FONT_FAMILY,
        "transition_default_font_size": 8,

        "comment_default_font_family": APP_FONT_FAMILY,
        "comment_default_font_size": 9,
        "comment_default_font_italic": True,
        
        # Perspective Settings
        "last_used_perspective": "Design Focus",
        "user_perspective_names": [],
    }
    
    QT_PEN_STYLES_MAP = {
        "Solid": Qt.SolidLine, "Dash": Qt.DashLine, "Dot": Qt.DotLine,
        "DashDot": Qt.DashDotLine, "DashDotDot": Qt.DashDotDotLine,
        "CustomDash": Qt.CustomDashLine,
    }
    STRING_TO_QT_PEN_STYLE = {name: enum_val for name, enum_val in QT_PEN_STYLES_MAP.items()}
    QT_PEN_STYLE_TO_STRING = {enum_val: name for name, enum_val in QT_PEN_STYLES_MAP.items()}


    def __init__(self, app_name="BSMDesigner", parent=None):
        super().__init__(parent)
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "BSM-Devs", app_name)
        logger.info(f"Settings will be loaded/saved at: {self.settings.fileName()}")
        self._init_defaults()

    def _init_defaults(self):
        for key, value in self.DEFAULTS.items():
            if not self.settings.contains(key):
                logger.info(f"Setting '{key}' not found, initializing with default: {value}")
                self.settings.setValue(key, value)
        self.settings.sync()

    def get(self, key: str, default_override=None):
        if self.settings.contains(key):
            value = self.settings.value(key)
            default_value = self.DEFAULTS.get(key)
            if default_value is not None:
                if isinstance(default_value, bool):
                    if isinstance(value, str):
                        return value.lower() in ('true', '1', 't', 'y', 'yes')
                    return bool(value)
                if isinstance(default_value, int):
                    return int(self.settings.value(key, type=int))
                if isinstance(default_value, float):
                    return float(self.settings.value(key, type=float))
            # QSettings handles string lists correctly
            return value
        
        if default_override is not None:
            return default_override
        return self.DEFAULTS.get(key)

    def set(self, key: str, value: object, save_immediately: bool = True):
        old_value = self.get(key)
        
        # Ensure lists are compared by content, not identity
        if isinstance(old_value, list) and isinstance(value, list):
            is_same = old_value == value
        else:
            is_same = str(old_value).lower() == str(value).lower()
        
        if not is_same:
            self.settings.setValue(key, value)
            if save_immediately:
                self.settings.sync()
            self.settingChanged.emit(key, value)
            logger.info(f"Setting '{key}' changed to: {value}")
        else:
            logger.debug(f"Setting '{key}' set to same value: {value}. No change emitted.")
            
    def remove_setting(self, key: str, save_immediately: bool = True):
        if self.settings.contains(key):
            self.settings.remove(key)
            if save_immediately:
                self.settings.sync()
            logger.info(f"Setting '{key}' removed.")
        else:
            logger.debug(f"Setting '{key}' not found, cannot remove.")


    def reset_to_defaults(self):
        logger.info("Resetting all settings to defaults.")
        self.settings.clear()
        self._init_defaults()
        for key, value in self.DEFAULTS.items():
            self.settingChanged.emit(key, value)
        logger.info("Settings have been reset to default values.")

    def save_settings(self):
        self.settings.sync()
        logger.debug("QSettings sync complete.")