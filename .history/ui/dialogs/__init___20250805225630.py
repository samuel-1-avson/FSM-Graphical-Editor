
# fsm_designer_project/ui/dialogs/__init__.py
"""
Initializes the dialogs package and re-exports all dialog classes from
their respective modules. This allows other parts of the application
to continue importing them directly from `ui.dialogs`.
"""

# Import from property dialogs module
from .property_dialogs import (
    StatePropertiesDialog,
    TransitionPropertiesDialog,
    CommentPropertiesDialog,
    SubFSMEditorDialog
)

# Import from settings dialogs module
from .settings_dialogs import (
    SettingsDialog,
    ThemeEditDialog
)

# Import from tool dialogs module
from .tool_dialogs import (
    FindItemDialog,
    SnippetManagerDialog,
    SnippetEditDialog,
    AutoLayoutPreviewDialog,
    ImportFromTextDialog,
    SystemInfoDialog,
    QuickAccessSettingsDialog
)

# Import from the new project dialog file
from .new_project_dialog import NewProjectDialog

# Define the public API of this package
__all__ = [
    "StatePropertiesDialog",
    "TransitionPropertiesDialog",
    "CommentPropertiesDialog",
    "SubFSMEditorDialog",
    "SettingsDialog",
    "ThemeEditDialog",
    "FindItemDialog",
    "SnippetManagerDialog",
    "SnippetEditDialog",
    "AutoLayoutPreviewDialog",
    "ImportFromTextDialog",
    "NewProjectDialog",
    "SystemInfoDialog",
    "QuickAccessSettingsDialog",
]
