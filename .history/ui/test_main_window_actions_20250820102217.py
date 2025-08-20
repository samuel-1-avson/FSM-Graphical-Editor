# tests/ui/test_main_window_actions.py
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from fsm_designer_project.main import MainWindow
from fsm_designer_project.core.application_context import ApplicationContext
from fsm_designer_project.ui.graphics.graphics_items import GraphicsStateItem

# Make sure qapp_args is available from conftest.py
pytestmark = pytest.mark.usefixtures("qapp_args")

@pytest.fixture
def app(qtbot):
    """Create and tear down the main application window."""
    # Use the ApplicationContext for proper dependency injection
    test_context = ApplicationContext(app_name="BSM_Test_App_UI")
    window = MainWindow(context=test_context)
    qtbot.addWidget(window)
    window.show()
    yield window
    window.close()

def test_add_state_action(app, qtbot):
    """
    Test that clicking the 'Add State' button adds a state to the current scene.
    """
    # 1. Ensure we start with a clean tab
    app.action_handler.file_handler.on_new_file()
    editor = app.current_editor()
    assert editor is not None
    scene = editor.scene
    
    # 2. Count the number of states before the action
    initial_state_count = len([item for item in scene.items() if isinstance(item, GraphicsStateItem)])
    assert initial_state_count == 0

    # 3. Simulate a user clicking the "Add State" button in the ribbon
    # Note: We trigger the action directly, which is equivalent to a click.
    qtbot.mouseClick(app.add_state_mode_action, Qt.MouseButton.LeftButton) # Switch to Add State mode
    
    # Simulate a click on the scene to place the state
    view = editor.view
    scene_pos = view.mapToScene(view.viewport().rect().center())
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(scene_pos))

    # 4. Assert that a new state has been added
    final_states = [item for item in scene.items() if isinstance(item, GraphicsStateItem)]
    assert len(final_states) == initial_state_count + 1
    
    # Optional: More detailed assertions
    new_state = final_states[0]
    assert new_state.text_label.startswith("State")
    assert new_state.isSelected()