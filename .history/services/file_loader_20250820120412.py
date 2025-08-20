# fsm_designer_project/services/file_loader.py

import json
import logging
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# jsonschema is a required dependency for this to work.
# We handle its potential absence gracefully.
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    jsonschema = None # Ensure the name exists to avoid NameError

logger = logging.getLogger(__name__)

class FileLoaderWorker(QObject):
    """
    A worker that loads and validates a .bsm file in a background thread
    to avoid blocking the main UI. It communicates results back to the main
    thread via Qt signals.
    """
    # Signal emitted upon completion.
    # It carries the parsed diagram data on success, or an empty dictionary
    # and a descriptive error string on failure.
    load_finished = pyqtSignal(dict, str)
    
    @pyqtSlot(str, dict)
    def load_file(self, file_path: str, schema: dict):
        """
        Reads, parses, and validates a JSON file from the given path.

        This is a Qt slot designed to be called via a queued connection from
        the main thread.

        Args:
            file_path (str): The absolute path to the .bsm file to load.
            schema (dict): The JSON schema to validate the file content against.
        """
        logger.info(f"FileLoaderWorker: Starting to load and validate '{file_path}'...")
        try:
            # 1. Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                self.load_finished.emit({}, "File is empty.")
                logger.warning(f"FileLoaderWorker: File is empty: '{file_path}'.")
                return

            # 2. Parse the JSON data
            data = json.loads(content)
            
            # 3. Validate against the schema
            if JSONSCHEMA_AVAILABLE and schema:
                jsonschema.validate(instance=data, schema=schema)
            else:
                logger.warning("jsonschema library not available, skipping file validation.")

            # 4. Success: Emit the data
            self.load_finished.emit(data, "")
            logger.info(f"FileLoaderWorker: Successfully loaded and validated '{file_path}'.")

        except FileNotFoundError:
            error_msg = f"The file could not be found at the specified path:\n{file_path}"
            logger.error(f"FileLoaderWorker: {error_msg}")
            self.load_finished.emit({}, error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"The file is not a valid JSON file.\n\nDetails: {e}"
            logger.error(f"FileLoaderWorker: JSON decode error in '{file_path}': {e}")
            self.load_finished.emit({}, error_msg)
        except jsonschema.ValidationError as e:
            error_path = " -> ".join(map(str, e.path))
            message = (f"The diagram file has an invalid structure.\n\n"
                       f"<b>Error:</b> {e.message}\n"
                       f"<b>Location:</b> {error_path or 'Root'}")
            logger.error(f"FileLoaderWorker: Schema validation failed for '{file_path}': {e.message}")
            self.load_finished.emit({}, message)
        except Exception as e:
            error_msg = f"An unexpected error occurred while loading the file:\n{e}"
            logger.error(f"FileLoaderWorker: Unexpected error loading '{file_path}': {e}", exc_info=True)
            self.load_finished.emit({}, error_msg)