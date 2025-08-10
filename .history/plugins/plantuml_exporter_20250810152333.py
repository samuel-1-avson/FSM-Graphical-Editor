# fsm_designer_project/codegen/plantuml_exporter.py
from typing import Dict

def generate_plantuml_text(diagram_data: Dict) -> str:
    """Generates PlantUML text from diagram data."""
    lines = ["@startuml", "hide empty description"]
    
    states = diagram_data.get('states', [])
    transitions = diagram_data.get('transitions', [])

    # Initial state
    initial_state = next((s['name'] for s in states if s.get('is_initial')), None)
    if initial_state:
        lines.append(f"[*] --> {initial_state}")

    # State definitions with actions
    for state in states:
        name = state.get('name')
        if name:
            lines.append(f"state {name} {{")
            if state.get('entry_action'):
                lines.append(f"  {name} : entry / {state['entry_action'].replace(chr(10), '; ')}")
            if state.get('during_action'):
                lines.append(f"  {name} : {state['during_action'].replace(chr(10), '; ')}")
            if state.get('exit_action'):
                lines.append(f"  {name} : exit / {state['exit_action'].replace(chr(10), '; ')}")
            lines.append("}")

    # Transitions
    for t in transitions:
        source = t.get('source')
        target = t.get('target')
        label_parts = []
        if t.get('event'):
            label_parts.append(t['event'])
        if t.get('condition'):
            label_parts.append(f"[{t['condition']}]")
        if t.get('action'):
            label_parts.append(f"/ {t['action']}")
        
        label = " ".join(label_parts)
        lines.append(f"{source} --> {target} : {label}")

    lines.append("@enduml")
    return "\n".join(lines)