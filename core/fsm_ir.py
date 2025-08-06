# fsm_designer_project/core/fsm_ir.py
"""
Defines the Intermediate Representation (IR) for a Finite State Machine.

These data classes provide a language-agnostic, structured representation of an FSM,
serving as the single source of truth for all simulation engines and code
generators. The IR decouples the application's core logic from the specifics
of the .bsm file format.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

# ==============================================================================
# Atomic IR Components
# ==============================================================================

@dataclass
class Action:
    """
    Represents a piece of code to be executed, associated with a specific
    programming language or execution environment.
    """
    language: str = "Python (Generic Simulation)"
    code: str = ""

@dataclass
class Condition(Action):
    """
    Represents a condition to be evaluated. It is structurally identical
    to an Action but semantically represents a boolean expression.
    """
    pass

# ==============================================================================
# Structural IR Components
# ==============================================================================

@dataclass
class State:
    """Represents a single state in the FSM."""
    name: str
    is_initial: bool = False
    is_final: bool = False
    is_superstate: bool = False
    entry_action: Optional[Action] = None
    during_action: Optional[Action] = None
    exit_action: Optional[Action] = None
    description: str = ""
    # Stores visual properties like color, position, font, etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    # For hierarchical FSMs, this holds the nested FSM model.
    sub_fsm: Optional['FsmModel'] = None

@dataclass
class Transition:
    """Represents a transition between two states."""
    source_name: str
    target_name: str
    event: Optional[str] = None
    condition: Optional[Condition] = None
    action: Optional[Action] = None
    description: str = ""
    # Stores visual properties like color, line style, curve offsets, etc.
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Comment:
    """Represents a comment or note on the diagram."""
    text: str
    # Stores visual properties like position, width, font, etc.
    properties: Dict[str, Any] = field(default_factory=dict)

# ==============================================================================
# Root IR Model
# ==============================================================================

@dataclass
class FsmModel:
    """
    The root container for the entire FSM Intermediate Representation.
    It holds all states, transitions, and other diagram-level information.
    """
    name: str = "UntitledFSM"
    states: Dict[str, State] = field(default_factory=dict)
    transitions: List[Transition] = field(default_factory=list)
    comments: List[Comment] = field(default_factory=list)
    # Top-level metadata, such as project name or author.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_initial_state(self) -> Optional[State]:
        """
        Finds and returns the initial state of the FSM.
        
        Returns:
            The State object marked as initial, or the first state found
            as a fallback, or None if no states exist.
        """
        for state in self.states.values():
            if state.is_initial:
                return state
        # Fallback if no initial state is explicitly marked
        return next(iter(self.states.values()), None)

    def get_state(self, name: str) -> Optional[State]:
        """Convenience method to retrieve a state by its name."""
        return self.states.get(name)