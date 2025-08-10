# fsm_designer_project/utils/python_code_generator.py
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
    templates_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("python_fsm.py.j2")
    
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