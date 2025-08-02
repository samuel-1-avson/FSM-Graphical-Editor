# fsm_designer_project/utils/logging_setup.py

import logging
import html
import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtWidgets import (QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QComboBox, QLineEdit, QLabel, 
                           QCheckBox, QSpinBox, QGroupBox, QSplitter,
                           QTreeWidget, QTreeWidgetItem, QTabWidget,
                           QProgressBar, QSlider, QApplication)
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon, QPixmap, QPainter
from PyQt5.QtCore import Qt

from .config import (
    COLOR_ACCENT_ERROR, COLOR_ACCENT_WARNING, COLOR_TEXT_SECONDARY,
    COLOR_TEXT_EDITOR_DARK_PRIMARY, COLOR_ACCENT_SUCCESS, COLOR_BACKGROUND_EDITOR_DARK,
    COLOR_TEXT_EDITOR_DARK_SECONDARY, COLOR_ACCENT_PRIMARY
)

logger = logging.getLogger(__name__)

class LogLevel(Enum):
    """Enhanced log level enumeration with colors and priorities"""
    DEBUG = (logging.DEBUG, COLOR_TEXT_EDITOR_DARK_SECONDARY, "🔍")
    INFO = (logging.INFO, COLOR_TEXT_EDITOR_DARK_PRIMARY, "ℹ️")
    WARNING = (logging.WARNING, COLOR_ACCENT_WARNING, "⚠️")
    ERROR = (logging.ERROR, COLOR_ACCENT_ERROR, "❌")
    CRITICAL = (logging.CRITICAL, COLOR_ACCENT_ERROR, "🔥")
    
    def __init__(self, level: int, color: str, icon: str):
        self.level = level
        self.color = color
        self.icon = icon

@dataclass
class LogEntry:
    """Enhanced log entry with metadata"""
    timestamp: datetime
    level: LogLevel
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    thread_id: int
    process_id: int
    exc_info: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

class LogStats:
    """Statistics tracker for log entries"""
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.counts = {level: 0 for level in LogLevel}
        self.total_entries = 0
        self.start_time = datetime.now()
        self.loggers = {}
    
    def add_entry(self, entry: LogEntry):
        self.total_entries += 1
        for level in LogLevel:
            if level.level == entry.level.level:
                self.counts[level] += 1
                break
        
        if entry.logger_name not in self.loggers:
            self.loggers[entry.logger_name] = 0
        self.loggers[entry.logger_name] += 1

class QtLogSignal(QObject):
    """Enhanced signal emitter for thread-safe logging"""
    log_received = pyqtSignal(object)
    clear_logs_signal = pyqtSignal()
    stats_updated = pyqtSignal(object)
    filter_changed = pyqtSignal(object)

class LogTheme:
    """Theming system for log display"""
    def __init__(self, name: str):
        self.name = name
        self.colors = {}
        self.fonts = {}
        self.styles = {}
    
    @classmethod
    def create_dark_theme(cls):
        theme = cls("Dark")
        theme.colors = {
            'background': COLOR_BACKGROUND_EDITOR_DARK,
            'text_primary': COLOR_TEXT_EDITOR_DARK_PRIMARY,
            'text_secondary': COLOR_TEXT_EDITOR_DARK_SECONDARY,
            'accent': COLOR_ACCENT_PRIMARY,
            'success': COLOR_ACCENT_SUCCESS,
            'warning': COLOR_ACCENT_WARNING,
            'error': COLOR_ACCENT_ERROR,
            'border': '#3c3c3c',
            'selection': '#404040'
        }
        theme.fonts = {
            'log_text': QFont("Consolas", 9),
            'timestamp': QFont("Consolas", 7),
            'ui': QFont("Segoe UI", 9)
        }
        return theme

class AdvancedHtmlFormatter(logging.Formatter):
    """Enhanced HTML formatter with rich styling and features"""
    
    def __init__(self, theme: LogTheme, show_icons: bool = True, 
                 show_thread_info: bool = False, compact_mode: bool = False):
        super().__init__()
        self.theme = theme
        self.show_icons = show_icons
        self.show_thread_info = show_thread_info
        self.compact_mode = compact_mode
        self.level_colors = {level.level: level.color for level in LogLevel}
    
    def format(self, record) -> str:
        """Create rich HTML formatted log entry"""
        entry = self._create_log_entry(record)
        return self._format_html(entry)
    
    def _create_log_entry(self, record) -> LogEntry:
        """Convert LogRecord to enhanced LogEntry"""
        level = next((l for l in LogLevel if l.level == record.levelno), LogLevel.INFO)
        
        return LogEntry(
            timestamp=datetime.fromtimestamp(record.created),
            level=level,
            logger_name=record.name,
            message=record.getMessage(),
            module=record.module if hasattr(record, 'module') else '',
            function=record.funcName if hasattr(record, 'funcName') else '',
            line_number=record.lineno if hasattr(record, 'lineno') else 0,
            thread_id=record.thread if hasattr(record, 'thread') else 0,
            process_id=record.process if hasattr(record, 'process') else 0,
            exc_info=self.formatException(record.exc_info) if record.exc_info else None,
            extra_data=getattr(record, 'extra_data', None)
        )
    
    def _format_html(self, entry: LogEntry) -> str:
        """Format LogEntry as HTML"""
        timestamp_str = entry.timestamp.strftime('%H:%M:%S.%f')[:-3]
        escaped_msg = html.escape(entry.message)
        
        # Build components
        components = []
        
        # Timestamp
        timestamp_html = f"<span style='color:{self.theme.colors['text_secondary']}; font-size:7pt;'>[{timestamp_str}]</span>"
        components.append(timestamp_html)
        
        # Level with icon
        level_html = f"<b style='color:{entry.level.color};'>"
        if self.show_icons:
            level_html += f"{entry.level.icon} "
        level_html += f"{entry.level.name}</b>"
        components.append(level_html)
        
        # Logger name
        logger_html = f"<span style='color:{self.theme.colors['text_secondary']}; font-style:italic;'>[{html.escape(entry.logger_name)}]</span>"
        components.append(logger_html)
        
        # Thread info (optional)
        if self.show_thread_info and not self.compact_mode:
            thread_html = f"<span style='color:{self.theme.colors['text_secondary']}; font-size:7pt;'>(T:{entry.thread_id})</span>"
            components.append(thread_html)
        
        # Message
        message_html = f"<span style='color:{entry.level.color};'>{escaped_msg}</span>"
        components.append(message_html)
        
        # Function/line info for errors
        if entry.level.level >= logging.ERROR and not self.compact_mode:
            location_html = f"<span style='color:{self.theme.colors['text_secondary']}; font-size:7pt;'> [{entry.function}:{entry.line_number}]</span>"
            components.append(location_html)
        
        # Exception info
        if entry.exc_info:
            exc_html = f"<pre style='color:{COLOR_ACCENT_ERROR}; margin:2px 0; padding:4px; background-color:#2d1b1b; border-left:3px solid {COLOR_ACCENT_ERROR};'>{html.escape(entry.exc_info)}</pre>"
            components.append(exc_html)
        
        # Extra data
        if entry.extra_data:
            extra_html = f"<details style='color:{self.theme.colors['text_secondary']}; margin:2px 0;'><summary>Extra Data</summary><pre>{html.escape(json.dumps(entry.extra_data, indent=2))}</pre></details>"
            components.append(extra_html)
        
        # Combine components
        separator = " " if not self.compact_mode else " "
        content = separator.join(components)
        
        # Wrap in container
        container_style = (
            f"line-height: {'1.2' if self.compact_mode else '1.4'}; "
            f"margin-bottom: {'1px' if self.compact_mode else '3px'}; "
            f"font-family: Consolas, 'Courier New', monospace; "
            f"font-size: {'8pt' if self.compact_mode else '9pt'}; "
            f"padding: {'1px 4px' if not self.compact_mode else '0'}; "
            f"border-left: 2px solid {entry.level.color}; "
            f"margin-left: 2px; "
            f"padding-left: 6px;"
        )
        
        return f"<div style='{container_style}'>{content}</div>"

class EnhancedQTextEditHandler(logging.Handler, QObject):
    """Enhanced log handler with advanced features"""
    
    def __init__(self, text_edit_widget: QTextEdit, theme: LogTheme = None):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.widget = text_edit_widget
        self.theme = theme or LogTheme.create_dark_theme()
        
        # Enhanced formatter
        self.html_formatter = AdvancedHtmlFormatter(self.theme)
        self.setFormatter(self.html_formatter)
        
        # Signal system
        self.log_signal_emitter = QtLogSignal()
        self.log_signal_emitter.log_received.connect(self._append_log_entry)
        self.log_signal_emitter.clear_logs_signal.connect(self.widget.clear)
        
        # Storage and filtering
        self._all_entries: List[LogEntry] = []
        self.min_level = logging.INFO
        self.text_filter = ""
        self.stats = LogStats()
        
        # Performance optimization
        self._batch_timer = QTimer()
        self._batch_timer.timeout.connect(self._flush_batch)
        self._batch_timer.setSingleShot(True)
        self._pending_entries = []
        self._batch_size = 50
        self._batch_timeout = 100  # ms
        
        # Setup widget appearance
        self._setup_widget_appearance()
        
        # Auto-scroll management
        self._auto_scroll = True
        self._max_entries = 10000  # Limit for performance
    
    def _setup_widget_appearance(self):
        """Configure the widget's appearance"""
        palette = self.widget.palette()
        palette.setColor(QPalette.Base, QColor(self.theme.colors['background']))
        palette.setColor(QPalette.Text, QColor(self.theme.colors['text_primary']))
        self.widget.setPalette(palette)
        
        # Set font
        self.widget.setFont(self.theme.fonts['log_text'])
        
        # Configure scrolling
        self.widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Connect scroll events
        scrollbar = self.widget.verticalScrollBar()
        scrollbar.valueChanged.connect(self._on_scroll_changed)
    
    def _on_scroll_changed(self, value):
        """Handle scroll changes to manage auto-scroll"""
        maximum = self.widget.verticalScrollBar().maximum()
        self._auto_scroll = (value >= maximum - 10)  # Near bottom
    
    @pyqtSlot(object)
    def _append_log_entry(self, entry: LogEntry):
        """Append a single log entry to the widget"""
        html = self.html_formatter._format_html(entry)
        self.widget.append(html)
        
        if self._auto_scroll:
            scrollbar = self.widget.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def matches(self, entry: LogEntry) -> bool:
        """Check if an entry matches the simple filter criteria."""
        if entry.level.level < self.min_level:
            return False
        
        if self.text_filter:
            # Simple case-insensitive search in message or logger name
            filter_text = self.text_filter.lower()
            if filter_text not in entry.message.lower() and \
               filter_text not in entry.logger_name.lower():
                return False
        
        return True


    def emit(self, record):
        """Handle log record emission with batching"""
        try:
            # Create enhanced log entry
            entry = self.html_formatter._create_log_entry(record)
            
            # Store in memory
            self._all_entries.append(entry)
            self.stats.add_entry(entry)
            
            # Maintain size limit
            if len(self._all_entries) > self._max_entries:
                self._all_entries = self._all_entries[-self._max_entries:]
            
            # Check filter
            if self.matches(entry):
                # Add to batch
                self._pending_entries.append(entry)
                
                # Start or restart batch timer
                if len(self._pending_entries) >= self._batch_size:
                    self._flush_batch()
                else:
                    self._batch_timer.start(self._batch_timeout)
            
            # Emit stats update
            self.log_signal_emitter.stats_updated.emit(self.stats)
            
        except Exception as e:
            self.handleError(record)
    
    def _flush_batch(self):
        """Flush pending entries to UI"""
        if not self._pending_entries:
            return
        
        # Process batch
        for entry in self._pending_entries:
            self.log_signal_emitter.log_received.emit(entry)
        
        self._pending_entries.clear()
        self._batch_timer.stop()
    
    def _refresh_display(self):
        """Refresh the display based on current filter"""
        # Clear widget
        self.log_signal_emitter.clear_logs_signal.emit()
        
        # Filter entries
        filtered_entries = [
            entry for entry in self._all_entries 
            if self.matches(entry)
        ]
        
        # Display filtered entries in batches
        batch_size = 100
        for i in range(0, len(filtered_entries), batch_size):
            batch = filtered_entries[i:i + batch_size]
            for entry in batch:
                self.log_signal_emitter.log_received.emit(entry)
            
            # Allow UI to update
            QApplication.processEvents()
    
    def clear_log(self):
        """Clear all logs and reset stats"""
        self._all_entries.clear()
        self._pending_entries.clear()
        self.stats.reset()
        self.log_signal_emitter.clear_logs_signal.emit()
        logging.info("Log cleared by user.")
    
    def export_logs(self, filename: str, format_type: str = "html", 
                   filtered_only: bool = True) -> bool:
        """Export logs to file"""
        try:
            if filtered_only:
                entries = [e for e in self._all_entries if self.matches(e)]
            else:
                entries = self._all_entries
            path = Path(filename)
            
            if format_type.lower() == "html":
                self._export_html(path, entries)
            elif format_type.lower() == "json":
                self._export_json(path, entries)
            elif format_type.lower() == "txt":
                self._export_text(path, entries)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return False
    
    def _export_html(self, path: Path, entries: List[LogEntry]):
        """Export logs as HTML"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Application Logs</title>
    <style>
        body { background: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace; }
        .log-entry { margin-bottom: 2px; padding: 2px 4px; border-left: 2px solid #666; }
        .debug { border-left-color: #666; }
        .info { border-left-color: #4fc3f7; }
        .warning { border-left-color: #ffb74d; }
        .error { border-left-color: #f44336; }
        .critical { border-left-color: #b71c1c; }
    </style>
</head>
<body>
""")
            for entry in entries:
                html = self.html_formatter._format_html(entry)
                f.write(html)
            f.write("</body></html>")
    
    def _export_json(self, path: Path, entries: List[LogEntry]):
        """Export logs as JSON"""
        data = []
        for entry in entries:
            data.append({
                'timestamp': entry.timestamp.isoformat(),
                'level': entry.level.name,
                'logger': entry.logger_name,
                'message': entry.message,
                'module': entry.module,
                'function': entry.function,
                'line': entry.line_number,
                'thread_id': entry.thread_id,
                'process_id': entry.process_id,
                'exc_info': entry.exc_info,
                'extra_data': entry.extra_data
            })
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _export_text(self, path: Path, entries: List[LogEntry]):
        """Export logs as plain text"""
        with open(path, 'w', encoding='utf-8') as f:
            for entry in entries:
                timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                line = f"[{timestamp}] [{entry.level.name:8}] [{entry.logger_name}] {entry.message}\n"
                if entry.exc_info:
                    line += f"{entry.exc_info}\n"
                f.write(line)
    
    def get_stats(self) -> LogStats:
        """Get current statistics"""
        return self.stats
    
    def set_max_entries(self, max_entries: int):
        """Set maximum number of entries to keep in memory"""
        self._max_entries = max_entries
        if len(self._all_entries) > max_entries:
            self._all_entries = self._all_entries[-max_entries:]
    
    def set_theme(self, theme: LogTheme):
        """Update the theme"""
        self.theme = theme
        self.html_formatter.theme = theme
        self._setup_widget_appearance()
        self._refresh_display()

def setup_global_logging(log_widget: QTextEdit) -> EnhancedQTextEditHandler:
    """
    Sets up the global root logger to send messages to the provided QTextEdit widget.
    This is the main entry point for simple logging setup.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers to prevent duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # Create and add a console handler for debugging
    console_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)-8s] [%(name)-20.20s] %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO) # Keep console less verbose
    root_logger.addHandler(console_handler)

    # Create and add the UI handler
    ui_handler = EnhancedQTextEditHandler(log_widget)
    ui_handler.setLevel(logging.DEBUG) # Capture all levels for the UI
    root_logger.addHandler(ui_handler)
    
    logging.info("Global logging system initialized.")
    return ui_handler