# fsm_designer_project/managers/c_simulation_manager.py

import os
import logging
import subprocess
import tempfile
import sys
import ctypes
import json
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
import shutil
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit, QGroupBox,
    QHeaderView, QTableWidget, QTableWidgetItem, QComboBox,
    QStyle, QMessageBox, QHBoxLayout, QLabel, QInputDialog,
    QProgressBar, QSplitter, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QSpinBox, QFrame
)
from PyQt5.QtCore import (
    QObject, pyqtSlot, pyqtSignal, QThread, QMetaObject, 
    Q_ARG, Qt, QStandardPaths, QDir, QTimer
)
from PyQt5.QtGui import QFont, QColor, QPalette

from ..utils import get_standard_icon
from ..utils.c_code_generator import generate_c_code_content

logger = logging.getLogger(__name__)

class CompilerType(Enum):
    MSVC = "msvc"
    GCC = "gcc"
    CLANG = "clang"
    UNKNOWN = "unknown"

@dataclass
class CompilationResult:
    success: bool
    library_path: str
    output: str
    compiler_type: CompilerType
    compilation_time: float
    warnings: List[str]
    errors: List[str]

@dataclass
class FSMState:
    name: str
    id: int
    entry_actions: List[str]
    exit_actions: List[str]
    is_current: bool = False

@dataclass
class FSMEvent:
    name: str
    id: int
    description: str

class CCompilerWorker(QObject):
    compile_started = pyqtSignal()
    compile_progress = pyqtSignal(str)  # Progress message
    compile_finished = pyqtSignal(CompilationResult)

    def __init__(self):
        super().__init__()
        self._compiler_cache = {}
        self._build_counter = 0

    def _find_vcvarsall_bat(self) -> Optional[str]:
        """Enhanced MSVC detection with caching."""
        if 'vcvarsall' in self._compiler_cache:
            return self._compiler_cache['vcvarsall']
            
        # Check common Visual Studio installation paths
        program_files_paths = [
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        ]
        
        vs_versions = ["2022", "2019", "2017", "2015"]
        vs_editions = ["Community", "Professional", "Enterprise", "BuildTools"]

        for pf_path in program_files_paths:
            for version in vs_versions:
                for edition in vs_editions:
                    vcvars_path = Path(pf_path) / "Microsoft Visual Studio" / version / edition / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                    if vcvars_path.exists():
                        logger.info(f"Found vcvarsall.bat at: {vcvars_path}")
                        self._compiler_cache['vcvarsall'] = str(vcvars_path)
                        return str(vcvars_path)
        
        self._compiler_cache['vcvarsall'] = None
        return None

    def _detect_available_compilers(self) -> List[Tuple[CompilerType, str]]:
        """Detect all available C compilers on the system."""
        compilers = []
        
        # Check for MSVC
        if sys.platform == "win32":
            vcvars_path = self._find_vcvarsall_bat()
            if vcvars_path:
                compilers.append((CompilerType.MSVC, "cl"))
        
        # Check for GCC
        gcc_path = shutil.which("gcc")
        if gcc_path:
            compilers.append((CompilerType.GCC, gcc_path))
            
        # Check for Clang
        clang_path = shutil.which("clang")
        if clang_path:
            compilers.append((CompilerType.CLANG, clang_path))
            
        return compilers

    def _get_msvc_environment(self) -> Optional[dict]:
        """Enhanced MSVC environment setup with caching."""
        if 'msvc_env' in self._compiler_cache:
            return self._compiler_cache['msvc_env']
            
        vcvars_path = self._find_vcvarsall_bat()
        if not vcvars_path:
            logger.warning("Could not find vcvarsall.bat. MSVC environment cannot be set up.")
            return None

        try:
            self.compile_progress.emit("Setting up MSVC environment...")
            # Use a batch script to capture the environment after running vcvarsall.bat
            command = f'"{vcvars_path}" x64 >nul 2>&1 && set'
            result = subprocess.run(command, capture_output=True, text=True, shell=True, check=True, timeout=30)
            
            env = os.environ.copy()
            for line in result.stdout.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    env[key] = value
                    
            logger.info("Successfully captured MSVC environment.")
            self._compiler_cache['msvc_env'] = env
            return env
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Failed to capture MSVC environment using vcvarsall.bat: {e}")
            self._compiler_cache['msvc_env'] = None
            return None

    def _parse_compiler_output(self, output: str, compiler_type: CompilerType) -> Tuple[List[str], List[str]]:
        """Parse compiler output to extract warnings and errors."""
        warnings = []
        errors = []
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if compiler_type == CompilerType.MSVC:
                if ': warning ' in line.lower():
                    warnings.append(line)
                elif ': error ' in line.lower():
                    errors.append(line)
            else:  # GCC/Clang
                if ': warning:' in line:
                    warnings.append(line)
                elif ': error:' in line:
                    errors.append(line)
                    
        return warnings, errors

    def _get_unique_library_name(self, fsm_name: str, compiler_type: CompilerType) -> str:
        """Generate a unique library name to avoid conflicts."""
        self._build_counter += 1
        timestamp = int(time.time() * 1000) % 100000  # Last 5 digits of timestamp
        return f"{fsm_name}_{compiler_type.value}_{self._build_counter}_{timestamp}"

    @pyqtSlot(str, str, str, bool)
    def run_compile(self, c_code: str, h_code: str, fsm_name: str, optimize: bool = True):
        """Enhanced compilation with better error handling and optimization options."""
        self.compile_started.emit()
        start_time = time.time()
        
        build_dir_path = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "build"
        
        try:
            build_dir_path.mkdir(parents=True, exist_ok=True)
            build_dir = str(build_dir_path)

            # Generate unique library name
            available_compilers = self._detect_available_compilers()
            if not available_compilers:
                result = CompilationResult(
                    success=False,
                    library_path="",
                    output="No C compiler found. Please install Visual Studio C++ Build Tools, MinGW/GCC, or Clang.",
                    compiler_type=CompilerType.UNKNOWN,
                    compilation_time=0,
                    warnings=[],
                    errors=["No compiler available"]
                )
                self.compile_finished.emit(result)
                return

            # Use the first available compiler
            compiler_type, compiler_path = available_compilers[0]
            unique_name = self._get_unique_library_name(fsm_name, compiler_type)
            
            self.compile_progress.emit(f"Using {compiler_type.value.upper()} compiler...")

            c_path = os.path.join(build_dir, f"{unique_name}.c")
            h_path = os.path.join(build_dir, f"{unique_name}.h")

            # Write source files
            with open(c_path, 'w', encoding='utf-8') as f:
                f.write(c_code)
            with open(h_path, 'w', encoding='utf-8') as f:
                f.write(h_code)

            env = os.environ.copy()
            command = []
            
            if compiler_type == CompilerType.MSVC:
                msvc_env = self._get_msvc_environment()
                if msvc_env:
                    env = msvc_env
                    lib_ext = ".dll"
                    lib_path = os.path.join(build_dir, f"{unique_name}{lib_ext}")
                    
                    # Enhanced MSVC flags
                    flags = ['/LD', '/W3', '/D', 'FSM_CORE_BUILD_DLL']
                    if optimize:
                        flags.extend(['/O2', '/DNDEBUG'])
                    else:
                        flags.extend(['/Od', '/D_DEBUG', '/Zi'])
                        
                    command = ['cl'] + flags + [f'/Fe:{lib_path}', c_path]
                else:
                    raise RuntimeError("MSVC environment setup failed")
                    
            else:  # GCC or Clang
                if sys.platform == "win32":
                    lib_ext = ".dll"
                    base_flags = ['-shared']
                elif sys.platform == "darwin":
                    lib_ext = ".dylib"
                    base_flags = ['-dynamiclib']
                else:  # Linux
                    lib_ext = ".so"
                    base_flags = ['-shared', '-fPIC']
                
                lib_path = os.path.join(build_dir, f"{unique_name}{lib_ext}")
                
                # Enhanced GCC/Clang flags
                flags = base_flags + ['-Wall', '-Wextra']
                if optimize:
                    flags.extend(['-O2', '-DNDEBUG'])
                else:
                    flags.extend(['-O0', '-g', '-D_DEBUG'])
                    
                command = [compiler_path] + flags + ['-o', lib_path, c_path]

            self.compile_progress.emit("Compiling...")
            logger.info(f"Compilation command: {' '.join(command)}")
            
            # Run compilation
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=False,
                cwd=build_dir,
                env=env,
                timeout=60  # 60 second timeout
            )

            compilation_time = time.time() - start_time
            output = f"--- Compiler: {compiler_type.value.upper()} ---\n"
            output += f"--- Command: {' '.join(command)} ---\n"
            output += f"--- STDOUT ---\n{process.stdout}\n"
            output += f"--- STDERR ---\n{process.stderr}\n"
            output += f"--- Compilation Time: {compilation_time:.2f}s ---"
            
            warnings, errors = self._parse_compiler_output(process.stderr, compiler_type)
            
            result = CompilationResult(
                success=process.returncode == 0,
                library_path=lib_path if process.returncode == 0 else "",
                output=output,
                compiler_type=compiler_type,
                compilation_time=compilation_time,
                warnings=warnings,
                errors=errors
            )
            
            self.compile_finished.emit(result)
            
        except subprocess.TimeoutExpired:
            result = CompilationResult(
                success=False,
                library_path="",
                output="Compilation timed out after 60 seconds.",
                compiler_type=CompilerType.UNKNOWN,
                compilation_time=60,
                warnings=[],
                errors=["Compilation timeout"]
            )
            self.compile_finished.emit(result)
            
        except Exception as e:
            logger.error(f"C compilation failed with unexpected error: {e}", exc_info=True)
            result = CompilationResult(
                success=False,
                library_path="",
                output=f"An unexpected error occurred during compilation: {e}",
                compiler_type=CompilerType.UNKNOWN,
                compilation_time=time.time() - start_time,
                warnings=[],
                errors=[str(e)]
            )
            self.compile_finished.emit(result)

class CSimulationManager(QObject):
    
    simulationStateChanged = pyqtSignal(bool)  # True if active, False if inactive
    stateTransitioned = pyqtSignal(str, str)   # from_state, to_state
    eventTriggered = pyqtSignal(str, bool)     # event_name, handled

    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        
        # C Library interface
        self.c_library = None
        self.c_fsm_init = None
        self.c_fsm_run = None
        self.c_fsm_get_current_state = None
        self.c_fsm_get_state_name = None
        self.c_fsm_cleanup = None
        
        # FSM State tracking
        self.fsm_states: Dict[str, FSMState] = {}
        self.fsm_events: Dict[str, FSMEvent] = {}
        self.current_state_id = -1
        self.previous_state_id = -1
        
        # Manager state
        self._is_compiling = False
        self._is_initialized = False
        self._library_path = None
        self._compilation_result: Optional[CompilationResult] = None
        
        # Auto-refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_state)
        self._refresh_timer.setInterval(100)  # 100ms refresh rate
        
        self._cleanup_old_builds()
        self._setup_worker()

    def _cleanup_old_builds(self):
        """Enhanced cleanup with better error handling."""
        build_dir_path = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "build"
        if build_dir_path.exists():
            logger.info(f"Cleaning up old build directory: {build_dir_path}")
            try:
                # Force unload any loaded libraries first
                if self.c_library:
                    self._unload_library()
                    
                # Clean up old files
                for file_path in build_dir_path.glob("*"):
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                    except OSError as e:
                        logger.warning(f"Could not remove file {file_path}: {e}")
                        
            except OSError as e:
                logger.warning(f"Could not completely clean up old build directory: {e}")

    def _setup_worker(self):
        """Enhanced worker setup with progress tracking."""
        self.compile_thread = QThread()
        self.compile_worker = CCompilerWorker()
        self.compile_worker.moveToThread(self.compile_thread)
        
        # Connect signals
        self.compile_worker.compile_started.connect(self._on_compile_started)
        self.compile_worker.compile_progress.connect(self._on_compile_progress)
        self.compile_worker.compile_finished.connect(self._on_compile_finished)
        
        self.compile_thread.start()

    def create_dock_widget_contents(self) -> QWidget:
        """Enhanced UI with better organization and monitoring."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Main splitter
        splitter = QSplitter(Qt.Vertical)
        
        # Top panel - Controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Compilation Controls
        compile_group = QGroupBox("Compilation")
        compile_layout = QVBoxLayout(compile_group)
        
        compile_controls = QHBoxLayout()
        self.compile_btn = QPushButton("Compile FSM", icon=get_standard_icon(QStyle.SP_CommandLink))
        self.compile_btn.clicked.connect(self.on_compile_fsm)
        
        self.optimize_cb = QCheckBox("Optimize (-O2)")
        self.optimize_cb.setChecked(True)
        self.optimize_cb.setToolTip("Enable compiler optimizations")
        
        compile_controls.addWidget(self.compile_btn)
        compile_controls.addWidget(self.optimize_cb)
        compile_controls.addStretch()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        
        compile_layout.addLayout(compile_controls)
        compile_layout.addWidget(self.progress_bar)
        compile_layout.addWidget(self.progress_label)
        
        # Simulation Controls
        sim_group = QGroupBox("Simulation Control")
        sim_layout = QHBoxLayout(sim_group)
        
        self.init_btn = QPushButton("Initialize", icon=get_standard_icon(QStyle.SP_MediaPlay))
        self.init_btn.clicked.connect(self.on_initialize_fsm)
        
        self.reset_btn = QPushButton("Reset", icon=get_standard_icon(QStyle.SP_MediaSkipBackward))
        self.reset_btn.clicked.connect(self.on_initialize_fsm)
        
        self.auto_refresh_cb = QCheckBox("Auto Refresh")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.toggled.connect(self._toggle_auto_refresh)
        
        sim_layout.addWidget(self.init_btn)
        sim_layout.addWidget(self.reset_btn)
        sim_layout.addStretch()
        sim_layout.addWidget(self.auto_refresh_cb)
        
        # Event Controls
        event_group = QGroupBox("Event Trigger")
        event_layout = QHBoxLayout(event_group)
        
        self.event_combo = QComboBox()
        self.event_combo.setMinimumWidth(150)
        
        self.trigger_btn = QPushButton("Trigger Event")
        self.trigger_btn.clicked.connect(self.on_trigger_event)
        
        self.step_count_spin = QSpinBox()
        self.step_count_spin.setRange(1, 1000)
        self.step_count_spin.setValue(1)
        self.step_count_spin.setPrefix("Steps: ")
        
        event_layout.addWidget(QLabel("Event:"))
        event_layout.addWidget(self.event_combo, 1)
        event_layout.addWidget(self.step_count_spin)
        event_layout.addWidget(self.trigger_btn)
        
        # Add groups to top panel
        top_layout.addWidget(compile_group)
        top_layout.addWidget(sim_group)
        top_layout.addWidget(event_group)
        
        # Status Panel
        status_group = QGroupBox("Status & State Information")
        status_layout = QVBoxLayout(status_group)
        
        # Status display
        status_info = QHBoxLayout()
        self.status_label = QLabel("Status: Uncompiled")
        self.status_label.setWordWrap(True)
        
        # Compilation info
        self.compilation_info = QLabel("")
        self.compilation_info.setFont(QFont("Consolas", 8))
        self.compilation_info.setStyleSheet("QLabel { color: gray; }")
        
        status_info.addWidget(self.status_label, 1)
        status_layout.addLayout(status_info)
        status_layout.addWidget(self.compilation_info)
        
        # State tree
        self.state_tree = QTreeWidget()
        self.state_tree.setHeaderLabels(["State/Event", "ID", "Status"])
        self.state_tree.setMaximumHeight(150)
        status_layout.addWidget(self.state_tree)
        
        top_layout.addWidget(status_group)
        splitter.addWidget(top_widget)
        
        # Bottom panel - Output
        output_group = QGroupBox("Compiler Output & Simulation Log")
        output_layout = QVBoxLayout(output_group)
        
        self.compiler_output = QTextEdit()
        self.compiler_output.setReadOnly(True)
        self.compiler_output.setFont(QFont("Consolas", 9))
        self.compiler_output.setPlaceholderText(
            "Compiler output and simulation logs will appear here.\n"
            "- Compilation messages\n"
            "- State transitions\n"
            "- Event handling results"
        )
        output_layout.addWidget(self.compiler_output)
        
        splitter.addWidget(output_group)
        splitter.setSizes([300, 200])  # Give more space to controls
        
        layout.addWidget(splitter)
        
        self._update_ui_state()
        return container

    def _toggle_auto_refresh(self, enabled: bool):
        """Toggle automatic state refresh."""
        if enabled and self._is_initialized:
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()

    def _refresh_state(self):
        """Refresh the current FSM state."""
        if not self._is_initialized or not self.c_fsm_get_current_state:
            return
            
        try:
            new_state_id = self.c_fsm_get_current_state()
            if new_state_id != self.current_state_id:
                self.previous_state_id = self.current_state_id
                self.current_state_id = new_state_id
                
                # Find state names
                from_state = "Unknown"
                to_state = "Unknown"
                
                for name, state in self.fsm_states.items():
                    if state.id == self.previous_state_id:
                        from_state = name
                    if state.id == self.current_state_id:
                        to_state = name
                        
                self.stateTransitioned.emit(from_state, to_state)
                self._update_state_display()
                
        except Exception as e:
            logger.error(f"Error refreshing state: {e}")

    @pyqtSlot()
    def on_initialize_fsm(self):
        """Initializes or resets the compiled FSM in the C library."""
        if not self.c_library or not self.c_fsm_init:
            QMessageBox.warning(self.mw, "Not Compiled", "Please compile the FSM before initializing.")
            return

        try:
            self.c_fsm_init()
            self._is_initialized = True
            self.compiler_output.append("\n--- FSM Initialized/Reset ---")
            
            # Perform an initial state refresh
            self._refresh_state()
            
            self.status_label.setText("Status: Initialized. Ready to trigger events.")
            logger.info("C FSM initialized successfully.")
        except Exception as e:
            self._is_initialized = False
            self.status_label.setText("Status: Initialization failed.")
            self.compiler_output.append(f"ERROR during FSM initialization: {e}")
            logger.error(f"Failed to initialize C FSM: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "Initialization Error", f"An error occurred while initializing the FSM library:\n{e}")

        self._update_ui_state()
        self.simulationStateChanged.emit(self._is_initialized)

    @pyqtSlot()
    def on_trigger_event(self):
        """Triggers an event in the compiled FSM."""
        if not self._is_initialized or not self.c_fsm_run:
            QMessageBox.warning(self.mw, "Not Initialized", "Please initialize the FSM simulation first.")
            return

        event_name = self.event_combo.currentText()
        if not event_name or event_name not in self.fsm_events:
            QMessageBox.warning(self.mw, "Invalid Event", f"Event '{event_name}' is not defined in the FSM.")
            return
            
        event_id = self.fsm_events[event_name].id
        steps = self.step_count_spin.value()
        
        self.compiler_output.append(f"\n--- Triggering event: {event_name} (ID: {event_id}) for {steps} step(s) ---")
        
        try:
            for i in range(steps):
                self.c_fsm_run(event_id)
                self._refresh_state()
            
            # Find the current state name for logging
            current_state_name = "Unknown"
            for name, state_info in self.fsm_states.items():
                if state_info.id == self.current_state_id:
                    current_state_name = name
                    break
            
            self.compiler_output.append(f"Event triggered successfully. New state: {current_state_name}")
            self.eventTriggered.emit(event_name, True)
        except Exception as e:
            self.compiler_output.append(f"ERROR during event trigger: {e}")
            logger.error(f"Failed to trigger C FSM event: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "Event Trigger Error", f"An error occurred while running the FSM:\n{e}")
            self.eventTriggered.emit(event_name, False)
            
        self._update_ui_state()


    def on_compile_fsm(self):
        """Enhanced compilation with better validation."""
        editor = self.mw.current_editor()
        if not editor:
            QMessageBox.warning(self.mw, "No Diagram", "Please open a diagram to compile.")
            return

        diagram_data = editor.scene.get_diagram_data()
        if not diagram_data.get('states'):
            QMessageBox.warning(self.mw, "Empty Diagram", "Cannot compile an empty FSM.")
            return
            
        # Validate diagram
        states = diagram_data.get('states', [])
        transitions = diagram_data.get('transitions', [])
        
        if len(states) == 0:
            QMessageBox.warning(self.mw, "Invalid Diagram", "FSM must have at least one state.")
            return
            
        self._is_compiling = True
        self._update_ui_state()
        self.compiler_output.clear()
        self.compiler_output.append("=== Starting FSM Compilation ===\n")
        self.compiler_output.append(f"States: {len(states)}, Transitions: {len(transitions)}\n")

        try:
            fsm_name = "bsm_compiled_fsm"
            self.compiler_output.append("Generating C code...\n")
            
            code_dict = generate_c_code_content(diagram_data, fsm_name, "Generic C (Header/Source Pair)")
            c_code = code_dict['c']
            h_code = code_dict['h']
            
            # Parse FSM structure from header
            self._parse_fsm_structure(h_code, diagram_data)
            
            self.compiler_output.append("Code generated successfully. Starting compilation...\n")
            
            # Start compilation
            QMetaObject.invokeMethod(
                self.compile_worker, "run_compile", Qt.QueuedConnection,
                Q_ARG(str, c_code), Q_ARG(str, h_code), Q_ARG(str, fsm_name), 
                Q_ARG(bool, self.optimize_cb.isChecked())
            )
            
        except Exception as e:
            self.compiler_output.append(f"ERROR during code generation:\n{e}\n")
            logger.error(f"Code generation error: {e}", exc_info=True)
            self._is_compiling = False
            self._update_ui_state()

    def _parse_fsm_structure(self, h_code: str, diagram_data: dict):
        """Enhanced FSM structure parsing."""
        self.fsm_states.clear()
        self.fsm_events.clear()
        
        # Parse states from enum and diagram data
        state_enum = self._parse_c_enum(h_code, "STATE_")
        states_data = diagram_data.get('states', [])
        
        for state_data in states_data:
            state_name = state_data.get('name', 'Unknown')
            # The key for state_enum should be the SANITIZED c_name without the prefix
            sanitized_name_key = sanitize_c_identifier(state_name, "s_").upper()
            if sanitized_name_key in state_enum:
                self.fsm_states[state_name] = FSMState(
                    name=state_name,
                    id=state_enum[sanitized_name_key],
                    entry_actions=state_data.get('entry_actions', []),
                    exit_actions=state_data.get('exit_actions', [])
                )
        
        # Parse events from enum and diagram data
        event_enum = self._parse_c_enum(h_code, "EVENT_")
        transitions_data = diagram_data.get('transitions', [])
        
        # Collect unique events
        unique_events = set()
        for trans in transitions_data:
            event = trans.get('event', '')
            if event and event != 'null':
                unique_events.add(event)
        
        for event_name in unique_events:
            sanitized_event_key = sanitize_c_identifier(event_name, "evt_").upper()
            if sanitized_event_key in event_enum:
                self.fsm_events[event_name] = FSMEvent(
                    name=event_name,
                    id=event_enum[sanitized_event_key],
                    description=f"Event: {event_name}"
                )

    def _parse_c_enum(self, h_code: str, prefix: str) -> Dict[str, int]:
        """Enhanced enum parser with better error handling."""
        enum_map = {}
        in_enum = False
        value = 0
        
        try:
            for line in h_code.splitlines():
                line = line.strip()
                
                if "typedef enum" in line: # Simplified check
                    in_enum = True
                    continue
                    
                if in_enum:
                    if line.startswith(prefix):
                        # Handle explicit values like STATE_IDLE = 0,
                        if '=' in line:
                            parts = line.split('=')
                            name = parts[0].strip()
                            try:
                                value = int(parts[1].split(',')[0].strip())
                            except (ValueError, IndexError):
                                pass
                        else:
                            name = line.split(',')[0].strip()
                            
                        if name:
                            # Use the full name from the enum (e.g., STATE_OFF) as the key
                            enum_map[name] = value
                            value += 1
                            
                    elif "}" in line:
                        break
                        
        except Exception as e:
            logger.error(f"Error parsing enum with prefix {prefix}: {e}")
            
        return enum_map

    @pyqtSlot()
    def _on_compile_started(self):
        """Handle compilation start."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_label.setText("Preparing compilation...")

    @pyqtSlot(str)
    def _on_compile_progress(self, message: str):
        """Handle compilation progress updates."""
        self.progress_label.setText(message)
        self.compiler_output.append(f"[PROGRESS] {message}")

    @pyqtSlot(CompilationResult)
    def _on_compile_finished(self, result: CompilationResult):
        """Enhanced compilation result handling."""
        self._is_compiling = False
        self._compilation_result = result
        
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        # Display compilation results
        self.compiler_output.append("\n=== Compilation Results ===")
        self.compiler_output.append(f"Success: {result.success}")
        self.compiler_output.append(f"Compiler: {result.compiler_type.value.upper()}")
        self.compiler_output.append(f"Time: {result.compilation_time:.2f}s")
        self.compiler_output.append(f"Warnings: {len(result.warnings)}")
        self.compiler_output.append(f"Errors: {len(result.errors)}")
        
        if result.warnings:
            self.compiler_output.append("\n--- WARNINGS ---")
            for warning in result.warnings:
                self.compiler_output.append(warning)
                
        if result.errors:
            self.compiler_output.append("\n--- ERRORS ---")
            for error in result.errors:
                self.compiler_output.append(error)
        
        self.compiler_output.append(f"\n{result.output}")
        
        if result.success:
            self._library_path = result.library_path
            self._load_library()
            self.status_label.setText("Status: Compiled successfully. Ready to initialize.")
            
            # Update compilation info
            self.compilation_info.setText(
                f"Compiled with {result.compiler_type.value.upper()} in {result.compilation_time:.2f}s | "
                f"{len(result.warnings)} warnings, {len(result.errors)} errors"
            )
        else:
            self.status_label.setText("Status: Compilation failed.")
            self.compilation_info.setText("Compilation failed - see output for details")
            self.c_library = None
            self._is_initialized = False
        
        self._update_ui_state()

    def _load_library(self):
        """Loads the compiled shared library and defines function prototypes."""
        if not self._library_path or not os.path.exists(self._library_path):
            logger.error("Cannot load C library: Path is invalid or file does not exist.")
            return

        try:
            self._unload_library() # Ensure any previous library is unloaded
            self.c_library = ctypes.CDLL(self._library_path)
            
            fsm_name = self._compilation_result.library_path.split('_')[0]
            base_name = os.path.basename(fsm_name)

            # Define function prototypes
            self.c_fsm_init = getattr(self.c_library, f"{base_name}_init")
            self.c_fsm_run = getattr(self.c_library, f"{base_name}_run")
            self.c_fsm_get_current_state = getattr(self.c_library, f"{base_name}_get_current_state")
            
            # Set argtypes and restypes
            self.c_fsm_init.argtypes = []
            self.c_fsm_init.restype = None
            self.c_fsm_run.argtypes = [ctypes.c_int]
            self.c_fsm_run.restype = None
            self.c_fsm_get_current_state.argtypes = []
            self.c_fsm_get_current_state.restype = ctypes.c_int
            
            logger.info(f"Successfully loaded C FSM library from {self._library_path}")
        except (AttributeError, OSError) as e:
            self.c_library = None
            logger.error(f"Failed to load C FSM library or its functions: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "Library Load Error", f"Could not load the compiled library:\n{e}")

    def _unload_library(self):
        """Unloads the C library, handling OS-specific mechanisms."""
        if not self.c_library:
            return

        handle = self.c_library._handle
        self.c_library = None
        self.c_fsm_init = None
        self.c_fsm_run = None
        self.c_fsm_get_current_state = None

        if sys.platform == "win32":
            ctypes.windll.kernel32.FreeLibrary(handle)
        else: # Linux/macOS
            ctypes.cdll.LoadLibrary('libdl.so').dlclose(handle)
        logger.info("Unloaded previous C FSM library.")

    def _update_ui_state(self):
        """Updates the enabled/disabled state of UI controls."""
        is_compiled = bool(self._compilation_result and self._compilation_result.success)
        
        self.compile_btn.setEnabled(not self._is_compiling)
        self.init_btn.setEnabled(is_compiled and not self._is_compiling)
        self.reset_btn.setEnabled(is_compiled and self._is_initialized and not self._is_compiling)
        self.trigger_btn.setEnabled(self._is_initialized and not self._is_compiling)
        self.event_combo.setEnabled(self._is_initialized and not self._is_compiling)
        
        self._update_state_display()

    def _update_state_display(self):
        """Updates the state tree and event combo box."""
        self.state_tree.clear()
        self.event_combo.clear()

        # States
        states_root = QTreeWidgetItem(self.state_tree, ["States"])
        for name, state in sorted(self.fsm_states.items(), key=lambda item: item[1].id):
            status = "CURRENT" if state.id == self.current_state_id else ""
            item = QTreeWidgetItem(states_root, [name, str(state.id), status])
            if status == "CURRENT":
                item.setBackground(0, QColor("#1E3A8A")) # Dark blue background
                item.setForeground(0, Qt.white)
        
        # Events
        events_root = QTreeWidgetItem(self.state_tree, ["Events"])
        for name, event in sorted(self.fsm_events.items()):
            QTreeWidgetItem(events_root, [name, str(event.id), ""])
            self.event_combo.addItem(name)

        self.state_tree.expandAll()

    def shutdown(self):
        """Cleans up resources when the application closes."""
        self._refresh_timer.stop()
        if self.compile_thread.isRunning():
            self.compile_thread.quit()
            self.compile_thread.wait(1000)
        self._unload_library()
        self._cleanup_old_builds()