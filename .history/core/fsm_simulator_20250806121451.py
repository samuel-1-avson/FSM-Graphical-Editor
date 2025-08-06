# fsm_designer_project/core/fsm_simulator.py
"""
Provides the core, non-GUI simulation engine for Finite State Machines.

This module contains the FSMSimulator class, which handles state transitions,
action execution, variable management, and hierarchical state logic based on
diagram data. It also includes a basic security checker for executing user code.
"""

import logging
import re
from typing import List, Dict, Any, Set, Tuple, Optional
# --- NEW: Import QObject and pyqtSignal for the data logging feature ---
from PyQt5.QtCore import QObject, pyqtSignal
# --- MODIFIED: Import the IR classes ---
from .fsm_ir import FsmModel, State
logger = logging.getLogger(__name__)

class FSMError(Exception):
    """Custom exception for FSM simulation errors."""
    pass

def check_code_safety_basic(code_str: str, known_vars: Set[str]) -> Tuple[bool, str]:
    """
    A basic security check for Python code snippets to prevent unsafe operations.

    This is not a foolproof sandbox but aims to block common dangerous patterns.

    Args:
        code_str: The Python code snippet to check.
        known_vars: A set of known safe variable names (not currently used but
                    available for future enhancements).

    Returns:
        A tuple containing a boolean (True if safe) and a message string
        (empty on success, descriptive on failure).
    """
    if "import " in code_str or "from " in code_str:
        return False, "Imports are not allowed in FSM actions/conditions."
    if re.search(r'\.[_]{2}[a-zA-Z_]+', code_str):
        match = re.search(r'\.[_]{2}([a-zA-Z_]+)', code_str)
        if match:
            return False, f"Access to the attribute '__{match.group(1)}' is restricted."
    disallowed_functions = ['open', 'eval', 'exec', 'exit', 'quit', 'input', 'compile', 'breakpoint', '__import__']
    for func in disallowed_functions:
        if re.search(rf'\b{func}\s*\(', code_str):
            return False, f"Calling the function '{func}' is not allowed for security reasons."
    return True, ""

# --- MODIFIED: The class now inherits from QObject to support signals ---
class FSMSimulator(QObject):
    """
    Core, non-GUI FSM simulation engine with support for hierarchical states.

    This class takes FSM data (states, transitions) and simulates its
    behavior based on incoming events. It manages the current state path,
    a dictionary of variables, and executes actions in a sandboxed environment.
    """
    # --- NEW: Signal to emit data after each tick for logging/plotting ---
    tick_processed = pyqtSignal(int, dict)

    def __init__(self, fsm_model: FsmModel, halt_on_action_error: bool = False):
        super().__init__()
        
        self.model = fsm_model
        self._halt_on_error = halt_on_action_error
        
        self._initial_variables = {}
        self._variables: Dict[str, Any] = {}
        
        self.current_tick = 0
        self.paused_on_breakpoint = False
        self.simulation_halted_flag = False
        self.breakpoints: Dict[str, Set[Any]] = {'states': set(), 'transitions': set()}
        self._action_log: List[str] = []
        self.current_state_path: List[State] = [] # Now a list of State objects
        self._internal_event_queue: List[str] = []
        
        self.stop_at_tick = -1

        self.reset()

    # --- NEW: Method to support the Data Dictionary feature ---
    def set_initial_variables(self, initial_vars: dict):
        """
        Sets the initial state of variables for the simulation.
        This is called before the simulation starts.
        """
        self._initial_variables = initial_vars.copy()
        # The reset method will use this new initial state
        self.reset()

    # --- NEW: Method to support formal simulation time ---
    def set_stop_tick(self, tick: int):
        """Sets a tick count at which the simulation should automatically halt."""
        self.stop_at_tick = tick if tick > 0 else -1

    def reset(self) -> None:
        """Resets the simulator to its initial state and clears all variables."""
        self._action_log.clear()
        
        # --- MODIFIED: Reset variables to the initial set from the data dictionary ---
        self._variables.clear()
        self._variables.update(self._initial_variables)
        
        self.current_tick = 0
        self.paused_on_breakpoint = False
        self.simulation_halted_flag = False
        self.current_state_path = []
        self._internal_event_queue.clear()
        
        initial_state = next((s for s_name, s in self.states.items() if s.get('is_initial')), None)
        if not initial_state and self.states:
            initial_state = next(iter(self.states.values()))
        
        if initial_state:
            self._enter_state(initial_state)
        else:
            self.simulation_halted_flag = True
            raise FSMError("No states found in FSM data.")

    def _enter_state(self, state_data: Dict[str, Any]) -> None:
        """Internal method to handle the logic of entering a new state."""
        self.current_state_path.append(state_data)
        self.log_action(f"Entering state: {self.get_current_state_name()}")
        self._execute_action(state_data.get('entry_action'))

        # Check for completion of a sub-machine
        if state_data.get('is_final') and len(self.current_state_path) > 1:
            parent_state = self.current_state_path[-2]
            completion_event = f"__internal_completion_for_{parent_state['name']}"
            self.send(completion_event)
            self.log_action(f"Sub-machine in '{parent_state['name']}' reached final state. Queued completion event.")

        # If entering a superstate, recursively enter its initial sub-state
        if state_data.get('is_superstate'):
            sub_fsm_data = state_data.get('sub_fsm_data', {})
            sub_states = {s['name']: s for s in sub_fsm_data.get('states', [])}
            sub_initial = next((s for s_name, s in sub_states.items() if s.get('is_initial')), None)
            if not sub_initial and sub_states:
                sub_initial = next(iter(sub_states.values()))
            
            if sub_initial:
                self._enter_state(sub_initial)

    def _execute_action(self, code: Optional[str]) -> None:
        """Executes a code snippet safely in the simulator's variable context."""
        if not code:
            return
            
        is_safe, msg = check_code_safety_basic(code, set(self._variables.keys()))
        if not is_safe:
            error = f"[ACTION BLOCKED] {msg}: '{code}'"
            self.log_action(error)
            if self._halt_on_error:
                self.simulation_halted_flag = True
                raise FSMError(error)
            return
            
        try:
            exec_globals = {'sm': self, 'current_tick': self.current_tick}
            exec(code, exec_globals, self._variables)
        except Exception as e:
            error = f"[CODE ERROR] {type(e).__name__}: {e} in code: '{code}'"
            self.log_action(error)
            if self._halt_on_error:
                self.simulation_halted_flag = True
                raise FSMError(error)

    def send(self, event_name: str) -> None:
        """Allows action code to post an event for processing in the current step."""
        if event_name:
            self.log_action(f"Internal event '{event_name}' sent.")
            self._internal_event_queue.append(event_name)

    def step(self, event_name: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Executes a single step of the simulation.
        ...
        """
        # --- START FIX ---
        # MODIFIED: The halt/breakpoint/stop_tick checks are now at the top,
        # before the tick is incremented, to ensure correct termination.
        if self.stop_at_tick > 0 and self.current_tick >= self.stop_at_tick:
            self.simulation_halted_flag = True
            if not any("Reached configured stop tick" in log for log in self._action_log):
                 self.log_action(f"[HALT] Reached configured stop tick: {self.stop_at_tick}")
            return self.get_current_state_name(), self.get_last_executed_actions_log()

        if self.simulation_halted_flag or self.paused_on_breakpoint:
            return self.get_current_state_name(), self.get_last_executed_actions_log()
        # --- END FIX ---
        
        # Original position of the checks was here, which was incorrect.
        self.current_tick += 1
        self._action_log.clear()
        
        events_to_process = self._internal_event_queue[:]
        self._internal_event_queue.clear()

        # Execute 'during' action, which might queue more internal events
        current_leaf_state = self.current_state_path[-1]
        self._execute_action(current_leaf_state.get('during_action'))
        
        events_to_process.extend(self._internal_event_queue)
        self._internal_event_queue.clear()
        if event_name:
            events_to_process.append(event_name)
        
        transition_taken_this_step = False
        while events_to_process and not transition_taken_this_step:
            current_event = events_to_process.pop(0)
            
            # Check for transitions from the innermost state outwards
            for i in range(len(self.current_state_path) - 1, -1, -1):
                state_to_check = self.current_state_path[i]
                
                is_completion_event = current_event == f"__internal_completion_for_{state_to_check['name']}"

                for trans in self.transitions:
                    if trans['source'] != state_to_check['name']:
                        continue

                    event_matches = (trans.get('event') == current_event) or (is_completion_event and not trans.get('event'))
                    if not event_matches:
                        continue
                        
                    condition_ok = True
                    if trans.get('condition'):
                        try:
                            condition_ok = bool(eval(trans['condition'], {"__builtins__": {}}, self._variables))
                        except Exception as e:
                            self.log_action(f"[EVAL ERROR] {e} in condition: '{trans['condition']}'")
                            condition_ok = False
                    
                    if condition_ok:
                        # --- TRANSITION BREAKPOINT CHECK ---
                        transition_tuple = (trans['source'], trans['target'], trans.get('event'))
                        if transition_tuple in self.breakpoints['transitions']:
                            self.paused_on_breakpoint = True
                            self.log_action(f"BREAKPOINT HIT on transition from '{trans['source']}' to '{trans['target']}' on event '{trans.get('event')}'")
                            # We must return here BEFORE executing any actions
                            return self.get_current_state_name(), self.get_last_executed_actions_log()

                        log_event_name = "completion" if is_completion_event else current_event
                        self.log_action(f"Transition on '{log_event_name}' from '{state_to_check['name']}' to '{trans['target']}'")

                        # Exit all states up to the transition's source
                        for _ in range(len(self.current_state_path) - 1, i - 1, -1):
                            exiting_state = self.current_state_path.pop()
                            self.log_action(f"Exiting state: {exiting_state['name']}")
                            self._execute_action(exiting_state.get('exit_action'))

                        self._execute_action(trans.get('action'))
                        
                        new_state_data = self.states.get(trans['target'])
                        if new_state_data:
                            self._enter_state(new_state_data)
                            if self.current_state_path[-1]['name'] in self.breakpoints['states']:
                                self.paused_on_breakpoint = True
                                self.log_action(f"BREAKPOINT HIT at state {self.current_state_path[-1]['name']}")
                        else:
                            raise FSMError(f"Target state '{trans['target']}' not found.")
                        
                        transition_taken_this_step = True
                        break  # from for trans loop
                
                if transition_taken_this_step:
                    break  # from for state_to_check loop

        # --- NEW: Emit signal with current tick data for plotting ---
        self.tick_processed.emit(self.current_tick, self._variables.copy())
        # --- END NEW ---

        return self.get_current_state_name(), self.get_last_executed_actions_log()

    def get_current_state_name(self) -> str:
        """Returns the full hierarchical path of the current state."""
        if not self.current_state_path:
            return "Halted"
        return " (".join(s['name'] for s in self.current_state_path) + ")" * (len(self.current_state_path) - 1)

    def get_current_leaf_state_name(self) -> str:
        """Returns the name of the innermost active state."""
        return self.current_state_path[-1]['name'] if self.current_state_path else "Halted"

    def get_variables(self) -> Dict[str, Any]:
        """Returns a copy of the current simulation variables."""
        return self._variables.copy()

    def log_action(self, msg: str) -> None:
        """Adds a message to the internal action log for the current step."""
        prefix = "[SUB] " * (len(self.current_state_path) - 1)
        self._action_log.append(f"{prefix}[Tick {self.current_tick}] {msg}")

    def get_last_executed_actions_log(self) -> List[str]:
        """Returns and clears the log of actions from the most recent step."""
        log = self._action_log[:]
        self._action_log.clear()
        return log

    def get_possible_events_from_current_state(self) -> List[str]:
        """Gets a list of all valid event strings that can trigger a transition from any active state."""
        if not self.current_state_path:
            return []
        
        possible_events = set()
        for state in self.current_state_path:
            for t in self.transitions:
                if t['source'] == state['name'] and t.get('event'):
                    possible_events.add(t['event'])
        return sorted(list(possible_events))

    def add_state_breakpoint(self, state_name: str) -> None:
        """Adds a breakpoint for a specific state."""
        self.breakpoints['states'].add(state_name)

    def remove_state_breakpoint(self, state_name: str) -> None:
        """Removes a breakpoint for a specific state."""
        self.breakpoints['states'].discard(state_name)

    def add_transition_breakpoint(self, source: str, target: str, event: str | None):
        """Adds a breakpoint for a specific transition."""
        self.breakpoints['transitions'].add((source, target, event))

    def remove_transition_breakpoint(self, source: str, target: str, event: str | None):
        """Removes a breakpoint for a specific transition."""
        self.breakpoints['transitions'].discard((source, target, event))

    def continue_simulation(self) -> bool:
        """Resumes the simulation if it is currently paused at a breakpoint."""
        if self.paused_on_breakpoint:
            self.paused_on_breakpoint = False
            return True
        return False