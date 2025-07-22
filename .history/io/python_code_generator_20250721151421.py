# fsm_designer_project/python_code_generator.py
import os
import re
import logging
import textwrap
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PyQt5.QtCore import QDateTime, Qt

try:
    from ..utils.config import APP_NAME, APP_VERSION, DEFAULT_EXECUTION_ENV
except ImportError:
    APP_NAME, APP_VERSION, DEFAULT_EXECUTION_ENV = "BSM_Designer", "Unknown", "Python (Generic Simulation)"

logger = logging.getLogger(__name__)

# ... (sanitize_python_identifier function remains unchanged) ...
PYTHON_KEYWORDS = {"False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"}
def sanitize_python_identifier(name_str: str, prefix_if_invalid="s_") -> str:
    # (Same implementation as before)
    if not name_str:
        return f"{prefix_if_invalid}unnamed_identifier"
    sanitized = name_str
    for char_to_replace in " .-:/\\[]{}()\"'":
        sanitized = sanitized.replace(char_to_replace, '_')
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    if not sanitized:
        return f"{prefix_if_invalid}sanitized_empty"
    if sanitized[0].isdigit():
        sanitized = prefix_if_invalid + sanitized
    if not sanitized:
        return f"{prefix_if_invalid}sanitized_empty_after_digit_prefix"
    if sanitized in PYTHON_KEYWORDS:
        sanitized = f"{sanitized}_"
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', sanitized):
        generic_name = "".join(c if c.isalnum() else '_' for c in name_str if c.isprintable())
        generic_name = re.sub(r'_+', '_', generic_name).strip('_')
        if not generic_name: return f"{prefix_if_invalid}fully_sanitized_empty"
        candidate = generic_name
        if candidate[0].isdigit(): candidate = prefix_if_invalid + candidate
        if candidate in PYTHON_KEYWORDS: candidate += "_"
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', candidate):
            import hashlib
            name_hash = hashlib.md5(name_str.encode()).hexdigest()[:6]
            return f"{prefix_if_invalid}id_{name_hash}"
        return candidate
    return sanitized


def generate_python_fsm_code(diagram_data: dict, class_name_base: str) -> str:
    """Generates the Python FSM class code as a string."""
    states = diagram_data.get('states', [])
    transitions = diagram_data.get('transitions', [])

    if not states:
        raise ValueError("Cannot generate Python code: No states defined.")

    # --- Setup Jinja2 ---
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True)

    # --- Prepare Data for Template ---
    temp_class_name = sanitize_python_identifier(class_name_base, "FSM")
    class_name = temp_class_name[0].upper() + temp_class_name[1:] if temp_class_name else "GeneratedFsm"
    
    description = next((s['description'] for s in states if s.get('is_initial')), diagram_data.get('description', 'A Finite State Machine.'))
    
    context = {
        "app_name": APP_NAME, "app_version": APP_VERSION,
        "fsm_name_original": class_name_base, "class_name": class_name,
        "description": description, "timestamp": QDateTime.currentDateTime().toString(Qt.ISODate),
        "states": [], "transitions": []
    }

    state_name_to_py_var = {}
    initial_state_found = False

    # Process States
    for s_data in states:
        original_name = s_data['name']
        py_var_name = sanitize_python_identifier(original_name.lower(), "state_")
        state_name_to_py_var[original_name] = py_var_name
        
        is_initial = s_data.get('is_initial', False) and not initial_state_found
        if is_initial: initial_state_found = True

        state_ctx = {"original_name": original_name, "py_var_name": py_var_name, "is_initial": is_initial,
                     "is_final": s_data.get('is_final', False), "action_language": s_data.get('action_language', DEFAULT_EXECUTION_ENV)}

        for action_key, code_str in [('entry', s_data.get('entry_action')), ('exit', s_data.get('exit_action'))]:
            if code_str:
                method_name = sanitize_python_identifier(f"on_{action_key}_{original_name.lower()}", "action_")
                state_ctx[f'{action_key}_method'] = method_name
                state_ctx[f'{action_key}_action_code'] = code_str
        if s_data.get('during_action'):
            state_ctx['during_action_code'] = s_data.get('during_action')
            
        context['states'].append(state_ctx)
    
    if not initial_state_found and context['states']:
        context['states'][0]['is_initial'] = True # Default to first if none marked

    # Process Transitions
    for i, t_data in enumerate(transitions):
        src_name, tgt_name, event_str = t_data.get('source'), t_data.get('target'), t_data.get('event', '').strip()
        if not all([src_name, tgt_name, event_str]): continue

        src_py_var = state_name_to_py_var.get(src_name)
        tgt_py_var = state_name_to_py_var.get(tgt_name)
        if not src_py_var or not tgt_py_var: continue

        trans_ctx = {
            "py_var_name": sanitize_python_identifier(f"t_{src_py_var}_to_{tgt_py_var}_on_{event_str.lower()}", f"t_{i}_"),
            "source_py_var": src_py_var, "target_py_var": tgt_py_var,
            "source_name": src_name, "target_name": tgt_name, "event_str": event_str,
            "action_language": t_data.get('action_language', DEFAULT_EXECUTION_ENV)
        }
        
        if cond_code := t_data.get('condition', '').strip():
            trans_ctx['cond_method'] = sanitize_python_identifier(f"check_{trans_ctx['py_var_name']}", "cond_")
            trans_ctx['condition_code'] = cond_code

        if act_code := t_data.get('action', '').strip():
            trans_ctx['on_method'] = sanitize_python_identifier(f"do_{trans_ctx['py_var_name']}", "act_")
            trans_ctx['action_code'] = act_code

        context['transitions'].append(trans_ctx)

    template = env.get_template("python_fsm.py.j2")
    return template.render(context)


def generate_python_fsm_file(diagram_data: dict, output_dir: str, class_name_base: str) -> str:
    """Generates the Python FSM file by calling the content generator and writing to disk."""
    try:
        py_code = generate_python_fsm_code(diagram_data, class_name_base)
        
        file_name = f"{sanitize_python_identifier(class_name_base.lower())}.py"
        py_file_path = os.path.join(output_dir, file_name)
        
        with open(py_file_path, 'w', encoding='utf-8') as f:
            f.write(py_code)
        
        logger.info(f"Generated Python FSM file: {py_file_path}")
        return py_file_path
    except (ValueError, IOError) as e:
        logger.error(f"Failed to generate Python FSM file: {e}", exc_info=True)
        raise