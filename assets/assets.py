# fsm_designer_project/assets/assets.py
"""
Central loader for all static asset data from JSON files.

This module acts as the single source of truth for built-in assets like
code snippets, FSM templates, and target device profiles. It loads them from
the adjacent 'data' directory and exposes them as Python constants.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

# --- Centralized Data Loading Logic ---

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

def _load_json_asset(filename: str, fallback_data: dict) -> dict:
    """
    Loads data from a JSON file in the data directory with robust error handling.
    """
    filepath = os.path.join(_DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            logger.debug(f"Loading asset data from: {filepath}")
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Asset data file not found: {filepath}. Using fallback data.")
        return fallback_data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {filepath}: {e}. Using fallback data.")
        return fallback_data
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading {filepath}: {e}", exc_info=True)
        return fallback_data

# --- Public Data Constants ---

# Load built-in mechatronics code snippets
MECHATRONICS_SNIPPETS = _load_json_asset('snippets.json', fallback_data={
    "Error": {"actions": {"Loading Failed": ""}}
})

# Load built-in FSM templates for drag-and-drop
FSM_TEMPLATES_BUILTIN = _load_json_asset('templates.json', fallback_data={
    "ErrorTemplate": {"name": "Loading Failed", "states": [], "transitions": []}
})

# Load target device profiles for resource estimation
TARGET_PROFILES = _load_json_asset('profiles.json', fallback_data={
    "FallbackDevice": {"name": "Loading Failed", "sram_b": 1, "flash_kb": 1}
})

# Load the BSM file schema for validation
BSM_SCHEMA = _load_json_asset('bsm_schema.json', fallback_data={
    "title": "Schema Loading Failed"
})