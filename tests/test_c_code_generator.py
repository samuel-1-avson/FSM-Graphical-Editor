# tests/test_c_code_generator.py
import pytest
from fsm_designer_project.c_code_generator import sanitize_c_identifier, generate_c_code_content

def test_sanitize_c_identifier():
    assert sanitize_c_identifier("State Name 1") == "State_Name_1"
    assert sanitize_c_identifier("1_State") == "s_1_State"
    assert sanitize_c_identifier("My-State.Name") == "My_State_Name"
    assert sanitize_c_identifier("if") == "fsm_if"
    assert sanitize_c_identifier("some_var(copy)") == "some_varcopy"
    assert sanitize_c_identifier("") == "s_Unnamed"
    assert sanitize_c_identifier("____") == "s_SanitizedEmpty"

def test_generate_c_code_from_simple_fsm():
    diagram_data = {
        "states": [
            {"name": "Off", "is_initial": True, "entry_action": "set_led_off();"},
            {"name": "On", "exit_action": "log_exit_on();"}
        ],
        "transitions": [
            {"source": "Off", "target": "On", "event": "toggle", "condition": "is_enabled == true", "action": "count_toggles();"}
        ]
    }
    
    code = generate_c_code_content(diagram_data, "my_blinker")

    # Test Header File (.h)
    assert "FSM_MY_BLINKER_H" in code['h']
    assert "typedef enum {" in code['h']
    assert "STATE_OFF," in code['h']
    assert "STATE_ON," in code['h']
    assert "EVENT_TOGGLE," in code['h']
    assert "void my_blinker_init(void);" in code['h']
    assert "void entry_action_Off(void);" in code['h']
    assert "void action_trans_Off_to_On_toggle(void);" in code['h']
    assert "void exit_action_On(void);" in code['h']

    # Test Source File (.c)
    assert '#include "my_blinker.h"' in code['c']
    assert "static FSM_State_t current_fsm_state;" in code['c']
    assert "current_fsm_state = STATE_OFF;" in code['c']
    assert "case STATE_OFF:" in code['c']
    assert "if ((event_id == EVENT_TOGGLE) && (is_enabled == true))" in code['c']
    assert "next_state = STATE_ON;" in code['c']
    assert "void entry_action_Off(void)" in code['c']
    assert "// Original Python-like action(s):\n    // set_led_off();" in code['c']

def test_generate_c_code_empty_fsm():
    with pytest.raises(ValueError, match="Cannot generate code: No states defined"):
        generate_c_code_content({}, "empty_fsm")