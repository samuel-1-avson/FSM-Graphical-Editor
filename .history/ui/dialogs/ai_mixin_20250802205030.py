# fsm_designer_project/ui/dialogs/ai_mixin.py
from PyQt5.QtWidgets import QWidget, QPushButton, QInputDialog, QMessageBox, QMainWindow, QStyle
from ...utils import get_standard_icon

class AiHelperMixin:
    """A mixin class to provide AI helper button functionality to dialogs."""
    
    def _create_ai_helper_button(self, target_widget, code_type="action"):
        button = QPushButton()
        button.setIcon(get_standard_icon(QStyle.SP_MessageBoxQuestion, "AI"))
        button.setToolTip(f"Generate {code_type} code with AI")
        button.clicked.connect(lambda: self._on_ai_helper_clicked(target_widget, code_type))
        return button

    def _on_ai_helper_clicked(self, target_widget, code_type):
        description, ok = QInputDialog.getText(self, f"Generate {code_type.capitalize()} Code", f"Describe the {code_type} you want to create:")
        if not (ok and description.strip()):
            return
        
        main_win = self.parent()
        while main_win and not isinstance(main_win, QMainWindow):
            main_win = main_win.parent()
        
        if not main_win or not hasattr(main_win, 'ai_chat_ui_manager'):
            QMessageBox.warning(self, "AI Not Available", "The AI assistant UI manager could not be found.")
            return
            
        language = self.action_language_combo.currentText()
        prompt = f"Generate a code snippet for this {code_type} in {language}: '{description}'. Respond with only the code, no explanations."
        
        main_win.ai_chat_ui_manager.handle_inline_ai_request(prompt, language, target_widget)