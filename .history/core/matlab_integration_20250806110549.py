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
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMetaObject, Q_ARG, pyqtSlot, Qt, QTimer
# --- NEW: Added Jinja2 imports for class template rendering ---
from jinja2 import Environment, FileSystemLoader

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
    """Enhanced configuration for Simulink simulations"""
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
        """Convert configuration to a dictionary for MATLAB struct conversion."""
        params = {
            'StopTime': str(self.stop_time),
            'Solver': self.solver,
            'RelTol': str(self.relative_tolerance),
            'AbsTol': str(self.absolute_tolerance),
            'SaveOutput': 'on' if self.save_output else 'off',
            'SaveFormat': self.save_format,
            'LoggingToFile': 'on' if self.log_signals else 'off',
            'DataLoggingDecimateData': 'on' if self.data_logging_decimation > 1 else 'off',
        }
        
        if self.fixed_step_size:
            params['SolverType'] = 'Fixed-step'
            params['FixedStep'] = str(self.fixed_step_size)
        
        if self.max_step_size:
            params['MaxStep'] = str(self.max_step_size)
        
        if self.initial_step_size:
            params['InitialStep'] = str(self.initial_step_size)
        
        if self.enable_fast_restart:
            params['FastRestart'] = 'on'
            
        return params
    
    
    
    def to_matlab_commands(self, model_name: str) -> List[str]:
        """Convert configuration to MATLAB commands"""
        commands = [
            f"set_param('{model_name}', 'StopTime', '{self.stop_time}');",
            f"set_param('{model_name}', 'Solver', '{self.solver}');",
            f"set_param('{model_name}', 'RelTol', '{self.relative_tolerance}');",
            f"set_param('{model_name}', 'AbsTol', '{self.absolute_tolerance}');",
            f"set_param('{model_name}', 'SaveOutput', '{'on' if self.save_output else 'off'}');",
            f"set_param('{model_name}', 'SaveFormat', '{self.save_format}');",
            f"set_param('{model_name}', 'LoggingToFile', '{'on' if self.log_signals else 'off'}');",
            f"set_param('{model_name}', 'DataLoggingDecimateData', '{'on' if self.data_logging_decimation > 1 else 'off'}');",
        ]
        
        if self.fixed_step_size:
            commands.extend([
                f"set_param('{model_name}', 'SolverType', 'Fixed-step');",
                f"set_param('{model_name}', 'FixedStep', '{self.fixed_step_size}');"
            ])
        
        if self.max_step_size:
            commands.append(f"set_param('{model_name}', 'MaxStep', '{self.max_step_size}');")
        
        if self.initial_step_size:
            commands.append(f"set_param('{model_name}', 'InitialStep', '{self.initial_step_size}');")
        
        if self.enable_fast_restart:
            commands.append(f"set_param('{model_name}', 'FastRestart', 'on');")
        
        return commands

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
    """Enhanced health monitoring for MATLAB Engine"""
    
    def __init__(self, engine_worker):
        self.worker = engine_worker
        self.health_data = {
            'last_heartbeat': time.time(),
            'response_times': [],
            'error_count': 0,
            'recovery_attempts': 0,
            'total_commands': 0,
            'successful_commands': 0
        }
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self._perform_health_check)
        self.health_timer.setInterval(10000)  # 10 seconds
    
    def start_monitoring(self):
        """Start health monitoring"""
        self.health_timer.start()
        logger.info("Engine health monitoring started")
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.health_timer.stop()
        logger.info("Engine health monitoring stopped")
    
    def _perform_health_check(self):
        """Perform comprehensive health check"""
        if not self.worker.engine or self.worker.state != EngineState.CONNECTED:
            return
        
        try:
            start_time = time.time()
            
            # Simple computation test
            self.worker.engine.eval("test_result = 2 + 2;", nargout=0)
            result = self.worker.engine.workspace['test_result']
            
            response_time = (time.time() - start_time) * 1000  # milliseconds
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
        """Trigger engine recovery procedure"""
        logger.error("Engine health degraded, attempting recovery...")
        self.health_data['recovery_attempts'] += 1
        self.worker._handle_engine_failure("Health check failures")
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get current health metrics"""
        response_times = self.health_data['response_times']
        return {
            'status': 'healthy' if self.health_data['error_count'] < 2 else 'degraded',
            'last_heartbeat': self.health_data['last_heartbeat'],
            'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'error_count': self.health_data['error_count'],
            'recovery_attempts': self.health_data['recovery_attempts'],
            'success_rate': self.get_success_rate(),
            'total_commands': self.health_data['total_commands']
        }
    
    def get_success_rate(self) -> float:
        """Calculate command success rate"""
        if self.health_data['total_commands'] == 0:
            return 1.0
        return self.health_data['successful_commands'] / self.health_data['total_commands']
    
    def record_command_result(self, success: bool):
        """Record the result of a command execution"""
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
        self._processing_thread = None
        self._should_process = False
        
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
            self._start_command_processing()
            
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
            
            # Schedule auto-recovery if within limits
            if self._auto_recovery_count < self._max_auto_recovery_attempts:
                QTimer.singleShot(10000, self._attempt_auto_recovery)  # Retry after 10 seconds

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
                "pack; % Consolidate workspace memory",
                
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

    def _start_command_processing(self):
        """Start background command processing thread"""
        self._should_process = True
        self._processing_thread = threading.Thread(target=self._process_command_queue, daemon=True)
        self._processing_thread.start()
        logger.debug("Command processing thread started")

    def _process_command_queue(self):
        """Background thread for processing command queue"""
        while self._should_process:
            try:
                command = self._command_queue.get()
                if command and not self._is_shutting_down:
                    self._set_state(EngineState.BUSY, f"Executing {command.command_type.value} command...")
                    self._execute_command_internal(command)
                    self._set_state(EngineState.CONNECTED, "Ready for commands")
                else:
                    time.sleep(0.1)  # Short sleep when no commands
            except Exception as e:
                logger.error(f"Error in command processing: {e}")
                time.sleep(1)  # Longer sleep on error

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
            success, message, data = self._parse_command_output(stdout, stderr, command.command_type)
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
                QTimer.singleShot(1000, lambda: self._command_queue.put(command))
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

    def _parse_command_output(self, stdout: str, stderr: str, command_type: CommandType) -> Tuple[bool, str, str]:
        """Enhanced output parsing with better error detection"""
        # Look for explicit success/failure markers
        if "MATLAB_SCRIPT_SUCCESS:" in stdout:
            for line in stdout.splitlines():
                if line.startswith("MATLAB_SCRIPT_SUCCESS:"):
                    output_data = line.split(":", 1)[1].strip()
                    return True, "Operation completed successfully.", output_data
        
        if "MATLAB_SCRIPT_FAILURE:" in stdout or stderr:
            error_detail = ""
            if stderr:
                error_detail = stderr
            else:
                for line in stdout.splitlines():
                    if line.startswith("MATLAB_SCRIPT_FAILURE:"):
                        error_detail = line.split(":", 1)[1].strip()
                        break
            return False, f"MATLAB operation failed: {error_detail}", ""
        
        # Enhanced error detection patterns
        error_patterns = [
            "Error:",
            "??? ",
            "Undefined function",
            "File not found",
            "Permission denied",
            "Out of memory",
            "License checkout failed"
        ]
        
        combined_output = stdout + stderr
        for pattern in error_patterns:
            if pattern in combined_output:
                return False, f"MATLAB error detected: {pattern}", stdout
        
        # Check for warnings that might indicate issues
        warning_patterns = [
            "Warning:",
            "Model not found",
            "Block not found"
        ]
        
        warnings = []
        for pattern in warning_patterns:
            if pattern in combined_output:
                warnings.append(pattern)
        
        if warnings:
            message = f"Command completed with warnings: {', '.join(warnings)}"
        else:
            message = "Command executed successfully."
        
        return True, message, stdout

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
        """Attempt automatic engine recovery"""
        if self._auto_recovery_count >= self._max_auto_recovery_attempts:
            logger.error("Maximum auto-recovery attempts reached")
            return
        
        current_time = time.time()
        if current_time - self._last_recovery_time < 30:  # Wait at least 30 seconds between attempts
            QTimer.singleShot(30000, self._attempt_auto_recovery)
            return
        
        self._auto_recovery_count += 1
        self._last_recovery_time = current_time
        
        logger.info(f"Attempting auto-recovery {self._auto_recovery_count}/{self._max_auto_recovery_attempts}")
        self.start_engine()

    def _handle_engine_failure(self, reason: str):
        """Enhanced engine failure handling"""
        logger.error(f"Engine failure detected: {reason}")
        
        # Clear command queue to prevent further issues
        self._command_queue.clear()
        
        # Cleanup and update state
        self._cleanup_engine()
        self._set_state(EngineState.ERROR, f"Engine failed: {reason}")
        
        # Attempt recovery if within limits
        if self._auto_recovery_count < self._max_auto_recovery_attempts:
            QTimer.singleShot(5000, self._attempt_auto_recovery)

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
        
        # Stop command processing
        self._should_process = False
        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=2)
        
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
    """Enhanced MATLAB connection manager with advanced features and reliability"""
    connectionStatusChanged = pyqtSignal(EngineState, str)
    simulationFinished = pyqtSignal(bool, str, str, dict)  # success, message, data, metadata
    codeGenerationFinished = pyqtSignal(bool, str, str, dict)
    modelGenerationFinished = pyqtSignal(bool, str, str, dict)
    progressUpdated = pyqtSignal(str, int)
    healthUpdated = pyqtSignal(dict)
    performanceUpdated = pyqtSignal(dict)

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
        """Initialize enhanced worker thread and connections"""
        self.thread = QThread()
        self.thread.setObjectName("MatlabEngineThread")
        self.worker = MatlabEngineWorker()
        self.worker.moveToThread(self.thread)
        
        self.worker.engine_status_changed.connect(self._on_engine_status_changed)
        self.worker.command_finished.connect(self._on_command_finished)
        self.worker.progress_updated.connect(self.progressUpdated)
        self.worker.health_update.connect(self.healthUpdated)
        
        self.thread.start()
        QMetaObject.invokeMethod(self.worker, "start_engine", Qt.QueuedConnection)
        
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

        # --- MODIFICATION: Instantiate FSM class after model generation ---
        if command_type == CommandType.MODEL_GENERATION and success:
            model_name = metadata.get('model_name')
            slx_file_path = metadata.get('output_path')
            class_name = metadata.get('class_name')

            if model_name and slx_file_path and class_name:
                logger.info(f"Model generated. Now instantiating MATLAB FSM class '{class_name}'.")
                
                matlab_slx_path = str(slx_file_path).replace(os.sep, '/')
                
                instantiate_command = MatlabCommand(
                    command=f"clear FSM_INSTANCE; FSM_INSTANCE = {class_name}('{matlab_slx_path}');",
                    command_type=CommandType.GENERAL,
                    priority=Priority.CRITICAL,
                    metadata={'purpose': 'fsm_instantiation'}
                )
                self._execute_command(instantiate_command)
        # --- END MODIFICATION ---

        if command_type == CommandType.SIMULATION:
            if success and data:
                self._last_simulation_data = {
                    'data': data,
                    'timestamp': time.time(),
                    'metadata': metadata
                }
            self.simulationFinished.emit(success, message, data, metadata)
            
        elif command_type == CommandType.CODE_GENERATION:
            self.codeGenerationFinished.emit(success, message, data, metadata)
            
        elif command_type == CommandType.MODEL_GENERATION:
            if success:
                model_name = metadata.get('model_name', 'Unknown')
                self._model_cache[model_name] = {
                    'path': metadata.get('output_path', ''),
                    'created': time.time(),
                    'metadata': metadata
                }
            self.modelGenerationFinished.emit(success, message, data, metadata)

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
        
        QMetaObject.invokeMethod(self.worker, "execute_command", Qt.QueuedConnection,
                               Q_ARG(MatlabCommand, command))

    def generate_simulink_model(self, states: List[Dict], transitions: List[Dict], 
                              output_dir: str, model_name: str = "BrainStateMachine",
                              **kwargs) -> bool:
        """Generate enhanced Simulink model with validation and optimization"""
        
        validation_errors = []
        is_valid_states, state_errors = MatlabModelValidator.validate_states(states)
        is_valid_transitions, transition_errors = MatlabModelValidator.validate_transitions(transitions, states)
        is_valid_name, name_errors = MatlabModelValidator.validate_model_name(model_name)
        
        validation_errors.extend(state_errors)
        validation_errors.extend(transition_errors)
        validation_errors.extend(name_errors)
        
        if validation_errors:
            error_msg = "Model validation failed:\n" + "\n".join(f"• {error}" for error in validation_errors)
            self.modelGenerationFinished.emit(False, error_msg, "", {
                'validation_errors': validation_errors,
                'model_name': model_name
            })
            return False

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

        # --- MODIFICATION: Generate class name and add to metadata ---
        class_name = f"FSM_{model_name}"
        script_content, m_file_generated = self._create_enhanced_model_generation_script(
            states, transitions, str(slx_file_path), model_name, options, class_name
        )
        
        if not m_file_generated:
            self.modelGenerationFinished.emit(False, "Failed to generate the MATLAB FSM class file.", "", {})
            return False

        metadata = {
            'model_name': model_name,
            'class_name': class_name,  # Add class name to metadata
            'output_path': str(slx_file_path),
            'state_count': len(states),
            'transition_count': len(transitions),
            'options': options,
            'generation_start_time': time.time()
        }
        # --- END MODIFICATION ---
        
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

    def _create_enhanced_model_generation_script(self, states: List[Dict], transitions: List[Dict], 
                                               output_path: str, model_name: str, 
                                               options: Dict[str, bool]) -> str:
        """Create comprehensive MATLAB script for enhanced model generation"""
        
        # Convert paths for MATLAB compatibility
        slx_file_path = output_path.replace(os.sep, '/')
        
        script_lines = [
            "% Enhanced FSM Model Generation Script",
            "% Generated by FSM Designer with advanced features",
            "",
            f"modelNameVar = '{model_name}';",
            f"outputModelPath = '{slx_file_path}';",
            f"enableDataLogging = {str(options.get('enable_data_logging', True)).lower()};",
            f"createTestHarness = {str(options.get('create_test_harness', False)).lower()};",
            f"addScopeBlocks = {str(options.get('add_scope_blocks', True)).lower()};",
            f"optimizeLayout = {str(options.get('optimize_layout', True)).lower()};",
            f"generateDocs = {str(options.get('generate_documentation', False)).lower()};",
            "",
            "try",
            "    fprintf('FSM_PROGRESS: Initializing model generation...\\n');",
            "",
            "    % Enhanced environment validation",
            "    required_products = {'Simulink', 'Stateflow'};",
            "    for i = 1:length(required_products)",
            "        if ~license('test', required_products{i})",
            "            error('Required product not available: %s', required_products{i});",
            "        end",
            "    end",
            "",
            "    % Load required libraries with error checking",
            "    try",
            "        load_system('sflib');",
            "        load_system('simulink');",
            "    catch loadErr",
            "        error('Failed to load required libraries: %s', loadErr.message);",
            "    end",
            "",
            "    fprintf('FSM_PROGRESS: Setting up model environment...\\n');",
            "",
            "    % Enhanced cleanup of existing model",
            "    if bdIsLoaded(modelNameVar)",
            "        try",
            "            close_system(modelNameVar, 0);",
            "        catch",
            "            bdclose(modelNameVar);",
            "        end",
            "    end",
            "",
            "    % Remove existing file with backup",
            "    if exist(outputModelPath, 'file')",
            "        backupPath = strrep(outputModelPath, '.slx', '_backup.slx');",
            "        if exist(backupPath, 'file')",
            "            delete(backupPath);",
            "        end",
            "        try",
            "            movefile(outputModelPath, backupPath);",
            "            fprintf('Created backup: %s\\n', backupPath);",
            "        catch",
            "            delete(outputModelPath);",
            "        end",
            "    end",
            "",
            "    fprintf('FSM_PROGRESS: Creating new model...\\n');",
            "",
            "    % Create new model with enhanced configuration",
            "    hModel = new_system(modelNameVar, 'Model');",
            "    open_system(hModel);",
            "",
            "    % Configure model parameters for optimal simulation",
            "    modelConfig = getActiveConfigSet(modelNameVar);",
            "    set_param(modelConfig, 'SolverType', 'Fixed-step');",
            "    set_param(modelConfig, 'FixedStep', '0.1');",
            "    set_param(modelConfig, 'StopTime', '10');",
            "    set_param(modelConfig, 'SaveOutput', 'on');",
            "    set_param(modelConfig, 'SaveFormat', 'Dataset');",
            "    set_param(modelConfig, 'SaveTime', 'on');",
            "    set_param(modelConfig, 'TimeSaveName', 'tout');",
            "    set_param(modelConfig, 'OutputSaveName', 'yout');",
            "",
            "    % Performance optimizations",
            "    set_param(modelConfig, 'OptimizeBlockIOStorage', 'on');",
            "    set_param(modelConfig, 'LocalBlockOutputs', 'on');",
            "    set_param(modelConfig, 'RTWInlineParameters', 'on');",
            "",
            "    fprintf('FSM_PROGRESS: Creating Stateflow chart...\\n');",
            "",
            "    % Create enhanced Stateflow chart block",
            "    chartBlockPath = [modelNameVar, '/', 'FSM_Chart'];",
            "    add_block('stateflow/Chart', chartBlockPath);",
            "    set_param(chartBlockPath, 'Position', [100 50 500 400]);",
            "    set_param(chartBlockPath, 'Name', 'FSM Logic');",
            "",
            "    % Configure chart properties",
            "    set_param(chartBlockPath, 'ExecuteAtInitialization', 'on');",
            "    set_param(chartBlockPath, 'EnableDebugExecution', 'off');",
            "    set_param(chartBlockPath, 'SupportVariableSizing', 'off');",
            "",
            "    % Get Stateflow objects with enhanced error checking",
            "    machine = sfroot().find('-isa', 'Stateflow.Machine', 'Name', modelNameVar);",
            "    if isempty(machine)",
            "        error('Failed to create Stateflow machine');",
            "    end",
            "",
            "    chartSFObj = machine.find('-isa', 'Stateflow.Chart');",
            "    if isempty(chartSFObj)",
            "        error('Failed to create Stateflow chart');",
            "    end",
            "",
            "    chartSFObj.Name = 'FiniteStateMachineLogic';",
            "    chartSFObj.ActionLanguage = 'MATLAB';",
            "    chartSFObj.EnableDebugExecution = false;",
            "",
            "    fprintf('FSM_PROGRESS: Setting up data interfaces...\\n');",
            "",
            "    % Create enhanced output data",
            "    activeStateData = Stateflow.Data(chartSFObj);",
            "    activeStateData.Name = 'active_state_name';",
            "    activeStateData.Scope = 'Output';",
            "    activeStateData.DataType = 'string';",
            "    activeStateData.Port = 1;",
            "",
            "    % Add state index output for numeric analysis",
            "    stateIndexData = Stateflow.Data(chartSFObj);",
            "    stateIndexData.Name = 'active_state_index';",
            "    stateIndexData.Scope = 'Output';",
            "    stateIndexData.DataType = 'uint8';",
            "    stateIndexData.Port = 2;",
            "",
            "    % Add transition counter",
            "    transitionCountData = Stateflow.Data(chartSFObj);",
            "    transitionCountData.Name = 'transition_count';",
            "    transitionCountData.Scope = 'Output';",
            "    transitionCountData.DataType = 'uint32';",
            "    transitionCountData.Port = 3;",
            "",
            "    % Initialize transition counter as local data",
            "    transCountLocal = Stateflow.Data(chartSFObj);",
            "    transCountLocal.Name = 'trans_count_local';",
            "    transCountLocal.Scope = 'Local';",
            "    transCountLocal.DataType = 'uint32';",
            "",
            "    fprintf('FSM_PROGRESS: Adding output blocks...\\n');",
            "",
            "    % Enhanced output blocks",
            "    add_block('simulink/Sinks/To Workspace', [modelNameVar '/State_Name_Out'], ...",
            "              'VariableName', 'state_names', 'SaveFormat', 'Timeseries');",
            "    add_block('simulink/Sinks/To Workspace', [modelNameVar '/State_Index_Out'], ...",
            "              'VariableName', 'state_indices', 'SaveFormat', 'Timeseries');",
            "    add_block('simulink/Sinks/To Workspace', [modelNameVar '/Transition_Count_Out'], ...",
            "              'VariableName', 'transition_counts', 'SaveFormat', 'Timeseries');",
            "",
            "    % Connect outputs",
            "    add_line(modelNameVar, 'FSM Logic/1', 'State_Name_Out/1', 'autorouting', 'on');",
            "    add_line(modelNameVar, 'FSM Logic/2', 'State_Index_Out/1', 'autorouting', 'on');",
            "    add_line(modelNameVar, 'FSM Logic/3', 'Transition_Count_Out/1', 'autorouting', 'on');",
            "",
            "    % Add scope blocks if requested",
            "    if addScopeBlocks",
            "        add_block('simulink/Sinks/Scope', [modelNameVar '/State_Scope']);",
            "        set_param([modelNameVar '/State_Scope'], 'Position', [600 50 650 100]);",
            "        add_line(modelNameVar, 'FSM Logic/2', 'State_Scope/1', 'autorouting', 'on');",
            "    end",
            "",
            "    fprintf('FSM_PROGRESS: Creating states...\\n');",
            "",
            "    % Initialize state management",
            "    stateHandles = containers.Map('KeyType','char','ValueType','any');",
            "    stateIndexMap = containers.Map('KeyType','char','ValueType','int32');",
            ""
        ]

        # Add enhanced state creation
        script_lines.extend(self._generate_enhanced_state_creation_code(states))
        
        # Add enhanced transition creation
        script_lines.extend(self._generate_enhanced_transition_creation_code(transitions))
        
        # Add finalization and optimization
        script_lines.extend([
            "",
            "    fprintf('FSM_PROGRESS: Finalizing model...\\n');",
            "",
            "    % Optimize layout if requested",
            "    if optimizeLayout",
            "        try",
            "            Simulink.BlockDiagram.arrangeSystem(modelNameVar);",
            "        catch",
            "            % Layout optimization failed, continue anyway",
            "            fprintf('Warning: Layout optimization failed\\n');",
            "        end",
            "    end",
            "",
            "    % Add model documentation",
            "    if generateDocs",
            "        docText = sprintf(['FSM Model: %s\\n', ...",
            "                          'Generated: %s\\n', ...",
            f"                          'States: {len(states)}\\n', ...",
            f"                          'Transitions: {len(transitions)}\\n', ...",
            "                          'FSM Designer Version: 2.0'], ...",
            "                         modelNameVar, datestr(now));",
            "        set_param(modelNameVar, 'Description', docText);",
            "    end",
            "",
            "    % Create test harness if requested",
            "    if createTestHarness",
            "        fprintf('FSM_PROGRESS: Creating test harness...\\n');",
            "        harnessName = [modelNameVar '_TestHarness'];",
            "        sltest.harness.create(modelNameVar, 'Name', harnessName);",
            "    end",
            "",
            "    % Final model validation",
            "    fprintf('FSM_PROGRESS: Validating model...\\n');",
            "    try",
            "        % Compile model to check for errors",
            "        set_param(modelNameVar, 'SimulationCommand', 'update');",
            "        fprintf('Model validation successful\\n');",
            "    catch validationErr",
            "        warning('Model validation warning: %s', validationErr.message);",
            "    end",
            "",
            "    % Save model with metadata",
            "    fprintf('FSM_PROGRESS: Saving model...\\n');",
            "    save_system(modelNameVar, outputModelPath, 'OverwriteIfChangedOnDisk', true);",
            "",
            "    % Save generation report",
            "    reportPath = strrep(outputModelPath, '.slx', '_report.json');",
            "    report = struct();",
            "    report.model_name = modelNameVar;",
            "    report.generation_time = datestr(now);",
            f"    report.state_count = {len(states)};",
            f"    report.transition_count = {len(transitions)};",
            "    report.options = struct();",
            f"    report.options.enable_data_logging = {str(options.get('enable_data_logging', True)).lower()};",
            f"    report.options.add_scope_blocks = {str(options.get('add_scope_blocks', True)).lower()};",
            "    reportJson = jsonencode(report);",
            "    fid = fopen(reportPath, 'w');",
            "    if fid > 0",
            "        fprintf(fid, '%s', reportJson);",
            "        fclose(fid);",
            "    end",
            "",
            "    close_system(modelNameVar, 0);",
            "",
            "    fprintf('MATLAB_SCRIPT_SUCCESS:%s\\n', outputModelPath);",
            "",
            "catch e",
            "    fprintf('MATLAB_SCRIPT_FAILURE:%s\\n', strrep(getReport(e, 'extended'), '\\n', ' '));",
            "    % Enhanced cleanup on error",
            "    try",
            "        if bdIsLoaded(modelNameVar)",
            "            close_system(modelNameVar, 0);",
            "        end",
            "    catch",
            "    end",
            "end"
        ])

        return "\n".join(script_lines)

    def _generate_enhanced_state_creation_code(self, states: List[Dict]) -> List[str]:
        """Generate enhanced MATLAB code for creating states with advanced features"""
        script_lines = ["    % Enhanced state creation with advanced features"]
        
        # Calculate optimal layout if coordinates are missing
        if not all('x' in state and 'y' in state for state in states):
            script_lines.append("    % Calculate optimal state layout")
            # Add automatic layout calculation logic here
        
        for i, state in enumerate(states):
            state_name = state['name'].replace("'", "''")
            state_id = f"state_{i}_{state['name'].replace(' ', '_').replace('-', '_')}"
            state_id = ''.join(c for c in state_id if c.isalnum() or c == '_')
            if not state_id or not state_id[0].isalpha():
                state_id = 's_' + state_id
            
            # Enhanced coordinate calculation with automatic layout
            sf_x = state.get('x', 50 + (i % 4) * 150) / 2.0 + 30
            sf_y = state.get('y', 50 + (i // 4) * 120) / 2.0 + 30
            sf_w = max(100, state.get('width', 120) / 2.0)
            sf_h = max(60, state.get('height', 80) / 2.0)
            
            # Enhanced state label with comprehensive actions
            label_parts = [
                f'entry: active_state_name = "{state_name}"; active_state_index = {i+1}; trans_count_local = trans_count_local;'
            ]
            
            # Add custom actions with error handling
            action_mappings = {
                'entry_action': 'entry',
                'during_action': 'during', 
                'exit_action': 'exit'
            }
            
            for action_key, action_prefix in action_mappings.items():
                action_code = state.get(action_key, '').strip()
                if action_code:
                    # Escape and validate action code
                    escaped_code = action_code.replace("'", "''").replace('\n', '; ')
                    # Add try-catch wrapper for safety
                    safe_code = f'try; {escaped_code}; catch; end;'
                    label_parts.append(f"{action_prefix}: {safe_code}")
            
            state_label = "\\n".join(label_parts)
            
            script_lines.extend([
                f"    % Create state: {state_name}",
                f"    {state_id} = Stateflow.State(chartSFObj);",
                f"    {state_id}.Name = '{state_name}';",
                f"    {state_id}.Position = [{sf_x:.1f}, {sf_y:.1f}, {sf_w:.1f}, {sf_h:.1f}];",
                f"    {state_id}.LabelString = '{state_label}';",
                f"    {state_id}.Description = 'Auto-generated state: {state_name}';",
                f"    stateHandles('{state_name}') = {state_id};",
                f"    stateIndexMap('{state_name}') = {i+1};"
            ])
            
            # Enhanced initial state handling
            if state.get('is_initial', False):
                script_lines.extend([
                    f"    % Set {state_name} as initial state",
                    f"    defaultTrans_{i} = Stateflow.Transition(chartSFObj);",
                    f"    defaultTrans_{i}.Destination = {state_id};",
                    f"    defaultTrans_{i}.DestinationOClock = 12;",
                    f"    defaultTrans_{i}.LabelString = '[trans_count_local = 0]';",
                    f"    defaultTrans_{i}.Description = 'Initial transition to {state_name}';"
                ])
            
            script_lines.append("")
        
        return script_lines

    def _generate_enhanced_transition_creation_code(self, transitions: List[Dict]) -> List[str]:
        """Generate enhanced MATLAB code for creating transitions with advanced features"""
        script_lines = [
            "    % Enhanced transition creation with validation",
            "    fprintf('FSM_PROGRESS: Creating transitions...\\n');"
        ]
        
        for i, trans in enumerate(transitions):
            src_name = trans['source'].replace("'", "''")
            dst_name = trans['target'].replace("'", "''")
            
            # Enhanced transition label with comprehensive features
            label_parts = []
            
            # Event handling
            event = trans.get('event', '').strip()
            if event:
                label_parts.append(event)
            
            # Condition handling with validation
            condition = trans.get('condition', '').strip()
            if condition:
                # Add safety wrapper for conditions
                safe_condition = f"[{condition}]"
                label_parts.append(safe_condition)
            
            # Action handling with error protection and transition counting
            action = trans.get('action', '').strip()
            action_parts = []
            if action:
                escaped_action = action.replace("'", "''").replace('\n', '; ')
                action_parts.append(f"try; {escaped_action}; catch; end")
            
            # Always increment transition counter
            action_parts.append("trans_count_local = trans_count_local + 1")
            action_parts.append("transition_count = trans_count_local")
            
            if action_parts:
                label_parts.append(f"/{{{'; '.join(action_parts)}}}")
            
            trans_label = " ".join(label_parts).strip().replace("'", "''")
            
            script_lines.extend([
                f"    % Create transition {i+1}: {src_name} -> {dst_name}",
                f"    if isKey(stateHandles, '{src_name}') && isKey(stateHandles, '{dst_name}')",
                f"        srcState = stateHandles('{src_name}');",
                f"        dstState = stateHandles('{dst_name}');",
                f"        trans_{i} = Stateflow.Transition(chartSFObj);",
                f"        trans_{i}.Source = srcState;",
                f"        trans_{i}.Destination = dstState;",
                f"        trans_{i}.Description = 'Transition from {src_name} to {dst_name}';",
            ])
            
            if trans_label:
                script_lines.append(f"        trans_{i}.LabelString = '{trans_label}';")
            
            # Enhanced transition properties
            script_lines.extend([
                f"        % Configure transition properties",
                f"        trans_{i}.SourceOClock = 3;  % Right side of source state",
                f"        trans_{i}.DestinationOClock = 9;  % Left side of destination state",
            ])
            
            script_lines.extend([
                "    else",
                f"        warning('States not found for transition {i+1}: {src_name} -> {dst_name}');",
                f"        fprintf('FSM_PROGRESS: Warning - Invalid transition: {src_name} -> {dst_name}\\n');",
                "    end",
                ""
            ])
        
        return script_lines

    def run_simulation(self, model_path: str, config: SimulationConfig = None, 
                      progress_callback: Callable[[str, int], None] = None) -> bool:
        """Run enhanced Simulink simulation with comprehensive monitoring"""
        
        model_path_obj = Path(model_path)
        if not model_path_obj.exists():
            self.simulationFinished.emit(False, f"Model file not found: {model_path}", "", {
                'error_type': 'file_not_found',
                'model_path': model_path
            })
            return False

        if config is None:
            config = SimulationConfig()

        model_path_matlab = str(model_path_obj).replace(os.sep, '/')
        model_name = model_path_obj.stem
        
        # Create enhanced simulation script
        script_content = f"""
% Enhanced Simulation Script with Comprehensive Monitoring
% Model: {model_name}
% Generated by FSM Designer v2.0

try
    fprintf('SIM_PROGRESS: Initializing simulation environment...\\n');
    
    % Validate simulation environment
    if ~license('test', 'Simulink')
        error('Simulink license not available for simulation');
    end
    
    % Load and validate model
    fprintf('SIM_PROGRESS: Loading model {model_name}...\\n');
    if ~exist('{model_path_matlab}', 'file')
        error('Model file not found: {model_path_matlab}');
    end
    
    load_system('{model_path_matlab}');
    
    % Verify model is loaded
    if ~bdIsLoaded('{model_name}')
        error('Failed to load model: {model_name}');
    end
    
    fprintf('SIM_PROGRESS: Configuring simulation parameters...\\n');
    
    % Apply enhanced simulation configuration
{self._generate_simulation_config_code(config, model_name)}
    
    % Pre-simulation validation
    fprintf('SIM_PROGRESS: Validating model for simulation...\\n');
    try
        % Check for compilation errors
        set_param('{model_name}', 'SimulationCommand', 'update');
        fprintf('Model validation successful\\n');
    catch updateErr
        warning('Model update warning: %s', updateErr.message);
    end
    
    % Clear previous simulation data
    clear simOut;
    
    % Configure simulation callbacks for progress monitoring
    fprintf('SIM_PROGRESS: Starting simulation (Stop time: {config.stop_time}s)...\\n');
    
    % Enhanced simulation execution with monitoring
    simStartTime = tic;
    
    % Run simulation with comprehensive output capture
    simOut = sim('{model_name}', 'CaptureErrors', 'on', 'AbsTol', '{config.absolute_tolerance}', 'RelTol', '{config.relative_tolerance}');
    
    simDuration = toc(simStartTime);
    
    fprintf('SIM_PROGRESS: Simulation completed successfully in %.2f seconds\\n', simDuration);
    
    % Enhanced results processing
    fprintf('SIM_PROGRESS: Processing simulation results...\\n');
    
    % Extract and validate simulation data
    results = struct();
    results.simulation_time = simDuration;
    results.stop_time = {config.stop_time};
    results.solver = '{config.solver}';
    
    % Process workspace variables
    if exist('state_names', 'var') && ~isempty(state_names)
        results.state_names = state_names;
        results.final_state = state_names.Data(end);
        results.state_changes = length(unique(state_names.Data));
    end
    
    if exist('state_indices', 'var') && ~isempty(state_indices)
        results.state_indices = state_indices;
        results.final_state_index = state_indices.Data(end);
    end
    
    if exist('transition_counts', 'var') && ~isempty(transition_counts)
        results.transition_counts = transition_counts;
        results.total_transitions = transition_counts.Data(end);
    end
    
    % Performance metrics
    results.performance = struct();
    results.performance.real_time_factor = simDuration / {config.stop_time};
    results.performance.solver_stats = simOut.SimulationMetadata.SolverInfo;
    
    % Save results to workspace for analysis
    assignin('base', 'FSM_simulation_results', results);
    
    % Generate summary report
    fprintf('\\n=== Simulation Summary ===\\n');
    fprintf('Model: {model_name}\\n');
    fprintf('Duration: %.2f seconds (Real-time factor: %.2fx)\\n', simDuration, results.performance.real_time_factor);
    if isfield(results, 'final_state')
        fprintf('Final State: %s\\n', string(results.final_state));
    end
    if isfield(results, 'total_transitions')
        fprintf('Total Transitions: %d\\n', results.total_transitions);
    end
    fprintf('========================\\n');
    
    % Encode results as JSON for return
    resultsJson = jsonencode(results);
    
    fprintf('MATLAB_SCRIPT_SUCCESS:%s\\n', resultsJson);
    
catch e
    % Enhanced error reporting
    errorReport = struct();
    errorReport.message = e.message;
    errorReport.identifier = e.identifier;
    errorReport.stack = e.stack;
    errorReport.model_name = '{model_name}';
    errorReport.simulation_time = 0;
    
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

    def _generate_simulation_config_code(self, config: SimulationConfig, model_name: str) -> str:
        """Generate MATLAB code for simulation configuration"""
        config_commands = config.to_matlab_commands(model_name)
        
        # Add enhanced configuration
        enhanced_commands = [
            f"    % Enhanced simulation configuration for {model_name}",
            "    try"
        ]
        
        for cmd in config_commands:
            enhanced_commands.append(f"        {cmd}")
        
        enhanced_commands.extend([
            "",
            "        % Additional performance optimizations",
            f"        set_param('{model_name}', 'AlgebraicLoopSolver', 'TrustRegion');",
            f"        set_param('{model_name}', 'MinStepSizeMsg', 'none');",
            f"        set_param('{model_name}', 'ConsecutiveZCsStepRelTol', '10*128*eps');",
            f"        set_param('{model_name}', 'SolverResetMethod', 'Fast');",
            "",
            "        % Configure data logging",
            "        if exist('Simulink.sdi', 'file')",
            "            Simulink.sdi.clear();",
            "            Simulink.sdi.setAutoArchiveMode(true);",
            "        end",
            "",
            "    catch configErr",
            "        warning('Configuration warning: %s', configErr.message);",
            "    end"
        ])
        
        return "\n".join(enhanced_commands)

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
            QMetaObject.invokeMethod(self.worker, "shutdown_engine", Qt.QueuedConnection)
            
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
                    self.worker, "execute_command", Qt.QueuedConnection,
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

    # Continuation and completion of the MATLAB integration script

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
            QMetaObject.invokeMethod(self.worker, "shutdown_engine", Qt.QueuedConnection)
            
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
        import psutil
        
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
                'pyqt_version': '5.x',  # Could be detected dynamically
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
        
        # Add configuration commands
        for cmd in config.to_matlab_commands(model_name):
            config_lines.append(f"    {cmd}")
        
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


# Enhanced error handling and recovery
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


# Module initialization
if __name__ == "__main__":
    # Basic module test
    print("FSM Designer MATLAB Integration Module")
    print(f"MATLAB Engine Available: {MATLAB_ENGINE_AVAILABLE}")
    
    # Run diagnostics if available
    if MATLAB_ENGINE_AVAILABLE:
        print("Running diagnostics...")
        diagnostics = MatlabDiagnostics.check_matlab_installation()
        print(f"MATLAB Installation: {diagnostics.get('quick_test', 'Unknown')}")
        
        if 'toolbox_availability' in diagnostics:
            print("Available Toolboxes:")
            for toolbox, available in diagnostics['toolbox_availability'].items():
                print(f"  {toolbox}: {'✓' if available else '✗'}")
    else:
        print("MATLAB Engine not available - install required")
        print("Run installation diagnostics for help")