# fsm_designer_project/utils/theme_config.py
"""
Provides a globally accessible singleton-like object for theme configuration.
This object is populated at runtime by the ThemeManager and serves as the
single source of truth for all dynamic color and style values in the application.
"""
from PyQt5.QtGui import QColor

class ThemeConfig:
    """A class to hold all dynamic theme configuration values."""
    def __init__(self):
        # Initialize with placeholder values to ensure attributes exist.
        # The ThemeManager will populate these with actual theme data.
        self.COLOR_BACKGROUND_APP = "#ECEFF1"
        self.COLOR_BACKGROUND_LIGHT = "#FAFAFA"
        self.COLOR_BACKGROUND_MEDIUM = "#E0E0E0"
        self.COLOR_BACKGROUND_DARK = "#BDBDBD"
        self.COLOR_BACKGROUND_EDITOR_DARK = "#263238"
        self.COLOR_TEXT_EDITOR_DARK_PRIMARY = "#ECEFF1"
        self.COLOR_TEXT_EDITOR_DARK_SECONDARY = "#90A4AE"
        self.COLOR_BACKGROUND_DIALOG = "#FFFFFF"
        self.COLOR_TEXT_PRIMARY = "#212121"
        self.COLOR_TEXT_SECONDARY = "#757575"
        self.COLOR_TEXT_ON_ACCENT = "#FFFFFF"
        self.COLOR_ACCENT_PRIMARY = "#0277BD"
        self.COLOR_ACCENT_PRIMARY_LIGHT = "#B3E5FC"
        self.COLOR_ACCENT_SECONDARY = "#FF8F00"
        self.COLOR_ACCENT_SUCCESS = "#4CAF50"
        self.COLOR_ACCENT_WARNING = "#FFC107"
        self.COLOR_ACCENT_ERROR = "#D32F2F"
        self.COLOR_BORDER_LIGHT = "#CFD8DC"
        self.COLOR_BORDER_MEDIUM = "#90A4AE"
        self.COLOR_BORDER_DARK = "#607D8B"
        self.COLOR_ITEM_STATE_DEFAULT_BG = "#E3F2FD"
        self.COLOR_ITEM_STATE_DEFAULT_BORDER = "#64B5F6"
        self.COLOR_ITEM_TRANSITION_DEFAULT = "#00796B"
        self.COLOR_ITEM_COMMENT_BG = "#FFF9C4"
        self.COLOR_ITEM_COMMENT_BORDER = "#FFEE58"
        self.COLOR_GRID_MINOR = "#ECEFF1"
        self.COLOR_GRID_MAJOR = "#CFD8DC"
        self.COLOR_DRAGGABLE_BUTTON_BG = "#E8EAF6"
        self.COLOR_DRAGGABLE_BUTTON_BORDER = "#C5CAE9"
        self.COLOR_DRAGGABLE_BUTTON_HOVER_BG = "#B9D9EB"
        self.COLOR_DRAGGABLE_BUTTON_HOVER_BORDER = "#0277BD"
        self.COLOR_DRAGGABLE_BUTTON_PRESSED_BG = "#98BAD6"
        # Derived colors will also be populated here
        self.COLOR_ITEM_STATE_SELECTION_BG = ""
        self.COLOR_ITEM_STATE_SELECTION_BORDER = ""
        self.COLOR_ITEM_TRANSITION_SELECTION = ""
        self.COLOR_PY_SIM_STATE_ACTIVE = QColor("#4CAF50")

    def update_from_dict(self, theme_data: dict):
        """Populates attributes from a theme dictionary and calculates derived colors."""
        for key, value in theme_data.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Calculate professional derived colors
        self.COLOR_PY_SIM_STATE_ACTIVE = QColor(self.COLOR_ACCENT_SUCCESS)
        
        accent_secondary_color = QColor(self.COLOR_ACCENT_SECONDARY)
        self.COLOR_ITEM_STATE_SELECTION_BG = accent_secondary_color.lighter(180 if accent_secondary_color.lightnessF() < 0.5 else 130).name()
        self.COLOR_ITEM_STATE_SELECTION_BORDER = accent_secondary_color.name()
        
        accent_primary_color = QColor(self.COLOR_ACCENT_PRIMARY)
        self.COLOR_ITEM_TRANSITION_SELECTION = accent_primary_color.lighter(160 if accent_primary_color.lightnessF() < 0.5 else 130).name()

# Create a single, globally accessible instance
theme_config = ThemeConfig()