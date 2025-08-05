# fsm_designer_project/ui/widgets/modern_ribbon_toolbar.py
# Professional Ribbon Toolbar with Minimal Design and Enhanced UX
# Redesigned for professional appearance with improved usability

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton, 
    QLabel, QFrame, QButtonGroup, QSizePolicy, QMenu, QComboBox,
    QLineEdit, QSpacerItem, QGraphicsDropShadowEffect, QApplication
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PyQt5.QtGui import QIcon, QColor, QFont, QPainter, QPalette, QFontMetrics

from ...utils import get_standard_icon

# Professional Color Scheme - Minimal and Monochrome
COLORS = {
    'primary': '#2563EB',        # Professional blue
    'primary_light': '#DBEAFE',  # Light blue
    'primary_dark': '#1E40AF',   # Dark blue
    'background': '#FFFFFF',     # Pure white
    'surface': '#F8FAFC',        # Very light gray
    'surface_hover': '#F1F5F9',  # Light gray hover
    'border': '#E2E8F0',         # Light border
    'border_focus': '#CBD5E1',   # Focused border
    'text_primary': '#0F172A',   # Almost black
    'text_secondary': '#64748B', # Medium gray
    'text_muted': '#94A3B8',     # Light gray text
    'shadow': 'rgba(0, 0, 0, 0.05)', # Subtle shadow
    'error': '#EF4444',          # Error red
    'success': '#10B981',        # Success green
}

class ProfessionalButton(QToolButton):
    """Minimalist professional button with subtle interactions"""
    
    def __init__(self, action, is_large=True, parent=None):
        super().__init__(parent)
        self.setDefaultAction(action)
        self.is_large = is_large
        self._setup_button()
        self._apply_professional_style()

    def _setup_button(self):
        """Configure button properties"""
        if self.is_large:
            self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            self.setIconSize(QSize(24, 24))  # Smaller, more refined icons
            self.setMinimumSize(QSize(72, 68))
            self.setMaximumSize(QSize(82, 68))
        else:
            self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            self.setIconSize(QSize(16, 16))
            self.setMinimumSize(QSize(78, 24))
            self.setMaximumHeight(24)
        
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # Remove heavy shadows for cleaner look
        self.setGraphicsEffect(None)
        
        # Enhanced accessibility
        if hasattr(self.defaultAction(), 'toolTip') and self.defaultAction().toolTip():
            self.setToolTip(self.defaultAction().toolTip())

    def _apply_professional_style(self):
        """Apply minimal professional styling"""
        padding = "6px 4px" if self.is_large else "2px 8px"
        font_size = "8pt"
        
        self.setStyleSheet(f"""
            ProfessionalButton {{
                border: 1px solid transparent;
                border-radius: 4px;
                padding: {padding};
                background-color: transparent;
                color: {COLORS['text_primary']};
                font-size: {font_size};
                font-weight: 400;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            ProfessionalButton:hover {{
                background-color: {COLORS['surface_hover']};
                border: 1px solid {COLORS['border_focus']};
                color: {COLORS['primary']};
            }}
            ProfessionalButton:pressed {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary_dark']};
                border: 1px solid {COLORS['primary']};
            }}
            ProfessionalButton:checked {{
                background-color: {COLORS['primary_light']};
                border: 1px solid {COLORS['primary']};
                color: {COLORS['primary_dark']};
                font-weight: 500;
            }}
            ProfessionalButton:disabled {{
                color: {COLORS['text_muted']};
                background-color: transparent;
                border: 1px solid transparent;
            }}
        """)

class ProfessionalSplitButton(QWidget):
    """Clean split button with professional styling"""
    
    def __init__(self, main_action, menu_actions, parent=None):
        super().__init__(parent)
        self._setup_layout()
        self._create_buttons(main_action, menu_actions)
        self._apply_styling()

    def _setup_layout(self):
        """Setup the layout"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def _create_buttons(self, main_action, menu_actions):
        """Create main and dropdown buttons"""
        # Main button
        self.main_button = QToolButton()
        self.main_button.setDefaultAction(main_action)
        self.main_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.main_button.setIconSize(QSize(24, 24))
        self.main_button.setMinimumSize(QSize(56, 68))
        
        # Dropdown button with modern icon
        self.dropdown_button = QToolButton()
        self.dropdown_button.setText("▼")  # Clean dropdown indicator
        self.dropdown_button.setMaximumWidth(16)
        self.dropdown_button.setMinimumHeight(68)
        self.dropdown_button.setPopupMode(QToolButton.InstantPopup)
        
        # Professional menu
        menu = QMenu(self)
        menu.addActions(menu_actions)
        self.dropdown_button.setMenu(menu)
        
        self.layout().addWidget(self.main_button)
        self.layout().addWidget(self.dropdown_button)

    def _apply_styling(self):
        """Apply professional split button styling"""
        main_style = f"""
            QToolButton {{
                border: 1px solid transparent;
                border-radius: 4px 0px 0px 4px;
                background-color: transparent;
                color: {COLORS['text_primary']};
                font-size: 8pt;
                font-weight: 400;
                padding: 4px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QToolButton:hover {{
                background-color: {COLORS['surface_hover']};
                border: 1px solid {COLORS['border_focus']};
                color: {COLORS['primary']};
            }}
            QToolButton:pressed {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary_dark']};
            }}
        """
        
        dropdown_style = f"""
            QToolButton {{
                border: 1px solid transparent;
                border-left: 1px solid {COLORS['border']};
                border-radius: 0px 4px 4px 0px;
                background-color: transparent;
                color: {COLORS['text_secondary']};
                font-size: 8pt;
                padding: 2px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QToolButton:hover {{
                background-color: {COLORS['surface_hover']};
                border: 1px solid {COLORS['border_focus']};
                border-left: 1px solid {COLORS['border_focus']};
                color: {COLORS['primary']};
            }}
            QToolButton:pressed {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary_dark']};
            }}
        """
        
        self.main_button.setStyleSheet(main_style)
        self.dropdown_button.setStyleSheet(dropdown_style)

class ProfessionalGroup(QFrame):
    """Clean, minimal ribbon group with professional appearance"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.title = title
        self._setup_layout()
        self._apply_styling()

    def _setup_layout(self):
        """Setup the group layout"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(2)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(2, 2, 2, 2)
        self.content_layout.setSpacing(2)
        
        main_layout.addWidget(self.content_widget, 1)
        
        # Professional title
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        
        # Clean typography
        font = QFont()
        font.setFamily("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        font.setPointSize(7)
        font.setWeight(QFont.Normal)
        title_label.setFont(font)
        
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']}; 
                font-size: 7pt; 
                font-weight: 400;
                padding: 4px 2px 2px 2px;
                border-top: 1px solid {COLORS['border']};
                margin-top: 2px;
                background-color: transparent;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
        """)
        main_layout.addWidget(title_label)

    def _apply_styling(self):
        """Apply minimal professional styling"""
        self.setMinimumHeight(96)
        self.setMaximumHeight(96)
        self.setMinimumWidth(76)
        
        self.setStyleSheet(f"""
            ProfessionalGroup {{
                border-radius: 4px;
                background-color: transparent;
                border: 1px solid transparent;
            }}
            ProfessionalGroup:hover {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
            }}
        """)

    def add_action_button(self, action, is_large=True):
        """Add a professional action button"""
        button = ProfessionalButton(action, is_large)
        self.content_layout.addWidget(button)
        return button

    def add_split_button(self, main_action, menu_actions):
        """Add a professional split button"""
        split_button = ProfessionalSplitButton(main_action, menu_actions)
        self.content_layout.addWidget(split_button)
        return split_button

    def add_widget(self, widget):
        """Add a custom widget"""
        self.content_layout.addWidget(widget)

    def add_vertical_group(self, actions):
        """Add vertical group of buttons"""
        v_widget = QWidget()
        v_layout = QVBoxLayout(v_widget)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(1)
        
        for action in actions:
            btn = ProfessionalButton(action, is_large=False)
            v_layout.addWidget(btn)
        
        v_layout.addStretch()
        self.content_layout.addWidget(v_widget)
        return v_widget

    def add_separator(self):
        """Add a clean vertical separator"""
        separator = QFrame()
        separator.setFrameStyle(QFrame.VLine | QFrame.Plain)
        separator.setStyleSheet(f"""
            QFrame {{
                color: {COLORS['border']}; 
                background-color: {COLORS['border']};
                margin: 6px 2px;
                max-width: 1px;
            }}
        """)
        separator.setMaximumWidth(1)
        self.content_layout.addWidget(separator)

class ProfessionalInputGroup(QWidget):
    """Professional input controls group"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._setup_layout(title)
        self._apply_styling()

    def _setup_layout(self, title):
        """Setup the input group layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(3)
        layout.addLayout(self.content_layout)
        
        # Professional title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        
        font = QFont()
        font.setFamily("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        font.setPointSize(7)
        font.setWeight(QFont.Normal)
        title_label.setFont(font)
        
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']}; 
                font-size: 7pt; 
                font-weight: 400;
                padding: 4px 2px;
                border-top: 1px solid {COLORS['border']};
                margin-top: 2px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
        """)
        layout.addWidget(title_label)

    def _apply_styling(self):
        """Apply professional styling"""
        self.setMinimumHeight(86)
        self.setMaximumHeight(86)

    def add_combo(self, items, current_text=None):
        """Add a professional combo box"""
        combo = QComboBox()
        combo.addItems(items)
        if current_text:
            combo.setCurrentText(current_text)
        
        combo.setMinimumWidth(100)
        combo.setMaximumHeight(22)
        
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 8pt;
                color: {COLORS['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QComboBox:hover {{
                border: 1px solid {COLORS['border_focus']};
                background-color: {COLORS['surface']};
            }}
            QComboBox:focus {{
                border: 1px solid {COLORS['primary']};
                background-color: {COLORS['background']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 18px;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: 2px solid {COLORS['text_secondary']};
                border-top: none;
                border-right: none;
                width: 4px;
                height: 4px;
                transform: rotate(-45deg);
                margin-right: 4px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                selection-background-color: {COLORS['primary_light']};
                selection-color: {COLORS['primary_dark']};
            }}
        """)
        
        self.content_layout.addWidget(combo)
        return combo

    def add_line_edit(self, placeholder=""):
        """Add a professional line edit"""
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumWidth(100)
        edit.setMaximumHeight(22)
        
        edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 8pt;
                color: {COLORS['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QLineEdit:hover {{
                border: 1px solid {COLORS['border_focus']};
                background-color: {COLORS['surface']};
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
                background-color: {COLORS['background']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
                font-style: normal;
            }}
        """)
        
        self.content_layout.addWidget(edit)
        return edit

class ProfessionalTab(QWidget):
    """Clean tab with professional layout"""
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(6)
        self.layout.addStretch()

    def add_group(self, group):
        """Add a group with clean separator"""
        self.layout.insertWidget(self.layout.count() - 1, group)
        
        # Minimal separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet(f"""
            QFrame {{
                color: {COLORS['border']}; 
                background-color: {COLORS['border']};
                margin: 8px 0px; 
                max-width: 1px;
            }}
        """)
        self.layout.insertWidget(self.layout.count() - 1, separator)

class ProfessionalRibbon(QWidget):
    """Professional ribbon with minimal design and enhanced UX"""
    
    tab_changed = pyqtSignal(str)
    search_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = {}
        self.current_tab_widget = None
        self.file_button = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        self._init_ui()

    def _init_ui(self):
        """Initialize the professional UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Professional tab bar
        self._create_tab_bar()
        main_layout.addWidget(self.tab_bar)

        # Clean content area
        self._create_content_area()
        main_layout.addWidget(self.content_area)

    def _create_tab_bar(self):
        """Create professional tab bar"""
        self.tab_bar = QWidget()
        self.tab_bar.setFixedHeight(32)
        self.tab_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        
        self.tab_layout = QHBoxLayout(self.tab_bar)
        self.tab_layout.setContentsMargins(0, 0, 8, 0)
        self.tab_layout.setSpacing(0)

        # Professional File button
        self._create_file_button()
        
        # Tab buttons container
        self._create_tab_container()
        
        # Professional search
        self._create_search_area()

    def _create_file_button(self):
        """Create professional file button"""
        self.file_button = QToolButton()
        self.file_button.setText("File")
        self.file_button.setCheckable(True)
        self.file_button.setPopupMode(QToolButton.InstantPopup)
        self.file_button.setFixedSize(48, 28)
        
        self.file_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
                border: none; 
                border-radius: 4px;
                padding: 0px 8px;
                font-weight: 500;
                font-size: 8pt;
                margin: 2px 8px 2px 4px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QToolButton:hover {{ 
                background-color: {COLORS['primary_dark']};
            }}
            QToolButton:pressed, QToolButton:checked {{ 
                background-color: {COLORS['primary_dark']};
            }}
        """)
        self.file_button.clicked.connect(self._on_file_button_clicked)
        self.tab_layout.addWidget(self.file_button)

    def _create_tab_container(self):
        """Create tab buttons container"""
        self.tab_buttons_container = QWidget()
        self.tab_buttons_layout = QHBoxLayout(self.tab_buttons_container)
        self.tab_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_buttons_layout.setSpacing(0)
        self.tab_layout.addWidget(self.tab_buttons_container)

        self.tab_button_group = QButtonGroup(self)
        self.tab_button_group.setExclusive(True)
        self.tab_button_group.buttonClicked.connect(self._on_tab_clicked)

    def _create_search_area(self):
        """Create professional search area"""
        self.tab_layout.addStretch()
        
        # Search input
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setFixedSize(140, 22)
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 11px;
                padding: 0px 12px;
                font-size: 8pt;
                color: {COLORS['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QLineEdit:hover {{
                border: 1px solid {COLORS['border_focus']};
                background-color: {COLORS['background']};
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
                background-color: {COLORS['background']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """)
        
        self.tab_layout.addWidget(self.search_bar)

    def _create_content_area(self):
        """Create clean content area"""
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setFixedHeight(100)
        
        self.content_area.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

    def _create_tab_button(self, text):
        """Create professional tab button"""
        button = QPushButton(text)
        button.setCheckable(True)
        button.setFixedHeight(28)
        
        # Calculate width based on text
        font_metrics = QFontMetrics(button.font())
        text_width = font_metrics.horizontalAdvance(text)
        button.setMinimumWidth(text_width + 24)
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border: none;
                border-bottom: 2px solid transparent;
                padding: 4px 12px; 
                color: {COLORS['text_secondary']}; 
                font-weight: 400;
                font-size: 8pt;
                margin: 0px 1px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['surface_hover']};
                color: {COLORS['text_primary']};
                border-bottom: 2px solid {COLORS['border_focus']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['background']};
                border-bottom: 2px solid {COLORS['primary']};
                color: {COLORS['primary']};
                font-weight: 500;
            }}
        """)
        return button

    def add_tab(self, name):
        """Add a new professional tab"""
        tab_widget = ProfessionalTab(name, self)
        button = self._create_tab_button(name)
        
        button.setToolTip(f"Switch to {name} tab")
        
        self.tab_button_group.addButton(button)
        self.tab_buttons_layout.addWidget(button)
        self.tabs[button] = tab_widget
        return tab_widget

    def _on_file_button_clicked(self):
        """Handle file button click"""
        if btn := self.tab_button_group.checkedButton():
            self.tab_button_group.setExclusive(False)
            btn.setChecked(False)
            self.tab_button_group.setExclusive(True)
        
        if self.current_tab_widget:
            self.current_tab_widget.hide()
            self.current_tab_widget = None

    def _on_tab_clicked(self, button):
        """Handle tab click"""
        if self.file_button.isChecked():
            self.file_button.setChecked(False)
        
        if self.current_tab_widget:
            self.current_tab_widget.hide()
        
        self.current_tab_widget = self.tabs.get(button)
        if self.current_tab_widget:
            # Clear existing content
            if self.content_layout.count() > 0:
                item = self.content_layout.takeAt(0)
                if item and item.widget():
                    item.widget().setParent(None)
            
            # Add new tab content
            self.content_layout.addWidget(self.current_tab_widget)
            self.current_tab_widget.show()
            
            self.tab_changed.emit(self.current_tab_widget.name)

    def _on_search_text_changed(self, text):
        """Handle search with debouncing"""
        self.search_timer.stop()
        if text.strip():
            self.search_timer.start(300)

    def _perform_search(self):
        """Perform search"""
        search_text = self.search_bar.text().strip()
        if search_text:
            self.search_requested.emit(search_text)

    def set_file_menu(self, menu: QMenu):
        """Set professional file menu"""
        self.file_button.setMenu(menu)
        
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 16px 6px 28px;
                color: {COLORS['text_primary']};
                font-size: 8pt;
                border-radius: 3px;
                margin: 1px 4px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary_dark']};
            }}
            QMenu::item:disabled {{
                color: {COLORS['text_muted']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {COLORS['border']};
                margin: 4px 8px;
            }}
        """)
        
        menu.aboutToHide.connect(lambda: self.file_button.setChecked(False))

    def select_first_tab(self):
        """Select the first tab"""
        if self.tab_button_group.buttons():
            first_button = self.tab_button_group.buttons()[0]
            first_button.click()

    def set_search_placeholder(self, text):
        """Set search placeholder"""
        self.search_bar.setPlaceholderText(text)

    def clear_search(self):
        """Clear search"""
        self.search_bar.clear()

    def get_current_tab_name(self):
        """Get current tab name"""
        if self.current_tab_widget:
            return self.current_tab_widget.name
        return None

    def set_tab_enabled(self, tab_name, enabled):
        """Enable/disable a specific tab"""
        for button, tab_widget in self.tabs.items():
            if tab_widget.name == tab_name:
                button.setEnabled(enabled)
                if not enabled and button.isChecked():
                    self.select_first_tab()
                break

    def add_quick_access_button(self, action):
        """Add quick access button to tab bar"""
        quick_button = QToolButton()
        quick_button.setDefaultAction(action)
        quick_button.setIconSize(QSize(16, 16))
        quick_button.setFixedSize(24, 24)
        quick_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        
        quick_button.setStyleSheet(f"""
            QToolButton {{
                border: 1px solid transparent;
                border-radius: 4px;
                background-color: transparent;
                color: {COLORS['text_secondary']};
                margin: 4px 2px;
            }}
            QToolButton:hover {{
                background-color: {COLORS['surface_hover']};
                border: 1px solid {COLORS['border_focus']};
                color: {COLORS['primary']};
            }}
            QToolButton:pressed {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary_dark']};
            }}
        """)
        
        # Insert before search area
        self.tab_layout.insertWidget(self.tab_layout.count() - 1, quick_button)
        return quick_button

    def set_compact_mode(self, compact=True):
        """Toggle compact mode for responsive design"""
        if compact:
            self.tab_bar.setFixedHeight(28)
            self.content_area.setFixedHeight(84)
            # Update button sizes for compact mode
            for button in self.tab_button_group.buttons():
                button.setFixedHeight(24)
            self.file_button.setFixedSize(42, 24)
        else:
            self.tab_bar.setFixedHeight(32)
            self.content_area.setFixedHeight(100)
            # Restore normal sizes
            for button in self.tab_button_group.buttons():
                button.setFixedHeight(28)
            self.file_button.setFixedSize(48, 28)

# Professional utility components

class ProfessionalColorButton(QToolButton):
    """Minimal color picker button"""
    
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, color=Qt.black, parent=None):
        super().__init__(parent)
        self.current_color = QColor(color)
        self.setFixedSize(24, 24)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.clicked.connect(self._show_color_dialog)
        self._update_color_display()

    def _update_color_display(self):
        """Update button color display"""
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {self.current_color.name()};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                border: 1px solid {COLORS['border_focus']};
            }}
            QToolButton:pressed {{
                border: 1px solid {COLORS['primary']};
            }}
        """)

    def _show_color_dialog(self):
        """Show professional color picker"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            self._update_color_display()
            self.color_changed.emit(color)

    def set_color(self, color):
        """Set color programmatically"""
        self.current_color = QColor(color)
        self._update_color_display()

class ProfessionalSpinBox(QWidget):
    """Professional spin box component"""
    
    value_changed = pyqtSignal(int)
    
    def __init__(self, minimum=0, maximum=100, value=0, parent=None):
        super().__init__(parent)
        self.setFixedSize(72, 22)
        self._setup_spinbox(minimum, maximum, value)

    def _setup_spinbox(self, minimum, maximum, value):
        """Setup the spin box"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        from PyQt5.QtWidgets import QSpinBox
        self.spinbox = QSpinBox()
        self.spinbox.setRange(minimum, maximum)
        self.spinbox.setValue(value)
        self.spinbox.valueChanged.connect(self.value_changed.emit)
        
        self.spinbox.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 8pt;
                color: {COLORS['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QSpinBox:hover {{
                border: 1px solid {COLORS['border_focus']};
                background-color: {COLORS['surface']};
            }}
            QSpinBox:focus {{
                border: 1px solid {COLORS['primary']};
                background-color: {COLORS['background']};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 14px;
                border: none;
                background-color: transparent;
                border-radius: 2px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {COLORS['surface_hover']};
            }}
            QSpinBox::up-arrow {{
                image: none;
                border: 1px solid {COLORS['text_secondary']};
                border-bottom: none;
                border-left: none;
                width: 3px;
                height: 3px;
                transform: rotate(-45deg);
            }}
            QSpinBox::down-arrow {{
                image: none;
                border: 1px solid {COLORS['text_secondary']};
                border-top: none;
                border-right: none;
                width: 3px;
                height: 3px;
                transform: rotate(-45deg);
            }}
        """)
        
        layout.addWidget(self.spinbox)

    def value(self):
        return self.spinbox.value()

    def setValue(self, value):
        self.spinbox.setValue(value)

# Professional factory for common ribbon elements

class ProfessionalRibbonFactory:
    """Factory for creating professional ribbon components"""
    
    @staticmethod
    def create_file_menu():
        """Create professional file menu"""
        from PyQt5.QtWidgets import QAction
        menu = QMenu()
        
        # File actions with clean icons
        new_action = QAction("New", menu)
        new_action.setShortcut("Ctrl+N")
        new_action.setToolTip("Create a new document")
        menu.addAction(new_action)
        
        open_action = QAction("Open", menu)
        open_action.setShortcut("Ctrl+O")
        open_action.setToolTip("Open an existing document")
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        save_action = QAction("Save", menu)
        save_action.setShortcut("Ctrl+S")
        save_action.setToolTip("Save the current document")
        menu.addAction(save_action)
        
        save_as_action = QAction("Save As...", menu)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.setToolTip("Save document with a new name")
        menu.addAction(save_as_action)
        
        menu.addSeparator()
        
        exit_action = QAction("Exit", menu)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setToolTip("Exit the application")
        menu.addAction(exit_action)
        
        return menu

    @staticmethod
    def create_edit_group():
        """Create professional edit group"""
        from PyQt5.QtWidgets import QAction
        
        group = ProfessionalGroup("Edit")
        
        # Edit actions
        undo_action = QAction("Undo", group)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setToolTip("Undo the last action")
        
        redo_action = QAction("Redo", group)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.setToolTip("Redo the last undone action")
        
        cut_action = QAction("Cut", group)
        cut_action.setShortcut("Ctrl+X")
        cut_action.setToolTip("Cut selection to clipboard")
        
        copy_action = QAction("Copy", group)
        copy_action.setShortcut("Ctrl+C")
        copy_action.setToolTip("Copy selection to clipboard")
        
        paste_action = QAction("Paste", group)
        paste_action.setShortcut("Ctrl+V")
        paste_action.setToolTip("Paste from clipboard")
        
        # Add to group with clean layout
        group.add_vertical_group([undo_action, redo_action])
        group.add_separator()
        group.add_vertical_group([cut_action, copy_action, paste_action])
        
        return group

    @staticmethod
    def create_format_group():
        """Create professional format group"""
        from PyQt5.QtWidgets import QAction
        
        group = ProfessionalGroup("Format")
        
        # Format actions
        bold_action = QAction("Bold", group)
        bold_action.setShortcut("Ctrl+B")
        bold_action.setCheckable(True)
        bold_action.setToolTip("Make text bold")
        
        italic_action = QAction("Italic", group)
        italic_action.setShortcut("Ctrl+I")
        italic_action.setCheckable(True)
        italic_action.setToolTip("Make text italic")
        
        underline_action = QAction("Underline", group)
        underline_action.setShortcut("Ctrl+U")
        underline_action.setCheckable(True)
        underline_action.setToolTip("Underline text")
        
        # Add format controls
        group.add_vertical_group([bold_action, italic_action, underline_action])
        
        return group

    @staticmethod
    def create_view_group():
        """Create professional view group"""
        from PyQt5.QtWidgets import QAction
        
        group = ProfessionalGroup("View")
        
        # View actions
        zoom_in_action = QAction("Zoom In", group)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.setToolTip("Zoom in")
        
        zoom_out_action = QAction("Zoom Out", group)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.setToolTip("Zoom out")
        
        zoom_fit_action = QAction("Fit to Window", group)
        zoom_fit_action.setToolTip("Fit content to window")
        
        # Add view controls
        group.add_vertical_group([zoom_in_action, zoom_out_action, zoom_fit_action])
        
        return group

# Usage example for FSM Designer
def create_fsm_ribbon():
    """Create a professional ribbon for FSM Designer"""
    ribbon = ProfessionalRibbon()
    
    # Set professional file menu
    file_menu = ProfessionalRibbonFactory.create_file_menu()
    ribbon.set_file_menu(file_menu)
    
    # Home tab
    home_tab = ribbon.add_tab("Home")
    home_tab.add_group(ProfessionalRibbonFactory.create_edit_group())
    
    # States group
    states_group = ProfessionalGroup("States")
    from PyQt5.QtWidgets import QAction
    
    add_state_action = QAction("Add State", states_group)
    add_state_action.setToolTip("Add a new state to the diagram")
    
    delete_state_action = QAction("Delete", states_group)
    delete_state_action.setToolTip("Delete selected state")
    
    initial_state_action = QAction("Set Initial", states_group)
    initial_state_action.setToolTip("Set as initial state")
    
    final_state_action = QAction("Set Final", states_group)
    final_state_action.setToolTip("Set as final state")
    
    states_group.add_action_button(add_state_action, is_large=True)
    states_group.add_vertical_group([delete_state_action, initial_state_action, final_state_action])
    
    home_tab.add_group(states_group)
    
    # Transitions group
    transitions_group = ProfessionalGroup("Transitions")
    
    add_transition_action = QAction("Add Transition", transitions_group)
    add_transition_action.setToolTip("Add a new transition")
    
    edit_transition_action = QAction("Edit", transitions_group)
    edit_transition_action.setToolTip("Edit transition properties")
    
    delete_transition_action = QAction("Delete", transitions_group)
    delete_transition_action.setToolTip("Delete selected transition")
    
    transitions_group.add_action_button(add_transition_action, is_large=True)
    transitions_group.add_vertical_group([edit_transition_action, delete_transition_action])
    
    home_tab.add_group(transitions_group)
    
    # View tab
    view_tab = ribbon.add_tab("View")
    view_tab.add_group(ProfessionalRibbonFactory.create_view_group())
    
    # Zoom controls
    zoom_group = ProfessionalInputGroup("Zoom")
    zoom_combo = zoom_group.add_combo(["25%", "50%", "75%", "100%", "125%", "150%", "200%"], "100%")
    view_tab.add_group(zoom_group)
    
    # Select first tab
    ribbon.select_first_tab()
    
    return ribbon

# Export main classes
__all__ = [
    'ProfessionalRibbon',
    'ProfessionalGroup', 
    'ProfessionalInputGroup',
    'ProfessionalButton',
    'ProfessionalColorButton',
    'ProfessionalSpinBox',
    'ProfessionalRibbonFactory',
    'create_fsm_ribbon'
]