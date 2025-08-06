# fsm_designer_project/ui/widgets/rich_text_editor.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QToolBar
from PyQt6.QtGui import QIcon, QFont, QAction
from PyQt6.QtCore import Qt, QSize
from ...utils import get_standard_icon
from PyQt6.QtWidgets import QStyle

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
        bold_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton, "B"), "Bold", self)
        bold_action.setCheckable(True)
        bold_action.triggered.connect(lambda c: self.text_edit.setFontWeight(QFont.Weight.Bold if c else QFont.Weight.Normal))
        self.toolbar.addAction(bold_action)

        italic_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton, "I"), "Italic", self)
        italic_action.setCheckable(True)
        italic_action.triggered.connect(self.text_edit.setFontItalic)
        self.toolbar.addAction(italic_action)
        
        underline_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton, "U"), "Underline", self)
        underline_action.setCheckable(True)
        underline_action.triggered.connect(self.text_edit.setFontUnderline)
        self.toolbar.addAction(underline_action)

        self.toolbar.addSeparator()

        bullet_list_action = QAction(get_standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton, "UL"), "Bullet List", self)
        bullet_list_action.triggered.connect(self._insert_bullet_list)
        self.toolbar.addAction(bullet_list_action)

        # Connect text edit's state to update toolbar buttons
        self.text_edit.currentCharFormatChanged.connect(lambda f: bold_action.setChecked(f.fontWeight() > QFont.Weight.Normal))
        self.text_edit.currentCharFormatChanged.connect(lambda f: italic_action.setChecked(f.fontItalic()))
        self.text_edit.currentCharFormatChanged.connect(lambda f: underline_action.setChecked(f.fontUnderline()))

    def _insert_bullet_list(self):
        cursor = self.text_edit.textCursor()
        cursor.insertList(Qt.TextListFormat.Style.ListDisc)

    def toHtml(self):
        return self.text_edit.toHtml()

    def setFocus(self, reason=Qt.FocusReason.OtherFocusReason):
        self.text_edit.setFocus(reason)