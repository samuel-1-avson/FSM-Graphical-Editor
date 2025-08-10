# fsm_designer_project/core/__init__.py
"""Initializes the 'core' package and exposes its key classes."""

# Note: GitManager, HardwareLinkManager, MatlabConnection have been moved to 'services'.
# Note: CustomSnippetManager has been moved to 'managers'.
from .fsm_simulator import FSMSimulator, FSMError
from .resource_estimator import ResourceEstimator
from .fsm_ir import FsmModel, State, Transition, Comment, Action, Condition
from .fsm_parser import parse_diagram_to_ir
from .c_fsm_simulator import CFsmSimulator, CSimError

__all__ = [
    "FSMSimulator",
    "FSMError",
    "CFsmSimulator",
    "CSimError",
    "ResourceEstimator",
    "FsmModel",
    "State",
    "Transition",
    "Comment",
    "Action",
    "Condition",
    "parse_diagram_to_ir",
]