# fsm_designer_project/managers/settings_manager.py
# (This file is being moved from core/ to managers/)
import json
import os
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from PyQt5.QtCore import QObject, QStandardPaths, pyqtSignal, QDir, Qt, QSettings, QTimer
from PyQt5.QtGui import QColor

logger = logging.getLogger(__name__)

class SettingCategory(Enum):
    """Enumeration of setting categories for better organization."""
    VIEW = "view"
    BEHAVIOR = "behavior"
    APPEARANCE = "appearance"
    DEFAULTS = "defaults"
    AI = "ai"
    PERSPECTIVE = "perspective"

@dataclass
class SettingDefinition:
    """Definition of a setting with metadata."""
    key: str
    default_value: Any
    category: SettingCategory
    description: str = ""
    validator: Optional[Callable[[Any], bool]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    
    def validate(self, value: Any) -> bool:
        """Validate a value against this setting's constraints."""
        # Custom validator takes precedence
        if self.validator:
            return self.validator(value)
        
        # Type validation
        if not isinstance(value, type(self.default_value)):
            return False
        
        # Range validation for numeric values
        if isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
        
        # Allowed values validation
        if self.allowed_values and value not in self.allowed_values:
            return False
        
        return True

class SettingsManager(QObject):
    """Enhanced settings manager with validation, categorization, and better error handling."""
    
    settingChanged = pyqtSignal(str, object)
    settingsReset = pyqtSignal()
    settingsLoaded = pyqtSignal()
    
    # Define all settings with metadata
    SETTING_DEFINITIONS = {
        # View settings
        "view_show_grid": SettingDefinition(
            "view_show_grid", True, SettingCategory.VIEW,
            "Show grid lines on canvas"
        ),
        "view_snap_to_grid": SettingDefinition(
            "view_snap_to_grid", True, SettingCategory.VIEW,
            "Enable snapping to grid"
        ),
        "view_snap_to_objects": SettingDefinition(
            "view_snap_to_objects", True, SettingCategory.VIEW,
            "Enable snapping to other objects"
        ),
        "view_show_snap_guidelines": SettingDefinition(
            "view_show_snap_guidelines", True, SettingCategory.VIEW,
            "Show snap guidelines"
        ),
        "grid_size": SettingDefinition(
            "grid_size", 20, SettingCategory.VIEW,
            "Grid size in pixels", min_value=5, max_value=100
        ),
        
        # Behavior settings
        "resource_monitor_enabled": SettingDefinition(
            "resource_monitor_enabled", True, SettingCategory.BEHAVIOR,
            "Enable system resource monitoring"
        ),
        "resource_monitor_interval_ms": SettingDefinition(
            "resource_monitor_interval_ms", 2000, SettingCategory.BEHAVIOR,
            "Resource monitor update interval in milliseconds",
            min_value=500, max_value=10000
        ),
        "autosave_enabled": SettingDefinition(
            "autosave_enabled", False, SettingCategory.BEHAVIOR,
            "Enable automatic saving"
        ),
        "autosave_interval_minutes": SettingDefinition(
            "autosave_interval_minutes", 5, SettingCategory.BEHAVIOR,
            "Autosave interval in minutes", min_value=1, max_value=60
        ),
        "recent_files": SettingDefinition(
            "recent_files", [], SettingCategory.BEHAVIOR,
            "List of recently opened files"
        ),
        "window_geometry": SettingDefinition("window_geometry", "", SettingCategory.BEHAVIOR),
        "window_state": SettingDefinition("window_state", "", SettingCategory.BEHAVIOR),
        "quick_access_commands": SettingDefinition(
            "quick_access_commands",
            ["Save File", "Undo", "Redo"],
            SettingCategory.BEHAVIOR,
            "Commands shown in the Quick Access Toolbar"
        ),
        
        # Appearance settings
        "appearance_theme": SettingDefinition(
            "appearance_theme", "Dark", SettingCategory.APPEARANCE,
            "Application theme", allowed_values=["Light", "Dark", "Auto", "Crimson"]
        ),
        "canvas_grid_minor_color": SettingDefinition(
            "canvas_grid_minor_color", "#455A64", SettingCategory.APPEARANCE,
            "Color of minor grid lines"
        ),
        "canvas_grid_major_color": SettingDefinition(
            "canvas_grid_major_color", "#546E7A", SettingCategory.APPEARANCE,
            "Color of major grid lines"
        ),
        "canvas_snap_guideline_color": SettingDefinition(
            "canvas_snap_guideline_color", "#E57373", SettingCategory.APPEARANCE,
            "Color of snap guidelines"
        ),
        
        # Default Item Visuals
        "state_default_shape": SettingDefinition(
            "state_default_shape", "rectangle", SettingCategory.DEFAULTS,
            "Default shape for states",
            allowed_values=["rectangle", "circle", "rounded_rectangle", "ellipse"]
        ),
        "state_default_font_family": SettingDefinition(
            "state_default_font_family", "Segoe UI, Arial, sans-serif",
            SettingCategory.DEFAULTS, "Default font family for states"
        ),
        "state_default_font_size": SettingDefinition(
            "state_default_font_size", 10, SettingCategory.DEFAULTS,
            "Default font size for states", min_value=6, max_value=72
        ),
        "state_default_font_bold": SettingDefinition(
            "state_default_font_bold", True, SettingCategory.DEFAULTS,
            "Default bold setting for state text"
        ),
        "state_default_font_italic": SettingDefinition(
            "state_default_font_italic", False, SettingCategory.DEFAULTS,
            "Default italic setting for state text"
        ),
        "state_default_border_style_str": SettingDefinition(
            "state_default_border_style_str", "Solid", SettingCategory.DEFAULTS,
            "Default border style for states",
            allowed_values=["Solid", "Dash", "Dot", "DashDot", "DashDotDot"]
        ),
        "state_default_border_width": SettingDefinition(
            "state_default_border_width", 1.8, SettingCategory.DEFAULTS,
            "Default border width for states", min_value=0.1, max_value=10.0
        ),
        "item_default_state_color": SettingDefinition(
            "item_default_state_color", "#4A6572", SettingCategory.DEFAULTS,
            "Default color for states"
        ),
        
        "transition_default_line_style_str": SettingDefinition(
            "transition_default_line_style_str", "Solid", SettingCategory.DEFAULTS,
            "Default line style for transitions",
            allowed_values=["Solid", "Dash", "Dot", "DashDot", "DashDotDot"]
        ),
        "transition_default_line_width": SettingDefinition(
            "transition_default_line_width", 2.2, SettingCategory.DEFAULTS,
            "Default line width for transitions", min_value=0.1, max_value=10.0
        ),
        "transition_default_arrowhead_style": SettingDefinition(
            "transition_default_arrowhead_style", "filled", SettingCategory.DEFAULTS,
            "Default arrowhead style for transitions",
            allowed_values=["filled", "open", "none"]
        ),
        "transition_default_font_family": SettingDefinition(
            "transition_default_font_family", "Segoe UI, Arial, sans-serif",
            SettingCategory.DEFAULTS, "Default font family for transitions"
        ),
        "transition_default_font_size": SettingDefinition(
            "transition_default_font_size", 8, SettingCategory.DEFAULTS,
            "Default font size for transitions", min_value=6, max_value=72
        ),
        "item_default_transition_color": SettingDefinition(
            "item_default_transition_color", "#4DB6AC", SettingCategory.DEFAULTS,
            "Default color for transitions"
        ),
        
        "comment_default_font_family": SettingDefinition(
            "comment_default_font_family", "Segoe UI, Arial, sans-serif",
            SettingCategory.DEFAULTS, "Default font family for comments"
        ),
        "comment_default_font_size": SettingDefinition(
            "comment_default_font_size", 9, SettingCategory.DEFAULTS,
            "Default font size for comments", min_value=6, max_value=72
        ),
        "comment_default_font_italic": SettingDefinition(
            "comment_default_font_italic", True, SettingCategory.DEFAULTS,
            "Default italic setting for comment text"
        ),
        "item_default_comment_bg_color": SettingDefinition(
            "item_default_comment_bg_color", "#424242", SettingCategory.DEFAULTS,
            "Default background color for comments"
        ),
        
        # AI Assistant Settings
        "ai_provider": SettingDefinition(
            "ai_provider", "Gemini (Google AI)", SettingCategory.AI, "Selected AI Provider"
        ),
        "ai_api_key_gemini_(google_ai)": SettingDefinition("ai_api_key_gemini_(google_ai)", "", SettingCategory.AI),
        "ai_api_key_openai_(gpt)": SettingDefinition("ai_api_key_openai_(gpt)", "", SettingCategory.AI),
        "ai_api_key_groq_(llama3)": SettingDefinition("ai_api_key_groq_(llama3)", "", SettingCategory.AI),
        "ai_api_key_anthropic_(claude)": SettingDefinition("ai_api_key_anthropic_(claude)", "", SettingCategory.AI),
        "ai_api_key_deepseek": SettingDefinition("ai_api_key_deepseek", "", SettingCategory.AI),
        
        # Perspective Settings
        "last_used_perspective": SettingDefinition(
            "last_used_perspective", "Design Focus", SettingCategory.PERSPECTIVE,
            "Last used perspective mode"
        ),
        "user_perspective_names": SettingDefinition(
            "user_perspective_names", [], SettingCategory.PERSPECTIVE,
            "User-defined perspective names"
        ),
        "perspective_Design Focus": SettingDefinition("perspective_Design Focus", "", SettingCategory.PERSPECTIVE),
        "perspective_Simulation Focus": SettingDefinition("perspective_Simulation Focus", "", SettingCategory.PERSPECTIVE),
        "perspective_IDE Focus": SettingDefinition("perspective_IDE Focus", "", SettingCategory.PERSPECTIVE),
        "perspective_AI Focus": SettingDefinition("perspective_AI Focus", "", SettingCategory.PERSPECTIVE),
        "perspective_Developer View": SettingDefinition("perspective_Developer View", "", SettingCategory.PERSPECTIVE),
    }
    
    # Legacy compatibility - provides defaults as a simple dict
    DEFAULTS = {key: definition.default_value 
                for key, definition in SETTING_DEFINITIONS.items()}
    
    QT_PEN_STYLES_MAP = {
        "Solid": Qt.SolidLine, "Dash": Qt.DashLine, "Dot": Qt.DotLine,
                "DashDotDot": Qt.DashDotDotLine,
        "CustomDash": Qt.CustomDashLine,
    }
    STRING_TO_QT_PEN_STYLE = {name: enum_val for name, enum_val in QT_PEN_STYLES_MAP.items()}
    QT_PEN_STYLE_TO_STRING = {enum_val: name for name, enum_val in QT_PEN_STYLES_MAP.items()}

    def __init__(self, app_name="BSMDesigner", parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "BSM-Devs", app_name)
        
        # Cache for frequently accessed settings
        self._cache = {}
        self._cache_dirty = set()
        
        # Batch update support
        self._batch_mode = False
        self._batch_changes = {}
        
        # Auto-sync timer for performance
        self._sync_timer = QTimer()
        self._sync_timer.setSingleShot(True)
        self._sync_timer.timeout.connect(self._perform_sync)
        self._sync_timer.setInterval(1000)  # 1 second delay
        
        logger.info(f"Settings will be loaded/saved at: {self.settings.fileName()}")
        self._init_defaults()
        self.settingsLoaded.emit()

    def _init_defaults(self):
        """Initialize settings with defaults if they don't exist."""
        for key, definition in self.SETTING_DEFINITIONS.items():
            if not self.settings.contains(key):
                logger.info(f"Setting '{key}' not found, initializing with default: {definition.default_value}")
                self.settings.setValue(key, definition.default_value)
        self.settings.sync()

    def get(self, key: str, default_override=None) -> Any:
        """Get a setting value with caching and proper type conversion."""
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        # Get definition
        definition = self.SETTING_DEFINITIONS.get(key)
        if not definition:
            # Check for dynamic perspective keys
            if key.startswith("perspective_"):
                 return self.settings.value(key, default_override)
            logger.warning(f"Unknown setting key: '{key}'")
            return default_override
        
        # Get value from storage
        value = self.settings.value(key)
        default_value = default_override if default_override is not None else definition.default_value
        
        if value is None:
            logger.debug(f"Setting '{key}' is None in storage. Using default.")
            self._cache[key] = default_value
            return default_value

        # Convert to proper type
        try:
            converted_value = self._convert_value(value, definition.default_value)
            
            # Validate the converted value
            if not definition.validate(converted_value):
                logger.warning(f"Setting '{key}' value '{converted_value}' failed validation. Using default.")
                converted_value = default_value
            
            self._cache[key] = converted_value
            return converted_value
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not convert setting '{key}' with value '{value}' to expected type. Error: {e}. Using default.")
            self._cache[key] = default_value
            return default_value

    def _convert_value(self, value: Any, default_value: Any) -> Any:
        """Convert a value to match the type of the default value."""
        if isinstance(default_value, bool):
            if isinstance(value, str):
                return value.lower() in ('true', '1', 't', 'y', 'yes')
            return bool(value)
        elif isinstance(default_value, int):
            return int(value)
        elif isinstance(default_value, float):
            return float(value)
        elif isinstance(default_value, list) and not isinstance(value, list):
            if value == "":
                return []
            # Try to parse as JSON if it's a string
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Could not convert value to list: {value}")
            return default_value
        return value

    def set(self, key: str, value: Any, save_immediately: bool = True) -> bool:
        """Set a setting value with validation and batching support."""
        definition = self.SETTING_DEFINITIONS.get(key)
        if not definition:
            if key.startswith("perspective_"): # Allow dynamic perspective keys
                pass 
            else:
                logger.warning(f"Unknown setting key: '{key}'. Setting anyway.")
        elif not definition.validate(value):
            logger.error(f"Setting '{key}' value '{value}' failed validation. Not setting.")
            return False
        
        old_value = self.get(key)
        
        # Check if value actually changed
        if isinstance(old_value, list) and isinstance(value, list):
            is_same = old_value == value
        else:
            is_same = str(old_value) == str(value)
        
        if is_same:
            logger.debug(f"Setting '{key}' set to same value: {value}. No change.")
            return True
        
        # Update cache
        self._cache[key] = value
        
        if self._batch_mode:
            # Store in batch changes
            self._batch_changes[key] = value
        else:
            # Update immediately
            self.settings.setValue(key, value)
            if save_immediately:
                self._schedule_sync()
            self.settingChanged.emit(key, value)
            logger.info(f"Setting '{key}' changed to: {value}")
        
        return True

    def get_by_category(self, category: SettingCategory) -> Dict[str, Any]:
        """Get all settings in a specific category."""
        result = {}
        for key, definition in self.SETTING_DEFINITIONS.items():
            if definition.category == category:
                result[key] = self.get(key)
        return result

    def reset_category(self, category: SettingCategory):
        """Reset all settings in a category to defaults."""
        logger.info(f"Resetting category '{category.value}' to defaults.")
        for key, definition in self.SETTING_DEFINITIONS.items():
            if definition.category == category:
                self.set(key, definition.default_value, save_immediately=False)
        self.settings.sync()

    def begin_batch_update(self):
        """Begin a batch update to avoid multiple sync operations."""
        self._batch_mode = True
        self._batch_changes.clear()

    def end_batch_update(self, save_immediately: bool = True):
        """End batch update and apply all changes."""
        if not self._batch_mode:
            return
        
        self._batch_mode = False
        
        # Apply all batched changes
        for key, value in self._batch_changes.items():
            self.settings.setValue(key, value)
            self.settingChanged.emit(key, value)
            logger.info(f"Batch setting '{key}' changed to: {value}")
        
        if save_immediately:
            self._schedule_sync()
        
        self._batch_changes.clear()

    def _schedule_sync(self):
        """Schedule a sync operation to avoid too frequent disk writes."""
        self._sync_timer.start()

    def _perform_sync(self):
        """Perform the actual sync to disk."""
        self.settings.sync()
        logger.debug("Settings synced to disk.")

    def remove_setting(self, key: str, save_immediately: bool = True):
        """Remove a setting."""
        if self.settings.contains(key):
            self.settings.remove(key)
            # Remove from cache
            self._cache.pop(key, None)
            if save_immediately:
                self._schedule_sync()
            logger.info(f"Setting '{key}' removed.")
        else:
            logger.debug(f"Setting '{key}' not found, cannot remove.")

    def reset_to_defaults(self):
        """Reset all settings to their defaults."""
        logger.info("Resetting all settings to defaults.")
        
        self.begin_batch_update()
        try:
            # Clear cache
            self._cache.clear()
            
            # Reset all settings
            for key, definition in self.SETTING_DEFINITIONS.items():
                self.settings.setValue(key, definition.default_value)
                self._batch_changes[key] = definition.default_value
        finally:
            self.end_batch_update(save_immediately=True)
        
        self.settingsReset.emit()
        logger.info("Settings have been reset to default values.")

    def export_settings(self, filepath: str) -> bool:
        """Export settings to a JSON file."""
        try:
            settings_data = {}
            for key in self.SETTING_DEFINITIONS.keys():
                settings_data[key] = self.get(key)
            
            with open(filepath, 'w') as f:
                json.dump(settings_data, f, indent=2, default=str)
            
            logger.info(f"Settings exported to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            return False

    def import_settings(self, filepath: str) -> bool:
        """Import settings from a JSON file."""
        try:
            with open(filepath, 'r') as f:
                settings_data = json.load(f)
            
            self.begin_batch_update()
            try:
                for key, value in settings_data.items():
                    if key in self.SETTING_DEFINITIONS:
                        self.set(key, value, save_immediately=False)
            finally:
                self.end_batch_update(save_immediately=True)
            
            logger.info(f"Settings imported from: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            return False

    def get_setting_info(self, key: str) -> Optional[SettingDefinition]:
        """Get metadata about a setting."""
        return self.SETTING_DEFINITIONS.get(key)

    def get_all_setting_keys(self) -> List[str]:
        """Get all available setting keys."""
        return list(self.SETTING_DEFINITIONS.keys())

    def is_default_value(self, key: str) -> bool:
        """Check if a setting has its default value."""
        definition = self.SETTING_DEFINITIONS.get(key)
        if not definition:
            return False
        return self.get(key) == definition.default_value

    def save_settings(self):
        """Force immediate save of all settings."""
        self._sync_timer.stop()
        self._perform_sync()

    def clear_cache(self):
        """Clear the settings cache."""
        self._cache.clear()
        logger.debug("Settings cache cleared.")