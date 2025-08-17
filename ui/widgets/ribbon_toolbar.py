# fsm_designer_project/ui/widgets/ribbon_toolbar.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton,
    QLabel, QFrame, QButtonGroup, QSizePolicy, QMenu, QComboBox,
    QLineEdit, QSpacerItem, QGraphicsDropShadowEffect, QApplication,
    QGraphicsOpacityEffect, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, QParallelAnimationGroup, QAbstractAnimation
from PyQt6.QtGui import QIcon, QColor, QFont, QPainter, QPalette, QFontMetrics, QPixmap, QPainterPath, QAction

from ...utils import get_standard_icon


class ModernButton(QToolButton):
    """Modern, clean button with subtle animations and professional styling"""
    
    def __init__(self, action, style="large", parent=None):
        super().__init__(parent)
        self.setDefaultAction(action)
        self.button_style = style
        self._is_hovered = False
        self._setup_button()
        self._setup_animations()

    def _setup_button(self):
        """Configure button with modern, clean styling"""
        if self.button_style == "large":
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            self.setIconSize(QSize(32, 32))
            self.setMinimumSize(QSize(72, 68))
            self.setMaximumSize(QSize(80, 68))
        elif self.button_style == "medium":
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.setIconSize(QSize(20, 20))
            self.setMinimumSize(QSize(70, 24))
            self.setMaximumHeight(24)
        else:  # small
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.setIconSize(QSize(16, 16))
            self.setMinimumSize(QSize(60, 22))
            self.setMaximumHeight(22)
        
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Modern styling
        self.setStyleSheet("""
            ModernButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
                color: #2c3e50;
                font-size: 11px;
                font-weight: 500;
            }
            ModernButton:hover {
                background: rgba(52, 152, 219, 0.1);
                border: 1px solid rgba(52, 152, 219, 0.3);
            }
            ModernButton:pressed {
                background: rgba(52, 152, 219, 0.2);
                border: 1px solid rgba(52, 152, 219, 0.5);
            }
            ModernButton:checked {
                background: rgba(52, 152, 219, 0.15);
                border: 1px solid rgba(52, 152, 219, 0.4);
            }
        """)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_animations(self):
        """Setup smooth hover animations"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._is_hovered = True

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._is_hovered = False

class ModernSplitButton(QWidget):
    """Modern split button with clean design"""
    
    clicked = pyqtSignal()
    
    def __init__(self, main_action, menu_actions, parent=None):
        super().__init__(parent)
        self._setup_layout()
        self._create_buttons(main_action, menu_actions)

    def _setup_layout(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def _create_buttons(self, main_action, menu_actions):
        # Main button
        self.main_button = QToolButton()
        self.main_button.setDefaultAction(main_action)
        self.main_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.main_button.setIconSize(QSize(32, 32))
        self.main_button.setMinimumSize(QSize(56, 68))
        self.main_button.clicked.connect(self.clicked.emit)
        
        # Dropdown button
        self.dropdown_button = QToolButton()
        self.dropdown_button.setText("▼")
        self.dropdown_button.setMaximumWidth(16)
        self.dropdown_button.setMinimumHeight(68)
        self.dropdown_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # Create and style menu
        menu = QMenu(self)
        menu.addActions(menu_actions)
        self.dropdown_button.setMenu(menu)
        
        # Apply modern styling
        button_style = """
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: #2c3e50;
                font-size: 11px;
                font-weight: 500;
            }
            QToolButton:hover {
                background: rgba(52, 152, 219, 0.1);
                border: 1px solid rgba(52, 152, 219, 0.3);
            }
            QToolButton:pressed {
                background: rgba(52, 152, 219, 0.2);
            }
        """
        self.main_button.setStyleSheet(button_style)
        self.dropdown_button.setStyleSheet(button_style)
        
        self.layout().addWidget(self.main_button)
        self.layout().addWidget(self.dropdown_button)

class ModernRibbonGroup(QFrame):
    """Modern ribbon group with clean, organized layout"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernRibbonGroup")
        self.title = title
        self._setup_layout()
        self._apply_styling()

    def _setup_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(2)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 2, 4, 2)
        self.content_layout.setSpacing(3)
        
        main_layout.addWidget(self.content_widget, 1)
        
        # Clean title label
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(False)
        
        # Modern typography
        font = QFont("Segoe UI", 8, QFont.Weight.Normal)
        title_label.setFont(font)
        title_label.setStyleSheet("""
            color: #7f8c8d;
            background: transparent;
            padding: 2px;
            border: none;
        """)
        
        main_layout.addWidget(title_label)

    def _apply_styling(self):
        self.setMinimumHeight(96)
        self.setMaximumHeight(96)
        self.setMinimumWidth(60)
        
        self.setStyleSheet("""
            ModernRibbonGroup {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                margin: 1px;
            }
            ModernRibbonGroup:hover {
                background: rgba(236, 240, 241, 0.5);
                border: 1px solid rgba(189, 195, 199, 0.3);
            }
        """)

    def add_button(self, action, style="large"):
        """Add a modern button"""
        button = ModernButton(action, style)
        self.content_layout.addWidget(button)
        return button

    def add_split_button(self, main_action, menu_actions):
        """Add a modern split button"""
        split_button = ModernSplitButton(main_action, menu_actions)
        self.content_layout.addWidget(split_button)
        return split_button

    def add_widget(self, widget):
        """Add custom widget"""
        self.content_layout.addWidget(widget)

    def add_button_column(self, actions):
        """Add vertical column of small buttons"""
        column_widget = QWidget()
        column_layout = QVBoxLayout(column_widget)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(1)
        
        for action in actions:
            btn = ModernButton(action, style="small")
            column_layout.addWidget(btn)
        
        if len(actions) < 3:
            column_layout.addStretch()
        
        self.content_layout.addWidget(column_widget)
        return column_widget

    def add_separator(self):
        """Add clean vertical separator"""
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Plain)
        separator.setMaximumWidth(1)
        separator.setStyleSheet("""
            background: #bdc3c7;
            border: none;
            margin: 8px 2px;
        """)
        self.content_layout.addWidget(separator)

class ModernInputGroup(QWidget):
    """Modern input controls group with clean design"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._setup_layout(title)

    def _setup_layout(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)
        
        # Content area
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(2)
        layout.addLayout(self.content_layout, 1)
        
        # Clean title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 8))
        title_label.setStyleSheet("color: #7f8c8d; padding: 2px;")
        layout.addWidget(title_label)
        
        self.setMinimumHeight(88)
        self.setMaximumHeight(88)
        self.setMinimumWidth(100)

    def add_combo(self, items, current_text=None):
        """Add modern combo box"""
        combo = QComboBox()
        combo.addItems(items)
        if current_text:
            combo.setCurrentText(current_text)
        
        combo.setMinimumWidth(90)
        combo.setMaximumHeight(24)
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        
        combo.setStyleSheet("""
            QComboBox {
                background: white;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                color: #2c3e50;
            }
            QComboBox:hover {
                border: 1px solid #3498db;
            }
            QComboBox:focus {
                border: 2px solid #3498db;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #7f8c8d;
                margin-right: 4px;
            }
        """)
        
        self.content_layout.addWidget(combo)
        return combo

    def add_line_edit(self, placeholder=""):
        """Add modern line edit"""
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumWidth(90)
        edit.setMaximumHeight(24)
        
        edit.setStyleSheet("""
            QLineEdit {
                background: white;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                color: #2c3e50;
            }
            QLineEdit:hover {
                border: 1px solid #3498db;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
                outline: none;
            }
        """)
        
        self.content_layout.addWidget(edit)
        return edit

class ModernTab(QWidget):
    """Modern tab with clean layout and smooth animations"""
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(6)
        self.layout.addStretch()
        
        # Fade animation
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(250)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def add_group(self, group):
        """Add group with clean separator"""
        self.layout.insertWidget(self.layout.count() - 1, group)
        
        # Add separator if not the first group
        if self.layout.count() > 2:
            separator = QFrame()
            separator.setFrameStyle(QFrame.Shape.VLine | QFrame.Shadow.Plain)
            separator.setMaximumWidth(1)
            separator.setStyleSheet("""
                background: #d5dbdb;
                border: none;
                margin: 6px 3px;
            """)
            self.layout.insertWidget(self.layout.count() - 2, separator)

    def show_animated(self):
        """Show with smooth animation"""
        self.show()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

class ModernRibbon(QWidget):
    """Modern, clean ribbon interface with professional design"""
    
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
        self._apply_modern_theme()

    def _init_ui(self):
        """Initialize modern UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Tab bar
        self._create_tab_bar()
        main_layout.addWidget(self.tab_bar)

        # Content area
        self._create_content_area()
        main_layout.addWidget(self.content_area)

    def _create_tab_bar(self):
        """Create modern tab bar"""
        self.tab_bar = QWidget()
        self.tab_bar.setFixedHeight(32)
        self.tab_bar.setObjectName("ModernTabBar")

        self.tab_layout = QHBoxLayout(self.tab_bar)
        self.tab_layout.setContentsMargins(4, 2, 4, 0)
        self.tab_layout.setSpacing(1)

        # File button
        self._create_file_button()
        
        # Tab buttons
        self._create_tab_container()
        
        # Search bar
        self._create_search_bar()

    def _create_file_button(self):
        """Create modern file button"""
        self.file_button = QToolButton()
        self.file_button.setText("File")
        self.file_button.setCheckable(True)
        self.file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.file_button.setFixedSize(48, 28)
        self.file_button.setCursor(Qt.CursorShape.PointingHandCursor)
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

    def _create_search_bar(self):
        """Create modern search bar"""
        self.tab_layout.addStretch()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setFixedSize(180, 26)
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        
        self.tab_layout.addWidget(self.search_bar)

    def _create_content_area(self):
        """Create modern content area"""
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_area.setObjectName("ModernContentArea")
        self.content_area.setFixedHeight(100)
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

    def _apply_modern_theme(self):
        """Apply modern, clean theme"""
        self.setStyleSheet("""
            ModernRibbon {
                background: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
            
            #ModernTabBar {
                background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
                border-bottom: 1px solid #dee2e6;
            }
            
            #ModernContentArea {
                background: #f8f9fa;
                border-top: 1px solid #dee2e6;
            }
            
            QToolButton[objectName="FileButton"] {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
            }
            QToolButton[objectName="FileButton"]:hover {
                background: #2980b9;
            }
            QToolButton[objectName="FileButton"]:pressed {
                background: #21618c;
            }
            
            QPushButton[objectName="ModernTabButton"] {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                color: #2c3e50;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton[objectName="ModernTabButton"]:hover {
                background: rgba(52, 152, 219, 0.1);
            }
            QPushButton[objectName="ModernTabButton"]:checked {
                background: rgba(52, 152, 219, 0.15);
                border-bottom: 2px solid #3498db;
            }
            
            QLineEdit {
                background: white;
                border: 1px solid #bdc3c7;
                border-radius: 13px;
                padding: 4px 12px;
                font-size: 11px;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
                outline: none;
            }
        """)

    def add_tab(self, name):
        """Add new tab"""
        tab_widget = ModernTab(name, self)
        button = QPushButton(name)
        button.setCheckable(True)
        button.setObjectName("ModernTabButton")
        button.setFixedHeight(28)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Optimal width
        font_metrics = QFontMetrics(button.font())
        text_width = font_metrics.horizontalAdvance(name)
        button.setMinimumWidth(text_width + 24)
        
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
            if self.content_layout.count() > 0:
                item = self.content_layout.takeAt(0)
                if item and item.widget():
                    item.widget().setParent(None)
            
            self.content_layout.addWidget(self.current_tab_widget)
            self.current_tab_widget.show_animated()
            
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
        """Set file menu"""
        self.file_button.setObjectName("FileButton")
        self.file_button.setMenu(menu)
        menu.aboutToHide.connect(lambda: self.file_button.setChecked(False))

    def select_first_tab(self):
        """Select first tab"""
        if self.tab_button_group.buttons():
            self.tab_button_group.buttons()[0].click()

# Modern utility components

class ModernColorButton(QToolButton):
    """Modern color picker button"""
    
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, color=Qt.GlobalColor.black, parent=None):
        super().__init__(parent)
        self.current_color = QColor(color)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._show_color_dialog)
        self._update_color_display()
        
        self.setStyleSheet("""
            QToolButton {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
            QToolButton:hover {
                border: 1px solid #3498db;
            }
        """)

    def _update_color_display(self):
        """Update color display"""
        pixmap = QPixmap(22, 22)
        pixmap.fill(self.current_color)
        
        painter = QPainter(pixmap)
        painter.setPen(QColor("#bdc3c7"))
        painter.drawRect(0, 0, 21, 21)
        painter.end()
        
        self.setIcon(QIcon(pixmap))
        self.setToolTip(f"Color: {self.current_color.name()}")

    def _show_color_dialog(self):
        """Show color picker"""
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.current_color, self, "Choose Color")
        if color.isValid():
            self.current_color = color
            self._update_color_display()
            self.color_changed.emit(color)

# Factory for creating common ribbon elements

class ModernRibbonFactory:
    """Factory for creating modern ribbon components"""
    
    @staticmethod
    def create_file_menu():
        """Create modern file menu"""
        from PyQt6.QtGui import QKeySequence
        menu = QMenu()
        
        # File operations
        new_action = QAction("📄 New", menu)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        menu.addAction(new_action)
        
        open_action = QAction("📂 Open", menu)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        save_action = QAction("💾 Save", menu)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        menu.addAction(save_action)
        
        save_as_action = QAction("💾 Save As...", menu)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        menu.addAction(save_as_action)
        
        menu.addSeparator()
        
        exit_action = QAction("🚪 Exit", menu)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        menu.addAction(exit_action)
        
        return menu

    @staticmethod
    def create_edit_group():
        """Create modern edit group"""
        from PyQt6.QtGui import QKeySequence
        
        group = ModernRibbonGroup("Edit")
        
        # Undo/Redo
        undo_action = QAction("⮌ Undo", group)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        
        redo_action = QAction("⮎ Redo", group)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        
        # Clipboard
        cut_action = QAction("✂️ Cut", group)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        
        copy_action = QAction("📋 Copy", group)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        
        paste_action = QAction("📄 Paste", group)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        
        group.add_button_column([undo_action, redo_action])
        group.add_separator()
        group.add_button_column([cut_action, copy_action, paste_action])
        
        return group

# Create modern FSM Designer ribbon
def create_modern_fsm_ribbon():
    """Create modern FSM Designer ribbon"""
    ribbon = ModernRibbon()
    
    # File menu
    file_menu = ModernRibbonFactory.create_file_menu()
    ribbon.set_file_menu(file_menu)
    
    # Home tab
    home_tab = ribbon.add_tab("Home")
    
    # Edit group
    edit_group = ModernRibbonFactory.create_edit_group()
    home_tab.add_group(edit_group)
    
    # States group
    states_group = ModernRibbonGroup("States")
    
    add_state_action = QAction("➕ Add State", states_group)
    add_state_action.setShortcut("Ctrl+Shift+S")
    
    delete_state_action = QAction("🗑️ Delete", states_group)
    delete_state_action.setShortcut("Delete")
    
    initial_state_action = QAction("🏁 Initial", states_group)
    final_state_action = QAction("🎯 Final", states_group)
    
    states_group.add_button(add_state_action)
    states_group.add_separator()
    states_group.add_button_column([delete_state_action, initial_state_action, final_state_action])
    
    home_tab.add_group(states_group)
    
    # Transitions group
    transitions_group = ModernRibbonGroup("Transitions")
    
    add_transition_action = QAction("🔗 Add", transitions_group)
    add_transition_action.setShortcut("Ctrl+T")
    
    edit_transition_action = QAction("✏️ Edit", transitions_group)
    edit_transition_action.setShortcut("F2")
    
    delete_transition_action = QAction("❌ Delete", transitions_group)
    delete_transition_action.setShortcut("Ctrl+Delete")
    
    transitions_group.add_button(add_transition_action)
    transitions_group.add_separator()
    transitions_group.add_button_column([edit_transition_action, delete_transition_action])
    
    home_tab.add_group(transitions_group)
    
    # Tools group
    tools_group = ModernRibbonGroup("Tools")
    
    validate_action = QAction("✅ Validate", tools_group)
    validate_action.setShortcut("F5")
    
    simulate_action = QAction("▶️ Simulate", tools_group)
    simulate_action.setShortcut("F6")
    
    export_action = QAction("💻 Export", tools_group)
    export_action.setShortcut("Ctrl+E")
    
    tools_group.add_button(validate_action)
    tools_group.add_separator()
    tools_group.add_button_column([simulate_action, export_action])
    
    home_tab.add_group(tools_group)
    
    # View tab
    view_tab = ribbon.add_tab("View")
    
    # Zoom group
    zoom_group = ModernInputGroup("Zoom")
    zoom_combo = zoom_group.add_combo([
        "25%", "50%", "75%", "100%", "125%", "150%", "200%", "Fit"
    ], "100%")
    view_tab.add_group(zoom_group)
    
    # Layout group
    layout_group = ModernRibbonGroup("Layout")
    
    auto_layout_action = QAction("🔄 Auto", layout_group)
    auto_layout_action.setShortcut("Ctrl+L")
    
    grid_action = QAction("⊞ Grid", layout_group)
    grid_action.setShortcut("Ctrl+G")
    grid_action.setCheckable(True)
    
    align_h_action = QAction("↔ Align H", layout_group)
    align_v_action = QAction("↕ Align V", layout_group)
    
    layout_group.add_button(auto_layout_action)
    layout_group.add_separator()
    layout_group.add_button_column([grid_action, align_h_action, align_v_action])
    
    view_tab.add_group(layout_group)
    
    # Design tab
    design_tab = ribbon.add_tab("Design")
    
    # Theme group
    theme_group = ModernInputGroup("Theme")
    theme_combo = theme_group.add_combo([
        "Default", "Modern", "Dark", "Classic"
    ], "Default")
    design_tab.add_group(theme_group)
    
    # Colors group
    colors_group = ModernRibbonGroup("Colors")
    
    # Create color picker widgets
    state_color_widget = QWidget()
    state_color_layout = QVBoxLayout(state_color_widget)
    state_color_layout.setContentsMargins(0, 0, 0, 0)
    state_color_layout.setSpacing(2)
    
    state_label = QLabel("State")
    state_label.setFont(QFont("Segoe UI", 8))
    state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    state_label.setStyleSheet("color: #7f8c8d;")
    
    state_color_btn = ModernColorButton(QColor("#e3f2fd"))
    state_color_btn.setToolTip("State fill color")
    
    state_color_layout.addWidget(state_label)
    state_color_layout.addWidget(state_color_btn)
    state_color_layout.addStretch()
    
    transition_color_widget = QWidget()
    transition_color_layout = QVBoxLayout(transition_color_widget)
    transition_color_layout.setContentsMargins(0, 0, 0, 0)
    transition_color_layout.setSpacing(2)
    
    transition_label = QLabel("Line")
    transition_label.setFont(QFont("Segoe UI", 8))
    transition_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    transition_label.setStyleSheet("color: #7f8c8d;")
    
    transition_color_btn = ModernColorButton(QColor("#1976d2"))
    transition_color_btn.setToolTip("Transition line color")
    
    transition_color_layout.addWidget(transition_label)
    transition_color_layout.addWidget(transition_color_btn)
    transition_color_layout.addStretch()
    
    colors_group.add_widget(state_color_widget)
    colors_group.add_widget(transition_color_widget)
    
    design_tab.add_group(colors_group)
    
    # Style group
    style_group = ModernInputGroup("Style")
    style_combo = style_group.add_combo([
        "Rounded", "Square", "Circle", "Diamond"
    ], "Rounded")
    design_tab.add_group(style_group)
    
    # Select first tab
    ribbon.select_first_tab()
    
    return ribbon

# Additional utility functions

def apply_modern_menu_style(menu):
    """Apply modern styling to a menu"""
    menu.setStyleSheet("""
        QMenu {
            background: white;
            border: 1px solid #bdc3c7;
            border-radius: 6px;
            padding: 4px 0px;
        }
        QMenu::item {
            background: transparent;
            padding: 6px 20px;
            color: #2c3e50;
            font-size: 11px;
        }
        QMenu::item:selected {
            background: rgba(52, 152, 219, 0.1);
            color: #2c3e50;
        }
        QMenu::separator {
            height: 1px;
            background: #ecf0f1;
            margin: 4px 0px;
        }
    """)

class ModernStatusIndicator(QWidget):
    """Modern status indicator for ribbon"""
    
    def __init__(self, text="Ready", parent=None):
        super().__init__(parent)
        self._setup_ui(text)
    
    def _setup_ui(self, text):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)
        
        # Status dot
        self.status_dot = QFrame()
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setStyleSheet("""
            background: #27ae60;
            border-radius: 4px;
        """)
        
        # Status text
        self.status_label = QLabel(text)
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet("color: #2c3e50;")
        
        layout.addWidget(self.status_dot)
        layout.addWidget(self.status_label)
        layout.addStretch()
    
    def set_status(self, text, color="#27ae60"):
        """Update status"""
        self.status_label.setText(text)
        self.status_dot.setStyleSheet(f"""
            background: {color};
            border-radius: 4px;
        """)

# Export all modern classes
__all__ = [
    'ModernRibbon',
    'ModernRibbonGroup', 
    'ModernInputGroup',
    'ModernButton',
    'ModernColorButton',
    'ModernRibbonFactory',
    'ModernStatusIndicator',
    'create_modern_fsm_ribbon',
    'apply_modern_menu_style'
]