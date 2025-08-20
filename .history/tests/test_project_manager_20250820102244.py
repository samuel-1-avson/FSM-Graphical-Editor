# fsm_designer_project/tests/test_project_manager.py

import os
import json
import pytest
from PyQt6.QtCore import QObject
from pathlib import Path

# Import the core components needed for testing
from fsm_designer_project.managers import ProjectManager
from fsm_designer_project.managers.signal_bus import signal_bus
from fsm_designer_project.utils.config import PROJECT_FILE_EXTENSION, FILE_EXTENSION

# conftest.py should provide this fixture to initialize a QApplication instance
pytestmark = pytest.mark.usefixtures("qapp_args")


@pytest.fixture
def project_manager():
    """
    Provides a ProjectManager instance for testing.
    Crucially, it uses a dummy QObject as a parent instead of a full QMainWindow.
    """
    dummy_parent = QObject()
    pm = ProjectManager(parent=dummy_parent)
    return pm

def test_project_manager_initial_state(project_manager):
    """Test that the project manager starts in a clean, non-project state."""
    assert not project_manager.is_project_open()
    assert project_manager.current_project_path is None
    assert not project_manager.project_data

def test_create_new_project(project_manager, tmp_path: Path, qtbot):
    """Test the successful creation of a new project."""
    project_name = "TestProject"
    main_diagram = f"main_fsm{FILE_EXTENSION}"
    project_dir = tmp_path / project_name
    project_file_path = project_dir / f"{project_name}{PROJECT_FILE_EXTENSION}"

    # Use qtbot to wait for the project_loaded signal from the global signal bus
    with qtbot.waitSignal(signal_bus.project_loaded, timeout=1000) as blocker:
        success = project_manager.create_new_project(
            project_path=str(project_file_path),
            project_name=project_name,
            main_diagram_filename=main_diagram
        )

    # --- Assertions ---
    assert success is True
    assert project_manager.is_project_open()
    assert project_manager.current_project_path == str(project_file_path)
    
    # Check project data in the manager
    assert project_manager.project_data["name"] == project_name
    assert project_manager.project_data["main_diagram"] == main_diagram
    assert project_manager.project_data["version"] == "1.0"

    # Check that files were actually created on disk
    assert project_file_path.exists()
    main_diagram_path = project_dir / main_diagram
    assert main_diagram_path.exists()

    # Verify the content of the created files
    with open(project_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert data["name"] == project_name
    
    with open(main_diagram_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert data == {"states": [], "transitions": [], "comments": []}

    # Verify the signal was emitted correctly
    assert blocker.args[0] == str(project_file_path)
    assert blocker.args[1]["name"] == project_name

def test_load_project(project_manager, tmp_path: Path, qtbot):
    """Test loading an existing, valid project."""
    # First, create a valid project structure to load
    project_name = "ExistingProject"
    main_diagram = f"diagram1{FILE_EXTENSION}"
    project_dir = tmp_path / project_name
    project_dir.mkdir()
    project_file_path = project_dir / f"{project_name}{PROJECT_FILE_EXTENSION}"
    
    project_data = {
        "version": "1.0",
        "name": project_name,
        "main_diagram": main_diagram
    }
    with open(project_file_path, 'w', encoding='utf-8') as f:
        json.dump(project_data, f)
    
    # Now, test loading it
    with qtbot.waitSignal(signal_bus.project_loaded, timeout=1000) as blocker:
        success = project_manager.load_project(str(project_file_path))

    assert success is True
    assert project_manager.is_project_open()
    assert project_manager.project_data["name"] == project_name
    
    # Verify the signal was emitted correctly
    assert blocker.args[0] == str(project_file_path)
    assert blocker.args[1]["name"] == project_name

def test_load_nonexistent_project(project_manager):
    """Test that loading a non-existent project fails gracefully."""
    success = project_manager.load_project("/non/existent/path/project.bsmproj")
    assert success is False
    assert not project_manager.is_project_open()

def test_load_invalid_project_file(project_manager, tmp_path: Path):
    """Test loading a malformed project file."""
    invalid_file = tmp_path / "invalid.bsmproj"
    
    # Test 1: Not a valid JSON file
    with open(invalid_file, 'w', encoding='utf-8') as f:
        f.write("this is not json")
    
    success = project_manager.load_project(str(invalid_file))
    assert success is False
    assert not project_manager.is_project_open()

    # Test 2: Valid JSON but missing required keys
    with open(invalid_file, 'w', encoding='utf-8') as f:
        json.dump({"some_other_key": "value"}, f)
        
    success = project_manager.load_project(str(invalid_file))
    assert success is False
    assert not project_manager.is_project_open()

def test_close_project(project_manager, tmp_path: Path, qtbot):
    """Test that closing a project resets the state and emits the correct signal."""
    # First, load a project to have something to close
    project_name = "ProjectToClose"
    project_dir = tmp_path / project_name
    project_dir.mkdir()
    project_file_path = project_dir / f"{project_name}{PROJECT_FILE_EXTENSION}"
    with open(project_file_path, 'w', encoding='utf-8') as f:
        json.dump({"name": project_name, "main_diagram": "main.bsm"}, f)
    
    project_manager.load_project(str(project_file_path))
    assert project_manager.is_project_open()

    # Now, close it and check the signal
    with qtbot.waitSignal(signal_bus.project_closed, timeout=1000):
        project_manager.close_project()

    assert not project_manager.is_project_open()
    assert project_manager.current_project_path is None
    assert not project_manager.project_data

def test_save_project(project_manager, tmp_path: Path):
    """Test saving changes to project data."""
    # Create a project first
    project_name = "ProjectToSave"
    project_dir = tmp_path / project_name
    project_file_path = project_dir / f"{project_name}{PROJECT_FILE_EXTENSION}"
    project_manager.create_new_project(str(project_file_path), project_name, "main.bsm")
    
    # Modify the project data
    project_manager.project_data["new_key"] = "new_value"
    project_manager.project_data["name"] = "Modified Name"
    
    # Save the project
    success = project_manager.save_project()
    assert success is True

    # Verify the saved file on disk
    with open(project_file_path, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    
    assert saved_data["name"] == "Modified Name"
    assert saved_data["new_key"] == "new_value"