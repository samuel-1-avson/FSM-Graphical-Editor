# tests/ui/test_main_window_actions.py
import pytest
from PyQt6.QtCore import Qt, QPointF
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
    
    # Clear any previous test settings
    test_context.settings_manager.settings.clear()

    window = MainWindow(context=test_context)
    qtbot.addWidget(window)
    window.show()
    yield window
    window.close()

def test_application_startup(app, qtbot):
    """Test that the application starts up correctly and shows the welcome screen."""
    assert app.windowTitle().startswith("Brain State Machine Designer")
    assert app.centralWidget() == app.welcome_widget
    assert not app.tab_widget.isVisible()

def test_new_file_action_creates_tab(app, qtbot):
    """Test the 'New File' action creates a new, empty editor tab."""
    assert app.tab_widget.count() == 0
    
    # Simulate clicking 'File > New File'
    app.new_file_action.trigger()
    
    assert app.tab_widget.count() == 1
    assert app.centralWidget() == app.tab_widget
    editor = app.current_editor()
    assert editor is not None
    assert editor.file_path is None
    assert editor.get_tab_title() == "Untitled*"

def test_add_state_via_mode_button(app, qtbot):
    """
    Test that clicking the 'Add State' mode button and then the scene adds a state.
    """
    # Start with a clean tab
    app.new_file_action.trigger()
    editor = app.current_editor()
    scene = editor.scene
    
    initial_state_count = len([item for item in scene.items() if isinstance(item, GraphicsStateItem)])
    
    # 1. Activate "Add State" mode
    app.add_state_mode_action.trigger()
    assert scene.current_mode == "state"
    
    # 2. Simulate a click on the scene to place the state
    view = editor.view
    # We click in the center of the view's visible area
    scene_pos = view.mapToScene(view.viewport().rect().center())
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(scene_pos))

    # 3. Assert that a new state has been added
    final_states = [item for item in scene.items() if isinstance(item, GraphicsStateItem)]
    assert len(final_states) == initial_state_count + 1
    
    # 4. Verify properties of the new state
    new_state = final_states[0]
    assert new_state.text_label == "State_1" # Or whatever your naming scheme is
    assert new_state.isSelected()
    
    # 5. Check that the mode returned to "select"
    assert scene.current_mode == "select"