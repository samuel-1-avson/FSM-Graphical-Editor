# fsm_designer_project/ribbon_toolbar.py
"""
Modern ribbon-style toolbar implementation for FSM Designer.
Provides a more intuitive and visually appealing interface.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton, 
    QLabel, QFrame, QButtonGroup, QSizePolicy, QMenu, QWidgetAction,
    QSlider, QSpinBox, QComboBox, QColorDialog, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QPixmap, QPainter, QBrush

from .utils import get_standard_icon
from .config import (
    COLOR_ACCENT_PRIMARY, COLOR_BACKGROUND_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_BORDER_LIGHT, COLOR_TEXT_SECONDARY, COLOR_BACKGROUND_APP
)


class RibbonButton(QToolButton):
    """Enhanced button for ribbon interface with hover effects."""
    
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setText(text)
        if icon:
            self.setIcon(icon)
        self.setIconSize(QSize(32, 32))
        self.setMinimumSize(QSize(80, 70))
        self.setMaximumHeight(75)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # Enhanced styling
        self.setStyleSheet("""
            RibbonButton {
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
                background-color: transparent;
            }
            RibbonButton:hover {
                background-color: rgba(0, 120, 215, 0.1);
                border: 1px solid rgba(0, 120, 215, 0.3);
            }
            RibbonButton:pressed {
                background-color: rgba(0, 120, 215, 0.2);
                border: 1px solid rgba(0, 120, 215, 0.5);
            }
            RibbonButton:checked {
                background-color: rgba(0, 120, 215, 0.15);
                border: 1px solid rgba(0, 120, 215, 0.4);
            }
        """)


class RibbonTab(QWidget):
    """A tab in the ribbon containing groups of related functions."""
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)
        self.groups = []
        
        # Add stretch at the end
        self.layout.addStretch()
        
    def add_group(self, group):
        """Add a ribbon group to this tab."""
        # Remove the stretch, add group, then re-add stretch
        self.layout.takeAt(self.layout.count() - 1)
        self.layout.addWidget(group)
        self.groups.append(group)
        self.layout.addStretch()


class RibbonGroup(QFrame):
    """A group of related controls within a ribbon tab."""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            RibbonGroup {{
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 4px;
                background-color: {COLOR_BACKGROUND_LIGHT};
                margin: 2px;
            }}
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 3, 5, 3)
        main_layout.setSpacing(2)
        
        # Content area
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(4)
        main_layout.addLayout(self.content_layout)
        
        # Title label
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-size: 8pt;
                font-weight: bold;
                padding: 2px;
                background-color: transparent;
            }}
        """)
        main_layout.addWidget(title_label)
        
    def add_button(self, button):
        """Add a button to this group."""
        self.content_layout.addWidget(button)
        
    def add_widget(self, widget):
        """Add any widget to this group."""
        self.content_layout.addWidget(widget)
        
    def add_separator(self):
        """Add a vertical separator."""
        separator = QFrame()
        separator.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        separator.setStyleSheet(f"QFrame {{ color: {COLOR_BORDER_LIGHT}; }}")
        self.content_layout.addWidget(separator)


class ModernRibbon(QWidget):
    """Modern ribbon interface replacing traditional toolbar."""
    
    # Signals
    newFileRequested = pyqtSignal()
    openFileRequested = pyqtSignal()
    saveFileRequested = pyqtSignal()
    modeChanged = pyqtSignal(str)
    zoomChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = {}
        self.current_tab = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the ribbon UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Tab bar
        self.tab_bar = QWidget()
        self.tab_bar.setFixedHeight(30)
        self.tab_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND_APP};
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            }}
        """)
        
        self.tab_layout = QHBoxLayout(self.tab_bar)
        self.tab_layout.setContentsMargins(10, 0, 10, 0)
        self.tab_layout.setSpacing(5)
        
        # Tab buttons group
        self.tab_button_group = QButtonGroup(self)
        self.tab_button_group.buttonClicked.connect(self.on_tab_clicked)
        
        main_layout.addWidget(self.tab_bar)
        
        # Content area
        self.content_area = QWidget()
        self.content_area.setFixedHeight(85)
        self.content_area.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border-bottom: 2px solid {COLOR_ACCENT_PRIMARY};
            }}
        """)
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content_area)
        
        # Create tabs
        self.create_home_tab()
        self.create_design_tab()
        self.create_simulation_tab()
        self.create_view_tab()
        
        # Select first tab
        if self.tab_button_group.buttons():
            self.tab_button_group.buttons()[0].click()
            
    def create_tab_button(self, text):
        """Create a styled tab button."""
        button = QPushButton(text)
        button.setCheckable(True)
        button.setFixedHeight(28)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                padding: 0 15px;
                color: {COLOR_TEXT_PRIMARY};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 120, 215, 0.1);
            }}
            QPushButton:checked {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border-top: 2px solid {COLOR_ACCENT_PRIMARY};
                border-left: 1px solid {COLOR_BORDER_LIGHT};
                border-right: 1px solid {COLOR_BORDER_LIGHT};
            }}
        """)
        return button
        
    def add_tab(self, name, tab_widget):
        """Add a new tab to the ribbon."""
        button = self.create_tab_button(name)
        self.tab_button_group.addButton(button)
        self.tab_layout.addWidget(button)
        self.tabs[button] = tab_widget
        
    def on_tab_clicked(self, button):
        """Handle tab button clicks."""
        # Hide all tabs
        for tab in self.tabs.values():
            tab.hide()
            
        # Show selected tab
        if button in self.tabs:
            self.tabs[button].show()
            self.current_tab = self.tabs[button]
            
        # Update content area
        if self.content_layout.count() > 0:
            self.content_layout.takeAt(0)
        self.content_layout.addWidget(self.current_tab)
        
    def create_home_tab(self):
        """Create the Home tab with file operations and clipboard."""
        tab = RibbonTab("Home")
        
        # File group
        file_group = RibbonGroup("File")
        
        new_btn = RibbonButton("New", get_standard_icon(QStyle.SP_FileIcon))
        new_btn.clicked.connect(self.newFileRequested.emit)
        file_group.add_button(new_btn)
        
        open_btn = RibbonButton("Open", get_standard_icon(QStyle.SP_DialogOpenButton))
        open_btn.clicked.connect(self.openFileRequested.emit)
        file_group.add_button(open_btn)
        
        save_btn = RibbonButton("Save", get_standard_icon(QStyle.SP_DialogSaveButton))
        save_btn.clicked.connect(self.saveFileRequested.emit)
        file_group.add_button(save_btn)
        
        tab.add_group(file_group)
        
        # Clipboard group
        clipboard_group = RibbonGroup("Clipboard")
        
        cut_btn = RibbonButton("Cut", get_standard_icon(QStyle.SP_DialogCancelButton))
        clipboard_group.add_button(cut_btn)
        
        copy_btn = RibbonButton("Copy", get_standard_icon(QStyle.SP_FileDialogDetailedView))
        clipboard_group.add_button(copy_btn)
        
        paste_btn = RibbonButton("Paste", get_standard_icon(QStyle.SP_DialogApplyButton))
        clipboard_group.add_button(paste_btn)
        
        tab.add_group(clipboard_group)
        
        self.add_tab("Home", tab)
        
    def create_design_tab(self):
        """Create the Design tab with FSM elements."""
        tab = RibbonTab("Design")
        
        # Elements group
        elements_group = RibbonGroup("Elements")
        
        state_btn = RibbonButton("State", self.create_state_icon())
        state_btn.setCheckable(True)
        state_btn.clicked.connect(lambda: self.modeChanged.emit("add_state"))
        elements_group.add_button(state_btn)
        
        transition_btn = RibbonButton("Transition", self.create_transition_icon())
        transition_btn.setCheckable(True)
        transition_btn.clicked.connect(lambda: self.modeChanged.emit("add_transition"))
        elements_group.add_button(transition_btn)
        
        comment_btn = RibbonButton("Comment", get_standard_icon(QStyle.SP_MessageBoxInformation))
        comment_btn.setCheckable(True)
        comment_btn.clicked.connect(lambda: self.modeChanged.emit("add_comment"))
        elements_group.add_button(comment_btn)
        
        tab.add_group(elements_group)
        
        # Layout group
        layout_group = RibbonGroup("Layout")
        
        align_left_btn = RibbonButton("Align Left", get_standard_icon(QStyle.SP_ArrowLeft))
        layout_group.add_button(align_left_btn)
        
        align_center_btn = RibbonButton("Center", get_standard_icon(QStyle.SP_DialogResetButton))
        layout_group.add_button(align_center_btn)
        
        align_right_btn = RibbonButton("Align Right", get_standard_icon(QStyle.SP_ArrowRight))
        layout_group.add_button(align_right_btn)
        
        tab.add_group(layout_group)
        
        self.add_tab("Design", tab)
        
    def create_simulation_tab(self):
        """Create the Simulation tab."""
        tab = RibbonTab("Simulation")
        
        # Control group
        control_group = RibbonGroup("Control")
        
        play_btn = RibbonButton("Start", get_standard_icon(QStyle.SP_MediaPlay))
        control_group.add_button(play_btn)
        
        pause_btn = RibbonButton("Pause", get_standard_icon(QStyle.SP_MediaPause))
        control_group.add_button(pause_btn)
        
        stop_btn = RibbonButton("Stop", get_standard_icon(QStyle.SP_MediaStop))
        control_group.add_button(stop_btn)
        
        step_btn = RibbonButton("Step", get_standard_icon(QStyle.SP_ArrowForward))
        control_group.add_button(step_btn)
        
        tab.add_group(control_group)
        
        self.add_tab("Simulation", tab)
        
    def create_view_tab(self):
        """Create the View tab with zoom and display options."""
        tab = RibbonTab("View")
        
        # Zoom group
        zoom_group = RibbonGroup("Zoom")
        
        zoom_in_btn = RibbonButton("Zoom In", get_standard_icon(QStyle.SP_DialogYesButton))
        zoom_in_btn.clicked.connect(lambda: self.zoomChanged.emit(120))
        zoom_group.add_button(zoom_in_btn)
        
        zoom_out_btn = RibbonButton("Zoom Out", get_standard_icon(QStyle.SP_DialogNoButton))
        zoom_out_btn.clicked.connect(lambda: self.zoomChanged.emit(-120))
        zoom_group.add_button(zoom_out_btn)
        
        # Zoom slider
        zoom_widget = QWidget()
        zoom_layout = QVBoxLayout(zoom_widget)
        zoom_layout.setContentsMargins(5, 5, 5, 5)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.setTickInterval(50)
        self.zoom_slider.valueChanged.connect(lambda v: self.zoomChanged.emit(v))
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_label)
        
        zoom_group.add_widget(zoom_widget)
        
        tab.add_group(zoom_group)
        
        # Display group
        display_group = RibbonGroup("Display")
        
        grid_btn = RibbonButton("Grid", get_standard_icon(QStyle.SP_FileDialogDetailedView))
        grid_btn.setCheckable(True)
        grid_btn.setChecked(True)
        display_group.add_button(grid_btn)
        
        rulers_btn = RibbonButton("Rulers", get_standard_icon(QStyle.SP_ToolBarHorizontalExtensionButton))
        rulers_btn.setCheckable(True)
        display_group.add_button(rulers_btn)
        
        minimap_btn = RibbonButton("Minimap", get_standard_icon(QStyle.SP_TitleBarNormalButton))
        minimap_btn.setCheckable(True)
        display_group.add_button(minimap_btn)
        
        tab.add_group(display_group)
        
        self.add_tab("View", tab)
        
    def create_state_icon(self):
        """Create a simple state icon."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw rounded rectangle
        painter.setBrush(QBrush(QColor(COLOR_ACCENT_PRIMARY)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 24, 24, 4, 4)
        
        painter.end()
        return QIcon(pixmap)
        
    def create_transition_icon(self):
        """Create a simple transition arrow icon."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw arrow
        painter.setPen(QColor(COLOR_ACCENT_PRIMARY))
        painter.drawLine(6, 16, 26, 16)
        painter.drawLine(20, 10, 26, 16)
        painter.drawLine(20, 22, 26, 16)
        
        painter.end()
        return QIcon(pixmap)
        
    def update_zoom_label(self, value):
        """Update the zoom percentage label."""
        self.zoom_label.setText(f"{value}%")
        self.zoom_slider.setValue(value)