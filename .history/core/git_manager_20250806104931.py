# fsm_designer_project/git_manager.py
"""
Manages asynchronous Git operations for the application.

This module provides the GitManager class, which uses a QThread and a worker
object to run Git commands (like status, diff, commit, push, pull) without
blocking the main UI thread. It communicates results back via Qt signals.
"""

import logging
import os
import subprocess
from typing import List, Callable
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QMetaObject, Qt, Q_ARG

logger = logging.getLogger(__name__)

class GitWorker(QObject):
    """Executes a Git command in a non-GUI worker thread."""
    # --- MODIFIED SIGNAL ---
    command_finished = pyqtSignal(str, bool, str, str)  # command_id, success, stdout, stderr

    def __init__(self):
        super().__init__()
        # --- FIX: Remove this redundant flag ---
        # self._is_running = False

    # --- MODIFIED SLOT ---
    @pyqtSlot(str, list, str)
    def run_command(self, command_id: str, command: List[str], working_dir: str) -> None:
        """
        Executes a subprocess command in the specified directory.

        Args:
            command_id: A unique identifier for this command execution.
            command: A list of strings representing the command and its arguments.
            working_dir: The directory in which to run the command.
        """
        # --- FIX: Remove this redundant check ---
        # if self._is_running:
        #     logger.warning("GitWorker: Another command is already running.")
        #     return
        # self._is_running = True
        logger.info(f"GitWorker: Running command '{' '.join(command)}' in '{working_dir}' (ID: {command_id})")
        try:
            startupinfo = None
            if os.name == 'nt':
                # Prevents a console window from popping up on Windows for git operations.
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.run(
                command,
                cwd=working_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,  # 2 minute timeout for network operations
                check=False,
                startupinfo=startupinfo
            )
            success = process.returncode == 0
            self.command_finished.emit(command_id, success, process.stdout, process.stderr)

        except FileNotFoundError:
            self.command_finished.emit(command_id, False, "", "Git command not found. Is Git installed and in your system's PATH?")
        except subprocess.TimeoutExpired:
            self.command_finished.emit(command_id, False, "", "Git operation timed out.")
        except Exception as e:
            logger.error(f"GitWorker: Unexpected error running command '{' '.join(command)}': {e}", exc_info=True)
            self.command_finished.emit(command_id, False, "", f"An unexpected error occurred: {e}")
        finally:
            self._is_running = False

class GitManager(QObject):
    """
    Manages asynchronous Git operations and repository status checking for files.
    """
    git_status_updated = pyqtSignal(str, bool, bool)  # file_path, is_in_repo, has_uncommitted_changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: GitWorker | None = None
        self.thread: QThread | None = None
        self._repo_root_cache: dict[str, str | None] = {}  # Cache repo root paths for performance
        # --- NEW ATTRIBUTES for robust callbacks ---
        self._callbacks: dict[str, Callable] = {}
        self._next_command_id = 0
        # --- END NEW ---
        self._setup_worker()

    def _setup_worker(self) -> None:
        """Initializes the worker object and moves it to a dedicated QThread."""
        self.thread = QThread()
        self.thread.setObjectName("GitManagerThread")
        self.worker = GitWorker()
        self.worker.moveToThread(self.thread)
        # --- MODIFICATION: Connect signal once to a dispatcher ---
        self.worker.command_finished.connect(self._on_command_finished)
        self.thread.start()
        logger.info("GitManager worker thread started.")

    @pyqtSlot(str, bool, str, str)
    def _on_command_finished(self, command_id: str, success: bool, stdout: str, stderr: str):
        """Dispatcher that calls the correct callback based on the command ID."""
        callback = self._callbacks.pop(command_id, None)
        if callback:
            callback(success, stdout, stderr)
        else:
            logger.warning(f"No callback found for git command with ID '{command_id}'")

    @pyqtSlot(str)
    def check_file_status(self, file_path: str) -> None:
        """
        Checks if a file is in a Git repository and if it has uncommitted changes.
        This operation is lightweight and runs synchronously in the calling thread,
        but it avoids blocking for extended periods.

        Args:
            file_path: The absolute path to the file to check.
        """
        if not file_path or not os.path.exists(file_path):
            self.git_status_updated.emit(file_path, False, False)
            return

        file_dir = os.path.dirname(file_path)

        # Check cache for repo root to avoid repeated disk I/O and subprocess calls
        if file_dir in self._repo_root_cache:
            repo_root = self._repo_root_cache[file_dir]
        else:
            try:
                # Use subprocess to find the git repo root
                result = subprocess.run(
                    ['git', 'rev-parse', '--show-toplevel'],
                    cwd=file_dir, capture_output=True, text=True, check=True
                )
                repo_root = result.stdout.strip()
                self._repo_root_cache[file_dir] = repo_root
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._repo_root_cache[file_dir] = None
                repo_root = None
        
        if not repo_root:
            self.git_status_updated.emit(file_path, False, False)
            return

        # Check the status of the specific file using 'git status --porcelain'
        try:
            status_result = subprocess.run(
                ['git', 'status', '--porcelain=v1', '--untracked-files=no', '--', file_path],
                cwd=repo_root, capture_output=True, text=True, check=True
            )
            # If the command returns any output, the file has been modified, added, etc.
            has_changes = bool(status_result.stdout.strip())
            self.git_status_updated.emit(file_path, True, has_changes)
        except (subprocess.CalledProcessError, FileNotFoundError):
             # This could happen if git disappears mid-run or other errors.
             self.git_status_updated.emit(file_path, False, False)

    def run_command_in_repo(self, command: List[str], file_path: str, finished_callback: Callable[[bool, str, str], None]) -> None:
        """
        Executes a Git command asynchronously in the repository containing the given file.

        Args:
            command: The Git command and its arguments as a list of strings.
            file_path: A path to a file within the desired repository.
            finished_callback: A function to call upon completion. It receives
                               (success: bool, stdout: str, stderr: str).
        """
        file_dir = os.path.dirname(file_path)
        repo_root = self._repo_root_cache.get(file_dir)
        
        if not repo_root:  # If not cached, find it synchronously for this command
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', '--show-toplevel'],
                    cwd=file_dir, capture_output=True, text=True, check=True
                )
                repo_root = result.stdout.strip()
                self._repo_root_cache[file_dir] = repo_root
            except (subprocess.CalledProcessError, FileNotFoundError):
                finished_callback(False, "", f"Not a Git repository or Git not found: '{file_dir}'")
                return

        if self.worker and self.thread and self.thread.isRunning():
            # --- MODIFICATION: Use the command ID system ---
            command_id = f"git_cmd_{self._next_command_id}"
            self._next_command_id += 1
            self._callbacks[command_id] = finished_callback
            
            # Invoke the command on the worker thread via a queued signal
            QMetaObject.invokeMethod(self.worker, "run_command", Qt.QueuedConnection,
                                     Q_ARG(str, command_id),
                                     Q_ARG(list, command),
                                     Q_ARG(str, repo_root))
            # --- END MODIFICATION ---
        else:
            logger.error("GitManager: Worker or thread is not available to run command.")
            finished_callback(False, "", "Git worker is not available.")

    def stop(self) -> None:
        """Stops the worker thread gracefully."""
        logger.info("Stopping GitManager thread...")
        if self.thread:
            self.thread.quit()
            if not self.thread.wait(1000):  # Wait up to 1 second
                logger.warning("GitManager thread did not quit gracefully, terminating.")
                self.thread.terminate()