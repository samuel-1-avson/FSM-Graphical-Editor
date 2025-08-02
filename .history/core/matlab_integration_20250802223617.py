# fsm_designer_project/core/matlab_integration.py

import sys
import os
import io
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMetaObject, Q_ARG, pyqtSlot, Qt, QTimer

try:
    import matlab.engine
    MATLAB_ENGINE_AVAILABLE = True
except ImportError:
    matlab = None
    MATLAB_ENGINE_AVAILABLE = False

logger = logging.getLogger(__name__)

class EngineState(Enum):
    """MATLAB Engine connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"

class CommandType(Enum):
    """Types of MATLAB commands"""
    SIMULATION = "simulation"
    CODE_GENERATION = "code_generation"
    MODEL_GENERATION = "model_generation"
    GENERAL = "general"

@dataclass
class MatlabCommand:
    """Represents a MATLAB command with metadata"""
    command: str
    command_type: CommandType
    timeout: float = 30.0
    callback_signal: Optional[pyqtSignal] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SimulationConfig:
    """Configuration for Simulink simulations"""
    stop_time: float = 10.0
    solver: str = 'ode45'
    fixed_step_size: Optional[float] = None
    save_output: bool = True
    output_variables: List[str] = None
    
    def __post_init__(self):
        if self.output_variables is None:
            self.output_variables = ['active_state_name']

@dataclass
class CodeGenConfig:
    """Configuration for code generation"""
    language: str = "C++"
    target_file: str = "ert.tlc"
    optimization_level: str = "O2"
    generate_makefile: bool = True
    include_comments: bool = True
    custom_defines: Dict[str, str] = None
    
    def __post_init__(self):
        if self.custom_defines is None:
            self.custom_defines = {}

class MatlabEngineWorker(QObject):
    """
    Enhanced worker that runs in a separate thread to handle all blocking MATLAB Engine calls.
    Provides robust error handling, connection management, and command queuing.
    """
    engine_status_changed = pyqtSignal(EngineState, str)  # state, message
    command_finished = pyqtSignal(bool, str, str, CommandType)  # success, message, data_output, type
    progress_updated = pyqtSignal(str, int)  # operation, percentage
    
    def __init__(self):
        super().__init__()
        self.engine = None
        self.state = EngineState.DISCONNECTED
        self._is_shutting_down = False
        self._command_queue = []
        self._current_command = None
        self._engine_info = {}
        
        # Health monitoring
        self._last_heartbeat = time.time()

    @pyqtSlot()
    def start_engine(self):
        """Start MATLAB Engine with enhanced error handling and validation"""
        if self.state == EngineState.CONNECTED:
            self.engine_status_changed.emit(EngineState.CONNECTED, "Engine already running.")
            return

        if not MATLAB_ENGINE_AVAILABLE:
            msg = ("MATLAB Engine for Python not found. Please install it from your MATLAB installation directory.\n"
                   "Typical installation: cd \"matlabroot\\extern\\engines\\python\" && python setup.py install")
            self._set_state(EngineState.ERROR, msg)
            return

        self._set_state(EngineState.CONNECTING, "Starting MATLAB Engine...")
        
        try:
            logger.info("Starting MATLAB Engine with enhanced configuration...")
            
            # Start engine in headless mode for background processing
            self.engine = matlab.engine.start_matlab('-nodesktop -nosplash')
            
            # Validate engine and gather information
            self._validate_and_configure_engine()
            
            # Create and start health monitoring timer within the worker thread
            self._heartbeat_timer = QTimer()
            self._heartbeat_timer.timeout.connect(self._check_engine_health)
            self._heartbeat_timer.setInterval(5000)  # 5 seconds
            self._heartbeat_timer.start()
            
            self._last_heartbeat = time.time()
            
            self._set_state(EngineState.CONNECTED, 
                          f"MATLAB Engine connected successfully. Version: {self._engine_info.get('version', 'Unknown')}")
            
        except Exception as e:
            msg = f"Failed to start MATLAB Engine: {e}"
            logger.error(msg, exc_info=True)
            self._cleanup_engine()
            self._set_state(EngineState.ERROR, msg)

    def _validate_and_configure_engine(self):
        """Validate engine connection and configure MATLAB environment"""
        # Get MATLAB version and configuration
        version_cmd = "version('-release')"
        matlab_version = self.engine.eval(version_cmd)
        
        # Get PID for monitoring
        pid_cmd = ("name_parts = string(java.lang.management.ManagementFactory.getRuntimeMXBean().getName()).split('@'); "
                   "pid = name_parts{1};")
        self.engine.eval(pid_cmd, nargout=0)
        pid = self.engine.workspace['pid']
        
        # Check required toolboxes
        required_toolboxes = ['Simulink', 'Stateflow']
        available_toolboxes = []
        
        for toolbox in required_toolboxes:
            try:
                result = self.engine.eval(f"license('test', '{toolbox}')")
                if result:
                    available_toolboxes.append(toolbox)
            except:
                pass
        
        # Store engine information
        self._engine_info = {
            'version': matlab_version,
            'pid': pid,
            'available_toolboxes': available_toolboxes,
            'required_toolboxes': required_toolboxes
        }
        
        # Configure MATLAB environment
        self.engine.eval("addpath(genpath('.')); % Add current directory recursively", nargout=0)
        self.engine.eval("warning('off', 'all'); % Suppress warnings for cleaner output", nargout=0)
        
        logger.info(f"MATLAB Engine validated. Version: {matlab_version}, PID: {pid}")
        logger.info(f"Available toolboxes: {available_toolboxes}")

    def _check_engine_health(self):
        """Monitor engine health and attempt recovery if needed"""
        if self.state != EngineState.CONNECTED or not self.engine:
            return
            
        try:
            # Simple heartbeat command
            self.engine.eval("1+1", nargout=0)
            self._last_heartbeat = time.time()
        except Exception as e:
            logger.warning(f"Engine health check failed: {e}")
            if time.time() - self._last_heartbeat > 30:  # 30 seconds without response
                self._handle_engine_failure("Engine health check timeout")

    def _handle_engine_failure(self, reason: str):
        """Handle engine failure and attempt recovery"""
        logger.error(f"Engine failure detected: {reason}")
        self._cleanup_engine()
        self._set_state(EngineState.ERROR, f"Engine failed: {reason}")
        
        # Attempt automatic recovery
        QTimer.singleShot(5000, self.start_engine)  # Retry after 5 seconds

    @pyqtSlot(MatlabCommand)
    def execute_command(self, command: MatlabCommand):
        """Execute a MATLAB command with enhanced error handling and timeout"""
        if self.state != EngineState.CONNECTED:
            msg = f"Cannot execute command: Engine state is {self.state.value}"
            self._emit_command_result(False, msg, "", command.command_type)
            return

        self._current_command = command
        
        try:
            logger.debug(f"Executing {command.command_type.value} command (timeout: {command.timeout}s)")
            
            # Set up output capture
            from io import StringIO
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            
            # Execute with timeout
            start_time = time.time()
            self.engine.eval(command.command, nargout=0, 
                           stdout=stdout_capture, stderr=stderr_capture,
                           background=False)
            
            execution_time = time.time() - start_time
            stdout = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()

            logger.debug(f"Command executed in {execution_time:.2f}s")
            logger.debug(f"MATLAB STDOUT:\n{stdout}")
            if stderr:
                logger.warning(f"MATLAB STDERR:\n{stderr}")

            # Parse results based on output markers
            success, message, data = self._parse_command_output(stdout, stderr, command.command_type)
            self._emit_command_result(success, message, data, command.command_type)

        except matlab.engine.MatlabExecutionError as e:
            logger.error(f"MATLAB execution error: {e}", exc_info=True)
            self._emit_command_result(False, f"MATLAB Execution Error: {e}", "", command.command_type)
        except Exception as e:
            logger.error(f"Unexpected error executing command: {e}", exc_info=True)
            self._emit_command_result(False, f"Unexpected Error: {e}", "", command.command_type)
        finally:
            self._current_command = None

    def _parse_command_output(self, stdout: str, stderr: str, command_type: CommandType) -> Tuple[bool, str, str]:
        """Parse MATLAB command output for success/failure indicators"""
        if "MATLAB_SCRIPT_SUCCESS:" in stdout:
            output_data = ""
            for line in stdout.splitlines():
                if line.startswith("MATLAB_SCRIPT_SUCCESS:"):
                    output_data = line.split(":", 1)[1].strip()
                    break
            return True, "Operation completed successfully.", output_data
        
        elif "MATLAB_SCRIPT_FAILURE:" in stdout or stderr:
            error_detail = stderr
            if not error_detail:
                for line in stdout.splitlines():
                    if line.strip().startswith("MATLAB_SCRIPT_FAILURE:"):
                        error_detail = line.split(":", 1)[1].strip()
                        break
            return False, f"MATLAB operation failed: {error_detail}", ""
        
        else:
            # No explicit markers, assume success if no stderr
            if stderr:
                return False, f"Command completed with warnings: {stderr}", stdout
            return True, "Command executed successfully.", stdout

    def _emit_command_result(self, success: bool, message: str, data: str, command_type: CommandType):
        """Emit command result signal"""
        self.command_finished.emit(success, message, data, command_type)

    def _set_state(self, new_state: EngineState, message: str):
        """Update engine state and emit signal"""
        self.state = new_state
        self.engine_status_changed.emit(new_state, message)

    def _cleanup_engine(self):
        """Clean up engine resources"""
        if hasattr(self, '_heartbeat_timer') and self._heartbeat_timer.isActive():
            self._heartbeat_timer.stop()
            
        if self.engine:
            try:
                self.engine.quit()
            except:
                pass
            self.engine = None

    @pyqtSlot()
    def shutdown_engine(self):
        """Shutdown engine gracefully"""
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        self._set_state(EngineState.SHUTTING_DOWN, "Shutting down engine...")
        
        logger.info("Shutting down MATLAB Engine...")
        self._cleanup_engine()
        self._set_state(EngineState.DISCONNECTED, "Engine shut down successfully.")


class MatlabConnection(QObject):
    """Enhanced MATLAB connection manager with improved reliability and features"""
    connectionStatusChanged = pyqtSignal(EngineState, str)
    simulationFinished = pyqtSignal(bool, str, str)
    codeGenerationFinished = pyqtSignal(bool, str, str)
    modelGenerationFinished = pyqtSignal(bool, str, str)
    progressUpdated = pyqtSignal(str, int)

    def __init__(self):
        super().__init__()
        self.state = EngineState.DISCONNECTED
        self.thread: Optional[QThread] = None
        self.worker: Optional[MatlabEngineWorker] = None

    def connect(self):
        """Initialize worker thread and connections on-demand."""
        if self.state != EngineState.DISCONNECTED:
            logger.info("MATLAB connection process already started or complete.")
            return

        self.state = EngineState.CONNECTING
        self.connectionStatusChanged.emit(EngineState.CONNECTING, "Initializing...")

        self.thread = QThread()
        self.thread.setObjectName("MatlabEngineThread")
        self.worker = MatlabEngineWorker()
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.worker.engine_status_changed.connect(self._on_engine_status_changed)
        self.worker.command_finished.connect(self._on_command_finished)
        self.worker.progress_updated.connect(self.progressUpdated)
        
        # Start thread and engine
        self.thread.start()
        QMetaObject.invokeMethod(self.worker, "start_engine", Qt.QueuedConnection)

    @pyqtSlot(EngineState, str)
    def _on_engine_status_changed(self, state: EngineState, message: str):
        """Handle engine status changes"""
        self.state = state
        self.connectionStatusChanged.emit(state, message)

    @pyqtSlot(bool, str, str, CommandType)
    def _on_command_finished(self, success: bool, message: str, data: str, command_type: CommandType):
        """Route command results to appropriate signals"""
        if command_type == CommandType.SIMULATION:
            self.simulationFinished.emit(success, message, data)
        elif command_type == CommandType.CODE_GENERATION:
            self.codeGenerationFinished.emit(success, message, data)
        elif command_type == CommandType.MODEL_GENERATION:
            self.modelGenerationFinished.emit(success, message, data)

    def is_connected(self) -> bool:
        """Check if engine is connected"""
        return self.state == EngineState.CONNECTED

    def _execute_command(self, command: MatlabCommand):
        """Execute a command on the worker thread"""
        if not self.is_connected() or not self.worker:
            self._on_command_finished(False, "MATLAB Engine not connected.", "", command.command_type)
            return
        
        QMetaObject.invokeMethod(self.worker, "execute_command", Qt.QueuedConnection,
                               Q_ARG(MatlabCommand, command))

    def ensure_connection_and_execute(self, command: MatlabCommand):
        """
        Ensures the MATLAB engine is running, then executes a command.
        This is the new primary way to interact with MATLAB.
        """
        if self.is_connected():
            self._execute_command(command)
        else:
            # --- FIX: CORRECTED CONSTANT NAME ---
            self.connectionStatusChanged.connect(
                lambda state, msg: self._execute_command(command) if state == EngineState.CONNECTED else None,
                Qt.SingleShotConnection
            )
            # --- END FIX ---
            self.connect()

    def generate_simulink_model(self, states: List[Dict], transitions: List[Dict], 
                              output_dir: str, model_name: str = "BrainStateMachine") -> bool:
        """Generate Simulink model with enhanced Stateflow chart creation"""
        if not states:
            self.modelGenerationFinished.emit(False, "No states provided for model generation.", "")
            return False

        slx_file_path = Path(output_dir) / f"{model_name}.slx"
        
        script_content = self._create_model_generation_script(states, transitions, str(slx_file_path), model_name)
        
        command = MatlabCommand(
            command=script_content,
            command_type=CommandType.MODEL_GENERATION,
            timeout=60.0,
            metadata={'model_name': model_name, 'output_path': str(slx_file_path)}
        )
        
        self.ensure_connection_and_execute(command)
        return True

    def _create_model_generation_script(self, states: List[Dict], transitions: List[Dict], 
                                      output_path: str, model_name: str) -> str:
        """Create enhanced MATLAB script for model generation"""
        slx_file_path = output_path.replace(os.sep, '/')
        
        script_lines = [
            f"modelNameVar = '{model_name}';",
            f"outputModelPath = '{slx_file_path}';",
            "",
            "try",
            "    if ~license('test', 'Simulink') || ~license('test', 'Stateflow')",
            "        error('Simulink or Stateflow license not available');",
            "    end",
            "    load_system('sflib'); load_system('simulink');",
            "    if bdIsLoaded(modelNameVar), close_system(modelNameVar, 0); end",
            "    if exist(outputModelPath, 'file'), delete(outputModelPath); end",
            "    hModel = new_system(modelNameVar, 'Model'); open_system(hModel);",
            "    set_param(modelNameVar, 'SolverType', 'Fixed-step', 'FixedStep', '0.1', 'StopTime', '10');",
            "    chartPath = [modelNameVar, '/', 'FSM_Chart'];",
            "    add_block('stateflow/Chart', chartPath, 'Position', [100 50 400 350]);",
            "    machine = sfroot().find('-isa', 'Stateflow.Machine', 'Name', modelNameVar);",
            "    chart = machine.find('-isa', 'Stateflow.Chart');",
            "    chart.Name = 'FiniteStateMachineLogic';",
            "    outputData = Stateflow.Data(chart);",
            "    outputData.Name = 'active_state_name'; outputData.Scope = 'Output'; outputData.DataType = 'string';",
            "    add_block('simulink/Sinks/To Workspace', [modelNameVar '/State_Out'], 'VariableName', 'active_state_name', 'SaveFormat', 'Array');",
            "    add_line(modelNameVar, 'FSM_Chart/1', 'State_Out/1', 'autorouting', 'on');",
            "    stateHandles = containers.Map('KeyType','char','ValueType','any');"
        ]

        script_lines.extend(self._generate_state_creation_code(states))
        script_lines.extend(self._generate_transition_creation_code(transitions))

        script_lines.extend([
            "    save_system(modelNameVar, outputModelPath, 'OverwriteIfChangedOnDisk', true);",
            "    close_system(modelNameVar, 0);",
            "    fprintf('MATLAB_SCRIPT_SUCCESS:%s\\n', outputModelPath);",
            "catch e",
            "    fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', strrep(getReport(e, 'extended'), '\\n', ' '));",
            "    if bdIsLoaded(modelNameVar), close_system(modelNameVar, 0); end",
            "end"
        ])

        return "\n".join(script_lines)

    def _generate_state_creation_code(self, states: List[Dict]) -> List[str]:
        script_lines = []
        for i, state in enumerate(states):
            state_name = state['name'].replace("'", "''")
            state_id = f"state_{i}_{state['name'].replace(' ', '_').replace('-', '_')}"
            state_id = ''.join(c for c in state_id if c.isalnum() or c == '_')
            if not state_id or not state_id[0].isalpha(): state_id = 's_' + state_id
            
            sf_x = state.get('x', 20 + i*150) / 2.5 + 20
            sf_y = state.get('y', 20) / 2.5 + 20
            sf_w = max(80, state.get('width', 120) / 2.5)
            sf_h = max(50, state.get('height', 60) / 2.5)
            
            label_parts = [f'entry: active_state_name = "{state_name}";']
            for action_key, action_prefix in [('entry_action', 'entry'), ('during_action', 'during'), ('exit_action', 'exit')]:
                action_code = state.get(action_key)
                if action_code:
                    label_parts.append(f"{action_prefix}: {action_code.replace("'", "''").replace(chr(10), '; ')}")
            state_label = "\\n".join(label_parts)
            
            script_lines.extend([
                f"    {state_id} = Stateflow.State(chart);",
                f"    {state_id}.Name = '{state_name}';",
                f"    {state_id}.Position = [{sf_x}, {sf_y}, {sf_w}, {sf_h}];",
                f"    {state_id}.LabelString = '{state_label}';",
                f"    stateHandles('{state_name}') = {state_id};"
            ])
            
            if state.get('is_initial', False):
                script_lines.append(f"    defaultTrans_{i} = Stateflow.Transition(chart); defaultTrans_{i}.Destination = {state_id};")
        return script_lines

    def _generate_transition_creation_code(self, transitions: List[Dict]) -> List[str]:
        script_lines = []
        for i, trans in enumerate(transitions):
            src_name = trans['source'].replace("'", "''")
            dst_name = trans['target'].replace("'", "''")
            
            label_parts = []
            if trans.get('event'): label_parts.append(trans['event'])
            if trans.get('condition'): label_parts.append(f"[{trans['condition']}]")
            if trans.get('action'): label_parts.append(f"/{{{trans['action']}}}")
            trans_label = " ".join(label_parts).strip().replace("'", "''")
            
            script_lines.extend([
                f"    if isKey(stateHandles, '{src_name}') && isKey(stateHandles, '{dst_name}')",
                f"        srcState = stateHandles('{src_name}'); dstState = stateHandles('{dst_name}');",
                f"        trans_{i} = Stateflow.Transition(chart);",
                f"        trans_{i}.Source = srcState; trans_{i}.Destination = dstState;",
                f"        trans_{i}.LabelString = '{trans_label}';" if trans_label else "",
                "    else",
                f"        warning('States not found for transition {i}: {src_name} -> {dst_name}');",
                "    end"
            ])
        return script_lines

    def run_simulation(self, model_path: str, config: SimulationConfig = None) -> bool:
        if not Path(model_path).exists():
            self.simulationFinished.emit(False, f"Model file not found: {model_path}", "")
            return False
        if config is None: config = SimulationConfig()

        model_path_matlab = str(Path(model_path)).replace(os.sep, '/')
        model_name = Path(model_path).stem
        
        script_content = f"""
try
    load_system('{model_path_matlab}');
    set_param('{model_name}', 'StopTime', '{config.stop_time}', 'Solver', '{config.solver}', 'SaveOutput', 'on');
    fprintf('Starting simulation of model: {model_name}\\n');
    simOut = sim('{model_name}');
    fprintf('MATLAB_SCRIPT_SUCCESS:Simulation completed successfully\\n');
catch e
    fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', strrep(getReport(e, 'basic'),'\\n',' '));
end
if bdIsLoaded('{model_name}'), close_system('{model_name}', 0); end
"""

        command = MatlabCommand(
            command=script_content,
            command_type=CommandType.SIMULATION,
            timeout=config.stop_time + 30.0,
            metadata={'model_path': model_path, 'config': config}
        )
        
        self.ensure_connection_and_execute(command)
        return True

    def generate_code(self, model_path: str, config: CodeGenConfig = None, 
                     output_dir: Optional[str] = None) -> bool:
        if not Path(model_path).exists():
            self.codeGenerationFinished.emit(False, f"Model file not found: {model_path}", "")
            return False
        if config is None: config = CodeGenConfig()
        if output_dir is None: output_dir = str(Path(model_path).parent)

        model_path_matlab = str(Path(model_path)).replace(os.sep, '/')
        output_dir_matlab = str(Path(output_dir)).replace(os.sep, '/')
        model_name = Path(model_path).stem

        script_content = f"""
try
    if ~license('test', 'MATLAB_Coder') || ~license('test', 'Simulink_Coder')
        error('Required coder license not available.');
    end
    load_system('{model_path_matlab}');
    set_param('{model_name}', 'SystemTargetFile', '{config.target_file}');
    cfg = getActiveConfigSet('{model_name}');
    set_param(cfg, 'TargetLang', '{config.language}', 'OptimizationLevel', '{config.optimization_level}');
    set_param(cfg, 'GenerateComments', '{"on" if config.include_comments else "off"}');
    set_param(cfg, 'GenerateMakefile', '{"on" if config.generate_makefile else "off"}');
    {self._generate_custom_defines_code(config.custom_defines)}
    if ~exist('{output_dir_matlab}', 'dir'), mkdir('{output_dir_matlab}'); end
    fprintf('Starting code generation for model: {model_name}\\n');
    rtwbuild('{model_name}', 'CodeGenFolder', '{output_dir_matlab}', 'GenCodeOnly', true);
    actualCodeDir = fullfile('{output_dir_matlab}', '{model_name}_ert_rtw');
    if ~exist(actualCodeDir, 'dir'), actualCodeDir = '{output_dir_matlab}'; end
    fprintf('MATLAB_SCRIPT_SUCCESS:%s\\n', actualCodeDir);
catch e
    fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', strrep(getReport(e, 'basic'),'\\n',' '));
end
if bdIsLoaded('{model_name}'), close_system('{model_name}', 0); end
"""

        command = MatlabCommand(
            command=script_content,
            command_type=CommandType.CODE_GENERATION,
            timeout=120.0,
            metadata={'model_path': model_path, 'config': config, 'output_dir': output_dir}
        )
        
        self.ensure_connection_and_execute(command)
        return True

    def _generate_custom_defines_code(self, custom_defines: Dict[str, str]) -> str:
        if not custom_defines: return ""
        lines = [f"    set_param(cfg, 'CustomDefine', [get_param(cfg, 'CustomDefine'), ' -D{name}={value}']);"
                 for name, value in custom_defines.items()]
        return "\n".join(lines)

    def execute_custom_command(self, command: str, timeout: float = 30.0) -> bool:
        matlab_command = MatlabCommand(command=command, command_type=CommandType.GENERAL, timeout=timeout)
        self.ensure_connection_and_execute(matlab_command)
        return True

    def get_engine_info(self) -> Dict[str, Any]:
        if self.worker and hasattr(self.worker, '_engine_info'):
            return self.worker._engine_info.copy()
        return {}

    def shutdown(self):
        if self.thread and self.thread.isRunning():
            QMetaObject.invokeMethod(self.worker, "shutdown_engine", Qt.QueuedConnection)
            self.thread.quit()
            if not self.thread.wait(5000):
                logger.warning("MATLAB Engine thread did not quit gracefully. Terminating.")
                self.thread.terminate()
                self.thread.wait(2000)


class MatlabModelValidator:
    """Utility class for validating Simulink models and FSM definitions"""
    
    @staticmethod
    def validate_states(states: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate state definitions"""
        errors = []
        
        if not states:
            errors.append("No states defined")
            return False, errors
        
        # Check for required fields
        state_names = set()
        initial_states = 0
        
        for i, state in enumerate(states):
            # Check required fields
            if 'name' not in state or not state['name']:
                errors.append(f"State {i}: Missing or empty name")
                continue
            
            # Check for duplicate names
            name = state['name']
            if name in state_names:
                errors.append(f"Duplicate state name: {name}")
            state_names.add(name)
            
            # Check initial state count
            if state.get('is_initial', False):
                initial_states += 1
            
            # Validate coordinates
            if 'x' in state and not isinstance(state['x'], (int, float)):
                errors.append(f"State {name}: Invalid x coordinate")
            if 'y' in state and not isinstance(state['y'], (int, float)):
                errors.append(f"State {name}: Invalid y coordinate")
        
        # Check initial state count
        if initial_states == 0:
            errors.append("No initial state defined")
        elif initial_states > 1:
            errors.append(f"Multiple initial states defined ({initial_states})")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_transitions(transitions: List[Dict], states: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate transition definitions"""
        errors = []
        
        if not states:
            errors.append("Cannot validate transitions: No states defined")
            return False, errors
        
        state_names = {state['name'] for state in states}
        
        for i, trans in enumerate(transitions):
            # Check required fields
            if 'source' not in trans or not trans['source']:
                errors.append(f"Transition {i}: Missing or empty source state")
                continue
            if 'target' not in trans or not trans['target']:
                errors.append(f"Transition {i}: Missing or empty target state")
                continue
            
            # Check state references
            source = trans['source']
            target = trans['target']
            
            if source not in state_names:
                errors.append(f"Transition {i}: Source state '{source}' not found")
            if target not in state_names:
                errors.append(f"Transition {i}: Target state '{target}' not found")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_model_name(model_name: str) -> Tuple[bool, List[str]]:
        """Validate Simulink model name"""
        errors = []
        
        if not model_name:
            errors.append("Model name cannot be empty")
            return False, errors
        
        # Check MATLAB identifier rules
        if not model_name[0].isalpha():
            errors.append("Model name must start with a letter")
        
        if not all(c.isalnum() or c == '_' for c in model_name):
            errors.append("Model name can only contain letters, numbers, and underscores")
        
        if len(model_name) > 63:
            errors.append("Model name cannot exceed 63 characters")
        
        # Check for reserved MATLAB keywords
        matlab_keywords = {
            'break', 'case', 'catch', 'continue', 'else', 'elseif', 'end',
            'for', 'function', 'global', 'if', 'otherwise', 'persistent',
            'return', 'switch', 'try', 'while', 'sin', 'cos', 'tan', 'pi'
        }
        
        if model_name.lower() in matlab_keywords:
            errors.append(f"Model name '{model_name}' is a reserved MATLAB keyword")
        
        return len(errors) == 0, errors


class MatlabDiagnostics:
    """Utility class for MATLAB diagnostics and troubleshooting"""
    
    @staticmethod
    def check_matlab_installation() -> Dict[str, Any]:
        """Check MATLAB installation and dependencies"""
        result = {
            'matlab_engine_available': MATLAB_ENGINE_AVAILABLE,
            'installation_path': None,
            'version': None,
            'required_toolboxes': ['Simulink', 'Stateflow', 'MATLAB_Coder', 'Simulink_Coder'],
            'available_toolboxes': [],
            'issues': []
        }
        
        if not MATLAB_ENGINE_AVAILABLE:
            result['issues'].append("MATLAB Engine for Python not installed")
            return result
        
        try:
            # Try to start a temporary engine for diagnostics
            temp_engine = matlab.engine.start_matlab()
            
            # Get MATLAB installation info
            matlab_root = temp_engine.eval("matlabroot")
            version = temp_engine.eval("version('-release')")
            
            result['installation_path'] = matlab_root
            result['version'] = version
            
            # Check available toolboxes
            for toolbox in result['required_toolboxes']:
                try:
                    available = temp_engine.eval(f"license('test', '{toolbox}')")
                    if available:
                        result['available_toolboxes'].append(toolbox)
                    else:
                        result['issues'].append(f"Toolbox not available: {toolbox}")
                except:
                    result['issues'].append(f"Could not check toolbox: {toolbox}")
            
            temp_engine.quit()
            
        except Exception as e:
            result['issues'].append(f"Could not start MATLAB Engine: {e}")
        
        return result
    
    @staticmethod
    def generate_diagnostic_report() -> str:
        """Generate a comprehensive diagnostic report"""
        diag = MatlabDiagnostics.check_matlab_installation()
        
        report_lines = [
            "MATLAB Integration Diagnostic Report",
            "=" * 40,
            "",
            f"MATLAB Engine Available: {diag['matlab_engine_available']}",
            f"Installation Path: {diag['installation_path'] or 'Not found'}",
            f"Version: {diag['version'] or 'Unknown'}",
            "",
            "Required Toolboxes:",
        ]
        
        for toolbox in diag['required_toolboxes']:
            status = "✓" if toolbox in diag['available_toolboxes'] else "✗"
            report_lines.append(f"  {status} {toolbox}")
        
        if diag['issues']:
            report_lines.extend([
                "",
                "Issues Found:",
            ])
            for issue in diag['issues']:
                report_lines.append(f"  • {issue}")
        
        if not diag['issues']:
            report_lines.extend([
                "",
                "✓ All checks passed! MATLAB integration should work properly."
            ])
        
        return "\n".join(report_lines)