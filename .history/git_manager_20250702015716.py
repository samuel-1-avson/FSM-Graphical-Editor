# fsm_designer_project/git_manager.py
import logging
import os
import subprocess
import uuid
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QMetaObject, Qt, Q_ARG

logger = logging.getLogger(__name__)

class GitWorker(QObject):
    """Executes a Git command in a worker thread."""
    # MODIFIED: Signal now includes a unique ID
    command_finished = pyqtSignal(str, bool, str, str) # request_id, success, stdout, stderr

    def __init__(self):
        super().__init__()
        self._is_running = False

    @pyqtSlot(list, str, str) # MODIFIED: Added request_id
    def run_command(self, command: list, working_dir: str, request_id: str):
        if self._is_running:
            logger.warning("GitWorker: Another command is already running.")
            self.command_finished.emit(request_id, False, "", "Worker is busy.")
            return

        self._is_running = True
        logger.info(f"GitWorker: Running command '{' '.join(command)}' in '{working_dir}' for request {request_id}")
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.run(
                command, cwd=working_dir, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=120, check=False,
                startupinfo=startupinfo
            )
            success = process.returncode == 0
            self.command_finished.emit(request_id, success, process.stdout, process.stderr)

        except FileNotFoundError:
            self.command_finished.emit(request_id, False, "", "Git command not found. Is Git installed and in your system's PATH?")
        except subprocess.TimeoutExpired:
            self.command_finished.emit(request_id, False, "", "Git operation timed out.")
        except Exception as e:
            logger.error(f"GitWorker: Unexpected error running command '{' '.join(command)}': {e}", exc_info=True)
            self.command_finished.emit(request_id, False, "", f"An unexpected error occurred: {e}")
        finally:
            self._is_running = False

class GitManager(QObject):
    """Manages asynchronous Git operations and repository status checking."""
    git_status_updated = pyqtSignal(str, bool, bool) # file_path, is_in_repo, has_uncommitted_changes
    # NEW: A safe, managed signal for command results
    command_result = pyqtSignal(str, bool, str, str) # request_id, success, stdout, stderr

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: GitWorker | None = None
        self.thread: QThread | None = None
        self._repo_root_cache = {}
        self._setup_worker()

    def _setup_worker(self):
        self.thread = QThread()
        self.thread.setObjectName("GitManagerThread")
        self.worker = GitWorker()
        self.worker.moveToThread(self.thread)
        # Connect the worker's signal to a slot ON THIS MANAGER
        self.worker.command_finished.connect(self._on_worker_command_finished)
        self.thread.start()
        logger.info("GitManager worker thread started.")

    @pyqtSlot(str)
    def check_file_status(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            self.git_status_updated.emit(file_path, False, False)
            return

        file_dir = os.path.dirname(file_path)
        repo_root = self._repo_root_cache.get(file_dir)
        if repo_root is None:
            try:
                result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=file_dir, capture_output=True, text=True, check=True)
                repo_root = result.stdout.strip()
                self._repo_root_cache[file_dir] = repo_root
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._repo_root_cache[file_dir] = "" # Cache failure as empty string
                repo_root = ""

        if not repo_root:
            self.git_status_updated.emit(file_path, False, False)
            return

        try:
            status_result = subprocess.run(
                ['git', 'status', '--porcelain=v1', '--untracked-files=no', '--', file_path],
                cwd=repo_root, capture_output=True, text=True, check=True
            )
            has_changes = bool(status_result.stdout.strip())
            self.git_status_updated.emit(file_path, True, has_changes)
        except (subprocess.CalledProcessError, FileNotFoundError):
             self.git_status_updated.emit(file_path, True, False) # In repo, but maybe an error checking status

    def run_command_in_repo(self, command: list, file_path: str) -> str:
        """
        Runs a command and returns a unique request ID for tracking.
        The result will be emitted via the `command_result` signal.
        """
        file_dir = os.path.dirname(file_path)
        repo_root = self._repo_root_cache.get(file_dir, None)
        if repo_root is None:
             try:
                result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=file_dir, capture_output=True, text=True, check=True)
                repo_root = result.stdout.strip()
             except (subprocess.CalledProcessError, FileNotFoundError):
                repo_root = ""
             self._repo_root_cache[file_dir] = repo_root

        request_id = str(uuid.uuid4())
        
        if not repo_root:
            QMetaObject.invokeMethod(self, "_emit_command_result_on_main_thread", Qt.QueuedConnection,
                                     Q_ARG(str, request_id), Q_ARG(bool, False),
                                     Q_ARG(str, ""), Q_ARG(str, f"Not a Git repository: '{file_dir}'"))
            return request_id

        if self.worker and self.thread and self.thread.isRunning():
            QMetaObject.invokeMethod(self.worker, "run_command", Qt.QueuedConnection,
                                     Q_ARG(list, command),
                                     Q_ARG(str, repo_root),
                                     Q_ARG(str, request_id))
        else:
            logger.error("GitManager: Worker or thread is not available to run command.")
            QMetaObject.invokeMethod(self, "_emit_command_result_on_main_thread", Qt.QueuedConnection,
                                     Q_ARG(str, request_id), Q_ARG(bool, False),
                                     Q_ARG(str, ""), Q_ARG(str, "Git worker is not available."))
        return request_id

    @pyqtSlot(str, bool, str, str)
    def _on_worker_command_finished(self, request_id: str, success: bool, stdout: str, stderr: str):
        """Worker signal handler. Emits the manager's public signal."""
        self.command_result.emit(request_id, success, stdout, stderr)

    @pyqtSlot(str, bool, str, str)
    def _emit_command_result_on_main_thread(self, request_id: str, success: bool, stdout: str, stderr: str):
        """Helper to emit signal from the main thread if the command fails before reaching the worker."""
        self.command_result.emit(request_id, success, stdout, stderr)

    def stop(self):
        logger.info("Stopping GitManager thread...")
        if self.thread:
            self.thread.quit()
            if not self.thread.wait(1000):
                logger.warning("GitManager thread did not quit gracefully, terminating.")
                self.thread.terminate()