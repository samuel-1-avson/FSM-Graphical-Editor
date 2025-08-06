# fsm_designer_project/utils/config.py
"""
Central configuration file for the FSM Designer application.

Contains static application settings, UI defaults, and dynamically populated
theme colors.
"""
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

# ==============================================================================
# STATIC APPLICATION CONFIGURATION
# ==============================================================================
# These values are constant and define the application's identity.

APP_VERSION = "2.0.0"
APP_NAME = "Brain State Machine Designer"
FILE_EXTENSION = ".bsm"
FILE_FILTER = f"Brain State Machine Files (*{FILE_EXTENSION});;All Files (*)"

# --- FIX: Moved project constants here ---
PROJECT_FILE_EXTENSION = ".bsmproj"
PROJECT_FILE_FILTER = f"BSM Project Files (*{PROJECT_FILE_EXTENSION})"
# --- END FIX ---

# MIME types for custom drag-and-drop operations
MIME_TYPE_BSM_ITEMS = "application/x-bsm-designer-items"
MIME_TYPE_BSM_TEMPLATE = "application/x-bsm-template"

# Default language for actions/conditions in new items
DEFAULT_EXECUTION_ENV = "Python (Generic Simulation)"


# ==============================================================================
# STATIC UI DEFAULTS
# ==============================================================================
# These values define the default appearance and behavior of UI elements.
# They can be overridden by user settings.

# --- Fonts ---
APP_FONT_FAMILY = "Segoe UI, Arial, sans-serif"
APP_FONT_SIZE_STANDARD = "9pt"
APP_FONT_SIZE_SMALL = "8pt"
APP_FONT_SIZE_EDITOR = "10pt"

# --- Default Item Properties ---
DEFAULT_STATE_SHAPE = "rectangle"
DEFAULT_STATE_BORDER_STYLE = Qt.PenStyle.SolidLine
DEFAULT_STATE_BORDER_WIDTH = 1.8

DEFAULT_TRANSITION_LINE_STYLE = Qt.PenStyle.SolidLine
DEFAULT_TRANSITION_LINE_WIDTH = 2.2
DEFAULT_TRANSITION_ARROWHEAD = "filled"


# ==============================================================================
# DYNAMIC THEME COLORS & STYLESHEET
# ==============================================================================
# IMPORTANT: The color variables below are DYNAMIC. They are initialized with
# a default 'Light' theme but are populated at runtime by the ThemeManager
# based on user settings. Do not treat them as constants.

# Initial default colors (Light Theme) to prevent errors on startup
# before the ThemeManager takes over.
_INITIAL_THEME_DATA = {
    "COLOR_BACKGROUND_APP": "#ECEFF1", "COLOR_BACKGROUND_LIGHT": "#FAFAFA",
    "COLOR_BACKGROUND_MEDIUM": "#E0E0E0", "COLOR_BACKGROUND_DARK": "#BDBDBD",
    "COLOR_BACKGROUND_EDITOR_DARK": "#263238", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#ECEFF1",
    "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#90A4AE", "COLOR_BACKGROUND_DIALOG": "#FFFFFF",
    "COLOR_TEXT_PRIMARY": "#212121", "COLOR_TEXT_SECONDARY": "#757575",
    "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#0277BD",
    "COLOR_ACCENT_PRIMARY_LIGHT": "#B3E5FC", "COLOR_ACCENT_SECONDARY": "#FF8F00",
    "COLOR_ACCENT_SUCCESS": "#4CAF50", "COLOR_ACCENT_WARNING": "#FFC107",
    "COLOR_ACCENT_ERROR": "#D32F2F", "COLOR_BORDER_LIGHT": "#CFD8DC",
    "COLOR_BORDER_MEDIUM": "#90A4AE", "COLOR_BORDER_DARK": "#607D8B",
    "COLOR_ITEM_STATE_DEFAULT_BG": "#E3F2FD", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#64B5F6",
    "COLOR_ITEM_TRANSITION_DEFAULT": "#00796B", "COLOR_ITEM_COMMENT_BG": "#FFF9C4",
    "COLOR_ITEM_COMMENT_BORDER": "#FFEE58", "COLOR_GRID_MINOR": "#ECEFF1",
    "COLOR_GRID_MAJOR": "#CFD8DC", "COLOR_DRAGGABLE_BUTTON_BG": "#E8EAF6",
    "COLOR_DRAGGABLE_BUTTON_BORDER": "#C5CAE9", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#B9D9EB",
    "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#0277BD", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#98BAD6"
}

# Define global variables so linters don't complain.
for key in _INITIAL_THEME_DATA:
    globals()[key] = ""

# These colors are derived from the main theme colors
COLOR_ITEM_STATE_SELECTION_BG = ""
COLOR_ITEM_STATE_SELECTION_BORDER = ""
COLOR_ITEM_TRANSITION_SELECTION = ""
COLOR_SNAP_GUIDELINE = QColor(Qt.GlobalColor.red) # This one is static for now
COLOR_PY_SIM_STATE_ACTIVE = QColor("#4CAF50") # This will be updated by the theme manager
COLOR_PY_SIM_STATE_ACTIVE_PEN_WIDTH = 2.5


def DYNAMIC_UPDATE_COLORS_FROM_THEME(theme_data: dict):
    """
    Populates the global color variables in this module from a theme dictionary.
    This function is the single source of truth for setting theme colors at runtime.
    """
    global COLOR_PY_SIM_STATE_ACTIVE, COLOR_ITEM_STATE_SELECTION_BG, \
           COLOR_ITEM_STATE_SELECTION_BORDER, COLOR_ITEM_TRANSITION_SELECTION

    for key, value in theme_data.items():
        if key in globals():
            globals()[key] = value

    COLOR_PY_SIM_STATE_ACTIVE = QColor(globals().get("COLOR_ACCENT_SUCCESS"))
    
    accent_secondary_color = QColor(globals().get("COLOR_ACCENT_SECONDARY", "#FF8F00"))
    # --- FIX: Changed self. to direct global variable assignment ---
    globals()['COLOR_ITEM_STATE_SELECTION_BG'] = accent_secondary_color.lighter(180 if accent_secondary_color.lightnessF() < 0.5 else 130).name()
    globals()['COLOR_ITEM_STATE_SELECTION_BORDER'] = accent_secondary_color.name()
    
    accent_primary_color = QColor(globals().get("COLOR_ACCENT_PRIMARY", "#0277BD"))
    globals()['COLOR_ITEM_TRANSITION_SELECTION'] = accent_primary_color.lighter(160 if accent_primary_color.lightnessF() < 0.5 else 130).name()

# Initial population to ensure variables are not empty before the ThemeManager takes over.
DYNAMIC_UPDATE_COLORS_FROM_THEME(_INITIAL_THEME_DATA)