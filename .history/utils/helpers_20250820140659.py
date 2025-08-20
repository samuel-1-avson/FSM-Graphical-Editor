# fsm_designer_project/utils/helpers.py
import os 
import sys 
import platform
import subprocess
import logging
from PyQt6.QtWidgets import QApplication, QStyle
from PyQt6.QtGui import QIcon, QFont, QFontDatabase, QAction, QKeySequence
from PyQt6.QtCore import QFile, QDir, QIODevice, QFileInfo, QUrl, QStandardPaths
from PyQt6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)

# --- Font Management ---
_preferred_ui_font = None

def get_preferred_ui_font() -> QFont:
    """
    Finds the best available modern UI font on the system and caches the result.
    This ensures the application uses a high-quality, native-looking font
    across different operating systems.
    """
    global _preferred_ui_font
    if _preferred_ui_font is not None:
        return _preferred_ui_font

    # A list of high-quality UI fonts in order of preference
    preferred_fonts = [
        "Segoe UI",      # Windows
        "San Francisco",  # macOS (SF Pro, etc.) - Note: Might not be directly queryable
        ".SF NS",         # Actual family name for San Francisco on macOS
        "Cantarell",      # GNOME/Fedora
        "Ubuntu",         # Ubuntu
        "Roboto",         # Android/ChromeOS, often available
        "Noto Sans",      # Google's comprehensive font
        "Arial"           # Last resort fallback
    ]
    
    available_families = QFontDatabase.families()
    
    best_family = "sans-serif" # Ultimate fallback for Qt
    for family in preferred_fonts:
        if family in available_families:
            best_family = family
            break
            
    _preferred_ui_font = QFont(best_family)
    logger.info(f"Selected preferred UI font: {best_family}")
    return _preferred_ui_font


# --- UI Helpers ---

def get_standard_icon(style_enum_value, alt_text=""):
    """
    Get a standard icon from the QStyle.StandardPixmap enum value.
    Returns an empty QIcon on failure.
    """
    if not isinstance(style_enum_value, QStyle.StandardPixmap):
        logger.error(
            f"Invalid type for style_enum_value in get_standard_icon. "
            f"Expected QStyle.StandardPixmap, got {type(style_enum_value)} (value: {style_enum_value}). Alt: {alt_text}"
        )
        return QIcon()

    try:
        style = QApplication.style()
        if not style:
            logger.error("QApplication.style() returned None. Cannot get standard icon.")
            return QIcon()
            
        icon = style.standardIcon(style_enum_value)
        if icon.isNull():
            logger.debug(
                f"Standard icon for enum {style_enum_value} is null (Alt: {alt_text}). "
                f"Current style: {style.objectName()}"
            )
            return QIcon()
        return icon
    except Exception as e:
        logger.error(
            f"Exception in get_standard_icon for enum {style_enum_value} (Alt: {alt_text}): {e}",
            exc_info=True
        )
        return QIcon()

def set_shortcut_and_tooltip(action: QAction, shortcut_key_str: str):
    """
    Sets a QKeySequence for an action and updates its tooltip with the
    platform-appropriate modifier key names (e.g., 'Cmd' on macOS).
    
    Args:
        action: The QAction to modify.
        shortcut_key_str: The shortcut string using standard names (e.g., "Ctrl+S").
    """
    # 1. Set the actual shortcut. Qt handles the mapping of Ctrl -> Cmd internally.
    action.setShortcut(QKeySequence(shortcut_key_str))
    
    # 2. Create a user-friendly display string for the tooltip.
    display_shortcut = shortcut_key_str
    if sys.platform == "darwin":  # 'darwin' is the identifier for macOS
        display_shortcut = display_shortcut.replace("Ctrl+", "⌘")
        display_shortcut = display_shortcut.replace("Alt+", "⌥")
        display_shortcut = display_shortcut.replace("Shift+", "⇧")
    
    # 3. Update the tooltip.
    base_tooltip = action.toolTip()
    action.setToolTip(f"{base_tooltip} ({display_shortcut})")


# --- File System Helpers ---

def _get_bundled_file_path(filename: str, resource_prefix: str = "") -> str | None:
    """
    Tries to get a file path from Qt resources first, then falls back to filesystem.
    If from resources, copies to a temporary location and returns that path.
    """
    RESOURCES_AVAILABLE = 'resources_rc' in sys.modules

    if RESOURCES_AVAILABLE:
        actual_resource_path_prefix = f"/{resource_prefix}" if resource_prefix else ""
        resource_path = f":{actual_resource_path_prefix}/{filename}".replace("//", "/")

        if QFile.exists(resource_path):
            logger.debug(f"Found bundled file '{filename}' in Qt Resources at: {resource_path}")
            
            app_temp_root_dir = QDir(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation))
            session_temp_dir = app_temp_root_dir.filePath(f"BSMDesigner_Temp_{QApplication.applicationPid()}")
            
            if not QDir(session_temp_dir).exists():
                QDir().mkpath(session_temp_dir)

            temp_disk_path = QDir(session_temp_dir).filePath(filename)

            if QFile.exists(temp_disk_path):
                return temp_disk_path

            if QFile.copy(resource_path, temp_disk_path):
                logger.debug(f"Copied resource '{resource_path}' to temporary disk path: {temp_disk_path}")
                return temp_disk_path
            else:
                logger.warning(f"Failed to copy resource '{resource_path}' to '{temp_disk_path}'.")
        else:
            logger.debug(f"File '{resource_path}' not found in Qt Resources.")

    # Filesystem fallback
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        # __file__ is in utils/, so ../ is fsm_designer_project/utils, ../../ is fsm_designer_project/
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    prefix_to_subdir_map = {
        "examples": "examples",
        "docs": "docs",
        "icons": "dependencies/icons"
    }
    
    search_path = base_path
    if resource_prefix and resource_prefix in prefix_to_subdir_map:
        search_path = os.path.join(base_path, prefix_to_subdir_map[resource_prefix])
    
    full_path = os.path.join(search_path, filename)
    
    if os.path.exists(full_path):
        logger.debug(f"Found bundled file '{filename}' via filesystem fallback at: {full_path}")
        return full_path
            
    logger.warning(f"Bundled file '{filename}' (prefix: '{resource_prefix}') ultimately not found.")
    return None

def reveal_in_file_manager(path: str):
    """
    Reveals a file or directory in the native file manager.
    Selects the file if the platform supports it.
    """
    if not os.path.exists(path):
        logger.warning(f"Cannot reveal path, it does not exist: {path}")
        return

    try:
        if platform.system() == "Windows":
            subprocess.run(['explorer', '/select,', os.path.normpath(path)], check=True)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(['open', '-R', path], check=True)
        else:  # Linux and other Unix-like systems
            dir_path = os.path.dirname(path) if not os.path.isdir(path) else path
            subprocess.run(['xdg-open', dir_path], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError, Exception) as e:
        logger.error(f"Could not reveal path '{path}' using native command: {e}")
        # Fallback to Qt's less specific but more universal method
        folder = os.path.dirname(path) if not os.path.isdir(path) else path
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))