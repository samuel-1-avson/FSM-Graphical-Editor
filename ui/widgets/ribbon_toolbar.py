# fsm_designer_project/ui/widgets/ribbon_toolbar.py
# Enhanced Modern Ribbon Toolbar with improved UI/UX
# fsm_designer_project/ui/widgets/ribbon_toolbar.py

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton, 
    QLabel, QFrame, QButtonGroup, QSizePolicy, QMenu, QComboBox,
    QLineEdit, QSpacerItem, QGraphicsDropShadowEffect, QApplication
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PyQt5.QtGui import QIcon, QColor, QFont, QPainter, QPalette, QFontMetrics

from ...utils import get_standard_icon
from ...utils.config import (
    COLOR_ACCENT_PRIMARY, COLOR_BACKGROUND_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_BORDER_LIGHT, COLOR_TEXT_SECONDARY, COLOR_BACKGROUND_APP,
    COLOR_BACKGROUND_MEDIUM, COLOR_ACCENT_PRIMARY_LIGHT, COLOR_TEXT_ON_ACCENT
)

class RibbonButton(QToolButton):
    """Enhanced ribbon button with improved visual feedback and accessibility"""
    
    def __init__(self, action, is_large=True, parent=None):
        super().__init__(parent)
        self.setDefaultAction(action)
        self.is_large = is_large
        self._hover_animation = None
        self._is_hovered = False
        
        # Enhanced sizing and layout
        if is_large:
            self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            self.setIconSize(QSize(32, 32))
            self.setMinimumSize(QSize(84, 76))
            self.setMaximumSize(QSize(94, 76))
        else:
            self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            self.setIconSize(QSize(16, 16))
            self.setMinimumSize(QSize(80, 26))
            self.setMaximumHeight(26)
        
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # Add subtle drop shadow for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(3)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)
        
        # Enable tooltips for better accessibility
        if action and action.toolTip():
            self.setToolTip(action.toolTip())
        
        self.update_style()

    def update_style(self):
        """Enhanced styling with better visual hierarchy"""
        padding = "8px 6px" if self.is_large else "3px 10px"
        font_size = "8pt" if self.is_large else "8pt"
        font_weight = "500" if self.is_large else "normal"
        
        self.setStyleSheet(f"""
            RibbonButton {{
                border: 1px solid transparent;
                border-radius: 6px;
                padding: {padding};
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                font-size: {font_size};
                font-weight: {font_weight};
                text-align: center;
            }}
            RibbonButton:hover {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
                border: 1px solid {COLOR_ACCENT_PRIMARY};
                color: {COLOR_ACCENT_PRIMARY};
                font-weight: 600;
            }}
            RibbonButton:pressed {{
                background-color: {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
                color: {COLOR_TEXT_ON_ACCENT};
                border: 1px solid {QColor(COLOR_ACCENT_PRIMARY).darker(120).name()};
                padding-top: {"9px" if self.is_large else "4px"};
            }}
            RibbonButton:checked {{
                background-color: {COLOR_ACCENT_PRIMARY};
                border: 1px solid {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
                color: {COLOR_TEXT_ON_ACCENT};
                font-weight: 600;
            }}
            RibbonButton:disabled {{
                color: {COLOR_TEXT_SECONDARY};
                background-color: transparent;
                border: 1px solid transparent;
            }}
        """)

    def enterEvent(self, event):
        """Add hover effect with smooth transition"""
        super().enterEvent(event)
        self._is_hovered = True
        
    def leaveEvent(self, event):
        """Remove hover effect"""
        super().leaveEvent(event)
        self._is_hovered = False

class RibbonSplitButton(QWidget):
    """Enhanced split button with better visual separation"""
    
    def __init__(self, main_action, menu_actions, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main button
        self.main_button = QToolButton()
        self.main_button.setDefaultAction(main_action)
        self.main_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.main_button.setIconSize(QSize(32, 32))
        self.main_button.setMinimumSize(QSize(64, 76))
        
        # Dropdown button with better visual design
        self.dropdown_button = QToolButton()
        self.dropdown_button.setText("⌄")  # Better dropdown arrow
        self.dropdown_button.setMaximumWidth(18)
        self.dropdown_button.setMinimumHeight(76)
        self.dropdown_button.setPopupMode(QToolButton.InstantPopup)
        
        # Enhanced menu styling
        menu = QMenu(self)
        menu.addActions(menu_actions)
        self.dropdown_button.setMenu(menu)
        
        layout.addWidget(self.main_button)
        layout.addWidget(self.dropdown_button)
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(3)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)
        
        self.update_style()

    def update_style(self):
        """Enhanced split button styling"""
        main_button_style = f"""
            QToolButton {{
                border: 1px solid transparent;
                border-radius: 6px 0px 0px 6px;
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 8pt;
                font-weight: 500;
                padding: 6px;
            }}
            QToolButton:hover {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
                border: 1px solid {COLOR_ACCENT_PRIMARY};
                color: {COLOR_ACCENT_PRIMARY};
            }}
            QToolButton:pressed {{
                background-color: {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
                color: {COLOR_TEXT_ON_ACCENT};
            }}
        """
        
        dropdown_style = f"""
            QToolButton {{
                border: 1px solid transparent;
                border-left: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 0px 6px 6px 0px;
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 10pt;
                font-weight: bold;
                padding: 4px;
            }}
            QToolButton:hover {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
                border: 1px solid {COLOR_ACCENT_PRIMARY};
                border-left: 1px solid {COLOR_ACCENT_PRIMARY};
                color: {COLOR_ACCENT_PRIMARY};
            }}
            QToolButton:pressed {{
                background-color: {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
                color: {COLOR_TEXT_ON_ACCENT};
            }}
        """
        
        self.main_button.setStyleSheet(main_button_style)
        self.dropdown_button.setStyleSheet(dropdown_style)

class RibbonGroup(QFrame):
    """Enhanced ribbon group with better organization and visual clarity"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.title = title
        
        # Enhanced layout with better spacing
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(3)
        
        # Content area with subtle background
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border-radius: 4px;
            }}
        """)
        
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(2, 2, 2, 2)
        self.content_layout.setSpacing(4)
        
        main_layout.addWidget(self.content_widget, 1)
        
        # Enhanced title label
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        
        # Better font metrics for title
        font = QFont()
        font.setPointSize(7)
        font.setWeight(QFont.Medium)
        title_label.setFont(font)
        
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY}; 
                font-size: 7pt; 
                font-weight: 500;
                padding: 3px 2px 2px 2px;
                border-top: 1px solid {COLOR_BORDER_LIGHT};
                margin-top: 3px;
                background-color: transparent;
            }}
        """)
        main_layout.addWidget(title_label)
        
        # Enhanced dimensions
        self.setMinimumHeight(104)
        self.setMaximumHeight(104)
        self.setMinimumWidth(80)
        
        # Add subtle hover effect to the entire group
        self.setStyleSheet(f"""
            RibbonGroup {{
                border-radius: 6px;
                background-color: transparent;
            }}
            RibbonGroup:hover {{
                background-color: {QColor(COLOR_BACKGROUND_LIGHT).lighter(102).name()};
            }}
        """)

    def add_action_button(self, action, is_large=True):
        """Add an enhanced action button"""
        button = RibbonButton(action, is_large)
        self.content_layout.addWidget(button)
        return button

    def add_split_button(self, main_action, menu_actions):
        """Add an enhanced split button"""
        split_button = RibbonSplitButton(main_action, menu_actions)
        self.content_layout.addWidget(split_button)
        return split_button

    def add_widget(self, widget):
        """Add a custom widget to the group"""
        self.content_layout.addWidget(widget)

    def add_vertical_group(self, actions):
        """Add a vertical group of small buttons"""
        v_widget = QWidget()
        v_layout = QVBoxLayout(v_widget)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(3)
        
        for action in actions:
            btn = RibbonButton(action, is_large=False)
            v_layout.addWidget(btn)
        
        v_layout.addStretch()
        self.content_layout.addWidget(v_widget)
        return v_widget

    def add_separator(self):
        """Add a vertical separator with better styling"""
        separator = QFrame()
        separator.setFrameStyle(QFrame.VLine | QFrame.Plain)
        separator.setStyleSheet(f"""
            QFrame {{
                color: {COLOR_BORDER_LIGHT}; 
                background-color: {COLOR_BORDER_LIGHT};
                margin: 8px 3px;
                max-width: 1px;
            }}
        """)
        separator.setMaximumWidth(1)
        self.content_layout.addWidget(separator)

class RibbonComboGroup(QWidget):
    """Enhanced combo group with better input styling"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(4)
        layout.addLayout(self.content_layout)
        
        # Enhanced title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        
        font = QFont()
        font.setPointSize(7)
        font.setWeight(QFont.Medium)
        title_label.setFont(font)
        
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY}; 
                font-size: 7pt; 
                font-weight: 500;
                padding: 3px 2px;
                border-top: 1px solid {COLOR_BORDER_LIGHT};
                margin-top: 3px;
            }}
        """)
        layout.addWidget(title_label)
        
        self.setMinimumHeight(94)
        self.setMaximumHeight(94)

    def add_combo(self, items, current_text=None):
        """Add an enhanced combo box"""
        combo = QComboBox()
        combo.addItems(items)
        if current_text:
            combo.setCurrentText(current_text)
        
        combo.setMinimumWidth(110)
        combo.setMaximumHeight(24)
        
        # Enhanced combo box styling
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 8pt;
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
            }}
            QComboBox:hover {{
                border: 1px solid {COLOR_ACCENT_PRIMARY};
                background-color: white;
            }}
            QComboBox:focus {{
                border: 2px solid {COLOR_ACCENT_PRIMARY};
                background-color: white;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: 2px solid {COLOR_TEXT_SECONDARY};
                border-top: none;
                border-right: none;
                width: 6px;
                height: 6px;
                transform: rotate(-45deg);
            }}
        """)
        
        self.content_layout.addWidget(combo)
        return combo

    def add_line_edit(self, placeholder=""):
        """Add an enhanced line edit"""
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumWidth(110)
        edit.setMaximumHeight(24)
        
        # Enhanced line edit styling
        edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 8pt;
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
            }}
            QLineEdit:hover {{
                border: 1px solid {COLOR_ACCENT_PRIMARY};
                background-color: white;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLOR_ACCENT_PRIMARY};
                background-color: white;
            }}
            QLineEdit::placeholder {{
                color: {COLOR_TEXT_SECONDARY};
                font-style: italic;
            }}
        """)
        
        self.content_layout.addWidget(edit)
        return edit

class RibbonTab(QWidget):
    """Enhanced ribbon tab with better layout management"""
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 4, 12, 4)
        self.layout.setSpacing(8)
        self.layout.addStretch()

    def add_group(self, group):
        """Add a group with enhanced separator"""
        self.layout.insertWidget(self.layout.count() - 1, group)
        
        # Enhanced separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet(f"""
            QFrame {{
                color: {COLOR_BORDER_LIGHT}; 
                background-color: {COLOR_BORDER_LIGHT};
                margin: 12px 0px; 
                max-width: 1px;
            }}
        """)
        self.layout.insertWidget(self.layout.count() - 1, separator)

class ModernRibbon(QWidget):
    """Enhanced modern ribbon with improved UX and accessibility"""
    
    tab_changed = pyqtSignal(str)  # Signal for tab changes
    search_requested = pyqtSignal(str)  # Signal for search
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = {}
        self.current_tab_widget = None
        self.file_button = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        self.init_ui()

    def init_ui(self):
        """Initialize the enhanced UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Enhanced tab bar with gradient background
        self.tab_bar = QWidget()
        self.tab_bar.setFixedHeight(36)
        self.tab_bar.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {COLOR_BACKGROUND_MEDIUM}, 
                    stop: 0.8 {QColor(COLOR_BACKGROUND_MEDIUM).darker(105).name()},
                    stop: 1 {QColor(COLOR_BACKGROUND_MEDIUM).darker(110).name()});
                border-bottom: 2px solid {COLOR_BORDER_LIGHT};
            }}
        """)
        
        self.tab_layout = QHBoxLayout(self.tab_bar)
        self.tab_layout.setContentsMargins(0, 0, 12, 0)
        self.tab_layout.setSpacing(0)

        # Enhanced File button with modern design
        self.file_button = QToolButton()
        self.file_button.setText("File")
        self.file_button.setCheckable(True)
        self.file_button.setPopupMode(QToolButton.InstantPopup)
        self.file_button.setFixedSize(54, 32)
        
        # Add drop shadow to file button
        file_shadow = QGraphicsDropShadowEffect()
        file_shadow.setBlurRadius(4)
        file_shadow.setColor(QColor(0, 0, 0, 30))
        file_shadow.setOffset(0, 2)
        self.file_button.setGraphicsEffect(file_shadow)
        
        self.file_button.setStyleSheet(f"""
            QToolButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {COLOR_ACCENT_PRIMARY}, 
                    stop: 1 {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()});
                color: {COLOR_TEXT_ON_ACCENT};
                border: none; 
                border-radius: 0px;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                padding: 0px 12px;
                font-weight: 600;
                font-size: 9pt;
                margin: 2px 0px;
            }}
            QToolButton:hover {{ 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {QColor(COLOR_ACCENT_PRIMARY).lighter(115).name()}, 
                    stop: 1 {COLOR_ACCENT_PRIMARY});
            }}
            QToolButton:pressed, QToolButton:checked {{ 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {QColor(COLOR_ACCENT_PRIMARY).darker(115).name()}, 
                    stop: 1 {QColor(COLOR_ACCENT_PRIMARY).darker(125).name()});
            }}
        """)
        self.file_button.clicked.connect(self.on_file_button_clicked)
        self.tab_layout.addWidget(self.file_button)
        
        # Enhanced separator
        file_separator = QFrame()
        file_separator.setFrameShape(QFrame.VLine)
        file_separator.setFrameShadow(QFrame.Plain)
        file_separator.setStyleSheet(f"""
            QFrame {{
                color: {COLOR_BORDER_LIGHT};
                background-color: {COLOR_BORDER_LIGHT};
                margin: 6px 0px;
                max-width: 1px;
            }}
        """)
        self.tab_layout.addWidget(file_separator)
        self.tab_layout.addSpacing(16)

        # Enhanced tab buttons container
        self.tab_buttons_container = QWidget()
        self.tab_buttons_layout = QHBoxLayout(self.tab_buttons_container)
        self.tab_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_buttons_layout.setSpacing(2)
        self.tab_layout.addWidget(self.tab_buttons_container)

        self.tab_button_group = QButtonGroup(self)
        self.tab_button_group.setExclusive(True)
        self.tab_button_group.buttonClicked.connect(self.on_tab_clicked)

        # Enhanced search area
        self.tab_layout.addStretch()
        
        # Search container with icon
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(12)
        
        # Search separator
        search_separator = QFrame()
        search_separator.setFrameShape(QFrame.VLine)
        search_separator.setFrameShadow(QFrame.Plain)
        search_separator.setStyleSheet(f"""
            QFrame {{
                color: {COLOR_BORDER_LIGHT};
                background-color: {COLOR_BORDER_LIGHT};
                margin: 8px 0px;
                max-width: 1px;
            }}
        """)
        search_layout.addWidget(search_separator)
        
        # Enhanced search bar with icon
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search commands...")
        self.search_bar.setFixedSize(160, 24)
        self.search_bar.textChanged.connect(self.on_search_text_changed)
        
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 12px;
                padding: 0px 16px;
                font-size: 8pt;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QLineEdit:hover {{
                border: 1px solid {COLOR_ACCENT_PRIMARY};
                background-color: white;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLOR_ACCENT_PRIMARY};
                background-color: white;
                padding: 0px 15px;
            }}
            QLineEdit::placeholder {{
                color: {COLOR_TEXT_SECONDARY};
            }}
        """)
        search_layout.addWidget(self.search_bar)
        
        self.tab_layout.addWidget(search_container)

        main_layout.addWidget(self.tab_bar)

        # Enhanced content area with subtle effects
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setFixedHeight(108)
        
        # Add subtle inner shadow effect
        content_shadow = QGraphicsDropShadowEffect()
        content_shadow.setBlurRadius(8)
        content_shadow.setColor(QColor(0, 0, 0, 15))
        content_shadow.setOffset(0, -2)
        self.content_area.setGraphicsEffect(content_shadow)
        
        self.content_area.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {COLOR_BACKGROUND_LIGHT}, 
                    stop: 0.05 {QColor(COLOR_BACKGROUND_LIGHT).darker(102).name()},
                    stop: 1 {COLOR_BACKGROUND_LIGHT});
                border-bottom: 2px solid {COLOR_BORDER_LIGHT};
            }}
        """)
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content_area)

    def create_tab_button(self, text):
        """Create an enhanced tab button"""
        button = QPushButton(text)
        button.setCheckable(True)
        button.setFixedHeight(32)
        
        # Better width calculation based on text
        font_metrics = QFontMetrics(button.font())
        text_width = font_metrics.horizontalAdvance(text)
        button.setMinimumWidth(text_width + 32)
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border: 1px solid transparent; 
                border-bottom: none;
                padding: 4px 20px; 
                color: {COLOR_TEXT_PRIMARY}; 
                font-weight: 400;
                font-size: 8pt;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-top: 2px;
            }}
            QPushButton:hover {{ 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {COLOR_ACCENT_PRIMARY_LIGHT}, 
                    stop: 1 {QColor(COLOR_ACCENT_PRIMARY_LIGHT).darker(105).name()});
                border-top: 1px solid {COLOR_BORDER_LIGHT};
                border-left: 1px solid {COLOR_BORDER_LIGHT};
                border-right: 1px solid {COLOR_BORDER_LIGHT};
                color: {COLOR_ACCENT_PRIMARY};
                font-weight: 500;
            }}
            QPushButton:checked {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {COLOR_BACKGROUND_LIGHT}, 
                    stop: 1 {QColor(COLOR_BACKGROUND_LIGHT).darker(102).name()});
                border-top: 3px solid {COLOR_ACCENT_PRIMARY};
                border-left: 1px solid {COLOR_BORDER_LIGHT};
                border-right: 1px solid {COLOR_BORDER_LIGHT};
                border-bottom: 1px solid {COLOR_BACKGROUND_LIGHT};
                font-weight: 600;
                color: {COLOR_ACCENT_PRIMARY};
                margin-top: 0px;
            }}
        """)
        return button

    def add_tab(self, name):
        """Add a new tab with enhanced features"""
        tab_widget = RibbonTab(name, self)
        button = self.create_tab_button(name)
        
        # Add tooltip for accessibility
        button.setToolTip(f"Switch to {name} tab")
        
        self.tab_button_group.addButton(button)
        self.tab_buttons_layout.addWidget(button)
        self.tabs[button] = tab_widget
        return tab_widget

    def on_file_button_clicked(self):
        """Handle file button click with animation"""
        if btn := self.tab_button_group.checkedButton():
            self.tab_button_group.setExclusive(False)
            btn.setChecked(False)
            self.tab_button_group.setExclusive(True)
        
        if self.current_tab_widget:
            self.current_tab_widget.hide()
            self.current_tab_widget = None

    def on_tab_clicked(self, button):
        """Handle tab click with enhanced feedback"""
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
            
            # Add new tab content with smooth transition
            self.content_layout.addWidget(self.current_tab_widget)
            self.current_tab_widget.show()
            
            # Emit signal for tab change
            self.tab_changed.emit(self.current_tab_widget.name)

    def on_search_text_changed(self, text):
        """Handle search text changes with debouncing"""
        self.search_timer.stop()
        if text.strip():
            self.search_timer.start(300)  # 300ms delay for better UX

    def _perform_search(self):
        """Perform the actual search"""
        search_text = self.search_bar.text().strip()
        if search_text:
            self.search_requested.emit(search_text)

    def set_file_menu(self, menu: QMenu):
        """Set file menu with enhanced styling"""
        self.file_button.setMenu(menu)
        
        # Enhanced menu styling with modern design
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 2px solid {COLOR_BORDER_LIGHT};
                border-radius: 8px;
                padding: 6px 0px;
            }}
            QMenu::item {{
                padding: 8px 24px 8px 36px;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 9pt;
                border-radius: 4px;
                margin: 2px 6px;
            }}
            QMenu::item:selected {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
                color: {COLOR_ACCENT_PRIMARY};
                font-weight: 500;
            }}
            QMenu::item:disabled {{
                color: {COLOR_TEXT_SECONDARY};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {COLOR_BORDER_LIGHT};
                margin: 6px 12px;
            }}
            QMenu::icon {{
                padding-left: 8px;
            }}
        """)
        
        menu.aboutToHide.connect(lambda: self.file_button.setChecked(False))

    def select_first_tab(self):
        """Select the first tab with animation"""
        if self.tab_button_group.buttons():
            first_button = self.tab_button_group.buttons()[0]
            first_button.click()

    def set_search_placeholder(self, text):
        """Set custom search placeholder text"""
        self.search_bar.setPlaceholderText(f"🔍 {text}")

    def clear_search(self):
        """Clear the search bar"""
        self.search_bar.clear()

    def get_current_tab_name(self):
        """Get the name of the currently active tab"""
        if self.current_tab_widget:
            return self.current_tab_widget.name
        return None

    def set_tab_enabled(self, tab_name, enabled):
        """Enable or disable a specific tab"""
        for button, tab_widget in self.tabs.items():
            if tab_widget.name == tab_name:
                button.setEnabled(enabled)
                if not enabled and button.isChecked():
                    # Switch to first available tab if current is disabled
                    self.select_first_tab()
                break

    def add_quick_access_button(self, action):
        """Add a quick access button to the tab bar"""
        quick_button = QToolButton()
        quick_button.setDefaultAction(action)
        quick_button.setIconSize(QSize(16, 16))
        quick_button.setFixedSize(28, 28)
        quick_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        
        quick_button.setStyleSheet(f"""
            QToolButton {{
                border: 1px solid transparent;
                border-radius: 4px;
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                margin: 2px;
            }}
            QToolButton:hover {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
                border: 1px solid {COLOR_ACCENT_PRIMARY};
            }}
            QToolButton:pressed {{
                background-color: {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
                color: {COLOR_TEXT_ON_ACCENT};
            }}
        """)
        
        # Insert before search area
        self.tab_layout.insertWidget(self.tab_layout.count() - 1, quick_button)
        return quick_button

    def set_compact_mode(self, compact=True):
        """Toggle compact mode for smaller screens"""
        if compact:
            self.tab_bar.setFixedHeight(30)
            self.content_area.setFixedHeight(88)
            # Update button sizes and fonts for compact mode
            for button in self.tab_button_group.buttons():
                button.setFixedHeight(26)
        else:
            self.tab_bar.setFixedHeight(36)
            self.content_area.setFixedHeight(108)
            # Restore normal sizes
            for button in self.tab_button_group.buttons():
                button.setFixedHeight(32)

# Additional utility classes for enhanced functionality

class RibbonColorButton(QToolButton):
    """Special color picker button for ribbon"""
    
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, color=Qt.black, parent=None):
        super().__init__(parent)
        self.current_color = QColor(color)
        self.setFixedSize(32, 32)
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.clicked.connect(self.show_color_dialog)
        self.update_color_display()

    def update_color_display(self):
        """Update the button to show current color"""
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {self.current_color.name()};
                border: 2px solid {COLOR_BORDER_LIGHT};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                border: 2px solid {COLOR_ACCENT_PRIMARY};
            }}
            QToolButton:pressed {{
                border: 2px solid {QColor(COLOR_ACCENT_PRIMARY).darker(120).name()};
            }}
        """)

    def show_color_dialog(self):
        """Show color picker dialog"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            self.update_color_display()
            self.color_changed.emit(color)

    def set_color(self, color):
        """Set the current color programmatically"""
        self.current_color = QColor(color)
        self.update_color_display()

class RibbonSpinBox(QWidget):
    """Enhanced spin box for ribbon interface"""
    
    value_changed = pyqtSignal(int)
    
    def __init__(self, minimum=0, maximum=100, value=0, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 24)
        
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
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 8pt;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QSpinBox:hover {{
                border: 1px solid {COLOR_ACCENT_PRIMARY};
                background-color: white;
            }}
            QSpinBox:focus {{
                border: 2px solid {COLOR_ACCENT_PRIMARY};
                background-color: white;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 16px;
                border: none;
                background-color: transparent;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
            }}
            QSpinBox::up-arrow {{
                image: none;
                border: 2px solid {COLOR_TEXT_SECONDARY};
                border-bottom: none;
                border-left: none;
                width: 4px;
                height: 4px;
                transform: rotate(-45deg);
            }}
            QSpinBox::down-arrow {{
                image: none;
                border: 2px solid {COLOR_TEXT_SECONDARY};
                border-top: none;
                border-right: none;
                width: 4px;
                height: 4px;
                transform: rotate(-45deg);
            }}
        """)
        
        layout.addWidget(self.spinbox)

    def value(self):
        return self.spinbox.value()

    def setValue(self, value):
        self.spinbox.setValue(value)

# Example usage and factory functions
class RibbonFactory:
    """Factory class for creating common ribbon elements"""
    
    @staticmethod
    def create_standard_file_menu():
        """Create a standard file menu"""
        from PyQt5.QtWidgets import QAction
        menu = QMenu()
        
        # Standard file actions
        new_action = QAction("New", menu)
        new_action.setShortcut("Ctrl+N")
        menu.addAction(new_action)
        
        open_action = QAction("Open", menu)
        open_action.setShortcut("Ctrl+O")
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        save_action = QAction("Save", menu)
        save_action.setShortcut("Ctrl+S")
        menu.addAction(save_action)
        
        save_as_action = QAction("Save As...", menu)
        save_as_action.setShortcut("Ctrl+Shift+S")
        menu.addAction(save_as_action)
        
        menu.addSeparator()
        
        exit_action = QAction("Exit", menu)
        exit_action.setShortcut("Ctrl+Q")
        menu.addAction(exit_action)
        
        return menu

    @staticmethod
    def create_edit_group():
        """Create a standard edit group"""
        from PyQt5.QtWidgets import QAction
        
        group = RibbonGroup("Edit")
        
        # Create standard edit actions
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
        
        # Add buttons to group
        group.add_vertical_group([undo_action, redo_action])
        group.add_separator()
        group.add_vertical_group([cut_action, copy_action, paste_action])
        
        return group