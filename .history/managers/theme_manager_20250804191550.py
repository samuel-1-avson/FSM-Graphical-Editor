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

    # Professional Theme Definitions
    THEME_DATA_LIGHT = {
        "COLOR_BACKGROUND_APP": "#FAFAFA", "COLOR_BACKGROUND_LIGHT": "#FFFFFF",
        "COLOR_BACKGROUND_MEDIUM": "#F5F5F5", "COLOR_BACKGROUND_DARK": "#EEEEEE",
        "COLOR_BACKGROUND_EDITOR_DARK": "#FCFCFC", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#2C3E50",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#7F8C8D", "COLOR_BACKGROUND_DIALOG": "#FFFFFF",
        "COLOR_TEXT_PRIMARY": "#2C3E50", "COLOR_TEXT_SECONDARY": "#7F8C8D",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#3498DB",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#EBF3FD", "COLOR_ACCENT_SECONDARY": "#9B59B6",
        "COLOR_ACCENT_SUCCESS": "#27AE60", "COLOR_ACCENT_WARNING": "#F39C12",
        "COLOR_ACCENT_ERROR": "#E74C3C", "COLOR_BORDER_LIGHT": "#E1E8ED",
        "COLOR_BORDER_MEDIUM": "#CCD6DD", "COLOR_BORDER_DARK": "#AAB8C2",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#EBF3FD", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#3498DB",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#27AE60", "COLOR_ITEM_COMMENT_BG": "#FEF9E7",
        "COLOR_ITEM_COMMENT_BORDER": "#F39C12", "COLOR_GRID_MINOR": "#F8F9FA",
        "COLOR_GRID_MAJOR": "#E9ECEF", "COLOR_DRAGGABLE_BUTTON_BG": "#FFFFFF",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#E1E8ED", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#EBF3FD",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#3498DB", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#D6EAF8"
    }

    THEME_DATA_DARK = {
        "COLOR_BACKGROUND_APP": "#1E1E1E", "COLOR_BACKGROUND_LIGHT": "#2D2D30",
        "COLOR_BACKGROUND_MEDIUM": "#3E3E42", "COLOR_BACKGROUND_DARK": "#4D4D50",
        "COLOR_BACKGROUND_EDITOR_DARK": "#1E1E1E", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#CCCCCC",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#9CDCFE", "COLOR_BACKGROUND_DIALOG": "#2D2D30",
        "COLOR_TEXT_PRIMARY": "#CCCCCC", "COLOR_TEXT_SECONDARY": "#9A9A9A",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#007ACC",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#1E3A5F", "COLOR_ACCENT_SECONDARY": "#CE9178",
        "COLOR_ACCENT_SUCCESS": "#73C991", "COLOR_ACCENT_WARNING": "#FFCC02",
        "COLOR_ACCENT_ERROR": "#F14C4C", "COLOR_BORDER_LIGHT": "#3E3E42",
        "COLOR_BORDER_MEDIUM": "#4D4D50", "COLOR_BORDER_DARK": "#5A5A5A",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#1E3A5F", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#007ACC",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#73C991", "COLOR_ITEM_COMMENT_BG": "#3A3017",
        "COLOR_ITEM_COMMENT_BORDER": "#FFCC02", "COLOR_GRID_MINOR": "#2D2D30",
        "COLOR_GRID_MAJOR": "#3E3E42", "COLOR_DRAGGABLE_BUTTON_BG": "#2D2D30",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#3E3E42", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#1E3A5F",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#007ACC", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#1A334D"
    }
    
    # Professional Monochrome Theme
    THEME_DATA_MONOCHROME = {
        "COLOR_BACKGROUND_APP": "#FFFFFF", "COLOR_BACKGROUND_LIGHT": "#FFFFFF",
        "COLOR_BACKGROUND_MEDIUM": "#F8F9FA", "COLOR_BACKGROUND_DARK": "#E9ECEF",
        "COLOR_BACKGROUND_EDITOR_DARK": "#FDFDFD", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#212529",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#6C757D", "COLOR_BACKGROUND_DIALOG": "#FFFFFF",
        "COLOR_TEXT_PRIMARY": "#212529", "COLOR_TEXT_SECONDARY": "#6C757D",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#495057",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#F8F9FA", "COLOR_ACCENT_SECONDARY": "#6C757D",
        "COLOR_ACCENT_SUCCESS": "#28A745", "COLOR_ACCENT_WARNING": "#FFC107",
        "COLOR_ACCENT_ERROR": "#DC3545", "COLOR_BORDER_LIGHT": "#DEE2E6",
        "COLOR_BORDER_MEDIUM": "#CED4DA", "COLOR_BORDER_DARK": "#ADB5BD",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#F8F9FA", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#495057",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#6C757D", "COLOR_ITEM_COMMENT_BG": "#FFF3CD",
        "COLOR_ITEM_COMMENT_BORDER": "#FFEAA7", "COLOR_GRID_MINOR": "#F8F9FA",
        "COLOR_GRID_MAJOR": "#E9ECEF", "COLOR_DRAGGABLE_BUTTON_BG": "#FFFFFF",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#DEE2E6", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#F8F9FA",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#495057", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#E9ECEF"
    }

    # Professional Blue Theme
    THEME_DATA_PROFESSIONAL_BLUE = {
        "COLOR_BACKGROUND_APP": "#F7F9FC", "COLOR_BACKGROUND_LIGHT": "#FFFFFF",
        "COLOR_BACKGROUND_MEDIUM": "#F1F5F9", "COLOR_BACKGROUND_DARK": "#E2E8F0",
        "COLOR_BACKGROUND_EDITOR_DARK": "#FEFEFE", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#1E293B",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#64748B", "COLOR_BACKGROUND_DIALOG": "#FFFFFF",
        "COLOR_TEXT_PRIMARY": "#1E293B", "COLOR_TEXT_SECONDARY": "#64748B",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#2563EB",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#EFF6FF", "COLOR_ACCENT_SECONDARY": "#7C3AED",
        "COLOR_ACCENT_SUCCESS": "#059669", "COLOR_ACCENT_WARNING": "#D97706",
        "COLOR_ACCENT_ERROR": "#DC2626", "COLOR_BORDER_LIGHT": "#E2E8F0",
        "COLOR_BORDER_MEDIUM": "#CBD5E1", "COLOR_BORDER_DARK": "#94A3B8",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#EFF6FF", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#2563EB",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#059669", "COLOR_ITEM_COMMENT_BG": "#FFFBEB",
        "COLOR_ITEM_COMMENT_BORDER": "#D97706", "COLOR_GRID_MINOR": "#F8FAFC",
        "COLOR_GRID_MAJOR": "#F1F5F9", "COLOR_DRAGGABLE_BUTTON_BG": "#FFFFFF",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#E2E8F0", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#EFF6FF",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#2563EB", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#DBEAFE"
    }

    # Professional Dark Blue Theme  
    THEME_DATA_PROFESSIONAL_DARK = {
        "COLOR_BACKGROUND_APP": "#0F172A", "COLOR_BACKGROUND_LIGHT": "#1E293B",
        "COLOR_BACKGROUND_MEDIUM": "#334155", "COLOR_BACKGROUND_DARK": "#475569",
        "COLOR_BACKGROUND_EDITOR_DARK": "#0C1222", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#F1F5F9",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#94A3B8", "COLOR_BACKGROUND_DIALOG": "#1E293B",
        "COLOR_TEXT_PRIMARY": "#F1F5F9", "COLOR_TEXT_SECONDARY": "#CBD5E1",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#3B82F6",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#1E3A8A", "COLOR_ACCENT_SECONDARY": "#8B5CF6",
        "COLOR_ACCENT_SUCCESS": "#10B981", "COLOR_ACCENT_WARNING": "#F59E0B",
        "COLOR_ACCENT_ERROR": "#EF4444", "COLOR_BORDER_LIGHT": "#334155",
        "COLOR_BORDER_MEDIUM": "#475569", "COLOR_BORDER_DARK": "#64748B",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#1E3A8A", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#3B82F6",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#10B981", "COLOR_ITEM_COMMENT_BG": "#451A03",
        "COLOR_ITEM_COMMENT_BORDER": "#F59E0B", "COLOR_GRID_MINOR": "#1E293B",
        "COLOR_GRID_MAJOR": "#334155", "COLOR_DRAGGABLE_BUTTON_BG": "#1E293B",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#334155", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#1E3A8A",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#3B82F6", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#1E40AF"
    }

    # Minimal Gray Theme
    THEME_DATA_MINIMAL_GRAY = {
        "COLOR_BACKGROUND_APP": "#FAFAFA", "COLOR_BACKGROUND_LIGHT": "#FFFFFF",
        "COLOR_BACKGROUND_MEDIUM": "#F5F5F5", "COLOR_BACKGROUND_DARK": "#EEEEEE",
        "COLOR_BACKGROUND_EDITOR_DARK": "#FCFCFC", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#424242",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#757575", "COLOR_BACKGROUND_DIALOG": "#FFFFFF",
        "COLOR_TEXT_PRIMARY": "#424242", "COLOR_TEXT_SECONDARY": "#757575",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#616161",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#F5F5F5", "COLOR_ACCENT_SECONDARY": "#9E9E9E",
        "COLOR_ACCENT_SUCCESS": "#4CAF50", "COLOR_ACCENT_WARNING": "#FF9800",
        "COLOR_ACCENT_ERROR": "#F44336", "COLOR_BORDER_LIGHT": "#E0E0E0",
        "COLOR_BORDER_MEDIUM": "#BDBDBD", "COLOR_BORDER_DARK": "#9E9E9E",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#F5F5F5", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#616161",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#757575", "COLOR_ITEM_COMMENT_BG": "#FFF8E1",
        "COLOR_ITEM_COMMENT_BORDER": "#FFB74D", "COLOR_GRID_MINOR": "#FAFAFA",
        "COLOR_GRID_MAJOR": "#F0F0F0", "COLOR_DRAGGABLE_BUTTON_BG": "#FFFFFF",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#E0E0E0", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#F5F5F5",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#616161", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#EEEEEE"
    }

    # Corporate Theme
    THEME_DATA_CORPORATE = {
        "COLOR_BACKGROUND_APP": "#F8F9FA", "COLOR_BACKGROUND_LIGHT": "#FFFFFF",
        "COLOR_BACKGROUND_MEDIUM": "#F1F3F4", "COLOR_BACKGROUND_DARK": "#E8EAED",
        "COLOR_BACKGROUND_EDITOR_DARK": "#FEFEFE", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#202124",
        "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#5F6368", "COLOR_BACKGROUND_DIALOG": "#FFFFFF",
        "COLOR_TEXT_PRIMARY": "#202124", "COLOR_TEXT_SECONDARY": "#5F6368",
        "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#1A73E8",
        "COLOR_ACCENT_PRIMARY_LIGHT": "#E8F0FE", "COLOR_ACCENT_SECONDARY": "#137333",
        "COLOR_ACCENT_SUCCESS": "#137333", "COLOR_ACCENT_WARNING": "#EA8600",
        "COLOR_ACCENT_ERROR": "#D93025", "COLOR_BORDER_LIGHT": "#DADCE0",
        "COLOR_BORDER_MEDIUM": "#BDC1C6", "COLOR_BORDER_DARK": "#9AA0A6",
        "COLOR_ITEM_STATE_DEFAULT_BG": "#E8F0FE", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#1A73E8",
        "COLOR_ITEM_TRANSITION_DEFAULT": "#137333", "COLOR_ITEM_COMMENT_BG": "#FEF7E0",
        "COLOR_ITEM_COMMENT_BORDER": "#EA8600", "COLOR_GRID_MINOR": "#F8F9FA",
        "COLOR_GRID_MAJOR": "#F1F3F4", "COLOR_DRAGGABLE_BUTTON_BG": "#FFFFFF",
        "COLOR_DRAGGABLE_BUTTON_BORDER": "#DADCE0", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#E8F0FE",
        "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#1A73E8", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#D2E3FC"
    }

    THEME_KEYS = list(THEME_DATA_LIGHT.keys())

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
        # Load all professional themes
        self.themes = {
            "Light": self.THEME_DATA_LIGHT.copy(),
            "Dark": self.THEME_DATA_DARK.copy(),
            "Monochrome": self.THEME_DATA_MONOCHROME.copy(),
            "Professional Blue": self.THEME_DATA_PROFESSIONAL_BLUE.copy(),
            "Professional Dark": self.THEME_DATA_PROFESSIONAL_DARK.copy(),
            "Minimal Gray": self.THEME_DATA_MINIMAL_GRAY.copy(),
            "Corporate": self.THEME_DATA_CORPORATE.copy()
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
        """Get sorted list of theme names with professional themes first."""
        professional_themes = ["Light", "Dark", "Monochrome", "Professional Blue", 
                               "Professional Dark", "Minimal Gray", "Corporate"]
        user_themes = [name for name in self.themes.keys() if name not in professional_themes]
        return professional_themes + sorted(user_themes)

    def is_default_theme(self, name: str) -> bool:
        return name in ["Light", "Dark", "Monochrome", "Professional Blue", 
                       "Professional Dark", "Minimal Gray", "Corporate"]

    def get_theme_data(self, name: str) -> Optional[Dict[str, str]]:
        return self.themes.get(name)
        
    def derive_theme_from_palette(self, core_palette: Dict[str, str]) -> Dict[str, str]:
        """Generate a full theme dictionary from a small set of core palette colors."""
        p = {key: QColor(value) for key, value in core_palette.items()}
        is_dark = p["COLOR_BACKGROUND_APP"].lightnessF() < 0.5
        
        t = {} # The derived theme dictionary
        
        # Direct assignments
        t.update({key: val.name() for key, val in p.items()})

        # Enhanced logic-based derivations with better professional appearance
        t["COLOR_BACKGROUND_LIGHT"]    = p["COLOR_BACKGROUND_APP"].lighter(108 if is_dark else 103).name()
        t["COLOR_BACKGROUND_MEDIUM"]   = p["COLOR_BACKGROUND_APP"].lighter(120 if is_dark else 97).name()
        t["COLOR_BACKGROUND_DARK"]     = p["COLOR_BACKGROUND_APP"].lighter(135 if is_dark else 93).name()
        t["COLOR_BACKGROUND_DIALOG"]  = t["COLOR_BACKGROUND_LIGHT"]
        t["COLOR_TEXT_SECONDARY"]      = p["COLOR_TEXT_PRIMARY"].lighter(140 if is_dark else 85).name()
        t["COLOR_TEXT_ON_ACCENT"]      = "#FFFFFF" if p["COLOR_ACCENT_PRIMARY"].lightnessF() < 0.65 else "#000000"
        t["COLOR_ACCENT_PRIMARY_LIGHT"]= p["COLOR_ACCENT_PRIMARY"].lighter(175 if is_dark else 145).name()

        # Editor colors for better readability
        editor_bg = QColor(p["COLOR_BACKGROUND_EDITOR_DARK"])
        t["COLOR_TEXT_EDITOR_DARK_PRIMARY"] = editor_bg.lighter(200 if is_dark else 25).name()
        t["COLOR_TEXT_EDITOR_DARK_SECONDARY"] = editor_bg.lighter(160 if is_dark else 45).name()
        
        # Professional border styling
        t["COLOR_BORDER_LIGHT"]        = p["COLOR_BACKGROUND_APP"].darker(110 if is_dark else 105).name()
        t["COLOR_BORDER_MEDIUM"]       = p["COLOR_BACKGROUND_APP"].darker(125 if is_dark else 115).name()
        t["COLOR_BORDER_DARK"]         = p["COLOR_BACKGROUND_APP"].darker(140 if is_dark else 130).name()
        
        # Item styling with better contrast
        t["COLOR_ITEM_STATE_DEFAULT_BG"]      = p["COLOR_ACCENT_PRIMARY"].lighter(175 if is_dark else 150).name()
        t["COLOR_ITEM_STATE_DEFAULT_BORDER"]  = p["COLOR_ACCENT_PRIMARY"].name()
        t["COLOR_ITEM_TRANSITION_DEFAULT"]    = p["COLOR_ACCENT_SECONDARY"].name()
        t["COLOR_ITEM_COMMENT_BG"]            = p["COLOR_ACCENT_WARNING"].lighter(180 if is_dark else 160).name()
        t["COLOR_ITEM_COMMENT_BORDER"]        = p["COLOR_ACCENT_WARNING"].darker(105).name()
        
        # Grid with subtle appearance
        t["COLOR_GRID_MINOR"] = p["COLOR_BACKGROUND_APP"].lighter(105 if is_dark else 102).name()
        t["COLOR_GRID_MAJOR"] = p["COLOR_BACKGROUND_APP"].lighter(115 if is_dark else 97).name()
        
        # Professional button styling
        t["COLOR_DRAGGABLE_BUTTON_BG"] = t["COLOR_BACKGROUND_LIGHT"]
        t["COLOR_DRAGGABLE_BUTTON_BORDER"] = t["COLOR_BORDER_LIGHT"]
        t["COLOR_DRAGGABLE_BUTTON_HOVER_BG"] = t["COLOR_ACCENT_PRIMARY_LIGHT"]
        t["COLOR_DRAGGABLE_BUTTON_HOVER_BORDER"] = t["COLOR_ACCENT_PRIMARY"]
        t["COLOR_DRAGGABLE_BUTTON_PRESSED_BG"] = p["COLOR_ACCENT_PRIMARY"].darker(105).name()

        # Ensure all keys are present
        for key in self.THEME_KEYS:
            if key not in t:
                t[key] = self.THEME_DATA_PROFESSIONAL_DARK[key] if is_dark else self.THEME_DATA_PROFESSIONAL_BLUE[key]
                logger.warning(f"Key '{key}' was missing during theme derivation; used fallback.")
        return t

    def get_current_stylesheet(self, theme_data: Dict[str, str]) -> str:
        """
        Generates the enhanced professional application-wide stylesheet from a theme dictionary.
        """
        is_dark = QColor(theme_data["COLOR_BACKGROUND_APP"]).lightnessF() < 0.5
        grad_stop_1 = QColor(theme_data["COLOR_BACKGROUND_MEDIUM"]).lighter(103 if is_dark else 102).name()
        grad_stop_2 = QColor(theme_data["COLOR_BACKGROUND_MEDIUM"]).darker(101 if is_dark else 98).name()
        
        return f"""
        /* Professional Base Styling */
        QWidget {{
            font-family: {config.APP_FONT_FAMILY};
            font-size: {config.APP_FONT_SIZE_STANDARD};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            font-weight: 400;
        }}
        
        QMainWindow {{
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
            border: none;
        }}
        
        /* Professional Dock Widget Styling */
        QDockWidget::title {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {grad_stop_1}, stop:1 {grad_stop_2});
            padding: 8px 12px 8px 50px;
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-bottom: 2px solid {theme_data['COLOR_ACCENT_PRIMARY']};
            font-weight: 600;
            font-size: {config.APP_FONT_SIZE_STANDARD};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        QDockWidget {{
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            titlebar-close-icon: url(:/icons/close.png);
            titlebar-normal-icon: url(:/icons/undock.png);
        }}
        
        QDockWidget QWidget {{
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
        }}
        
        QDockWidget::close-button, QDockWidget::float-button {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            background: transparent;
            border: none;
            border-radius: 3px;
            width: 16px;
            height: 16px;
        }}
        
        QDockWidget::close-button {{
            left: 8px;
            top: 6px;
        }}
        
        QDockWidget::float-button {{
            left: 28px;
            top: 6px;
        }}
        
        QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
            background-color: {theme_data['COLOR_ACCENT_ERROR']};
        }}
        
        /* Professional Toolbar Styling */
        QToolBar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {grad_stop_1}, stop:1 {grad_stop_2});
            border: none;
            border-bottom: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            padding: 4px;
            spacing: 2px;
            min-height: 32px;
        }}
        
        QToolButton {{
            background-color: transparent;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            padding: 6px 8px;
            margin: 1px;
            border: 1px solid transparent;
            border-radius: 4px;
            font-weight: 500;
            min-width: 24px;
            min-height: 24px;
        }}
        
        QToolButton:hover, QDockWidget#ElementsPaletteDock QToolButton:hover {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
            border: 1px solid {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(130).name() if QColor(theme_data['COLOR_ACCENT_PRIMARY_LIGHT']).lightnessF() > 0.6 else theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        
        QToolButton:pressed, QDockWidget#ElementsPaletteDock QToolButton:pressed {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            border: 1px solid {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(110).name()};
        }}
        
        QToolButton:checked, QDockWidget#ElementsPaletteDock QToolButton:checked {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            border: 1px solid {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(120).name()};
            font-weight: 600;
        }}
        
        QToolButton:disabled {{
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            background-color: transparent;
            border: 1px solid transparent;
        }}
        
        /* Professional Menu Styling */
        QMenuBar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {grad_stop_1}, stop:1 {grad_stop_2});
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: none;
            border-bottom: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            padding: 2px;
            font-weight: 500;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-radius: 3px;
            margin: 2px 1px;
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
            border-radius: 6px;
            padding: 6px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}
        
        QMenu::item {{
            padding: 8px 30px 8px 30px;
            border-radius: 4px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            margin: 1px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        
        QMenu::separator {{
            height: 1px;
            background: {theme_data['COLOR_BORDER_LIGHT']};
            margin: 6px 8px;
        }}
        
        QMenu::icon {{
            padding-left: 8px;
        }}
        
        /* Professional Status Bar */
        QStatusBar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {grad_stop_1}, stop:1 {grad_stop_2});
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: none;
            border-top: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            padding: 4px;
            font-size: {config.APP_FONT_SIZE_SMALL};
        }}
        
        QStatusBar::item {{
            border: none;
            margin: 0 3px;
        }}
        
        /* Professional Status Labels */
        QLabel#StatusLabel, QLabel#MatlabStatusLabel, QLabel#PySimStatusLabel, 
        QLabel#AIChatStatusLabel, QLabel#InternetStatusLabel, QLabel#MainOpStatusLabel, 
        QLabel#IdeFileStatusLabel, QMainWindow QLabel[objectName$="StatusLabel"],
        QLabel#ZoomStatusLabel, QLabel#InteractionModeStatusLabel {{
            padding: 3px 6px;
            font-size: {config.APP_FONT_SIZE_SMALL};
            border-radius: 3px;
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            background-color: transparent;
            font-weight: 500;
        }}
        
        QLabel#CpuStatusLabel, QLabel#RamStatusLabel, QLabel#GpuStatusLabel {{
            font-size: {config.APP_FONT_SIZE_SMALL};
            padding: 4px 8px;
            min-width: 65px;
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            background-color: {theme_data['COLOR_BACKGROUND_LIGHT']};
            border-radius: 4px;
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            font-weight: 500;
        }}
        
        /* Professional Dialog Styling */
        QDialog {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            border-radius: 8px;
        }}
        
        QDialog QLabel, QDialog QCheckBox, QDialog QRadioButton, 
        QDialog QSpinBox, QDialog QDoubleSpinBox, QDialog QFontComboBox {{
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        
        QLabel {{
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            background-color: transparent;
        }}
        
        /* Professional Input Controls */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lighter(103 if QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lightnessF() > 0.5 else 115).name()};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            border-radius: 4px;
            padding: 6px 8px;
            font-size: {config.APP_FONT_SIZE_STANDARD};
            selection-background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            selection-color: {theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, 
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 2px solid {theme_data['COLOR_ACCENT_PRIMARY']};
            outline: none;
            background-color: {QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lighter(105 if QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lightnessF() > 0.5 else 118).name()};
        }}
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, 
        QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
            background-color: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            border-color: {theme_data['COLOR_BORDER_LIGHT']};
        }}
        
        /* Professional ComboBox */
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left-width: 1px;
            border-left-color: {theme_data['COLOR_BORDER_MEDIUM']};
            border-left-style: solid;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
            background-color: {QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lightnessF() > 0.5 else 110).name()};
        }}
        
        QComboBox::drop-down:hover {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
        }}
        
        QComboBox::down-arrow {{
            image: url(:/icons/arrow_down.png);
            width: 12px; 
            height: 12px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            selection-background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            selection-color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            border-radius: 4px;
            padding: 2px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            alternate-background-color: {QColor(theme_data['COLOR_BACKGROUND_DIALOG']).darker(102).name()};
        }}
        
        /* Professional Button Styling */
        QPushButton {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            padding: 8px 16px;
            border-radius: 6px;
            min-height: 24px;
            font-weight: 500;
            font-size: {config.APP_FONT_SIZE_STANDARD};
        }}
        
        QPushButton:hover {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {QColor(grad_stop_1).lighter(108).name()}, stop: 1 {QColor(grad_stop_2).lighter(108).name()});
            border-color: {theme_data['COLOR_BORDER_DARK']};
        }}
        
        QPushButton:pressed {{
            background-color: {QColor(theme_data['COLOR_BACKGROUND_DARK']).name()};
            border-color: {theme_data['COLOR_BORDER_DARK']};
        }}
        
        QPushButton:disabled {{
            background-color: {QColor(theme_data['COLOR_BACKGROUND_LIGHT']).darker(102 if QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lightnessF() < 0.5 else 95).name()};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            border-color: {theme_data['COLOR_BORDER_LIGHT']};
        }}
        
        QDialogButtonBox QPushButton {{
            min-width: 90px;
            padding: 8px 20px;
        }}
        
        /* Primary Action Buttons */
        QDialogButtonBox QPushButton[text="OK"], QDialogButtonBox QPushButton[text="OK & Save"], 
        QDialogButtonBox QPushButton[text="Apply & Close"], QDialogButtonBox QPushButton[text="Save"], 
        QDialogButtonBox QPushButton[text="Apply"] {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            border-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(120).name()};
            font-weight: 600;
        }}
        
        QDialogButtonBox QPushButton[text="OK"]:hover, QDialogButtonBox QPushButton[text="OK & Save"]:hover, 
        QDialogButtonBox QPushButton[text="Apply & Close"]:hover, QDialogButtonBox QPushButton[text="Save"]:hover, 
        QDialogButtonBox QPushButton[text="Apply"]:hover {{
            background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()};
        }}
        
        /* Secondary Action Buttons */
        QDialogButtonBox QPushButton[text="Cancel"], QDialogButtonBox QPushButton[text="Discard"],
        QDialogButtonBox QPushButton[text="Close"] {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-color: {theme_data['COLOR_BORDER_MEDIUM']};
        }}
        
        QDialogButtonBox QPushButton[text="Cancel"]:hover, QDialogButtonBox QPushButton[text="Discard"]:hover,
        QDialogButtonBox QPushButton[text="Close"]:hover {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {QColor(grad_stop_1).darker(105).name()}, stop: 1 {QColor(grad_stop_2).darker(105).name()});
        }}
        
        /* Professional Group Box */
        QGroupBox {{
            background-color: transparent;
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-radius: 6px;
            margin-top: 12px;
            padding: 12px 10px 10px 10px;
            font-weight: 500;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 10px;
            left: 12px;
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
            color: {theme_data['COLOR_ACCENT_PRIMARY']};
            font-weight: 600;
            border-radius: 3px;
        }}
        
        /* Professional Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-top: none;
            border-bottom-left-radius: 6px;
            border-bottom-right-radius: 6px;
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            padding: 8px;
        }}
        
        QTabBar::tab {{
            background: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-bottom-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 18px;
            margin-right: 2px;
            min-width: 80px;
            font-weight: 500;
        }}
        
        QTabBar::tab:selected {{
            background: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            font-weight: 600;
            border-bottom-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
        }}
        
        QTabBar::tab:!selected:hover {{
            background: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-bottom-color: {theme_data['COLOR_BORDER_LIGHT']};
        }}
        
        /* Professional Checkbox */
        QCheckBox {{
            spacing: 10px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            font-weight: 500;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
        }}
        
        QCheckBox::indicator:unchecked {{
            border: 2px solid {theme_data['COLOR_BORDER_MEDIUM']};
            border-radius: 3px;
            background-color: {QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lightnessF() > 0.5 else 115).name()};
        }}
        
        QCheckBox::indicator:unchecked:hover {{
            border: 2px solid {theme_data['COLOR_ACCENT_PRIMARY']};
        }}
        
        QCheckBox::indicator:checked {{
            border: 2px solid {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(120).name()};
            border-radius: 3px;
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            image: url(:/icons/check.png);
        }}
        
        QCheckBox::indicator:checked:hover {{
            background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()};
        }}

        /* Professional Code Editor Styling */
        QTextEdit#LogOutputWidget, QTextEdit#PySimActionLog, QTextBrowser#AIChatDisplay,
        QPlainTextEdit#ActionCodeEditor, QTextEdit#IDEOutputConsole, QPlainTextEdit#StandaloneCodeEditor,
        QTextEdit#SubFSMJsonEditor, QPlainTextEdit#LivePreviewEditor {{
            font-family: 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace;
            font-size: {config.APP_FONT_SIZE_EDITOR};
            background-color: {theme_data['COLOR_BACKGROUND_EDITOR_DARK']};
            color: {theme_data['COLOR_TEXT_EDITOR_DARK_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_DARK']};
            border-radius: 6px;
            padding: 8px;
            selection-background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(110).name()};
            selection-color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            line-height: 1.4;
        }}

        /* Professional Scrollbars */
        QScrollBar:vertical {{
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            background: {QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_LIGHT']).lightnessF() > 0.5 else 110).name()};
            width: 16px;
            margin: 0px;
            border-radius: 8px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {theme_data['COLOR_BORDER_DARK']};
            min-height: 30px;
            border-radius: 8px;
            margin: 2px;
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
            height: 16px;
            margin: 0px;
            border-radius: 8px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {theme_data['COLOR_BORDER_DARK']};
            min-width: 30px;
            border-radius: 8px;
            margin: 2px;
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
        QTextEdit#SubFSMJsonEditor QScrollBar:vertical {{
            border: 1px solid {theme_data['COLOR_BORDER_DARK']};
            background: {QColor(theme_data['COLOR_BACKGROUND_EDITOR_DARK']).lighter(110).name()};
        }}
        
        QTextEdit#LogOutputWidget QScrollBar::handle:vertical, QTextEdit#PySimActionLog QScrollBar::handle:vertical,
        QTextBrowser#AIChatDisplay QScrollBar::handle:vertical, QPlainTextEdit#ActionCodeEditor QScrollBar::handle:vertical,
        QTextEdit#IDEOutputConsole QScrollBar::handle:vertical, QPlainTextEdit#StandaloneCodeEditor QScrollBar::vertical,
        QTextEdit#SubFSMJsonEditor QScrollBar::handle:vertical {{
            background: {theme_data['COLOR_TEXT_EDITOR_DARK_SECONDARY']};
        }}
        
        QTextEdit#LogOutputWidget QScrollBar::handle:vertical:hover, QTextEdit#PySimActionLog QScrollBar::handle:vertical:hover,
        QTextBrowser#AIChatDisplay QScrollBar::handle:vertical:hover, QPlainTextEdit#ActionCodeEditor QScrollBar::handle:vertical:hover,
        QTextEdit#IDEOutputConsole QScrollBar::handle:vertical:hover, QPlainTextEdit#StandaloneCodeEditor QScrollBar::handle:vertical:hover,
        QTextEdit#SubFSMJsonEditor QScrollBar::handle:vertical:hover {{
            background: {QColor(theme_data['COLOR_TEXT_EDITOR_DARK_SECONDARY']).lighter(120).name()};
        }}

        /* Professional Special Buttons */
        QPushButton#SnippetButton {{
            background-color: {theme_data['COLOR_ACCENT_SECONDARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            border: 1px solid {QColor(theme_data['COLOR_ACCENT_SECONDARY']).darker(130).name()};
            font-weight: 500;
            padding: 6px 12px;
            min-height: 0;
            border-radius: 4px;
        }}
        
        QPushButton#SnippetButton:hover {{
            background-color: {QColor(theme_data['COLOR_ACCENT_SECONDARY']).lighter(110).name()};
        }}
        
        QPushButton#ColorButton, QPushButton#ColorButtonPropertiesDock {{
            border: 2px solid {theme_data['COLOR_BORDER_MEDIUM']}; 
            min-height: 28px; 
            padding: 4px;
            border-radius: 6px;
        }}
        
        QPushButton#ColorButton:hover, QPushButton#ColorButtonPropertiesDock:hover {{
            border: 2px solid {theme_data['COLOR_ACCENT_PRIMARY']};
        }}
        
        /* Professional Progress Bar */
        QProgressBar {{
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']}; 
            border-radius: 4px;
            background-color: {theme_data['COLOR_BACKGROUND_LIGHT']}; 
            text-align: center;
            color: {theme_data['COLOR_TEXT_PRIMARY']}; 
            height: 16px;
            font-weight: 500;
        }}
        
        QProgressBar::chunk {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']}; 
            border-radius: 3px;
        }}
        
        /* Professional Draggable Buttons */
        QPushButton#DraggableToolButton {{
            background-color: {theme_data['COLOR_DRAGGABLE_BUTTON_BG']}; 
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_DRAGGABLE_BUTTON_BORDER']};
            padding: 8px 10px;
            text-align: left;
            font-weight: 500;
            min-height: 36px;
            border-radius: 6px;
        }}
        
        QPushButton#DraggableToolButton:hover {{
            background-color: {QColor(theme_data['COLOR_DRAGGABLE_BUTTON_HOVER_BG']).name() if isinstance(theme_data['COLOR_DRAGGABLE_BUTTON_HOVER_BG'], QColor) else theme_data['COLOR_DRAGGABLE_BUTTON_HOVER_BG']};
            border-color: {theme_data['COLOR_DRAGGABLE_BUTTON_HOVER_BORDER']};
        }}
        
        QPushButton#DraggableToolButton:pressed {{ 
            background-color: {QColor(theme_data['COLOR_DRAGGABLE_BUTTON_PRESSED_BG']).name() if isinstance(theme_data['COLOR_DRAGGABLE_BUTTON_PRESSED_BG'], QColor) else theme_data['COLOR_DRAGGABLE_BUTTON_PRESSED_BG']}; 
        }}

        /* Professional Properties Dock */
        #PropertiesDock QLabel#PropertiesLabel {{
            padding: 8px; 
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']}; 
            border-radius: 4px;
            font-size: {config.APP_FONT_SIZE_STANDARD};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            font-weight: 500;
        }}
        
        #PropertiesDock QPushButton {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']}; 
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            font-weight: 600;
            border-radius: 4px;
            padding: 6px 12px;
        }}
        
        #PropertiesDock QPushButton:hover {{ 
            background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()}; 
        }}

        /* Professional Elements Palette */
        QDockWidget#ElementsPaletteDock QToolButton {{
            padding: 8px 10px; 
            text-align: left;
            min-height: 38px;
            font-weight: 500;
            border-radius: 4px;
        }}
        
        QDockWidget#ElementsPaletteDock QGroupBox {{
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            font-weight: 500;
        }}
        
        QDockWidget#ElementsPaletteDock QGroupBox::title {{
            color: {theme_data['COLOR_ACCENT_PRIMARY']};
            background-color: {theme_data['COLOR_BACKGROUND_APP']};
            font-weight: 600;
        }}

        /* Professional PySimDock */
        QDockWidget#PySimDock QPushButton {{
            padding: 6px 12px;
            border-radius: 4px;
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
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-radius: 4px;
        }}
        
        QDockWidget#PySimDock QHeaderView::section,
        QTableWidget QHeaderView::section {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
            padding: 6px;
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-bottom: 2px solid {theme_data['COLOR_BORDER_DARK']};
            font-weight: 600;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
        }}
        
        /* Professional Action Buttons */
        QDockWidget#AIChatbotDock QPushButton#AIChatSendButton,
        QDockWidget#PySimDock QPushButton[text="Trigger"] {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']}; 
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            font-weight: 600;
            padding: 6px 12px;
            min-width: 0;
            border-radius: 4px;
        }}
        
        QDockWidget#AIChatbotDock QPushButton#AIChatSendButton:hover,
        QDockWidget#PySimDock QPushButton[text="Trigger"]:hover {{
            background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()};
        }}
        
        QDockWidget#AIChatbotDock QPushButton#AIChatSendButton:disabled,
        QDockWidget#PySimDock QPushButton[text="Trigger"]:disabled {{
            background-color: {theme_data['COLOR_BACKGROUND_MEDIUM']};
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            border-color: {theme_data['COLOR_BORDER_LIGHT']};
        }}
        
        /* Professional Input Fields */
        QLineEdit#AIChatInput, QLineEdit#PySimEventNameEdit {{
            padding: 8px 10px;
            border-radius: 4px;
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
        }}
        
        QLineEdit#AIChatInput:focus, QLineEdit#PySimEventNameEdit:focus {{
            border: 2px solid {theme_data['COLOR_ACCENT_PRIMARY']};
        }}
        
        /* Professional Problems Dock */
        QDockWidget#ProblemsDock QListWidget {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-radius: 4px;
        }}
        
        QDockWidget#ProblemsDock QListWidget::item {{
            padding: 6px;
            border-bottom: 1px dotted {theme_data['COLOR_BORDER_LIGHT']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border-radius: 2px;
        }}
        
        QDockWidget#ProblemsDock QListWidget::item:selected {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
            color: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(130).name() if QColor(theme_data['COLOR_ACCENT_PRIMARY_LIGHT']).lightnessF() > 0.6 else theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        
        QDockWidget#ProblemsDock QListWidget::item:hover {{
            background-color: {QColor(theme_data['COLOR_ACCENT_PRIMARY_LIGHT']).lighter(110).name()};
        }}
        
        /* Professional Labels */
        QLabel#ErrorLabel {{
            color: {theme_data['COLOR_ACCENT_ERROR']};
            font-weight: 600;
        }}
        
        QLabel#HardwareHintLabel {{
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            font-style: italic;
            font-size: 8pt;
        }}
        
        QLabel#SafetyNote {{
            color: {theme_data['COLOR_TEXT_SECONDARY']};
            font-style: italic;
            font-size: {config.APP_FONT_SIZE_SMALL};
        }}
        
        /* Professional IDE Groups */
        QGroupBox#IDEOutputGroup, QGroupBox#IDEToolbarGroup {{
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-radius: 6px;
            font-weight: 500;
        }}

        /* Professional Radio Buttons */
        QRadioButton {{
            spacing: 10px;
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            font-weight: 500;
        }}
        
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}
        
        QRadioButton::indicator:unchecked {{
            border: 2px solid {theme_data['COLOR_BORDER_MEDIUM']};
            border-radius: 8px;
            background-color: {QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lighter(102 if QColor(theme_data['COLOR_BACKGROUND_DIALOG']).lightnessF() > 0.5 else 115).name()};
        }}
        
        QRadioButton::indicator:unchecked:hover {{
            border: 2px solid {theme_data['COLOR_ACCENT_PRIMARY']};
        }}
        
        QRadioButton::indicator:checked {{
            border: 2px solid {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(120).name()};
            border-radius: 8px;
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
        }}
        
        QRadioButton::indicator:checked::after {{
            width: 6px;
            height: 6px;
            border-radius: 3px;
            background-color: {theme_data['COLOR_TEXT_ON_ACCENT']};
            margin: 3px;
        }}

        /* Professional Slider */
        QSlider::groove:horizontal {{
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            height: 6px;
            background: {theme_data['COLOR_BACKGROUND_LIGHT']};
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background: {theme_data['COLOR_ACCENT_PRIMARY']};
            border: 1px solid {QColor(theme_data['COLOR_ACCENT_PRIMARY']).darker(120).name()};
            width: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: {QColor(theme_data['COLOR_ACCENT_PRIMARY']).lighter(110).name()};
        }}

        /* Professional Splitter */
        QSplitter::handle {{
            background-color: {theme_data['COLOR_BORDER_MEDIUM']};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        QSplitter::handle:hover {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
        }}

        /* Professional Tree Widget */
        QTreeWidget {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
            border-radius: 4px;
            alternate-background-color: {QColor(theme_data['COLOR_BACKGROUND_DIALOG']).darker(102).name()};
        }}
        
        QTreeWidget::item {{
            padding: 4px;
            border-bottom: 1px solid {theme_data['COLOR_BORDER_LIGHT']};
        }}
        
        QTreeWidget::item:selected {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY']};
            color: {theme_data['COLOR_TEXT_ON_ACCENT']};
        }}
        
        QTreeWidget::item:hover {{
            background-color: {theme_data['COLOR_ACCENT_PRIMARY_LIGHT']};
        }}
        
        QTreeWidget::branch:has-siblings:!adjoins-item {{
            border-image: url(:/icons/vline.png) 0;
        }}
        
        QTreeWidget::branch:has-siblings:adjoins-item {{
            border-image: url(:/icons/branch-more.png) 0;
        }}
        
        QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {{
            border-image: url(:/icons/branch-end.png) 0;
        }}
        
        QTreeWidget::branch:has-children:!has-siblings:closed,
        QTreeWidget::branch:closed:has-children:has-siblings {{
            border-image: none;
            image: url(:/icons/branch-closed.png);
        }}
        
        QTreeWidget::branch:open:has-children:!has-siblings,
        QTreeWidget::branch:open:has-children:has-siblings {{
            border-image: none;
            image: url(:/icons/branch-open.png);
        }}

        /* Tooltip Styling */
        QToolTip {{
            background-color: {theme_data['COLOR_BACKGROUND_DIALOG']};
            color: {theme_data['COLOR_TEXT_PRIMARY']};
            border: 1px solid {theme_data['COLOR_BORDER_MEDIUM']};
            border-radius: 4px;
            padding: 6px;
            font-size: {config.APP_FONT_SIZE_SMALL};
        }}
        """

    def update_dynamic_config_colors(self, theme_data: dict):
        """
        Populates the global color variables in the config module with professional enhancements.
        """
        for key, value in theme_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Enhanced professional color calculations
        config.COLOR_PY_SIM_STATE_ACTIVE = QColor(config.COLOR_ACCENT_SUCCESS)
        
        accent_secondary_color = QColor(config.COLOR_ACCENT_SECONDARY)
        config.COLOR_ITEM_STATE_SELECTION_BG = accent_secondary_color.lighter(170 if accent_secondary_color.lightnessF() < 0.5 else 135).name()
        config.COLOR_ITEM_STATE_SELECTION_BORDER = accent_secondary_color.name()
        
        accent_primary_color = QColor(config.COLOR_ACCENT_PRIMARY)
        config.COLOR_ITEM_TRANSITION_SELECTION = accent_primary_color.lighter(150 if accent_primary_color.lightnessF() < 0.5 else 125).name()

    def get_theme_description(self, theme_name: str) -> str:
        """Get a professional description for each theme."""
        descriptions = {
            "Light": "Clean and bright interface with excellent readability for daytime use",
            "Dark": "Modern dark theme optimized for low-light environments and reduced eye strain",
            "Monochrome": "Minimalist grayscale design focusing on content without color distractions",
            "Professional Blue": "Corporate-friendly theme with calming blue accents and high contrast",
            "Professional Dark": "Sophisticated dark theme with professional blue highlights",
            "Minimal Gray": "Ultra-clean minimal design with subtle gray tones",
            "Corporate": "Enterprise-ready theme inspired by modern business applications"
        }
        return descriptions.get(theme_name, "Custom user-defined theme")

    def get_recommended_theme_for_environment(self, environment: str) -> str:
        """Recommend themes based on usage environment."""
        recommendations = {
            "office": "Corporate",
            "home": "Professional Blue", 
            "presentation": "Monochrome",
            "low_light": "Professional Dark",
            "high_contrast": "Light",
            "minimal": "Minimal Gray"
        }
        return recommendations.get(environment.lower(), "Professional Blue")