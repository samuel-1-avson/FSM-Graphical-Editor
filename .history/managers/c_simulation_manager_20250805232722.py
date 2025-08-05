
# fsm_designer_project/managers/c_simulation_manager.py
import os
import logging
import subprocess
import tempfile
import sys
import ctypes
from typing import Dict, List
import shutil
from pathlib import Path

# --- FIX: Add all necessary PyQt imports ---
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit, QGroupBox,
    QHeaderView, QTableWidget, QTableWidgetItem, QComboBox,
    QStyle, QMessageBox, QHBoxLayout, QLabel, QInputDialog
)
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QThread, QMetaObject, Q_ARG, Qt, QStandardPaths, QDir

from ..utils import get_standard_icon
from ..utils.c_code_generator import generate_c_code_content

logger = logging.getLogger(__name__)

# --- Worker for background compilation ---
class CCompilerWorker(QObject):
    compile_finished = pyqtSignal(bool, str, str)  # success, library_path, output

    def _find_compiler(self) -> (str, List[str]):
        """Detects the available C compiler (MSVC cl.exe or gcc)."""
        # Prefer cl.exe if available (often set up by "Developer Command Prompt for VS")
        try:
            subprocess.run(['cl', '/?'], capture_output=True, check=True, timeout=5)
            logger.info("Found MSVC compiler (cl.exe).")
            # /LD creates a DLL. /Fe sets the output name. /W3 is a common warning level.
            # /D FSM_BUILD_DLL is crucial for our export macro.
            return 'cl', ['cl', '/LD', '/W3', '/D', 'FSM_BUILD_DLL', '/Fe:']
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.info("cl.exe not found or not working, falling back to gcc.")
            # Fallback to gcc
            if sys.platform == "win32":
                return 'gcc', ['gcc', '-shared', '-o']
            elif sys.platform == "darwin":
                return 'gcc', ['gcc', '-dynamiclib', '-o']
            else: # Linux
                return 'gcc', ['gcc', '-shared', '-fPIC', '-o']

    @pyqtSlot(str, str, str)
    def run_compile(self, c_code: str, h_code: str, fsm_name: str):
        """
        Compiles the given C code into a shared library in a dedicated build directory.
        """
        # --- MODIFICATION: Use a dedicated app build directory instead of a system temp dir ---
        build_dir_path = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "build"
        try:
            build_dir_path.mkdir(parents=True, exist_ok=True)
            build_dir = str(build_dir_path)

            c_path = os.path.join(build_dir, f"{fsm_name}.c")
            h_path = os.path.join(build_dir, f"{fsm_name}.h")

            with open(c_path, 'w', encoding='utf-8') as f:
                f.write(c_code)
            with open(h_path, 'w', encoding='utf-8') as f:
                f.write(h_code)

            compiler_name, compiler_base_cmd = self._find_compiler()

            lib_ext = ".dll" if sys.platform == "win32" else ".so" if sys.platform != "darwin" else ".dylib"
            lib_path = os.path.join(build_dir, f"{fsm_name}{lib_ext}")

            if compiler_name == 'cl':
                command = compiler_base_cmd + [lib_path, c_path]
            else: # gcc
                command = compiler_base_cmd + [lib_path, c_path]

            logger.info(f"Running compiler command: {' '.join(command)}")
            
            use_shell = sys.platform == "win32"

            # Execute from the build directory
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=use_shell,
                cwd=build_dir # Set the working directory for the compiler
            )

            output = f"--- Compiler: {compiler_name} ---\n--- STDOUT ---\n{process.stdout}\n--- STDERR ---\n{process.stderr}"
            if process.returncode == 0:
                self.compile_finished.emit(True, lib_path, output)
            else:
                self.compile_finished.emit(False, "", output)
        # --- END MODIFICATION ---
        except FileNotFoundError:
            self.compile_finished.emit(False, "", "No C compiler (gcc or cl.exe) found. Please install a C compiler and ensure it's in your system's PATH, or run this application from a Developer Command Prompt for Visual Studio.")
        except Exception as e:
            logger.error(f"C compilation failed with unexpected error: {e}", exc_info=True)
            self.compile_finished.emit(False, "", f"An unexpected error occurred during compilation: {e}")

# --- Manager and UI class ---
class CSimulationManager(QObject):
    
    simulationStateChanged = pyqtSignal(bool) # True if active, False if inactive

    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        
        self.c_library = None
        self.c_fsm_init = None
        self.c_fsm_run = None
        self.c_fsm_get_current_state = None
        self.c_fsm_get_state_name = None
        self.c_state_enum = {}
        self.c_event_enum = {}

        self._is_compiling = False
        self._is_initialized = False
        self._library_path = None

        self._cleanup_old_builds()
        self._setup_worker()

    def _cleanup_old_builds(self):
        """Remove old compiled libraries from previous sessions."""
        build_dir_path = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "build"
        if build_dir_path.exists():
            logger.info(f"Cleaning up old build directory: {build_dir_path}")
            try:
                shutil.rmtree(build_dir_path)
            except OSError as e:
                logger.warning(f"Could not completely clean up old build directory: {e}")

    def _setup_worker(self):
        self.compile_thread = QThread()
        self.compile_worker = CCompilerWorker()
        self.compile_worker.moveToThread(self.compile_thread)
        self.compile_worker.compile_finished.connect(self._on_compile_finished)
        self.compile_thread.start()
        
    def create_dock_widget_contents(self) -> QWidget:
        """Creates the main widget for the C Simulation dock."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Controls
        controls_group = QGroupBox("C Simulation Control")
        controls_layout = QHBoxLayout(controls_group)
        self.compile_btn = QPushButton("Compile FSM", icon=get_standard_icon(QStyle.SP_CommandLink))
        self.compile_btn.clicked.connect(self.on_compile_fsm)
        self.init_btn = QPushButton("Initialize", icon=get_standard_icon(QStyle.SP_MediaPlay))
        self.init_btn.clicked.connect(self.on_initialize_fsm)
        self.reset_btn = QPushButton("Reset", icon=get_standard_icon(QStyle.SP_MediaSkipBackward))
        self.reset_btn.clicked.connect(self.on_initialize_fsm) # Reset is just re-init
        controls_layout.addWidget(self.compile_btn)
        controls_layout.addWidget(self.init_btn)
        controls_layout.addWidget(self.reset_btn)
        layout.addWidget(controls_group)

        # Event Triggering
        event_group = QGroupBox("Event Trigger")
        event_layout = QHBoxLayout(event_group)
        self.event_combo = QComboBox()
        self.trigger_btn = QPushButton("Trigger")
        self.trigger_btn.clicked.connect(self.on_trigger_event)
        event_layout.addWidget(self.event_combo, 1)
        event_layout.addWidget(self.trigger_btn)
        layout.addWidget(event_group)
        
        # Status & Output
        status_group = QGroupBox("Status & Output")
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel("Status: Uncompiled")
        self.compiler_output = QTextEdit()
        self.compiler_output.setReadOnly(True)
        self.compiler_output.setPlaceholderText("Compiler output and simulation logs will appear here.")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.compiler_output, 1)
        layout.addWidget(status_group)

        self._update_ui_state()
        return container

    def on_compile_fsm(self):
        editor = self.mw.current_editor()
        if not editor:
            QMessageBox.warning(self.mw, "No Diagram", "Please open a diagram to compile.")
            return

        diagram_data = editor.scene.get_diagram_data()
        if not diagram_data.get('states'):
            QMessageBox.warning(self.mw, "Empty Diagram", "Cannot compile an empty FSM.")
            return
            
        self._is_compiling = True
        self._update_ui_state()
        self.compiler_output.setText("Generating C code...\n")

        try:
            fsm_name = "bsm_compiled_fsm"
            code_dict = generate_c_code_content(diagram_data, fsm_name, "Generic C (Header/Source Pair)")
            c_code = code_dict['c']
            h_code = code_dict['h']
            
            # --- Parse Enums from Header ---
            self.c_state_enum = self._parse_c_enum(h_code, "STATE_")
            self.c_event_enum = self._parse_c_enum(h_code, "EVENT_")

            self.compiler_output.append("Code generated. Invoking compiler...\n")
            QMetaObject.invokeMethod(self.compile_worker, "run_compile", Qt.QueuedConnection,
                                     Q_ARG(str, c_code), Q_ARG(str, h_code), Q_ARG(str, fsm_name))
        except Exception as e:
            self.compiler_output.append(f"ERROR during code generation:\n{e}")
            self._is_compiling = False
            self._update_ui_state()

    def _parse_c_enum(self, h_code: str, prefix: str) -> Dict[str, int]:
        """A simple parser to extract enum values from the generated header."""
        enum_map = {}
        in_enum = False
        value = 0
        for line in h_code.splitlines():
            line = line.strip()
            if "typedef enum" in line:
                in_enum = True
                continue
            if in_enum and line.startswith(prefix):
                name = line.split(',')[0].replace(prefix, '')
                enum_map[name] = value
                value += 1
            if in_enum and "}" in line:
                break
        return enum_map

    @pyqtSlot(bool, str, str)
    def _on_compile_finished(self, success: bool, library_path: str, output: str):
        self._is_compiling = False
        self.compiler_output.append(f"Compiler finished.\n{output}")
        if success:
            self._library_path = library_path
            self._load_library()
            self.status_label.setText(f"Status: Compiled successfully. Ready to initialize.")
        else:
            self.status_label.setText("Status: Compile Error.")
            self.c_library = None
        self._update_ui_state()

    def _load_library(self):
        try:
            # Unload the old library if it exists to allow recompiling
            if self.c_library:
                if sys.platform == "win32":
                    ctypes.windll.kernel32.FreeLibrary(self.c_library._handle)
                else:
                    # On Linux/macOS, ctypes doesn't have a public unload.
                    # The OS should handle it, but for repeated compiles,
                    # this can be an issue. A more robust solution might
                    # involve copying the DLL to a unique name each time.
                    # For now, we'll rely on the OS.
                    pass
                self.c_library = None

            self.c_library = ctypes.CDLL(self._library_path)
            
            fsm_name = os.path.basename(self._library_path).split('.')[0]
            
            # Define function prototypes
            self.c_fsm_init = getattr(self.c_library, f"{fsm_name}_init")
            self.c_fsm_init.restype = None

            self.c_fsm_run = getattr(self.c_library, f"{fsm_name}_run")
            self.c_fsm_run.argtypes = [ctypes.c_int] # event_id
            self.c_fsm_run.restype = None

            self.c_fsm_get_current_state = getattr(self.c_library, f"{fsm_name}_get_current_state")
            self.c_fsm_get_current_state.restype = ctypes.c_int

            logger.info(f"Successfully loaded C library: {self._library_path}")
            self.event_combo.clear()
            self.event_combo.addItem("None (Internal Step)", -1) # FSM_NO_EVENT is -1
            for name, val in self.c_event_enum.items():
                self.event_combo.addItem(name, val)

        except (AttributeError, OSError) as e:
            self.compiler_output.append(f"\nERROR loading shared library:\n{e}")
            self.c_library = None
            self._update_ui_state()

    def on_initialize_fsm(self):
        if not self.c_library: return
        self.c_fsm_init()
        self._is_initialized = True
        self.compiler_output.append("\n--- C FSM Initialized ---")
        self._update_ui_state()

    def on_trigger_event(self):
        if not self._is_initialized: return

        event_id = self.event_combo.currentData()
        event_name = self.event_combo.currentText()
        
        self.compiler_output.append(f"Running with event: {event_name} (ID: {event_id})")
        self.c_fsm_run(event_id)
        self._update_ui_state()

    def _update_ui_state(self):
        self.compile_btn.setEnabled(not self._is_compiling)
        self.compile_btn.setText("Compiling..." if self._is_compiling else "Compile FSM")
        
        is_ready = self.c_library is not None
        self.init_btn.setEnabled(is_ready)
        self.reset_btn.setEnabled(self._is_initialized)
        
        run_enabled = self._is_initialized
        self.event_combo.setEnabled(run_enabled)
        self.trigger_btn.setEnabled(run_enabled)

        if self._is_initialized:
            state_id = self.c_fsm_get_current_state()
            state_name = "Unknown"
            for name, val in self.c_state_enum.items():
                if val == state_id:
                    state_name = name
                    break
            self.status_label.setText(f"Status: Initialized. Current State: {state_name} ({state_id})")
        
        self.simulationStateChanged.emit(self._is_initialized)

    def shutdown(self):
        if self.compile_thread:
            self.compile_thread.quit()
            self.compile_thread.wait(1000)
