# fsm_designer_project/logging_setup.py

import logging
import html
import time
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QTextEdit
from ..utils import (
    COLOR_ACCENT_ERROR, COLOR_ACCENT_WARNING, COLOR_TEXT_SECONDARY,
    COLOR_TEXT_EDITOR_DARK_PRIMARY, COLOR_ACCENT_SUCCESS, COLOR_BACKGROUND_EDITOR_DARK,
    COLOR_TEXT_EDITOR_DARK_SECONDARY
)
from PyQt5.QtGui import QColor, QPalette

logger = logging.getLogger(__name__)

class QtLogSignal(QObject):
    log_received = pyqtSignal(str)
    clear_logs_signal = pyqtSignal()

class HtmlFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()
        self.level_colors = {
            logging.DEBUG: COLOR_TEXT_EDITOR_DARK_SECONDARY, # Use dynamic color string
            logging.INFO: COLOR_TEXT_EDITOR_DARK_PRIMARY,    # Use dynamic color string
            logging.WARNING: COLOR_ACCENT_WARNING,           # Use dynamic color string
            logging.ERROR: COLOR_ACCENT_ERROR,               # Use dynamic color string
            logging.CRITICAL: QColor(COLOR_ACCENT_ERROR).darker(120).name(), # Darker error
        }

    def format(self, record):
        timestamp = time.strftime('%H:%M:%S', time.localtime(record.created))
        plain_message = record.getMessage()
        escaped_msg = html.escape(plain_message)

        level_color_str = self.level_colors.get(record.levelno, COLOR_TEXT_EDITOR_DARK_PRIMARY)
        level_name_html = f"<b style='color:{level_color_str};'>{html.escape(record.levelname)}</b>"
        
        # Use a consistent secondary text color for logger name
        logger_name_color_str = COLOR_TEXT_EDITOR_DARK_SECONDARY 
        logger_name_html = f"<span style='color:{logger_name_color_str}; font-style:italic;'>[{html.escape(record.name)}]</span>"

        message_html = f"<span style='color:{level_color_str};'>{escaped_msg}</span>"

        log_entry_html = (
            f"<div style='line-height: 1.3; margin-bottom: 2px; font-family: Consolas, \"Courier New\", monospace; font-size: 9pt;'>"
            f"<span style='color:{COLOR_TEXT_EDITOR_DARK_SECONDARY}; font-size:7pt;'>[{timestamp}]</span> " # Darker timestamp
            f"{level_name_html} "
            f"{logger_name_html} "
            f"{message_html}"
            f"</div>"
        )
        return log_entry_html

class PlainTextFormatter(logging.Formatter):
    """
    A simple formatter to get plain text output for saving or copying the log.
    """
    def format(self, record):
        # We need to call the base class formatter, but this custom class is just for the format string
        # Temporarily create a formatter with the desired format string.
        temp_formatter = logging.Formatter('%(asctime)s [%(levelname)-7s] [%(name)s] %(message)s', '%H:%M:%S')
        return temp_formatter.format(record).strip()


class QTextEditHandler(logging.Handler):
    def __init__(self, text_edit_widget: QTextEdit):
        super().__init__()
        self.widget = text_edit_widget
        self.log_signal_emitter = QtLogSignal()
        self.log_signal_emitter.log_received.connect(self.widget.append)
        self.log_signal_emitter.clear_logs_signal.connect(self.widget.clear)

        self._all_records = []
        self._filter_level = logging.INFO
        self._filter_text = ""

    def _passes_filters(self, record: logging.LogRecord) -> bool:
        if record.levelno < self._filter_level:
            return False
        
        if self._filter_text:
            text_filter = self._filter_text.lower()
            # Check message and logger name for the filter text
            if text_filter not in record.getMessage().lower() and \
               text_filter not in record.name.lower():
                return False

        return True

    def set_filters(self, level=logging.INFO, text=""):
        """Sets the log level and text filters, then redisplays the logs."""
        logger.debug(f"Log filters set to level: {logging.getLevelName(level)}, text: '{text}'")
        self._filter_level = level
        self._filter_text = text.strip().lower() if text else ""
        self._redisplay_logs()

    def _redisplay_logs(self):
        """Clears and re-populates the log widget based on current filters."""
        # Using the signal mechanism ensures this is thread-safe
        self.log_signal_emitter.clear_logs_signal.emit()
        # Collect all messages that pass the filter
        filtered_messages = [self.format(record) for record in self._all_records if self._passes_filters(record)]
        # Use a single `append` with joined messages for much better performance than emitting one by one
        if filtered_messages:
            full_html = "".join(filtered_messages)
            self.log_signal_emitter.log_received.emit(full_html)
        
        self.widget.verticalScrollBar().setValue(self.widget.verticalScrollBar().maximum())
        logger.debug("Log view redisplayed with current filters.")

    def clear_log(self):
        """Clears all stored log records and updates the widget."""
        self._all_records = []
        self.log_signal_emitter.clear_logs_signal.emit()
        logging.info("Log cleared by user.") # This will be re-added as the first message
        
    def get_full_log_text(self, plain: bool = True) -> str:
        """Returns the full, unfiltered log history as a single string."""
        if plain:
            formatter = PlainTextFormatter()
            return "\n".join(formatter.format(record) for record in self._all_records)
        else:
            formatter = HtmlFormatter()
            # Simple version for HTML export (could be improved with full doc structure)
            return "".join(formatter.format(record) for record in self._all_records)


    def emit(self, record):
        try:
            # Store every record regardless of filters
            self._all_records.append(record)

            # Only append to the widget if it passes the current filters
            if self._passes_filters(record):
                msg = self.format(record)
                self.log_signal_emitter.log_received.emit(msg)
        except Exception:
            self.handleError(record)

def setup_global_logging(log_widget: QTextEdit) -> QTextEditHandler:
    """Configures the root logger to use a console handler and a custom UI handler."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) 

    # Clean up any existing handlers
    for handler in root_logger.handlers[:]: 
        root_logger.removeHandler(handler)
        handler.close()

    # Console Handler (for terminal output)
    console_formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(levelname)-7s] [%(name)-25.25s] %(message)s',
                                          datefmt='%H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG) 
    root_logger.addHandler(console_handler)

    # UI Handler (for the application's log dock)
    ui_handler = QTextEditHandler(log_widget)
    ui_handler.setFormatter(HtmlFormatter())
    ui_handler.setLevel(logging.DEBUG) # Let the handler's internal filter manage display level
    root_logger.addHandler(ui_handler)

    # Set background color of the log_widget to match editor dark theme
    palette = log_widget.palette()
    palette.setColor(QPalette.Base, QColor(COLOR_BACKGROUND_EDITOR_DARK))
    log_widget.setPalette(palette)


    logging.info("Logging initialized (UI: HTML, Console: Plain).")
    
    # Return the instance of the handler so the main window can control it
    return ui_handler