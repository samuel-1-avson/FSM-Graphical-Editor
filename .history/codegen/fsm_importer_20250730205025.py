# fsm_designer_project/utils/fsm_importer.py
import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def parse_plantuml(text: str) -> Dict:
    """Parses PlantUML state diagram text into a dictionary."""
    states = {}
    transitions = []
    initial_state = None
    state_actions = {}
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith("'") or line.startswith("hide empty description"):
            continue

        # Initial state
        match = re.match(r"\[\*\]\s*-->\s*(\w+)", line)
        if match:
            initial_state = match.group(1).strip()
            if initial_state not in states:
                states[initial_state] = {'is_initial': True}
            else:
                states[initial_state]['is_initial'] = True
            continue

        # State with actions
        match = re.match(r"(\w+)\s*:\s*(.*)", line)
        if match:
            state_name = match.group(1).strip()
            action_text = match.group(2).strip()
            if state_name not in states:
                states[state_name] = {'is_initial': False}
            
            if 'entry /' in action_text:
                states[state_name]['entry_action'] = action_text.split('entry /')[1].strip()
            elif 'exit /' in action_text:
                states[state_name]['exit_action'] = action_text.split('exit /')[1].strip()
            else: # During action
                states[state_name]['during_action'] = action_text
            continue

        # Transition
        match = re.match(r"(\w+)\s*-->\s*(\w+)\s*:\s*(.*)", line)
        if match:
            source, target, label = match.groups()
            source, target, label = source.strip(), target.strip(), label.strip()
            
            if source not in states: states[source] = {'is_initial': False}
            if target not in states: states[target] = {'is_initial': False}
            
            transitions.append({'source': source, 'target': target, 'event': label})
            continue
            
        # Simple state declaration
        if re.match(r"state\s+(\w+)", line):
            state_name = re.match(r"state\s+(\w+)", line).group(1).strip()
            if state_name not in states:
                states[state_name] = {'is_initial': False}
    
    state_list = [{'name': name, **props} for name, props in states.items()]
    return {'states': state_list, 'transitions': transitions, 'comments': []}

def parse_mermaid(text: str) -> Dict:
    """Parses Mermaid state diagram text into a dictionary."""
    states = {}
    transitions = []
    initial_state = None
    
    # Remove comments and empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip() and not line.strip().startswith('%%')]

    for line in lines:
        # Initial state
        match = re.match(r"\[\*\]\s*-->\s*(\w+)", line)
        if match:
            initial_state = match.group(1).strip()
            if initial_state not in states:
                states[initial_state] = {'is_initial': True}
            else:
                states[initial_state]['is_initial'] = True
            continue

        # Transition
        match = re.match(r"(\w+)\s*-->\s*(\w+)\s*:\s*(.*)", line)
        if match:
            source, target, event = match.groups()
            source, target, event = source.strip(), target.strip(), event.strip()
            
            if source not in states: states[source] = {'is_initial': False}
            if target not in states: states[target] = {'is_initial': False}
            
            transitions.append({'source': source, 'target': target, 'event': event})
            continue
        
        # State with actions
        match = re.match(r"(\w+)\s*:\s*(.*)", line)
        if match:
            state_name, action = match.groups()
            state_name, action = state_name.strip(), action.strip()
            if state_name not in states:
                states[state_name] = {'is_initial': False}
            # Mermaid doesn't distinguish action types in this syntax, assign to 'entry'
            states[state_name]['entry_action'] = action
            continue

    state_list = [{'name': name, **props} for name, props in states.items()]
    return {'states': state_list, 'transitions': transitions, 'comments': []}