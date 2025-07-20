# fsm_designer_project/fsm_simulator.py
import logging
import re
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

class FSMError(Exception):
    """Custom exception for FSM simulation errors."""
    pass

def check_code_safety_basic(code_str: str, known_vars: set) -> tuple[bool, str]:
    """A basic security check for Python code snippets."""
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

class FSMSimulator:
    """Core, non-GUI FSM simulation engine with support for hierarchical states."""
    
    def __init__(self, states_data: List[Dict], transitions_data: List[Dict], halt_on_action_error: bool = False):
        self.states = {s['name']: s for s in states_data}
        self.transitions = transitions_data
        self._halt_on_error = halt_on_action_error
        self._variables = {}
        self.current_tick = 0
        self.paused_on_breakpoint = False
        self.simulation_halted_flag = False
        self.breakpoints = {'states': set()}
        self._action_log = []
        self.current_state_path: List[Dict] = []
        self._internal_event_queue: List[str] = []
        self.reset()

    def reset(self):
        self._action_log.clear()
        self._variables.clear()
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

    def _enter_state(self, state_data):
        self.current_state_path.append(state_data)
        self.log_action(f"Entering state: {self.get_current_state_name()}")
        self._execute_action(state_data.get('entry_action'))

        # --- START OF FIX for BUG-02 ---
        # Check for sub-machine completion
        if state_data.get('is_final') and len(self.current_state_path) > 1:
            parent_state = self.current_state_path[-2] # The superstate
            completion_flag = f"{parent_state['name']}_sub_completed"
            self._variables[completion_flag] = True
            self.log_action(f"Sub-machine in '{parent_state['name']}' reached final state. Set flag '{completion_flag}'.")
        # --- END OF FIX for BUG-02 ---

        if state_data.get('is_superstate'):
            sub_fsm_data = state_data.get('sub_fsm_data', {})
            sub_states = {s['name']: s for s in sub_fsm_data.get('states', [])}
            sub_initial = next((s for s_name, s in sub_states.items() if s.get('is_initial')), None)
            if not sub_initial and sub_states:
                sub_initial = next(iter(sub_states.values()))
            
            if sub_initial:
                self._enter_state(sub_initial)

    def _execute_action(self, code):
        if not code: return
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

    def send(self, event_name: str):
        """Allows action code to post an event for processing in the current step."""
        if event_name:
            self.log_action(f"Internal event '{event_name}' sent.")
            self._internal_event_queue.append(event_name)

    def step(self, event_name=None):
        if self.simulation_halted_flag or self.paused_on_breakpoint:
            return self.get_current_state_name(), self.get_last_executed_actions_log()

        self.current_tick += 1
        self._action_log.clear()
        self._internal_event_queue.clear()

        # 1. Execute 'during' action for the current state at the start of the tick.
        current_leaf_state = self.current_state_path[-1]
        self._execute_action(current_leaf_state.get('during_action'))
        
        # Also check for completion transitions from parent states
        for i in range(len(self.current_state_path) - 1):
            parent_state = self.current_state_path[i]
            if parent_state.get('is_superstate'):
                completion_flag = f"{parent_state['name']}_sub_completed"
                if self._variables.get(completion_flag) is True:
                    self._internal_event_queue.append(f"{parent_state['name']}_completed_event")


        # 2. Add the external event to the queue to be processed first.
        if event_name:
            self._internal_event_queue.append(event_name)
        
        # 3. Process all events in the queue until it's empty.
        transition_taken_this_step = False
        while self._internal_event_queue and not transition_taken_this_step:
            current_event = self._internal_event_queue.pop(0)
            
            # Check for transitions from the current leaf state up to the root
            for i in range(len(self.current_state_path) - 1, -1, -1):
                state_to_check = self.current_state_path[i]
                
                # Special handling for completion events
                is_completion_event = current_event == f"{state_to_check['name']}_completed_event"

                for trans in self.transitions:
                    # Match source state
                    if trans['source'] != state_to_check['name']:
                        continue

                    # Match event (or no event for completion transitions)
                    event_matches = (trans['event'] == current_event) or (is_completion_event and not trans['event'])
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
                        self.log_action(f"Transition on '{current_event}' from '{state_to_check['name']}' to '{trans['target']}'")

                        # Exit all states from leaf up to the source of the transition
                        for j in range(len(self.current_state_path) - 1, i - 1, -1):
                            exiting_state = self.current_state_path.pop()
                            self.log_action(f"Exiting state: {exiting_state['name']}")
                            self._execute_action(exiting_state.get('exit_action'))
                            # --- START OF FIX for BUG-02 ---
                            if exiting_state.get('is_superstate'):
                                completion_flag = f"{exiting_state['name']}_sub_completed"
                                if completion_flag in self._variables:
                                    del self._variables[completion_flag]
                                    self.log_action(f"Exited superstate '{exiting_state['name']}'. Cleared flag '{completion_flag}'.")
                            # --- END OF FIX for BUG-02 ---

                        self._execute_action(trans.get('action'))
                        
                        new_state_data = self.states.get(trans['target'])
                        if new_state_data:
                            self._enter_state(new_state_data)
                            
                            if self.current_state_path[-1]['name'] in self.breakpoints['states']:
                                self.paused_on_breakpoint = True
                                self.log_action(f"BREAKPOINT HIT at state {self.current_state_path[-1]['name']}")
                        else:
                            raise FSMError(f"Target state '{trans['target']}' not found")
                        
                        transition_taken_this_step = True
                        break # Exit the 'for trans' loop
                
                if transition_taken_this_step:
                    break # Exit the 'for state_to_check' loop

        return self.get_current_state_name(), self.get_last_executed_actions_log()

    def get_current_state_name(self):
        if not self.current_state_path: return "Halted"
        return " (".join(s['name'] for s in self.current_state_path) + ")" * (len(self.current_state_path) - 1)

    def get_current_leaf_state_name(self):
        return self.current_state_path[-1]['name'] if self.current_state_path else "Halted"

    def get_variables(self) -> Dict[str, Any]:
        return self._variables.copy()

    def log_action(self, msg: str):
        prefix = "[SUB] " * (len(self.current_state_path) - 1)
        self._action_log.append(f"{prefix}[Tick {self.current_tick}] {msg}")

    def get_last_executed_actions_log(self) -> List[str]:
        log = self._action_log[:]
        self._action_log.clear()
        return log

    def get_possible_events_from_current_state(self) -> List[str]:
        if not self.current_state_path: return []
        
        possible_events = set()
        for state in self.current_state_path:
            for t in self.transitions:
                if t['source'] == state['name'] and t.get('event'):
                    possible_events.add(t['event'])
        return sorted(list(possible_events))


    def add_state_breakpoint(self, state_name: str):
        self.breakpoints['states'].add(state_name)

    def remove_state_breakpoint(self, state_name: str):
        self.breakpoints['states'].discard(state_name)

    def continue_simulation(self) -> bool:
        if self.paused_on_breakpoint:
            self.paused_on_breakpoint = False
            return True
        return False