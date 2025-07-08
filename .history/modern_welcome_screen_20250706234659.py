# fsm_designer_project/modern_welcome_screen.py
"""
Modern welcome screen with enhanced visuals and animations.
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QScrollArea, QGridLayout, QStyle
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QBrush, QColor, QPen, QLinearGradient
from PyQt5.QtWidgets import QStyle
from .utils import get_standard_icon
from .config import (
    APP_NAME, APP_VERSION, COLOR_ACCENT_PRIMARY, COLOR_BACKGROUND_LIGHT,
    COLOR_TEXT_PRIMARY, COLOR_BORDER_LIGHT, COLOR_TEXT_SECONDARY,
    COLOR_BACKGROUND_APP, COLOR_ACCENT_SECONDARY
)


class ActionCard(QFrame):
    """Modern action card with hover effects."""
    
    clicked = pyqtSignal()
    
    def __init__(self, title, description, icon, parent=None):
        super().__init__(parent)
        self.title = title
        self.init_ui(title, description, icon)
        
    def init_ui(self, title, description, icon):
        """Initialize the UI."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(280, 120)
        
        # Apply initial style
        self.update_style(False)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Icon
        icon_label = QLabel()
        if isinstance(icon, QIcon):
            icon_label.setPixmap(icon.pixmap(48, 48))
        else:
            icon_label.setPixmap(self.create_gradient_icon())
        icon_label.setFixedSize(48, 48)
        layout.addWidget(icon_label)
        
        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: 12pt;
                font-weight: bold;
            }}
        """)
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-size: 9pt;
            }}
        """)
        text_layout.addWidget(desc_label)
        text_layout.addStretch()
        
        layout.addLayout(text_layout)
        
        # Add shadow effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(10)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        
    def create_gradient_icon(self):
        """Create a gradient icon."""
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient
        gradient = QLinearGradient(0, 0, 48, 48)
        gradient.setColorAt(0, QColor(COLOR_ACCENT_PRIMARY))
        gradient.setColorAt(1, QColor(COLOR_ACCENT_SECONDARY))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 48, 48, 8, 8)
        
        painter.end()
        return pixmap
        
    def update_style(self, hover):
        """Update card style based on hover state."""
        if hover:
            self.setStyleSheet(f"""
                ActionCard {{
                    background-color: {COLOR_BACKGROUND_LIGHT};
                    border: 2px solid {COLOR_ACCENT_PRIMARY};
                    border-radius: 8px;
                }}
            """)
            self.shadow.setBlurRadius(20)
            self.shadow.setOffset(0, 4)
        else:
            self.setStyleSheet(f"""
                ActionCard {{
                    background-color: {COLOR_BACKGROUND_LIGHT};
                    border: 1px solid {COLOR_BORDER_LIGHT};
                    border-radius: 8px;
                }}
            """)
            self.shadow.setBlurRadius(10)
            self.shadow.setOffset(0, 2)
            
    def enterEvent(self, event):
        """Handle mouse enter."""
        self.update_style(True)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self.update_style(False)
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class RecentFileItem(QFrame):
    """Recent file item with preview."""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(60)
        
        self.setStyleSheet(f"""
            RecentFileItem {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 8px;
            }}
            RecentFileItem:hover {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # File icon
        icon_label = QLabel()
        icon_label.setPixmap(get_standard_icon(QStyle.SP_FileIcon).pixmap(32, 32))
        layout.addWidget(icon_label)
        
        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        file_name = os.path.basename(self.file_path)
        name_label = QLabel(file_name)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-weight: bold;
            }}
        """)
        info_layout.addWidget(name_label)
        
        path_label = QLabel(self.file_path)
        path_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-size: 8pt;
            }}
        """)
        info_layout.addWidget(path_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)


class ModernWelcomeScreen(QWidget):
    """Modern welcome screen with enhanced design."""
    
    # Signals
    newFileRequested = pyqtSignal()
    openFileRequested = pyqtSignal()
    openRecentRequested = pyqtSignal(str)
    showGuideRequested = pyqtSignal()
    showExamplesRequested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create gradient background
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {COLOR_BACKGROUND_APP},
                    stop: 1 {QColor(COLOR_BACKGROUND_APP).darker(105).name()}
                );
            }}
        """)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 12px;
                background-color: transparent;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 0, 0, 0.3);
            }
        """)
        main_layout.addWidget(scroll)
        
        # Content widget
        content = QWidget()
        scroll.setWidget(content)
        
        # Content layout
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(60, 60, 60, 60)
        content_layout.setSpacing(40)
        
        # Header
        self.create_header(content_layout)
        
        # Action cards
        self.create_action_cards(content_layout)
        
        # Recent files
        self.create_recent_files(content_layout)
        
        # Footer
        self.create_footer(content_layout)
        
        content_layout.addStretch()
        
    def create_header(self, layout):
        """Create the header section."""
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(10)
        
        # Logo/Title
        title_label = QLabel(APP_NAME)
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_ACCENT_PRIMARY};
                padding: 20px;
            }}
        """)
        header_layout.addWidget(title_label)
        
        # Version and tagline
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-size: 12pt;
            }}
        """)
        header_layout.addWidget(version_label)
        
        tagline_label = QLabel("Design, Simulate, and Generate Finite State Machines")
        tagline_label.setAlignment(Qt.AlignCenter)
        tagline_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: 14pt;
                padding: 10px;
            }}
        """)
        header_layout.addWidget(tagline_label)
        
        layout.addWidget(header_widget)
        
    def create_action_cards(self, layout):
        """Create action cards section."""
        cards_widget = QWidget()
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setSpacing(20)
        
        # Create cards
        new_card = ActionCard(
            "New Diagram",
            "Create a new FSM from scratch",
            get_standard_icon(QStyle.SP_FileIcon)
        )
        new_card.clicked.connect(self.newFileRequested.emit)
        cards_layout.addWidget(new_card, 0, 0)
        
        open_card = ActionCard(
            "Open Diagram",
            "Open an existing FSM file",
            get_standard_icon(QStyle.SP_DialogOpenButton)
        )
        open_card.clicked.connect(self.openFileRequested.emit)
        cards_layout.addWidget(open_card, 0, 1)
        
        guide_card = ActionCard(
            "Quick Start Guide",
            "Learn the basics in minutes",
            get_standard_icon(QStyle.SP_MessageBoxInformation)
        )
        guide_card.clicked.connect(self.showGuideRequested.emit)
        cards_layout.addWidget(guide_card, 1, 0)
        
        examples_card = ActionCard(
            "Browse Examples",
            "Explore sample FSM designs",
            get_standard_icon(QStyle.SP_DirIcon)
        )
        examples_card.clicked.connect(self.showExamplesRequested.emit)
        cards_layout.addWidget(examples_card, 1, 1)
        
        # Center the grid
        cards_container = QWidget()
        cards_container_layout = QHBoxLayout(cards_container)
        cards_container_layout.addStretch()
        cards_container_layout.addWidget(cards_widget)
        cards_container_layout.addStretch()
        
        layout.addWidget(cards_container)
        
    def create_recent_files(self, layout):
        """Create recent files section."""
        # Section header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        recent_label = QLabel("Recent Files")
        recent_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: 16pt;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(recent_label)
        header_layout.addStretch()
        
        layout.addWidget(header_widget)
        
        # Recent files container
        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(10)
        
        # Placeholder
        self.no_recent_label = QLabel("No recent files")
        self.no_recent_label.setAlignment(Qt.AlignCenter)
        self.no_recent_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-style: italic;
                padding: 40px;
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 8px;
            }}
        """)
        self.recent_layout.addWidget(self.no_recent_label)
        
        layout.addWidget(self.recent_container)
        
    def create_footer(self, layout):
        """Create footer section."""
        footer = QLabel("© 2024 FSM Designer | Built with PyQt5")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-size: 9pt;
                padding: 20px;
            }}
        """)
        layout.addWidget(footer)
        
    def update_recent_files(self, recent_files):
        """Update recent files list."""
        # Clear existing items
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not recent_files:
            self.recent_layout.addWidget(self.no_recent_label)
            self.no_recent_label.show()
        else:
            self.no_recent_label.hide()
            for file_path in recent_files[:5]:  # Show up to 5 recent files
                item = RecentFileItem(file_path)
                item.clicked.connect(self.openRecentRequested.emit)
                self.recent_layout.addWidget(item)