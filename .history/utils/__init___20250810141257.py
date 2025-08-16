# fsm_designer_project/utils/__init__.py
"""
Initializes the 'utils' package.

This package contains general-purpose helper modules that are not specific to
any one part of the application, such as logging setup, theme configuration,
and standard icon retrieval.
"""

from .helpers import get_standard_icon, _get_bundled_file_path
from .logging_setup import setup_global_logging
from .config import (
    APP_VERSION, APP_NAME, FILE_EXTENSION, FILE_FILTER,
    PROJECT_FILE_EXTENSION, PROJECT_FILE_FILTER,
    MIME_TYPE_BSM_ITEMS, MIME_TYPE_BSM_TEMPLATE, DEFAULT_EXECUTION_ENV,
    APP_FONT_FAMILY, APP_FONT_SIZE_STANDARD, APP_FONT_SIZE_SMALL,
    APP_FONT_SIZE_EDITOR, DEFAULT_STATE_SHAPE, DEFAULT_STATE_BORDER_STYLE,
    DEFAULT_STATE_BORDER_WIDTH, DEFAULT_TRANSITION_LINE_STYLE,
    DEFAULT_TRANSITION_LINE_WIDTH, DEFAULT_TRANSITION_ARROWHEAD,
    DYNAMIC_UPDATE_COLORS_FROM_THEME
)

# Note: The color variables are not exported here as they are meant to be used
# via the 'config' module directly (e.g., from ..utils import config).

__all__ = [
    "get_standard_icon",
    "_get_bundled_file_path",
    "setup_global_logging",
    "APP_VERSION",
    "APP_NAME",
    "FILE_EXTENSION",
    "FILE_FILTER",
    "PROJECT_FILE_EXTENSION",
    "PROJECT_FILE_FILTER",
    "MIME_TYPE_BSM_ITEMS",
    "MIME_TYPE_BSM_TEMPLATE",
    "DEFAULT_EXECUTION_ENV",
    "APP_FONT_FAMILY",
    "APP_FONT_SIZE_STANDARD",
    "APP_FONT_SIZE_SMALL",
    "APP_FONT_SIZE_EDITOR",
    "DEFAULT_STATE_SHAPE",
    "DEFAULT_STATE_BORDER_STYLE",
    "DEFAULT_STATE_BORDER_WIDTH",
    "DEFAULT_TRANSITION_LINE_STYLE",
    "DEFAULT_TRANSITION_LINE_WIDTH",
    "DEFAULT_TRANSITION_ARROWHEAD",
    "DYNAMIC_UPDATE_COLORS_FROM_THEME",
]