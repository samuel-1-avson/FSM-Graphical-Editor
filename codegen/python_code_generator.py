# fsm_designer_project/codegen/python_code_generator.py
import re
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
from typing import Dict
from ..utils.config import APP_NAME, APP_VERSION

def sanitize_python_identifier(name: str) -> str:
    """Sanitizes a string to be a valid Python identifier."""
    if not name: return "unnamed_fsm_item"
    s = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if not s or not s[0].isalpha():
        s = "fsm_" + s
    return s

def generate_python_fsm_code(diagram_data: Dict, class_name: str) -> str:
    """Generates a Python FSM class file content."""
    # Note: Corrected path for templates location relative to this file
    templates_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("python_fsm.py.j2")
    
    # Prepare states for the template
    for state in diagram_data.get('states', []):
        state_name = state.get('name', 'unnamed_state')
        state['original_name'] = state_name
        state['py_var_name'] = sanitize_python_identifier(state_name)
        if state.get('entry_action'):
            state['entry_method'] = f"on_enter_{state['py_var_name']}"
            state['entry_action_code'] = state.get('entry_action', '')
        else:
            state['entry_method'] = None
        if state.get('exit_action'):
            state['exit_method'] = f"on_exit_{state['py_var_name']}"
            state['exit_action_code'] = state.get('exit_action', '')
        else:
            state['exit_method'] = None
        state['during_action_code'] = state.get('during_action', '')
        state['action_language'] = state.get('action_language', 'Python')

    # Prepare transitions for the template
    for trans in diagram_data.get('transitions', []):
        source_state = next((s for s in diagram_data['states'] if s['name'] == trans['source']), None)
        target_state = next((s for s in diagram_data['states'] if s['name'] == trans['target']), None)

        if source_state and target_state:
            trans['source_name'] = source_state.get('name')
            trans['target_name'] = target_state.get('name')
            trans['source_py_var'] = sanitize_python_identifier(source_state['name'])
            trans['target_py_var'] = sanitize_python_identifier(target_state['name'])
            trans['event_str'] = trans.get('event', f"event_{trans['source_py_var']}_to_{trans['target_py_var']}")
            trans['py_var_name'] = sanitize_python_identifier(trans['event_str'])
            
            if trans.get('condition'):
                trans['cond_method'] = f"cond_{trans['py_var_name']}"
                trans['condition_code'] = trans.get('condition', 'True')
            else:
                trans['cond_method'] = None

            if trans.get('action'):
                trans['on_method'] = f"on_{trans['py_var_name']}"
                trans['action_code'] = trans.get('action', 'pass')
            else:
                trans['on_method'] = None
            
            trans['action_language'] = trans.get('action_language', 'Python')

    # Prepare context for the template
    context = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fsm_name_original": class_name,
        "class_name": sanitize_python_identifier(class_name),
        "description": "Auto-generated FSM from BSM Designer.",
        "states": diagram_data['states'],
        "transitions": diagram_data['transitions']
    }
    
    return template.render(context)