# tests/conftest.py
import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication

# --- ADD THIS BLOCK AT THE TOP ---
# This ensures that pytest can find the 'fsm_designer_project' module.
# It adds the project's root directory to Python's import path.
# __file__ -> .../fsm_designer_project/tests/conftest.py
# os.path.dirname(__file__) -> .../fsm_designer_project/tests
# os.path.join(..., '..') -> .../fsm_designer_project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    # We insert at the beginning of the path to ensure our project's
    # modules are found before any potentially conflicting installed modules.
    sys.path.insert(0, project_root)
# --- END OF BLOCK ---

@pytest.fixture(scope="session")
def qapp_args():
    """Provides a QCoreApplication instance for tests that need it without a GUI."""
    return QApplication.instance() or QApplication([])