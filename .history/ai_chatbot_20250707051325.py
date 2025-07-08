# fsm_designer_project/ai_chatbot.py

from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTime, QTimer, Qt, QMetaObject, pyqtSlot, Q_ARG, QSize, QUrl
import json
import re
import logging
from enum import Enum, auto
import html
import uuid
from typing import Dict, List, Tuple

# --- NEW: Import the provider system ---
from .ai_providers import get_provider_by_name, AIProvider

from PyQt5.QtGui import QIcon, QColor, QDesktopServices
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextBrowser, QHBoxLayout, QLineEdit,
                             QPushButton, QLabel, QStyle, QMessageBox, QInputDialog, QAction, QApplication,
                             QDialog, QDialogButtonBox, QTextEdit)

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from .config import (
    APP_FONT_SIZE_SMALL, COLOR_BACKGROUND_MEDIUM, COLOR_ACCENT_WARNING,
    COLOR_ACCENT_PRIMARY, COLOR_ACCENT_SECONDARY, COLOR_TEXT_PRIMARY,
    COLOR_ACCENT_ERROR, COLOR_TEXT_SECONDARY, COLOR_BACKGROUND_EDITOR_DARK,
    COLOR_TEXT_EDITOR_DARK_PRIMARY, COLOR_BORDER_LIGHT, COLOR_TEXT_ON_ACCENT,
    COLOR_ACCENT_SUCCESS, COLOR_BACKGROUND_DIALOG, COLOR_BORDER_MEDIUM
)
from .utils import get_standard_icon

logger = logging.getLogger(__name__)

class AIStatus(Enum):
    INITIALIZING = auto()
    READY = auto()
    THINKING = auto()
    API_KEY_REQUIRED = auto()
    API_KEY_ERROR = auto()
    OFFLINE = auto()
    ERROR = auto()
    INACTIVE = auto()
    HISTORY_CLEARED = auto()
    CONTENT_BLOCKED = auto()
    RATE_LIMIT = auto()
    CONNECTION_ERROR = auto()
    AUTHENTICATION_ERROR = auto()
    PROVIDER_NOT_SET = auto()

class ChatbotWorker(QObject):
    """
    A generic worker for executing AI provider requests in a background thread.
    It is provider-agnostic and receives a configured provider instance.
    """
    responseReady = pyqtSignal(str)
    errorOccurred = pyqtSignal(AIStatus, str)
    statusUpdate = pyqtSignal(AIStatus, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.provider: AIProvider | None = None
        self._is_stopped = False
        logger.info("ChatbotWorker initialized (Generic).")

    @pyqtSlot(object)
    def set_provider_slot(self, provider_instance: AIProvider):
        """Receives the configured AI provider instance from the manager."""
        self.provider = provider_instance
        provider_name = self.provider.get_name() if self.provider else "None"
        logger.info(f"WORKER: Provider set to: {provider_name}")

        if self.provider and self.provider.is_configured():
            self.statusUpdate.emit(AIStatus.READY, f"Status: AI Assistant ready ({provider_name}).")
        elif not self.provider:
            self.statusUpdate.emit(AIStatus.PROVIDER_NOT_SET, "Status: No AI Provider set.")
        else:
            self.statusUpdate.emit(AIStatus.API_KEY_REQUIRED, "Status: API Key required.")

    @pyqtSlot(list, bool)
    def process_message_slot(self, conversation_history: List[Dict], is_json_mode: bool):
        """Processes a request using the currently configured provider."""
        if self._is_stopped:
            logger.info("WORKER_PROCESS: Worker is stopped, ignoring message.")
            return

        if not self.provider or not self.provider.is_configured():
            msg = "AI provider not configured. Please set the provider and API key in settings."
            self.errorOccurred.emit(AIStatus.PROVIDER_NOT_SET, msg)
            return

        provider_name = self.provider.get_name()
        self.statusUpdate.emit(AIStatus.THINKING, f"Status: Thinking ({provider_name})...")

        try:
            ai_response_content = self.provider.generate_response(conversation_history, is_json_mode)

            if self._is_stopped:
                return

            self.responseReady.emit(ai_response_content)
            self.statusUpdate.emit(AIStatus.READY, f"Status: Ready ({provider_name}).")

        except PermissionError as e:
            self.errorOccurred.emit(AIStatus.AUTHENTICATION_ERROR, str(e))
            self.statusUpdate.emit(AIStatus.API_KEY_ERROR, "Status: API Key or Permission Error.")
        except ConnectionAbortedError as e:
            self.errorOccurred.emit(AIStatus.RATE_LIMIT, str(e))
            self.statusUpdate.emit(AIStatus.ERROR, "Status: Rate Limit Exceeded.")
        except ConnectionRefusedError as e:
            self.errorOccurred.emit(AIStatus.CONNECTION_ERROR, str(e))
            self.statusUpdate.emit(AIStatus.OFFLINE, "Status: Connection Error.")
        except ValueError as e:  # For content blocking or other value errors from providers
            self.errorOccurred.emit(AIStatus.CONTENT_BLOCKED, str(e))
            self.statusUpdate.emit(AIStatus.ERROR, "Status: Content Generation Error.")
        except Exception as e:
            err_msg = f"Unexpected error from '{provider_name}': {e}"
            self.errorOccurred.emit(AIStatus.ERROR, err_msg)
            self.statusUpdate.emit(AIStatus.ERROR, "Status: Unexpected Provider Error.")

    @pyqtSlot()
    def stop_processing_slot(self):
        logger.info("WORKER: stop_processing_slot called.")
        self._is_stopped = True


class AIChatUIManager(QObject):
    inlineResponseReady = pyqtSignal(str, str, str)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.mw = main_window

        self.ai_chat_display: QTextBrowser = None
        self.ai_chat_input: QLineEdit = None
        self.ai_chat_send_button: QPushButton = None
        self.ai_chat_status_label: QLabel = None
        self.original_send_button_icon: QIcon = None

        self._code_snippet_cache: Dict[str, str] = {}
        self._last_copy_feedback_timer: QTimer | None = None
        self._pending_status_update: tuple[AIStatus, str] | None = None
        self._original_status_text: str = ""
        self._original_status_stylesheet: str = ""
        self._inline_request_targets: Dict[str, QWidget] = {}
        self.md_parser = MarkdownIt("commonmark", {"breaks": True, "html": False})

        self._connect_actions_to_manager_slots()
        self._connect_ai_chatbot_signals()

    def _connect_actions_to_manager_slots(self):
        settings_action = getattr(self.mw, 'openai_settings_action', None)
        if settings_action and isinstance(settings_action, QAction):
            try:
                settings_action.triggered.disconnect()
            except TypeError:
                pass
            settings_action.triggered.connect(self.on_ai_settings)
        else:
            logger.error("AIChatUIManager: CRITICAL - 'openai_settings_action' NOT FOUND on MainWindow.")

        ask_fsm_action = getattr(self.mw, 'ask_ai_to_generate_fsm_action', None)
        if ask_fsm_action and isinstance(ask_fsm_action, QAction):
            try:
                ask_fsm_action.triggered.disconnect(self.on_ask_ai_to_generate_fsm)
            except TypeError:
                pass
            ask_fsm_action.triggered.connect(self.on_ask_ai_to_generate_fsm)
        else:
            logger.error("AIChatUIManager: Could not find 'ask_ai_to_generate_fsm_action'.")

        clear_chat_action = getattr(self.mw, 'clear_ai_chat_action', None)
        if clear_chat_action and isinstance(clear_chat_action, QAction):
            try:
                clear_chat_action.triggered.disconnect(self.on_clear_ai_chat_history)
            except TypeError:
                pass
            clear_chat_action.triggered.connect(self.on_clear_ai_chat_history)
        else:
            logger.error("AIChatUIManager: Could not find 'clear_ai_chat_action'.")

    def _connect_ai_chatbot_signals(self):
        if self.mw.ai_chatbot_manager:
            self.mw.ai_chatbot_manager.statusUpdate.connect(self.update_status_display)
            self.mw.ai_chatbot_manager.errorOccurred.connect(self.handle_ai_error)
            self.mw.ai_chatbot_manager.fsmDataReceived.connect(self.handle_fsm_data_from_ai)
            self.mw.ai_chatbot_manager.plainResponseReady.connect(self.handle_plain_ai_response)
            self.mw.ai_chatbot_manager.inlineResponseReady.connect(self.handle_inline_ai_response)

    def create_dock_widget_contents(self) -> QWidget:
        ai_chat_widget = QWidget()
        ai_chat_layout = QVBoxLayout(ai_chat_widget)
        ai_chat_layout.setContentsMargins(4,4,4,4)
        ai_chat_layout.setSpacing(4)

        self.ai_chat_display = QTextBrowser()
        self.ai_chat_display.setReadOnly(True)
        self.ai_chat_display.setAcceptRichText(True)
        self.ai_chat_display.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.TextSelectableByKeyboard)
        self.ai_chat_display.setOpenLinks(False)
        self.ai_chat_display.setObjectName("AIChatDisplay")
        self.ai_chat_display.setPlaceholderText("AI chat history will appear here...")
        self.ai_chat_display.anchorClicked.connect(self.on_chat_anchor_clicked)
        ai_chat_layout.addWidget(self.ai_chat_display, 1)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)
        self.ai_chat_input = QLineEdit()
        self.ai_chat_input.setObjectName("AIChatInput")
        self.ai_chat_input.setPlaceholderText("Type your message to the AI...")
        self.ai_chat_input.returnPressed.connect(self.on_send_ai_chat_message)
        input_layout.addWidget(self.ai_chat_input, 1)

        self.ai_chat_send_button = QPushButton()
        self.original_send_button_icon = get_standard_icon(QStyle.SP_ArrowRight, "SndAI")
        self.ai_chat_send_button.setIcon(self.original_send_button_icon)
        self.ai_chat_send_button.setIconSize(QSize(16,16))
        self.ai_chat_send_button.setObjectName("AIChatSendButton")
        self.ai_chat_send_button.setToolTip("Send message to AI")
        self.ai_chat_send_button.setFixedWidth(32)
        self.ai_chat_send_button.clicked.connect(self.on_send_ai_chat_message)
        input_layout.addWidget(self.ai_chat_send_button)
        ai_chat_layout.addLayout(input_layout)

        self.ai_chat_status_label = QLabel("Status: Initializing...")
        self.ai_chat_status_label.setObjectName("AIChatStatusLabel")
        ai_chat_layout.addWidget(self.ai_chat_status_label)

        return ai_chat_widget

    @pyqtSlot(AIStatus, str)
    def update_status_display(self, status_enum: AIStatus, status_text: str):
        if not self.ai_chat_status_label: return

        if self._last_copy_feedback_timer and self._last_copy_feedback_timer.isActive():
            self._pending_status_update = (status_enum, status_text)
            return
        self._pending_status_update = None

        self.ai_chat_status_label.setText(status_text)
        base_style = f"font-size: {APP_FONT_SIZE_SMALL}; padding: 1px 3px; border-radius: 2px;"
        can_send_message = False
        is_thinking_ui = False

        if status_enum in [AIStatus.PROVIDER_NOT_SET, AIStatus.API_KEY_REQUIRED, AIStatus.API_KEY_ERROR, AIStatus.INACTIVE, AIStatus.AUTHENTICATION_ERROR]:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: white; background-color: {COLOR_ACCENT_ERROR}; font-weight: bold;")
        elif status_enum == AIStatus.OFFLINE or status_enum == AIStatus.CONNECTION_ERROR:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {COLOR_TEXT_PRIMARY}; background-color: {COLOR_ACCENT_WARNING};")
        elif status_enum in [AIStatus.ERROR, AIStatus.CONTENT_BLOCKED, AIStatus.RATE_LIMIT]:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: white; background-color: {COLOR_ACCENT_ERROR}; font-weight: bold;")
        elif status_enum == AIStatus.THINKING or status_enum == AIStatus.INITIALIZING:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {COLOR_TEXT_PRIMARY}; background-color: {QColor(COLOR_ACCENT_SECONDARY).lighter(130).name()}; font-style: italic;")
            is_thinking_ui = True
        elif status_enum == AIStatus.READY:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: white; background-color: {COLOR_ACCENT_SUCCESS};")
            can_send_message = True
        elif status_enum == AIStatus.HISTORY_CLEARED:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {COLOR_TEXT_SECONDARY}; background-color: {QColor(COLOR_BACKGROUND_MEDIUM).lighter(105).name()};")
            if self.mw.ai_chatbot_manager and self.mw.ai_chatbot_manager.get_current_ai_status() == AIStatus.READY:
                 can_send_message = True
        else:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {COLOR_TEXT_SECONDARY}; background-color: {COLOR_BACKGROUND_MEDIUM};")

        if self.ai_chat_send_button:
            self.ai_chat_send_button.setEnabled(can_send_message)
            if is_thinking_ui:
                self.ai_chat_send_button.setText("...")
                self.ai_chat_send_button.setIcon(QIcon())
            else:
                self.ai_chat_send_button.setText("")
                self.ai_chat_send_button.setIcon(self.original_send_button_icon)

        if self.ai_chat_input:
            self.ai_chat_input.setEnabled(can_send_message)
            if can_send_message and self.mw and hasattr(self.mw, 'ai_chatbot_dock') and self.mw.ai_chatbot_dock and self.mw.ai_chatbot_dock.isVisible() and self.mw.isActiveWindow():
                self.ai_chat_input.setFocus()

        if hasattr(self.mw, 'ask_ai_to_generate_fsm_action'):
            self.mw.ask_ai_to_generate_fsm_action.setEnabled(can_send_message)

    def _format_code_block(self, code_content: str, language: str = "") -> str:
        bg_color = COLOR_BACKGROUND_EDITOR_DARK
        text_color = COLOR_TEXT_EDITOR_DARK_PRIMARY
        border_color = QColor(bg_color).lighter(130).name()

        code_id = str(uuid.uuid4())
        self._code_snippet_cache[code_id] = code_content

        lang_display = f"<span style='color: {COLOR_TEXT_SECONDARY}; font-size: 7pt; margin-bottom: 3px; display: block;'>{html.escape(language)}</span>" if language else ""

        copy_button_bg_color = QColor(COLOR_BACKGROUND_DIALOG).lighter(105 if QColor(COLOR_BACKGROUND_DIALOG).lightnessF() > 0.5 else 115).name()
        copy_button_text_color = COLOR_TEXT_PRIMARY
        copy_button_border_color = COLOR_BORDER_MEDIUM

        copy_button_html = (
            f'<a href="copycode:{code_id}" '
            f'style="float:right; margin-left:8px; margin-top:-2px; padding:1px 5px; font-size:7.5pt; text-decoration:none; '
            f'background-color:{copy_button_bg_color}; color:{copy_button_text_color}; '
            f'border:1px solid {copy_button_border_color}; border-radius:3px;" '
            f'title="Copy code to clipboard"> Copy</a>'
        )

        escaped_code = html.escape(code_content)
        return (f'<div style="position:relative; margin: 8px 0; padding: 10px; background-color:{bg_color}; color:{text_color}; '
                f'border:1px solid {border_color}; border-radius:4px; font-family: Consolas, monospace; white-space:pre-wrap; overflow-x:auto;">'
                f'{copy_button_html}'
                f'{lang_display}'
                f'<div style="clear:both;"></div>'
                f'{escaped_code}</div>')
                
    def _render_tokens_to_styled_html(self, tokens: list[SyntaxTreeNode]) -> str:
        """Renders a token stream from markdown-it to styled HTML suitable for QTextBrowser."""
        inline_code_style = f"background-color:{QColor(COLOR_BACKGROUND_MEDIUM).lighter(105).name()}; color:{COLOR_ACCENT_PRIMARY}; padding:1px 4px; border-radius:3px; font-family:Consolas,monospace; font-size: 0.9em;"
        blockquote_style = f"border-left: 2px solid {COLOR_BORDER_MEDIUM}; margin-left: 5px; padding-left: 10px; color: {COLOR_TEXT_SECONDARY}; font-style: italic;"
        
        # --- FIX for BUG-03: Refactor rendering to use markdown-it token stream ---
        original_fence_renderer = self.md_parser.renderer.rules.get("fence")
        original_code_inline_renderer = self.md_parser.renderer.rules.get("code_inline")
        original_blockquote_open_renderer = self.md_parser.renderer.rules.get("blockquote_open")
        
        def render_fence(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            token = tokens_list[idx]
            lang = token.info.strip().split(" ")[0] if token.info else ""
            return self._format_code_block(token.content, lang)
        
        def render_code_inline(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            return f'<code style="{inline_code_style}">{html.escape(tokens_list[idx].content)}</code>'
        
        def render_blockquote_open(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            return f'<blockquote style="{blockquote_style}">'
            
        self.md_parser.renderer.rules["fence"] = render_fence
        self.md_parser.renderer.rules["code_inline"] = render_code_inline
        self.md_parser.renderer.rules["blockquote_open"] = render_blockquote_open

        rendered_html = self.md_parser.renderer.render(tokens, self.md_parser.options, {})
        
        if original_fence_renderer: self.md_parser.renderer.rules["fence"] = original_fence_renderer
        if original_code_inline_renderer: self.md_parser.renderer.rules["code_inline"] = original_code_inline_renderer
        if original_blockquote_open_renderer: self.md_parser.renderer.rules["blockquote_open"] = original_blockquote_open_renderer

        return rendered_html

    def _append_to_chat_display(self, sender: str, message: str):
        if not self.ai_chat_display: return
        timestamp = QTime.currentTime().toString('hh:mm:ss')

        sender_color = COLOR_ACCENT_PRIMARY
        sender_name_raw = sender
        if sender == "You": sender_color = COLOR_ACCENT_SECONDARY
        elif sender == "System Error": sender_color = COLOR_ACCENT_ERROR; sender_name_raw = f"<b>{html.escape(sender)}</b>"
        elif sender == "System": sender_color = QColor(COLOR_TEXT_SECONDARY)
        elif sender in ["Diagram", "Validation Helper", "IDE", "You (Inline Request)"]:
            sender_color = QColor(COLOR_ACCENT_SUCCESS).darker(110)

        sender_color_str = sender_color.name() if isinstance(sender_color, QColor) else sender_color
        sender_name_html = sender_name_raw if sender in ["System Error"] else html.escape(sender)

        tokens = self.md_parser.parse(message)
        final_message_html = self._render_tokens_to_styled_html(tokens)

        bg_msg_color = QColor(sender_color_str).lighter(185).name()
        if sender == "System Error": bg_msg_color = QColor(COLOR_ACCENT_ERROR).lighter(180).name()
        elif sender == "System": bg_msg_color = QColor(COLOR_BACKGROUND_MEDIUM).lighter(105).name()
        elif sender in ["Diagram", "Validation Helper", "IDE", "You (Inline Request)"]: bg_msg_color = QColor(sender_color_str).lighter(190).name()

        html_to_append = (f"<div style='margin-bottom: 10px; padding: 6px 8px; border-left: 3px solid {sender_color_str}; background-color: {bg_msg_color}; border-radius: 4px;'>"
                          f"<div style='margin-bottom: 3px;'>"
                          f"<strong style='color:{sender_color_str}; font-size: 9pt;'>{sender_name_html}</strong>"
                          f"<span style='font-size:7pt; color:{COLOR_TEXT_SECONDARY}; margin-left: 6px;'>[{timestamp}]</span> "
                          f"</div>"
                          f"<div style='padding-left: 2px; line-height:1.4; font-size: 9pt;'>{final_message_html}</div></div>")

        self.ai_chat_display.append(html_to_append)
        self.ai_chat_display.ensureCursorVisible()

    @pyqtSlot()
    def on_ai_settings(self):
        """Handle the AI settings action, now using the generic dialog."""
        logger.info("AIChatUI: SLOT on_ai_settings CALLED!")
        if not self.mw.ai_chatbot_manager or not self.mw.settings_manager:
            QMessageBox.warning(self.mw, "AI Error", "AI or Settings Manager is not initialized.")
            return

        from .dialogs import AiSettingsDialog
        dialog = AiSettingsDialog(self.mw.settings_manager, self.mw)

        if dialog.exec_():
            provider_name, api_key = dialog.get_settings()
            logger.info(f"AIChatUI: AI Settings dialog accepted. Provider: '{provider_name}', Key: {'SET' if api_key else 'EMPTY'}")

            # Save the globally selected provider name
            self.mw.settings_manager.set("ai_provider_name", provider_name)
            
            # Save the specific key for that provider
            # The key name is derived from the provider name for namespacing
            setting_key = f"ai_{provider_name.split(' ')[0].lower()}_api_key"
            self.mw.settings_manager.set(setting_key, api_key)

            # Reconfigure the chatbot manager with the new settings
            self.mw.ai_chatbot_manager.configure_provider(provider_name, api_key)

    @pyqtSlot(QUrl)
    def on_chat_anchor_clicked(self, url: QUrl):
        if url.scheme() == 'copycode':
            code_id = url.path()
            if code_id in self._code_snippet_cache:
                code_to_copy = self._code_snippet_cache[code_id]
                clipboard = QApplication.clipboard()
                clipboard.setText(code_to_copy)
                logger.info(f"Copied code snippet (ID: {code_id}) to clipboard.")
                if self.ai_chat_status_label:
                    if self._last_copy_feedback_timer and self._last_copy_feedback_timer.isActive():
                        self._last_copy_feedback_timer.stop()
                    else:
                        self._original_status_text = self.ai_chat_status_label.text()
                        self._original_status_stylesheet = self.ai_chat_status_label.styleSheet()
                    self.ai_chat_status_label.setText("Status: Code copied to clipboard!")
                    self.ai_chat_status_label.setStyleSheet(f"font-size: {APP_FONT_SIZE_SMALL}; padding: 1px 3px; border-radius: 2px; color: {COLOR_TEXT_ON_ACCENT}; background-color: {COLOR_ACCENT_SUCCESS}; font-weight:bold;")
                    self._last_copy_feedback_timer = QTimer(self)
                    self._last_copy_feedback_timer.setSingleShot(True)
                    def revert_status():
                        if hasattr(self, '_pending_status_update') and self._pending_status_update:
                            pending_enum, pending_text = self._pending_status_update
                            self._pending_status_update = None
                            self.update_status_display(pending_enum, pending_text)
                        elif hasattr(self, '_original_status_text'):
                            self.ai_chat_status_label.setText(self._original_status_text)
                            self.ai_chat_status_label.setStyleSheet(self._original_status_stylesheet)
                        elif self.mw.ai_chatbot_manager and self.mw.ai_chatbot_manager.get_current_ai_status() == AIStatus.READY:
                             self.update_status_display(AIStatus.READY, "Status: Ready.")
                    self._last_copy_feedback_timer.timeout.connect(revert_status)
                    self._last_copy_feedback_timer.start(2000)
            else:
                logger.warning(f"Could not find code snippet for ID: {code_id}")
        elif url.scheme() in ['http', 'https', 'file']:
            QDesktopServices.openUrl(url)

    @pyqtSlot(AIStatus, str)
    def handle_ai_error(self, error_status_enum: AIStatus, error_message: str):
        self._append_to_chat_display("System Error", error_message)
        logger.error("AIChatUI: AI Chatbot Error (%s): %s", error_status_enum.name, error_message)

    @pyqtSlot(dict, str)
    def handle_fsm_data_from_ai(self, fsm_data: dict, source_message: str):
        logger.info("AIChatUI: Received FSM data. Source: '%s...'", source_message[:30])
        self._append_to_chat_display("AI", f"Received FSM structure. (Source: {source_message[:30]}...) Adding to diagram.")
        if not fsm_data or (not fsm_data.get('states') and not fsm_data.get('transitions')):
            logger.error("AIChatUI: AI returned empty or invalid FSM data.")
            self._append_to_chat_display("System", "AI did not return a valid FSM structure to draw.")
            if self.mw.ai_chatbot_manager:
                 self.mw.ai_chatbot_manager._update_current_ai_status(AIStatus.ERROR, "Status: AI returned no FSM data.")
            return

        msg_box = QMessageBox(self.mw)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Add AI Generated FSM")
        msg_box.setText("AI has generated an FSM. Do you want to clear the current diagram before adding the new FSM, or add to the existing one?")
        clear_btn = msg_box.addButton("Clear and Add", QMessageBox.YesRole)
        add_btn = msg_box.addButton("Add to Existing", QMessageBox.NoRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        msg_box.setDefaultButton(cancel_btn)
        msg_box.exec_()

        clicked_button = msg_box.clickedButton()
        if clicked_button == cancel_btn:
            logger.info("AIChatUI: User cancelled adding AI FSM.")
            if self.mw.ai_chatbot_manager:
                self.mw.ai_chatbot_manager._update_current_ai_status(AIStatus.READY, "Status: FSM generation cancelled.")
            return

        clear_current = (clicked_button == clear_btn)
        self.mw._add_fsm_data_to_scene(fsm_data, clear_current_diagram=clear_current, original_user_prompt=source_message)
        logger.info("AIChatUI: FSM data from AI processed and added to scene.")

    @pyqtSlot(str)
    def handle_plain_ai_response(self, ai_message: str):
        logger.info("AIChatUI: Received plain AI response.")
        self._append_to_chat_display("AI", ai_message)

    @pyqtSlot(str, str, str)
    def handle_inline_ai_response(self, code_snippet: str, source_prompt: str, request_id: str):
        logger.info(f"AIChatUI: Received INLINE AI response for prompt: '{source_prompt[:40]}...'")
        self._append_to_chat_display("You (Inline Request)", source_prompt)
        self._append_to_chat_display("AI", code_snippet)
        target_widget = self._inline_request_targets.pop(request_id, None)

        if target_widget and isinstance(target_widget, (QTextEdit, QLineEdit)):
            logger.info(f"Injecting AI-generated code directly into widget: {target_widget.objectName()}")
            code_match = re.search(r"```(?:\w+\n)?(.*?)\n?```", code_snippet, re.DOTALL)
            code_to_insert = code_match.group(1).strip() if code_match else code_snippet.strip()
            target_widget.insertPlainText(code_to_insert)
            dialog = target_widget.parent()
            while dialog and not isinstance(dialog, QDialog):
                dialog = dialog.parent()
            if dialog:
                dialog.raise_()
                dialog.activateWindow()
        else:
            logger.warning(f"Could not find target widget for inline request ID '{request_id}'. Falling back to message box.")
            QMessageBox.information(
                self.mw, "AI Code Generated",
                "The AI has generated the requested code snippet.\n\n"
                "It has been added to the main AI Chat window. Use the 'Copy' button to paste it into the appropriate field."
            )
        
        if hasattr(self.mw, 'ai_chatbot_dock'):
            self.mw.ai_chatbot_dock.setVisible(True)
            self.mw.ai_chatbot_dock.raise_()

    @pyqtSlot()
    def on_send_ai_chat_message(self):
        if not self.ai_chat_input or not self.ai_chat_send_button.isEnabled(): return
        message = self.ai_chat_input.text().strip()
        if not message: return
        self.ai_chat_input.clear()
        self._append_to_chat_display("You", message)
        if self.mw.ai_chatbot_manager:
            self.mw.ai_chatbot_manager.send_message(message)
        else:
            self.handle_ai_error(AIStatus.ERROR, "AI Chatbot Manager not initialized.")

    @pyqtSlot()
    def on_ask_ai_to_generate_fsm(self):
        logger.info("AIChatUI: on_ask_ai_to_generate_fsm CALLED!")
        description, ok = QInputDialog.getMultiLineText(self.mw, "Generate FSM", "Describe the FSM you want to create:", "Example: A traffic light with states Red, Yellow, Green...")
        if ok and description.strip():
            logger.info("AIChatUI: Sending FSM desc: '%s...'", description[:50])
            if self.mw.ai_chatbot_manager:
                self.mw.ai_chatbot_manager.generate_fsm_from_description(description)
                self._append_to_chat_display("You", f"Generate an FSM: {description}")
            else:
                self.handle_ai_error(AIStatus.ERROR, "AI Chatbot Manager not initialized.")
        elif ok: QMessageBox.warning(self.mw, "Empty Description", "Please provide a description for the FSM.")

    @pyqtSlot()
    def on_clear_ai_chat_history(self):
        logger.info("AIChatUI: on_clear_ai_chat_history CALLED!")
        if self.mw.ai_chatbot_manager:
            reply = QMessageBox.question(self.mw, "Clear Chat History", "Are you sure you want to clear the entire AI chat history?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.mw.ai_chatbot_manager.clear_conversation_history()
                if self.ai_chat_display:
                    self.ai_chat_display.clear()
                    self.ai_chat_display.setPlaceholderText("AI chat history will appear here...")
                logger.info("AIChatUI: Chat history cleared by user.")
                self._append_to_chat_display("System", "Chat history cleared.")
                self._code_snippet_cache.clear()
        else:
            self.handle_ai_error(AIStatus.ERROR, "AI Chatbot Manager not initialized.")
            
    def handle_inline_ai_request(self, prompt: str, language: str, target_widget: QWidget = None):
        """Sends a request to the AI manager specifically for an inline code snippet."""
        logger.info(f"AIChatUI: Handling INLINE AI request for language '{language}': '{prompt[:50]}...'")
        
        request_id = ""
        if target_widget:
            request_id = f"inline_req_{uuid.uuid4()}"
            self._inline_request_targets[request_id] = target_widget

        if self.mw.ai_chatbot_manager:
            self.mw.ai_chatbot_manager.generate_inline_code_snippet(prompt, request_id)
        else:
            self.handle_ai_error(AIStatus.ERROR, "AI Chatbot Manager not initialized for inline request.")