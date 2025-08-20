# tests/conftest.py
import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication

# --- CORRECTED PATH MANIPULATION BLOCK ---
# This ensures that pytest can find the 'fsm_designer_project' module
# by adding the project's PARENT directory to Python's import path.

# Path to the current file: .../fsm_designer_project/tests/conftest.py
current_file_path = os.path.abspath(__file__)

# Path to the 'tests' directory: .../fsm_designer_project/tests
tests_dir = os.path.dirname(current_file_path)

# Path to the project root: .../fsm_designer_project
project_root = os.path.dirname(tests_dir)

# Path to the directory CONTAINING the project: .../Project research
project_parent_dir = os.path.dirname(project_root)

# Add the parent directory to sys.path so 'import fsm_designer_project' works
if project_parent_dir not in sys.path:
    sys.path.insert(0, project_parent_dir)
# --- END OF BLOCK ---

@pytest.fixture(scope="session")
def qapp_args():
    """Provides a QCoreApplication instance for tests that need it without a GUI."""
    return QApplication.instance() or QApplication([])