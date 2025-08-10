# fsm_designer_project/ui/widgets/modern_welcome_screen.py
"""
Modern welcome screen with enhanced visuals and animations.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, PYQT_VERSION_STR
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QBrush, QColor, QPen, QLinearGradient
import os
from PyQt6.QtWidgets import QStyle
from ...codegen import get_standard_icon
from ...codegen.config import (
    APP_NAME, APP_VERSION, COLOR_ACCENT_PRIMARY, COLOR_BACKGROUND_LIGHT,
    COLOR_TEXT_PRIMARY, COLOR_BORDER_LIGHT, COLOR_TEXT_SECONDARY,
    COLOR_BACKGROUND_APP, COLOR_ACCENT_SECONDARY, PROJECT_FILE_EXTENSION
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
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(280, 120)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Icon
        self.icon_label = QLabel()
        if isinstance(icon, QIcon):
            self.icon_label.setPixmap(icon.pixmap(48, 48))
        else:
            self.icon_label.setPixmap(self.create_gradient_icon())
        self.icon_label.setFixedSize(48, 48)
        layout.addWidget(self.icon_label)
        
        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        
        self.title_label = QLabel(title)
        text_layout.addWidget(self.title_label)
        
        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        text_layout.addWidget(self.desc_label)
        text_layout.addStretch()
        
        layout.addLayout(text_layout)
        
        # Add shadow effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(10)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)

        # Apply initial style
        self.update_styles(False)
        
    def create_gradient_icon(self):
        """Create a gradient icon."""
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create gradient
        gradient = QLinearGradient(0, 0, 48, 48)
        gradient.setColorAt(0, QColor(COLOR_ACCENT_PRIMARY))
        gradient.setColorAt(1, QColor(COLOR_ACCENT_SECONDARY))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 48, 48, 8, 8)
        
        painter.end()
        return pixmap
        
    def update_styles(self, hover):
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
        
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 12pt; font-weight: bold;")
        self.desc_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 9pt;")
            
    def enterEvent(self, event):
        """Handle mouse enter."""
        super().enterEvent(event)
        self.update_styles(True)
        
    def leaveEvent(self, event):
        """Handle mouse leave."""
        super().leaveEvent(event)
        self.update_styles(False)
        
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class RecentFileItem(QFrame):
    """Recent file item with preview."""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.init_ui()
        self.update_styles()
        
    def init_ui(self):
        """Initialize the UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(60)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # File icon
        icon_label = QLabel()
        # --- MODIFICATION: Use a folder/dir icon for projects ---
        icon_label.setPixmap(get_standard_icon(QStyle.StandardPixmap.SP_DirIcon).pixmap(32, 32))
        layout.addWidget(icon_label)
        
        # File info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # --- MODIFICATION: Display Project Name and Path ---
        project_dir = os.path.dirname(self.file_path)
        project_name = os.path.basename(project_dir)
        self.name_label = QLabel(project_name)
        self.path_label = QLabel(project_dir)
        # --- END MODIFICATION ---

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.path_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
    def update_styles(self):
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
        self.name_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: bold;")
        self.path_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 8pt;")

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)



class ModernWelcomeScreen(QWidget):
    """Modern welcome screen with enhanced design."""
    
    # Signals
    newFileRequested = pyqtSignal()
    openProjectRequested = pyqtSignal()
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
        
        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_layout.addWidget(self.scroll_area)
        
        # Content widget
        content = QWidget()
        self.scroll_area.setWidget(content)
        
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
        
        self.update_styles()

    def update_styles(self):
        """Re-apply all stylesheets to reflect theme changes."""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {COLOR_BACKGROUND_APP},
                    stop: 1 {QColor(COLOR_BACKGROUND_APP).darker(105).name()}
                );
            }}
        """)
        self.scroll_area.setStyleSheet("""
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
        self.title_label.setStyleSheet(f"color: {COLOR_ACCENT_PRIMARY}; font-size: 32pt; font-weight: bold; padding: 20px;")
        self.version_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12pt;")
        self.tagline_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 14pt; padding: 10px;")
        self.recent_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 16pt; font-weight: bold;")
        self.no_recent_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-style: italic; padding: 40px; background-color: {COLOR_BACKGROUND_LIGHT}; border: 1px solid {COLOR_BORDER_LIGHT}; border-radius: 8px;")
        self.footer_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 9pt; padding: 20px;")
        
        # Update children widgets
        for child in self.findChildren(ActionCard):
            child.update_styles(False) # Reset hover state
        for child in self.findChildren(RecentFileItem):
            child.update_styles()
            
    def create_header(self, layout):
        """Create the header section."""
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(10)
        
        # Logo/Title
        self.title_label = QLabel(APP_NAME)
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label)
        
        # Version and tagline
        self.version_label = QLabel(f"Version {APP_VERSION}")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.version_label)
        
        self.tagline_label = QLabel("Design, Simulate, and Generate Finite State Machines")
        self.tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.tagline_label)
        
        layout.addWidget(header_widget)
        
    def create_action_cards(self, layout):
        """Create action cards section."""
        cards_widget = QWidget()
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setSpacing(20)
        
        # --- MODIFICATION: "New Project" card ---
        new_card = ActionCard(
            "New Project",
            "Start a new FSM project",
            get_standard_icon(QStyle.StandardPixmap.SP_FileIcon)
        )
        new_card.clicked.connect(self.newFileRequested.emit)
        cards_layout.addWidget(new_card, 0, 0)
        
        # --- MODIFICATION: "Open Project" card ---
        open_card = ActionCard(
            "Open Project",
            "Open an existing .bsmproj file",
            get_standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton)
        )
        open_card.clicked.connect(self.openProjectRequested.emit)
        cards_layout.addWidget(open_card, 0, 1)
        # --- END MODIFICATION ---
        
        guide_card = ActionCard(
            "Quick Start Guide",
            "Learn the basics in minutes",
            get_standard_icon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        guide_card.clicked.connect(self.showGuideRequested.emit)
        cards_layout.addWidget(guide_card, 1, 0)
        
        examples_card = ActionCard(
            "Browse Examples",
            "Explore sample FSM designs",
            get_standard_icon(QStyle.StandardPixmap.SP_DirIcon)
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
        
        # --- FIX: Update label to be specific to projects ---
        self.recent_label = QLabel("Recent Projects")
        # --- END FIX ---
        header_layout.addWidget(self.recent_label)
        header_layout.addStretch()
        
        layout.addWidget(header_widget)
        
        # Recent files container
        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(10)
        
        # Placeholder
        self.no_recent_label = QLabel("No recent projects")
        self.no_recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_layout.addWidget(self.no_recent_label)
        
        layout.addWidget(self.recent_container)
        
    def create_footer(self, layout):
        """Create footer section."""
        self.footer_label = QLabel(f"© 2024 FSM Designer | Built with PyQt{PYQT_VERSION_STR}")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.footer_label)
        
    def update_recent_files(self, recent_files):
        """Update recent files list, filtering for projects."""
        if not hasattr(self, 'recent_layout'):
            return
            
        # Clear existing items
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Filter the list to only show project files
        project_files = [p for p in recent_files if p.endswith(PROJECT_FILE_EXTENSION)]
        
        if not project_files:
            if hasattr(self, 'no_recent_label'):
                self.recent_layout.addWidget(self.no_recent_label)
                self.no_recent_label.show()
        else:
            if hasattr(self, 'no_recent_label'):
                self.no_recent_label.hide()
            # Show up to 5 recent projects
            for file_path in project_files[:5]:
                item = RecentFileItem(file_path)
                item.clicked.connect(self.openRecentRequested.emit)
                self.recent_layout.addWidget(item)
# For compatibility with older code that might import WelcomeWidget
WelcomeWidget = ModernWelcomeScreen