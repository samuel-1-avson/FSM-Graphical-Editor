# fsm_designer_project/utils/config.py
"""
Central configuration file for the FSM Designer application.

Contains STATIC application settings, UI defaults, and constants.

IMPORTANT: All dynamic, theme-related colors have been moved. To access theme
colors at runtime, do not import from this module. Instead, import the shared
`theme_config` object like this:

from fsm_designer_project.utils.theme_config import theme_config
color = theme_config.COLOR_ACCENT_PRIMARY
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
PROJECT_FILE_EXTENSION = ".bsmproj"
PROJECT_FILE_FILTER = f"BSM Project Files (*{PROJECT_FILE_EXTENSION})"

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

# --- Static Colors (Not part of themes) ---
COLOR_SNAP_GUIDELINE = QColor(Qt.GlobalColor.red)
COLOR_PY_SIM_STATE_ACTIVE_PEN_WIDTH = 2.5

# ==============================================================================
# DYNAMIC THEME COLORS & STYLESHEET
# ==============================================================================
# All dynamic theme colors have been moved to `utils.theme_config.theme_config`.
# The DYNAMIC_UPDATE_COLORS_FROM_THEME function is now obsolete and has been removed.
# To use theme colors, `from fsm_designer_project.utils.theme_config import theme_config`.