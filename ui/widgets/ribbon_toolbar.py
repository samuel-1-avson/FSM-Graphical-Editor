# fsm_designer_project/ui/widgets/ribbon_toolbar.py

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QToolButton, 
    QLabel, QFrame, QButtonGroup, QSizePolicy, QMenu, QComboBox,
    QLineEdit, QSpacerItem
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QFont

from ...utils import get_standard_icon
from ...utils.config import (
    COLOR_ACCENT_PRIMARY, COLOR_BACKGROUND_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_BORDER_LIGHT, COLOR_TEXT_SECONDARY, COLOR_BACKGROUND_APP,
    COLOR_BACKGROUND_MEDIUM, COLOR_ACCENT_PRIMARY_LIGHT, COLOR_TEXT_ON_ACCENT
)

class RibbonButton(QToolButton):
    def __init__(self, action, is_large=True, parent=None):
        super().__init__(parent)
        self.setDefaultAction(action)
        self.is_large = is_large
        if is_large:
            self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            self.setIconSize(QSize(32, 32))
            self.setMinimumSize(QSize(80, 72))
            self.setMaximumSize(QSize(90, 72))
        else:
            self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            self.setIconSize(QSize(16, 16))
            self.setMinimumSize(QSize(75, 24))
            self.setMaximumHeight(24)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.update_style()

    def update_style(self):
        padding = "6px 4px" if self.is_large else "2px 8px"
        font_size = "8pt"
        self.setStyleSheet(f"""
            RibbonButton {{
                border: 1px solid transparent;
                border-radius: 3px;
                padding: {padding};
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                font-size: {font_size};
                font-weight: normal;
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
                background-color: transparent;
            }}
        """)

class RibbonSplitButton(QWidget):
    def __init__(self, main_action, menu_actions, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.main_button = QToolButton()
        self.main_button.setDefaultAction(main_action)
        self.main_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.main_button.setIconSize(QSize(32, 32))
        self.main_button.setMinimumSize(QSize(60, 72))
        self.dropdown_button = QToolButton()
        self.dropdown_button.setText("▼")
        self.dropdown_button.setMaximumWidth(16)
        self.dropdown_button.setMinimumHeight(72)
        self.dropdown_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        menu.addActions(menu_actions)
        self.dropdown_button.setMenu(menu)
        layout.addWidget(self.main_button)
        layout.addWidget(self.dropdown_button)
        self.update_style()

    def update_style(self):
        button_style = f"""
            QToolButton {{
                border: 1px solid transparent;
                border-radius: 3px;
                background-color: transparent;
                color: {COLOR_TEXT_PRIMARY};
                font-size: 8pt;
                padding: 3px;
            }}
            QToolButton:hover {{
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
                border: 1px solid {COLOR_ACCENT_PRIMARY};
            }}
        """
        self.main_button.setStyleSheet(button_style)
        self.dropdown_button.setStyleSheet(button_style + f"""
            QToolButton {{
                border-left: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 0px 3px 3px 0px;
                font-size: 6pt;
                max-width: 16px;
                padding: 2px;
            }}
        """)

class RibbonGroup(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.title = title
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(2)
        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(3)
        main_layout.addWidget(self.content_widget)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY}; 
                font-size: 7pt; 
                font-weight: normal;
                padding: 2px 0px;
                border-top: 1px solid {COLOR_BORDER_LIGHT};
                margin-top: 2px;
            }}
        """)
        main_layout.addWidget(title_label)
        self.setMinimumHeight(98)
        self.setMaximumHeight(98)

    def add_action_button(self, action, is_large=True):
        button = RibbonButton(action, is_large)
        self.content_layout.addWidget(button)
        return button

    def add_split_button(self, main_action, menu_actions):
        split_button = RibbonSplitButton(main_action, menu_actions)
        self.content_layout.addWidget(split_button)
        return split_button

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_vertical_group(self, actions):
        v_widget = QWidget()
        v_layout = QVBoxLayout(v_widget)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)
        for action in actions:
            btn = RibbonButton(action, is_large=False)
            v_layout.addWidget(btn)
        v_layout.addStretch()
        self.content_layout.addWidget(v_widget)
        return v_widget

    def add_separator(self):
        separator = QFrame()
        separator.setFrameStyle(QFrame.VLine | QFrame.Sunken)
        separator.setStyleSheet(f"color: {COLOR_BORDER_LIGHT}; margin: 4px 2px;")
        separator.setMaximumWidth(2)
        self.content_layout.addWidget(separator)

class RibbonComboGroup(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(3)
        layout.addLayout(self.content_layout)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLOR_TEXT_SECONDARY}; 
                font-size: 7pt; 
                padding: 2px 0px;
                border-top: 1px solid {COLOR_BORDER_LIGHT};
                margin-top: 2px;
            }}
        """)
        layout.addWidget(title_label)
        self.setMinimumHeight(88)
        self.setMaximumHeight(88)

    def add_combo(self, items, current_text=None):
        combo = QComboBox()
        combo.addItems(items)
        if current_text:
            combo.setCurrentText(current_text)
        combo.setMinimumWidth(100)
        combo.setMaximumHeight(22)
        self.content_layout.addWidget(combo)
        return combo

    def add_line_edit(self, placeholder=""):
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumWidth(100)
        edit.setMaximumHeight(22)
        self.content_layout.addWidget(edit)
        return edit

class RibbonTab(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 2, 8, 2)
        self.layout.setSpacing(6)
        self.layout.addStretch()

    def add_group(self, group):
        self.layout.insertWidget(self.layout.count() - 1, group)
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet(f"color: {COLOR_BORDER_LIGHT}; margin: 8px 0px; max-width: 1px;")
        self.layout.insertWidget(self.layout.count() - 1, separator)

class ModernRibbon(QWidget):
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

        # Tab bar
        self.tab_bar = QWidget()
        self.tab_bar.setFixedHeight(28)
        self.tab_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND_MEDIUM};
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            }}
        """)
        self.tab_layout = QHBoxLayout(self.tab_bar)
        self.tab_layout.setContentsMargins(8, 0, 8, 0)
        self.tab_layout.setSpacing(0)

        # File button
        self.file_button = QToolButton()
        self.file_button.setText("File")
        self.file_button.setCheckable(True)
        self.file_button.setPopupMode(QToolButton.InstantPopup)
        self.file_button.setFixedSize(50, 26)
        self.file_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLOR_ACCENT_PRIMARY}; 
                color: {COLOR_TEXT_ON_ACCENT};
                border: none; 
                border-radius: 2px;
                padding: 0px;
                font-weight: 600;
                font-size: 8pt;
            }}
            QToolButton:hover {{ 
                background-color: {QColor(COLOR_ACCENT_PRIMARY).lighter(110).name()}; 
            }}
            QToolButton:pressed, QToolButton:checked {{ 
                background-color: {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
            }}
        """)
        self.file_button.clicked.connect(self.on_file_button_clicked)
        self.tab_layout.addWidget(self.file_button)
        self.tab_layout.addSpacing(8)

        # Tab buttons container
        self.tab_buttons_container = QWidget()
        self.tab_buttons_layout = QHBoxLayout(self.tab_buttons_container)
        self.tab_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_buttons_layout.setSpacing(0)
        self.tab_layout.addWidget(self.tab_buttons_container)

        self.tab_button_group = QButtonGroup(self)
        self.tab_button_group.setExclusive(True)
        self.tab_button_group.buttonClicked.connect(self.on_tab_clicked)

        # Search bar
        self.search_bar = QLineEdit() # Made this an instance attribute
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setFixedSize(120, 20)
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 10px;
                padding: 0px 8px;
                font-size: 8pt;
            }}
        """)
        self.tab_layout.addStretch()
        self.tab_layout.addWidget(self.search_bar)

        main_layout.addWidget(self.tab_bar)

        # Content area
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setFixedHeight(102)
        self.content_area.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {COLOR_BACKGROUND_LIGHT}, 
                    stop: 1 {QColor(COLOR_BACKGROUND_LIGHT).darker(103).name()});
            }}
        """)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content_area)

    def create_tab_button(self, text):
        button = QPushButton(text)
        button.setCheckable(True)
        button.setFixedHeight(26)
        button.setMinimumWidth(len(text) * 8 + 20)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border: 1px solid transparent; 
                border-bottom: none;
                padding: 0px 12px; 
                color: {COLOR_TEXT_PRIMARY}; 
                font-weight: 400;
                font-size: 8pt;
                border-radius: 0px;
            }}
            QPushButton:hover {{ 
                background-color: {COLOR_ACCENT_PRIMARY_LIGHT}; 
                border-top: 1px solid {COLOR_BORDER_LIGHT};
                border-left: 1px solid {COLOR_BORDER_LIGHT};
                border-right: 1px solid {COLOR_BORDER_LIGHT};
            }}
            QPushButton:checked {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                border-top: 2px solid {COLOR_ACCENT_PRIMARY};
                border-left: 1px solid {COLOR_BORDER_LIGHT};
                border-right: 1px solid {COLOR_BORDER_LIGHT};
                border-bottom: 1px solid {COLOR_BACKGROUND_LIGHT};
                font-weight: 500;
            }}
        """)
        return button

    def add_tab(self, name):
        tab_widget = RibbonTab(name, self)
        button = self.create_tab_button(name)
        self.tab_button_group.addButton(button)
        self.tab_buttons_layout.addWidget(button)
        self.tabs[button] = tab_widget
        return tab_widget

    def on_file_button_clicked(self):
        if btn := self.tab_button_group.checkedButton():
            self.tab_button_group.setExclusive(False)
            btn.setChecked(False)
            self.tab_button_group.setExclusive(True)
        if self.current_tab_widget:
            self.current_tab_widget.hide()

    def on_tab_clicked(self, button):
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
        self.file_button.setMenu(menu)
        menu.aboutToHide.connect(lambda: self.file_button.setChecked(False))

    def select_first_tab(self):
        if self.tab_button_group.buttons():
            self.tab_button_group.buttons()[0].click()