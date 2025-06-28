# bsm_designer_project/editor_widget.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QUndoStack
from .graphics_scene import DiagramScene, ZoomableView
from .snippet_manager import CustomSnippetManager

class EditorWidget(QWidget):
    def __init__(self, main_window_ref, custom_snippet_manager: CustomSnippetManager):
        super().__init__(main_window_ref)
        self.mw = main_window_ref

        # Each editor tab has its own state
        self.file_path: str | None = None
        self._is_dirty = False

        # Each editor has its own undo stack
        self.undo_stack = QUndoStack(self)

        # Each editor has its own scene and view
        self.scene = DiagramScene(self.undo_stack, parent_window=self.mw, custom_snippet_manager=custom_snippet_manager)
        self.view = ZoomableView(self.scene, self)

        # Set up the layout for this widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        # Connect signals from this editor's scene to the main window's handlers
        self.scene.modifiedStatusChanged.connect(self.set_dirty)
        self.scene.selectionChanged.connect(self.mw._update_zoom_to_selection_action_enable_state)
        self.scene.selectionChanged.connect(self.mw._update_align_distribute_actions_enable_state)
        self.scene.selectionChanged.connect(self.mw._update_properties_dock)
        self.view.zoomChanged.connect(self.mw.update_zoom_status_display)
        
    def is_dirty(self) -> bool:
        return self._is_dirty

    def set_dirty(self, dirty=True):
        if self._is_dirty == dirty:
            return
        self._is_dirty = dirty
        
        # Find the index of this widget in the parent QTabWidget and update its title
        if tab_widget := self.parentWidget():
            if isinstance(tab_widget, QTabWidget):
                index = tab_widget.indexOf(self)
                if index != -1:
                    tab_widget.setTabText(index, self.get_tab_title())
                    # Also update the main window title if this is the active tab
                    if tab_widget.currentWidget() == self:
                        self.mw._update_window_title()

    def get_tab_title(self) -> str:
        """Generates the title for this tab, including the dirty indicator '*'."""
        base_name = "Untitled"
        if self.file_path:
            base_name = os.path.basename(self.file_path)
        
        return f"{base_name}{'*' if self.is_dirty() else ''}"