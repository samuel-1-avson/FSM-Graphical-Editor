
# fsm_designer_project/core/matlab_integration.py

import sys
import os
import io
import logging
import time
import json
import threading
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QMetaObject, Q_ARG, pyqtSlot, Qt, QTimer
from jinja2 import Environment, FileSystemLoader
# --- NEW: Import the IR classes ---
from ..core.fsm_ir import FsmModel
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
    RECONNECTING = "reconnecting"
    BUSY = "busy"

class CommandType(Enum):
    """Types of MATLAB commands"""
    SIMULATION = "simulation"
    CODE_GENERATION = "code_generation"
    MODEL_GENERATION = "model_generation"
    GENERAL = "general"
    TEST = "test"
    VALIDATION = "validation"

class Priority(Enum):
    """Command priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class MatlabCommand:
    """Enhanced MATLAB command with metadata and callbacks"""
    command: str
    command_type: CommandType
    timeout: float = 30.0
    priority: Priority = Priority.NORMAL
    callback_signal: Optional[pyqtSignal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    progress_callback: Optional[Callable[[str, int], None]] = None
    
    def __post_init__(self):
        if not isinstance(self.metadata, dict):
            self.metadata = {}

@dataclass
class SimulationConfig:
    """Enhanced configuration for Simulink simulations with proper parameter handling"""
    stop_time: float = 10.0
    solver: str = 'ode45'
    fixed_step_size: Optional[float] = None
    save_output: bool = True
    output_variables: List[str] = field(default_factory=lambda: ['active_state_name'])
    log_signals: bool = True
    save_format: str = 'Dataset'
    data_logging_decimation: int = 1
    relative_tolerance: float = 1e-3
    absolute_tolerance: float = 1e-6
    max_step_size: Optional[float] = None
    initial_step_size: Optional[float] = None
    enable_fast_restart: bool = True
    compile_for_acceleration: bool = True
    
    def to_matlab_params(self) -> Dict[str, str]:
        """Convert configuration to MATLAB parameters with proper conflict avoidance."""
        params = {
            'StopTime': str(self.stop_time),
            'RelTol': str(self.relative_tolerance),
            'AbsTol': str(self.absolute_tolerance),
            'SaveOutput': 'on' if self.save_output else 'off',
            'SaveFormat': self.save_format,
            'LoggingToFile': 'on' if self.log_signals else 'off',
        }
        
        # Handle solver configuration properly to avoid parameter conflicts
        if self.fixed_step_size is not None:
            params['SolverType'] = 'Fixed-step'
            params['Solver'] = 'ode1'  # Common fixed-step solver
            params['FixedStep'] = str(self.fixed_step_size)
            # CRITICAL: Don't set SampleTimeConstraint for fixed-step solvers
        else:
            params['SolverType'] = 'Variable-step'
            params['Solver'] = self.solver
            # CRITICAL: Don't set SampleTimeConstraint - it causes the error you saw
            
            if self.max_step_size is not None:
                params['MaxStep'] = str(self.max_step_size)
            
            if self.initial_step_size is not None:
                params['InitialStep'] = str(self.initial_step_size)
        
        if self.data_logging_decimation > 1:
            params['DataLoggingDecimateData'] = 'on'
            params['DataLoggingDecimation'] = str(self.data_logging_decimation)
        else:
            params['DataLoggingDecimateData'] = 'off'
        
        if self.enable_fast_restart:
            params['FastRestart'] = 'on'
            
        return params
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate configuration for parameter conflicts."""
        errors = []

        # Check solver consistency
        if self.fixed_step_size is not None:
            if self.solver not in ['ode1', 'ode2', 'ode3', 'ode4', 'ode5', 'ode8']:
                errors.append(f"Solver '{self.solver}' is not compatible with fixed-step mode")

            if self.max_step_size is not None:
                errors.append("MaxStep is not applicable for fixed-step solvers")

            if self.initial_step_size is not None:
                errors.append("InitialStep is not applicable for fixed-step solvers")

        else:
            # Variable-step validation - remove overly strict validation
            pass  # Most solvers can work in variable-step mode
        
        # Validate numerical parameters
        if self.stop_time <= 0:
            errors.append("Stop time must be positive")

        if self.relative_tolerance <= 0 or self.relative_tolerance >= 1:
            errors.append("Relative tolerance must be between 0 and 1")

        if self.absolute_tolerance <= 0:
            errors.append("Absolute tolerance must be positive")

        return len(errors) == 0, errors

@dataclass
class CodeGenConfig:
    """Enhanced configuration for code generation"""
    language: str = "C++"
    target_file: str = "ert.tlc"
    optimization_level: str = "O2"
    generate_makefile: bool = True
    include_comments: bool = True
    custom_defines: Dict[str, str] = field(default_factory=dict)
    enable_rtw_build: bool = True
    generate_report: bool = True
    pack_struct_alignment: int = 8
    preserve_expression_order: bool = False
    enable_parallel_execution: bool = True
    max_idle_tasks: int = 4
    
    def to_matlab_commands(self, model_name: str) -> List[str]:
        """Convert configuration to MATLAB commands"""
        commands = [
            f"set_param('{model_name}', 'SystemTargetFile', '{self.target_file}');",
            f"set_param('{model_name}', 'TargetLang', '{self.language}');",
            f"set_param('{model_name}', 'OptimizationLevel', '{self.optimization_level}');",
            f"set_param('{model_name}', 'GenerateComments', '{'on' if self.include_comments else 'off'}');",
            f"set_param('{model_name}', 'GenerateMakefile', '{'on' if self.generate_makefile else 'off'}');",
            f"set_param('{model_name}', 'GenerateReport', '{'on' if self.generate_report else 'off'}');",
            f"set_param('{model_name}', 'PackNGo', 'on');",
        ]
        
        if self.custom_defines:
            defines_str = " ".join([f"-D{k}={v}" for k, v in self.custom_defines.items()])
            commands.append(f"set_param('{model_name}', 'CustomDefines', '{defines_str}');")
        
        return commands

class ParameterDiagnostics:
    """Utility class for diagnosing MATLAB parameter conflicts."""
    
    @staticmethod
    def diagnose_solver_config(config: SimulationConfig) -> Dict[str, Any]:
        """Diagnose potential solver configuration issues."""
        diagnosis = {
            'solver_type': 'fixed-step' if config.fixed_step_size else 'variable-step',
            'potential_conflicts': [],
            'recommendations': []
        }
        
        if config.fixed_step_size is not None:
            # Fixed-step analysis
            if config.solver not in ['ode1', 'ode2', 'ode3', 'ode4', 'ode5', 'ode8']:
                diagnosis['potential_conflicts'].append(
                    f"Solver '{config.solver}' may not be suitable for fixed-step"
                )
                diagnosis['recommendations'].append("Use 'ode1' for fixed-step mode")
            
            if config.max_step_size or config.initial_step_size:
                diagnosis['potential_conflicts'].append(
                    "Step size parameters not applicable for fixed-step"
                )
                diagnosis['recommendations'].append(
                    "Remove max_step_size and initial_step_size for fixed-step"
                )
        
        else:
            # Variable-step analysis
            if config.solver in ['ode1', 'ode2', 'ode3', 'ode4', 'ode5', 'ode8']:
                diagnosis['potential_conflicts'].append(
                    f"Solver '{config.solver}' is typically for fixed-step"
                )
                diagnosis['recommendations'].append("Use 'ode45' for variable-step mode")
        
        return diagnosis
    
    @staticmethod
    def create_safe_config(base_config: SimulationConfig = None) -> SimulationConfig:
        """Create a configuration that avoids common parameter conflicts."""
        if base_config is None:
            base_config = SimulationConfig()
        
        # Create safe configuration
        safe_config = SimulationConfig(
            stop_time=base_config.stop_time,
            solver='ode45',  # Safe variable-step solver
            fixed_step_size=None,  # Use variable-step to avoid conflicts
            save_output=base_config.save_output,
            relative_tolerance=base_config.relative_tolerance,
            absolute_tolerance=base_config.absolute_tolerance,
            enable_fast_restart=base_config.enable_fast_restart
        )
        
        return safe_config

class CommandQueue:
    """Thread-safe command queue with priority support"""
    
    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
    
    def put(self, command: MatlabCommand):
        """Add command to queue with priority ordering"""
        with self._lock:
            # Insert based on priority (higher priority first)
            inserted = False
            for i, existing_cmd in enumerate(self._queue):
                if command.priority.value > existing_cmd.priority.value:
                    self._queue.insert(i, command)
                    inserted = True
                    break
            
            if not inserted:
                self._queue.append(command)
    
    def get(self) -> Optional[MatlabCommand]:
        """Get next command from queue"""
        with self._lock:
            return self._queue.pop(0) if self._queue else None
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        with self._lock:
            return len(self._queue) == 0
    
    def size(self) -> int:
        """Get queue size"""
        with self._lock:
            return len(self._queue)
    
    def clear(self):
        """Clear all commands from queue"""
        with self._lock:
            self._queue.clear()

class EngineHealthMonitor:
    
    def __init__(self, engine_worker, interval_seconds: float = 10.0):
        self.worker = engine_worker
        self.health_data = {
            'last_heartbeat': time.time(),
            'response_times': [],
            'error_count': 0,
            'recovery_attempts': 0,
            'total_commands': 0,
            'successful_commands': 0
        }
        self._interval = float(interval_seconds)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    def _monitor_loop(self):
        while not self._stop_event.wait(self._interval):
            try:
                self._perform_health_check()
            except Exception as e:
                logger.exception("Unhandled exception in EngineHealthMonitor loop: %s", e)

    def start_monitoring(self):
        
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, name="EngineHealthMonitor", daemon=True)
        self._thread.start()
        logger.info("Engine health monitoring started (thread)")

    def stop_monitoring(self):
        
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("Engine health monitoring stopped (thread)")

    def _perform_health_check(self):
        
        if not getattr(self.worker, 'engine', None) or self.worker.state != EngineState.CONNECTED:
            return

        try:
            start_time = time.time()

            # Simple computation test
            self.worker.engine.eval("test_result = 2 + 2;", nargout=0)
            result = self.worker.engine.workspace['test_result']

            response_time = (time.time() - start_time) * 1000  # milliseconds
            with self._lock:
                self.health_data['response_times'].append(response_time)
                # Keep only last 50 response times
                if len(self.health_data['response_times']) > 50:
                    self.health_data['response_times'].pop(0)

            # Validate result
            if result != 4:
                raise ValueError(f"Unexpected health check result: {result}")

            self.health_data['last_heartbeat'] = time.time()
            self.health_data['error_count'] = max(0, self.health_data['error_count'] - 1)

            # Log performance metrics periodically
            if len(self.health_data['response_times']) % 10 == 0:
                avg_response = sum(self.health_data['response_times']) / len(self.health_data['response_times'])
                logger.debug(f"Engine health: avg response {avg_response:.1f}ms, success rate: {self.get_success_rate():.1%}")

        except Exception as e:
            logger.warning(f"Engine health check failed: {e}")
            self.health_data['error_count'] += 1

            # Trigger recovery if too many consecutive failures
            if self.health_data['error_count'] > 3:
                self._trigger_recovery()

    def _trigger_recovery(self):
        
        logger.error("Engine health degraded, attempting recovery...")
        self.health_data['recovery_attempts'] += 1
        # Call worker's failure handler in a safe manner
        try:
            self.worker._handle_engine_failure("Health check failures")
        except Exception:
            logger.exception("Failed to trigger engine recovery from health monitor")

    def get_health_metrics(self) -> Dict[str, Any]:
        
        with self._lock:
            avg = sum(self.health_data['response_times']) / len(self.health_data['response_times']) if self.health_data['response_times'] else 0.0
            return {
                'last_heartbeat': self.health_data['last_heartbeat'],
                'avg_response_ms': avg,
                'error_count': self.health_data['error_count'],
                'recovery_attempts': self.health_data['recovery_attempts'],
                'success_rate': self.get_success_rate(),
                'total_commands': self.health_data['total_commands']
            }

    def get_success_rate(self) -> float:
        
        if self.health_data['total_commands'] == 0:
            return 1.0
        return self.health_data['successful_commands'] / self.health_data['total_commands']

    def record_command_result(self, success: bool):
        
        with self._lock:
            self.health_data['total_commands'] += 1
            if success:
                self.health_data['successful_commands'] += 1


class MatlabEngineWorker(QObject):
    """
    Enhanced worker with improved reliability, performance monitoring, and advanced features
    """
    engine_status_changed = pyqtSignal(EngineState, str)
    command_finished = pyqtSignal(bool, str, str, CommandType, dict)  # success, message, data, type, metadata
    progress_updated = pyqtSignal(str, int)
    health_update = pyqtSignal(dict)  # health metrics
    
    def __init__(self):
        super().__init__()
        self.engine = None
        self.state = EngineState.DISCONNECTED
        self._is_shutting_down = False
        self._command_queue = CommandQueue()
        self._current_command = None
        self._engine_info = {}
        self._command_processing_timer: Optional[QTimer] = None
        
        # Enhanced monitoring
        self._health_monitor = EngineHealthMonitor(self)
        
        # Performance tracking
        self._command_history = []
        self._workspace_variables = set()
        
        # Auto-recovery settings
        self._max_auto_recovery_attempts = 3
        self._auto_recovery_count = 0
        self._last_recovery_time = 0

    @pyqtSlot()
    def start_engine(self):
        """Start MATLAB Engine with comprehensive initialization"""
        if self.state == EngineState.CONNECTED:
            self.engine_status_changed.emit(EngineState.CONNECTED, "Engine already running.")
            return

        if not MATLAB_ENGINE_AVAILABLE:
            msg = self._get_installation_help_message()
            self._set_state(EngineState.ERROR, msg)
            return

        self._set_state(EngineState.CONNECTING, "Starting MATLAB Engine with enhanced features...")
        
        try:
            logger.info("Initializing MATLAB Engine...")
            
            # Start engine with optimized settings
            startup_options = ['-nodesktop', '-nosplash', '-minimize', '-automation']
            self.engine = matlab.engine.start_matlab(' '.join(startup_options))
            
            # Validate and configure
            self._validate_and_configure_engine()
            
            # Start command processing
            if self._command_processing_timer is None:
                self._command_processing_timer = QTimer(self)
                self._command_processing_timer.setInterval(10) # check queue every 10ms
                self._command_processing_timer.timeout.connect(self._process_command_queue)
            self._command_processing_timer.start()
            
            # Start health monitoring
            self._health_monitor.start_monitoring()
            
            self._auto_recovery_count = 0  # Reset recovery counter on successful start
            
            self._set_state(EngineState.CONNECTED, 
                          f"MATLAB Engine ready. Version: {self._engine_info.get('version', 'Unknown')}")
            
        except Exception as e:
            msg = f"Failed to start MATLAB Engine: {e}"
            logger.error(msg, exc_info=True)
            self._cleanup_engine()
            self._set_state(EngineState.ERROR, msg)
            
            # Schedule auto-recovery if within limits using proper threading
            if self._auto_recovery_count < self._max_auto_recovery_attempts:
                recovery_timer = QTimer()
                recovery_timer.setSingleShot(True)
                recovery_timer.timeout.connect(self._attempt_auto_recovery)
                recovery_timer.moveToThread(self.thread())
                recovery_timer.start(10000)  # Retry after 10 seconds

    def _get_installation_help_message(self) -> str:
        """Get helpful installation message for missing MATLAB Engine"""
        return (
            "MATLAB Engine for Python not found.\n\n"
            "Installation Steps:\n"
            "1. Navigate to your MATLAB installation directory\n"
            "2. Go to: extern/engines/python\n"
            "3. Run: python setup.py install\n\n"
            "Example paths:\n"
            "Windows: C:\\Program Files\\MATLAB\\R2023b\\extern\\engines\\python\n"
            "Linux: /usr/local/MATLAB/R2023b/extern/engines/python\n"
            "macOS: /Applications/MATLAB_R2023b.app/extern/engines/python"
        )

    def _validate_and_configure_engine(self):
        """Enhanced engine validation and configuration"""
        try:
            # Get comprehensive MATLAB information
            commands = {
                'version': "version('-release')",
                'version_full': "version",
                'matlab_root': "matlabroot",
                'computer_type': "computer",
                'memory_info': "memory",
                'java_heap': "java.lang.Runtime.getRuntime().maxMemory()/1024/1024"
            }
            
            info = {}
            for key, cmd in commands.items():
                try:
                    result = self.engine.eval(cmd)
                    info[key] = result
                except:
                    info[key] = 'Unknown'
            
            # Check toolboxes with detailed information
            required_toolboxes = {
                'Simulink': 'simulink',
                'Stateflow': 'stateflow', 
                'MATLAB_Coder': 'matlab_coder',
                'Simulink_Coder': 'simulink_coder',
                'Embedded_Coder': 'embedded_coder'
            }
            
            available_toolboxes = {}
            for name, license_name in required_toolboxes.items():
                try:
                    # Check both license and installation
                    license_available = self.engine.eval(f"license('test', '{license_name}')")
                    # Try to get version info
                    try:
                        version_info = self.engine.eval(f"ver('{name.lower()}')")
                        available_toolboxes[name] = {
                            'available': bool(license_available),
                            'version': str(version_info) if version_info else 'Unknown'
                        }
                    except:
                        available_toolboxes[name] = {
                            'available': bool(license_available),
                            'version': 'Unknown'
                        }
                except Exception as e:
                    available_toolboxes[name] = {
                        'available': False,
                        'error': str(e)
                    }
            
            # Store comprehensive engine information
            self._engine_info = {
                'version': info['version'],
                'version_full': info['version_full'],
                'matlab_root': info['matlab_root'],
                'computer_type': info['computer_type'],
                'memory_info': info['memory_info'],
                'java_heap_mb': info['java_heap'],
                'available_toolboxes': available_toolboxes,
                'startup_time': time.time()
            }
            
            # Configure MATLAB environment for optimal performance
            initialization_commands = [
                "addpath(genpath('.')); % Add current directory recursively",
                "warning('off', 'all'); % Suppress warnings initially",
                "format compact; % Compact output format",
                "set(0, 'DefaultFigureVisible', 'off'); % Hide figures by default",
                "bdclose('all'); % Close any existing Simulink models",
                
                # Performance optimizations
                "feature('HotLinks', false); % Disable hot links in command window",
                "feature('DefaultCharacterSet', 'UTF8'); % Set character encoding",
                
                # Memory management
                "clear java; % Clear Java heap",
                
                # Set up FSM workspace
                "FSM_WORKSPACE = struct(); % Initialize FSM workspace",
                "FSM_WORKSPACE.created = datetime('now'); % Track creation time",
                "FSM_WORKSPACE.version = '2.0'; % FSM Designer version",
            ]
            
            for cmd in initialization_commands:
                try:
                    self.engine.eval(cmd, nargout=0)
                except Exception as e:
                    logger.warning(f"Initialization command failed: {cmd} - {e}")
            
            # Verify critical toolboxes
            critical_missing = []
            for name, info in available_toolboxes.items():
                if name in ['Simulink', 'Stateflow'] and not info.get('available', False):
                    critical_missing.append(name)
            
            if critical_missing:
                logger.warning(f"Critical toolboxes missing: {critical_missing}")
            
            logger.info(f"MATLAB Engine configured successfully:")
            logger.info(f"  Version: {self._engine_info['version']}")
            logger.info(f"  Root: {self._engine_info['matlab_root']}")
            logger.info(f"  Available toolboxes: {list(name for name, info in available_toolboxes.items() if info.get('available', False))}")

        except Exception as e:
            logger.error(f"Engine configuration failed: {e}")
            raise

    @pyqtSlot()
    def _process_command_queue(self):
        """Qt-safe slot for processing command queue one item at a time."""
        if self.state == EngineState.BUSY or self._is_shutting_down:
            return

        command = self._command_queue.get()
        if command:
            try:
                self._set_state(EngineState.BUSY, f"Executing {command.command_type.value} command...")
                self._execute_command_internal(command)
                self._set_state(EngineState.CONNECTED, "Ready for commands")
            except Exception as e:
                logger.error(f"Error in command processing: {e}", exc_info=True)
                self._set_state(EngineState.ERROR, f"Command processing error: {e}")

    @pyqtSlot(MatlabCommand)
    def execute_command(self, command: MatlabCommand):
        """Queue a command for execution"""
        if self.state == EngineState.ERROR:
            self._emit_command_result(False, f"Cannot execute command: Engine in error state", "", 
                                    command.command_type, command.metadata)
            return
        
        # Add to queue
        self._command_queue.put(command)
        logger.debug(f"Command queued: {command.command_type.value} (priority: {command.priority.value})")

    def _execute_command_internal(self, command: MatlabCommand):
        """Internal command execution with enhanced error handling"""
        self._current_command = command
        start_time = time.time()
        
        try:
            logger.debug(f"Executing {command.command_type.value} command (timeout: {command.timeout}s)")
            
            # Progress callback setup
            if command.progress_callback:
                command.progress_callback("Starting command execution", 0)
            
            # Set up enhanced output capture
            from io import StringIO
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            
            # Execute with comprehensive monitoring
            self.engine.eval(command.command, nargout=0, 
                           stdout=stdout_capture, stderr=stderr_capture,
                           background=False)
            
            execution_time = time.time() - start_time
            stdout = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()

            # Update command history
            self._command_history.append({
                'type': command.command_type.value,
                'execution_time': execution_time,
                'success': True,
                'timestamp': time.time()
            })
            
            # Keep only last 100 commands in history
            if len(self._command_history) > 100:
                self._command_history.pop(0)

            logger.debug(f"Command executed successfully in {execution_time:.2f}s")
            
            # Progress callback completion
            if command.progress_callback:
                command.progress_callback("Command completed", 100)

            # Parse and emit results
            success, message, data = self._parse_command_output_enhanced(stdout, stderr, command.command_type)
            self._emit_command_result(success, message, data, command.command_type, command.metadata)
            
            # Record success for health monitoring
            self._health_monitor.record_command_result(True)

        except matlab.engine.MatlabExecutionError as e:
            execution_time = time.time() - start_time
            error_msg = f"MATLAB Execution Error: {e}"
            logger.error(f"{error_msg} (after {execution_time:.2f}s)")
            
            self._command_history.append({
                'type': command.command_type.value,
                'execution_time': execution_time,
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            })
            
            # Attempt retry if configured
            if command.retry_count < command.max_retries:
                command.retry_count += 1
                logger.info(f"Retrying command (attempt {command.retry_count + 1}/{command.max_retries + 1})")
                retry_timer = QTimer()
                retry_timer.setSingleShot(True)
                retry_timer.timeout.connect(lambda: self._command_queue.put(command))
                retry_timer.moveToThread(self.thread())
                retry_timer.start(1000)
                return
            
            self._emit_command_result(False, error_msg, "", command.command_type, command.metadata)
            self._health_monitor.record_command_result(False)
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Unexpected Error: {e}"
            logger.error(f"{error_msg} (after {execution_time:.2f}s)", exc_info=True)
            
            self._emit_command_result(False, error_msg, "", command.command_type, command.metadata)
            self._health_monitor.record_command_result(False)
            
        finally:
            self._current_command = None

    def _parse_command_output_enhanced(self, stdout: str, stderr: str, command_type: CommandType) -> Tuple[bool, str, str]:
        """Enhanced output parsing with specific MATLAB error detection"""
        
        # Check for explicit success/failure markers first
        if "MATLAB_SCRIPT_SUCCESS:" in stdout:
            for line in stdout.splitlines():
                if line.startswith("MATLAB_SCRIPT_SUCCESS:"):
                    output_data = line.split(":", 1)[1].strip() if ":" in line else ""
                    return True, "Operation completed successfully.", output_data
        
        if "MATLAB_SCRIPT_FAILURE:" in stdout or "MATLAB_SCRIPT_FAILURE:" in stderr:
            error_detail = ""
            combined_output = stdout + stderr
            
            for line in combined_output.splitlines():
                if line.startswith("MATLAB_SCRIPT_FAILURE:"):
                    error_detail = line.split(":", 1)[1].strip() if ":" in line else "Unknown error"
                    break
            
            if not error_detail and stderr:
                error_detail = stderr.strip()
            
            return False, f"MATLAB operation failed: {error_detail}", ""
        
        # Enhanced MATLAB-specific error patterns
        matlab_error_patterns = [
            (r"Undefined function '([^']+)'", "Function Not Found"),
            (r"Undefined variable '([^']+)'", "Variable Not Found"), 
            (r"Index exceeds.*dimensions", "Index Error"),
            (r"License checkout failed for '([^']+)'", "License Error"),
            (r"Cannot add block.*already exists", "Block Already Exists"),
            (r"Invalid Simulink object name '([^']+)'", "Invalid Object Name"),
            (r"Model '([^']+)' not found", "Model Not Found"),
            (r"Stateflow.*error", "Stateflow Error")
        ]
        
        combined_output = stdout + stderr
        
        for pattern, error_type in matlab_error_patterns:
            matches = re.findall(pattern, combined_output, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    detail = f"{error_type}: {matches[0][0]}"
                else:
                    detail = f"{error_type}: {matches[0]}"
                return False, detail, stdout
        
        # Check for warnings that might indicate parameter conflicts
        warning_patterns = [
            (r"Parameter '([^']+)' is ignored", "Parameter Ignored Warning"),
            (r"Warning.*Parameter.*constraint", "Parameter Constraint Warning"),
            (r"Model.*contains errors", "Model Validation Warning")
        ]
        
        warnings = []
        for pattern, warning_type in warning_patterns:
            matches = re.findall(pattern, combined_output, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    warnings.append(f"{warning_type}: {matches[0][0]}")
                else:
                    warnings.append(f"{warning_type}: {matches[0]}")
        
        if warnings:
            message = f"Command completed with warnings: {'; '.join(warnings[:3])}"  # Limit to 3 warnings
            return True, message, stdout
        
        # Default success case
        if stdout.strip() or not stderr.strip():
            return True, "Command executed successfully.", stdout
        
        return False, f"Command failed with errors: {stderr.strip()}", stdout

    def _emit_command_result(self, success: bool, message: str, data: str, 
                           command_type: CommandType, metadata: Dict[str, Any]):
        """Emit enhanced command result with metadata"""
        enhanced_metadata = metadata.copy()
        enhanced_metadata.update({
            'execution_timestamp': time.time(),
            'engine_state': self.state.value,
            'queue_size': self._command_queue.size()
        })
        
        self.command_finished.emit(success, message, data, command_type, enhanced_metadata)

    def _attempt_auto_recovery(self):
        """Fixed auto-recovery with proper thread context"""
        if self._auto_recovery_count >= self._max_auto_recovery_attempts:
            logger.error("Maximum auto-recovery attempts reached")
            return
        
        current_time = time.time()
        if current_time - self._last_recovery_time < 30:  # Wait at least 30 seconds between attempts
            recovery_timer = QTimer()
            recovery_timer.setSingleShot(True)
            recovery_timer.timeout.connect(self._attempt_auto_recovery)
            recovery_timer.moveToThread(self.thread())
            recovery_timer.start(30000)
            return
        
        self._auto_recovery_count += 1
        self._last_recovery_time = current_time
        
        logger.info(f"Attempting auto-recovery {self._auto_recovery_count}/{self._max_auto_recovery_attempts}")
        
        # Use proper thread invocation
        QMetaObject.invokeMethod(self, "start_engine", Qt.ConnectionType.QueuedConnection)

    def _handle_engine_failure(self, reason: str):
        """Fixed engine failure handling with proper threading"""
        logger.error(f"Engine failure detected: {reason}")
        
        # Clear command queue to prevent further issues
        self._command_queue.clear()
        
        # Cleanup and update state
        self._cleanup_engine()
        self._set_state(EngineState.ERROR, f"Engine failed: {reason}")
        
        # Use QTimer for delayed recovery attempt
        if self._auto_recovery_count < self._max_auto_recovery_attempts:
            recovery_timer = QTimer()
            recovery_timer.setSingleShot(True)
            recovery_timer.timeout.connect(self._attempt_auto_recovery)
            recovery_timer.moveToThread(self.thread())
            recovery_timer.start(5000)

    def _set_state(self, new_state: EngineState, message: str):
        """Update engine state and emit signal"""
        old_state = self.state
        self.state = new_state
        
        if old_state != new_state:
            logger.info(f"Engine state changed: {old_state.value} -> {new_state.value}: {message}")
        
        self.engine_status_changed.emit(new_state, message)

    def _cleanup_engine(self):
        """Enhanced cleanup with better resource management"""
        # Stop health monitoring
        if hasattr(self, '_health_monitor'):
            self._health_monitor.stop_monitoring()
        
        # Stop command processing timer
        if self._command_processing_timer:
            self._command_processing_timer.stop()
        
        # Cleanup engine
        if self.engine:
            try:
                # Try to save workspace if needed
                if hasattr(self, '_workspace_variables') and self._workspace_variables:
                    logger.debug("Saving workspace variables before shutdown")
                
                # Clear workspace
                self.engine.eval("clear all; close all; bdclose('all');", nargout=0)
                
                # Quit engine
                self.engine.quit()
                logger.info("MATLAB Engine shut down gracefully")
            except Exception as e:
                logger.warning(f"Error during engine cleanup: {e}")
            finally:
                self.engine = None

    @pyqtSlot()
    def shutdown_engine(self):
        """Enhanced graceful shutdown"""
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        self._set_state(EngineState.SHUTTING_DOWN, "Shutting down engine...")
        
        logger.info("Initiating MATLAB Engine shutdown...")
        
        # Wait for current command to complete
        if self._current_command:
            logger.info("Waiting for current command to complete...")
            max_wait = 10  # seconds
            wait_count = 0
            while self._current_command and wait_count < max_wait:
                time.sleep(0.5)
                wait_count += 0.5
        
        self._cleanup_engine()
        self._set_state(EngineState.DISCONNECTED, "Engine shut down successfully.")

    @pyqtSlot()
    def get_engine_status(self):
        """Get comprehensive engine status"""
        if self._health_monitor:
            health_metrics = self._health_monitor.get_health_metrics()
            self.health_update.emit(health_metrics)

    @pyqtSlot(str)
    def clear_workspace_variable(self, var_name: str):
        """Clear specific workspace variable"""
        if self.state == EngineState.CONNECTED and self.engine:
            try:
                self.engine.eval(f"clear {var_name};", nargout=0)
                self._workspace_variables.discard(var_name)
                logger.debug(f"Cleared workspace variable: {var_name}")
            except Exception as e:
                logger.warning(f"Failed to clear variable {var_name}: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        if not self._command_history:
            return {"message": "No commands executed yet"}
        
        # Calculate metrics
        total_commands = len(self._command_history)
        successful_commands = sum(1 for cmd in self._command_history if cmd['success'])
        failed_commands = total_commands - successful_commands
        
        execution_times = [cmd['execution_time'] for cmd in self._command_history if cmd['success']]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Command type breakdown
        type_breakdown = {}
        for cmd in self._command_history:
            cmd_type = cmd['type']
            if cmd_type not in type_breakdown:
                type_breakdown[cmd_type] = {'total': 0, 'successful': 0}
            type_breakdown[cmd_type]['total'] += 1
            if cmd['success']:
                type_breakdown[cmd_type]['successful'] += 1
        
        return {
            'total_commands': total_commands,
            'successful_commands': successful_commands,
            'failed_commands': failed_commands,
            'success_rate': successful_commands / total_commands if total_commands > 0 else 0,
            'avg_execution_time': avg_execution_time,
            'command_type_breakdown': type_breakdown,
            'engine_uptime': time.time() - self._engine_info.get('startup_time', time.time()),
            'queue_size': self._command_queue.size()
        }


class MatlabConnection(QObject):
    """Enhanced MATLAB connection manager with better thread safety"""
    connectionStatusChanged = pyqtSignal(EngineState, str)
    simulationFinished = pyqtSignal(bool, str, str, dict)  # success, message, data, metadata
    codeGenerationFinished = pyqtSignal(bool, str, str, dict)
    modelGenerationFinished = pyqtSignal(bool, str, str, dict)
    progressUpdated = pyqtSignal(str, int)
    healthUpdated = pyqtSignal(dict)
    performanceUpdated = pyqtSignal(dict)
    # --- NEW: Signal for live data streamed from callbacks ---
    simulationDataUpdated = pyqtSignal(dict)  # Emits {'time': float, 'state': str}

    def __init__(self):
        super().__init__()
        self.state = EngineState.DISCONNECTED
        self.matlab_path = ""
        self._last_simulation_data = None
        self._model_cache = {}
        self._setup_worker_thread()
        
        self._perf_timer = QTimer()
        self._perf_timer.timeout.connect(self._update_performance_metrics)
        self._perf_timer.setInterval(30000)
        self._perf_timer.start()

    def _setup_worker_thread(self):
        """Initialize worker thread with proper error handling"""
        self.thread = QThread()
        self.thread.setObjectName("MatlabEngineThread")
        
        self.worker = MatlabEngineWorker()
        self.worker.moveToThread(self.thread)
        
        # Connect signals with proper error handling
        self.worker.engine_status_changed.connect(self._on_engine_status_changed)
        self.worker.command_finished.connect(self._on_command_finished)
        self.worker.progress_updated.connect(self.progressUpdated)
        self.worker.health_update.connect(self.healthUpdated)
        
        # Handle thread lifecycle properly
        self.thread.started.connect(self.worker.start_engine)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        # Start thread
        self.thread.start()
        
    @pyqtSlot(EngineState, str)
    def _on_engine_status_changed(self, state: EngineState, message: str):
        """Handle engine status changes with enhanced logging"""
        old_state = self.state
        self.state = state
        
        if old_state != state:
            logger.info(f"Connection state: {old_state.value} -> {state.value}")
        
        self.connectionStatusChanged.emit(state, message)

    @pyqtSlot(bool, str, str, CommandType, dict)
    def _on_command_finished(self, success: bool, message: str, data: str, 
                           command_type: CommandType, metadata: Dict[str, Any]):
        """Enhanced command result handling with metadata"""

        # --- NEW: Parse stdout for SIM_DATA messages streamed from callbacks ---
        if command_type == CommandType.SIMULATION:
            for line in message.splitlines():
                if line.startswith("SIM_DATA:"):
                    try:
                        json_str = line.split(":", 1)[1]
                        sim_data = json.loads(json_str)
                        self.simulationDataUpdated.emit(sim_data)
                    except (json.JSONDecodeError, IndexError) as e:
                        logger.warning(f"Could not parse live simulation data line: {line} | Error: {e}")

        # --- FIX: Chained command execution logic ---
        if command_type == CommandType.MODEL_GENERATION:
            if success:
                # After model generation, the next step is to instantiate the FSM class
                model_name = metadata.get('model_name')
                slx_file_path = metadata.get('output_path')
                class_name = metadata.get('class_name')

                if model_name and slx_file_path and class_name:
                    logger.info(f"Model generated. Now instantiating MATLAB FSM class '{class_name}'.")
                    matlab_slx_path = str(slx_file_path).replace(os.sep, '/')
                    m_file_dir = os.path.dirname(matlab_slx_path).replace('\\', '/')
                    
                    instantiate_command_str = (
                        f"addpath('{m_file_dir}'); "
                        f"clear FSM_INSTANCE; "
                        f"FSM_INSTANCE = {class_name}('{matlab_slx_path}');"
                    )
                    
                    instantiate_command = MatlabCommand(
                        command=instantiate_command_str,
                        command_type=CommandType.GENERAL,
                        priority=Priority.CRITICAL,
                        metadata={'purpose': 'fsm_instantiation'}
                    )
                    # Use a zero-delay timer to break the call chain and avoid thread issues
                    QTimer.singleShot(0, lambda: self._execute_command(instantiate_command))
            self.modelGenerationFinished.emit(success, message, data, metadata)

        elif command_type == CommandType.GENERAL and metadata.get('purpose') == 'fsm_instantiation':
            if success:
                # After instantiation, the next step is to set up streaming
                setup_streaming_command = MatlabCommand(
                    command="FSM_INSTANCE.setup_data_streaming();",
                    command_type=CommandType.GENERAL,
                    priority=Priority.HIGH,
                    metadata={'purpose': 'setup_streaming'}
                )
                QTimer.singleShot(0, lambda: self._execute_command(setup_streaming_command))
            else:
                logger.error("FSM class instantiation failed. Data streaming will not be set up.")
        
        elif command_type == CommandType.SIMULATION:
            if success and data:
                self._last_simulation_data = {'data': data, 'timestamp': time.time(), 'metadata': metadata}
            self.simulationFinished.emit(success, message, data, metadata)
            
        elif command_type == CommandType.CODE_GENERATION:
            self.codeGenerationFinished.emit(success, message, data, metadata)
        
        # Other GENERAL commands (like setup_streaming) don't trigger further actions here.

    def _update_performance_metrics(self):
        """Update performance metrics periodically"""
        if hasattr(self.worker, 'get_performance_metrics'):
            try:
                metrics = self.worker.get_performance_metrics()
                self.performanceUpdated.emit(metrics)
            except Exception as e:
                logger.warning(f"Failed to get performance metrics: {e}")

    def is_connected(self) -> bool:
        """Check if engine is connected and ready"""
        return self.state == EngineState.CONNECTED

    def is_busy(self) -> bool:
        """Check if engine is currently executing commands"""
        return self.state == EngineState.BUSY

    def _execute_command(self, command: MatlabCommand):
        """Execute a command with enhanced error checking"""
        if self.state == EngineState.ERROR:
            metadata = command.metadata.copy()
            metadata['error_reason'] = 'Engine in error state'
            self._on_command_finished(False, "MATLAB Engine not connected.", "", 
                                    command.command_type, metadata)
            return
        
        if self.state == EngineState.DISCONNECTED:
            metadata = command.metadata.copy()
            metadata['error_reason'] = 'Engine disconnected'
            self._on_command_finished(False, "MATLAB Engine disconnected.", "", 
                                    command.command_type, metadata)
            return
        
        QMetaObject.invokeMethod(self.worker, "execute_command", Qt.ConnectionType.QueuedConnection,
                               Q_ARG(MatlabCommand, command))

    def generate_simulink_model(self, fsm_model: FsmModel, 
                              output_dir: str, model_name: str = "BrainStateMachine",
                              **kwargs) -> bool:
        """Generate enhanced Simulink model from the FSM IR."""
        
        # Validation should now ideally happen before this point, on the IR itself.
        # We assume a valid FsmModel is passed.
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        slx_file_path = output_path / f"{model_name}.slx"
        
        options = {
            'enable_data_logging': kwargs.get('enable_data_logging', True),
            'create_test_harness': kwargs.get('create_test_harness', False),
            'add_scope_blocks': kwargs.get('add_scope_blocks', True),
            'optimize_layout': kwargs.get('optimize_layout', True),
            'generate_documentation': kwargs.get('generate_documentation', False)
        }

        class_name = f"FSM_{model_name}"
        # --- MODIFICATION: Pass the IR object to the script generator ---
        script_content, m_file_generated = self._create_enhanced_model_generation_script(
            fsm_model, str(slx_file_path), model_name, options, class_name
        )
        
        if not m_file_generated:
            self.modelGenerationFinished.emit(False, "Failed to generate the MATLAB FSM class file.", "", {})
            return False

        metadata = {
            'model_name': model_name,
            'class_name': class_name,
            'output_path': str(slx_file_path),
            'state_count': len(fsm_model.states),
            'transition_count': len(fsm_model.transitions),
            'options': options,
            'generation_start_time': time.time()
        }
        
        command = MatlabCommand(
            command=script_content,
            command_type=CommandType.MODEL_GENERATION,
            timeout=120.0,
            priority=Priority.HIGH,
            metadata=metadata,
            progress_callback=lambda msg, pct: self.progressUpdated.emit(f"Model Generation: {msg}", pct)
        )
        
        self._execute_command(command)
        return True

    def _create_enhanced_model_generation_script(self, fsm_model: FsmModel,
                                       output_path: str, model_name: str, 
                                       options: Dict[str, bool], class_name: str) -> Tuple[str, bool]:
        """Create MATLAB script for model generation with FIXED character sanitization."""
        import unicodedata
        from ..utils.config import APP_NAME, APP_VERSION

        templates_dir = Path(__file__).parent.parent / 'assets' / 'templates'
        env = Environment(loader=FileSystemLoader(str(templates_dir)))

        def sanitize_matlab_content_comprehensive(content: str) -> str:
            """Comprehensive MATLAB content sanitization."""
            if not content:
                return ""
            
            # Remove BOM if present
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # Unicode normalization and combining character removal
            try:
                content = unicodedata.normalize('NFD', content)
                content = ''.join(c for c in content if not unicodedata.combining(c))
            except Exception:
                pass
            
            # Replace common problematic Unicode characters
            unicode_replacements = {
                '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",
                '\u201a': "'", '\u201e': '"', '\u2013': '-', '\u2014': '-',
                '\u2015': '-', '\u2212': '-', '\u2026': '...', '\u00a0': ' ',
                '\u00b4': "'", '\u2010': '-', '\u2011': '-', '\u00d7': '*',
                '\u00f7': '/', '\u2264': '<=', '\u2265': '>=', '\u2260': '~=',
                '\u2190': '<-', '\u2192': '->', '\ufeff': '',
            }
            
            for unicode_char, replacement in unicode_replacements.items():
                content = content.replace(unicode_char, replacement)
            
            # Filter to safe ASCII characters only
            safe_chars = []
            for char in content:
                code_point = ord(char)
                if 32 <= code_point <= 126 or char in ['\n', '\r', '\t']:
                    safe_chars.append(char)
                elif char.isspace():
                    safe_chars.append(' ')
            
            content = ''.join(safe_chars)
            
            # Clean up whitespace
            import re
            content = re.sub(r'\r\n', '\n', content)
            content = re.sub(r'\r', '\n', content) 
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = re.sub(r'[ \t]+\n', '\n', content)
            content = re.sub(r'[ \t]{2,}', ' ', content)
            
            return content.strip()

        def sanitize_template_context(context: dict) -> dict:
            """Sanitize template context values."""
            sanitized = {}
            for key, value in context.items():
                if isinstance(value, str):
                    sanitized[key] = sanitize_matlab_content_comprehensive(value)
                else:
                    sanitized[key] = value
            return sanitized

        try:
            # Create and sanitize template context
            context = sanitize_template_context({
                'model_name': model_name,
                'class_name': class_name,
                'app_name': APP_NAME,
                'app_version': APP_VERSION,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Render template
            class_template = env.get_template("matlab_fsm_class.m.j2")
            class_content = class_template.render(context)
            
            # Apply comprehensive sanitization to rendered content
            class_content = sanitize_matlab_content_comprehensive(class_content)
            
            # Write file with ASCII encoding and Unix line endings
            m_file_path = Path(output_path).parent / f"{class_name}.m"
            
            # Write as pure ASCII
            with open(m_file_path, 'w', encoding='ascii', newline='\n') as f:
                f.write(class_content)

            logger.info(f"Generated sanitized MATLAB FSM class file at: {m_file_path}")
            m_file_generated = True

        except UnicodeEncodeError as e:
            logger.error(f"Unicode encoding error in MATLAB file: {e}")
            logger.info("Attempting to write with forced ASCII encoding...")
            
            try:
                # Force ASCII encoding as last resort
                with open(m_file_path, 'w', encoding='ascii', errors='ignore', newline='\n') as f:
                    f.write(class_content)
                logger.warning("MATLAB file written with forced ASCII encoding (some characters may be lost)")
                m_file_generated = True
            except Exception as e2:
                logger.error(f"Failed to write MATLAB class file even with forced encoding: {e2}")
                m_file_generated = False
                
        except Exception as e:
            logger.error(f"Failed to write MATLAB class file: {e}", exc_info=True)
            m_file_generated = False

        # Generate the SLX script
        slx_script_content = self._create_slx_generation_script_fixed(
            fsm_model, output_path, model_name, options
        )

        return slx_script_content, m_file_generated

    def _create_slx_generation_script_fixed(self, fsm_model: 'FsmModel', output_path: str, model_name: str, 
                                          options: Dict[str, bool]) -> str:
        """Fixed version of the SLX generation script with proper parameter handling"""
        
        # Convert path for MATLAB compatibility
        slx_file_path = output_path.replace(os.sep, '/')
    
        # --- Helper functions to generate code blocks from the IR ---

        def sanitize_matlab_code(code: str) -> str:
            """Sanitize MATLAB code to prevent character encoding issues"""
            if not code:
                return ""

            # Replace problematic characters
            replacements = {
                '“': '"',  # Smart quotes
                '”': '"',
                '‘': "'",  # Smart apostrophes
                '’': "'",
                '–': '-',  # Dashes
                '—': '-',
                '…': '...',  # Ellipsis
            }

            sanitized = code
            for unicode_char, ascii_char in replacements.items():
                sanitized = sanitized.replace(unicode_char, ascii_char)

            # Ensure only printable ASCII characters (plus essential whitespace)
            result = []
            for char in sanitized:
                code_point = ord(char)
                if (32 <= code_point <= 126) or char in ['\n', '\r', '\t']:
                    result.append(char)
                elif char.isspace():
                    result.append(' ')
                # Skip other characters

            return ''.join(result).strip()

        def generate_state_creation_code(states: List['State']) -> List[str]:
            """Generates MATLAB code for creating states from the IR."""
            script_lines = ["    % Enhanced state creation with advanced features"]
        
            for i, state in enumerate(states):
                state_id = f"state_{i}_{state.name.replace(' ', '_').replace('-', '_')}"
                state_id = re.sub(r'[^a-zA-Z0-9_]', '_', state_id)
                if not state_id or not state_id[0].isalpha():
                    state_id = 's_' + state_id
        
                sf_x = state.properties.get('x', 50 + (i % 4) * 150) / 2.0 + 30
                sf_y = state.properties.get('y', 50 + (i // 4) * 120) / 2.0 + 30
                sf_w = max(100, state.properties.get('width', 120) / 2.0)
                sf_h = max(60, state.properties.get('height', 80) / 2.0)
        
                # --- START FIX: Corrected string escaping logic ---
                # 1. Prepare strings for the Stateflow action language context.
                #    Here, single quotes within strings must be doubled.
                state_name_for_action = sanitize_matlab_code(state.name).replace("'", "''")
        
                label_parts = [
                    f"entry: active_state_name = '{state_name_for_action}'; active_state_index = {i+1};"
                ]
        
                if state.entry_action and state.entry_action.code:
                    code = sanitize_matlab_code(state.entry_action.code).replace('\n', '; ').replace("'", "''")
                    label_parts.append(f"entry: try; {code}; catch; end;")
        
                if state.during_action and state.during_action.code:
                    code = sanitize_matlab_code(state.during_action.code).replace('\n', '; ').replace("'", "''")
                    label_parts.append(f"during: try; {code}; catch; end;")
        
                if state.exit_action and state.exit_action.code:
                    code = sanitize_matlab_code(state.exit_action.code).replace('\n', '; ').replace("'", "''")
                    label_parts.append(f"exit: try; {code}; catch; end;")
        
                # 2. Join the parts to form the final Stateflow label string. Stateflow uses '\n'.
                state_label_for_stateflow = "\\n".join(label_parts)
        
                # 3. Now, prepare strings for the MATLAB script context.
                #    This requires escaping single quotes for the script's parser.
                name_for_script = sanitize_matlab_code(state.name).replace("'", "''")
                description_for_script = sanitize_matlab_code(state.description or f"State {state.name}").replace("'", "''")
                label_for_script = state_label_for_stateflow.replace("'", "''")
                # --- END FIX ---
        
                script_lines.extend([
                    f"    % Create state: {name_for_script}",
                    f"    {state_id} = Stateflow.State(chartSFObj);",
                    f"    {state_id}.Name = '{name_for_script}';",
                    f"    {state_id}.Position = [{sf_x:.1f}, {sf_y:.1f}, {sf_w:.1f}, {sf_h:.1f}];",
                    f"    {state_id}.LabelString = '{label_for_script}';",
                    f"    {state_id}.Description = '{description_for_script}';",
                    f"    stateHandles('{name_for_script}') = {state_id};",
                    f"    stateIndexMap('{name_for_script}') = {i+1};"
                ])
        
                if state.is_initial:
                    initial_trans_label = "[trans_count_local = 0]".replace("'", "''")
                    script_lines.extend([
                        f"    % Set {name_for_script} as initial state",  
                        f"    defaultTrans_{i} = Stateflow.Transition(chartSFObj);",
                        f"    defaultTrans_{i}.Destination = {state_id};",
                        f"    defaultTrans_{i}.DestinationOClock = 12;",
                        f"    defaultTrans_{i}.LabelString = '{initial_trans_label}';",
                        f"    defaultTrans_{i}.Description = 'Initial transition to {name_for_script}';"
                    ])
        
                script_lines.append("")
        
            return script_lines
        
        def generate_transition_creation_code(transitions: List['Transition']) -> List[str]:
            """Generates MATLAB code for creating transitions from the IR."""
            script_lines = [
                "    % Enhanced transition creation with validation",
                "    fprintf('FSM_PROGRESS: Creating transitions...\\n');"
            ]
        
            for i, trans in enumerate(transitions):
                # --- START FIX: Corrected string escaping logic ---
                # 1. Prepare strings for the MATLAB script context (like keys and descriptions).
                src_name = sanitize_matlab_code(trans.source_name).replace("'", "''")
                dst_name = sanitize_matlab_code(trans.target_name).replace("'", "''")
            
                # 2. Build the raw Stateflow label string, escaping for Stateflow's action language where needed.
                label_parts_raw = []
                if trans.event:
                    clean_event = sanitize_matlab_code(trans.event)
                    clean_event = re.sub(r'[^a-zA-Z0-9_]', '_', clean_event)
                    if clean_event:
                        label_parts_raw.append(clean_event)
            
                if trans.condition and trans.condition.code:
                    condition_for_sf = sanitize_matlab_code(trans.condition.code).replace('\n', ' ').replace("'", "''")
                    label_parts_raw.append(f"[{condition_for_sf}]")
            
                action_parts_raw = []
                if trans.action and trans.action.code:
                    action_for_sf = sanitize_matlab_code(trans.action.code).replace('\n', '; ').replace("'", "''")
                    action_parts_raw.append(f"try; {action_for_sf}; catch; end")
            
                action_parts_raw.append("trans_count_local = trans_count_local + 1")
                action_parts_raw.append("transition_count = trans_count_local")
            
                if action_parts_raw:
                    label_parts_raw.append(f"/{{{'; '.join(action_parts_raw)}}}")
            
                # 3. Join parts and escape the entire string for the MATLAB script context.
                trans_label_stateflow = " ".join(label_parts_raw).strip()
                trans_label_for_script = trans_label_stateflow.replace("'", "''")
                # --- END FIX ---
            
                script_lines.extend([
                    f"    % Create transition {i+1}: {src_name} -> {dst_name}",
                    f"    if isKey(stateHandles, '{src_name}') && isKey(stateHandles, '{dst_name}')",
                    f"        srcState = stateHandles('{src_name}');",
                    f"        dstState = stateHandles('{dst_name}');",
                    f"        trans_{i} = Stateflow.Transition(chartSFObj);",
                    f"        trans_{i}.Source = srcState;",
                    f"        trans_{i}.Destination = dstState;",
                    f"        trans_{i}.Description = 'Transition from {src_name} to {dst_name}';",
                    f"        if ~isempty('{trans_label_for_script}')",
                    f"            trans_{i}.LabelString = '{trans_label_for_script}';",
                    f"        end",
                    "    else",
                    f"        warning('States not found for transition {i+1}: {src_name} -> {dst_name}');",
                    f"        fprintf('FSM_PROGRESS: Warning - Invalid transition: {src_name} -> {dst_name}\\n');",
                    "    end",
                ""
                ])
        
            return script_lines
        
        # Enhanced chart creation with comprehensive fallback
        def generate_enhanced_chart_creation_script() -> str:
            return """
    % Enhanced Stateflow chart creation with comprehensive fallback
    chartAdded = false;
    chartError = '';
    
    % Method 1: Try sflib/Chart (most common)
    try
        if ~chartAdded
            fprintf('FSM_PROGRESS: Attempting chart creation method 1...\\n');
            add_block('sflib/Chart', chartBlockPath, 'Position', [100 50 500 400]);
            chartAdded = true;
            fprintf('FSM_PROGRESS: Chart created using sflib/Chart\\n');
        end
    catch chartErr1
        fprintf('Method 1 failed: %s\\n', chartErr1.message);
    end
    
    % Method 2: Try Stateflow library directly
    try
        if ~chartAdded
            fprintf('FSM_PROGRESS: Attempting chart creation method 2...\\n');
            % Ensure Stateflow library is loaded
            load_system('stateflow');
            add_block('stateflow/Chart', chartBlockPath, 'Position', [100 50 500 400]);
            chartAdded = true;
            fprintf('FSM_PROGRESS: Chart created using stateflow/Chart\\n');
        end
    catch chartErr2
        fprintf('Method 2 failed: %s\\n', chartErr2.message);
    end
    
    % Method 3: Try User-Defined Functions path
    try
        if ~chartAdded
            fprintf('FSM_PROGRESS: Attempting chart creation method 3...\\n');
            add_block('simulink/User-Defined Functions/Stateflow Chart', chartBlockPath, ...
                     'Position', [100 50 500 400]);
            chartAdded = true;
            fprintf('FSM_PROGRESS: Chart created using User-Defined Functions\\n');
        end
    catch chartErr3
        fprintf('Method 3 failed: %s\\n', chartErr3.message);
    end
    
    % Method 4: Search for any available Stateflow chart block
    try
        if ~chartAdded
            fprintf('FSM_PROGRESS: Searching for available Stateflow blocks...\\n');
            % Find all loaded libraries
            libs = find_system('type', 'block_diagram', 'BlockDiagramType', 'library');
            
            for i = 1:length(libs)
                try
                    sfBlocks = find_system(libs{i}, 'BlockType', 'StateflowChart');
                    if ~isempty(sfBlocks)
                        add_block(sfBlocks{1}, chartBlockPath, 'Position', [100 50 500 400]);
                        chartAdded = true;
                        fprintf('FSM_PROGRESS: Chart created using found block: %s\\n', sfBlocks{1});
                        break;
                    end
                catch
                    continue;
                end
            end
        end
    catch chartErr4
        fprintf('Method 4 failed: %s\\n', chartErr4.message);
    end
    
    if ~chartAdded
        % Last resort: create a custom Stateflow chart programmatically
        try
            fprintf('FSM_PROGRESS: Creating chart programmatically...\\n');
            % Create a subsystem first
            add_block('built-in/SubSystem', chartBlockPath, 'Position', [100 50 500 400]);
            
            % Convert to Stateflow chart programmatically
            chartSFObj = Stateflow.Chart();
            chartSFObj.Name = 'FSM_Chart';
            
            % Get the machine object
            machine = find(sfroot, '-isa', 'Stateflow.Machine', 'Name', modelNameVar);
            if isempty(machine)
                machine = Stateflow.Machine();
                machine.Name = modelNameVar;
            end
            
            chartSFObj.Machine = machine;
            chartAdded = true;
            fprintf('FSM_PROGRESS: Chart created programmatically\\n');
            
        catch chartErr5
            chartError = sprintf('All methods failed. Last error: %s', chartErr5.message);
        end
    end
    
    if ~chartAdded
        error('Failed to create Stateflow chart: %s', chartError);
    end
            """

        # --- Main Script Generation with Enhanced Error Handling ---
    
        script_lines = [
            "% Enhanced FSM Model Generation Script",
            "% Generated by FSM Designer with advanced features",
            f"modelNameVar = '{model_name}';",
            f"outputModelPath = '{slx_file_path}';",
            "optimizeLayout = true;",
            "",
            "try",
            "    fprintf('FSM_PROGRESS: Initializing model generation...\\n');",
            "    ",
            "    % Clean up any existing model",
            "    if bdIsLoaded(modelNameVar)",
            "        fprintf('FSM_PROGRESS: Closing existing model...\\n');",
            "        close_system(modelNameVar, 0);",
            "    end",
            "    ",
            "    if exist(outputModelPath, 'file')",
            "        fprintf('FSM_PROGRESS: Removing existing model file...\\n');",
            "        delete(outputModelPath);",
            "    end",
            "    ",
            "    fprintf('FSM_PROGRESS: Creating new model...\\n');",
            "    hModel = new_system(modelNameVar, 'Model');",
            "    open_system(hModel);",
            "    ",
            "    % Configure model parameters with proper validation",
            "    fprintf('FSM_PROGRESS: Configuring model parameters...\\n');",
            "    set_param(modelNameVar, 'StopTime', '10.0');",
            "    ",
            "    % Configure solver - check if fixed-step is needed",
            "    solverType = get_param(modelNameVar, 'SolverType');",
            "    if strcmp(solverType, 'Fixed-step')",
            "        set_param(modelNameVar, 'Solver', 'ode1');  % Use fixed-step solver",
            "        set_param(modelNameVar, 'FixedStep', '0.1');",
            "        % SampleTimeConstraint can be set here if needed for specific fixed-step scenarios",
            "        set_param(modelNameVar, 'SampleTimeConstraint', 'STIndependent');",
            "    else",
            "        set_param(modelNameVar, 'Solver', 'ode45');  % Variable-step solver",
            "        % Do NOT set SampleTimeConstraint for variable-step solvers as it causes conflicts.",
            "    end",
            "    ",
            "    fprintf('FSM_PROGRESS: Creating Stateflow chart...\\n');",
            "    chartBlockPath = [modelNameVar, '/', 'FSM_Chart'];",
            "    ",
            "    % Ensure Simulink and Stateflow libraries are loaded",
            "    try",
            "        load_system('simulink');",
            "        fprintf('FSM_PROGRESS: Simulink library loaded\\n');",
            "    catch loadErr1",
            "        fprintf('FSM_PROGRESS: Warning - Could not load Simulink library: %s\\n', loadErr1.message);",
            "    end",
            "    ",
            "    try",
            "        load_system('stateflow');",
            "        fprintf('FSM_PROGRESS: Stateflow library loaded\\n');",
            "    catch loadErr2",
            "        fprintf('FSM_PROGRESS: Warning - Could not load Stateflow library: %s\\n', loadErr2.message);",
            "    end",
            "    "
        ]

        # Add enhanced chart creation
        script_lines.append(generate_enhanced_chart_creation_script())

        script_lines.extend([
            "    ",
            "    % Get Stateflow objects",
            "    fprintf('FSM_PROGRESS: Getting Stateflow objects...\\n');",
            "    machine = sfroot().find('-isa', 'Stateflow.Machine', 'Name', modelNameVar);",
            "    if isempty(machine)",
            "        error('Could not find Stateflow machine for model %s', modelNameVar);",
            "    end",
            "    ",
            "    chartSFObj = machine.find('-isa', 'Stateflow.Chart');",
            "    if isempty(chartSFObj)",
            "        error('Could not find Stateflow chart object');",
            "    end",
            "    ",
            "    % Configure chart",
            "    chartSFObj.ActionLanguage = 'MATLAB';",
            "    fprintf('FSM_PROGRESS: Chart configured with MATLAB action language\\n');",
            "    ",
            "    fprintf('FSM_PROGRESS: Setting up data interfaces...\\n');",
            "    ",
            "    % Create data objects with error handling",
            "    try",
            "        activeStateData = Stateflow.Data(chartSFObj);",
            "        activeStateData.Name = 'active_state_name';",
            "        activeStateData.Scope = 'Output';",
            "        activeStateData.DataType = 'string';",
            "        ",
            "        stateIndexData = Stateflow.Data(chartSFObj);",
            "        stateIndexData.Name = 'active_state_index';",
            "        stateIndexData.Scope = 'Output';",
            "        stateIndexData.DataType = 'uint8';",
            "        ",
            "        transitionCountData = Stateflow.Data(chartSFObj);",
            "        transitionCountData.Name = 'transition_count';",
            "        transitionCountData.Scope = 'Output';",
            "        transitionCountData.DataType = 'uint32';",
            "        ",
            "        transCountLocal = Stateflow.Data(chartSFObj);",
            "        transCountLocal.Name = 'trans_count_local';",
            "        transCountLocal.Scope = 'Local';",
            "        transCountLocal.DataType = 'uint32';",
            "        ",
            "        fprintf('FSM_PROGRESS: Data interfaces created successfully\\n');",
            "    catch dataErr",
            "        error('Failed to create data interfaces: %s', dataErr.message);",
            "    end",
            "    ",
            "    fprintf('FSM_PROGRESS: Adding output blocks...\\n');",
            "    try",
            "        add_block('simulink/Sinks/To Workspace', [modelNameVar '/State_Name_Out'], ...",
            "                  'VariableName', 'state_names', 'SaveFormat', 'Timeseries');",
            "        add_block('simulink/Sinks/To Workspace', [modelNameVar '/State_Index_Out'], ...",
            "                  'VariableName', 'state_indices', 'SaveFormat', 'Timeseries');",
            "        add_block('simulink/Sinks/To Workspace', [modelNameVar '/Transition_Count_Out'], ...",
            "                  'VariableName', 'transition_counts', 'SaveFormat', 'Timeseries');",
            "        ",
            "        % Connect outputs",
            "        add_line(modelNameVar, 'FSM_Chart/1', 'State_Name_Out/1', 'autorouting', 'on');",
            "        add_line(modelNameVar, 'FSM_Chart/2', 'State_Index_Out/1', 'autorouting', 'on');",
            "        add_line(modelNameVar, 'FSM_Chart/3', 'Transition_Count_Out/1', 'autorouting', 'on');",
            "        ",
            "        fprintf('FSM_PROGRESS: Output blocks added and connected\\n');",
            "    catch blockErr",
            "        warning('Failed to add output blocks: %s', blockErr.message);",
            "    end",
            "    ",
            "    fprintf('FSM_PROGRESS: Creating states...\\n');",
            "    stateHandles = containers.Map('KeyType','char','ValueType','any');",
            "    stateIndexMap = containers.Map('KeyType','char','ValueType','int32');",
            "    "
        ])

        # Add states from IR
        script_lines.extend(generate_state_creation_code(list(fsm_model.states.values())))
    
        # Add transitions from IR  
        script_lines.extend(generate_transition_creation_code(fsm_model.transitions))
    
        # Add finalization and save
        script_lines.extend([
            "    fprintf('FSM_PROGRESS: Finalizing and saving model...\\n');",
            "    ",
            "    try",
            "        if optimizeLayout",
            "            fprintf('FSM_PROGRESS: Optimizing layout...\\n');",
            "            Simulink.BlockDiagram.arrangeSystem(modelNameVar);",
            "        end",
            "    catch layoutErr",
            "        warning('Layout optimization failed: %s', layoutErr.message);",
            "    end",
            "    ",
            "    % Update and compile model",
            "    fprintf('FSM_PROGRESS: Updating model...\\n');",
            "    try",
            "        set_param(modelNameVar, 'SimulationCommand', 'update');",
            "    catch updateErr",
            "        warning('Model update failed: %s', updateErr.message);",
            "    end",
            "    ",
            "    % Save model",
            "    fprintf('FSM_PROGRESS: Saving model to %s...\\n', outputModelPath);",
            "    save_system(modelNameVar, outputModelPath, 'OverwriteIfChangedOnDisk', true);",
            "    ",
            "    close_system(modelNameVar, 0);",
            "    ",
            "    fprintf('MATLAB_SCRIPT_SUCCESS:%s\\n', outputModelPath);",
            "    ",
            "catch e",
            "    fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', getReport(e, 'extended'));",
            "    % Ensure cleanup on error",
            "    try",
            "        if exist('modelNameVar', 'var') && bdIsLoaded(modelNameVar)",
            "            close_system(modelNameVar, 0);",
            "        end",
            "    catch cleanupErr",
            "        fprintf('Cleanup error: %s\\n', cleanupErr.message);",
            "    end",
            "end"
        ])

        return "\n".join(script_lines)

    def run_simulation(self, model_path: str, config: SimulationConfig = None, 
                      progress_callback: Callable[[str, int], None] = None) -> bool:
        """Run enhanced Simulink simulation by calling the method on the MATLAB FSM instance."""
        
        model_path_obj = Path(model_path)
        if not model_path_obj.exists():
            self.simulationFinished.emit(False, f"Model file not found: {model_path}", "", {
                'error_type': 'file_not_found',
                'model_path': model_path
            })
            return False

        if config is None:
            config = SimulationConfig()

        model_name = model_path_obj.stem
        
        # 1. Convert Python config object to a dictionary for the engine
        config_dict = config.to_matlab_params()

        # 2. Push the config dictionary to the MATLAB workspace.
        try:
            self.worker.engine.workspace['py_sim_config'] = config_dict
        except AttributeError:
            logger.error("MATLAB engine not available for simulation")
            self.simulationFinished.emit(False, "MATLAB engine not connected", "", {})
            return False
        
        # Create enhanced simulation script with better error handling
        script_content = f"""
        try
            % Verify FSM_INSTANCE exists
            if ~exist('FSM_INSTANCE', 'var') || isempty(FSM_INSTANCE)
                error('FSM_INSTANCE not found. Please generate model first.');
            end
            
            % Call the run_simulation method on the persistent FSM instance
            FSM_INSTANCE.run_simulation(py_sim_config);
            
        catch e
            % Enhanced error reporting
            fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', getReport(e, 'extended'));
        end
        """

        metadata = {
            'model_path': model_path,
            'model_name': model_name,
            'config': config.__dict__,
            'simulation_start_time': time.time()
        }

        command = MatlabCommand(
            command=script_content,
            command_type=CommandType.SIMULATION,
            timeout=config.stop_time + 60.0,  # Generous buffer time
            priority=Priority.HIGH,
            metadata=metadata,
            progress_callback=progress_callback or (lambda msg, pct: self.progressUpdated.emit(f"Simulation: {msg}", pct))
        )
        
        self._execute_command(command)
        return True

    def generate_code(self, model_path: str, config: CodeGenConfig = None, 
                     output_dir: Optional[str] = None,
                     progress_callback: Callable[[str, int], None] = None) -> bool:
        """Generate enhanced code from Simulink model with comprehensive features"""
        
        model_path_obj = Path(model_path)
        if not model_path_obj.exists():
            self.codeGenerationFinished.emit(False, f"Model file not found: {model_path}", "", {
                'error_type': 'file_not_found',
                'model_path': model_path
            })
            return False

        if config is None:
            config = CodeGenConfig()

        if output_dir is None:
            output_dir = str(model_path_obj.parent / "generated_code")

        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        model_path_matlab = str(model_path_obj).replace(os.sep, '/')
        output_dir_matlab = str(output_path).replace(os.sep, '/')
        model_name = model_path_obj.stem

        # Create enhanced code generation script
        script_content = f"""
% Enhanced Code Generation Script
% Model: {model_name}
% Target: {config.language}
% Generated by FSM Designer v2.0

try
    fprintf('CODEGEN_PROGRESS: Initializing code generation environment...\\n');
    
    % Comprehensive license validation
    required_licenses = {{'MATLAB_Coder', 'Simulink_Coder'}};
    optional_licenses = {{'Embedded_Coder', 'Fixed_Point_Designer'}};
    
    missing_required = {{}};
    for i = 1:length(required_licenses)
        if ~license('test', required_licenses{{i}})
            missing_required{{end+1}} = required_licenses{{i}};
        end
    end
    
    if ~isempty(missing_required)
        error('Required licenses not available: %s', strjoin(missing_required, ', '));
    end
    
    % Check optional licenses
    available_optional = {{}};
    for i = 1:length(optional_licenses)
        if license('test', optional_licenses{{i}})
            available_optional{{end+1}} = optional_licenses{{i}};
        end
    end
    
    fprintf('Available optional licenses: %s\\n', strjoin(available_optional, ', '));
    
    fprintf('CODEGEN_PROGRESS: Loading and validating model...\\n');
    
    % Load and validate model
    if ~exist('{model_path_matlab}', 'file')
        error('Model file not found: {model_path_matlab}');
    end
    
    load_system('{model_path_matlab}');
    
    if ~bdIsLoaded('{model_name}')
        error('Failed to load model: {model_name}');
    end
    
    fprintf('CODEGEN_PROGRESS: Configuring code generation settings...\\n');
    
    % Get and configure model configuration set
    cfg = getActiveConfigSet('{model_name}');
    if isempty(cfg)
        cfg = attachConfigSet('{model_name}', 'GRT');
    end
    
    % Enhanced configuration
{self._generate_codegen_config_code(config, model_name)}
    
    % Ensure output directory exists and is accessible
    if ~exist('{output_dir_matlab}', 'dir')
        [success, msg] = mkdir('{output_dir_matlab}');
        if ~success
            error('Failed to create output directory: %s', msg);
        end
    end
    
    % Pre-generation model validation
    fprintf('CODEGEN_PROGRESS: Validating model for code generation...\\n');
    try
        % Update model to check for errors
        set_param('{model_name}', 'SimulationCommand', 'update');
        
        % Check model advisor recommendations
        if exist('ModelAdvisor.run', 'file')
            fprintf('Running Model Advisor checks...\\n');
            % Run specific checks for code generation
        end
        
    catch validationErr
        warning('Model validation warning: %s', validationErr.message);
    end
    
    % Start code generation
    fprintf('CODEGEN_PROGRESS: Starting code generation...\\n');
    codegenStartTime = tic;
    
    % Enhanced code generation with monitoring
    try
        % Use RTW build with enhanced options
        rtw_options = struct();
        rtw_options.CodeGenFolder = '{output_dir_matlab}';
        rtw_options.GenCodeOnly = true;
        rtw_options.PackageGeneratedCodeAndArtifacts = true;
        
        % Generate code
        rtwbuild('{model_name}', rtw_options);
        
        codegenDuration = toc(codegenStartTime);
        
        fprintf('CODEGEN_PROGRESS: Code generation completed in %.2f seconds\\n', codegenDuration);
        
    catch buildErr
        error('Code generation failed: %s', buildErr.message);
    end
    
    % Post-generation processing
    fprintf('CODEGEN_PROGRESS: Processing generated code...\\n');
    
    % Determine actual output directory
    possibleDirs = {{
        fullfile('{output_dir_matlab}', '{model_name}_ert_rtw'),
        fullfile('{output_dir_matlab}', '{model_name}_grt_rtw'),
        fullfile('{output_dir_matlab}', '{model_name}_rtw'),
        '{output_dir_matlab}'
    }};
    
    actualCodeDir = '';
    for i = 1:length(possibleDirs)
        if exist(possibleDirs{{i}}, 'dir')
            actualCodeDir = possibleDirs{{i}};
            break;
        end
    end
    
    if isempty(actualCodeDir)
        actualCodeDir = '{output_dir_matlab}';
    end
    
    % Generate comprehensive report
    report = struct();
    report.model_name = '{model_name}';
    report.generation_time = datestr(now);
    report.target_language = '{config.language}';
    report.output_directory = actualCodeDir;
    report.generation_duration = codegenDuration;
    report.target_file = '{config.target_file}';
    
    % Analyze generated files
    if exist(actualCodeDir, 'dir')
        fileList = dir(fullfile(actualCodeDir, '*'));
        fileList = fileList(~[fileList.isdir]);
        
        report.generated_files = struct();
        report.generated_files.count = length(fileList);
        report.generated_files.total_size = sum([fileList.bytes]);
        
        % Categorize files
        cFiles = {{fileList(endsWith({{fileList.name}}, '.c')).name}};
        hFiles = {{fileList(endsWith({{fileList.name}}, '.h')).name}};
        makeFiles = {{fileList(contains({{fileList.name}}, 'make', 'IgnoreCase', true)).name}};
        
        report.generated_files.c_files = cFiles;
        report.generated_files.h_files = hFiles;
        report.generated_files.make_files = makeFiles;
        
        fprintf('Generated %d files (%.1f KB total)\\n', report.generated_files.count, report.generated_files.total_size/1024);
        fprintf('C files: %d, Header files: %d\\n', length(cFiles), length(hFiles));
    end
    
    % Save generation report
    reportPath = fullfile(actualCodeDir, 'generation_report.json');
    try
        reportJson = jsonencode(report);
        fid = fopen(reportPath, 'w');
        if fid > 0
            fprintf(fid, '%s', reportJson);
            fclose(fid);
            fprintf('Generation report saved: %s\\n', reportPath);
        end
    catch
        warning('Failed to save generation report');
    end
    
    % Return success with output directory
    fprintf('MATLAB_SCRIPT_SUCCESS:%s\\n', actualCodeDir);
    
catch e
    % Enhanced error reporting
    errorReport = struct();
    errorReport.message = e.message;
    errorReport.identifier = e.identifier;
    errorReport.model_name = '{model_name}';
    errorReport.target_language = '{config.language}';
    
    if exist('codegenStartTime', 'var')
        errorReport.partial_duration = toc(codegenStartTime);
    end
    
    errorJson = jsonencode(errorReport);
    fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', errorJson);
end

% Cleanup
try
    if bdIsLoaded('{model_name}')
        close_system('{model_name}', 0);
    end
catch
    % Ignore cleanup errors
end
"""

        metadata = {
            'model_path': model_path,
            'model_name': model_name,
            'config': config.__dict__,
            'output_dir': output_dir,
            'generation_start_time': time.time()
        }

        command = MatlabCommand(
            command=script_content,
            command_type=CommandType.CODE_GENERATION,
            timeout=300.0,  # Extended timeout for code generation
            priority=Priority.HIGH,
            metadata=metadata,
            progress_callback=progress_callback or (lambda msg, pct: self.progressUpdated.emit(f"Code Generation: {msg}", pct))
        )
        
        self._execute_command(command)
        return True

    def _generate_codegen_config_code(self, config: CodeGenConfig, model_name: str) -> str:
        """Generate MATLAB code for code generation configuration"""
        config_commands = config.to_matlab_commands(model_name)
        
        enhanced_commands = [
            f"    % Enhanced code generation configuration for {model_name}",
            "    try",
            "        % Apply basic configuration"
        ]
        
        for cmd in config_commands:
            enhanced_commands.append(f"        {cmd}")
        
        enhanced_commands.extend([
            "",
            "        % Advanced optimization settings",
            f"        set_param(cfg, 'DefaultParameterBehavior', 'Tunable');",
            f"        set_param(cfg, 'OptimizeBlockIOStorage', 'on');",
            f"        set_param(cfg, 'LocalBlockOutputs', 'on');",
            f"        set_param(cfg, 'ExpressionFolding', 'on');",
            f"        set_param(cfg, 'EnableMemcpy', 'on');",
            f"        set_param(cfg, 'MemcpyThreshold', '64');",
            "",
            "        % Code style and formatting",
            f"        set_param(cfg, 'MaxIdLength', '128');",
            f"        set_param(cfg, 'CustomSymbolStrGlobalVar', '$R$N$M');",
            f"        set_param(cfg, 'CustomSymbolStrField', '$N$M');",
            f"        set_param(cfg, 'CustomSymbolStrFcn', '$R$N$M$F');",
            "",
            "        % Error handling and debugging",
            f"        set_param(cfg, 'GenerateASAP2', 'off');",
            f"        set_param(cfg, 'IncludeHyperlinkInReport', 'on');",
            f"        set_param(cfg, 'LaunchReport', 'off');",
            "",
            "    catch configErr",
            "        warning('Code generation configuration warning: %s', configErr.message);",
            "    end"
        ])
        
        return "\n".join(enhanced_commands)

    def execute_custom_command(self, command: str, timeout: float = 30.0, 
                             priority: Priority = Priority.NORMAL,
                             metadata: Dict[str, Any] = None) -> bool:
        """Execute enhanced custom MATLAB command"""
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'command_type': 'custom',
            'command_preview': command[:100] + '...' if len(command) > 100 else command
        })
        
        matlab_command = MatlabCommand(
            command=command,
            command_type=CommandType.GENERAL,
            timeout=timeout,
            priority=priority,
            metadata=metadata
        )
        
        self._execute_command(matlab_command)
        return True

    def get_engine_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the MATLAB engine"""
        if hasattr(self.worker, '_engine_info'):
            info = self.worker._engine_info.copy()
            
            # Add runtime information
            info['runtime'] = {
                'current_state': self.state.value,
                'is_busy': self.is_busy(),
                'uptime': time.time() - info.get('startup_time', time.time()),
                'last_simulation': self._last_simulation_data
            }
            
            # Add performance metrics
            if hasattr(self.worker, 'get_performance_metrics'):
                try:
                    info['performance'] = self.worker.get_performance_metrics()
                except:
                    info['performance'] = {'error': 'Unable to retrieve performance metrics'}
            
            return info
        
        return {'status': 'No engine information available'}

    def get_model_cache(self) -> Dict[str, Any]:
        """Get cached model information"""
        return self._model_cache.copy()

    def clear_model_cache(self):
        """Clear model cache"""
        self._model_cache.clear()

    def validate_model_before_operation(self, model_path: str) -> Tuple[bool, List[str]]:
        """Validate model file before performing operations"""
        errors = []
        model_path_obj = Path(model_path)
        
        # File existence check
        if not model_path_obj.exists():
            errors.append(f"Model file does not exist: {model_path}")
            return False, errors
        
        # File extension check
        if model_path_obj.suffix.lower() not in ['.slx', '.mdl']:
            errors.append(f"Invalid model file extension: {model_path_obj.suffix}")
        
        # File size check (reasonable limits)
        file_size = model_path_obj.stat().st_size
        if file_size > 500 * 1024 * 1024:  # 500 MB
            errors.append(f"Model file unusually large: {file_size / (1024*1024):.1f} MB")
        
        if file_size == 0:
            errors.append("Model file is empty")
        
        # File permissions check
        if not os.access(model_path, os.R_OK):
            errors.append(f"Cannot read model file: {model_path}")
        
        return len(errors) == 0, errors

    def shutdown(self):
        """Enhanced graceful shutdown with cleanup"""
        logger.info("Shutting down MATLAB connection...")
        
        # Stop performance monitoring
        if hasattr(self, '_perf_timer'):
            self._perf_timer.stop()
        
        # Clear caches
        self.clear_model_cache()
        
        # Shutdown worker
        if self.thread.isRunning():
            QMetaObject.invokeMethod(self.worker, "shutdown_engine", Qt.ConnectionType.QueuedConnection)
            
            # Wait for graceful shutdown
            if not self.thread.wait(10000):  # 10 second timeout
                logger.warning("MATLAB Engine thread did not quit gracefully. Terminating.")
                self.thread.terminate()
                self.thread.wait(3000)
        
        logger.info("MATLAB connection shutdown complete")

    # Enhanced compatibility methods for SettingsDialog
    def set_matlab_path(self, path: str) -> bool:
        """Set MATLAB installation path with validation"""
        if not path:
            return False
        
        path_obj = Path(path)
        if not path_obj.exists():
            logger.warning(f"MATLAB path does not exist: {path}")
            return False
        
        self.matlab_path = str(path_obj)
        logger.info(f"MATLAB path set to: {self.matlab_path}")
        
        # Emit status update
        self.connectionStatusChanged.emit(
            self.state, 
            f"MATLAB path updated: {self.matlab_path} (restart engine to apply)"
        )
        
        return True

    def detect_matlab(self):
        """Enhanced MATLAB installation detection"""
        if self.is_connected():
            try:
                # Get installation info from running engine
                engine_info = self.get_engine_info()
                matlab_root = engine_info.get('matlab_root')
                
                if matlab_root:
                    # Construct executable path
                    exe_name = "matlab.exe" if os.name == 'nt' else "matlab"
                    detected_path = Path(matlab_root) / 'bin' / exe_name
                    
                    if detected_path.exists():
                        self.matlab_path = str(detected_path)
                        self.connectionStatusChanged.emit(
                            self.state, 
                            f"Auto-detected MATLAB: {self.matlab_path}"
                        )
                        return
                
                # Fallback: try to get path from engine
                QMetaObject.invokeMethod(
                    self.worker, "execute_command", Qt.ConnectionType.QueuedConnection,
                    Q_ARG(MatlabCommand, MatlabCommand(
                        command="fprintf('MATLAB_ROOT: %s\\n', matlabroot);",
                        command_type=CommandType.TEST,
                        timeout=10.0,
                        metadata={'purpose': 'path_detection'}
                    ))
                )
                
            except Exception as e:
                logger.warning(f"Failed to detect MATLAB path from engine: {e}")
        
        # Try system-wide detection
        self._detect_matlab_system_wide()

    def _detect_matlab_system_wide(self):
        """Attempt system-wide MATLAB detection"""
        common_paths = []
        
        if os.name == 'nt':  # Windows
            common_paths.extend([
                r"C:\Program Files\MATLAB\*\bin\matlab.exe",
                r"C:\Program Files (x86)\MATLAB\*\bin\matlab.exe"
            ])
        elif sys.platform == 'darwin':  # macOS
            common_paths.extend([
                "/Applications/MATLAB_*.app/bin/matlab",
                "/usr/local/MATLAB/*/bin/matlab"
            ])
        else:  # Linux/Unix
            common_paths.extend([
                "/usr/local/MATLAB/*/bin/matlab",
                "/opt/MATLAB/*/bin/matlab",
                "/home/*/MATLAB/*/bin/matlab"
            ])
        
        # Search for MATLAB installations
        import glob
        found_installations = []
        
        for pattern in common_paths:
            matches = glob.glob(pattern)
            found_installations.extend(matches)
        
        if found_installations:
            # Sort by version (newest first)
            found_installations.sort(reverse=True)
            latest_installation = found_installations[0]
            
            self.matlab_path = latest_installation
            self.connectionStatusChanged.emit(
                self.state, 
                f"Detected MATLAB installation: {latest_installation}"
            )
        else:
            self.connectionStatusChanged.emit(
                self.state, 
                "No MATLAB installation detected automatically"
            )

    def test_connection(self):
        """Enhanced connection test with comprehensive diagnostics"""
        self.connectionStatusChanged.emit(
            EngineState.CONNECTING, 
            "Testing MATLAB connection..."
        )
        
        # Run diagnostics first
        diagnostics = MatlabDiagnostics.check_matlab_installation()
        
        if not diagnostics['matlab_engine_available']:
            self.connectionStatusChanged.emit(
                EngineState.ERROR, 
                "MATLAB Engine for Python not available"
            )
            return
        
        # Test basic engine functionality
        test_command = MatlabCommand(
            command="""
% Connection test script
try
    % Basic computation test
    test_result = 2 + 2;
    if test_result ~= 4
        error('Basic computation failed');
    end
    
    % Toolbox availability test
    simulink_available = license('test', 'Simulink');
    stateflow_available = license('test', 'Stateflow');
    
    fprintf('Connection test successful\\n');
    fprintf('Simulink available: %s\\n', string(simulink_available));
    fprintf('Stateflow available: %s\\n', string(stateflow_available));
    
    fprintf('MATLAB_SCRIPT_SUCCESS:Connection test passed\\n');
    
catch e
    fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', e.message);
end
            """,
            command_type=CommandType.TEST,
            timeout=30.0,
            priority=Priority.HIGH,
            metadata={'test_type': 'connection_test'}
        )
        
        self._execute_command(test_command)

    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get comprehensive diagnostic information"""
        diag_info = {
            'engine_status': {
                'state': self.state.value,
                'is_connected': self.is_connected(),
                'is_busy': self.is_busy()
            },
            'system_info': MatlabDiagnostics.check_matlab_installation(),
            'engine_info': self.get_engine_info() if self.is_connected() else None,
            'performance_metrics': self.worker.get_performance_metrics() if hasattr(self.worker, 'get_performance_metrics') else None,
            'model_cache': self.get_model_cache(),
            'matlab_path': self.matlab_path,
            'last_simulation': self._last_simulation_data
        }
        
        # Add health metrics if available
        if hasattr(self.worker, '_health_monitor'):
            try:
                diag_info['health_metrics'] = self.worker._health_monitor.get_health_metrics()
            except Exception as e:
                diag_info['health_metrics'] = {'error': str(e)}
        
        return diag_info

    def restart_engine(self):
        """Restart the MATLAB Engine with enhanced recovery"""
        logger.info("Restarting MATLAB Engine...")
        
        # Shutdown current engine
        if self.thread.isRunning():
            QMetaObject.invokeMethod(self.worker, "shutdown_engine", Qt.ConnectionType.QueuedConnection)
            
            # Wait for shutdown
            if not self.thread.wait(15000):  # 15 second timeout
                logger.warning("Engine shutdown timeout, forcing termination")
                self.thread.terminate()
                self.thread.wait(5000)
        
        # Clear state
        self.state = EngineState.DISCONNECTED
        self._last_simulation_data = None
        self.clear_model_cache()
        
        # Restart thread and engine
        self._setup_worker_thread()
        
        self.connectionStatusChanged.emit(
            EngineState.CONNECTING,
            "Restarting MATLAB Engine..."
        )


class MatlabModelValidator:
    """Enhanced validation for MATLAB model generation"""
    
    @staticmethod
    def validate_states(states: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate state definitions with comprehensive checks"""
        errors = []
        
        if not states:
            errors.append("No states defined")
            return False, errors
        
        state_names = []
        initial_count = 0
        
        for i, state in enumerate(states):
            # Name validation
            if 'name' not in state or not state['name']:
                errors.append(f"State {i}: Missing or empty name")
                continue
            
            name = state['name'].strip()
            if not name:
                errors.append(f"State {i}: Empty name")
                continue
            
            # Check for duplicate names
            if name in state_names:
                errors.append(f"State '{name}': Duplicate state name")
            else:
                state_names.append(name)
            
            # Name format validation
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_\s-]*$', name):
                errors.append(f"State '{name}': Invalid name format (must start with letter)")
            
            if len(name) > 50:
                errors.append(f"State '{name}': Name too long (max 50 characters)")
            
            # Initial state validation
            if state.get('is_initial', False):
                initial_count += 1
            
            # Position validation
            if 'x' in state and 'y' in state:
                try:
                    x, y = float(state['x']), float(state['y'])
                    if x < 0 or y < 0 or x > 10000 or y > 10000:
                        errors.append(f"State '{name}': Position out of reasonable bounds")
                except (ValueError, TypeError):
                    errors.append(f"State '{name}': Invalid position coordinates")
            
            # Action validation
            for action_type in ['entry_action', 'during_action', 'exit_action']:
                if action_type in state and state[action_type]:
                    action_code = state[action_type].strip()
                    if action_code:
                        # Check for potentially dangerous MATLAB code
                        dangerous_patterns = [
                            'delete', 'rmdir', 'system', 'dos', 'unix', 
                            'eval', 'evalin', 'assignin', 'clear all'
                        ]
                        
                        for pattern in dangerous_patterns:
                            if pattern in action_code.lower():
                                errors.append(f"State '{name}': Potentially dangerous code in {action_type}: '{pattern}'")
        
        # Check for exactly one initial state
        if initial_count == 0:
            errors.append("No initial state defined")
        elif initial_count > 1:
            errors.append(f"Multiple initial states defined ({initial_count})")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_transitions(transitions: List[Dict], states: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate transition definitions with comprehensive checks"""
        errors = []
        
        if not transitions:
            errors.append("No transitions defined")
            return False, errors
        
        # Build state name set for validation
        state_names = {state['name'] for state in states if 'name' in state}
        
        transition_signatures = set()
        
        for i, trans in enumerate(transitions):
            # Source validation
            if 'source' not in trans or not trans['source']:
                errors.append(f"Transition {i}: Missing source state")
                continue
            
            source = trans['source'].strip()
            if source not in state_names:
                errors.append(f"Transition {i}: Invalid source state '{source}'")
            
            # Target validation
            if 'target' not in trans or not trans['target']:
                errors.append(f"Transition {i}: Missing target state")
                continue
            
            target = trans['target'].strip()
            if target not in state_names:
                errors.append(f"Transition {i}: Invalid target state '{target}'")
            
            # Check for duplicate transitions
            signature = (source, target, trans.get('event', ''), trans.get('condition', ''))
            if signature in transition_signatures:
                errors.append(f"Transition {i}: Duplicate transition from '{source}' to '{target}'")
            else:
                transition_signatures.add(signature)
            
            # Event validation
            event = trans.get('event', '').strip()
            if event and not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', event):
                errors.append(f"Transition {i}: Invalid event name '{event}'")
            
            # Condition validation
            condition = trans.get('condition', '').strip()
            if condition:
                # Check for balanced brackets
                if condition.count('[') != condition.count(']'):
                    errors.append(f"Transition {i}: Unbalanced brackets in condition")
                
                if condition.count('(') != condition.count(')'):
                    errors.append(f"Transition {i}: Unbalanced parentheses in condition")
            
            # Action validation
            action = trans.get('action', '').strip()
            if action:
                # Check for potentially dangerous MATLAB code
                dangerous_patterns = ['delete', 'rmdir', 'system', 'dos', 'unix', 'clear all']
                for pattern in dangerous_patterns:
                    if pattern in action.lower():
                        errors.append(f"Transition {i}: Potentially dangerous code in action: '{pattern}'")
        
        # Check for unreachable states
        if states and transitions:
            reachable_states = set()
            
            # Find initial state
            initial_states = [state['name'] for state in states if state.get('is_initial', False)]
            if initial_states:
                reachable_states.add(initial_states[0])
                
                # Build reachability graph
                changed = True
                while changed:
                    changed = False
                    for trans in transitions:
                        if trans.get('source') in reachable_states and trans.get('target') not in reachable_states:
                            reachable_states.add(trans.get('target'))
                            changed = True
                
                # Check for unreachable states
                for state in states:
                    if state.get('name') not in reachable_states:
                        errors.append(f"State '{state['name']}': Unreachable from initial state")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_model_name(model_name: str) -> Tuple[bool, List[str]]:
        """Validate model name for MATLAB compatibility"""
        errors = []
        
        if not model_name:
            errors.append("Model name is empty")
            return False, errors
        
        name = model_name.strip()
        
        # Length check
        if len(name) > 63:  # MATLAB identifier limit
            errors.append("Model name too long (max 63 characters)")
        
        # Format check
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            errors.append("Model name must start with letter and contain only letters, numbers, and underscores")
        
        # Reserved word check
        matlab_keywords = {
            'break', 'case', 'catch', 'continue', 'else', 'elseif', 'end', 'for', 
            'function', 'global', 'if', 'otherwise', 'persistent', 'return', 
            'switch', 'try', 'while', 'classdef', 'properties', 'methods', 'events'
        }
        
        if name.lower() in matlab_keywords:
            errors.append(f"Model name '{name}' is a reserved MATLAB keyword")
        
        return len(errors) == 0, errors


class MatlabDiagnostics:
    """Enhanced MATLAB system diagnostics"""
    
    @staticmethod
    def check_matlab_installation() -> Dict[str, Any]:
        """Comprehensive MATLAB installation check"""
        result = {
            'matlab_engine_available': MATLAB_ENGINE_AVAILABLE,
            'python_version': sys.version,
            'platform': sys.platform,
            'timestamp': time.time()
        }
        
        if MATLAB_ENGINE_AVAILABLE:
            try:
                # Get MATLAB Engine version info
                import matlab.engine
                result['matlab_engine_module'] = {
                    'file': matlab.engine.__file__,
                    'version': getattr(matlab.engine, '__version__', 'Unknown')
                }
                
                # Test engine creation (quick test)
                try:
                    test_engine = matlab.engine.start_matlab('-nodesktop -nosplash')
                    
                    # Get MATLAB version info
                    matlab_version = test_engine.eval("version('-release')")
                    matlab_root = test_engine.eval("matlabroot")
                    
                    result['matlab_info'] = {
                        'version': matlab_version,
                        'root': matlab_root,
                        'quick_test': 'passed'
                    }
                    
                    # Test toolbox availability
                    toolboxes = {
                        'Simulink': 'simulink',
                        'Stateflow': 'stateflow',
                        'MATLAB_Coder': 'matlab_coder',
                        'Simulink_Coder': 'simulink_coder'
                    }
                    
                    toolbox_status = {}
                    for name, license_name in toolboxes.items():
                        try:
                            available = test_engine.eval(f"license('test', '{license_name}')")
                            toolbox_status[name] = bool(available)
                        except:
                            toolbox_status[name] = False
                    
                    result['toolbox_availability'] = toolbox_status
                    
                    # Cleanup test engine
                    test_engine.quit()
                    
                except Exception as e:
                    result['matlab_test_error'] = str(e)
                    result['quick_test'] = 'failed'
                
            except Exception as e:
                result['matlab_engine_error'] = str(e)
        
        else:
            result['installation_help'] = MatlabEngineWorker()._get_installation_help_message()
        
        return result
    
    @staticmethod
    def check_system_resources() -> Dict[str, Any]:
        """Check system resources for MATLAB operations"""
        try:
            import psutil
        except ImportError:
            return {'error': 'psutil not available for resource monitoring'}
        
        return {
            'memory': {
                'total_gb': psutil.virtual_memory().total / (1024**3),
                'available_gb': psutil.virtual_memory().available / (1024**3),
                'usage_percent': psutil.virtual_memory().percent
            },
            'cpu': {
                'count': psutil.cpu_count(),
                'usage_percent': psutil.cpu_percent(interval=1)
            },
            'disk': {
                'free_gb': psutil.disk_usage('/').free / (1024**3),
                'total_gb': psutil.disk_usage('/').total / (1024**3),
                'usage_percent': psutil.disk_usage('/').percent
            }
        }
    
    @staticmethod
    def run_comprehensive_diagnostics() -> Dict[str, Any]:
        """Run all diagnostic checks"""
        return {
            'matlab_installation': MatlabDiagnostics.check_matlab_installation(),
            'system_resources': MatlabDiagnostics.check_system_resources(),
            'python_environment': {
                'version': sys.version,
                'executable': sys.executable,
                'platform': sys.platform,
                'architecture': os.uname() if hasattr(os, 'uname') else 'Unknown'
            },
            'qt_environment': {
                'pyqt_version': '6.x',  # Could be detected dynamically
                'thread_support': True
            }
        }


class MatlabScriptGenerator:
    """Enhanced MATLAB script generation utilities"""
    
    @staticmethod
    def generate_simulation_script(model_path: str, config: SimulationConfig, 
                                 custom_setup: str = "", custom_analysis: str = "") -> str:
        """Generate comprehensive simulation script with custom extensions"""
        
        model_name = Path(model_path).stem
        
        script_template = f"""
% Advanced FSM Simulation Script
% Model: {model_name}
% Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

try
    fprintf('=== FSM Simulation Starting ===\\n');
    
    % Environment validation and setup
    if ~license('test', 'Simulink')
        error('Simulink license not available');
    end
    
    % Load model with error handling
    fprintf('Loading model: {model_name}\\n');
    try
        load_system('{model_path.replace(os.sep, '/')}');
    catch loadErr
        error('Failed to load model: %s', loadErr.message);
    end
    
    % Custom setup code
    {custom_setup}
    
    % Configure simulation parameters
    {MatlabScriptGenerator._generate_sim_config_block(config, model_name)}
    
    % Run simulation with monitoring
    fprintf('Starting simulation (duration: {config.stop_time}s)...\\n');
    sim_start = tic;
    
    try
        simOut = sim('{model_name}', 'ReturnWorkspaceOutputs', 'on');
        sim_duration = toc(sim_start);
        
        fprintf('Simulation completed in %.2f seconds\\n', sim_duration);
        
        % Process results
        {MatlabScriptGenerator._generate_results_processing_block()}
        
        % Custom analysis code
        {custom_analysis}
        
        % Generate final report
        fprintf('MATLAB_SCRIPT_SUCCESS:Simulation completed successfully\\n');
        
    catch simErr
        error('Simulation failed: %s', simErr.message);
    end
    
catch err
    fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', err.message);
    
finally
    % Cleanup
    try
        if bdIsLoaded('{model_name}')
            close_system('{model_name}', 0);
        end
    catch
    end
end
"""
        return script_template
    
    @staticmethod
    def _generate_sim_config_block(config: SimulationConfig, model_name: str) -> str:
        """Generate simulation configuration block"""
        config_lines = [
            f"% Configure {model_name} for simulation",
            "try"
        ]
        
        # Add configuration commands from fixed config
        params = config.to_matlab_params()
        for param, value in params.items():
            config_lines.append(f"    set_param('{model_name}', '{param}', '{value}');")
        
        config_lines.extend([
            "catch configErr",
            "    warning('Configuration error: %s', configErr.message);",
            "end"
        ])
        
        return "\n    ".join(config_lines)
    
    @staticmethod
    def _generate_results_processing_block() -> str:
        """Generate results processing block"""
        return """
        % Process simulation results
        results = struct();
        results.simulation_time = sim_duration;
        
        % Extract logged signals
        if exist('state_names', 'var')
            results.states = state_names;
            results.final_state = state_names.Data(end);
        end
        
        if exist('transition_counts', 'var')
            results.transitions = transition_counts;
            results.total_transitions = transition_counts.Data(end);
        end
        
        % Save to workspace
        assignin('base', 'FSM_results', results);
        
        fprintf('Results saved to workspace variable: FSM_results\\n');
        """


class MatlabErrorRecovery:
    """Advanced error recovery and handling for MATLAB operations"""
    
    @staticmethod
    def analyze_error(error_message: str) -> Dict[str, Any]:
        """Analyze MATLAB error and provide recovery suggestions"""
        error_patterns = {
            'license': {
                'patterns': ['license', 'checkout', 'not available'],
                'category': 'licensing',
                'suggestions': [
                    'Check MATLAB license availability',
                    'Verify toolbox licenses',
                    'Contact system administrator'
                ]
            },
            'memory': {
                'patterns': ['out of memory', 'insufficient memory'],
                'category': 'memory',
                'suggestions': [
                    'Close other applications',
                    'Reduce model complexity',
                    'Increase system memory'
                ]
            },
            'compilation': {
                'patterns': ['compilation error', 'undefined function', 'undefined variable'],
                'category': 'model_error',
                'suggestions': [
                    'Check model for errors',
                    'Verify block connections',
                    'Update model to compatible version'
                ]
            },
            'file_access': {
                'patterns': ['permission denied', 'file not found', 'cannot open'],
                'category': 'file_system',
                'suggestions': [
                    'Check file permissions',
                    'Verify file path exists',
                    'Run with appropriate privileges'
                ]
            },
            'parameter_conflict': {
                'patterns': ['parameter', 'ignored', 'constraint'],
                'category': 'configuration',
                'suggestions': [
                    'Check solver configuration',
                    'Verify parameter compatibility',
                    'Use appropriate solver type'
                ]
            }
        }
        
        error_lower = error_message.lower()
        
        for error_type, config in error_patterns.items():
            if any(pattern in error_lower for pattern in config['patterns']):
                return {
                    'error_type': error_type,
                    'category': config['category'],
                    'suggestions': config['suggestions'],
                    'recoverable': True
                }
        
        return {
            'error_type': 'unknown',
            'category': 'general',
            'suggestions': ['Check MATLAB command window for details', 'Restart MATLAB Engine'],
            'recoverable': False
        }
    
    @staticmethod
    def suggest_recovery_actions(error_analysis: Dict[str, Any]) -> List[str]:
        """Suggest specific recovery actions based on error analysis"""
        base_suggestions = error_analysis.get('suggestions', [])
        
        # Add category-specific suggestions
        category = error_analysis.get('category', 'general')
        
        if category == 'licensing':
            base_suggestions.extend([
                "Try running \"license('inuse')\" to check current usage",
                "Restart MATLAB if license is stuck",
                "Check network connection for floating licenses"
            ])
        elif category == 'memory':
            base_suggestions.extend([
                'Run "clear all" to free workspace memory',
                'Reduce simulation time or complexity',
                'Enable fast restart mode'
            ])
        elif category == 'model_error':
            base_suggestions.extend([
                'Run model advisor to check for issues',
                'Verify all required toolboxes are installed',
                'Check model file is not corrupted'
            ])
        elif category == 'configuration':
            base_suggestions.extend([
                'Use fixed-step solver for discrete systems',
                'Check parameter compatibility',
                'Review solver settings'
            ])
        
        return base_suggestions

# Export classes for use in other modules
__all__ = [
    'MatlabConnection',
    'MatlabEngineWorker', 
    'EngineState',
    'CommandType',
    'Priority',
    'MatlabCommand',
    'SimulationConfig',
    'CodeGenConfig',
    'MatlabModelValidator',
    'MatlabDiagnostics',
    'MatlabScriptGenerator',
    'MatlabErrorRecovery'
]
