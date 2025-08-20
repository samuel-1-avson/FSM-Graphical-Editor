# tests/test_fsm_simulator.py
import pytest
# --- START MODIFICATION ---
# Import the parser and IR to create the FsmModel for the refactored simulator
from fsm_designer_project.core.fsm_parser import parse_diagram_to_ir
from fsm_designer_project.core.fsm_simulator import FSMSimulator, FSMError, check_code_safety_basic

@pytest.fixture
def toggle_fsm_data():
    return {
        "states": [
            {"name": "Off", "is_initial": True, "entry_action": "is_on = False"},
            {"name": "On", "entry_action": "is_on = True"},
        ],
        "transitions": [
            {"source": "Off", "target": "On", "event": "toggle"},
            {"source": "On", "target": "Off", "event": "toggle"},
        ]
    }

def test_fsm_initialization(toggle_fsm_data):
    # --- MODIFICATION: Instantiate simulator with FsmModel IR ---
    fsm_model = parse_diagram_to_ir(toggle_fsm_data)
    sim = FSMSimulator(fsm_model, context_object=None)
    # --- END MODIFICATION ---
    assert sim.get_current_state_name() == "Off"
    assert sim.get_variables()['is_on'] is False

def test_fsm_simple_transition(toggle_fsm_data):
    # --- MODIFICATION: Instantiate simulator with FsmModel IR ---
    fsm_model = parse_diagram_to_ir(toggle_fsm_data)
    sim = FSMSimulator(fsm_model, context_object=None)
    # --- END MODIFICATION ---
    sim.step(event_name="toggle")
    assert sim.get_current_state_name() == "On"
    assert sim.get_variables()['is_on'] is True
    sim.step(event_name="toggle")
    assert sim.get_current_state_name() == "Off"
    assert sim.get_variables()['is_on'] is False

def test_fsm_conditional_transition():
    fsm_data = {
        "states": [{"name": "A", "is_initial": True}, {"name": "B"}],
        "transitions": [
            {"source": "A", "target": "B", "event": "go", "condition": "x > 5", "action": "y = 10"}
        ]
    }
    # --- MODIFICATION: Instantiate simulator with FsmModel IR ---
    fsm_model = parse_diagram_to_ir(fsm_data)
    sim = FSMSimulator(fsm_model, context_object=None)
    # --- END MODIFICATION ---
    sim._variables['x'] = 3
    
    # Condition is false, should not transition
    sim.step(event_name="go")
    assert sim.get_current_state_name() == "A"
    assert 'y' not in sim.get_variables()

    # Condition is true, should transition
    sim._variables['x'] = 10
    sim.step(event_name="go")
    assert sim.get_current_state_name() == "B"
    assert sim.get_variables()['y'] == 10

def test_fsm_hierarchical_step():
    fsm_data = {
        "states": [
            {"name": "Idle", "is_initial": True},
            {"name": "Processing", "is_superstate": True, "sub_fsm_data": {
                "states": [
                    {"name": "SubIdle", "is_initial": True, "entry_action": "sub_status = 'idle'"},
                    {"name": "SubActive", "entry_action": "sub_status = 'active'"}
                ],
                "transitions": [{"source": "SubIdle", "target": "SubActive", "event": "work"}]
            }}
        ],
        "transitions": [{"source": "Idle", "target": "Processing", "event": "start"}]
    }
    # --- MODIFICATION: Instantiate simulator with FsmModel IR ---
    fsm_model = parse_diagram_to_ir(fsm_data)
    sim = FSMSimulator(fsm_model, context_object=None)
    # --- END MODIFICATION ---
    sim.step("start")
    assert sim.get_current_state_name() == "Processing (SubIdle)"
    assert sim.get_variables()['sub_status'] == 'idle'
    
    sim.step("work")
    assert sim.get_current_state_name() == "Processing (SubActive)"
    assert sim.get_variables()['sub_status'] == 'active'

def test_fsm_safety_checker():
    # Test unsafe code
    is_safe, msg = check_code_safety_basic("import os", set())
    assert not is_safe
    assert "Imports" in msg

    is_safe, msg = check_code_safety_basic("__import__('os').system('echo pwned')", set())
    assert not is_safe
    assert "Calling the function" in msg

    is_safe, msg = check_code_safety_basic("open('file.txt', 'w')", set())
    assert not is_safe
    assert "Calling the function 'open' is not allowed for security reasons" in msg
    
    is_safe, msg = check_code_safety_basic("my_obj.__class__", set())
    assert not is_safe
    assert "Access to the attribute '__class__' is restricted" in msg

    # Test safe code
    is_safe, msg = check_code_safety_basic("x = y + 10", {'y'})
    assert is_safe
    
    is_safe, msg = check_code_safety_basic("print(f'value: {x}')", {'x'})
    assert is_safe