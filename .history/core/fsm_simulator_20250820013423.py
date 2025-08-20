# fsm_designer_project/core/fsm_simulator.py
"""
Provides the core, non-GUI simulation engine for Finite State Machines.

This module contains the FSM Simulator, which executes FSM logic based on
the Intermediate Representation (IR). It uses Python's built-in `exec` and
`eval` functions to run user-defined action and condition code, providing a
flexible simulation environment.

It also supports timed transitions and hierarchical state logic.
"""

import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from .fsm_ir import FsmModel, State, Action, Condition, Transition

logger = logging.getLogger(__name__)

class FSMError(Exception):
    """Custom exception for FSM simulation errors."""
    pass

def check_code_safety_basic(code_str: str, known_vars: Set[str]) -> Tuple[bool, str]:
    """
    A basic security check for Python code snippets.
    This is not a sandbox, but prevents the most common dangerous operations.
    """
    import re
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


class FSMSimulator(QObject):
    """
    Core, non-GUI FSM simulation engine that executes code from the FSM model.
    """
    tick_processed = pyqtSignal(int, dict)
    # --- NEW SIGNAL ---
    transitionTaken = pyqtSignal(str, str, str) # from_state, to_state, event

    def __init__(self, fsm_model: FsmModel, halt_on_action_error: bool = False):
        super().__init__()
        
        self.model = fsm_model
        self._halt_on_error = halt_on_action_error
        self._variables: Dict[str, Any] = {}
        
        self.current_tick = 0
        self.paused_on_breakpoint = False
        self.simulation_halted_flag = False
        self.breakpoints: Dict[str, Set[Any]] = {'states': set(), 'transitions': set()}
        self._action_log: List[str] = []
        self.current_state_path: List[State] = []
        self._internal_event_queue: List[str] = []
        # --- FIX: Use hashable state name as key ---
        self._active_timers: Dict[str, Tuple[int, Transition]] = {}
        
        self.stop_at_tick = -1

        self.reset()

    def set_initial_variables(self, initial_vars: Dict[str, Any]):
        """Sets the initial variables for the simulation."""
        self._variables = initial_vars.copy()
        self.log_action(f"Initial variables set: {self._variables}")

    def set_stop_tick(self, tick: int):
        """Sets a tick count at which the simulation should automatically halt."""
        self.stop_at_tick = tick if tick > 0 else -1

    def reset(self) -> None:
        self._action_log.clear()
        self._variables.clear()
        self.log_action("Simulation variables reset.")
        
        self.current_tick = 0
        self.paused_on_breakpoint = False
        self.simulation_halted_flag = False
        self.current_state_path = []
        self._internal_event_queue.clear()
        self._active_timers.clear()
        
        initial_state = self.model.get_initial_state()
        if not initial_state and self.model.states:
            initial_state = next(iter(self.model.states.values()))
        
        if initial_state:
            self._enter_state(initial_state)
        else:
            self.simulation_halted_flag = True
            raise FSMError("No states found in FSM model.")

    def _enter_state(self, state: State) -> None:
        """Internal method to handle the logic of entering a new state."""
        self.current_state_path.append(state)
        self.log_action(f"Entering state: {self.get_current_state_name()}")
        self._execute_action(state.entry_action)

        # Check for completion of a sub-machine
        if state.is_final and len(self.current_state_path) > 1:
            parent_state = self.current_state_path[-2]
            completion_event = f"__internal_completion_for_{parent_state.name}"
            self.send(completion_event)
            self.log_action(f"Sub-machine in '{parent_state.name}' reached final state. Queued completion event.")

        # If entering a superstate, recursively enter its initial sub-state
        if state.is_superstate and state.sub_fsm:
            sub_initial = state.sub_fsm.get_initial_state()
            if sub_initial:
                self._enter_state(sub_initial)

    def _execute_action(self, action: Optional[Action]) -> None:
        """Executes an action using Python's `exec` function."""
        if not action or not action.code:
            return
            
        if action.language != "Python (Generic Simulation)":
            self.log_action(f"[SKIPPED] Action with language '{action.language}' cannot be executed in Python simulator.")
            return

        is_safe, msg = check_code_safety_basic(action.code, set(self._variables.keys()))
        if not is_safe:
            error = f"[SECURITY] Unsafe code blocked: {msg} in '{action.code}'"
            self.log_action(error)
            if self._halt_on_error:
                self.simulation_halted_flag = True
                raise FSMError(error)
            return
            
        try:
            exec(action.code, {"sm": self, "current_tick": self.current_tick}, self._variables)
        except Exception as e:
            error = f"[CODE ERROR] In action '{action.code}': {type(e).__name__} - {e}"
            self.log_action(error)
            if self._halt_on_error:
                self.simulation_halted_flag = True
                raise FSMError(error)

    def _evaluate_condition(self, condition: Optional[Condition]) -> bool:
        """Evaluates a condition using Python's `eval` function."""
        if not condition or not condition.code:
            return True  # A transition with no condition is considered true

        if condition.language != "Python (Generic Simulation)":
            self.log_action(f"[SKIPPED] Condition with language '{condition.language}' cannot be evaluated in Python simulator. Assuming False.")
            return False
            
        is_safe, msg = check_code_safety_basic(condition.code, set(self._variables.keys()))
        if not is_safe:
            error = f"[SECURITY] Unsafe code blocked: {msg} in '{condition.code}'"
            self.log_action(error)
            return False

        try:
            result = bool(eval(condition.code, {"sm": self}, self._variables))
            self.log_action(f"Condition '{condition.code}' -> {result}")
            return result
        except Exception as e:
            error = f"[CODE ERROR] In condition '{condition.code}': {type(e).__name__} - {e}"
            self.log_action(error)
            return False

    def send(self, event_name: str) -> None:
        """Allows action code to post an event for processing in the current step."""
        if event_name:
            self.log_action(f"Internal event '{event_name}' sent.")
            self._internal_event_queue.append(event_name)

    def step(self, event_name: Optional[str] = None) -> Tuple[str, List[str]]:
        if self.stop_at_tick > 0 and self.current_tick >= self.stop_at_tick:
            self.simulation_halted_flag = True
            if not any("Reached configured stop tick" in log for log in self._action_log):
                 self.log_action(f"[HALT] Reached configured stop tick: {self.stop_at_tick}")
            return self.get_current_state_name(), self.get_last_executed_actions_log()

        if self.simulation_halted_flag or self.paused_on_breakpoint:
            return self.get_current_state_name(), self.get_last_executed_actions_log()
        
        self.current_tick += 1
        self._action_log.clear()
        
        # 1. Process timed events
        for state_name, (expiry_tick, trans) in list(self._active_timers.items()):
            if self.current_tick >= expiry_tick:
                # Timer expired, inject a unique internal event
                timer_event = f"__internal_timer_for_{state_name}"
                self.send(timer_event)
                del self._active_timers[state_name]

        # 2. Gather all events for this step
        events_to_process = self._internal_event_queue[:]
        self._internal_event_queue.clear()
        if event_name:
            events_to_process.append(event_name)
        
        # 3. Execute "during" action of the current leaf state
        current_leaf_state = self.current_state_path[-1]
        self._execute_action(current_leaf_state.during_action)
        
        # Re-check internal queue in case 'during' action sent an event
        events_to_process.extend(self._internal_event_queue)
        self._internal_event_queue.clear()

        # 4. Process transitions for all events in the queue for this step
        transition_taken_this_step = False
        while events_to_process and not transition_taken_this_step:
            current_event = events_to_process.pop(0)
            
            # --- FIX: Iterate from the deepest state outwards ---
            for i in range(len(self.current_state_path) - 1, -1, -1):
                state_to_check = self.current_state_path[i]
                
                # Determine the correct FSM model for transition lookup
                # --- FIX: Handle transitions out of top-level superstates ---
                if i == 0:
                    fsm_context_for_transitions = self.model
                else:
                    parent_state = self.current_state_path[i-1]
                    fsm_context_for_transitions = parent_state.sub_fsm if parent_state.is_superstate else self.model
                
                is_completion_event = current_event == f"__internal_completion_for_{state_to_check.name}"
                is_timer_event = False # Timers not implemented in IR yet

                for trans in fsm_context_for_transitions.transitions:
                    if trans.source_name != state_to_check.name:
                        continue

                    event_matches = (
                        (trans.event == current_event) or
                        (is_completion_event and not trans.event)
                    )
                    if not event_matches:
                        continue
                        
                    if self._evaluate_condition(trans.condition):
                        transition_tuple = (trans.source_name, trans.target_name, trans.event)
                        if transition_tuple in self.breakpoints['transitions']:
                            self.paused_on_breakpoint = True
                            self.log_action(f"BREAKPOINT HIT on transition from '{trans.source_name}' to '{trans.target_name}'")
                            return self.get_current_state_name(), self.get_last_executed_actions_log()

                        log_event_name = "completion" if is_completion_event else current_event
                        self.log_action(f"Transition on '{log_event_name}' from '{state_to_check.name}' to '{trans.target_name}'")

                        # --- NEW: Emit signal for animation ---
                        self.transitionTaken.emit(trans.source_name, trans.target_name, trans.event or "")

                        # Exit states up to the source of the transition
                        # --- FIX: Ensure path is not empty before popping ---
                        while len(self.current_state_path) > i:
                            exiting_state = self.current_state_path.pop()
                            self.log_action(f"Exiting state: {exiting_state.name}")
                            if exiting_state.name in self._active_timers:
                                del self._active_timers[exiting_state.name]
                                self.log_action(f"Timer cancelled for state '{exiting_state.name}'.")
                            self._execute_action(exiting_state.exit_action)
                        
                        self._execute_action(trans.action)
                        
                        # --- FIX: Look up the new state in the correct FSM model context ---
                        new_state = fsm_context_for_transitions.states.get(trans.target_name)
                        if new_state:
                            self._enter_state(new_state)
                            if new_state.name in self.breakpoints['states']:
                                self.paused_on_breakpoint = True
                                self.log_action(f"BREAKPOINT HIT at state {new_state.name}")
                        else:
                            raise FSMError(f"Target state '{trans.target_name}' not found.")
                        
                        transition_taken_this_step = True
                        break
                
                if transition_taken_this_step:
                    break

        self.tick_processed.emit(self.current_tick, self.get_variables())
        return self.get_current_state_name(), self.get_last_executed_actions_log()

    def get_current_state_name(self) -> str:
        """Returns the full hierarchical path of the current state."""
        if not self.current_state_path:
            return "Halted"
        return " (".join(s.name for s in self.current_state_path) + ")" * (len(self.current_state_path) - 1)

    def get_current_leaf_state_name(self) -> str:
        """Returns the name of the innermost active state."""
        return self.current_state_path[-1].name if self.current_state_path else "Halted"

    def get_variables(self) -> Dict[str, Any]:
        """Returns a copy of the simulation variables."""
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
            for t in self.model.transitions:
                if t.source_name == state.name and t.event:
                    possible_events.add(t.event)
        return sorted(list(possible_events))

    def add_state_breakpoint(self, state_name: str) -> None:
        self.breakpoints['states'].add(state_name)

    def remove_state_breakpoint(self, state_name: str) -> None:
        self.breakpoints['states'].discard(state_name)

    def add_transition_breakpoint(self, source: str, target: str, event: str | None):
        self.breakpoints['transitions'].add((source, target, event))

    def remove_transition_breakpoint(self, source: str, target: str, event: str | None):
        self.breakpoints['transitions'].discard((source, target, event))

    def continue_simulation(self) -> bool:
        """Resumes the simulation if it is currently paused at a breakpoint."""
        if self.paused_on_breakpoint:
            self.paused_on_breakpoint = False
            return True
        return False