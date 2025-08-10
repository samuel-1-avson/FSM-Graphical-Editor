# fsm_designer_project/core/__init__.py
"""Initializes the 'core' package and exposes its key classes."""

# Note: GitManager, HardwareLinkManager, and MatlabConnection have been moved to the 'services' package.
# Note: CustomSnippetManager has been moved to the 'managers' package.
from .fsm_simulator import FSMSimulator, FSMError
from .resource_estimator import ResourceEstimator
from .snippet_manager import CustomSnippetManager

__all__ = [
    "FSMSimulator",
    "FSMError",
    "ResourceEstimator",
    "CustomSnippetManager",
]