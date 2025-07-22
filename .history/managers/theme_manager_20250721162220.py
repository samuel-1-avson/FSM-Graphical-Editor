# fsm_designer_project/managers/theme_manager.py
import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from PyQt5.QtCore import QObject, pyqtSignal, QStandardPaths, QDir, QFileSystemWatcher, pyqtSlot
from PyQt5.QtGui import QColor

# --- Import from the new assets.py or a data module in a larger refactor ---
# For now, we keep the direct config import but acknowledge it should change
from ..utils.config import (
    THEME_DATA_LIGHT, THEME_DATA_DARK, THEME_KEYS, APP_FONT_FAMILY,
    APP_FONT_SIZE_STANDARD, APP_FONT_SIZE_SMALL, APP_FONT_SIZE_EDITOR
)

logger = logging.getLogger(__name__)
DEFAULT_THEME_FILENAME = "user_themes.json"
BACKUP_THEME_FILENAME = "user_themes_backup.json"

class ThemeValidationError(Exception):
    """Custom exception for theme validation errors."""
    pass

class ThemeManager(QObject):
    """
    Enhanced theme manager with validation, stylesheet generation, and file watching.
    Manages loading, saving, and applying visual themes for the application.
    """
    
    themesChanged = pyqtSignal()
    themeAdded = pyqtSignal(str)      # theme_name
    themeRemoved = pyqtSignal(str)    # theme_name
    themeModified = pyqtSignal(str)   # theme_name
    loadError = pyqtSignal(str)       # error_message

    def __init__(self, app_name: str = "BSMDesigner", parent: Optional[QObject] = None):
        super().__init__(parent)
        self.app_name = app_name
        self.themes: Dict[str, Dict[str, str]] = {}
        self._theme_cache: Dict[str, Dict[str, QColor]] = {}
        self._file_watcher: Optional[QFileSystemWatcher] = None
        
        self._initialize_paths()
        self._setup_file_watcher()
        self.load_themes()

    def _initialize_paths(self) -> None:
        """Initialize storage paths with fallback options."""
        config_path = self._get_config_path()
        
        if not QDir(config_path).exists():
            if not QDir().mkpath(config_path):
                logger.error(f"Failed to create config directory: {config_path}")
                raise RuntimeError(f"Cannot create config directory: {config_path}")

        self.theme_file_path = os.path.join(config_path, DEFAULT_THEME_FILENAME)
        self.backup_file_path = os.path.join(config_path, BACKUP_THEME_FILENAME)
        logger.info(f"Theme storage path: {self.theme_file_path}")

    def _get_config_path(self) -> str:
        """Get the appropriate configuration path with fallbacks."""
        config_path = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        
        if not config_path:
            config_path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            if config_path and self.app_name:
                config_path = os.path.join(config_path, self.app_name)
        
        if not config_path:
            config_path = os.path.join(os.getcwd(), ".config", self.app_name)
            logger.warning(f"Using fallback config path: {config_path}")
        
        return config_path

    def _setup_file_watcher(self) -> None:
        """Set up file system watcher for automatic theme reloading."""
        try:
            self._file_watcher = QFileSystemWatcher(self)
            self._file_watcher.fileChanged.connect(self._on_file_changed)
            
            if os.path.exists(self.theme_file_path):
                self._file_watcher.addPath(self.theme_file_path)
        except Exception as e:
            logger.warning(f"Could not set up file watcher: {e}")

    @pyqtSlot(str)
    def _on_file_changed(self, path: str) -> None:
        """Handle file change events."""
        if path == self.theme_file_path:
            logger.info("Theme file changed externally, reloading themes.")
            self.load_themes()

    def load_themes(self) -> None:
        """Load default and user-defined themes with error handling."""
        self._theme_cache.clear()
        self.themes = {"Light": THEME_DATA_LIGHT.copy(), "Dark": THEME_DATA_DARK.copy()}

        if not os.path.exists(self.theme_file_path):
            logger.info("User themes file not found. Using default themes only.")
            self.themesChanged.emit()
            return

        try:
            with open(self.theme_file_path, 'r', encoding='utf-8') as f:
                user_themes = json.load(f)

            if not isinstance(user_themes, dict):
                raise ThemeValidationError("Theme file must contain a JSON object.")

            for theme_name, theme_data in user_themes.items():
                try:
                    self.themes[theme_name] = self._validate_theme_data(theme_name, theme_data)
                except ThemeValidationError as e:
                    logger.warning(f"Skipping invalid theme '{theme_name}': {e}")
        except Exception as e:
            error_msg = f"Failed to load user themes: {e}"
            logger.error(error_msg)
            self.loadError.emit(error_msg)
        
        self.themesChanged.emit()

    def _validate_theme_data(self, theme_name: str, theme_data: Any) -> Dict[str, str]:
        """Validate theme data structure and colors."""
        if not isinstance(theme_data, dict):
            raise ThemeValidationError("Theme data must be a dictionary.")

        validated_data = {}
        for key in THEME_KEYS:
            if key not in theme_data:
                raise ThemeValidationError(f"Missing required key '{key}'.")
            
            color_value = theme_data[key]
            if not isinstance(color_value, str) or not QColor(color_value).isValid():
                raise ThemeValidationError(f"Invalid color value '{color_value}' for key '{key}'.")
                
            validated_data[key] = QColor(color_value).name()

        return validated_data
        
    def save_theme(self, name: str, data: Dict[str, str]) -> bool:
        """Adds or updates a single user theme and saves all user themes to file."""
        if self.is_default_theme(name):
            logger.error(f"Cannot overwrite a default theme: '{name}'.")
            return False

        try:
            self.themes[name] = self._validate_theme_data(name, data)
            return self._save_user_themes_to_disk()
        except ThemeValidationError as e:
            logger.error(f"Failed to save theme '{name}' due to validation error: {e}")
            return False

    def delete_theme(self, name: str) -> bool:
        """Deletes a user-defined theme."""
        if self.is_default_theme(name):
            logger.warning(f"Cannot delete default theme: '{name}'.")
            return False
        
        if name in self.themes:
            del self.themes[name]
            self._theme_cache.pop(name, None)
            return self._save_user_themes_to_disk()
        return False
        
    def _save_user_themes_to_disk(self) -> bool:
        """Internal helper to save all non-default themes to the JSON file."""
        user_themes = {
            name: data for name, data in self.themes.items() if not self.is_default_theme(name)
        }
        
        try:
            temp_file_path = self.theme_file_path + ".tmp"
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                json.dump(user_themes, f, indent=2, sort_keys=True, ensure_ascii=False)
            
            os.replace(temp_file_path, self.theme_file_path)
            
            if self._file_watcher and self.theme_file_path not in self._file_watcher.files():
                self._file_watcher.addPath(self.theme_file_path)

            self.themesChanged.emit()
            return True
        except Exception as e:
            logger.error(f"Failed to save user themes to disk: {e}", exc_info=True)
            return False

    def get_theme_names(self) -> List[str]:
        return sorted(self.themes.keys())

    def is_default_theme(self, name: str) -> bool:
        return name in ["Light", "Dark"]

    def get_theme_data(self, name: str) -> Optional[Dict[str, str]]:
        return self.themes.get(name)
        
    def derive_theme_from_palette(self, core_palette: Dict[str, str]) -> Dict[str, str]:
        """Generate a full theme dictionary from a small set of core palette colors."""
        p = {key: QColor(value) for key, value in core_palette.items()}
        is_dark = p["COLOR_BACKGROUND_APP"].lightnessF() < 0.5
        
        t = {} # The derived theme dictionary
        
        # Direct assignments
        t.update({key: val.name() for key, val in p.items()})

        # Logic-based derivations
        t["COLOR_BACKGROUND_LIGHT"]    = p["COLOR_BACKGROUND_APP"].lighter(110 if is_dark else 102).name()
        t["COLOR_BACKGROUND_MEDIUM"]   = p["COLOR_BACKGROUND_APP"].lighter(125 if is_dark else 95).name()
        t["COLOR_BACKGROUND_DARK"]     = p["COLOR_BACKGROUND_APP"].lighter(140 if is_dark else 90).name()
        t["COLOR_BACKGROUND_DIALOG"]  = t["COLOR_BACKGROUND_LIGHT"]
        t["COLOR_TEXT_SECONDARY"]      = p["COLOR_TEXT_PRIMARY"].lighter(150 if is_dark else 80).name()
        t["COLOR_TEXT_ON_ACCENT"]      = "#FFFFFF" if p["COLOR_ACCENT_PRIMARY"].lightnessF() < 0.6 else "#000000"
        t["COLOR_ACCENT_PRIMARY_LIGHT"]= p["COLOR_ACCENT_PRIMARY"].lighter(120).name()

        t["COLOR_TEXT_EDITOR_DARK_PRIMARY"] = QColor(p["COLOR_BACKGROUND_EDITOR_DARK"]).lighter(180).name()
        t["COLOR_TEXT_EDITOR_DARK_SECONDARY"] = QColor(p["COLOR_BACKGROUND_EDITOR_DARK"]).lighter(140).name()
        
        t["COLOR_BORDER_LIGHT"]        = t["COLOR_BACKGROUND_MEDIUM"]
        t["COLOR_BORDER_MEDIUM"]       = t["COLOR_BACKGROUND_DARK"]
        t["COLOR_BORDER_DARK"]         = QColor(t["COLOR_BACKGROUND_DARK"]).lighter(115 if is_dark else 90).name()
        
        t["COLOR_ITEM_STATE_DEFAULT_BG"]      = p["COLOR_ACCENT_PRIMARY"].lighter(180 if is_dark else 160).name()
        t["COLOR_ITEM_STATE_DEFAULT_BORDER"]  = p["COLOR_ACCENT_PRIMARY"].name()
        t["COLOR_ITEM_TRANSITION_DEFAULT"]    = p["COLOR_ACCENT_SECONDARY"].name()
        t["COLOR_ITEM_COMMENT_BG"]            = p["COLOR_ACCENT_WARNING"].lighter(185 if is_dark else 165).name()
        t["COLOR_ITEM_COMMENT_BORDER"]        = p["COLOR_ACCENT_WARNING"].darker(110).name()
        
        t["COLOR_GRID_MINOR"] = t["COLOR_BACKGROUND_MEDIUM"]
        t["COLOR_GRID_MAJOR"] = t["COLOR_BACKGROUND_DARK"]
        
        t["COLOR_DRAGGABLE_BUTTON_BG"] = t["COLOR_BACKGROUND_LIGHT"]
        t["COLOR_DRAGGABLE_BUTTON_BORDER"] = t["COLOR_BORDER_LIGHT"]
        t["COLOR_DRAGGABLE_BUTTON_HOVER_BG"] = t["COLOR_ACCENT_PRIMARY_LIGHT"]
        t["COLOR_DRAGGABLE_BUTTON_HOVER_BORDER"] = t["COLOR_ACCENT_PRIMARY"]
        t["COLOR_DRAGGABLE_BUTTON_PRESSED_BG"] = p["COLOR_ACCENT_PRIMARY"].darker(110).name()

        # Ensure all keys are present
        for key in THEME_KEYS:
            if key not in t:
                t[key] = THEME_DATA_DARK[key] if is_dark else THEME_DATA_LIGHT[key]
                logger.warning(f"Key '{key}' was missing during theme derivation; used fallback.")
        return t

    def get_current_stylesheet(self, theme_data: Dict[str, str]) -> str:
        """
        Generates the application-wide stylesheet from a theme dictionary.
        This function was moved here from config.py for better encapsulation.
        """
        is_dark = QColor(theme_data["COLOR_BACKGROUND_APP"]).lightnessF() < 0.5
        grad_stop_1 = QColor(theme_data["COLOR_BACKGROUND_MEDIUM"]).lighter(105 if is_dark else 102).name()
        grad_stop_2 = QColor(theme_data["COLOR_BACKGROUND_MEDIUM"]).darker(102 if is_dark else 98).name()
        
        # Dynamically create the string by accessing the theme_data dictionary
        return f"""
        QWidget {{
            font-family: {APP_FONT_FAMILY};
            font-size: {APP_FONT_SIZE_STANDARD};
            color: {theme_data["COLOR_TEXT_PRIMARY"]};
        }}
        QMainWindow {{
            background-color: {theme_data["COLOR_BACKGROUND_APP"]};
        }}
        QDockWidget::title {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {grad_stop_1}, stop:1 {grad_stop_2});
            padding: 6px 10px 6px 48px;
            border: 1px solid {theme_data["COLOR_BORDER_LIGHT"]};
            border-bottom: 2px solid {theme_data["COLOR_ACCENT_PRIMARY"]};
            font-weight: bold;
            color: {theme_data["COLOR_TEXT_PRIMARY"]};
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }}
        QDialog {{
            background-color: {theme_data["COLOR_BACKGROUND_DIALOG"]};
            color: {theme_data["COLOR_TEXT_PRIMARY"]};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {QColor(theme_data["COLOR_BACKGROUND_DIALOG"]).lighter(102 if is_dark else 115).name()};
            color: {theme_data["COLOR_TEXT_PRIMARY"]};
            border: 1px solid {theme_data["COLOR_BORDER_MEDIUM"]};
            border-radius: 3px;
            padding: 5px 7px;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 1.5px solid {theme_data["COLOR_ACCENT_PRIMARY"]};
            outline: none;
        }}
        QPushButton {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
            color: {theme_data["COLOR_TEXT_PRIMARY"]};
            border: 1px solid {theme_data["COLOR_BORDER_MEDIUM"]};
            padding: 6px 15px;
            border-radius: 4px;
            min-height: 22px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {QColor(grad_stop_1).lighter(105).name()}, stop: 1 {QColor(grad_stop_2).lighter(105).name()});
            border-color: {theme_data["COLOR_BORDER_DARK"]};
        }}
        QTextEdit#LogOutputWidget, QTextEdit#PySimActionLog, QTextBrowser#AIChatDisplay,
        QPlainTextEdit#ActionCodeEditor, QTextEdit#IDEOutputConsole, QPlainTextEdit#StandaloneCodeEditor,
        QTextEdit#SubFSMJsonEditor, QPlainTextEdit#LivePreviewEditor
        {{
            font-family: Consolas, 'Courier New', monospace;
            font-size: {APP_FONT_SIZE_EDITOR};
            background-color: {theme_data["COLOR_BACKGROUND_EDITOR_DARK"]};
            color: {theme_data["COLOR_TEXT_EDITOR_DARK_PRIMARY"]};
            border: 1px solid {theme_data["COLOR_BORDER_DARK"]};
            selection-background-color: {QColor(theme_data["COLOR_ACCENT_PRIMARY"]).darker(110).name()};
            selection-color: {theme_data["COLOR_TEXT_ON_ACCENT"]};
        }}
        /* --- ADD OTHER STYLESHEET RULES HERE AS NEEDED --- */
        """