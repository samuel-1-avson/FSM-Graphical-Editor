# fsm_designer_project/fsm_importer.py
import re
import logging

logger = logging.getLogger(__name__)

def parse_plantuml(text: str) -> dict:
    diagram_data = {"states": [], "transitions": [], "comments": []}
    id_to_name_map = {}
    states_dict = {} # Use dict for easy access by ID

    # Regex patterns
    state_pattern = re.compile(r'^\s*state\s+"([^"]+)"\s+as\s+([a-zA-Z0-9_]+)')
    state_simple_pattern = re.compile(r'^\s*state\s+([a-zA-Z0-9_]+)')
    action_pattern = re.compile(r'^\s*([a-zA-Z0-9_]+)\s*:\s*(entry|exit|during)\s*/\s*(.*)')
    transition_pattern = re.compile(r'^\s*([a-zA-Z0-9_]+|\[\*\])\s*-->\s*([a-zA-Z0-9_]+|\[\*\])\s*(?::\s*(.*))?')
    
    # First pass: find all states
    for line in text.splitlines():
        match = state_pattern.match(line)
        if match:
            name, state_id = match.groups()
            id_to_name_map[state_id] = name
            states_dict[state_id] = {"name": name, "is_initial": False, "is_final": False}
        else:
            match_simple = state_simple_pattern.match(line)
            if match_simple:
                name = match_simple.group(1)
                state_id = name # If no 'as', ID is the name
                id_to_name_map[state_id] = name
                states_dict[state_id] = {"name": name, "is_initial": False, "is_final": False}

    # Second pass: parse actions and transitions
    for line in text.splitlines():
        action_match = action_pattern.match(line)
        if action_match:
            state_id, action_type, code = action_match.groups()
            if state_id in states_dict:
                states_dict[state_id][f"{action_type}_action"] = code.replace('\\n', '\n')
            continue

        trans_match = transition_pattern.match(line)
        if trans_match:
            src_id, tgt_id, label = trans_match.groups()
            
            if src_id == "[*]" and tgt_id in states_dict:
                states_dict[tgt_id]["is_initial"] = True
                continue
            if tgt_id == "[*]" and src_id in states_dict:
                states_dict[src_id]["is_final"] = True
                continue
                
            if src_id in id_to_name_map and tgt_id in id_to_name_map:
                trans_data = {"source": id_to_name_map[src_id], "target": id_to_name_map[tgt_id]}
                if label:
                    # Simple label parsing for event/condition/action
                    # A more robust parser would be needed for complex labels
                    parts = re.match(r"([^\[/]*)(?:\[(.*?)\])?(?:/\s*\{(.*?)\})?", label.strip())
                    if parts:
                        event, condition, action = parts.groups()
                        trans_data["event"] = event.strip() if event else ""
                        trans_data["condition"] = condition.strip() if condition else ""
                        trans_data["action"] = action.strip().replace('\\n', '\n') if action else ""
                diagram_data["transitions"].append(trans_data)

    diagram_data["states"] = list(states_dict.values())
    return diagram_data

def parse_mermaid(text: str) -> dict:
    # Implementation would be similar, with different regexes
    logger.warning("Mermaid parsing is not yet fully implemented.")
    return {"states": [], "transitions": [], "comments": []}