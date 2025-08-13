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

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit, QGroupBox,
    QHeaderView, QTableWidget, QTableWidgetItem, QComboBox,
    QStyle, QMessageBox, QHBoxLayout, QLabel, QInputDialog,
    QProgressBar, QSplitter, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QSpinBox, QFrame
)
from PyQt6.QtCore import (
    QObject, pyqtSlot, pyqtSignal, QThread, QMetaObject, 
    Q_ARG, Qt, QStandardPaths, QDir, QTimer
)
from PyQt6.QtGui import QFont, QColor, QPalette

# --- MODIFIED: Corrected import path ---
from ..utils import get_standard_icon
from ..codegen.c_code_generator import generate_c_code_content, sanitize_c_identifier

logger = logging.getLogger(__name__)

class CompilerType(Enum):
    MSVC = "msvc"
    GCC = "gcc"
    CLANG = "clang"
    TCC = "tcc"  # Added Tiny C Compiler as fallback
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
        """Enhanced MSVC detection with better error handling."""
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
        
        # Also check for Visual Studio Build Tools
        for pf_path in program_files_paths:
            for version in vs_versions:
                build_tools_path = Path(pf_path) / "Microsoft Visual Studio" / version / "BuildTools" / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
                if build_tools_path.exists():
                    logger.info(f"Found vcvarsall.bat (BuildTools) at: {build_tools_path}")
                    self._compiler_cache['vcvarsall'] = str(build_tools_path)
                    return str(build_tools_path)
        
        self._compiler_cache['vcvarsall'] = None
        logger.warning("vcvarsall.bat not found. MSVC compiler will not be available.")
        return None

    def _test_msvc_availability(self, env: dict) -> bool:
        """Test if MSVC compiler is actually available with the given environment."""
        try:
            result = subprocess.run(
                ['cl', '/help'],
                capture_output=True,
                text=True,
                env=env,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _detect_available_compilers(self) -> List[Tuple[CompilerType, str]]:
        """Detect all available C compilers on the system with improved MSVC handling."""
        compilers = []
        
        # Check for GCC first (often more reliable on Windows with MSYS2/MinGW)
        gcc_path = shutil.which("gcc")
        if gcc_path:
            compilers.append((CompilerType.GCC, gcc_path))
            logger.info(f"Found GCC at: {gcc_path}")
            
        # Check for Clang
        clang_path = shutil.which("clang")
        if clang_path:
            compilers.append((CompilerType.CLANG, clang_path))
            logger.info(f"Found Clang at: {clang_path}")

        # Check for TCC (Tiny C Compiler) - lightweight fallback
        tcc_path = shutil.which("tcc")
        if tcc_path:
            compilers.append((CompilerType.TCC, tcc_path))
            logger.info(f"Found TCC at: {tcc_path}")
        
        # Check for MSVC with proper environment testing
        if sys.platform == "win32":
            vcvars_path = self._find_vcvarsall_bat()
            if vcvars_path:
                # Test if we can actually set up the MSVC environment
                test_env = self._get_msvc_environment()
                if test_env and self._test_msvc_availability(test_env):
                    compilers.append((CompilerType.MSVC, "cl"))
                    logger.info(f"MSVC compiler verified and available")
                else:
                    logger.warning("MSVC environment setup failed or compiler not accessible")
        
        if not compilers:
            logger.error("No C compilers found on system. Please install MinGW-W64, Clang, or Visual Studio.")
            
        return compilers

    def _get_msvc_environment(self) -> Optional[dict]:
        """Sets up the MSVC environment by calling vcvarsall.bat with improved error handling."""
        if 'msvc_env' in self._compiler_cache:
            return self._compiler_cache['msvc_env']

        vcvars_path = self._find_vcvarsall_bat()
        if not vcvars_path:
            logger.warning("Could not find vcvarsall.bat. MSVC environment not set.")
            self._compiler_cache['msvc_env'] = None
            return None
        
        try:
            self.compile_progress.emit("Setting up MSVC environment...")
            
            # Use a more robust approach to call vcvarsall.bat
            # First, try with cmd.exe /c instead of /S /C
            command = f'cmd.exe /c ""{vcvars_path}" x64 >nul 2>&1 && set"'
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=True,  # Use shell=True for this specific case
                check=False,  # Don't raise exception on non-zero return
                timeout=60,   # Increased timeout
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            if result.returncode != 0:
                logger.error(f"vcvarsall.bat failed with return code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                self._compiler_cache['msvc_env'] = None
                return None

            # Parse environment variables from output
            env = os.environ.copy()
            for line in result.stdout.splitlines():
                if '=' in line and not line.startswith('='):  # Skip lines starting with =
                    try:
                        key, value = line.split('=', 1)
                        env[key] = value
                    except ValueError:
                        continue  # Skip malformed lines
            
            # Verify that essential MSVC environment variables are set
            required_vars = ['VCINSTALLDIR', 'WindowsSdkDir', 'PATH']
            for var in required_vars:
                if var not in env or not env[var]:
                    logger.warning(f"Required MSVC environment variable {var} not found or empty")
            
            # Check if cl.exe is in the PATH
            cl_found = False
            for path_dir in env.get('PATH', '').split(os.pathsep):
                if path_dir and os.path.exists(os.path.join(path_dir, 'cl.exe')):
                    cl_found = True
                    break
            
            if not cl_found:
                logger.error("cl.exe not found in PATH after setting up MSVC environment")
                self._compiler_cache['msvc_env'] = None
                return None
            
            logger.info("Successfully captured MSVC environment.")
            self._compiler_cache['msvc_env'] = env
            return env
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
            logger.error(f"Failed to set up MSVC environment: {e}")
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
                elif ': error ' in line.lower() or ': fatal error ' in line.lower():
                    errors.append(line)
            elif compiler_type == CompilerType.TCC:
                if 'warning:' in line.lower():
                    warnings.append(line)
                elif 'error:' in line.lower():
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

    def _fix_include_path(self, c_code: str, original_header_name: str, new_header_name: str) -> str:
        """Fix the #include directive to use the correct header filename."""
        return c_code.replace(f'#include "{original_header_name}.h"', f'#include "{new_header_name}.h"')

    def _fix_c_code_issues(self, c_code: str, h_code: str) -> Tuple[str, str]:
        """Fix common C code generation issues for compilation."""
        
        # Fix DLL export/import issues - be more careful with replacements
        if sys.platform == "win32":
            # For header file: replace FSM_API with dllimport for external declaration
            fixed_h_code = h_code.replace('FSM_API ', '__declspec(dllimport) ')
            # For C file: replace FSM_API with dllexport for function definitions
            fixed_c_code = c_code.replace('FSM_API ', '__declspec(dllexport) ')
        else:
            fixed_h_code = h_code.replace('FSM_API ', 'extern ')
            fixed_c_code = c_code.replace('FSM_API ', '')
        
        # Add missing variable declarations and includes at the top of C file
        missing_includes = """#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>

// Missing variable declarations
static int timer_start_tick = 0;
static int current_tick = 0;
static bool event_sent = false;

// Missing constants
#define GREEN_DURATION 5
#define YELLOW_DURATION 2
#define RED_DURATION 5
#define False false
#define True true

"""
        
        # Insert the missing declarations after the first include statement
        include_pos = fixed_c_code.find('#include')
        if include_pos != -1:
            # Find the end of the include line
            include_end = fixed_c_code.find('\n', include_pos) + 1
            fixed_c_code = (fixed_c_code[:include_end] + 
                           missing_includes + 
                           fixed_c_code[include_end:])
        else:
            # If no include found, add at the beginning
            fixed_c_code = missing_includes + fixed_c_code
        
        # Remove problematic redefined macros from header
        fixed_h_code_lines = []
        for line in fixed_h_code.split('\n'):
            stripped = line.strip()
            # Skip any #define containing __declspec to avoid circular definitions
            if stripped.startswith('#define') and '__declspec' in stripped:
                continue
            fixed_h_code_lines.append(line)
        fixed_h_code = '\n'.join(fixed_h_code_lines)
        
        # Remove extra semicolons in declarations for both files
        fixed_c_code = fixed_c_code.replace(';;', ';')
        fixed_h_code = fixed_h_code.replace(';;', ';')
        
        # Fix common syntax issues
        fixed_c_code = self._fix_syntax_issues(fixed_c_code)
        
        return fixed_c_code, fixed_h_code
    
    def _fix_syntax_issues(self, c_code: str) -> str:
        """Fix common syntax issues in generated C code."""
        lines = c_code.split('\n')
        fixed_lines = []
        brace_depth = 0
        in_function = False
        current_function_name = ""
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Detect function start
            if stripped and not stripped.startswith('//') and not stripped.startswith('#'):
                if '(' in stripped and ')' in stripped and not in_function:
                    # This looks like a function declaration/definition
                    if '{' in stripped:
                        in_function = True
                        current_function_name = stripped.split('(')[0].split()[-1] if stripped.split('(') else ""
                        brace_depth = stripped.count('{') - stripped.count('}')
                    elif i + 1 < len(lines) and '{' in lines[i + 1]:
                        in_function = True
                        current_function_name = stripped.split('(')[0].split()[-1] if stripped.split('(') else ""
                elif in_function:
                    brace_depth += stripped.count('{') - stripped.count('}')
            
            # Fix assignment to constants (should be variable assignments or comments)
            if '=' in stripped and any(const in stripped for const in ['GREEN_DURATION', 'YELLOW_DURATION', 'RED_DURATION']):
                if not stripped.startswith('//'):
                    # Convert constant assignment to comment
                    for const in ['GREEN_DURATION', 'YELLOW_DURATION', 'RED_DURATION']:
                        if f'{const} = ' in stripped:
                            line = line.replace(f'{const} = ', f'// {const} = ')
            
            # Fix malformed function calls and ensure proper line endings
            if stripped and not stripped.endswith(';') and not stripped.endswith('{') and not stripped.endswith('}'):
                # Check if this looks like a statement that should end with semicolon
                if any(keyword in stripped for keyword in ['printf', 'timer_start_tick', 'event_sent']) and not stripped.startswith('//'):
                    if '=' in stripped or stripped.endswith('False') or stripped.endswith('True') or 'printf(' in stripped:
                        line = line.rstrip() + ';'
            
            # Handle function ending
            if in_function and brace_depth <= 0 and '}' in stripped:
                in_function = False
                current_function_name = ""
                brace_depth = 0
            
            fixed_lines.append(line)
            i += 1
        
        # Join the fixed lines
        result = '\n'.join(fixed_lines)
        
        # Additional fixes for specific patterns that cause issues
        result = self._fix_malformed_patterns(result)
        
        # Ensure file ends properly - count braces in final result
        open_braces = result.count('{')
        close_braces = result.count('}')
        if open_braces > close_braces:
            result += '\n' + '}' * (open_braces - close_braces)
        
        return result
    
    def _fix_malformed_patterns(self, c_code: str) -> str:
        """Fix specific malformed patterns in the generated code."""
        
        # Split into lines for processing
        lines = c_code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Fix lines that have multiple statements jammed together
            if ';}' in line and 'printf(' in line:
                # This likely has a printf statement followed by }
                parts = line.split(';}')
                if len(parts) == 2:
                    # Split into two lines
                    fixed_lines.append(parts[0] + ';')
                    if parts[1].strip():
                        fixed_lines.append(parts[1])
                    else:
                        fixed_lines.append('}')
                    continue
            
            # Fix function definitions that are all on one line
            if stripped and '(' in stripped and ')' in stripped and '{' in stripped and not stripped.startswith('//'):
                # Check if this is a malformed function with everything on one line
                if stripped.count('{') == 1 and ';' in stripped:
                    # Try to split it properly
                    before_brace = stripped.split('{')[0] + ' {'
                    after_brace = stripped.split('{')[1]
                    if after_brace.endswith('}'):
                        # Remove the closing brace, we'll add it back
                        after_brace = after_brace[:-1]
                        fixed_lines.append(line.replace(stripped, before_brace))
                        if after_brace.strip():
                            # Add the content inside the function
                            indented_content = '    ' + after_brace.strip()
                            fixed_lines.append(indented_content)
                        fixed_lines.append('}')
                        continue
            
            # Fix lines that end with extra content after function declaration
            if stripped.startswith('void ') and '{' in stripped:
                # Check for content after the opening brace
                brace_pos = stripped.find('{')
                if len(stripped) > brace_pos + 1:
                    after_brace = stripped[brace_pos + 1:].strip()
                    if after_brace and not after_brace.startswith('}'):
                        # Split the line
                        before_content = line[:line.find('{') + 1]
                        fixed_lines.append(before_content)
                        # Add the content as a separate line with proper indentation
                        if not after_brace.endswith('}'):
                            fixed_lines.append('    ' + after_brace)
                        else:
                            # Content ends with }, split that too
                            content_part = after_brace[:-1].strip()
                            if content_part:
                                fixed_lines.append('    ' + content_part)
                            fixed_lines.append('}')
                        continue
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    @pyqtSlot(str, str, str, bool)
    def run_compile(self, c_code: str, h_code: str, fsm_name: str, optimize: bool = True):
        """Enhanced compilation with better error handling and multiple compiler support."""
        self.compile_started.emit()
        start_time = time.time()
        
        build_dir_path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "build"
        
        try:
            build_dir_path.mkdir(parents=True, exist_ok=True)
            build_dir = str(build_dir_path)

            available_compilers = self._detect_available_compilers()
            if not available_compilers:
                result = CompilationResult(
                    success=False, library_path="",
                    output="No C compiler found. Please install:\n"
                           "- MinGW-W64/MSYS2 for GCC\n"
                           "- LLVM for Clang\n"
                           "- Visual Studio Build Tools for MSVC\n"
                           "- TCC (Tiny C Compiler) as a lightweight option\n\n"
                           "For Windows users, we recommend:\n"
                           "1. Install MinGW-W64 via MSYS2 (https://www.msys2.org/)\n"
                           "2. Or install Visual Studio Community with C++ development tools",
                    compiler_type=CompilerType.UNKNOWN, compilation_time=0,
                    warnings=[], errors=["No compiler available"]
                )
                self.compile_finished.emit(result)
                return

            last_error = None
            for compiler_type, compiler_path in available_compilers:
                try:
                    unique_name = self._get_unique_library_name(fsm_name, compiler_type)
                    self.compile_progress.emit(f"Trying {compiler_type.value.upper()} compiler...")
                    
                    result = self._compile_with_compiler(
                        compiler_type, compiler_path, c_code, h_code, 
                        unique_name, build_dir, optimize, start_time, fsm_name
                    )
                    
                    if result.success:
                        self.compile_finished.emit(result)
                        return
                    else:
                        last_error = result
                        self.compile_progress.emit(f"{compiler_type.value.upper()} failed, trying next...")
                        
                except Exception as e:
                    logger.warning(f"Compiler {compiler_type.value} failed with exception: {e}")
                    continue

            # If we get here, all compilers failed
            if last_error:
                self.compile_finished.emit(last_error)
            else:
                result = CompilationResult(
                    success=False, library_path="", output="All available compilers failed to compile the code.",
                    compiler_type=CompilerType.UNKNOWN, compilation_time=time.time() - start_time,
                    warnings=[], errors=["All compilers failed"]
                )
                self.compile_finished.emit(result)
            
        except Exception as e:
            logger.error(f"C compilation failed with unexpected error: {e}", exc_info=True)
            result = CompilationResult(
                success=False, library_path="", output=f"An unexpected error occurred during compilation: {e}",
                compiler_type=CompilerType.UNKNOWN, compilation_time=time.time() - start_time,
                warnings=[], errors=[str(e)]
            )
            self.compile_finished.emit(result)

    def _compile_with_compiler(self, compiler_type: CompilerType, compiler_path: str, 
                              c_code: str, h_code: str, unique_name: str, 
                              build_dir: str, optimize: bool, start_time: float, fsm_name: str) -> CompilationResult:
        """Compile with a specific compiler."""
        
        # Use the same filename for both C and header files
        c_path = os.path.join(build_dir, f"{unique_name}.c")
        h_path = os.path.join(build_dir, f"{unique_name}.h")

        # Update the #include directive in the C code to match the header filename
        fixed_c_code = self._fix_include_path(c_code, fsm_name, unique_name)
        
        # Apply code fixes to resolve compilation issues
        fixed_c_code, fixed_h_code = self._fix_c_code_issues(fixed_c_code, h_code)
        
        # Write the fixed code to files
        with open(c_path, 'w', encoding='utf-8') as f: 
            f.write(fixed_c_code)
        with open(h_path, 'w', encoding='utf-8') as f: 
            f.write(fixed_h_code)

        env = os.environ.copy()
        command = []
        
        if compiler_type == CompilerType.MSVC:
            env = self._get_msvc_environment()
            if not env: 
                raise RuntimeError("MSVC environment setup failed")
            lib_ext = ".dll"
            lib_path = os.path.join(build_dir, f"{unique_name}{lib_ext}")
            flags = ['/LD', '/W3', '/D', 'FSM_CORE_BUILD_DLL', '/nologo']  # Added /nologo
            if optimize: 
                flags.extend(['/O2', '/DNDEBUG'])
            else: 
                flags.extend(['/Od', '/D_DEBUG', '/Zi'])
            command = ['cl'] + flags + [f'/Fe:{lib_path}', c_path]
                
        elif compiler_type == CompilerType.TCC:
            if sys.platform == "win32": 
                lib_ext, base_flags = ".dll", ['-shared']
            elif sys.platform == "darwin": 
                lib_ext, base_flags = ".dylib", ['-shared']
            else: 
                lib_ext, base_flags = ".so", ['-shared', '-fPIC']
            lib_path = os.path.join(build_dir, f"{unique_name}{lib_ext}")
            flags = base_flags + (['-g'] if not optimize else []) + ['-I.']
            command = [compiler_path] + flags + ['-o', lib_path, c_path]
                
        else:  # GCC or Clang
            if sys.platform == "win32": 
                lib_ext, base_flags = ".dll", ['-shared']
            elif sys.platform == "darwin": 
                lib_ext, base_flags = ".dylib", ['-shared', '-fPIC']
            else: 
                lib_ext, base_flags = ".so", ['-shared', '-fPIC']
            lib_path = os.path.join(build_dir, f"{unique_name}{lib_ext}")
            flags = base_flags + ['-Wall', '-I.']
            if optimize: 
                flags.extend(['-O2', '-DNDEBUG'])
            else: 
                flags.extend(['-O0', '-g', '-D_DEBUG'])
            command = [compiler_path] + flags + ['-o', lib_path, c_path]

        logger.info(f"Compilation command: {' '.join(command)}")
        
        try:
            process = subprocess.run(
                command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                shell=False, cwd=build_dir, env=env, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
        except subprocess.TimeoutExpired:
            return CompilationResult(
                success=False, library_path="", 
                output=f"Compilation timed out after 60 seconds with {compiler_type.value.upper()}",
                compiler_type=compiler_type, compilation_time=time.time() - start_time,
                warnings=[], errors=["Compilation timeout"]
            )
        except FileNotFoundError as e:
            return CompilationResult(
                success=False, library_path="", 
                output=f"Compiler not found: {compiler_path}\nError: {e}\n\nPlease ensure the compiler is properly installed and in PATH.",
                compiler_type=compiler_type, compilation_time=time.time() - start_time,
                warnings=[], errors=[f"Compiler not found: {e}"]
            )
        except Exception as e:
            return CompilationResult(
                success=False, library_path="", 
                output=f"Compilation failed with {compiler_type.value.upper()}: {e}",
                compiler_type=compiler_type, compilation_time=time.time() - start_time,
                warnings=[], errors=[str(e)]
            )

        compilation_time = time.time() - start_time
        output = f"--- Compiler: {compiler_type.value.upper()} ---\n"
        output += f"--- Command: {' '.join(command)} ---\n"
        output += f"--- STDOUT ---\n{process.stdout}\n"
        output += f"--- STDERR ---\n{process.stderr}\n"
        output += f"--- Compilation Time: {compilation_time:.2f}s ---"
        
        warnings, errors = self._parse_compiler_output(process.stdout + process.stderr, compiler_type)
        
        return CompilationResult(
            success=process.returncode == 0,
            library_path=lib_path if process.returncode == 0 else "",
            output=output, compiler_type=compiler_type, compilation_time=compilation_time,
            warnings=warnings, errors=errors
        )

class CSimulationManager(QObject):
    
    simulationStateChanged = pyqtSignal(bool)  # True if active, False if inactive
    stateTransitioned = pyqtSignal(str, str)   # from_state, to_state
    eventTriggered = pyqtSignal(str, bool)     # event_name, handled

    def __init__(self, main_window):
        super().__init__(main_window)
        self.mw = main_window
        
        self.c_library = None
        self.c_fsm_init, self.c_fsm_run, self.c_fsm_get_current_state = None, None, None
        
        self.fsm_states: Dict[str, FSMState] = {}
        self.fsm_events: Dict[str, FSMEvent] = {}
        self.current_state_id, self.previous_state_id = -1, -1
        
        self._is_compiling, self._is_initialized = False, False
        self._library_path: Optional[str] = None
        self._compilation_result: Optional[CompilationResult] = None
        self._unique_name: Optional[str] = None  # Store the unique name for function lookup
        
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_state)
        self._refresh_timer.setInterval(100)
        
        self._cleanup_old_builds()
        self._setup_worker()

    def _cleanup_old_builds(self):
        """Cleans up old build files to prevent conflicts."""
        build_dir_path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "build"
        if build_dir_path.exists():
            logger.info(f"Cleaning up old build directory: {build_dir_path}")
            try:
                if self.c_library: 
                    self._unload_library()
                for file_path in build_dir_path.glob("*"):
                    try:
                        if file_path.is_file(): 
                            file_path.unlink()
                    except OSError as e:
                        logger.warning(f"Could not remove file {file_path}: {e}")
            except OSError as e:
                logger.warning(f"Could not clean up old build directory: {e}")

    def _setup_worker(self):
        self.compile_thread = QThread()
        self.compile_worker = CCompilerWorker()
        self.compile_worker.moveToThread(self.compile_thread)
        
        self.compile_worker.compile_started.connect(self._on_compile_started)
        self.compile_worker.compile_progress.connect(self._on_compile_progress)
        self.compile_worker.compile_finished.connect(self._on_compile_finished)
        
        self.compile_thread.start()

    def create_dock_widget_contents(self) -> QWidget:
        """Creates the main widget for the C Simulation dock."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(4,4,4,4)
        top_layout.setSpacing(8)
        
        # Compilation
        compile_group = QGroupBox("Compilation")
        compile_layout = QVBoxLayout(compile_group)
        compile_controls = QHBoxLayout()
        self.compile_btn = QPushButton("Compile FSM", icon=get_standard_icon(QStyle.StandardPixmap.SP_CommandLink))
        self.compile_btn.clicked.connect(self.on_compile_fsm)
        self.optimize_cb = QCheckBox("Optimize (-O2)")
        self.optimize_cb.setChecked(True)
        compile_controls.addWidget(self.compile_btn)
        compile_controls.addWidget(self.optimize_cb)
        compile_controls.addStretch()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("font-size: 8pt; color: gray;")
        compile_layout.addLayout(compile_controls)
        compile_layout.addWidget(self.progress_bar)
        compile_layout.addWidget(self.progress_label)
        top_layout.addWidget(compile_group)
        
        # Simulation
        sim_group = QGroupBox("Simulation Control")
        sim_layout = QHBoxLayout(sim_group)
        self.init_btn = QPushButton("Initialize", icon=get_standard_icon(QStyle.StandardPixmap.SP_MediaPlay))
        self.init_btn.clicked.connect(self.on_initialize_fsm)
        self.reset_btn = QPushButton("Reset", icon=get_standard_icon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.reset_btn.clicked.connect(self.on_initialize_fsm)
        self.auto_refresh_cb = QCheckBox("Auto Refresh")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.toggled.connect(self._toggle_auto_refresh)
        sim_layout.addWidget(self.init_btn)
        sim_layout.addWidget(self.reset_btn)
        sim_layout.addStretch()
        sim_layout.addWidget(self.auto_refresh_cb)
        top_layout.addWidget(sim_group)

        # Events
        event_group = QGroupBox("Event Trigger")
        event_layout = QHBoxLayout(event_group)
        self.event_combo = QComboBox()
        self.event_combo.setMinimumWidth(150)
        self.trigger_btn = QPushButton("Trigger")
        self.trigger_btn.clicked.connect(self.on_trigger_event)
        self.step_count_spin = QSpinBox()
        self.step_count_spin.setRange(1, 1000)
        self.step_count_spin.setValue(1)
        self.step_count_spin.setPrefix("Steps: ")
        event_layout.addWidget(QLabel("Event:"))
        event_layout.addWidget(self.event_combo, 1)
        event_layout.addWidget(self.step_count_spin)
        event_layout.addWidget(self.trigger_btn)
        top_layout.addWidget(event_group)
        
        # Status
        status_group = QGroupBox("Status & State Information")
        status_layout = QVBoxLayout(status_group)
        status_info = QHBoxLayout()
        self.status_label = QLabel("Status: Uncompiled")
        self.status_label.setWordWrap(True)
        self.compilation_info = QLabel("")
        self.compilation_info.setFont(QFont("Consolas", 8))
        self.compilation_info.setStyleSheet("QLabel { color: gray; }")
        status_info.addWidget(self.status_label, 1)
        status_layout.addLayout(status_info)
        status_layout.addWidget(self.compilation_info)
        self.state_tree = QTreeWidget()
        self.state_tree.setHeaderLabels(["State/Event", "ID", "Status"])
        self.state_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.state_tree.setMaximumHeight(150)
        status_layout.addWidget(self.state_tree)
        top_layout.addWidget(status_group)
        splitter.addWidget(top_widget)
        
        # Output
        output_group = QGroupBox("Compiler Output & Simulation Log")
        output_layout = QVBoxLayout(output_group)
        self.compiler_output = QTextEdit()
        self.compiler_output.setReadOnly(True)
        self.compiler_output.setFont(QFont("Consolas", 9))
        self.compiler_output.setPlaceholderText("Compiler output and simulation logs will appear here.")
        output_layout.addWidget(self.compiler_output)
        splitter.addWidget(output_group)
        
        splitter.setSizes([350, 200])
        layout.addWidget(splitter)
        
        self._update_ui_state()
        return container

    def _toggle_auto_refresh(self, enabled: bool):
        if enabled and self._is_initialized: 
            self._refresh_timer.start()
        else: 
            self._refresh_timer.stop()

    @pyqtSlot()
    def _refresh_state(self):
        if not self._is_initialized or not self.c_fsm_get_current_state: 
            return
        try:
            new_state_id = self.c_fsm_get_current_state()
            if new_state_id != self.current_state_id:
                self.previous_state_id, self.current_state_id = self.current_state_id, new_state_id
                from_state = next((name for name, state in self.fsm_states.items() if state.id == self.previous_state_id), "Unknown")
                to_state = next((name for name, state in self.fsm_states.items() if state.id == self.current_state_id), "Unknown")
                self.stateTransitioned.emit(from_state, to_state)
                self._update_state_display()
        except Exception as e: 
            logger.error(f"Error refreshing state: {e}")

    @pyqtSlot()
    def on_initialize_fsm(self):
        if not self.c_library or not self.c_fsm_init:
            QMessageBox.warning(self.mw, "Not Compiled", "Please compile the FSM before initializing.")
            return
        try:
            self.c_fsm_init()
            self._is_initialized = True
            self.compiler_output.append("\n--- FSM Initialized/Reset ---")
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
            for _ in range(steps):
                self.c_fsm_run(event_id)
                self._refresh_state()
            current_state_name = next((name for name, state_info in self.fsm_states.items() if state_info.id == self.current_state_id), "Unknown")
            self.compiler_output.append(f"Event triggered successfully. New state: {current_state_name}")
            self.eventTriggered.emit(event_name, True)
        except Exception as e:
            self.compiler_output.append(f"ERROR during event trigger: {e}")
            logger.error(f"Failed to trigger C FSM event: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "Event Trigger Error", f"An error occurred while running the FSM:\n{e}")
            self.eventTriggered.emit(event_name, False)
        self._update_ui_state()

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
        self.compiler_output.clear()
        self.compiler_output.append("=== Starting FSM Compilation ===\n")
        
        try:
            fsm_name = sanitize_c_identifier(os.path.splitext(os.path.basename(editor.file_path or "fsm"))[0], "fsm_")
            self.compiler_output.append("Generating C code...\n")
            code_dict = generate_c_code_content(diagram_data, fsm_name, "Generic C (Header/Source Pair)")
            self._parse_fsm_structure(code_dict['h'], diagram_data)
            self.compiler_output.append("Code generated successfully. Starting compilation...\n")
            QMetaObject.invokeMethod(self.compile_worker, "run_compile", Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, code_dict['c']), Q_ARG(str, code_dict['h']), Q_ARG(str, fsm_name), 
                Q_ARG(bool, self.optimize_cb.isChecked()))
        except Exception as e:
            self.compiler_output.append(f"ERROR during code generation:\n{e}\n")
            logger.error(f"Code generation error: {e}", exc_info=True)
            self._is_compiling = False
            self._update_ui_state()

    def _parse_fsm_structure(self, h_code: str, diagram_data: dict):
        self.fsm_states.clear()
        self.fsm_events.clear()
        state_enum = self._parse_c_enum(h_code, "STATE_")
        event_enum = self._parse_c_enum(h_code, "EVENT_")
        for state_data in diagram_data.get('states', []):
            state_name = state_data.get('name', 'Unknown')
            sanitized_name_key = "STATE_" + sanitize_c_identifier(state_name, "s_").upper()
            if sanitized_name_key in state_enum:
                self.fsm_states[state_name] = FSMState(name=state_name, id=state_enum[sanitized_name_key], entry_actions=[], exit_actions=[])
        
        for event_name in sorted(list(set(t['event'] for t in diagram_data.get('transitions', []) if t.get('event')))):
            sanitized_event_key = "EVENT_" + sanitize_c_identifier(event_name, "evt_").upper()
            if sanitized_event_key in event_enum:
                self.fsm_events[event_name] = FSMEvent(name=event_name, id=event_enum[sanitized_event_key], description=f"Event: {event_name}")

    def _parse_c_enum(self, h_code: str, prefix: str) -> Dict[str, int]:
        enum_map = {}
        in_enum = False
        value = 0
        for line in h_code.splitlines():
            line = line.strip()
            if "typedef enum" in line: 
                in_enum = True
                continue
            if in_enum:
                if line.startswith(prefix):
                    name = line.split(',')[0].strip().split('=')[0].strip()
                    if '=' in line: 
                        value = int(line.split('=')[1].split(',')[0].strip())
                    if name: 
                        enum_map[name] = value
                        value += 1
                elif "}" in line: 
                    break
        return enum_map

    @pyqtSlot()
    def _on_compile_started(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText("Preparing compilation...")

    @pyqtSlot(str)
    def _on_compile_progress(self, message: str):
        self.progress_label.setText(message)
        self.compiler_output.append(f"[PROGRESS] {message}")

    @pyqtSlot(CompilationResult)
    def _on_compile_finished(self, result: CompilationResult):
        self._is_compiling = False
        self._compilation_result = result
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.compiler_output.append("\n=== Compilation Results ===\n" + result.output)
        if result.success:
            self._library_path = result.library_path
            # Store the unique name for function lookup
            self._unique_name = os.path.splitext(os.path.basename(result.library_path))[0]
            self._load_library()
            self.status_label.setText("Status: Compiled successfully. Ready to initialize.")
            self.compilation_info.setText(f"Compiled with {result.compiler_type.value.upper()} in {result.compilation_time:.2f}s | {len(result.warnings)} warnings")
        else:
            self.status_label.setText("Status: Compilation failed.")
            self.compilation_info.setText("Compilation failed - see output for details")
            self.c_library = None
            self._is_initialized = False
        self._update_ui_state()

    def _load_library(self):
        if not self._library_path or not os.path.exists(self._library_path):
            logger.error("Cannot load C library: Path is invalid.")
            return
        try:
            self._unload_library()
            self.c_library = ctypes.CDLL(self._library_path)
            
            # Use the unique name for function lookup instead of trying to parse it
            fsm_base = self._unique_name if self._unique_name else "fsm"
            
            self.c_fsm_init = getattr(self.c_library, f"{fsm_base}_init")
            self.c_fsm_run = getattr(self.c_library, f"{fsm_base}_run")
            self.c_fsm_get_current_state = getattr(self.c_library, f"{fsm_base}_get_current_state")
            self.c_fsm_init.restype, self.c_fsm_run.restype, self.c_fsm_get_current_state.restype = None, None, ctypes.c_int
            self.c_fsm_run.argtypes = [ctypes.c_int]
            logger.info(f"Successfully loaded C FSM library from {self._library_path}")
        except (AttributeError, OSError) as e:
            self.c_library = None
            logger.error(f"Failed to load C FSM library: {e}", exc_info=True)
            QMessageBox.critical(self.mw, "Library Load Error", f"Could not load the compiled library:\n{e}")

    def _unload_library(self):
        if not self.c_library: 
            return
        handle = self.c_library._handle
        self.c_library = self.c_fsm_init = self.c_fsm_run = self.c_fsm_get_current_state = None
        try:
            if sys.platform == "win32":
                ctypes.windll.kernel32.FreeLibrary(handle)
            else:
                from ctypes.util import find_library
                libdl_path = find_library("dl")
                if libdl_path:
                    ctypes.CDLL(libdl_path).dlclose(handle)
                else:
                    logger.warning("Could not find libdl to unload C library.")
        except Exception as e: 
            logger.warning(f"Could not properly unload library: {e}")
        logger.info("Unloaded previous C FSM library.")

    def _update_ui_state(self):
        is_compiled = bool(self._compilation_result and self._compilation_result.success)
        self.compile_btn.setEnabled(not self._is_compiling)
        self.init_btn.setEnabled(is_compiled and not self._is_compiling)
        self.reset_btn.setEnabled(is_compiled and self._is_initialized and not self._is_compiling)
        self.trigger_btn.setEnabled(self._is_initialized and not self._is_compiling)
        self.event_combo.setEnabled(self._is_initialized and not self._is_compiling)
        self._update_state_display()

    def _update_state_display(self):
        self.state_tree.clear()
        self.event_combo.clear()
        states_root = QTreeWidgetItem(self.state_tree, ["States"])
        for name, state in sorted(self.fsm_states.items(), key=lambda item: item[1].id):
            status = "CURRENT" if state.id == self.current_state_id else ""
            item = QTreeWidgetItem(states_root, [name, str(state.id), status])
            if status: 
                item.setBackground(0, QColor("#1E3A8A"))
                item.setForeground(0, Qt.GlobalColor.white)
        events_root = QTreeWidgetItem(self.state_tree, ["Events"])
        for name, event in sorted(self.fsm_events.items()):
            QTreeWidgetItem(events_root, [name, str(event.id), ""])
            self.event_combo.addItem(name)
        self.state_tree.expandAll()

    def shutdown(self):
        self._refresh_timer.stop()
        if self.compile_thread.isRunning():
            self.compile_thread.quit()
            self.compile_thread.wait(1000)
        self._unload_library()
        self._cleanup_old_builds()