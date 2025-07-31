# fsm_designer_project/managers/theme_manager.py
import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from PyQt5.QtCore import QObject, pyqtSignal, QStandardPaths, QDir, QFileSystemWatcher, pyqtSlot
from PyQt5.QtGui import QColor

# --- NEW: Local import of config for dynamic modification ---
from ..utils import config

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

    # --- NEW: Theme data and keys are now class constants ---
    THEME_DATA_LIGHT = {
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

    THEME_DATA_DARK = {
        "COLOR_BACKGROUND_APP": "#263238", "COLOR_BACKGROUND_LIGHT": "#37474F",
        "COLOR_BACKGROUND_MEDIUM": "#455A64", "COLOR_BACKGROUND_DARK": "#546E7A",
        "COLOR_BACKGROUND_EDITOR_DARK": "#1A2428", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#CFD8DC",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#78909C", "COLOR_BACKGROUND_DIALOG": "#37474F",
        "COLOR_TEXT_PRIMARY": "#ECEFF1", "COLOR_TEXT_SECONDARY": "#B0BEC5",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#4FC3F7",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#81D4FA", "COLOR_ACCENT_SECONDARY": "#FFB74D",
        "COLOR_ACCENT_SUCCESS": "#81C784", "COLOR_ACCENT_WARNING": "#FFD54F",
        "COLOR_ACCENT_ERROR": "#E57373", "COLOR_BORDER_LIGHT": "#546E7A",
        "COLOR_BORDER_MEDIUM": "#78909C", "COLOR_BORDER_DARK": "#90A4AE",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#4A6572", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#78909C",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#4DB6AC", "COLOR_ITEM_COMMENT_BG": "#424242",
        "COLOR_ITEM_COMMENT_BORDER": "#616161", "COLOR_GRID_MINOR": "#455A64",
        "COLOR_GRID_MAJOR": "#546E7A", "COLOR_DRAGGABLE_BUTTON_BG": "#37474F",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#546E7A", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#546E7A",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#4FC3F7", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#62757f"
    }
    
    THEME_DATA_CRIMSON = {
        "COLOR_BACKGROUND_APP": "#800000",
        "COLOR_BACKGROUND_LIGHT": "#FFFFFF",
        "COLOR_BACKGROUND_MEDIUM": "#F0F0F0",
        "COLOR_BACKGROUND_DARK": "#E0E0E0",
        "COLOR_BACKGROUND_EDITOR_DARK": "#2A2121",
        "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#F0E6E6",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#A09696",
        "COLOR_BACKGROUND_DIALOG": "#FAFAFA",
        "COLOR_TEXT_PRIMARY": "#212121",
        "COLOR_TEXT_SECONDARY": "#757575",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF",
        "COLOR_ACCENT_PRIMARY": "#0078D7",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#CDE5F7",
        "COLOR_ACCENT_SECONDARY": "#C586C0",
        "COLOR_ACCENT_SUCCESS": "#28A745",
        "COLOR_ACCENT_WARNING": "#FFC107",
        "COLOR_ACCENT_ERROR": "#DC3545",
        "COLOR_BORDER_LIGHT": "#DCDCDC",
        "COLOR_BORDER_MEDIUM": "#C0C0C0",
        "COLOR_BORDER_DARK": "#A9A9A9",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#E3F2FD",
        "COLOR_ITEM_STATE_DEFAULT_BORDER": "#64B5F6",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#00796B",
        "COLOR_ITEM_COMMENT_BG": "#FFF9C4",
        "COLOR_ITEM_COMMENT_BORDER": "#FFEE58",
        "COLOR_GRID_MINOR": "#F0F0F0",
        "COLOR_GRID_MAJOR": "#E0E0E0",
        "COLOR_DRAGGABLE_BUTTON_BG": "#FAFAFA",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#DCDCDC",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#E6F2FA",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#0078D7",
        "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#CCE4F7"
    }

    THEME_KEYS = list(THEME_DATA_LIGHT.keys())
    # --- END NEW ---

    def __init__(self, app_name: str = "BSMDesigner", parent: Optional[QObject] = None):
        super().__init__(parent)
        self.app_name = app_name
        self.themes: Dict[str, Dict[str, str]] = {}
        self._theme_cache: Dict[str, Dict[str, QColor]] = {}
        self._file_watcher: Optional[QFileSystemWatcher] = None
        
        self._initialize_paths()
        self._setup_file_watcher()
        self.load_themes()

    # ... ( _initialize_paths, _get_config_path, _setup_file_watcher, _on_file_changed remain the same) ...

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
        # --- MODIFIED: Use class constants for default themes ---
        self.themes = {
            "Light": self.THEME_DATA_LIGHT.copy(),
            "Dark": self.THEME_DATA_DARK.copy(),
            "Crimson": self.THEME_DATA_CRIMSON.copy()
        }

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
        for key in self.THEME_KEYS:
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
        return name in ["Light", "Dark", "Crimson"]

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
        for key in self.THEME_KEYS:
            if key not in t:
                t[key] = self.THEME_DATA_DARK[key] if is_dark else self.THEME_DATA_LIGHT[key]
                logger.warning(f"Key '{key}' was missing during theme derivation; used fallback.")
        return t

    # --- NEW: Moved from config.py ---
    def get_current_stylesheet(self, theme_data: Dict[str, str]) -> str:
        """
        Generates the application-wide stylesheet from a theme dictionary.
        """
        is_dark = QColor(theme_data["COLOR_BACKGROUND_APP"]).lightnessF() < 0.5
        grad_stop_1 = QColor(theme_data["COLOR_BACKGROUND_MEDIUM"]).lighter(105 if is_dark else 102).name()
        grad_stop_2 = QColor(theme_data["COLOR_BACKGROUND_MEDIUM"]).darker(102 if is_dark else 98).name()
        
        return f"""
        QWidget {{
            font-family: {config.APP_FONT_FAMILY};
            font-size: {config.APP_FONT_SIZE_STANDARD};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QMainWindow {{
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
        }}
        QDockWidget::title {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {grad_stop_1}, stop:1 {grad_stop_2});
            padding: 6px 10px 6px 48px;
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-bottom: 2px solid {theme_data['COLOR_ACCENT_PRIMARY']};
            font-weight: bold;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }}
        QDockWidget {{
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QDockWidget QWidget {{
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
        }}
        QDockWidget::close-button {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 6px;
            top: 4px;
        }}
        QDockWidget::float-button {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 26px;
            top: 4px;
        }}
        QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
            background-color: {theme_data['COLOR_BACKGROUND_DARK']};
        }}
        QToolBar {{
            background-color: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            border-bottom: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            padding: 2px;
            spacing: 3px;
        }}
        QToolButton {{
            background-color: transparent;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            padding: 4px 6px;
            margin: 0px;
            border: 1px solid transparent;
            border-radius: 3px;
        }}
        QToolButton:hover, QDockWidget#ElementsPaletteDock QToolButton:hover {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
            border: 1px solid {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(130).name() if QColor(theme_data['COLOR_ACCENT_PRIMARY_LIGHT']).lightnessF() > 0.6 else theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        QToolButton:pressed, QDockWidget#ElementsPaletteDock QToolButton:pressed {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        QToolButton:checked, QDockWidget#ElementsPaletteDock QToolButton:checked {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            border: 1px solid {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(120).name()};
        }}
        QToolBar QToolButton:disabled {{
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            background-color: transparent;
        }}
        QMenuBar {{
            background-color: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-bottom: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            padding: 2px;
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 10px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QMenuBar::item:selected {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
            color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(130).name() if QColor(theme_data['COLOR_ACCENT_PRIMARY_LIGHT']).lightnessF() > 0.6 else theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QMenuBar::item:pressed {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        QMenu {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            border-radius: 3px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 5px 25px 5px 25px;
            border-radius: 3px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QMenu::item:selected {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {theme_data['COLOR_BORDER_LIGHT']};
            margin: 4px 6px;
        }}
        QMenu::icon {{
            padding-left: 5px;
        }}
        QStatusBar {{
            background-color: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-top: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            padding: 2px 4px;
        }}
        QStatusBar::item {{
            border: none;
            margin: 0 2px;
        }}
        QLabel#StatusLabel, QLabel#MatlabStatusLabel, QLabel#PySimStatusLabel, QLabel#AIChatStatusLabel, QLabel#InternetStatusLabel,
        QLabel#MainOpStatusLabel, QLabel#IdeFileStatusLabel,
        QMainWindow QLabel[objectName$="StatusLabel"],
        QLabel#ZoomStatusLabel, QLabel#InteractionModeStatusLabel
        {{
             padding: 1px 4px;
             font-size: {config.APP_FONT_SIZE_SMALL};
             border-radius: 2px;
             color: {theme_data['COLOR_TEXT_SECONDARY']};
        }}
        QLabel#CpuStatusLabel, QLabel#RamStatusLabel, QLabel#GpuStatusLabel {{
            font-size: {config.APP_FONT_SIZE_SMALL};
            padding: 1px 4px;
            min-width: 60px;
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
            border-radius: 2px;
            color: {theme_data['COLOR_TEXT_SECONDARY']};
        }}
        QDialog {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QDialog QLabel, QDialog QCheckBox, QDialog QRadioButton, QDialog QSpinBox, QDialog QDoubleSpinBox, QDialog QFontComboBox {{
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QLabel {{
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            background-color: transparent;
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lightnessF() > 0.5 else 115).name()};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            border-radius: 3px;
            padding: 5px 7px;
            font-size: {config.APP_FONT_SIZE_STANDARD};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 1.5px solid {theme_data['COLOR_ACCENT_PRIMARY']};
            outline: none;
        }}
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
            background-color: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            border-color: {theme_data['COLOR_BORDER_LIGHT']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 22px;
            border-left-width: 1px;
            border-left-color: {theme_data['COLOR_BORDER_MEDIUM']};
            border-left-style: solid;
            border-top-right-radius: 2px;
            border-bottom-right-radius: 2px;
            background-color: {QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lightnessF() > 0.5 else 110).name()};
        }}
        QComboBox::drop-down:hover {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
        }}
        QComboBox::down-arrow {{
             image: url(:/icons/arrow_down.png);
             width: 10px; height:10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            selection-background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            selection-color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            border-radius: 2px;
            padding: 1px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QPushButton {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            padding: 6px 15px;
            border-radius: 4px;
            min-height: 22px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {QColor(grad_stop_1).lighter(105).name()}, stop: 1 {QColor(grad_stop_2).lighter(105).name()});
            border-color: {theme_data['COLOR_BORDER_DARK']};
        }}
        QPushButton:pressed {{
            background-color: {QColor(theme_data['COLOR_BACKGROUND_DARK']).name()};
        }}
        QPushButton:disabled {{
            background-color: {QColor(theme_data['COLOR_BACKGROUND_LIGHT']).darker(102 if QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lightnessF() < 0.5 else 95).name()};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            border-color: {theme_data['COLOR_BORDER_LIGHT']};
        }}
        QDialogButtonBox QPushButton {{
            min-width: 80px;
        }}
        QDialogButtonBox QPushButton[text="OK"], QDialogButtonBox QPushButton[text="OK & Save"], QDialogButtonBox QPushButton[text="Apply & Close"],
        QDialogButtonBox QPushButton[text="Save"], QDialogButtonBox QPushButton[text="Apply"]
        {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            border-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(120).name()};
            font-weight: bold;
        }}
        QDialogButtonBox QPushButton[text="OK"]:hover, QDialogButtonBox QPushButton[text="OK & Save"]:hover, QDialogButtonBox QPushButton[text="Apply & Close"]:hover,
        QDialogButtonBox QPushButton[text="Save"]:hover, QDialogButtonBox QPushButton[text="Apply"]:hover
        {{
            background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()};
        }}
        QDialogButtonBox QPushButton[text="Cancel"], QDialogButtonBox QPushButton[text="Discard"],
        QDialogButtonBox QPushButton[text="Close"]
        {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-color: {theme_data['COLOR_BORDER_MEDIUM']};
        }}
        QDialogButtonBox QPushButton[text="Cancel"]:hover, QDialogButtonBox QPushButton[text="Discard"]:hover,
        QDialogButtonBox QPushButton[text="Close"]:hover
        {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {QColor(grad_stop_1).darker(105).name()}, stop: 1 {QColor(grad_stop_2).darker(105).name()});
        }}
        QGroupBox {{
            background-color: transparent;
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-radius: 4px;
            margin-top: 10px;
            padding: 10px 8px 8px 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 10px;
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
            color: {theme_data['COLOR_ACCENT_PRIMARY']};
            font-weight: bold;
            border-radius: 2px;
        }}
        QTabWidget::pane {{
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-top: none;
            border-bottom-left-radius: 3px;
            border-bottom-right-radius: 3px;
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            padding: 6px;
        }}
        QTabBar::tab {{
            background: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-bottom-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
            padding: 6px 15px;
            margin-right: 1px;
            min-width: 70px;
        }}
        QTabBar::tab:selected {{
            background: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            font-weight: bold;
            border-bottom-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
        }}
        QTabBar::tab:!selected:hover {{
            background: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-bottom-color: {theme_data['COLOR_BORDER_LIGHT']};
        }}
        QCheckBox {{
            spacing: 8px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
        }}
        QCheckBox::indicator:unchecked {{
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            border-radius: 2px;
            background-color: {QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lightnessF() > 0.5 else 110).name()};
        }}
        QCheckBox::indicator:unchecked:hover {{
            border: 1px solid {theme_data['COLOR_ACCENT_PRIMARY']};
        }}
        QCheckBox::indicator:checked {{
            border: 1px solid {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(120).name()};
            border-radius: 2px;
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            image: url(:/icons/check.png);
        }}
        QCheckBox::indicator:checked:hover {{
            background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()};
        }}
        QTextEdit#LogOutputWidget, QTextEdit#PySimActionLog, QTextBrowser#AIChatDisplay,
        QPlainTextEdit#ActionCodeEditor, QTextEdit#IDEOutputConsole, QPlainTextEdit#StandaloneCodeEditor,
        QTextEdit#SubFSMJsonEditor, QPlainTextEdit#LivePreviewEditor
        {{
             font-family: Consolas, 'Courier New', monospace;
             font-size: {config.APP_FONT_SIZE_EDITOR};
             background-color: {theme_data['COLOR_BACKGROUND_EDITOR_DARK']};
             color: {theme_data['COLOR_TEXT_EDITOR_DARK_PRIMARY']};
             border: 1px solid {theme_data['COLOR_BORDER_DARK']};
             border-radius: 3px;
             padding: 6px;
             selection-background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(110).name()};
             selection-color: {theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        QScrollBar:vertical {{
             border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
             background: {QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lightnessF() > 0.5 else 110).name()};
             width: 14px;
             margin: 0px;
        }}
        QScrollBar::handle:vertical {{
             background: {theme_data['COLOR_BORDER_DARK']};
             min-height: 25px;
             border-radius: 7px;
        }}
        QScrollBar::handle:vertical:hover {{
             background: {QColor(theme_data['COLOR_BORDER_DARK']).lighter(120).name()};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
             height: 0px;
             background: transparent;
        }}
        QScrollBar:horizontal {{
             border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
             background: {QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lightnessF() > 0.5 else 110).name()};
             height: 14px;
             margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
             background: {theme_data['COLOR_BORDER_DARK']};
             min-width: 25px;
             border-radius: 7px;
        }}
        QScrollBar::handle:horizontal:hover {{
             background: {QColor(theme_data['COLOR_BORDER_DARK']).lighter(120).name()};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
             width: 0px;
             background: transparent;
        }}

        /* Editor specific scrollbars */
        QTextEdit#LogOutputWidget QScrollBar:vertical, QTextEdit#PySimActionLog QScrollBar:vertical,
        QTextBrowser#AIChatDisplay QScrollBar:vertical, QPlainTextEdit#ActionCodeEditor QScrollBar:vertical,
        QTextEdit#IDEOutputConsole QScrollBar:vertical, QPlainTextEdit#StandaloneCodeEditor QScrollBar:vertical,
        QTextEdit#SubFSMJsonEditor QScrollBar:vertical
        {{
             border: 1px solid {theme_data['COLOR_BORDER_DARK']};
             background: {QColor(theme_data['COLOR_BACKGROUND_EDITOR_DARK']).lighter(110).name()};
        }}
        QTextEdit#LogOutputWidget QScrollBar::handle:vertical, QTextEdit#PySimActionLog QScrollBar::handle:vertical,
        QTextBrowser#AIChatDisplay QScrollBar::handle:vertical, QPlainTextEdit#ActionCodeEditor QScrollBar::handle:vertical,
        QTextEdit#IDEOutputConsole QScrollBar::handle:vertical, QPlainTextEdit#StandaloneCodeEditor QScrollBar::vertical,
        QTextEdit#SubFSMJsonEditor QScrollBar::handle:vertical
        {{
             background: {theme_data['COLOR_TEXT_EDITOR_DARK_SECONDARY']};
        }}
        QTextEdit#LogOutputWidget QScrollBar::handle:vertical:hover, QTextEdit#PySimActionLog QScrollBar::handle:vertical:hover,
        QTextBrowser#AIChatDisplay QScrollBar::handle:vertical:hover, QPlainTextEdit#ActionCodeEditor QScrollBar::handle:vertical:hover,
        QTextEdit#IDEOutputConsole QScrollBar::handle:vertical:hover, QPlainTextEdit#StandaloneCodeEditor QScrollBar::handle:vertical:hover,
        QTextEdit#SubFSMJsonEditor QScrollBar::handle:vertical:hover
        {{
             background: {QColor(theme_data['COLOR_TEXT_EDITOR_DARK_SECONDARY']).lighter(120).name()};
        }}

        QPushButton#SnippetButton {{
            background-color: {theme_data['COLOR_ACCENT_SECONDARY']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {QColor(theme_data['COLOR_ACCENT_SECONDARY']).darker(130).name()};
            font-weight: normal;
            padding: 4px 8px;
            min-height: 0;
        }}
        QPushButton#SnippetButton:hover {{
            background-color: {QColor(theme_data['COLOR_ACCENT_SECONDARY']).lighter(110).name()};
        }}
        QPushButton#ColorButton, QPushButton#ColorButtonPropertiesDock {{
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']}; min-height: 24px; padding: 3px;
        }}
        QPushButton#ColorButton:hover, QPushButton#ColorButtonPropertiesDock:hover {{
            border: 1px solid {theme_data['COLOR_ACCENT_PRIMARY']};
        }}
        QProgressBar {{
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']}; border-radius: 3px;
            background-color: {theme_data['COLOR_BACKGROUND_LIGHT']}; text-align: center;
            color: {theme_data['COLOR_TEXT_PRIMARY']}; height: 12px;
        }}
        QProgressBar::chunk {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']}; border-radius: 2px;
        }}
        QPushButton#DraggableToolButton {{
            background-color: {theme_data['COLOR_DRAGGABLE_BUTTON_BG']}; color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_DRAGGABLE_BUTTON_BORDER']};
            padding: 5px 7px;
            text-align: left;
            font-weight: 500;
            min-height: 32px;
        }}
        QPushButton#DraggableToolButton:hover {{
            background-color: {QColor(theme_data['COLOR_DRAGGABLE_BUTTON_HOVER_BG']).name() if isinstance(theme_data['COLOR_DRAGGABLE_BUTTON_HOVER_BG'], QColor) else theme_data['COLOR_DRAGGABLE_BUTTON_HOVER_BG']};
            border-color: {theme_data['COLOR_DRAGGABLE_BUTTON_HOVER_BORDER']};
        }}
        QPushButton#DraggableToolButton:pressed {{ background-color: {QColor(theme_data['COLOR_DRAGGABLE_BUTTON_PRESSED_BG']).name() if isinstance(theme_data['COLOR_DRAGGABLE_BUTTON_PRESSED_BG'], QColor) else theme_data['COLOR_DRAGGABLE_BUTTON_PRESSED_BG']}; }}

        #PropertiesDock QLabel#PropertiesLabel {{
            padding: 6px; background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']}; border-radius: 3px;
            font-size: {config.APP_FONT_SIZE_STANDARD};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        #PropertiesDock QPushButton {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']}; color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            font-weight:bold;
        }}
        #PropertiesDock QPushButton:hover {{ background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()}; }}

        QDockWidget#ElementsPaletteDock QToolButton {{
            padding: 6px 8px; text-align: left;
            min-height: 34px;
            font-weight: 500;
        }}
        QDockWidget#ElementsPaletteDock QGroupBox {{
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QDockWidget#ElementsPaletteDock QGroupBox::title {{
            color: {theme_data['COLOR_ACCENT_PRIMARY']};
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
        }}


        QDockWidget#PySimDock QPushButton {{
            padding: 5px 10px;
        }}
        QDockWidget#PySimDock QPushButton:disabled {{
            background-color: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
        }}
        QDockWidget#PySimDock QTableWidget {{
            alternate-background-color: {QColor(theme_data['COLOR_BACKGROUND_APP']).lighter(105 if QColor(theme_data['COLOR_BACKGROUND_APP']).lightnessF() > 0.5 else 115).name()};
            gridline-color: {theme_data['COLOR_BORDER_LIGHT']};
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
         QDockWidget#PySimDock QHeaderView::section,
         QTableWidget QHeaderView::section
         {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
            padding: 4px;
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-bottom: 2px solid {theme_data['COLOR_BORDER_DARK']};
            font-weight: bold;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QDockWidget#AIChatbotDock QPushButton#AIChatSendButton,
        QDockWidget#PySimDock QPushButton[text="Trigger"]
        {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']}; color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            font-weight: bold;
            padding: 5px;
            min-width: 0;
        }}
        QDockWidget#AIChatbotDock QPushButton#AIChatSendButton:hover,
        QDockWidget#PySimDock QPushButton[text="Trigger"]:hover
        {{
            background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()};
        }}
        QDockWidget#AIChatbotDock QPushButton#AIChatSendButton:disabled,
        QDockWidget#PySimDock QPushButton[text="Trigger"]:disabled
        {{
            background-color: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            border-color: {theme_data['COLOR_BORDER_LIGHT']};
        }}
        QLineEdit#AIChatInput, QLineEdit#PySimEventNameEdit
        {{
            padding: 6px 8px;
        }}
        QDockWidget#ProblemsDock QListWidget {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QDockWidget#ProblemsDock QListWidget::item {{
            padding: 4px;
            border-bottom: 1px dotted {theme_data['COLOR_BORDER_LIGHT']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        QDockWidget#ProblemsDock QListWidget::item:selected {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
            color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(130).name() if QColor(theme_data['COLOR_ACCENT_PRIMARY_LIGHT']).lightnessF() > 0.6 else theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        QLabel#ErrorLabel {{
            color: {theme_data['COLOR_ACCENT_ERROR']};
            font-weight: bold;
        }}
        QLabel#HardwareHintLabel {{
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            font-style: italic;
            font-size: 7.5pt;
        }}
        QLabel#SafetyNote {{
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            font-style: italic;
            font-size: {config.APP_FONT_SIZE_SMALL};
        }}
        QGroupBox#IDEOutputGroup, QGroupBox#IDEToolbarGroup {{
        }}
        """
    
    # --- NEW: Moved from config.py ---
    def update_dynamic_config_colors(self, theme_data: dict):
        """
        Populates the global color variables in the config module.
        """
        for key, value in theme_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.COLOR_PY_SIM_STATE_ACTIVE = QColor(config.COLOR_ACCENT_SUCCESS)
        
        accent_secondary_color = QColor(config.COLOR_ACCENT_SECONDARY)
        config.COLOR_ITEM_STATE_SELECTION_BG = accent_secondary_color.lighter(180 if accent_secondary_color.lightnessF() < 0.5 else 130).name()
        config.COLOR_ITEM_STATE_SELECTION_BORDER = accent_secondary_color.name()
        
        accent_primary_color = QColor(config.COLOR_ACCENT_PRIMARY)
        config.COLOR_ITEM_TRANSITION_SELECTION = accent_primary_color.lighter(160 if accent_primary_color.lightnessF() < 0.5 else 130).name()