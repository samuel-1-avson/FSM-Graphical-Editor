# fsm_designer_project/core/fsm_parser.py
"""
Parses the raw diagram data from a JSON file into the structured
Intermediate Representation (IR) defined in fsm_ir.py.

This module acts as the bridge between the stored file format and the
application's internal logic, ensuring that all backends (simulators,
code generators) receive a consistent and validated FSM model.
"""
import logging
from typing import Dict, Any, Optional

from .fsm_ir import FsmModel, State, Transition, Comment, Action, Condition

logger = logging.getLogger(__name__)

def parse_diagram_to_ir(diagram_data: Dict[str, Any], fsm_name: Optional[str] = "UntitledFSM") -> FsmModel:
    """
    Parses a diagram data dictionary from a .bsm file into the FsmModel IR.

    This function handles the conversion of flat dictionary data into structured
    dataclasses, including recursive parsing for hierarchical sub-machines.

    Args:
        diagram_data: The raw dictionary loaded from a .bsm JSON file.
        fsm_name: An optional name for the top-level FSM model.

    Returns:
        An FsmModel instance representing the complete FSM.
    """
    
    fsm = FsmModel(name=fsm_name)

    # --- Parse States ---
    for state_data in diagram_data.get('states', []):
        if not isinstance(state_data, dict) or 'name' not in state_data:
            logger.warning(f"Skipping invalid state data entry: {state_data}")
            continue

        state = State(
            name=state_data['name'],
            is_initial=state_data.get('is_initial', False),
            is_final=state_data.get('is_final', False),
            is_superstate=state_data.get('is_superstate', False),
            description=state_data.get('description', ''),
            properties={k: v for k, v in state_data.items() if k not in [
                'name', 'is_initial', 'is_final', 'is_superstate', 'description',
                'entry_action', 'during_action', 'exit_action', 'sub_fsm_data', 'action_language'
            ]}
        )
        
        lang = state_data.get('action_language', "Python (Generic Simulation)")
        
        if state_data.get('entry_action'):
            state.entry_action = Action(language=lang, code=state_data['entry_action'])
        if state_data.get('during_action'):
            state.during_action = Action(language=lang, code=state_data['during_action'])
        if state_data.get('exit_action'):
            state.exit_action = Action(language=lang, code=state_data['exit_action'])
        
        # Recursively parse sub-FSMs for hierarchical states
        if state.is_superstate and state_data.get('sub_fsm_data'):
            sub_fsm_name = f"SubFSM_{state.name}"
            state.sub_fsm = parse_diagram_to_ir(state_data['sub_fsm_data'], fsm_name=sub_fsm_name)
        
        fsm.states[state.name] = state

    # --- Parse Transitions ---
    for trans_data in diagram_data.get('transitions', []):
        if not isinstance(trans_data, dict) or 'source' not in trans_data or 'target' not in trans_data:
            logger.warning(f"Skipping invalid transition data entry: {trans_data}")
            continue

        trans = Transition(
            source_name=trans_data['source'],
            target_name=trans_data['target'],
            event=trans_data.get('event'),
            description=trans_data.get('description', ''),
            properties={k: v for k, v in trans_data.items() if k not in [
                'source', 'target', 'event', 'condition', 'action', 'description', 'action_language'
            ]}
        )
        
        lang = trans_data.get('action_language', "Python (Generic Simulation)")
        
        if trans_data.get('condition'):
            trans.condition = Condition(language=lang, code=trans_data['condition'])
        if trans_data.get('action'):
            trans.action = Action(language=lang, code=trans_data['action'])
        
        fsm.transitions.append(trans)

    # --- Parse Comments ---
    for comment_data in diagram_data.get('comments', []):
        if not isinstance(comment_data, dict) or 'text' not in comment_data:
            logger.warning(f"Skipping invalid comment data entry: {comment_data}")
            continue

        comment = Comment(
            text=comment_data['text'],
            properties={k: v for k, v in comment_data.items() if k != 'text'}
        )
        fsm.comments.append(comment)

    return fsm