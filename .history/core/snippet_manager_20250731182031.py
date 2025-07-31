# fsm_designer_project/core/snippet_manager.py
import os
import json
import logging
from PyQt5.QtCore import QStandardPaths, QDir

logger = logging.getLogger(__name__)

DEFAULT_SNIPPET_FILENAME = "custom_assets.json" # Renamed to reflect new purpose

class CustomSnippetManager:
    def __init__(self, app_name="BSMDesigner"):
        self.app_name = app_name
        self.custom_assets: dict = {}  # Structure: {lang: {category: {name: code}}}, and a special key "fsm_templates"

        config_path = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        if not config_path: # Fallback if AppConfigLocation is not specific enough
            config_path = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            if self.app_name and config_path: # Create a subdirectory for the app if using generic AppDataLocation
                app_dir = QDir(config_path)
                if not app_dir.exists(self.app_name):
                    app_dir.mkpath(self.app_name)
                config_path = os.path.join(config_path, self.app_name)

        if not config_path: # Further fallback to current working directory (less ideal)
            logger.warning("Could not determine a standard config path. Using current directory for assets.")
            config_path = os.getcwd()
            
        if not QDir(config_path).exists():
            QDir().mkpath(config_path)
            
        self.asset_file_path = os.path.join(config_path, DEFAULT_SNIPPET_FILENAME)
        logger.info(f"Custom assets will be loaded/saved at: {self.asset_file_path}")
        
        self.load_custom_assets()

    def load_custom_assets(self):
        if not os.path.exists(self.asset_file_path):
            logger.info(f"Custom asset file not found at '{self.asset_file_path}'. Starting with empty assets.")
            self.custom_assets = {}
            return

        try:
            with open(self.asset_file_path, 'r', encoding='utf-8') as f:
                self.custom_assets = json.load(f)
            if not isinstance(self.custom_assets, dict):
                logger.warning(f"Custom asset file '{self.asset_file_path}' does not contain a valid dictionary. Resetting to empty.")
                self.custom_assets = {}
            logger.info(f"Custom assets loaded successfully from '{self.asset_file_path}'.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from asset file '{self.asset_file_path}'. Backing up and resetting.", exc_info=True)
            self._backup_and_reset_assets()
        except Exception as e:
            logger.error(f"Failed to load custom assets from '{self.asset_file_path}': {e}", exc_info=True)
            self.custom_assets = {} # Default to empty on other errors

    def _backup_and_reset_assets(self):
        """Backs up the corrupted asset file and resets to an empty dictionary."""
        try:
            backup_path = self.asset_file_path + ".bak"
            if os.path.exists(self.asset_file_path):
                os.replace(self.asset_file_path, backup_path)
                logger.info(f"Backed up corrupted asset file to '{backup_path}'.")
        except Exception as e_backup:
            logger.error(f"Failed to back up corrupted asset file: {e_backup}")
        self.custom_assets = {}


    def save_custom_assets(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.asset_file_path), exist_ok=True)
            with open(self.asset_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.custom_assets, f, indent=4, ensure_ascii=False)
            logger.info(f"Custom assets saved successfully to '{self.asset_file_path}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to save custom assets to '{self.asset_file_path}': {e}", exc_info=True)
            return False

    def get_custom_snippets(self, language: str, category: str) -> dict:
        return self.custom_assets.get(language, {}).get(category, {})

    def add_custom_snippet(self, language: str, category: str, name: str, code: str) -> bool:
        if not language or not category or not name:
            logger.warning("Cannot add custom snippet: language, category, or name is empty.")
            return False
            
        if language not in self.custom_assets:
            self.custom_assets[language] = {}
        if category not in self.custom_assets[language]:
            self.custom_assets[language][category] = {}
        
        self.custom_assets[language][category][name] = code
        logger.info(f"Added/Updated custom snippet: [{language}][{category}] '{name}'")
        return self.save_custom_assets()

    def edit_custom_snippet(self, language: str, category: str, old_name: str, new_name: str, new_code: str) -> bool:
        if not language or not category or not old_name or not new_name:
            logger.warning("Cannot edit custom snippet: language, category, old_name or new_name is empty.")
            return False

        lang_data = self.custom_assets.get(language)
        if not lang_data:
            logger.warning(f"Cannot edit snippet: Language '{language}' not found.")
            return False
        cat_data = lang_data.get(category)
        if not cat_data:
            logger.warning(f"Cannot edit snippet: Category '{category}' not found for language '{language}'.")
            return False
        if old_name not in cat_data:
            logger.warning(f"Cannot edit snippet: Snippet '{old_name}' not found in [{language}][{category}].")
            return False

        if old_name != new_name:
            if new_name in cat_data:
                logger.warning(f"Cannot rename snippet to '{new_name}': name already exists in [{language}][{category}].")
                return False
            del cat_data[old_name]
        
        cat_data[new_name] = new_code
        logger.info(f"Edited custom snippet: [{language}][{category}] '{old_name}' -> '{new_name}'")
        return self.save_custom_assets()

    def delete_custom_snippet(self, language: str, category: str, name: str) -> bool:
        if not language or not category or not name:
            logger.warning("Cannot delete custom snippet: language, category, or name is empty.")
            return False

        lang_data = self.custom_assets.get(language, {})
        if not lang_data: return False
        cat_data = lang_data.get(category, {})
        if not cat_data: return False
        
        if name in cat_data:
            del cat_data[name]
            if not cat_data:
                del lang_data[category]
            if not lang_data:
                del self.custom_assets[language]
            logger.info(f"Deleted custom snippet: [{language}][{category}] '{name}'")
            return self.save_custom_assets()
        logger.warning(f"Snippet '{name}' not found for deletion in [{language}][{category}].")
        return False

    def get_all_languages_with_custom_snippets(self) -> list[str]:
        return sorted([lang for lang in self.custom_assets.keys() if lang != "fsm_templates"])

    def get_categories_for_language(self, language: str) -> list[str]:
        if language in self.custom_assets:
            return sorted(list(self.custom_assets[language].keys()))
        return []

    def get_snippet_names_for_language_category(self, language: str, category: str) -> list[str]:
        lang_data = self.custom_assets.get(language, {})
        cat_data = lang_data.get(category, {})
        return sorted(list(cat_data.keys()))

    def get_snippet_code(self, language: str, category: str, name: str) -> str | None:
        return self.custom_assets.get(language, {}).get(category, {}).get(name)

    # --- NEW TEMPLATE MANAGEMENT METHODS ---
    def get_custom_templates(self) -> dict:
        """Gets all custom FSM templates."""
        return self.custom_assets.get("fsm_templates", {})

    def save_custom_template(self, name: str, data: dict) -> bool:
        """Saves a single custom FSM template."""
        if "fsm_templates" not in self.custom_assets:
            self.custom_assets["fsm_templates"] = {}
        self.custom_assets["fsm_templates"][name] = data
        logger.info(f"Saved custom FSM template: '{name}'")
        return self.save_custom_assets()

    def template_exists(self, name: str) -> bool:
        """Checks if a custom template with the given name exists."""
        return name in self.get_custom_templates()


    def rename_custom_template(self, old_name: str, new_name: str) -> bool:
        """Renames a custom template."""
        if not old_name or not new_name or old_name == new_name:
            return False
            
        templates = self.get_custom_templates()
        if old_name in templates and new_name not in templates:
            # Move the data to the new key and update the internal name property
            template_data = templates.pop(old_name)
            template_data['name'] = new_name
            templates[new_name] = template_data
            
            logger.info(f"Renamed custom FSM template: '{old_name}' -> '{new_name}'")
            return self.save_custom_assets()
        
        logger.warning(f"Template rename failed: '{old_name}' not found or '{new_name}' already exists.")
        return False

    def delete_custom_template(self, name: str) -> bool:
        """Deletes a custom template by name."""
        templates = self.get_custom_templates()
        if name in templates:
            del templates[name]
            logger.info(f"Deleted custom FSM template: '{name}'")
            return self.save_custom_assets()
        return False