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
        "state_default_font_bold": True,
        "state_default_font_italic": False,
        "state_default_border_style_str": "Solid",
        "state_default_border_width": 1.8,
        "item_default_state_color": "#4A6572", # Updated to match dark theme default

        "transition_default_line_style_str": "Solid",
        "transition_default_line_width": 2.2,
        "transition_default_arrowhead_style": "filled",
        "transition_default_font_family": "Segoe UI, Arial, sans-serif",
        "transition_default_font_size": 8,
        "item_default_transition_color": "#4DB6AC", # Updated to match dark theme default

        "comment_default_font_family": "Segoe UI, Arial, sans-serif",
        "comment_default_font_size": 9,
        "comment_default_font_italic": True,
        "item_default_comment_bg_color": "#424242", # Updated to match dark theme default
        
        # --- AI Assistant Settings ---
        "ai_provider_name": "Gemini (Google AI)", # The default provider
        "ai_gemini_(google_ai)_api_key": "", # Key for each provider
        "ai_openai_(gpt)_api_key": "",
        "ai_anthropic_(claude)_api_key": "",
        "ai_groq_(llama3)_api_key": "",
        "ai_deepseek_api_key": "",
        
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
        value = self.settings.value(key)
        
        default_value = self.DEFAULTS.get(key)
        
        if value is None:
            logger.debug(f"Setting '{key}' is None in storage. Using default.")
            return default_override if default_override is not None else default_value

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
                if isinstance(default_value, list) and not isinstance(value, list):
                    if value == "":
                        return []
                    logger.warning(f"Setting '{key}' expected a list, but got {type(value)}. Returning default.")
                    return default_value
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not convert setting '{key}' with value '{value}' to expected type. Error: {e}. Returning default.")
                return default_value
        
        return value

    def set(self, key: str, value: object, save_immediately: bool = True):
        old_value = self.get(key)
        
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