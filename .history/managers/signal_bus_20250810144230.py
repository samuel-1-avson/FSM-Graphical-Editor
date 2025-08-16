# fsm_designer_project/managers/signal_bus.py
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QGraphicsItem
from typing import Dict

# A central place for all cross-component signals
class SignalBus(QObject):
    # File Operations
    request_new_file = pyqtSignal()
    request_open_file = pyqtSignal()
    request_save_file = pyqtSignal(bool)  # Returns success
    request_save_file_as = pyqtSignal(bool) # Returns success
    file_path_changed = pyqtSignal(str) # editor_file_path
    
    # UI State & Commands
    status_message_posted = pyqtSignal(str, str) # level, message
    ui_element_focus_requested = pyqtSignal(QGraphicsItem)
    ui_update_requested = pyqtSignal() # General signal to refresh UI state
    
    # Simulation
    simulation_started = pyqtSignal(object) # fsm_engine instance
    simulation_stopped = pyqtSignal()
    simulation_state_changed = pyqtSignal(bool) # is_active
    
    # AI
    ai_fix_requested = pyqtSignal(dict) # fix_data
    ai_fsm_generation_requested = pyqtSignal(str) # description
    
    # Settings
    theme_change_requested = pyqtSignal(str) # theme_name
    
    # Project
    project_loaded = pyqtSignal(str, dict) # path, data
    project_closed = pyqtSignal()
    
    def __init__(self):
        super().__init__()

# Create a singleton instance for global access
signal_bus = SignalBus()