# fsm_designer_project/ui/widgets/ribbon_toolbar.py
"""
Modern ribbon-style toolbar implementation for FSM Designer.
Provides a more intuitive and visually appealing interface.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton, 
    QLabel, QFrame, QButtonGroup, QSizePolicy, QMenu
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QColor

from ...utils import get_standard_icon
from ...utils.config import (
    COLOR_ACCENT_PRIMARY, COLOR_BACKGROUND_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_BORDER_LIGHT, COLOR_TEXT_SECONDARY, COLOR_BACKGROUND_APP,
    COLOR_BACKGROUND_MEDIUM, COLOR_ACCENT_PRIMARY_LIGHT, COLOR_TEXT_ON_ACCENT
)


class RibbonButton(QToolButton):
    """Enhanced button for ribbon interface with hover effects."""
    
    def __init__(self, action, is_large=True, parent=None):
        super().__init__(parent)
        self.setDefaultAction(action)
        self.is_large = is_large

        if is_large:
            self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            self.setIconSize(QSize(28, 28))
            self.setMinimumSize(QSize(75, 70))
        else:
            self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            self.setIconSize(QSize(16, 16))
            self.setMinimumSize(QSize(80, 28))

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.update_style()

    def update_style(self):
        padding = "4px" if self.is_large else "4px 8px"
        self.setStyleSheet(f"""
            RibbonButton {{
                border: 1px solid transparent;
                border-radius: 4px;
                padding: {padding};
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
            }}
            RibbonButton:hover {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
                border: 1px solid {COLOR_ACCENT_PRIMARY};
            }}
            RibbonButton:pressed {{
                background-color: {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
                color: {COLOR_TEXT_ON_ACCENT};
            }}
            RibbonButton:checked {{
                background-color: {QColor(COLOR_ACCENT_PRIMARY_LIGHT).darker(105).name()};
                border: 1px solid {COLOR_ACCENT_PRIMARY};
            }}
            RibbonButton:disabled {{
                color: {COLOR_TEXT_SECONDARY};
            }}
        """)


class RibbonGroup(QFrame):
    """A group of related controls within a ribbon tab."""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)
        
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(4)
        main_layout.addLayout(self.content_layout)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 8pt; padding-top:2px;")
        main_layout.addWidget(title_label)
        
    def add_action_button(self, action, is_large=True):
        button = RibbonButton(action, is_large)
        self.content_layout.addWidget(button)
        return button

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)
        
    def add_separator(self):
        separator = QFrame()
        separator.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        separator.setStyleSheet(f"color: {COLOR_BORDER_LIGHT};")
        self.content_layout.addWidget(separator)


class RibbonTab(QWidget):
    """A tab in the ribbon containing groups of related functions."""
    
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)
        self.layout.addStretch()
        
    def add_group(self, group):
        self.layout.insertWidget(self.layout.count() - 1, group)


class ModernRibbon(QWidget):
    """Modern ribbon interface replacing traditional toolbar."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = {}
        self.current_tab_widget = None
        self.file_button = None
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.tab_bar = QWidget()
        self.tab_bar.setFixedHeight(30)
        self.tab_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND_APP};
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            }}
        """)
        
        self.tab_layout = QHBoxLayout(self.tab_bar)
        self.tab_layout.setContentsMargins(5, 0, 5, 0)
        self.tab_layout.setSpacing(2)

        self.file_button = QToolButton()
        self.file_button.setText("File")
        self.file_button.setCheckable(True)
        self.file_button.setPopupMode(QToolButton.InstantPopup)
        self.file_button.setFixedHeight(28)
        self.file_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLOR_ACCENT_PRIMARY}; color: {COLOR_TEXT_ON_ACCENT};
                border: none; padding: 0 15px; font-weight: bold;
            }}
            QToolButton:hover {{ background-color: {QColor(COLOR_ACCENT_PRIMARY).lighter(110).name()}; }}
            QToolButton:checked, QToolButton[popupMode="1"] {{ /* popupMode="1" is for when menu is open */
                background-color: {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
            }}
        """)
        self.file_button.clicked.connect(self.on_file_button_clicked)
        self.tab_layout.addWidget(self.file_button)
        
        self.tab_button_group = QButtonGroup(self)
        self.tab_button_group.setExclusive(True)
        self.tab_button_group.buttonClicked.connect(self.on_tab_clicked)
        self.tab_layout.addStretch()
        
        main_layout.addWidget(self.tab_bar)
        
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setFixedHeight(85)
        self.content_area.setStyleSheet(f"background-color: {COLOR_BACKGROUND_LIGHT};")
        
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content_area)
        
    def create_tab_button(self, text):
        button = QPushButton(text)
        button.setCheckable(True)
        button.setFixedHeight(28)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: 1px solid transparent; border-bottom: none;
                padding: 0 15px; color: {COLOR_TEXT_PRIMARY}; font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {COLOR_ACCENT_PRIMARY_LIGHT}; }}
            QPushButton:checked {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT}; border-bottom: 1px solid {COLOR_BACKGROUND_LIGHT};
                border-top-left-radius: 4px; border-top-right-radius: 4px;
            }}
        """)
        return button
        
    def add_tab(self, name):
        tab_widget = RibbonTab(name, self)
        button = self.create_tab_button(name)
        self.tab_button_group.addButton(button)
        self.tab_layout.insertWidget(self.tab_layout.count() - 1, button)
        self.tabs[button] = tab_widget
        return tab_widget
    
    def on_file_button_clicked(self):
        """Handler to ensure tab buttons are deselected when File is clicked."""
        if btn := self.tab_button_group.checkedButton():
            self.tab_button_group.setExclusive(False)
            btn.setChecked(False)
            self.tab_button_group.setExclusive(True)

        if self.current_tab_widget:
            self.current_tab_widget.hide()
        
    def on_tab_clicked(self, button):
        """Handler for when a main tab (Home, View, etc.) is clicked."""
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
            self.current_tab_widget.show()

    def set_file_menu(self, menu: QMenu):
        """Assigns the File menu to the File button and manages its state."""
        self.file_button.setMenu(menu)
        # When the menu is closed (e.g., by clicking away), ensure the button is unchecked.
        menu.aboutToHide.connect(lambda: self.file_button.setChecked(False))

    def select_first_tab(self):
        if self.tab_button_group.buttons():
            self.tab_button_group.buttons()[0].click()