# enhanced_fsm_simulator.py
"""
Enhanced FSM Simulator that integrates with your existing statemachine-based simulator
and provides comprehensive animation and visualization capabilities.
"""

import logging
from typing import List, Dict, Set, Optional, Tuple, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QMessageBox, QGraphicsScene
from PyQt5.QtGui import QColor
from enum import Enum
import time

logger = logging.getLogger(__name__)

class SimulationMode(Enum):
    STOPPED = 0
    RUNNING = 1
    PAUSED = 2
    STEP_MODE = 3
    BREAKPOINT_PAUSED = 4

class AnimatedFSMSimulator(QObject):
    """
    Enhanced FSM simulator that integrates with your existing StateMachinePoweredSimulator
    and provides rich animation and visualization capabilities.
    """
    
    # Signals for GUI communication
    state_changed = pyqtSignal(str, str)  # current_state, previous_state
    transition_fired = pyqtSignal(str, str, str)  # from_state, to_state, event
    simulation_started = pyqtSignal()
    simulation_paused = pyqtSignal()
    simulation_stopped = pyqtSignal()
    simulation_finished = pyqtSignal()
    step_executed = pyqtSignal(int)  # step_number
    error_occurred = pyqtSignal(str)
    variables_changed = pyqtSignal(dict)
    breakpoint_hit = pyqtSignal(str)  # state_name
    log_message = pyqtSignal(str, str)  # message, level
    
    # Animation-specific signals
    animate_state_entry = pyqtSignal(str)  # state_name
    animate_state_exit = pyqtSignal(str)   # state_name
    animate_transition = pyqtSignal(str, str, str)  # from, to, event
    animate_input_symbol = pyqtSignal(str, int)  # symbol, position_index
    
    def __init__(self, graphics_scene=None, animation_manager=None):
        super().__init__()
        
        # Core simulator integration
        self.core_simulator = None  # Will be set with load_fsm_data
        self.graphics_scene = graphics_scene
        self.animation_manager = animation_manager
        
        # Simulation state
        self.mode = SimulationMode.STOPPED
        self.current_step = 0
        self.total_steps = 0
        self.previous_state = None
        
        # Input and execution
        self.input_sequence = []
        self.input_index = 0
        self.execution_history = []
        
        # Timing and control
        self.step_timer = QTimer()
        self.step_timer.setSingleShot(True)
        self.step_timer.timeout.connect(self._execute_next_step)
        self.step_delay = 1000  # milliseconds between steps
        
        # Animation synchronization
        self.animation_delay = 500  # delay for animations to complete
        self.sync_timer = QTimer()
        self.sync_timer.setSingleShot(True)
        self.sync_timer.timeout.connect(self._animation_sync_complete)
        
        # State mapping for graphics items
        self.state_graphics_map = {}  # state_name -> graphics_item
        self.transition_graphics_map = {}  # (from, to, event) -> graphics_item
        
        # Breakpoints and debugging
        self.breakpoints = set()
        self.watch_variables = set()
        
        # Thread safety
        self.mutex = QMutex()
    
    def load_fsm_data(self, states_data: List[Dict], transitions_data: List[Dict]):
        """Load FSM data and create the core simulator."""
        try:
            # Import your existing simulator
            from fsm_simulator import StateMachinePoweredSimulator
            
            self.core_simulator = StateMachinePoweredSimulator(
                states_data=states_data,
                transitions_data=transitions_data,
                halt_on_action_error=False
            )
            
            self.log_message.emit("FSM loaded successfully", "info")
            self._build_graphics_mapping()
            
        except Exception as e:
            error_msg = f"Failed to load FSM: {str(e)}"
            self.error_occurred.emit(error_msg)
            logger.error(error_msg, exc_info=True)
    
    def _build_graphics_mapping(self):
        """Build mapping between FSM states and graphics items."""
        if not self.graphics_scene:
            return
            
        self.state_graphics_map.clear()
        self.transition_graphics_map.clear()
        
        # Map states to graphics items
        for item in self.graphics_scene.items():
            if hasattr(item, 'state_name'):
                self.state_graphics_map[item.state_name] = item
            elif hasattr(item, 'transition_id'):
                # Assuming transition items have source, target, event info
                key = (item.source_state, item.target_state, item.event_name)
                self.transition_graphics_map[key] = item
    
    def set_input_sequence(self, sequence: List[str]):
        """Set the input sequence for simulation."""
        self.input_sequence = sequence
        self.input_index = 0
        self.total_steps = len(sequence)
        self.log_message.emit(f"Input sequence set: {sequence}", "info")
    
    def set_input_string(self, input_str: str, delimiter: str = None):
        """Convert input string to sequence."""
        if delimiter:
            sequence = [s.strip() for s in input_str.split(delimiter) if s.strip()]
        else:
            sequence = list(input_str) if input_str else []
        
        self.set_input_sequence(sequence)
    
    def start_simulation(self):
        """Start automatic simulation."""
        if not self.core_simulator:
            self.error_occurred.emit("No FSM loaded")
            return
        
        if not self.input_sequence:
            self.error_occurred.emit("No input sequence provided")
            return
        
        self.mode = SimulationMode.RUNNING
        self.current_step = 0
        self.input_index = 0
        self.execution_history.clear()
        
        # Reset core simulator
        self.core_simulator.reset()
        
        # Get initial state and trigger animation
        initial_state = self.core_simulator.get_current_leaf_state_name()
        if initial_state and initial_state != "UnknownLeaf":
            self.previous_state = None
            self.state_changed.emit(initial_state, "")
            self.animate_state_entry.emit(initial_state)
        
        self.simulation_started.emit()
        self.log_message.emit("Simulation started", "info")
        
        # Start first step after animation delay
        self.sync_timer.start(self.animation_delay)
    
    def pause_simulation(self):
        """Pause the simulation."""
        if self.mode == SimulationMode.RUNNING:
            self.mode = SimulationMode.PAUSED
            self.step_timer.stop()
            self.sync_timer.stop()
            self.simulation_paused.emit()
            self.log_message.emit("Simulation paused", "info")
    
    def resume_simulation(self):
        """Resume paused simulation."""
        if self.mode == SimulationMode.PAUSED:
            self.mode = SimulationMode.RUNNING
            # Continue with next step
            self.sync_timer.start(self.step_delay)
            self.log_message.emit("Simulation resumed", "info")
    
    def stop_simulation(self):
        """Stop and reset simulation."""
        self.mode = SimulationMode.STOPPED
        self.step_timer.stop()
        self.sync_timer.stop()
        
        if self.core_simulator:
            self.core_simulator.reset()
        
        self.current_step = 0
        self.input_index = 0
        self.execution_history.clear()
        
        self.simulation_stopped.emit()
        self.log_message.emit("Simulation stopped", "info")
    
    def step_once(self):
        """Execute a single simulation step."""
        if not self.core_simulator:
            self.error_occurred.emit("No FSM loaded")
            return
        
        old_mode = self.mode
        self.mode = SimulationMode.STEP_MODE
        
        if self.input_index >= len(self.input_sequence):
            if old_mode == SimulationMode.STEP_MODE:
                self.mode = SimulationMode.STOPPED
            self.simulation_finished.emit()
            return
        
        self._execute_step()
        
        if old_mode == SimulationMode.STEP_MODE:
            self.mode = SimulationMode.STOPPED
    
    def _execute_next_step(self):
        """Execute the next step in automatic mode."""
        if self.mode != SimulationMode.RUNNING:
            return
        
        if self.input_index >= len(self.input_sequence):
            self.mode = SimulationMode.STOPPED
            self.simulation_finished.emit()
            self.log_message.emit("Simulation completed", "info")
            return
        
        self._execute_step()
        
        # Schedule next step if still running
        if self.mode == SimulationMode.RUNNING:
            self.sync_timer.start(self.step_delay)
    
    def _execute_step(self):
        """Execute a single step of the simulation."""
        if not self.core_simulator or self.input_index >= len(self.input_sequence):
            return
        
        current_input = self.input_sequence[self.input_index]
        old_state = self.core_simulator.get_current_leaf_state_name()
        
        # Animate input consumption
        self.animate_input_symbol.emit(current_input, self.input_index)
        
        # Execute step in core simulator
        try:
            new_state, action_log = self.core_simulator.step(event_name=current_input)
            
            # Process action log
            for log_entry in action_log:
                self.log_message.emit(log_entry, "debug")
            
            # Check for state change
            if new_state != old_state and new_state != "UnknownLeaf":
                # Animate state exit
                if old_state and old_state != "UnknownLeaf":
                    self.animate_state_exit.emit(old_state)
                
                # Animate transition
                self.animate_transition.emit(old_state, new_state, current_input)
                
                # Animate state entry
                self.animate_state_entry.emit(new_state)
                
                # Emit state change signal
                self.state_changed.emit(new_state, old_state)
                self.previous_state = old_state
                
                # Check for breakpoints
                if new_state in self.breakpoints:
                    self.mode = SimulationMode.BREAKPOINT_PAUSED
                    self.breakpoint_hit.emit(new_state)
                    self.log_message.emit(f"Breakpoint hit at state: {new_state}", "warning")
                    return
            
            # Update variables and emit signal
            variables = self.core_simulator.get_variables()
            self.variables_changed.emit(variables)
            
            # Check for watched variables
            for var_name in self.watch_variables:
                if var_name in variables:
                    self.log_message.emit(f"Watch variable '{var_name}': {variables[var_name]}", "info")
            
            # Record execution step
            step_info = {
                'step': self.current_step,
                'input': current_input,
                'from_state': old_state,
                'to_state': new_state,
                'variables': variables.copy()
            }
            self.execution_history.append(step_info)
            
            self.current_step += 1
            self.input_index += 1
            self.step_executed.emit(self.current_step)
            
        except Exception as e:
            error_msg = f"Error during step execution: {str(e)}"
            self.error_occurred.emit(error_msg)
            self.mode = SimulationMode.STOPPED
            logger.error(error_msg, exc_info=True)
    
    def _animation_sync_complete(self):
        """Called when animation sync timer completes."""
        if self.mode == SimulationMode.RUNNING:
            self._execute_next_step()
    
    def continue_from_breakpoint(self):
        """Continue simulation from a breakpoint."""
        if self.mode == SimulationMode.BREAKPOINT_PAUSED:
            self.mode = SimulationMode.RUNNING
            self.sync_timer.start(self.step_delay)
            self.log_message.emit("Continuing from breakpoint", "info")
    
    def set_simulation_speed(self, speed_percent: int):
        """Set simulation speed as percentage (1-100)."""
        # Convert percentage to delay (inverse relationship)
        min_delay = 100
        max_delay = 3000
        self.step_delay = max_delay - (speed_percent / 100.0) * (max_delay - min_delay)
        self.step_delay = int(max(min_delay, min(max_delay, self.step_delay)))
    
    def add_breakpoint(self, state_name: str):
        """Add a breakpoint at the specified state."""
        self.breakpoints.add(state_name)
        if self.core_simulator:
            self.core_simulator.add_state_breakpoint(state_name)
        self.log_message.emit(f"Breakpoint added at state: {state_name}", "info")
    
    def remove_breakpoint(self, state_name: str):
        """Remove a breakpoint from the specified state."""
        self.breakpoints.discard(state_name)
        if self.core_simulator:
            self.core_simulator.remove_state_breakpoint(state_name)
        self.log_message.emit(f"Breakpoint removed from state: {state_name}", "info")
    
    def add_watch_variable(self, var_name: str):
        """Add a variable to watch during simulation."""
        self.watch_variables.add(var_name)
        self.log_message.emit(f"Watching variable: {var_name}", "info")
    
    def remove_watch_variable(self, var_name: str):
        """Remove a variable from watch list."""
        self.watch_variables.discard(var_name)
    
    def get_current_state(self) -> str:
        """Get the current state name."""
        if self.core_simulator:
            return self.core_simulator.get_current_leaf_state_name()
        return "Unknown"
    
    def get_possible_events(self) -> List[str]:
        """Get list of possible events from current state."""
        if self.core_simulator:
            return self.core_simulator.get_possible_events_from_current_state()
        return []
    
    def get_variables(self) -> Dict[str, Any]:
        """Get current FSM variables."""
        if self.core_simulator:
            return self.core_simulator.get_variables()
        return {}
    
    def get_execution_history(self) -> List[Dict]:
        """Get the execution history."""
        return self.execution_history.copy()
    
    def is_running(self) -> bool:
        """Check if simulation is currently running."""
        return self.mode == SimulationMode.RUNNING
    
    def is_paused(self) -> bool:
        """Check if simulation is paused."""
        return self.mode in [SimulationMode.PAUSED, SimulationMode.BREAKPOINT_PAUSED]
    
    def is_stopped(self) -> bool:
        """Check if simulation is stopped."""
        return self.mode == SimulationMode.STOPPED
    
    def get_progress(self) -> Tuple[int, int]:
        """Get simulation progress (current_step, total_steps)."""
        return (self.current_step, self.total_steps)