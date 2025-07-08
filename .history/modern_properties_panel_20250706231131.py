# fsm_designer_project/modern_properties_panel.py
"""
Modern properties panel with collapsible sections and enhanced styling.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QFrame,
    QScrollArea, QToolButton, QGridLayout, QColorDialog, QSlider,
    QButtonGroup, QRadioButton, QFontComboBox
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QParallelAnimationGroup
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPixmap, QPainter, QBrush, QPen

from .config import (
    COLOR_ACCENT_PRIMARY, COLOR_BACKGROUND_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_BORDER_LIGHT, COLOR_TEXT_SECONDARY, COLOR_BACKGROUND_APP,
    COLOR_BACKGROUND_MEDIUM
)


class CollapsibleSection(QWidget):
    """A collapsible section widget with smooth animation."""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self.init_ui(title)
        
    def init_ui(self, title):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        self.header = QFrame()
        self.header.setFixedHeight(32)
        self.header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BACKGROUND_MEDIUM};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 4px;
            }}
        """)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 0, 8, 0)
        
        # Toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setArrowType(Qt.DownArrow)
        self.toggle_button.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-weight: bold;
                font-size: 10pt;
            }}
        """)
        
        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        main_layout.addWidget(self.header)
        
        # Content area
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-top: none;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """)
        
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(8)
        
        main_layout.addWidget(self.content_widget)
        
        # Animation
        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
    def add_widget(self, widget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)
        
    def add_row(self, label, widget):
        """Add a labeled row to the content area."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        label_widget.setMinimumWidth(80)
        
        row_layout.addWidget(label_widget)
        row_layout.addWidget(widget, 1)
        
        self.content_layout.addWidget(row_widget)
        
    def toggle_collapsed(self):
        """Toggle the collapsed state with animation."""
        self.is_collapsed = not self.is_collapsed
        
        if self.is_collapsed:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.animation.setStartValue(self.content_widget.height())
            self.animation.setEndValue(0)
        else:
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.animation.setStartValue(0)
            self.animation.setEndValue(self.content_widget.sizeHint().height())
            
        self.animation.start()


class ColorButton(QPushButton):
    """Custom color button with preview."""
    
    colorChanged = pyqtSignal(QColor)
    
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self.color = color or QColor(Qt.white)
        self.setFixedSize(60, 24)
        self.clicked.connect(self.choose_color)
        self.update_color()
        
    def update_color(self):
        """Update the button appearance."""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color.name()};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid {COLOR_ACCENT_PRIMARY};
            }}
        """)
        
    def choose_color(self):
        """Open color dialog."""
        new_color = QColorDialog.getColor(self.color, self, "Choose Color")
        if new_color.isValid():
            self.color = new_color
            self.update_color()
            self.colorChanged.emit(self.color)
            
    def set_color(self, color):
        """Set the color programmatically."""
        self.color = color
        self.update_color()


class ModernPropertiesPanel(QScrollArea):
    """Modern properties panel with enhanced UI and animations."""
    
    # Signals
    propertyChanged = pyqtSignal(str, object)  # property_name, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item = None
        self.property_widgets = {}
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Main widget
        main_widget = QWidget()
        self.setWidget(main_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # Title
        self.title_label = QLabel("Properties")
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: 12pt;
                font-weight: bold;
                padding: 5px;
            }}
        """)
        self.main_layout.addWidget(self.title_label)
        
        # No selection label
        self.no_selection_label = QLabel("No item selected")
        self.no_selection_label.setAlignment(Qt.AlignCenter)
        self.no_selection_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-style: italic;
                padding: 40px;
            }}
        """)
        self.main_layout.addWidget(self.no_selection_label)
        
        # Sections container
        self.sections_container = QWidget()
        self.sections_layout = QVBoxLayout(self.sections_container)
        self.sections_layout.setContentsMargins(0, 0, 0, 0)
        self.sections_layout.setSpacing(5)
        self.main_layout.addWidget(self.sections_container)
        self.sections_container.hide()
        
        # Create sections
        self.create_general_section()
        self.create_appearance_section()
        self.create_behavior_section()
        self.create_advanced_section()
        
        # Add stretch
        self.main_layout.addStretch()
        
        # Style the scroll area
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLOR_BACKGROUND_APP};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLOR_BORDER_LIGHT};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLOR_ACCENT_PRIMARY};
            }}
        """)
        
    def create_general_section(self):
        """Create the general properties section."""
        self.general_section = CollapsibleSection("General")
        self.sections_layout.addWidget(self.general_section)
        
        # Name
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(lambda t: self.propertyChanged.emit("name", t))
        self.general_section.add_row("Name:", self.name_edit)
        
        # Type (read-only)
        self.type_label = QLabel()
        self.type_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self.general_section.add_row("Type:", self.type_label)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.textChanged.connect(
            lambda: self.propertyChanged.emit("description", self.description_edit.toPlainText())
        )
        self.general_section.add_row("Description:", self.description_edit)
        
    def create_appearance_section(self):
        """Create the appearance properties section."""
        self.appearance_section = CollapsibleSection("Appearance")
        self.sections_layout.addWidget(self.appearance_section)
        
        # Color
        self.color_button = ColorButton()
        self.color_button.colorChanged.connect(lambda c: self.propertyChanged.emit("color", c.name()))
        self.appearance_section.add_row("Color:", self.color_button)
        
        # Font
        font_widget = QWidget()
        font_layout = QHBoxLayout(font_widget)
        font_layout.setContentsMargins(0, 0, 0, 0)
        
        self.font_combo = QFontComboBox()
        self.font_combo.setMaximumWidth(150)
        self.font_combo.currentFontChanged.connect(
            lambda f: self.propertyChanged.emit("font_family", f.family())
        )
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(10)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.valueChanged.connect(
            lambda v: self.propertyChanged.emit("font_size", v)
        )
        
        font_layout.addWidget(self.font_combo)
        font_layout.addWidget(self.font_size_spin)
        
        self.appearance_section.add_row("Font:", font_widget)
        
        # Border width
        self.border_width_slider = QSlider(Qt.Horizontal)
        self.border_width_slider.setRange(1, 50)  # 0.1 to 5.0
        self.border_width_slider.setValue(18)  # 1.8
        self.border_width_slider.valueChanged.connect(
            lambda v: self.propertyChanged.emit("border_width", v / 10.0)
        )
        
        border_widget = QWidget()
        border_layout = QHBoxLayout(border_widget)
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.addWidget(self.border_width_slider)
        
        self.border_width_label = QLabel("1.8")
        self.border_width_label.setMinimumWidth(30)
        border_layout.addWidget(self.border_width_label)
        
        self.border_width_slider.valueChanged.connect(
            lambda v: self.border_width_label.setText(f"{v/10:.1f}")
        )
        
        self.appearance_section.add_row("Border:", border_widget)
        
    def create_behavior_section(self):
        """Create the behavior properties section."""
        self.behavior_section = CollapsibleSection("Behavior")
        self.sections_layout.addWidget(self.behavior_section)
        
        # State-specific properties
        self.initial_check = QCheckBox("Initial State")
        self.initial_check.toggled.connect(lambda c: self.propertyChanged.emit("is_initial", c))
        self.behavior_section.add_widget(self.initial_check)
        
        self.final_check = QCheckBox("Final State")
        self.final_check.toggled.connect(lambda c: self.propertyChanged.emit("is_final", c))
        self.behavior_section.add_widget(self.final_check)
        
        self.superstate_check = QCheckBox("Superstate")
        self.superstate_check.toggled.connect(lambda c: self.propertyChanged.emit("is_superstate", c))
        self.behavior_section.add_widget(self.superstate_check)
        
        # Transition-specific properties
        self.event_edit = QLineEdit()
        self.event_edit.textChanged.connect(lambda t: self.propertyChanged.emit("event", t))
        self.event_row = self.behavior_section.add_row("Event:", self.event_edit)
        
        self.condition_edit = QLineEdit()
        self.condition_edit.textChanged.connect(lambda t: self.propertyChanged.emit("condition", t))
        self.condition_row = self.behavior_section.add_row("Condition:", self.condition_edit)
        
    def create_advanced_section(self):
        """Create the advanced properties section."""
        self.advanced_section = CollapsibleSection("Advanced")
        self.advanced_section.toggle_collapsed()  # Start collapsed
        self.sections_layout.addWidget(self.advanced_section)
        
        # Actions (for states)
        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        self.entry_action_edit = QTextEdit()
        self.entry_action_edit.setMaximumHeight(50)
        self.entry_action_edit.setPlaceholderText("Entry action code...")
        self.entry_action_edit.textChanged.connect(
            lambda: self.propertyChanged.emit("entry_action", self.entry_action_edit.toPlainText())
        )
        
        self.exit_action_edit = QTextEdit()
        self.exit_action_edit.setMaximumHeight(50)
        self.exit_action_edit.setPlaceholderText("Exit action code...")
        self.exit_action_edit.textChanged.connect(
            lambda: self.propertyChanged.emit("exit_action", self.exit_action_edit.toPlainText())
        )
        
        actions_layout.addWidget(QLabel("Entry Action:"))
        actions_layout.addWidget(self.entry_action_edit)
        actions_layout.addWidget(QLabel("Exit Action:"))
        actions_layout.addWidget(self.exit_action_edit)
        
        self.advanced_section.add_widget(actions_widget)
        
    def set_item(self, item):
        """Set the current item to edit."""
        self.current_item = item
        
        if item is None:
            self.no_selection_label.show()
            self.sections_container.hide()
            self.title_label.setText("Properties")
            return
            
        self.no_selection_label.hide()
        self.sections_container.show()
        
        # Get item data
        item_data = item.get_data() if hasattr(item, 'get_data') else {}
        item_type = type(item).__name__
        
        # Update title
        self.title_label.setText(f"{item_type} Properties")
        
        # Update type label
        self.type_label.setText(item_type.replace("Graphics", "").replace("Item", ""))
        
        # Block signals while updating
        self.block_signals(True)
        
        # Update general properties
        self.name_edit.setText(item_data.get('name', ''))
        self.description_edit.setText(item_data.get('description', ''))
        
        # Update appearance
        color = item_data.get('color', '#FFFFFF')
        self.color_button.set_color(QColor(color))
        
        font_family = item_data.get('font_family', 'Arial')
        font = QFont(font_family)
        self.font_combo.setCurrentFont(font)
        
        font_size = item_data.get('font_size', 10)
        self.font_size_spin.setValue(font_size)
        
        border_width = item_data.get('border_width', 1.8)
        self.border_width_slider.setValue(int(border_width * 10))
        
        # Show/hide sections based on item type
        if "State" in item_type:
            self.initial_check.setVisible(True)
            self.final_check.setVisible(True)
            self.superstate_check.setVisible(True)
            self.event_edit.setVisible(False)
            self.condition_edit.setVisible(False)
            
            # Update state properties
            self.initial_check.setChecked(item_data.get('is_initial', False))
            self.final_check.setChecked(item_data.get('is_final', False))
            self.superstate_check.setChecked(item_data.get('is_superstate', False))
            
            # Update actions
            self.entry_action_edit.setText(item_data.get('entry_action', ''))
            self.exit_action_edit.setText(item_data.get('exit_action', ''))
            
        elif "Transition" in item_type:
            self.initial_check.setVisible(False)
            self.final_check.setVisible(False)
            self.superstate_check.setVisible(False)
            self.event_edit.setVisible(True)
            self.condition_edit.setVisible(True)
            
            # Update transition properties
            self.event_edit.setText(item_data.get('event', ''))
            self.condition_edit.setText(item_data.get('condition', ''))
            
        # Unblock signals
        self.block_signals(False)
        
    def block_signals(self, block):
        """Block/unblock all property signals."""
        widgets = [
            self.name_edit, self.description_edit, self.color_button,
            self.font_combo, self.font_size_spin, self.border_width_slider,
            self.initial_check, self.final_check, self.superstate_check,
            self.event_edit, self.condition_edit, self.entry_action_edit,
            self.exit_action_edit
        ]
        
        for widget in widgets:
            widget.blockSignals(block)
