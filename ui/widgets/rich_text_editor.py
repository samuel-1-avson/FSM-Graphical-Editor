# fsm_designer_project/ui/widgets/rich_text_editor.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QToolBar, QAction
from PyQt5.QtGui import QIcon, QFont # Import QFont
from PyQt5.QtCore import Qt, QSize
from ...utils import get_standard_icon
from PyQt5.QtWidgets import QStyle

class RichTextEditor(QWidget):
    def __init__(self, initial_html="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = QToolBar("Formatting")
        self.toolbar.setIconSize(QSize(16, 16))
        layout.addWidget(self.toolbar)

        self.text_edit = QTextEdit()
        self.text_edit.setHtml(initial_html)
        layout.addWidget(self.text_edit)

        self._create_actions()

    def _create_actions(self):
        bold_action = self.toolbar.addAction(get_standard_icon(QStyle.SP_DialogApplyButton, "B"), "Bold")
        bold_action.setCheckable(True)
        bold_action.triggered.connect(lambda c: self.text_edit.setFontWeight(QFont.Bold if c else QFont.Normal))

        italic_action = self.toolbar.addAction(get_standard_icon(QStyle.SP_DialogApplyButton, "I"), "Italic")
        italic_action.setCheckable(True)
        italic_action.triggered.connect(self.text_edit.setFontItalic)
        
        underline_action = self.toolbar.addAction(get_standard_icon(QStyle.SP_DialogApplyButton, "U"), "Underline")
        underline_action.setCheckable(True)
        underline_action.triggered.connect(self.text_edit.setFontUnderline)

        self.toolbar.addSeparator()

        bullet_list_action = self.toolbar.addAction(get_standard_icon(QStyle.SP_DialogApplyButton, "UL"), "Bullet List")
        bullet_list_action.triggered.connect(self._insert_bullet_list)

        # Connect text edit's state to update toolbar buttons
        self.text_edit.currentCharFormatChanged.connect(lambda f: bold_action.setChecked(f.fontWeight() > QFont.Normal))
        self.text_edit.currentCharFormatChanged.connect(lambda f: italic_action.setChecked(f.fontItalic()))
        self.text_edit.currentCharFormatChanged.connect(lambda f: underline_action.setChecked(f.fontUnderline()))

    def _insert_bullet_list(self):
        cursor = self.text_edit.textCursor()
        cursor.insertList(Qt.ListDisc)

    def toHtml(self):
        return self.text_edit.toHtml()

    def setFocus(self, reason=Qt.OtherFocusReason):
        self.text_edit.setFocus(reason)