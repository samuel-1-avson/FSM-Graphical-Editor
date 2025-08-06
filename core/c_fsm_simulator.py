# fsm_designer_project/core/c_fsm_simulator.py

import ctypes
import os
import sys
import json
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class CSimError(Exception):
    pass

class CFsmSimulator:
    """A Python wrapper for the compiled C++ FSM core engine."""

    def __init__(self, library_path: str):
        self.lib = self._load_library(library_path)
        self._define_c_api()
        
        self.handle = self.lib.create_fsm()
        if not self.handle:
            raise CSimError("Failed to create FSM handle in C++ core.")
            
        # Python-side state
        self._variables: Dict[str, any] = {}
        self.current_tick = 0
        self.current_state_name = "Uninitialized"

    def __del__(self):
        if hasattr(self, 'lib') and self.lib and hasattr(self, 'handle') and self.handle:
            self.lib.destroy_fsm(self.handle)

    def _load_library(self, library_path: str):
        """Loads the shared library."""
        if not os.path.exists(library_path):
            raise FileNotFoundError(f"C++ FSM library not found at: {library_path}. Please compile the core_engine.")
        try:
            return ctypes.CDLL(library_path)
        except OSError as e:
            raise CSimError(f"Failed to load C++ FSM library: {e}")

    def _define_c_api(self):
        """Define the argument and return types for the C functions."""
        # Lifecycle
        self.lib.create_fsm.restype = ctypes.c_void_p
        self.lib.destroy_fsm.argtypes = [ctypes.c_void_p]

        # Configuration
        self.lib.load_fsm_from_json.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.load_fsm_from_json.restype = ctypes.c_bool
        self.lib.set_initial_variables_from_json.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.reset_fsm.argtypes = [ctypes.c_void_p]

        # Simulation
        self.lib.step.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.resolve_condition.argtypes = [ctypes.c_void_p, ctypes.c_bool]
        self.lib.queue_internal_event.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        
        # Data Retrieval
        self.lib.get_current_state_name.argtypes = [ctypes.c_void_p]
        self.lib.get_current_state_name.restype = ctypes.c_char_p
        self.lib.get_variables_json.argtypes = [ctypes.c_void_p]
        self.lib.get_variables_json.restype = ctypes.c_char_p
        self.lib.get_and_clear_log_json.argtypes = [ctypes.c_void_p]
        self.lib.get_and_clear_log_json.restype = ctypes.c_char_p
        self.lib.get_current_tick.argtypes = [ctypes.c_void_p]
        self.lib.get_current_tick.restype = ctypes.c_int

        # Memory Management
        self.lib.free_string_memory.argtypes = [ctypes.c_char_p]

    def _call_c_func_with_string_return(self, func, *args):
        """Helper to call a C function that returns a string and manage memory."""
        c_ptr = func(*args)
        if not c_ptr:
            return ""
        py_str = c_ptr.decode('utf-8')
        self.lib.free_string_memory(c_ptr)
        return py_str

    def load_fsm(self, diagram_data: Dict):
        """Loads the FSM structure into the C++ engine."""
        json_str = json.dumps(diagram_data)
        success = self.lib.load_fsm_from_json(self.handle, json_str.encode('utf-8'))
        if not success:
            raise CSimError("Failed to load FSM data into C++ core.")
        self.reset()

    def set_initial_variables(self, initial_vars: Dict):
        """Sets the initial variables for the simulation."""
        self._variables = initial_vars.copy()
        json_str = json.dumps(self._variables)
        self.lib.set_initial_variables_from_json(self.handle, json_str.encode('utf-8'))

    def reset(self):
        """Resets the C++ FSM to its initial state."""
        self.lib.reset_fsm(self.handle)
        self._sync_state_from_c()
        
    def _sync_state_from_c(self):
        """Updates Python-side state from the C++ core."""
        self.current_tick = self.lib.get_current_tick(self.handle)
        self.current_state_name = self._call_c_func_with_string_return(self.lib.get_current_state_name, self.handle)

    def send(self, event_name: str):
        """Allows action code to post an event for processing in the current step."""
        if event_name:
            event_bytes = event_name.encode('utf-8')
            self.lib.queue_internal_event(self.handle, event_bytes)

    def step(self, event_name: Optional[str]) -> Tuple[str, List[str]]:
        """Executes one step of the simulation, handling condition callbacks."""
        full_python_log = []
        
        # 1. Tell C++ engine to perform a logic step
        event_bytes = event_name.encode('utf-8') if event_name else None
        self.lib.step(self.handle, event_bytes)

        # 2. Process action logs in a loop until C++ core has no more immediate actions
        while True:
            log_json_str = self._call_c_func_with_string_return(self.lib.get_and_clear_log_json, self.handle)
            if not log_json_str or log_json_str == "[]":
                break # No more actions from C++, step is complete

            action_log_c = json.loads(log_json_str)

            # 3. Process the action log in Python
            for entry_str in action_log_c:
                entry = json.loads(entry_str)
                action_type = entry['type']
                code = entry['data']

                if action_type == "AWAIT_CONDITION":
                    try:
                        result = bool(eval(code, {"sm": self}, self._variables))
                        full_python_log.append(f"[PY] Condition '{code}' -> {result}")
                        # Tell C++ core the result so it can proceed or stop
                        self.lib.resolve_condition(self.handle, result)
                    except Exception as e:
                        full_python_log.append(f"[PY ERROR] in condition '{code}': {e}")
                        # Tell C++ core the condition failed due to an error
                        self.lib.resolve_condition(self.handle, False)
                
                elif action_type in ["ENTRY_STATE", "EXIT_STATE", "TRANSITION_ACTION", "DURING_ACTION"]:
                    full_python_log.append(f"[PY] Executing: {code}")
                    try:
                        exec(code, {"sm": self, "current_tick": self.current_tick}, self._variables)
                    except Exception as e:
                        full_python_log.append(f"[PY ERROR] in action '{code}': {e}")

                elif action_type == "INFO":
                     full_python_log.append(f"[C CORE] {code}")

        # 4. Final state synchronization after all actions are processed
        self._sync_state_from_c()
        return self.current_state_name, full_python_log