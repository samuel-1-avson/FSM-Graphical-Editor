# bsm_designer_project/git_manager.py
import logging
import os
import subprocess
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QMetaObject, Qt, Q_ARG

logger = logging.getLogger(__name__)

class GitWorker(QObject):
    """Executes a Git command in a worker thread."""
    command_finished = pyqtSignal(bool, str, str) # success, stdout, stderr

    def __init__(self):
        super().__init__()
        self._is_running = False

    @pyqtSlot(list, str)
    def run_command(self, command: list, working_dir: str):
        if self._is_running:
            logger.warning("GitWorker: Another command is already running.")
            return

        self._is_running = True
        logger.info(f"GitWorker: Running command '{' '.join(command)}' in '{working_dir}'")
        try:
            # For git status, we don't want a new window to ever pop up (e.g., for credentials)
            # For interactive commands like commit/push, this might be a limitation, but for this basic
            # integration, it's safer.
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.run(
                command,
                cwd=working_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120, # 2 minute timeout for network ops
                check=False,
                startupinfo=startupinfo
            )
            success = process.returncode == 0
            self.command_finished.emit(success, process.stdout, process.stderr)

        except FileNotFoundError:
            self.command_finished.emit(False, "", "Git command not found. Is Git installed and in your system's PATH?")
        except subprocess.TimeoutExpired:
            self.command_finished.emit(False, "", "Git operation timed out.")
        except Exception as e:
            logger.error(f"GitWorker: Unexpected error running command '{' '.join(command)}': {e}", exc_info=True)
            self.command_finished.emit(False, "", f"An unexpected error occurred: {e}")
        finally:
            self._is_running = False

class GitManager(QObject):
    """Manages asynchronous Git operations and repository status checking."""
    git_status_updated = pyqtSignal(str, bool, bool) # file_path, is_in_repo, has_uncommitted_changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: GitWorker | None = None
        self.thread: QThread | None = None
        self._repo_root_cache = {} # Cache repo root paths to avoid repeated lookups
        self._setup_worker()

    def _setup_worker(self):
        self.thread = QThread()
        self.thread.setObjectName("GitManagerThread")
        self.worker = GitWorker()
        self.worker.moveToThread(self.thread)
        self.thread.start()
        logger.info("GitManager worker thread started.")

    @pyqtSlot(str)
    def check_file_status(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            self.git_status_updated.emit(file_path, False, False)
            return

        file_dir = os.path.dirname(file_path)

        # Find repo root
        if file_dir in self._repo_root_cache:
            repo_root = self._repo_root_cache[file_dir]
        else:
            try:
                # Use subprocess to find the git repo root to avoid blocking
                result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=file_dir, capture_output=True, text=True, check=True)
                repo_root = result.stdout.strip()
                self._repo_root_cache[file_dir] = repo_root
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._repo_root_cache[file_dir] = None
                repo_root = None
        
        if not repo_root:
            self.git_status_updated.emit(file_path, False, False)
            return

        # Check status of the specific file
        try:
            status_result = subprocess.run(
                ['git', 'status', '--porcelain=v1', '--untracked-files=no', '--', file_path],
                cwd=repo_root, capture_output=True, text=True, check=True
            )
            # If the output is not empty, the file has been modified.
            has_changes = bool(status_result.stdout.strip())
            self.git_status_updated.emit(file_path, True, has_changes)
        except (subprocess.CalledProcessError, FileNotFoundError):
             # This could happen if git disappears mid-run, etc.
             self.git_status_updated.emit(file_path, False, False)


    def run_command_in_repo(self, command: list, file_path: str, finished_callback: callable):
        file_dir = os.path.dirname(file_path)
        repo_root = self._repo_root_cache.get(file_dir)
        if not repo_root: # If not cached, find it synchronously for this one-off command
            try:
                result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=file_dir, capture_output=True, text=True, check=True)
                repo_root = result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                finished_callback(False, "", f"Not a Git repository or Git not found: '{file_dir}'")
                return

        if self.worker and self.thread and self.thread.isRunning():
            # Disconnect previous temporary connection if any
            try: self.worker.command_finished.disconnect()
            except TypeError: pass
            
            # Connect the one-shot callback
            self.worker.command_finished.connect(finished_callback)
            
            # Invoke the command
            QMetaObject.invokeMethod(self.worker, "run_command", Qt.QueuedConnection,
                                     Q_ARG(list, command),
                                     Q_ARG(str, repo_root))
        else:
            logger.error("GitManager: Worker or thread is not available to run command.")
            finished_callback(False, "", "Git worker is not available.")

    def stop(self):
        logger.info("Stopping GitManager thread...")
        if self.thread:
            self.thread.quit()
            if not self.thread.wait(1000):
                logger.warning("GitManager thread did not quit gracefully, terminating.")
                self.thread.terminate()