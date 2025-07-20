# fsm_designer_project/editor_widget.py

import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QUndoStack, QTabWidget

from .graphics_scene import DiagramScene, ZoomableView
from .snippet_manager import CustomSnippetManager
from .fsm_simulator import FSMSimulator, FSMError  # Import the simulator class for type hinting


class EditorWidget(QWidget):
    """
    A self-contained widget for a single tab in the main application.
    It encapsulates the scene, view, undo stack, and its own simulation state.
    """
    def __init__(self, main_window_ref, custom_snippet_manager: CustomSnippetManager):
        super().__init__(main_window_ref)
        self.mw = main_window_ref

        # --- Each editor tab now has its own state ---
        self.file_path: str | None = None
        self._is_dirty = False
        
        # <<< FIX: Each editor gets its own simulation engine and state. >>>
        # This is the core change to fix the bug. The simulation engine and its
        # active status are now tied to the tab, not the main window.
        self.py_fsm_engine: FSMSimulator | None = None
        self.py_sim_active = False
        self.has_uncommitted_changes = False # New property for Git status

        # Each editor has its own undo stack
        self.undo_stack = QUndoStack(self)

        # Each editor has its own scene and view
        self.scene = DiagramScene(self.undo_stack, parent_window=self.mw, custom_snippet_manager=custom_snippet_manager)
        self.view = ZoomableView(self.scene, self)

        # Set up the layout for this widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        # NOTE: Signal connections from the scene/view to the MainWindow are now
        # handled centrally in MainWindow._connect_editor_signals(). This makes
        # the component more self-contained and improves architectural clarity.

    def is_dirty(self) -> bool:
        """Returns True if the diagram has been modified since the last save."""
        return self._is_dirty

    def set_dirty(self, dirty=True):
        """Sets the dirty status and triggers a tab title update."""
        if self._is_dirty == dirty:
            return
        self._is_dirty = dirty
        
        # Find the index of this widget in the parent QTabWidget and update its title
        if (tab_widget := self.parentWidget()) and isinstance(tab_widget, QTabWidget):
            index = tab_widget.indexOf(self)
            if index != -1:
                tab_widget.setTabText(index, self.get_tab_title())
                # Also update the main window title if this is the active tab
                if tab_widget.currentWidget() == self:
                    self.mw._update_window_title()

    def get_tab_title(self) -> str:
        """
        Generates the title for this tab, including a dirty indicator '*'
        and a simulation status indicator. Git status is handled by icon now.
        """
        base_name = "Untitled"
        if self.file_path:
            base_name = os.path.basename(self.file_path)
        
        dirty_indicator = '*' if self.is_dirty() else ''
        
        # <<< FIX: Add a visual indicator when this specific tab is being simulated. >>>
        sim_indicator = " [Simulating]" if self.py_sim_active else ''
        
        return f"{base_name}{dirty_indicator}{sim_indicator}"