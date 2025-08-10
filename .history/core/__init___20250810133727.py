# fsm_designer_project/core/__init__.py
"""Initializes the 'core' package and exposes its key classes."""

from .fsm_simulator import FSMSimulator, FSMError
from ..services.git_manager import GitManager
from .hardware_link_manager import HardwareLinkManager
from .matlab_integration import MatlabConnection
from .resource_estimator import ResourceEstimator
from .snippet_manager import CustomSnippetManager

__all__ = [
    "FSMSimulator",
    "FSMError",
    "GitManager",
    "HardwareLinkManager",
    "MatlabConnection",
    "ResourceEstimator",
    "CustomSnippetManager",
]