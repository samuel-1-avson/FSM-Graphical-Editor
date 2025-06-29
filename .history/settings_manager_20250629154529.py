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
    COLOR_GRID_MINOR_LIGHT, COLOR_GRID_MAJOR_LIGHT, COLOR_SNAP_GUIDELINE,
    COLOR_ITEM_STATE_DEFAULT_BG, COLOR_ITEM_TRANSITION_DEFAULT, COLOR_ITEM_COMMENT_BG
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
        "recent_files": [],

        # Appearance settings
        "appearance_theme": "Light",
        "canvas_grid_minor_color": COLOR_GRID_MINOR_LIGHT,
        "canvas_grid_major_color": COLOR_GRID_MAJOR_LIGHT,
        "canvas_snap_guideline_color": QColor(COLOR_SNAP_GUIDELINE).name(),

        # Default Item Colors (NEW)
        "item_default_state_color": COLOR_ITEM_STATE_DEFAULT_BG,
        "item_default_transition_color": COLOR_ITEM_TRANSITION_DEFAULT,
        "item_default_comment_bg_color": COLOR_ITEM_COMMENT_BG,

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
        """
        Retrieves a setting value, ensuring proper type conversion and fallback to defaults.
        This method is made robust to handle cases where a stored setting is null/empty.
        """
        # --- FIX: Robustly handle potential None values from QSettings ---
        # The default_override is confusing with self.DEFAULTS, so we'll use a clear priority:
        # 1. Stored value (if valid)
        # 2. default_override (if provided)
        # 3. Application default from self.DEFAULTS
        
        # Get the value from QSettings. This can return None if the key does not exist,
        # or if the key exists but is empty (e.g., recent_files=).
        value = self.settings.value(key)
        
        # Get the application's hardcoded default value for this key
        default_value = self.DEFAULTS.get(key)
        
        # If the retrieved value is None, we MUST fall back to a valid default.
        if value is None:
            # If a one-time override was provided, use it. Otherwise, use the app default.
            logger.debug(f"Setting '{key}' is None in storage. Using default.")
            return default_override if default_override is not None else default_value

        # If we have a value, we should still try to cast it to the expected type
        # based on the application defaults. This handles cases where QSettings reads everything
        # as a string (e.g., 'true' for a boolean).
        if default_value is not None:
            try:
                if isinstance(default_value, bool):
                    if isinstance(value, str):
                        return value.lower() in ('true', '1', 't', 'y', 'yes')
                    return bool(value)
                if isinstance(default_value, int):
                    return int(value)
                if isinstance(default_value, float):
                    return float(value)
                # For lists, QSettings usually handles it, but if it's a string from an old version,
                # we can return the default list. An empty string value could be an empty list.
                if isinstance(default_value, list) and not isinstance(value, list):
                    if value == "":
                        return []
                    logger.warning(f"Setting '{key}' expected a list, but got {type(value)}. Returning default.")
                    return default_value

            except (ValueError, TypeError) as e:
                logger.warning(f"Could not convert setting '{key}' with value '{value}' to expected type. Error: {e}. Returning default.")
                return default_value
        
        # If no default type is defined or if it's just a string, return the value as-is.
        return value

    def set(self, key: str, value: object, save_immediately: bool = True):
        old_value = self.get(key)
        
        # Ensure lists are compared by content, not identity
        if isinstance(old_value, list) and isinstance(value, list):
            is_same = old_value == value
        else:
            is_same = str(old_value) == str(value)
        
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