# fsm_designer_project/resource_monitor.py
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTime, pyqtSlot, QMetaObject, Qt

import psutil
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    pynvml = None

logger = logging.getLogger(__name__)

class ResourceMonitorWorker(QObject):
    resourceUpdate = pyqtSignal(float, float, float, str)
    finished_signal = pyqtSignal()
    MAX_NVML_REINIT_ATTEMPTS = 3
    NVML_REINIT_BACKOFF_SECONDS = 30
    WORKER_LOOP_CHECK_INTERVAL_MS = 100

    def __init__(self, interval_ms=2000, parent=None):
        super().__init__(parent)
        self.data_collection_interval_ms = interval_ms
        self._nvml_initialized = False
        self._gpu_handle = None
        self._gpu_name_cache = "N/A"
        self._nvml_reinit_attempts = 0
        self._last_nvml_reinit_attempt_time = 0 
        self._stop_requested = False
        self._transient_error_count = 0 

        if PYNVML_AVAILABLE and pynvml:
            self._attempt_nvml_init()
        elif not PYNVML_AVAILABLE:
            self._gpu_name_cache = "N/A (pynvml N/A)"
        logger.debug("ResourceMonitorWorker initialized.")

    def _attempt_nvml_init(self, from_worker_loop=False):
        if self._stop_requested or self._nvml_initialized:
            return

        current_time_sec = QTime.currentTime().msecsSinceStartOfDay() // 1000
        if self._nvml_reinit_attempts >= self.MAX_NVML_REINIT_ATTEMPTS and \
           (current_time_sec - self._last_nvml_reinit_attempt_time) < self.NVML_REINIT_BACKOFF_SECONDS and \
           from_worker_loop:
            return

        try:
            logger.debug("Attempting pynvml.nvmlInit().")
            pynvml.nvmlInit()
            self._nvml_initialized = True
            self._nvml_reinit_attempts = 0 
            if pynvml.nvmlDeviceGetCount() > 0:
                self._gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                gpu_name_raw = pynvml.nvmlDeviceGetName(self._gpu_handle)
                if isinstance(gpu_name_raw, bytes):
                    self._gpu_name_cache = gpu_name_raw.decode('utf-8')
                elif isinstance(gpu_name_raw, str):
                    self._gpu_name_cache = gpu_name_raw
                else:
                    self._gpu_name_cache = "NVIDIA GPU Name TypeErr"
                logger.info(f"NVML initialized. GPU: {self._gpu_name_cache}")
            else:
                self._gpu_name_cache = "NVIDIA GPU N/A (No devices)"
                logger.info("NVML initialized but no NVIDIA GPUs found.")
        except pynvml.NVMLError as e_nvml:
            self._nvml_reinit_attempts += 1
            self._last_nvml_reinit_attempt_time = current_time_sec
            if self._nvml_reinit_attempts <= self.MAX_NVML_REINIT_ATTEMPTS or not from_worker_loop:
                logger.warning(f"Could not initialize NVML (attempt {self._nvml_reinit_attempts}): {e_nvml}")
            else:
                logger.debug(f"NVML init attempt {self._nvml_reinit_attempts} failed (backoff active): {e_nvml.value if hasattr(e_nvml, 'value') else e_nvml}")
            self._nvml_initialized = False
            error_code_str = f" (Code: {e_nvml.value})" if hasattr(e_nvml, 'value') else ""
            self._gpu_name_cache = f"NVML Init Err{error_code_str}"
        except AttributeError as e_attr:
            logger.warning(f"NVML: Attribute error during init (pynvml likely None): {e_attr}")
            self._nvml_initialized = False
            self._gpu_name_cache = "NVML Attr Err"
        except Exception as e: 
            logger.warning(f"Unexpected error during NVML init: {e}", exc_info=True)
            self._nvml_initialized = False
            self._gpu_name_cache = "NVML Unexp. Err"

    @pyqtSlot()
    def start_monitoring(self):
        logger.info("ResourceMonitorWorker: start_monitoring called.")
        self._stop_requested = False
        self._monitor_resources()

    @pyqtSlot()
    def stop_monitoring(self):
        logger.info("ResourceMonitorWorker: stop_monitoring_slot called. Setting _stop_requested = True.")
        self._stop_requested = True

    def _shutdown_nvml(self):
        if self._nvml_initialized and PYNVML_AVAILABLE and pynvml:
            try:
                logger.debug("Attempting pynvml.nvmlShutdown().")
                pynvml.nvmlShutdown()
                logger.info("ResourceMonitorWorker: NVML shutdown successfully.")
            except Exception as e:
                logger.warning(f"Error shutting down NVML: {e}")
        self._nvml_initialized = False
        self._gpu_handle = None

    def _monitor_resources(self):
        logger.info("ResourceMonitorWorker: _monitor_resources loop STARTED.")
        last_data_emit_time_ms = 0
        
        # --- KEY CHANGE: Remove direct access to self.thread() ---
        # The worker should not need to know about the thread it runs on.
        
        loop_count = 0
        while not self._stop_requested: # --- KEY CHANGE: Rely solely on the stop flag ---
            loop_count += 1
            if loop_count % 50 == 0 : 
                logger.debug(f"ResourceMonitorWorker: Loop iteration {loop_count}, StopRequested: {self._stop_requested}")

            current_loop_time_ms = QTime.currentTime().msecsSinceStartOfDay()

            if (current_loop_time_ms - last_data_emit_time_ms) >= self.data_collection_interval_ms or last_data_emit_time_ms == 0:
                if self._stop_requested:
                    logger.debug("ResourceMonitorWorker: Stop detected before emitting resourceUpdate.")
                    break 
                try:
                    cpu_usage = psutil.cpu_percent(interval=None)
                    ram_percent = psutil.virtual_memory().percent
                    gpu_util = -1.0 
                    gpu_name_to_emit = self._gpu_name_cache

                    if self._nvml_initialized and self._gpu_handle and PYNVML_AVAILABLE and pynvml:
                        try:
                            gpu_info = pynvml.nvmlDeviceGetUtilizationRates(self._gpu_handle)
                            gpu_util = float(gpu_info.gpu)
                            self._transient_error_count = 0 
                        except pynvml.NVMLError as e:
                            self._transient_error_count += 1
                            if self._transient_error_count % 15 == 1: 
                                logger.warning(f"NVML error getting GPU util (occurrence #{self._transient_error_count}): {e}. GPU may be in a low-power state.")
                            gpu_util = -2.0 
                            gpu_name_to_emit = f"NVML Read Err (Code: {e.value})" if hasattr(e, 'value') else "NVML Read Err"
                        except Exception as e_gen: 
                            logger.error(f"Unexpected error getting GPU util: {e_gen}")
                            gpu_util = -3.0 
                            gpu_name_to_emit = "GPU Mon. Err"
                    
                    if not self._stop_requested:
                        self.resourceUpdate.emit(cpu_usage, ram_percent, gpu_util, gpu_name_to_emit)
                    last_data_emit_time_ms = current_loop_time_ms

                except Exception as e:
                    logger.error(f"ResourceMonitorWorker: Error in data collection: {e}", exc_info=False)
                    if not self._stop_requested:
                         self.resourceUpdate.emit(-1.0, -1.0, -3.0, "Data Error")

            QThread.msleep(self.WORKER_LOOP_CHECK_INTERVAL_MS)

        logger.info(f"ResourceMonitorWorker: _monitor_resources loop EXITED (StopFlag: {self._stop_requested}). Emitting finished_signal.")
        self.finished_signal.emit()


class ResourceMonitorManager(QObject):
    def __init__(self, main_window_ref, settings_manager, parent=None):
        super().__init__(parent)
        self.mw = main_window_ref
        self.settings_manager = settings_manager
        self.worker: ResourceMonitorWorker | None = None
        self.thread: QThread | None = None

    def setup_and_start_monitor(self):
        if not self.settings_manager.get("resource_monitor_enabled"):
            logger.info("ResourceMonitorManager: Monitor is disabled by settings. Not starting.")
            return

        if self.thread or self.worker:
            logger.warning("ResourceMonitorManager: Monitor already set up.")
            return

        interval = self.settings_manager.get("resource_monitor_interval_ms")
        logger.info(f"ResourceMonitorManager: Setting up monitor with interval: {interval} ms.")

        self.thread = QThread(self.mw) 
        self.thread.setObjectName("ResourceMonitorQThread_Managed")
        self.worker = ResourceMonitorWorker(interval_ms=interval)
        self.worker.moveToThread(self.thread)
        
        if hasattr(self.mw, '_update_resource_display'):
            self.worker.resourceUpdate.connect(self.mw._update_resource_display)
        
        self.thread.started.connect(self.worker.start_monitoring)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker._shutdown_nvml)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._handle_worker_thread_finished) 

        self.thread.start()
        logger.info("ResourceMonitorManager: Monitor thread initialized and started.")
    
    @pyqtSlot()
    def _handle_worker_thread_finished(self):
        logger.debug("ResourceMonitorManager: Worker's finished_signal received, thread has finished.")
        # --- KEY CHANGE: Clear references after the thread confirms it's finished ---
        self.worker = None
        self.thread = None

    def stop_monitoring_system(self):
        logger.info("ResourceMonitorManager: stop_monitoring_system called.")
        
        if self.thread and self.thread.isRunning() and self.worker:
            logger.info("ResourceMonitorManager: Attempting to stop resource monitor worker and thread...")
            
            # --- KEY CHANGE: Simplified stop sequence ---
            # Tell the worker to stop its loop. The worker will emit finished_signal when its loop exits.
            # This signal will then trigger thread.quit() and the cleanup.
            QMetaObject.invokeMethod(self.worker, "stop_monitoring", Qt.QueuedConnection)
            
            logger.debug("ResourceMonitorManager: Waiting for resource monitor thread to finish...")
            if not self.thread.wait(2000): # Reduced timeout, should be faster now
                logger.warning("ResourceMonitorManager: Resource monitor thread did not finish gracefully within timeout. Terminating.")
                self.thread.terminate()
            else:
                logger.info("ResourceMonitorManager: Resource monitor thread stopped gracefully.")
        else:
            logger.debug("ResourceMonitorManager: Stop called but no running thread or worker found.")

        # --- KEY CHANGE: Cleanup references here as a final measure ---
        self.worker = None
        self.thread = None
        logger.debug("ResourceMonitorManager: Worker and thread references cleared.")