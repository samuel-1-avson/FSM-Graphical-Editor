# fsm_designer_project/fsm_simulator.py

print("fsm_simulator.py is being imported with python-statemachine integration, HIERARCHY AWARENESS, and Enhanced Security/Robustness!")

from statemachine import StateMachine, State
from statemachine.exceptions import TransitionNotAllowed, InvalidDefinition
from statemachine.event import Event as SMEvent


import logging
import ast # For AST-based safety checks

# Configure logging for this module
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid adding multiple handlers
    LOGGING_DATE_FORMAT = "%H:%M:%S"
    handler = logging.StreamHandler()
    formatter = logging.Formatter("--- FSM_SIM (%(asctime)s.%(msecs)03d): %(message)s", datefmt=LOGGING_DATE_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# --- START: Enhanced AST Safety Checker ---
class BasicSafetyVisitor(ast.NodeVisitor):
    def __init__(self, allowed_variable_names=None):
        super().__init__()
        self.violations = []
        self.allowed_call_names = {
            'print', 'len', 'abs', 'min', 'max', 'int', 'float', 'str', 'bool', 'round',
            'list', 'dict', 'set', 'tuple', 'range', 'sorted', 'sum', 'all', 'any',
            'isinstance', 'hasattr',
        }
        self.allowed_dunder_attrs = {
            '__len__', '__getitem__', '__setitem__', '__delitem__', '__contains__',
            '__add__', '__sub__', '__mul__', '__truediv__', '__floordiv__', '__mod__', '__pow__',
            '__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__',
            '__iter__', '__next__', '__call__',
            '__str__', '__repr__',
            '__bool__', '__hash__', '__abs__',
        }
        self.dangerous_attributes = {
            '__globals__', '__builtins__', '__code__', '__closure__', '__self__',
            '__class__', '__bases__', '__subclasses__', '__mro__',
            '__init__', '__new__', '__del__', '__dict__',
            '__getattribute__', '__setattr__', '__delattr__',
            '__get__', '__set__', '__delete__',
            '__init_subclass__', '__prepare__',
            'f_locals', 'f_globals', 'f_builtins', 'f_code', 'f_back', 'f_trace',
            'gi_frame', 'gi_code', 'gi_running', 'gi_yieldfrom',
            'co_code', 'co_consts', 'co_names', 'co_varnames', 'co_freevars', 'co_cellvars',
            'func_code', 'func_globals', 'func_builtins', 'func_closure', 'func_defaults',
            '__file__', '__cached__', '__loader__', '__package__', '__spec__',
            '_as_parameter_', '_fields_', '_length_', '_type_',
            '__annotations__', '__qualname__', '__module__',
            '__slots__', '__weakref__', '__set_name__',
            'format_map', 'mro', 'with_traceback',
        }
        self.truly_dangerous_attributes = self.dangerous_attributes - self.allowed_dunder_attrs
        self.allowed_variable_names = allowed_variable_names if allowed_variable_names else set()

    def visit_Import(self, node):
        self.violations.append("SecurityError: Imports (import) are not allowed in FSM code.")
        super().generic_visit(node)

    def visit_ImportFrom(self, node):
        self.violations.append("SecurityError: From-imports (from ... import) are not allowed in FSM code.")
        super().generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in ('eval', 'exec', 'compile', 'open', 'input',
                             'getattr', 'setattr', 'delattr',
                             'globals', 'locals', 'vars',
                             '__import__',
                             'memoryview', 'bytearray', 'bytes'
                             ):
                self.violations.append(f"SecurityError: Calling the function '{func_name}' is not allowed.")
            elif func_name not in self.allowed_call_names and \
                 func_name not in self.allowed_variable_names and \
                 func_name not in SAFE_BUILTINS: # Check against SAFE_BUILTINS too
                # Allow calls to user-defined functions if they are implicitly defined in the global scope
                # of the exec call (which they are, as script_globals can include them if defined in same string)
                # This pass assumes such functions are "safe" by virtue of being part of the same script context.
                # A more advanced checker might analyze these functions too.
                pass
        super().generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.attr, str):
            if node.attr in self.truly_dangerous_attributes:
                self.violations.append(f"SecurityError: Access to the attribute '{node.attr}' is restricted.")
            elif node.attr.startswith('__') and node.attr.endswith('__') and node.attr not in self.allowed_dunder_attrs:
                self.violations.append(f"SecurityError: Access to the special attribute '{node.attr}' is restricted.")
        super().generic_visit(node)

    def visit_Exec(self, node): # Python 2.x specific, unlikely to be used with ast.parse in Py3
        self.violations.append("SecurityError: The 'exec' statement/function is not allowed.")
        super().generic_visit(node)

def check_code_safety_basic(code_string: str, fsm_variables: set) -> tuple[bool, str]:
    if not code_string.strip():
        return True, ""
    try:
        tree = ast.parse(code_string, mode='exec')
        visitor = BasicSafetyVisitor(allowed_variable_names=fsm_variables)
        visitor.visit(tree)
        if visitor.violations:
            return False, "; ".join(visitor.violations)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError in user code: {e.msg} (line {e.lineno}, offset {e.offset})"
    except Exception as e:
        return False, f"Unexpected error during code safety check: {type(e).__name__} - {e}"

SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict, "float": float,
    "int": int, "len": len, "list": list, "max": max, "min": min, "print": print,
    "range": range, "round": round, "set": set, "str": str, "sum": sum, "tuple": tuple,
    "True": True, "False": False, "None": None,
    "isinstance": isinstance, "hasattr": hasattr,
    # Consider adding math functions if commonly used and safe, e.g., math.sin, math.cos
}
# --- END: Enhanced AST Safety Checker ---


class FSMError(Exception):
    pass

class StateMachinePoweredSimulator:
    def __init__(self, states_data, transitions_data, parent_simulator=None, log_prefix="", halt_on_action_error=False):
        self._states_input_data = {s['name']: s for s in states_data}
        self._transitions_input_data = transitions_data
        self._variables = {} 
        self._action_log = []
        self.FSMClass = None
        self.sm: StateMachine | None = None
        self._initial_state_name = None
        self.parent_simulator: StateMachinePoweredSimulator | None = parent_simulator
        self.log_prefix = log_prefix

        self.active_sub_simulator: StateMachinePoweredSimulator | None = None
        self.active_superstate_name: str | None = None
        self._halt_simulation_on_action_error = halt_on_action_error
        self.simulation_halted_flag = False
        
        self.current_tick = 0
        
        self.breakpoints = {"states": set(), "transitions": set()} 
        self.breakpoint_hit_flag = False 
        self.paused_on_breakpoint = False 

        try:
            self._build_fsm_class_and_instance()
            if self.sm and self.sm.current_state:
                self._log_action(f"FSM Initialized. Current state: {self.sm.current_state.id}")
            elif not self._states_input_data and not self.parent_simulator:
                 raise FSMError("No states defined in the FSM.")
            elif not self._states_input_data and self.parent_simulator:
                self._log_action("Sub-FSM initialized but has no states (inactive).")
            elif self.FSMClass and not self.sm and (self._states_input_data or self.parent_simulator):
                 raise FSMError("FSM Initialization failed: StateMachine (sm) instance is None after build. Check initial state definition.")

        except InvalidDefinition as e:
            logger.error(f"{self.log_prefix}FSM Definition Error during Initialization: {e}", exc_info=False)
            raise FSMError(f"FSM Definition Error: {e}")
        except FSMError:
            raise
        except Exception as e:
            logger.error(f"{self.log_prefix}Initialization failed: {e}", exc_info=True)
            raise FSMError(f"FSM Initialization failed: {e}")

    def _log_action(self, message, level_prefix_override=None):
        prefix_to_use = level_prefix_override if level_prefix_override is not None else self.log_prefix
        full_message = f"{prefix_to_use}[Tick {self.current_tick}] {message}"
        self._action_log.append(full_message)
        logger.info(full_message)

    def _create_dynamic_callback(self, code_string, callback_type="action", original_name="dynamic_callback"):
        current_fsm_variables = set(self._variables.keys())
        is_safe, safety_message = check_code_safety_basic(code_string, current_fsm_variables)
        
        if not is_safe:
            err_msg = f"SecurityError: Code execution blocked for '{original_name}'. Reason: {safety_message}"
            self._log_action(f"[Safety Check Failed] {err_msg}")
            if callback_type == "condition":
                def unsafe_condition_wrapper(*args, **kwargs):
                    self._log_action(f"[Condition Blocked by Safety Check] Unsafe code: '{code_string}' evaluated as False.")
                    return False
                unsafe_condition_wrapper.__name__ = f"{original_name}_blocked_condition_safety_{hash(code_string)}"
                return unsafe_condition_wrapper
            else: 
                def unsafe_action_wrapper(*args, **kwargs):
                    self._log_action(f"[Action Blocked by Safety Check] Unsafe code ignored: '{code_string}'.")
                unsafe_action_wrapper.__name__ = f"{original_name}_blocked_action_safety_{hash(code_string)}"
                return unsafe_action_wrapper

        simulator_self = self

        def dynamic_callback_wrapper(*args, **kwargs_from_sm_call):
            sm_instance_arg = kwargs_from_sm_call.get('machine')
            
            if not sm_instance_arg:
                simulator_self._log_action(f"[Callback Error] Could not determine StateMachine instance for '{original_name}'. Kwargs: {list(kwargs_from_sm_call.keys())}")
                if callback_type == "condition": return False
                return
            
            exec_globals = {"__builtins__": SAFE_BUILTINS.copy(), "sm": sm_instance_arg}
            
            exec_eval_locals_dict = simulator_self._variables.copy() 
            if "__builtins__" in exec_eval_locals_dict:
                del exec_eval_locals_dict["__builtins__"]
            exec_eval_locals_dict['current_tick'] = simulator_self.current_tick
            
            log_prefix_runtime = "[Action Runtime]" if callback_type == "action" else "[Condition Runtime]"
            current_state_for_log = sm_instance_arg.current_state.id if sm_instance_arg.current_state else "UnknownState"
            
            action_or_cond_id = original_name.split('_')[-1] if '_' in original_name else original_name
            simulator_self._log_action(f"{log_prefix_runtime} Executing: '{code_string}' in state '{current_state_for_log}' for '{action_or_cond_id}' with vars: {exec_eval_locals_dict}")

            try:
                if callback_type == "action":
                    exec(code_string, exec_globals, exec_eval_locals_dict) 
                    for key, value in exec_eval_locals_dict.items():
                        if key not in SAFE_BUILTINS and key != 'current_tick' and key != '__builtins__' and key != 'sm':
                            simulator_self._variables[key] = value
                    simulator_self._log_action(f"{log_prefix_runtime} Finished: '{code_string}'. Variables now: {simulator_self._variables}")
                    return None
                elif callback_type == "condition":
                    result = eval(code_string, exec_globals, exec_eval_locals_dict) 
                    simulator_self._log_action(f"{log_prefix_runtime} Result of '{code_string}': {result}")
                    return bool(result)
            except Exception as e: 
                err_type_name = type(e).__name__
                err_detail = str(e)
                if isinstance(e, SyntaxError): err_detail = f"{e.msg} (line {e.lineno}, offset {e.offset})"
                
                err_msg = (f"{err_type_name} in {callback_type} '{original_name}' (state context: {current_state_for_log}): "
                           f"{err_detail}. Code: '{code_string}'")
                simulator_self._log_action(f"[Code Error] {err_msg}")
                log_level = logging.ERROR if isinstance(e, (SyntaxError, TypeError, ZeroDivisionError, NameError)) else logging.WARNING
                logger.log(log_level, f"{simulator_self.log_prefix}{err_msg}", exc_info=True)
                
                if callback_type == "condition": return False
                if simulator_self._halt_simulation_on_action_error and callback_type == "action": 
                    simulator_self.simulation_halted_flag = True
                    raise FSMError(err_msg) 
            return None
        dynamic_callback_wrapper.__name__ = f"{original_name}_{callback_type}_{hash(code_string)}"
        return dynamic_callback_wrapper

    def _master_on_enter_state_impl(self, **kwargs):
        target: State = kwargs.get('target')
        sm_instance: StateMachine = kwargs.get('machine')
        
        if not target or not sm_instance: return 

        target_state_name = target.id
        self._log_action(f"Entering state: {target_state_name}")

        if target_state_name in self.breakpoints["states"]:
            self._log_action(f"BREAKPOINT HIT on entering state: {target_state_name}")
            self.breakpoint_hit_flag = True
            return 

        if target_state_name in self._states_input_data:
            state_def = self._states_input_data[target_state_name]
            if state_def.get('is_superstate', False):
                sub_fsm_data = state_def.get('sub_fsm_data')
                if sub_fsm_data and sub_fsm_data.get('states'):
                    self._log_action(f"Creating and activating sub-machine for superstate '{target_state_name}'")
                    try:
                        self.active_sub_simulator = StateMachinePoweredSimulator(
                            sub_fsm_data['states'], sub_fsm_data['transitions'],
                            parent_simulator=self, log_prefix=f"[SUB-{target_state_name}] ",
                            halt_on_action_error=self._halt_simulation_on_action_error
                        )
                        self.active_sub_simulator._variables = self._variables
                        self.active_superstate_name = target_state_name
                    except Exception as e_sub:
                        self._log_action(f"[Sub-FSM Error] Failed to initialize sub-machine for '{target_state_name}': {e_sub}")
                        self.active_sub_simulator = self.active_superstate_name = None
                        if self._halt_simulation_on_action_error:
                            self.simulation_halted_flag = True
                            raise FSMError(f"Sub-FSM init error for '{target_state_name}': {e_sub}")
                else:
                     self._log_action(f"Superstate '{target_state_name}' has no sub-machine data or states defined.")

    def _master_on_exit_state_impl(self, **kwargs):
        source: State = kwargs.get('source')
        if not source: return

        source_state_name = source.id
        self._log_action(f"Exiting state: {source_state_name}")
        if self.active_sub_simulator and self.active_superstate_name == source_state_name:
            self._log_action(f"Destroying active sub-machine from superstate '{source_state_name}'.")
            self.active_sub_simulator = None 
            self.active_superstate_name = None

    def _sm_before_transition_impl(self, **kwargs):
        event_data_obj = kwargs.get('event_data')
        source: State = kwargs.get('source')
        target: State = kwargs.get('target')
        event: str = kwargs.get('event')

        if not all([source, target, event_data_obj, event]): return
        triggered_event_name = event_data_obj.event
        self._log_action(f"Before transition on '{triggered_event_name}' from '{source.id}' to '{target.id}'")

    def _sm_after_transition_impl(self, **kwargs):
        event_data_obj = kwargs.get('event_data')
        source: State = kwargs.get('source')
        target: State = kwargs.get('target')
        event: str = kwargs.get('event')
        
        if not all([source, target, event_data_obj, event]): return
        triggered_event_name = event_data_obj.event
        self._log_action(f"After transition on '{triggered_event_name}' from '{source.id}' to '{target.id}'")

    def _build_fsm_class_and_instance(self):
        if not self._states_input_data: