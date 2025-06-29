# bsm_designer_project/theme_manager.py (NEW FILE)
import os
import json
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QStandardPaths, QDir
from .config import THEME_DATA_LIGHT, THEME_DATA_DARK, THEME_KEYS

logger = logging.getLogger(__name__)
DEFAULT_THEME_FILENAME = "user_themes.json"

class ThemeManager(QObject):
    themesChanged = pyqtSignal()

    def __init__(self, app_name="BSMDesigner", parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.themes = {}
        
        # --- Determine Storage Path ---
        config_path = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        if not config_path:
            config_path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            if self.app_name and config_path:
                app_dir = QDir(config_path)
                if not app_dir.exists(self.app_name):
                    app_dir.mkpath(self.app_name)
                config_path = os.path.join(config_path, self.app_name)

        if not config_path:
            config_path = os.getcwd()
            logger.warning(f"Could not determine a standard config path. Using current directory: {config_path}")

        if not QDir(config_path).exists():
            QDir().mkpath(config_path)

        self.theme_file_path = os.path.join(config_path, DEFAULT_THEME_FILENAME)
        logger.info(f"User themes will be loaded from: {self.theme_file_path}")
        
        self.load_themes()

    def load_themes(self):
        """Loads default themes and user-defined themes from JSON file."""
        # Start with built-in default themes
        self.themes = {
            "Light": THEME_DATA_LIGHT.copy(),
            "Dark": THEME_DATA_DARK.copy(),
        }

        if not os.path.exists(self.theme_file_path):
            logger.info("User themes file not found. Using default themes.")
            return

        try:
            with open(self.theme_file_path, 'r', encoding='utf-8') as f:
                user_themes = json.load(f)
            if isinstance(user_themes, dict):
                # Validate and merge user themes, overriding defaults if names match
                for theme_name, theme_data in user_themes.items():
                    if isinstance(theme_data, dict):
                        # Ensure all required keys are present
                        validated_data = {key: theme_data.get(key, self.themes["Light"][key]) for key in THEME_KEYS}
                        self.themes[theme_name] = validated_data
                    else:
                        logger.warning(f"Skipping invalid theme entry '{theme_name}' in user themes file.")
                logger.info(f"Loaded {len(user_themes)} user-defined themes.")
            else:
                 raise json.JSONDecodeError("Root object is not a dictionary", "", 0)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error reading user themes file '{self.theme_file_path}'. File may be corrupt. Error: {e}")

        self.themesChanged.emit()

    def save_themes(self) -> bool:
        """Saves only the user-defined themes to the JSON file."""
        user_themes = {name: data for name, data in self.themes.items() if name not in ["Light", "Dark"]}
        try:
            os.makedirs(os.path.dirname(self.theme_file_path), exist_ok=True)
            with open(self.theme_file_path, 'w', encoding='utf-8') as f:
                json.dump(user_themes, f, indent=4, ensure_ascii=False)
            logger.info(f"User themes saved successfully to '{self.theme_file_path}'.")
            self.themesChanged.emit()
            return True
        except Exception as e:
            logger.error(f"Failed to save user themes: {e}", exc_info=True)
            return False

    def get_theme_names(self) -> list[str]:
        """Returns a sorted list of all available theme names."""
        return sorted(list(self.themes.keys()))

    def get_theme_data(self, name: str) -> dict | None:
        """Returns the color data dictionary for a given theme name."""
        return self.themes.get(name)

    def save_theme(self, name: str, data: dict) -> bool:
        """Adds or updates a theme and saves it."""
        if not name.strip():
            logger.error("Cannot save theme with an empty name.")
            return False
            
        self.themes[name] = data
        return self.save_themes()

    def delete_theme(self, name: str) -> bool:
        """Deletes a custom theme."""
        if name in ["Light", "Dark"]:
            logger.warning("Cannot delete default 'Light' or 'Dark' themes.")
            return False
        if name in self.themes:
            del self.themes[name]
            return self.save_themes()
        logger.warning(f"Cannot delete theme '{name}': not found.")
        return False