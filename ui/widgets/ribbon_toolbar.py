# fsm_designer_project/ui/widgets/ribbon_toolbar.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton,
    QLabel, QFrame, QButtonGroup, QSizePolicy, QMenu, QComboBox,
    QLineEdit, QSpacerItem, QGraphicsDropShadowEffect, QApplication,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, QParallelAnimationGroup, QAbstractAnimation
from PyQt6.QtGui import QIcon, QColor, QFont, QPainter, QPalette, QFontMetrics, QPixmap, QPainterPath, QAction

from ...utils import get_standard_icon



class ProfessionalButton(QToolButton):
    """Enhanced professional button with animations and better UX"""
    
    def __init__(self, action, is_large=True, parent=None):
        super().__init__(parent)
        self.setDefaultAction(action)
        self.is_large = is_large
        self._setup_button()
        self._setup_animations()

    def _setup_button(self):
        """Configure button properties with professional styling"""
        if self.is_large:
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            self.setIconSize(QSize(32, 32))  # Larger, clearer icons
            self.setMinimumSize(QSize(80, 76))
            self.setMaximumSize(QSize(90, 76))
        else:
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.setIconSize(QSize(16, 16))
            self.setMinimumSize(QSize(80, 26))
            self.setMaximumHeight(26)
        
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        # Enhanced tooltips
        if hasattr(self.defaultAction(), 'toolTip') and self.defaultAction().toolTip():
            self.setToolTip(self.defaultAction().toolTip())
        
        # Professional cursor
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_animations(self):
        """Setup hover animations"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        """Enhanced hover effect"""
        super().enterEvent(event)
        self.animation.stop()
        self.animation.setStartValue(self.opacity_effect.opacity())
        self.animation.setEndValue(0.8)
        self.animation.start()

    def leaveEvent(self, event):
        """Enhanced leave effect"""
        super().leaveEvent(event)
        self.animation.stop()
        self.animation.setStartValue(self.opacity_effect.opacity())
        self.animation.setEndValue(1.0)
        self.animation.start()

class ProfessionalSplitButton(QWidget):
    """Enhanced split button with modern styling"""
    
    def __init__(self, main_action, menu_actions, parent=None):
        super().__init__(parent)
        self._setup_layout()
        self._create_buttons(main_action, menu_actions)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_layout(self):
        """Setup the layout with proper spacing"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def _create_buttons(self, main_action, menu_actions):
        """Create enhanced main and dropdown buttons"""
        # Main button with better styling
        self.main_button = QToolButton()
        self.main_button.setDefaultAction(main_action)
        self.main_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.main_button.setIconSize(QSize(32, 32))
        self.main_button.setMinimumSize(QSize(64, 76))
        self.main_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Modern dropdown button
        self.dropdown_button = QToolButton()
        self.dropdown_button.setText("⌄")  # Better dropdown arrow
        self.dropdown_button.setMaximumWidth(18)
        self.dropdown_button.setMinimumHeight(76)
        self.dropdown_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.dropdown_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Enhanced menu styling
        menu = QMenu(self)
        menu.addActions(menu_actions)
        self.dropdown_button.setMenu(menu)
        
        # Add subtle visual separation
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Plain)
        separator.setMaximumWidth(1)
        separator.setStyleSheet("color: #dee2e6; margin: 8px 0px;")
        
        self.layout().addWidget(self.main_button)
        self.layout().addWidget(separator)
        self.layout().addWidget(self.dropdown_button)

class ProfessionalGroup(QFrame):
    """Enhanced ribbon group with modern design and spacing"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("RibbonGroup")
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.title = title
        self._setup_layout()
        self._apply_professional_styling()

    def _setup_layout(self):
        """Setup the group layout with better spacing"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(4)
        
        # Content area with proper margins
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(4)
        
        main_layout.addWidget(self.content_widget, 1)
        
        # Professional title with better typography
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        
        # Enhanced typography
        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        title_label.setFont(font)
        title_label.setStyleSheet("""
            color: #6c757d;
            background: transparent;
            padding: 4px 0px;
            border: none;
        """)
        
        main_layout.addWidget(title_label)

    def _apply_professional_styling(self):
        """Apply enhanced professional styling"""
        self.setMinimumHeight(104)
        self.setMaximumHeight(104)
        self.setMinimumWidth(70)
        
        # Subtle group styling
        self.setStyleSheet("""
            ProfessionalGroup {
                background: transparent;
                border-radius: 6px;
                margin: 2px;
            }
            ProfessionalGroup:hover {
                background: rgba(0, 123, 255, 0.02);
            }
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
        """Add vertical group of buttons with better spacing"""
        v_widget = QWidget()
        v_layout = QVBoxLayout(v_widget)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)
        
        for action in actions:
            btn = ProfessionalButton(action, is_large=False)
            v_layout.addWidget(btn)
        
        v_layout.addStretch()
        self.content_layout.addWidget(v_widget)
        return v_widget

    def add_separator(self):
        """Add a modern vertical separator"""
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Plain)
        separator.setObjectName("RibbonSeparator")
        separator.setMaximumWidth(1)
        separator.setContentsMargins(0, 10, 0, 10)
        separator.setStyleSheet("""
            #RibbonSeparator {
                color: #e9ecef;
                background: #e9ecef;
                border: none;
                margin: 10px 6px;
            }
        """)
        self.content_layout.addWidget(separator)

class ProfessionalInputGroup(QWidget):
    """Enhanced input controls group with modern styling"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._setup_layout(title)
        self._apply_professional_styling()

    def _setup_layout(self, title):
        """Setup the input group layout with better spacing"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(4)
        layout.addLayout(self.content_layout)
        
        # Professional title with enhanced typography
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        
        font = QFont("Segoe UI", 9, QFont.Weight.Medium)
        title_label.setFont(font)
        title_label.setStyleSheet("""
            color: #6c757d;
            background: transparent;
            padding: 4px 0px;
            border: none;
        """)
        
        layout.addWidget(title_label)

    def _apply_professional_styling(self):
        """Apply enhanced professional styling"""
        self.setMinimumHeight(94)
        self.setMaximumHeight(94)
        self.setMinimumWidth(120)

    def add_combo(self, items, current_text=None):
        """Add a professional combo box with enhanced styling"""
        combo = QComboBox()
        combo.addItems(items)
        if current_text:
            combo.setCurrentText(current_text)
        
        combo.setMinimumWidth(110)
        combo.setMaximumHeight(26)
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Enhanced styling
        combo.setStyleSheet("""
            QComboBox {
                background: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                color: #495057;
                selection-background-color: #007bff;
            }
            QComboBox:hover {
                border: 1px solid #007bff;
            }
            QComboBox:focus {
                border: 2px solid #007bff;
                outline: none;
            }
        """)
        
        self.content_layout.addWidget(combo)
        return combo

    def add_line_edit(self, placeholder=""):
        """Add a professional line edit with enhanced styling"""
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumWidth(110)
        edit.setMaximumHeight(26)
        
        # Enhanced styling
        edit.setStyleSheet("""
            QLineEdit {
                background: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                color: #495057;
                selection-background-color: #007bff;
            }
            QLineEdit:hover {
                border: 1px solid #007bff;
            }
            QLineEdit:focus {
                border: 2px solid #007bff;
                outline: none;
            }
        """)
        
        self.content_layout.addWidget(edit)
        return edit

class ProfessionalTab(QWidget):
    """Enhanced tab with modern layout and animations"""
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 8, 12, 8)
        self.layout.setSpacing(8)
        self.layout.addStretch()
        
        # Add fade-in animation
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def add_group(self, group):
        """Add a group with professional separator"""
        self.layout.insertWidget(self.layout.count() - 1, group)
        
        # Modern separator with better styling
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Plain)
        separator.setObjectName("RibbonSeparator")
        separator.setMaximumWidth(1)
        separator.setContentsMargins(0, 10, 0, 10)
        separator.setStyleSheet("""
            #RibbonSeparator {
                color: #e9ecef;
                background: #e9ecef;
                border: none;
                margin: 10px 6px;
            }
        """)
        self.layout.insertWidget(self.layout.count() - 1, separator)

    def show_animated(self):
        """Show tab with fade animation"""
        self.show()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

class ProfessionalRibbon(QWidget):
    """Enhanced professional ribbon with modern design and better UX"""
    
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
        """Initialize the enhanced professional UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Enhanced tab bar
        self._create_enhanced_tab_bar()
        main_layout.addWidget(self.tab_bar)

        # Modern content area
        self._create_enhanced_content_area()
        main_layout.addWidget(self.content_area)

    def _create_enhanced_tab_bar(self):
        """Create enhanced professional tab bar"""
        self.tab_bar = QWidget()
        self.tab_bar.setFixedHeight(36)
        self.tab_bar.setObjectName("RibbonTabBar")

        self.tab_layout = QHBoxLayout(self.tab_bar)
        self.tab_layout.setContentsMargins(8, 4, 8, 0)
        self.tab_layout.setSpacing(2)

        # Enhanced File button
        self._create_enhanced_file_button()
        
        # Tab buttons container
        self._create_enhanced_tab_container()
        
        # Professional search with icon
        self._create_enhanced_search_area()

    def _create_enhanced_file_button(self):
        """Create enhanced professional file button"""
        self.file_button = QToolButton()
        self.file_button.setText("File")
        self.file_button.setCheckable(True)
        self.file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.file_button.setObjectName("FileButton")
        self.file_button.setFixedSize(52, 30)
        self.file_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_button.clicked.connect(self._on_file_button_clicked)
        
        # Enhanced tooltip
        self.file_button.setToolTip("File operations (Ctrl+Alt+F)")
        
        self.tab_layout.addWidget(self.file_button)

    def _create_enhanced_tab_container(self):
        """Create enhanced tab buttons container"""
        self.tab_buttons_container = QWidget()
        self.tab_buttons_layout = QHBoxLayout(self.tab_buttons_container)
        self.tab_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_buttons_layout.setSpacing(1)
        self.tab_layout.addWidget(self.tab_buttons_container)

        self.tab_button_group = QButtonGroup(self)
        self.tab_button_group.setExclusive(True)
        self.tab_button_group.buttonClicked.connect(self._on_tab_clicked)

    def _create_enhanced_search_area(self):
        """Create enhanced professional search area"""
        self.tab_layout.addStretch()
        
        # Search container for better positioning
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        
        # Enhanced search input
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search commands...")
        self.search_bar.setObjectName("RibbonSearchBar")
        self.search_bar.setFixedSize(220, 28)
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        self.search_bar.setToolTip("Search for commands and features (Ctrl+K)")
        
        search_layout.addWidget(self.search_bar)
        
        self.tab_layout.addWidget(search_container)

    def _create_enhanced_content_area(self):
        """Create enhanced content area"""
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_area.setObjectName("RibbonContentArea")
        self.content_area.setFixedHeight(108)
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

    def add_tab(self, name):
        """Add a new professional tab with animations"""
        tab_widget = ProfessionalTab(name, self)
        button = QPushButton(name)
        button.setCheckable(True)
        button.setObjectName("RibbonTabButton")
        button.setFixedHeight(30)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Calculate optimal width based on text
        font_metrics = QFontMetrics(button.font())
        text_width = font_metrics.horizontalAdvance(name)
        button.setMinimumWidth(text_width + 32)
        
        # Enhanced tooltip
        button.setToolTip(f"Switch to {name} tab")
        
        self.tab_button_group.addButton(button)
        self.tab_buttons_layout.addWidget(button)
        self.tabs[button] = tab_widget
        return tab_widget

    def _on_file_button_clicked(self):
        """Handle enhanced file button click"""
        if btn := self.tab_button_group.checkedButton():
            self.tab_button_group.setExclusive(False)
            btn.setChecked(False)
            self.tab_button_group.setExclusive(True)
        
        if self.current_tab_widget:
            self.current_tab_widget.hide()
            self.current_tab_widget = None

    def _on_tab_clicked(self, button):
        """Handle enhanced tab click with animations"""
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
            
            # Add new tab content with animation
            self.content_layout.addWidget(self.current_tab_widget)
            self.current_tab_widget.show_animated()
            
            self.tab_changed.emit(self.current_tab_widget.name)

    def _on_search_text_changed(self, text):
        """Handle search with enhanced debouncing"""
        self.search_timer.stop()
        if text.strip():
            self.search_timer.start(300)

    def _perform_search(self):
        """Perform enhanced search"""
        search_text = self.search_bar.text().strip()
        if search_text:
            self.search_requested.emit(search_text)

    def set_file_menu(self, menu: QMenu):
        """Set enhanced professional file menu"""
        self.file_button.setMenu(menu)
        
        # Enhanced menu styling is now part of the global theme
        
        menu.aboutToHide.connect(lambda: self.file_button.setChecked(False))

    def select_first_tab(self):
        """Select the first tab with animation"""
        if self.tab_button_group.buttons():
            first_button = self.tab_button_group.buttons()[0]
            first_button.click()

    def set_search_placeholder(self, text):
        """Set enhanced search placeholder"""
        self.search_bar.setPlaceholderText(text)

    def clear_search(self):
        """Clear search with animation"""
        self.search_bar.clear()

    def get_current_tab_name(self):
        """Get current tab name"""
        if self.current_tab_widget:
            return self.current_tab_widget.name
        return None

    def set_tab_enabled(self, tab_name, enabled):
        """Enable/disable a specific tab with visual feedback"""
        for button, tab_widget in self.tabs.items():
            if tab_widget.name == tab_name:
                button.setEnabled(enabled)
                if not enabled and button.isChecked():
                    self.select_first_tab()
                break

    def add_quick_access_button(self, action):
        """Add enhanced quick access button to tab bar"""
        quick_button = QToolButton()
        quick_button.setDefaultAction(action)
        quick_button.setIconSize(QSize(18, 18))
        quick_button.setFixedSize(28, 28)
        quick_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        quick_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Enhanced styling for quick access
        quick_button.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                margin: 2px;
            }
            QToolButton:hover {
                background: rgba(0, 123, 255, 0.1);
                border: 1px solid rgba(0, 123, 255, 0.2);
            }
            QToolButton:pressed {
                background: rgba(0, 123, 255, 0.2);
            }
        """)
        
        # Insert before search area
        self.tab_layout.insertWidget(self.tab_layout.count() - 1, quick_button)
        return quick_button

    def set_compact_mode(self, compact=True):
        """Toggle enhanced compact mode for responsive design"""
        if compact:
            self.tab_bar.setFixedHeight(30)
            self.content_area.setFixedHeight(88)
            # Update button sizes for compact mode
            for button in self.tab_button_group.buttons():
                button.setFixedHeight(26)
            self.file_button.setFixedSize(46, 26)
        else:
            self.tab_bar.setFixedHeight(36)
            self.content_area.setFixedHeight(108)
            # Restore normal sizes
            for button in self.tab_button_group.buttons():
                button.setFixedHeight(30)
            self.file_button.setFixedSize(52, 30)

    def set_theme(self, theme="light"):
        """Set professional theme (light/dark)"""
        if theme == "dark":
            dark_stylesheet = """
            /* Dark theme specifics would go here */
            """
            self.setStyleSheet(dark_stylesheet)
        else:
            self.setStyleSheet("") # Revert to default/global stylesheet

# Enhanced Professional utility components

class ProfessionalColorButton(QToolButton):
    """Enhanced color picker button with modern design"""
    
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, color=Qt.GlobalColor.black, parent=None):
        super().__init__(parent)
        self.current_color = QColor(color)
        self.setFixedSize(28, 28)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._show_color_dialog)
        self._update_color_display()
        
        # Enhanced styling
        self.setStyleSheet("""
            QToolButton {
                border: 2px solid #ced4da;
                border-radius: 4px;
                margin: 1px;
            }
            QToolButton:hover {
                border: 2px solid #007bff;
            }
            QToolButton:pressed {
                border: 2px solid #0056b3;
            }
        """)

    def _update_color_display(self):
        """Update button color display with better visual"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(self.current_color)
        
        # Add border for better visibility
        painter = QPainter(pixmap)
        painter.setPen(QColor("#dee2e6"))
        painter.drawRect(0, 0, 23, 23)
        painter.end()
        
        self.setIcon(QIcon(pixmap))
        self.setToolTip(f"Color: {self.current_color.name()}")

    def _show_color_dialog(self):
        """Show enhanced color picker"""
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.current_color, self, "Choose Color")
        if color.isValid():
            self.current_color = color
            self._update_color_display()
            self.color_changed.emit(color)

    def set_color(self, color):
        """Set color programmatically"""
        self.current_color = QColor(color)
        self._update_color_display()

class ProfessionalSpinBox(QWidget):
    """Enhanced professional spin box component"""
    
    value_changed = pyqtSignal(int)
    
    def __init__(self, minimum=0, maximum=100, value=0, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 26)
        self._setup_enhanced_spinbox(minimum, maximum, value)

    def _setup_enhanced_spinbox(self, minimum, maximum, value):
        """Setup the enhanced spin box"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        from PyQt6.QtWidgets import QSpinBox
        self.spinbox = QSpinBox()
        self.spinbox.setRange(minimum, maximum)
        self.spinbox.setValue(value)
        self.spinbox.valueChanged.connect(self.value_changed.emit)
        
        # Enhanced styling
        self.spinbox.setStyleSheet("""
            QSpinBox {
                background: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 11px;
                color: #495057;
            }
            QSpinBox:hover {
                border: 1px solid #007bff;
            }
            QSpinBox:focus {
                border: 2px solid #007bff;
                outline: none;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #f8f9fa;
                border: 1px solid #ced4da;
                width: 16px;
                border-radius: 2px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #e9ecef;
            }
        """)
        
        layout.addWidget(self.spinbox)

    def value(self):
        return self.spinbox.value()

    def setValue(self, value):
        self.spinbox.setValue(value)

# Enhanced Professional factory for common ribbon elements

class ProfessionalRibbonFactory:
    """Enhanced factory for creating professional ribbon components"""
    
    @staticmethod
    def create_enhanced_file_menu():
        """Create enhanced professional file menu"""
        from PyQt6.QtGui import QKeySequence
        menu = QMenu()
        
        # File actions with better organization
        new_action = QAction("🗋  New", menu)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.setToolTip("Create a new document (Ctrl+N)")
        menu.addAction(new_action)
        
        open_action = QAction("📁  Open", menu)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setToolTip("Open an existing document (Ctrl+O)")
        menu.addAction(open_action)
        
        # Recent files submenu
        recent_menu = menu.addMenu("📄  Recent Files")
        recent_menu.setToolTip("Recently opened files")
        
        menu.addSeparator()
        
        save_action = QAction("💾  Save", menu)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setToolTip("Save the current document (Ctrl+S)")
        menu.addAction(save_action)
        
        save_as_action = QAction("💾  Save As...", menu)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.setToolTip("Save document with a new name (Ctrl+Shift+S)")
        menu.addAction(save_as_action)
        
        menu.addSeparator()
        
        # Export submenu
        export_menu = menu.addMenu("📤  Export")
        export_menu.setToolTip("Export to different formats")
        
        menu.addSeparator()
        
        preferences_action = QAction("⚙️  Preferences", menu)
        preferences_action.setToolTip("Application preferences and settings")
        menu.addAction(preferences_action)
        
        menu.addSeparator()
        
        exit_action = QAction("🚪  Exit", menu)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setToolTip("Exit the application (Ctrl+Q)")
        menu.addAction(exit_action)
        
        return menu

    @staticmethod
    def create_enhanced_edit_group():
        """Create enhanced professional edit group"""
        from PyQt6.QtGui import QKeySequence
        
        group = ProfessionalGroup("Edit")
        
        # Edit actions with better icons and tooltips
        undo_action = QAction("↶  Undo", group)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setToolTip("Undo the last action (Ctrl+Z)")
        
        redo_action = QAction("↷  Redo", group)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setToolTip("Redo the last undone action (Ctrl+Y)")
        
        cut_action = QAction("✂️  Cut", group)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.setToolTip("Cut selection to clipboard (Ctrl+X)")
        
        copy_action = QAction("📋  Copy", group)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setToolTip("Copy selection to clipboard (Ctrl+C)")
        
        paste_action = QAction("📄  Paste", group)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.setToolTip("Paste from clipboard (Ctrl+V)")
        
        # Add to group with professional layout
        group.add_vertical_group([undo_action, redo_action])
        group.add_separator()
        group.add_vertical_group([cut_action, copy_action, paste_action])
        
        return group

    @staticmethod
    def create_enhanced_format_group():
        """Create enhanced professional format group"""
        from PyQt6.QtGui import QKeySequence
        
        group = ProfessionalGroup("Format")
        
        # Format actions with better visual indicators
        bold_action = QAction("𝐁  Bold", group)
        bold_action.setShortcut(QKeySequence.StandardKey.Bold)
        bold_action.setCheckable(True)
        bold_action.setToolTip("Make text bold (Ctrl+B)")
        
        italic_action = QAction("𝐼  Italic", group)
        italic_action.setShortcut(QKeySequence.StandardKey.Italic)
        italic_action.setCheckable(True)
        italic_action.setToolTip("Make text italic (Ctrl+I)")
        
        underline_action = QAction("U̲  Underline", group)
        underline_action.setShortcut(QKeySequence.StandardKey.Underline)
        underline_action.setCheckable(True)
        underline_action.setToolTip("Underline text (Ctrl+U)")
        
        # Add format controls with better spacing
        group.add_vertical_group([bold_action, italic_action, underline_action])
        
        return group

    @staticmethod
    def create_enhanced_view_group():
        """Create enhanced professional view group"""
        from PyQt6.QtGui import QAction
        
        group = ProfessionalGroup("View")
        
        # View actions with modern icons
        zoom_in_action = QAction("🔍+  Zoom In", group)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.setToolTip("Zoom in (Ctrl++)")
        
        zoom_out_action = QAction("🔍-  Zoom Out", group)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.setToolTip("Zoom out (Ctrl+-)")
        
        zoom_fit_action = QAction("⊞  Fit Window", group)
        zoom_fit_action.setShortcut("Ctrl+0")
        zoom_fit_action.setToolTip("Fit content to window (Ctrl+0)")
        
        fullscreen_action = QAction("⛶  Fullscreen", group)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setToolTip("Toggle fullscreen mode (F11)")
        
        # Add view controls
        group.add_vertical_group([zoom_in_action, zoom_out_action, zoom_fit_action, fullscreen_action])
        
        return group

# Enhanced usage example for FSM Designer
def create_enhanced_fsm_ribbon():
    """Create an enhanced professional ribbon for FSM Designer"""
    ribbon = ProfessionalRibbon()
    
    # Set enhanced professional file menu
    file_menu = ProfessionalRibbonFactory.create_enhanced_file_menu()
    ribbon.set_file_menu(file_menu)
    
    # Home tab with enhanced controls
    home_tab = ribbon.add_tab("Home")
    home_tab.add_group(ProfessionalRibbonFactory.create_enhanced_edit_group())
    
    # Enhanced States group
    states_group = ProfessionalGroup("States")
    from PyQt6.QtGui import QAction
    
    add_state_action = QAction("➕  Add State", states_group)
    add_state_action.setToolTip("Add a new state to the diagram (Ctrl+Shift+S)")
    add_state_action.setShortcut("Ctrl+Shift+S")
    
    delete_state_action = QAction("🗑️  Delete", states_group)
    delete_state_action.setToolTip("Delete selected state (Delete)")
    delete_state_action.setShortcut("Delete")
    
    initial_state_action = QAction("🏁  Set Initial", states_group)
    initial_state_action.setToolTip("Set as initial state (Ctrl+I)")
    initial_state_action.setShortcut("Ctrl+I")
    
    final_state_action = QAction("🎯  Set Final", states_group)
    final_state_action.setToolTip("Set as final state (Ctrl+F)")
    final_state_action.setShortcut("Ctrl+F")
    
    states_group.add_action_button(add_state_action, is_large=True)
    states_group.add_vertical_group([delete_state_action, initial_state_action, final_state_action])
    
    home_tab.add_group(states_group)
    
    # Enhanced Transitions group
    transitions_group = ProfessionalGroup("Transitions")
    
    add_transition_action = QAction("🔗  Add Transition", transitions_group)
    add_transition_action.setToolTip("Add a new transition between states (Ctrl+T)")
    add_transition_action.setShortcut("Ctrl+T")
    
    edit_transition_action = QAction("✏️  Edit", transitions_group)
    edit_transition_action.setToolTip("Edit transition properties (F2)")
    edit_transition_action.setShortcut("F2")
    
    delete_transition_action = QAction("❌  Delete", transitions_group)
    delete_transition_action.setToolTip("Delete selected transition (Ctrl+Delete)")
    delete_transition_action.setShortcut("Ctrl+Delete")
    
    transitions_group.add_action_button(add_transition_action, is_large=True)
    transitions_group.add_vertical_group([edit_transition_action, delete_transition_action])
    
    home_tab.add_group(transitions_group)
    
    # Enhanced Tools group
    tools_group = ProfessionalGroup("Tools")
    
    validate_action = QAction("✅  Validate", tools_group)
    validate_action.setToolTip("Validate FSM structure (F5)")
    validate_action.setShortcut("F5")
    
    simulate_action = QAction("▶️  Simulate", tools_group)
    simulate_action.setToolTip("Start FSM simulation (F6)")
    simulate_action.setShortcut("F6")
    
    export_code_action = QAction("💻  Export Code", tools_group)
    export_code_action.setToolTip("Export FSM as code (Ctrl+E)")
    export_code_action.setShortcut("Ctrl+E")
    
    tools_group.add_action_button(validate_action, is_large=True)
    tools_group.add_vertical_group([simulate_action, export_code_action])
    
    home_tab.add_group(tools_group)
    
    # Enhanced View tab
    view_tab = ribbon.add_tab("View")
    view_tab.add_group(ProfessionalRibbonFactory.create_enhanced_view_group())
    
    # Enhanced Zoom controls
    zoom_group = ProfessionalInputGroup("Zoom")
    zoom_combo = zoom_group.add_combo([
        "25%", "50%", "75%", "100%", "125%", "150%", "200%", "250%", "300%", "Fit Width", "Fit Page"
    ], "100%")
    zoom_combo.setToolTip("Select zoom level")
    view_tab.add_group(zoom_group)
    
    # Enhanced Layout group
    layout_group = ProfessionalGroup("Layout")
    
    auto_layout_action = QAction("🔄  Auto Layout", layout_group)
    auto_layout_action.setToolTip("Automatically arrange states (Ctrl+L)")
    auto_layout_action.setShortcut("Ctrl+L")
    
    grid_snap_action = QAction("⊞  Grid Snap", layout_group)
    grid_snap_action.setToolTip("Toggle grid snapping (Ctrl+G)")
    grid_snap_action.setShortcut("Ctrl+G")
    grid_snap_action.setCheckable(True)
    
    align_horizontal_action = QAction("↔  Align H", layout_group)
    align_horizontal_action.setToolTip("Align selected items horizontally")
    
    align_vertical_action = QAction("↕  Align V", layout_group)
    align_vertical_action.setToolTip("Align selected items vertically")
    
    layout_group.add_action_button(auto_layout_action, is_large=True)
    layout_group.add_vertical_group([grid_snap_action, align_horizontal_action, align_vertical_action])
    
    view_tab.add_group(layout_group)
    
    # Enhanced Design tab
    design_tab = ribbon.add_tab("Design")
    
    # Theme group
    theme_group = ProfessionalInputGroup("Theme")
    theme_combo = theme_group.add_combo([
        "Default", "Modern", "Classic", "High Contrast", "Dark Mode"
    ], "Default")
    theme_combo.setToolTip("Select application theme")
    design_tab.add_group(theme_group)
    
    # Colors group
    colors_group = ProfessionalGroup("Colors")
    
    state_color_btn = ProfessionalColorButton(QColor("#e3f2fd"))
    state_color_btn.setToolTip("State fill color")
    
    transition_color_btn = ProfessionalColorButton(QColor("#1976d2"))
    transition_color_btn.setToolTip("Transition line color")
    
    colors_widget = QWidget()
    colors_layout = QVBoxLayout(colors_widget)
    colors_layout.setSpacing(4)
    colors_layout.addWidget(QLabel("State:"))
    colors_layout.addWidget(state_color_btn)
    colors_layout.addWidget(QLabel("Transition:"))
    colors_layout.addWidget(transition_color_btn)
    
    colors_group.add_widget(colors_widget)
    design_tab.add_group(colors_group)
    
    # Select first tab
    ribbon.select_first_tab()
    
    return ribbon

# Export enhanced classes
__all__ = [
    'ProfessionalRibbon',
    'ProfessionalGroup', 
    'ProfessionalInputGroup',
    'ProfessionalButton',
    'ProfessionalColorButton',
    'ProfessionalSpinBox',
    'ProfessionalRibbonFactory',
    'create_enhanced_fsm_ribbon'
]