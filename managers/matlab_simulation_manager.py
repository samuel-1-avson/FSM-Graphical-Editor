# fsm_designer_project/managers/matlab_simulation_manager.py

import os
import time
import logging
import socket
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer, QMetaObject, Q_ARG, pyqtSlot, Qt

try:
    import matlab.engine
    MATLAB_ENGINE_AVAILABLE = True
except ImportError:
    MATLAB_ENGINE_AVAILABLE = False

logger = logging.getLogger(__name__)

class SimulationState(Enum):
    """Simulation states"""
    IDLE = "idle"
    LOADING = "loading"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class SimulationData:
    """Container for simulation data"""
    time: float
    active_state: str
    variables: Dict[str, Any]
    tick: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'time': self.time,
            'active_state': self.active_state,
            'variables': self.variables,
            'tick': self.tick
        }


@dataclass
class SimulationConfig:
    stop_time: float = 10.0
    step_size: Optional[float] = None
    solver: str = 'ode45'
    max_step_size: Optional[float] = None
    min_step_size: Optional[float] = None
    relative_tolerance: float = 1e-3
    absolute_tolerance: float = 1e-6
    output_options: str = 'RefineOutputTimes'
    refine_factor: int = 1
    save_output: bool = True
    save_states: bool = True
    decimation: int = 1
    limit_data_points: bool = True
    max_data_points: int = 2000

    def to_matlab_params(self) -> Dict[str, str]:
        params = {
            'StopTime': str(self.stop_time),
            'Solver': self.solver,
            'RelTol': str(self.relative_tolerance),
            'AbsTol': str(self.absolute_tolerance),
            'OutputOption': self.output_options,
            'Refine': str(self.refine_factor),
            'SaveOutput': 'on' if self.save_output else 'off',
            'SaveState': 'on' if self.save_states else 'off',
            'Decimation': str(self.decimation),
            'LimitDataPoints': 'on' if self.limit_data_points else 'off'
        }

        if self.step_size is not None:
            params['FixedStep'] = str(self.step_size)
        if self.max_step_size is not None:
            params['MaxStep'] = str(self.max_step_size)
        if self.min_step_size is not None:
            params['MinStep'] = str(self.min_step_size)
        if self.limit_data_points:
            params['MaxDataPoints'] = str(self.max_data_points)

        return params


class TcpReceiverWorker(QObject):
    """Listens on a TCP socket for data streamed from Simulink.

    This worker is designed to run in its own QThread. It accepts one
    connection at a time and emits `data_received` signals whenever a
    null-terminated message arrives. It handles socket timeouts so the
    thread can shut down quickly on request.
    """
    data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, host='127.0.0.1', port=30000, backlog=1, timeout=1.0):
        super().__init__()
        self.host = host
        self.port = int(port)
        self.backlog = backlog
        self.timeout = float(timeout)
        self._is_running = False
        self.server_socket: Optional[socket.socket] = None

    @pyqtSlot()
    def start_server(self):
        self._is_running = True
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.backlog)
            self.server_socket.settimeout(self.timeout)
            logger.info(f"TCP server listening for Simulink on {self.host}:{self.port}")

            while self._is_running:
                try:
                    conn, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.exception("Error accepting TCP connection: %s", e)
                    break

                with conn:
                    logger.info(f"TCP connection from Simulink established: {addr}")
                    conn.settimeout(self.timeout)
                    buffer = ""
                    while self._is_running:
                        try:
                            data = conn.recv(4096)
                            if not data:
                                logger.info("Simulink closed the TCP connection.")
                                break
                            buffer += data.decode('utf-8', errors='ignore')
                            while '\x00' in buffer:
                                message, buffer = buffer.split('\x00', 1)
                                if message:
                                    self.data_received.emit(message)
                        except socket.timeout:
                            continue
                        except Exception as e:
                            logger.exception("Error while receiving TCP data: %s", e)
                            self.error_occurred.emit(str(e))
                            break

        except Exception as e:
            if self._is_running:
                logger.exception("TCP server error: %s", e)
                self.error_occurred.emit(str(e))
        finally:
            self.stop_server()

    @pyqtSlot()
    def stop_server(self):
        if self._is_running:
            self._is_running = False
            if self.server_socket:
                try:
                    self.server_socket.close()
                    logger.info("TCP server socket closed.")
                except Exception as e:
                    logger.warning(f"Error closing TCP server socket: {e}")
                self.server_socket = None


class MatlabEngineWorker(QObject):
    """Worker responsible for MATLAB Engine interaction and simulation control.

    Important: QTimer objects are created in the initialize_engine method so
    they live in the correct thread (the worker's thread) and avoid
    cross-thread QTimer warnings.
    """

    # Status signals
    engine_status_changed = pyqtSignal(bool, str)  # connected, message
    simulation_state_changed = pyqtSignal(SimulationState, str)  # state, message

    # Data signals
    simulation_data_updated = pyqtSignal(SimulationData)
    simulation_progress = pyqtSignal(float, float)  # current_time, total_time

    # Event signals
    simulation_completed = pyqtSignal(bool, str, dict)  # success, message, final_data
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.engine = None
        self.current_model = None
        self.simulation_state = SimulationState.IDLE
        self.config = SimulationConfig()
        self._stop_requested = False
        self._pause_requested = False

        # Poll timer will be created inside initialize_engine (thread context)
        self._poll_timer: Optional[QTimer] = None
        self._poll_interval = 100  # ms

        # Performance tracking
        self._start_time = 0
        self._last_update_time = 0
        self._data_points_collected = 0

        # Monitoring utilities
        self.performance_monitor = None

    @pyqtSlot()
    def initialize_engine(self):
        """Initialize MATLAB Engine and timers in the worker thread."""
        if self.engine:
            self.engine_status_changed.emit(True, "Engine already initialized")
            return

        # Create QTimer in this thread's context
        if self._poll_timer is None:
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(self._poll_interval)
            self._poll_timer.timeout.connect(self._poll_simulation_status)

        if not MATLAB_ENGINE_AVAILABLE:
            msg = ("MATLAB Engine for Python not available. "
                   "Please install it from your MATLAB installation directory.")
            self.error_occurred.emit(msg)
            self.engine_status_changed.emit(False, msg)
            return

        try:
            logger.info("Initializing MATLAB Engine for simulation...")
            # --- FIX: Pass startup options as a single string ---
            self.engine = matlab.engine.start_matlab('-nodesktop -nosplash')

            # Configure MATLAB environment for simulation
            self._configure_matlab_environment()

            # Handle performance monitor
            try:
                from .matlab_simulation_manager import MatlabPerformanceMonitor  # local import for optionality
                self.performance_monitor = MatlabPerformanceMonitor()
                self.performance_monitor.start_monitoring()
            except Exception:
                self.performance_monitor = None

            version = self.engine.eval("version('-release')")
            self.engine_status_changed.emit(True, f"MATLAB Engine initialized (Version: {version})")

        except Exception as e:
            msg = f"Failed to initialize MATLAB Engine: {e}"
            logger.error(msg, exc_info=True)
            self.error_occurred.emit(msg)
            self.engine_status_changed.emit(False, msg)

    def _configure_matlab_environment(self):
        """Configure MATLAB environment for optimal simulation performance"""
        config_commands = [
            "warning('off', 'all');",
            "format compact;",
            "clear all;",
            "close all;",
        ]

        for cmd in config_commands:
            try:
                self.engine.eval(cmd, nargout=0)
            except Exception as e:
                logger.debug(f"MATLAB config command failed: {cmd} -> {e}")

    @pyqtSlot(str, SimulationConfig)
    def load_model(self, model_path: str, config: SimulationConfig):
        """Load Simulink model with configuration"""
        if not Path(model_path).exists():
            msg = f"Model file not found: {model_path}"
            self.error_occurred.emit(msg)
            return

        if not self.engine:
            self.error_occurred.emit("MATLAB Engine not initialized")
            return

        self._set_simulation_state(SimulationState.LOADING, "Loading model...")
        self.config = config

        try:
            matlab_path = str(Path(model_path).resolve()).replace('\\', '/')
            model_name = Path(model_path).stem

            logger.info(f"Loading Simulink model: {matlab_path}")

            # Close previously opened model to avoid name collisions
            try:
                if self.current_model:
                    self.engine.eval(f"if bdIsLoaded('{self.current_model}'), close_system('{self.current_model}', 0); end", nargout=0)
            except Exception:
                pass

            # Load the model by full path
            self.engine.eval(f"load_system('{matlab_path}')", nargout=0)

            # Configure model parameters
            self._configure_model_parameters(model_name)

            # Validate model
            self._validate_model(model_name)

            self.current_model = model_name
            self._set_simulation_state(SimulationState.IDLE, f"Model '{model_name}' loaded successfully")

        except Exception as e:
            msg = f"Failed to load model: {e}"
            logger.error(msg, exc_info=True)
            self._set_simulation_state(SimulationState.ERROR, msg)
            self.error_occurred.emit(msg)

    def _configure_model_parameters(self, model_name: str):
        """Configure model parameters for simulation"""
        params = self.config.to_matlab_params()

        for param, value in params.items():
            try:
                # Only set parameters that are valid for the model
                self.engine.eval(f"set_param('{model_name}', '{param}', '{value}')", nargout=0)
            except Exception as e:
                logger.debug(f"Failed to set parameter {param}={value}: {e}")

    def _validate_model(self, model_name: str):
        """Validate model for simulation"""
        try:
            compile_cmd = f"try; {model_name}([], [], [], 'compile'); {model_name}([], [], [], 'term'); catch; end"
            self.engine.eval(compile_cmd, nargout=0)

            # Determine if the model has outputs by querying block ports
            try:
                ports = self.engine.eval(f"get_param('{model_name}', 'Ports')")
                if not any(ports):
                    logger.warning("Model has no output ports - simulation data may be limited")
            except Exception:
                logger.debug("Could not query model ports")

        except Exception as e:
            logger.warning(f"Model validation warning: {e}")

    @pyqtSlot()
    def start_simulation(self):
        """Start the simulation"""
        if not self.current_model or not self.engine:
            self.error_occurred.emit("No model loaded or engine not available")
            return

        if self.simulation_state == SimulationState.RUNNING:
            logger.warning("Simulation already running")
            return

        try:
            self._set_simulation_state(SimulationState.RUNNING, "Starting simulation...")
            self._stop_requested = False
            self._pause_requested = False
            self._start_time = time.time()
            self._data_points_collected = 0

            logger.info(f"Starting simulation of model: {self.current_model}")
            self.engine.eval(f"set_param('{self.current_model}', 'SimulationCommand', 'start')", nargout=0)

            # Ensure poll timer exists and start it
            if self._poll_timer is not None:
                self._poll_timer.start()

            self._set_simulation_state(SimulationState.RUNNING, "Simulation running")

        except Exception as e:
            msg = f"Failed to start simulation: {e}"
            logger.error(msg, exc_info=True)
            self._set_simulation_state(SimulationState.ERROR, msg)
            self.error_occurred.emit(msg)

    @pyqtSlot()
    def pause_simulation(self):
        """Pause the simulation"""
        if self.simulation_state != SimulationState.RUNNING:
            return

        try:
            self.engine.eval(f"set_param('{self.current_model}', 'SimulationCommand', 'pause')", nargout=0)
            if self._poll_timer is not None:
                self._poll_timer.stop()
            self._set_simulation_state(SimulationState.PAUSED, "Simulation paused")

        except Exception as e:
            logger.error(f"Failed to pause simulation: {e}")
            self.error_occurred.emit(f"Failed to pause simulation: {e}")

    @pyqtSlot()
    def resume_simulation(self):
        """Resume the paused simulation"""
        if self.simulation_state != SimulationState.PAUSED:
            return

        try:
            self.engine.eval(f"set_param('{self.current_model}', 'SimulationCommand', 'continue')", nargout=0)
            if self._poll_timer is not None:
                self._poll_timer.start()
            self._set_simulation_state(SimulationState.RUNNING, "Simulation resumed")

        except Exception as e:
            logger.error(f"Failed to resume simulation: {e}")
            self.error_occurred.emit(f"Failed to resume simulation: {e}")

    @pyqtSlot()
    def stop_simulation(self):
        """Stop the simulation"""
        if self.simulation_state not in [SimulationState.RUNNING, SimulationState.PAUSED]:
            return

        self._stop_requested = True
        self._set_simulation_state(SimulationState.STOPPING, "Stopping simulation...")

        try:
            self.engine.eval(f"set_param('{self.current_model}', 'SimulationCommand', 'stop')", nargout=0)
            if self._poll_timer is not None:
                self._poll_timer.stop()

        except Exception as e:
            logger.error(f"Failed to stop simulation: {e}")
            self.error_occurred.emit(f"Failed to stop simulation: {e}")

    def _poll_simulation_status(self):
        """Poll simulation status and collect data"""
        if not self.engine or not self.current_model or self._stop_requested:
            return

        try:
            status = self.engine.eval(f"get_param('{self.current_model}', 'SimulationStatus')")

            if status == 'stopped':
                self._handle_simulation_completion()
                return
            elif status == 'paused':
                if self.simulation_state == SimulationState.RUNNING:
                    self._set_simulation_state(SimulationState.PAUSED, "Simulation paused")
                return

            current_time = float(self.engine.eval(f"get_param('{self.current_model}', 'SimulationTime')"))

            # Emit progress
            self.simulation_progress.emit(current_time, self.config.stop_time)

            # Collect data
            self._collect_simulation_data(current_time)

            # Update performance monitor
            try:
                if self.performance_monitor:
                    self.performance_monitor.update(current_time)
            except Exception:
                pass

            # Check for completion
            if current_time >= self.config.stop_time:
                self._handle_simulation_completion()

        except Exception as e:
            logger.error(f"Error during simulation polling: {e}")
            self._handle_simulation_error(str(e))

    def _collect_simulation_data(self, current_time: float):
        """Collect simulation data at current time"""
        try:
            active_state = "Unknown"
            try:
                state_value = self.engine.workspace.get('active_state_name', None)
                if state_value:
                    active_state = str(state_value)
            except Exception:
                pass

            variables = {}
            try:
                # Query some common workspace variables
                workspace_vars = self.engine.eval("who")
                var_candidates = ['tout', 'yout', 'xout', 'simout']
                for var_name in var_candidates:
                    if var_name in workspace_vars:
                        try:
                            var_value = self.engine.workspace[var_name]
                            variables[var_name] = self._matlab_to_python(var_value)
                        except Exception:
                            variables[var_name] = '<unreadable>'
            except Exception:
                pass

            sim_data = SimulationData(
                time=current_time,
                active_state=active_state,
                variables=variables,
                tick=self._data_points_collected
            )

            self.simulation_data_updated.emit(sim_data)
            self._data_points_collected += 1
            self._last_update_time = time.time()

            # Guard against collecting too many points
            if self.config.limit_data_points and self._data_points_collected > self.config.max_data_points:
                logger.warning("Reached max configured data points; stopping simulation to avoid memory blowup")
                self.stop_simulation()

        except Exception as e:
            logger.warning(f"Failed to collect simulation data: {e}")

    def _matlab_to_python(self, matlab_value):
        """Convert MATLAB value to Python-friendly types."""
        try:
            # Numeric arrays
            import matlab
            if isinstance(matlab_value, matlab.double):
                return [list(row) for row in matlab_value]
            if isinstance(matlab_value, matlab.logical):
                return bool(matlab_value)
            # Try generic conversions
            if hasattr(matlab_value, '_data'):
                return list(matlab_value._data)
            if hasattr(matlab_value, 'size'):
                try:
                    return list(matlab_value)
                except Exception:
                    return str(matlab_value)
            return matlab_value
        except Exception:
            try:
                return str(matlab_value)
            except Exception:
                return '<unconvertible>'

    def _handle_simulation_completion(self):
        """Handle simulation completion"""
        if self._poll_timer is not None:
            self._poll_timer.stop()

        try:
            final_data = self._collect_final_simulation_data()
            execution_time = time.time() - self._start_time
            message = f"Simulation completed successfully in {execution_time:.2f}s ({self._data_points_collected} data points)"
            self._set_simulation_state(SimulationState.COMPLETED, message)
            self.simulation_completed.emit(True, message, final_data)
            logger.info(message)
        except Exception as e:
            error_msg = f"Error during simulation completion: {e}"
            logger.error(error_msg)
            self._handle_simulation_error(error_msg)

    def _collect_final_simulation_data(self) -> Dict[str, Any]:
        """Collect final simulation data and results"""
        final_data = {
            'execution_time': time.time() - self._start_time,
            'data_points': self._data_points_collected,
            'final_time': 0.0,
            'workspace_variables': {}
        }
        try:
            final_data['final_time'] = float(self.engine.eval(f"get_param('{self.current_model}', 'SimulationTime')"))
            workspace_vars = self.engine.eval("who")
            for var_name in workspace_vars:
                try:
                    var_value = self.engine.workspace[var_name]
                    final_data['workspace_variables'][var_name] = self._matlab_to_python(var_value)
                except Exception:
                    final_data['workspace_variables'][var_name] = '<unreadable>'
        except Exception as e:
            logger.warning(f"Failed to collect final simulation data: {e}")
        return final_data

    def _handle_simulation_error(self, error_message: str):
        """Handle simulation error"""
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._set_simulation_state(SimulationState.ERROR, error_message)
        self.simulation_completed.emit(False, error_message, {})
        self.error_occurred.emit(error_message)

    def _set_simulation_state(self, state: SimulationState, message: str):
        """Update simulation state"""
        self.simulation_state = state
        self.simulation_state_changed.emit(state, message)

    @pyqtSlot()
    def cleanup(self):
        """Clean up MATLAB resources"""
        if self._poll_timer is not None:
            self._poll_timer.stop()

        if self.engine:
            try:
                if self.current_model and self.simulation_state == SimulationState.RUNNING:
                    self.engine.eval(f"set_param('{self.current_model}', 'SimulationCommand', 'stop')", nargout=0)
                if self.current_model:
                    self.engine.eval(f"close_system('{self.current_model}', 0)", nargout=0)
                self.engine.quit()
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
            finally:
                self.engine = None
                self.current_model = None


class MatlabSimulationManager(QObject):
    """Simulation manager that hosts the worker in a dedicated thread and
    exposes a higher-level API for the UI.
    """

    engine_status_changed = pyqtSignal(bool, str)
    simulation_state_changed = pyqtSignal(SimulationState, str)
    simulation_data_updated = pyqtSignal(SimulationData)
    simulation_progress = pyqtSignal(float, float)
    simulation_completed = pyqtSignal(bool, str, dict)
    simulation_plot_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = QThread()
        self.thread.setObjectName("MatlabSimulationThread")
        self.worker = MatlabEngineWorker()
        self.worker.moveToThread(self.thread)
        self._connect_worker_signals()

        self.is_engine_ready = False
        self.current_state = SimulationState.IDLE
        self.current_model_path = None
        self.simulation_config = SimulationConfig()

        self.tcp_thread: Optional[QThread] = None
        self.tcp_worker: Optional[TcpReceiverWorker] = None

        # Start worker thread
        self.thread.started.connect(self.worker.initialize_engine)
        self.thread.start()

    def _connect_worker_signals(self):
        self.worker.engine_status_changed.connect(self._on_engine_status_changed)
        self.worker.simulation_state_changed.connect(self._on_simulation_state_changed)
        self.worker.simulation_data_updated.connect(self.simulation_data_updated)
        self.worker.simulation_progress.connect(self.simulation_progress)
        self.worker.simulation_completed.connect(self.simulation_completed)
        self.worker.error_occurred.connect(self.error_occurred)

    def _setup_tcp_server(self, host='127.0.0.1', port=30000):
        if self.tcp_thread and self.tcp_thread.isRunning():
            logger.debug("TCP server thread is already running.")
            return

        self.tcp_thread = QThread()
        self.tcp_thread.setObjectName("MatlabTcpReceiverThread")
        self.tcp_worker = TcpReceiverWorker(host=host, port=port)
        self.tcp_worker.moveToThread(self.tcp_thread)

        self.tcp_worker.data_received.connect(self._on_tcp_data_received)
        self.tcp_worker.error_occurred.connect(self.error_occurred)

        self.tcp_thread.started.connect(self.tcp_worker.start_server)
        self.tcp_thread.start()

    def _stop_tcp_server(self):
        if self.tcp_worker:
            QMetaObject.invokeMethod(self.tcp_worker, "stop_server", Qt.ConnectionType.QueuedConnection)

        if self.tcp_thread:
            self.tcp_thread.quit()
            if not self.tcp_thread.wait(1000):
                logger.warning("TCP receiver thread did not stop gracefully. Terminating.")
                self.tcp_thread.terminate()
            self.tcp_thread = None
        self.tcp_worker = None

    @pyqtSlot(bool, str)
    def _on_engine_status_changed(self, connected: bool, message: str):
        self.is_engine_ready = connected
        self.engine_status_changed.emit(connected, message)

    @pyqtSlot(SimulationState, str)
    def _on_simulation_state_changed(self, state: SimulationState, message: str):
        self.current_state = state
        self.simulation_state_changed.emit(state, message)
        if state in [SimulationState.COMPLETED, SimulationState.ERROR, SimulationState.IDLE]:
            self._stop_tcp_server()

    def load_model(self, model_path: str, config: Optional[SimulationConfig] = None) -> bool:
        if not self.is_engine_ready:
            self.error_occurred.emit("MATLAB Engine not ready")
            return False

        if not Path(model_path).exists():
            self.error_occurred.emit(f"Model file not found: {model_path}")
            return False

        if config is None:
            config = SimulationConfig()

        self.current_model_path = model_path
        self.simulation_config = config

        QMetaObject.invokeMethod(
            self.worker, "load_model", Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, model_path),
            Q_ARG(SimulationConfig, config)
        )
        return True

    def start_simulation(self, tcp_host='127.0.0.1', tcp_port=30000) -> bool:
        if not self.is_engine_ready:
            self.error_occurred.emit("MATLAB Engine not ready")
            return False

        if self.current_state != SimulationState.IDLE:
            self.error_occurred.emit(f"Cannot start simulation in state: {self.current_state.value}")
            return False

        # Start TCP server before simulation so live data can be streamed
        self._setup_tcp_server(host=tcp_host, port=tcp_port)

        QMetaObject.invokeMethod(self.worker, "start_simulation", Qt.ConnectionType.QueuedConnection)
        return True

    def pause_simulation(self) -> bool:
        if self.current_state != SimulationState.RUNNING:
            return False
        QMetaObject.invokeMethod(self.worker, "pause_simulation", Qt.ConnectionType.QueuedConnection)
        return True

    def resume_simulation(self) -> bool:
        if self.current_state != SimulationState.PAUSED:
            return False
        QMetaObject.invokeMethod(self.worker, "resume_simulation", Qt.ConnectionType.QueuedConnection)
        return True

    def stop_simulation(self) -> bool:
        if self.current_state not in [SimulationState.RUNNING, SimulationState.PAUSED]:
            return False
        self._stop_tcp_server()
        QMetaObject.invokeMethod(self.worker, "stop_simulation", Qt.ConnectionType.QueuedConnection)
        return True

    @pyqtSlot(str)
    def _on_tcp_data_received(self, state_name: str):
        # Convert received live state name into SimulationData for UI
        live_data = SimulationData(
            time=0.0,  # Simulink should stream time if desired; placeholder
            active_state=state_name,
            variables={},
            tick=0
        )
        self.simulation_data_updated.emit(live_data)

    def get_simulation_state(self) -> SimulationState:
        return self.current_state

    def is_simulation_running(self) -> bool:
        return self.current_state == SimulationState.RUNNING

    def is_simulation_active(self) -> bool:
        return self.current_state in [SimulationState.RUNNING, SimulationState.PAUSED]

    def get_current_config(self) -> SimulationConfig:
        return self.simulation_config

    def shutdown(self):
        # Stop the TCP server if it's running
        self._stop_tcp_server()
        if self.thread.isRunning():
            QMetaObject.invokeMethod(self.worker, "cleanup", Qt.ConnectionType.QueuedConnection)
            self.thread.quit()
            if not self.thread.wait(5000):
                logger.warning("Simulation manager thread did not shut down gracefully")
                self.thread.terminate()
                self.thread.wait(2000)


class SimulationDataLogger:
    """Utility class for logging and analyzing simulation data"""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.data_history: List[SimulationData] = []
        self.start_time = None
        self.end_time = None

    def start_logging(self):
        self.data_history.clear()
        self.start_time = time.time()
        self.end_time = None

    def log_data(self, data: SimulationData):
        self.data_history.append(data)
        if self.log_file:
            self._write_to_file(data)

    def stop_logging(self):
        self.end_time = time.time()

    def _write_to_file(self, data: SimulationData):
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{data.time},{data.active_state},{data.tick}\n")
        except Exception as e:
            logger.warning(f"Failed to write to log file: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        if not self.data_history:
            return {}
        times = [d.time for d in self.data_history]
        states = [d.active_state for d in self.data_history]
        state_durations = {}
        current_state = None
        state_start_time = None
        for data in self.data_history:
            if data.active_state != current_state:
                if current_state is not None:
                    duration = data.time - state_start_time
                    state_durations[current_state] = state_durations.get(current_state, 0) + duration
                current_state = data.active_state
                state_start_time = data.time
        if current_state is not None and state_start_time is not None:
            duration = times[-1] - state_start_time
            state_durations[current_state] = state_durations.get(current_state, 0) + duration
        return {
            'total_time': times[-1] - times[0] if len(times) > 1 else 0,
            'data_points': len(self.data_history),
            'unique_states': len(set(states)),
            'state_durations': state_durations,
            'average_sampling_rate': len(times) / (times[-1] - times[0]) if len(times) > 1 else 0,
            'session_duration': self.end_time - self.start_time if self.end_time else None
        }

    def export_to_csv(self, filename: str):
        try:
            import csv
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Time', 'Active_State', 'Tick', 'Variables'])
                for data in self.data_history:
                    variables_str = ';'.join([f"{k}={v}" for k, v in data.variables.items()])
                    writer.writerow([data.time, data.active_state, data.tick, variables_str])
            logger.info(f"Simulation data exported to: {filename}")
        except Exception as e:
            logger.error(f"Failed to export data to CSV: {e}")
            raise


class MatlabPerformanceMonitor:
    """Monitor MATLAB simulation performance"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.start_time = None
        self.data_points = 0
        self.memory_usage = []
        self.cpu_usage = []
        self.simulation_times = []

    def start_monitoring(self):
        self.reset()
        self.start_time = time.time()

    def update(self, simulation_time: float):
        if self.start_time is None:
            return
        self.data_points += 1
        self.simulation_times.append(simulation_time)
        try:
            import psutil
            process = psutil.Process()
            self.memory_usage.append(process.memory_info().rss / 1024 / 1024)
            self.cpu_usage.append(process.cpu_percent())
        except ImportError:
            pass

    def get_metrics(self) -> Dict[str, Any]:
        if self.start_time is None:
            return {}
        elapsed_time = time.time() - self.start_time
        metrics = {
            'elapsed_time': elapsed_time,
            'data_points': self.data_points,
            'data_rate': self.data_points / elapsed_time if elapsed_time > 0 else 0,
            'simulation_progress': max(self.simulation_times) if self.simulation_times else 0
        }
        if self.memory_usage:
            metrics.update({
                'avg_memory_mb': sum(self.memory_usage) / len(self.memory_usage),
                'max_memory_mb': max(self.memory_usage),
                'current_memory_mb': self.memory_usage[-1]
            })
        if self.cpu_usage:
            metrics.update({
                'avg_cpu_percent': sum(self.cpu_usage) / len(self.cpu_usage),
                'max_cpu_percent': max(self.cpu_usage),
                'current_cpu_percent': self.cpu_usage[-1]
            })
        return metrics


# Factory helpers

def create_simulation_manager_with_logging(log_file: Optional[str] = None) -> Tuple[MatlabSimulationManager, SimulationDataLogger]:
    manager = MatlabSimulationManager()
    logger_obj = SimulationDataLogger(log_file)
    manager.simulation_data_updated.connect(logger_obj.log_data)

    def start_logging_session():
        logger_obj.start_logging()

    def stop_logging_session():
        logger_obj.stop_logging()

    manager.simulation_state_changed.connect(
        lambda state, msg: start_logging_session() if state == SimulationState.RUNNING else None
    )
    manager.simulation_state_changed.connect(
        lambda state, msg: stop_logging_session() if state in [SimulationState.COMPLETED, SimulationState.ERROR] else None
    )

    return manager, logger_obj


def create_default_simulation_config() -> SimulationConfig:
    return SimulationConfig(
        stop_time=10.0,
        step_size=0.1,
        solver='ode1',
        save_output=True,
        save_states=True,
        decimation=1,
        limit_data_points=True,
        max_data_points=5000
    )