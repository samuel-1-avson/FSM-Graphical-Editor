# fsm_designer_project/ui/ai/ai_chatbot.py
import sys
import os
import json
import re
import logging
from enum import Enum, auto
import html
import uuid
from typing import Dict, List, Tuple, Any

# --- NEW: Import the generic AI Provider and discovery function ---
from .ai_providers.base import AIProvider
from .ai_providers import get_available_providers

from PyQt6.QtGui import QMovie, QIcon, QColor, QDesktopServices, QAction
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextBrowser, QHBoxLayout, QLineEdit,
                             QPushButton, QLabel, QStyle, QMessageBox, QInputDialog, QApplication,
                             QDialog, QFormLayout, QDialogButtonBox, QGroupBox, QComboBox, QTextEdit, QCheckBox)

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from ...utils.theme_config import theme_config
from ...utils import config
from ...utils import get_standard_icon 
from ...managers.settings_manager import SettingsManager
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTime, QTimer, Qt, QMetaObject, pyqtSlot, Q_ARG, QSize, QUrl

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
    ACTION_PROPOSED = auto()
    AUTHENTICATION_ERROR = auto()
    AGENT_THINKING = auto()
    PROVIDER_NOT_SET = auto()

class ChatbotWorker(QObject):
    """
    Generic worker that processes messages using a configured AIProvider instance.
    """
    responseReady = pyqtSignal(str, bool)
    errorOccurred = pyqtSignal(AIStatus, str)
    statusUpdate = pyqtSignal(AIStatus, str)
    tool_call_request = pyqtSignal(str, str, dict) # message_id, tool_name, tool_args

    def __init__(self, parent=None):
        super().__init__(parent)
        self.provider: AIProvider | None = None
        self.conversation_history: List[Dict] = []
        self.current_diagram_context_json_str: str | None = None
        self._is_stopped = False
        self._is_agent_mode = False
        self._available_tools_json: str = ""
        logger.info("ChatbotWorker initialized (generic).")

    @pyqtSlot(AIProvider)
    def set_provider_slot(self, provider_instance: AIProvider):
        """Receives a configured AI provider instance from the manager."""
        self.provider = provider_instance
        if self.provider and self.provider.is_configured():
            self.statusUpdate.emit(AIStatus.READY, f"Status: Ready ({self.provider.get_name()}).")
        else:
            self.statusUpdate.emit(AIStatus.API_KEY_REQUIRED, "Status: AI Provider requires configuration.")

    @pyqtSlot(str)
    def set_diagram_context_slot(self, diagram_json_str: str):
        self.current_diagram_context_json_str = diagram_json_str if diagram_json_str else None

    @pyqtSlot(bool, str)
    def set_agent_mode_slot(self, is_agent_mode: bool, available_tools_json: str):
        self._is_agent_mode = is_agent_mode
        self._available_tools_json = available_tools_json


    def _prepare_system_prompt(self, user_message: str, force_fsm_generation: bool) -> Tuple[str, bool]:
        """Constructs the system prompt based on context and request type."""
        user_msg_lower = user_message.lower()
        is_fsm_generation_attempt = force_fsm_generation or any(
            re.search(r'\b' + re.escape(keyword) + r'\b', user_msg_lower)
            for keyword in ["generate fsm", "create fsm", "/generate_fsm"]
        )

        system_prompt_content = "You are a helpful assistant for designing Finite State Machines."

        # Add diagram context
        if self.current_diagram_context_json_str:
            try:
                diagram = json.loads(self.current_diagram_context_json_str)
                num_states = len(diagram.get("states", []))
                context_summary = f" The current diagram has {num_states} state(s)."
                system_prompt_content += context_summary
            except json.JSONDecodeError:
                system_prompt_content += " (Error reading diagram context)."
        else:
            system_prompt_content += " No diagram context was provided for this request."

        # Add instructions for FSM generation
        if is_fsm_generation_attempt:
            system_prompt_content += (
                " When asked to generate an FSM, you MUST respond with ONLY a valid JSON object. "
                "Do not include comments, explanations, or any other text outside the main JSON object."
            )
        elif self._is_agent_mode:
            system_prompt_content += (
                " You are now in Agent Mode. Your goal is to complete the user's task by calling available tools. "
                "Analyze the user's request and the current diagram. Formulate a plan. "
                "To call a tool, respond with ONLY a JSON object: "
                "{\"tool_name\": \"function_name\", \"tool_args\": {\"arg1\": \"value1\"}}. "
                f"The available tools are: {self._available_tools_json}"
            )
        else:
            # Instructions for conversational editing
            system_prompt_content += (
                " You can also edit the diagram. If the user asks to add, remove, or change something, "
                "respond with ONLY a JSON object like: "
                "{\"action\": \"add_state\", \"details\": {\"name\": \"MyNewState\"}} or "
                "{\"action\": \"add_transition\", \"details\": {\"source\": \"StateA\", \"target\": \"StateB\", \"event\": \"go\"}}. "
                "Valid actions are 'add_state', 'add_transition', 'rename_state', 'delete_item', and 'modify_state'. "
                "For any other conversation, respond with a normal text message."
            )

        # Add instructions for embedded code generation
        if any(re.search(r'\b' + re.escape(keyword) + r'\b', user_msg_lower) for keyword in ["arduino", "raspberry pi", "stm32"]):
             system_prompt_content += (
                " You are also an expert assistant for mechatronics and embedded systems programming. "
                "Provide clear, well-commented code snippets."
            )
        else:
             system_prompt_content += " For general conversation, provide helpful and concise answers."
             
        return system_prompt_content, is_fsm_generation_attempt

    @pyqtSlot(str, str)
    def process_tool_response_slot(self, message_id: str, tool_response: str):
        """Continues the conversation after a tool has been executed."""
        if self._is_stopped or not self._is_agent_mode:
            return

        self.conversation_history.append({"role": "tool", "content": tool_response})

        self.statusUpdate.emit(AIStatus.AGENT_THINKING, "Status: Agent is processing tool result...")

        try:
            ai_response_content = self.provider.generate_response(self.conversation_history, is_json_mode=False)
            if self._is_stopped: return
            self.conversation_history.append({"role": "assistant", "content": ai_response_content})
            self.responseReady.emit(ai_response_content, False)
            self.statusUpdate.emit(AIStatus.READY, f"Status: Ready ({self.provider.get_name()}).")
        except Exception as e:
            self.errorOccurred.emit(AIStatus.ERROR, f"Error after tool response: {e}")

    @pyqtSlot(str, bool)
    def process_message_slot(self, user_message: str, force_fsm_generation: bool):
        if self._is_stopped:
            return

        if not self.provider or not self.provider.is_configured():
            msg = "AI provider not configured. Please select a provider and set the API key in settings."
            self.errorOccurred.emit(AIStatus.PROVIDER_NOT_SET, msg)
            return

        status = AIStatus.AGENT_THINKING if self._is_agent_mode else AIStatus.THINKING
        status_text = "Agent is thinking..." if self._is_agent_mode else f"Thinking ({self.provider.get_name()})..."
        self.statusUpdate.emit(status, f"Status: {status_text}")

        system_prompt, is_json_mode = self._prepare_system_prompt(user_message, force_fsm_generation)

        # Prepare conversation history for the provider
        history_for_provider = [{"role": "system", "content": system_prompt}]
        history_context_limit = -8  # Keep last 4 user/assistant pairs
        for msg in self.conversation_history[history_context_limit:]:
            if msg.get("content"):
                role = "assistant" if msg["role"] == "assistant" else "user"
                history_for_provider.append({"role": role, "content": msg["content"]})
        history_for_provider.append({"role": "user", "content": user_message})

        try:
            ai_response_content = self.provider.generate_response(history_for_provider, is_json_mode=is_json_mode)

            if self._is_stopped: return

            # Check if the AI wants to call a tool (in agent mode)
            if self._is_agent_mode and ai_response_content.strip().startswith('{'):
                try:
                    tool_call_data = json.loads(ai_response_content)
                    if "tool_name" in tool_call_data and "tool_args" in tool_call_data:
                        message_id = str(uuid.uuid4())
                        self.conversation_history.append({"role": "user", "content": user_message})
                        self.conversation_history.append({"role": "assistant", "content": ai_response_content})
                        self.tool_call_request.emit(message_id, tool_call_data["tool_name"], tool_call_data["tool_args"])
                        return # Stop here, wait for the tool result to come back
                except json.JSONDecodeError:
                    pass # Not a valid tool call, treat as plain text below

            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": ai_response_content})
            self.responseReady.emit(ai_response_content, is_json_mode)
            self.statusUpdate.emit(AIStatus.READY, f"Status: Ready ({self.provider.get_name()}).")
        
        except PermissionError as e:
            self.errorOccurred.emit(AIStatus.AUTHENTICATION_ERROR, str(e))
        except ConnectionAbortedError as e: # Rate limit
            self.errorOccurred.emit(AIStatus.RATE_LIMIT, str(e))
        except ConnectionRefusedError as e: # Config/connection issue
            self.errorOccurred.emit(AIStatus.CONNECTION_ERROR, str(e))
        except Exception as e:
            err_msg = f"Unexpected error from provider '{self.provider.get_name()}': {e}"
            self.errorOccurred.emit(AIStatus.ERROR, err_msg)
            logger.error(err_msg, exc_info=True)
            self.statusUpdate.emit(AIStatus.ERROR, "Status: Unexpected Provider Error.")
        
    @pyqtSlot()
    def clear_history_slot(self):
        self.conversation_history = []
        logger.info("Conversation history cleared.")
        self.statusUpdate.emit(AIStatus.HISTORY_CLEARED, "Status: Chat history cleared.")
        
    @pyqtSlot()
    def stop_processing_slot(self):
        logger.info("WORKER: stop_processing_slot called.")
        self._is_stopped = True


class AISettingsDialog(QDialog):
    """Dialog to select an AI provider and enter its API key."""
    def __init__(self, settings_manager: SettingsManager, current_provider_name: str, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("AI Assistant Settings")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)
        form_widget = QWidget()
        layout = QFormLayout(form_widget)
        main_layout.addWidget(form_widget)

        # Provider Selector
        self.provider_combo = QComboBox()
        self.available_providers = get_available_providers()
        self.provider_combo.addItems(self.available_providers.keys())
        if current_provider_name in self.available_providers:
            self.provider_combo.setCurrentText(current_provider_name)
        layout.addRow("AI Provider:", self.provider_combo)

        # Key editor and note label
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter the API Key for the selected provider")
        layout.addRow("API Key:", self.api_key_edit)

        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        layout.addRow("", self.note_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        self._on_provider_changed(self.provider_combo.currentText())

    def _on_provider_changed(self, provider_name: str):
        """Update the UI when the provider selection changes."""
        notes = {
            "Gemini (Google AI)": 'Get a free key from <a href="https://aistudio.google.com/app/apikey">Google AI Studio</a>.',
            "OpenAI (GPT)": 'Get a key from your <a href="https://platform.openai.com/api-keys">OpenAI dashboard</a>.',
            "Groq (Llama3)": 'Get a key from <a href="https://console.groq.com/keys">GroqCloud</a>.',
            "Anthropic (Claude)": 'Get a key from your <a href="https://console.anthropic.com/settings/keys">Anthropic dashboard</a>.',
            "DeepSeek": 'Get a key from the <a href="https://platform.deepseek.com/api_keys">DeepSeek platform</a>.',
        }
        self.note_label.setText(notes.get(provider_name, "API Key required for this provider."))
        self.note_label.setOpenExternalLinks(True)

        key_name_in_settings = f"ai_api_key_{provider_name.replace(' ', '_').lower()}"
        key = self.settings_manager.get(key_name_in_settings, "")
        self.api_key_edit.setText(key)

    def get_selected_provider(self) -> str:
        return self.provider_combo.currentText()
    
    def get_key(self) -> str:
        return self.api_key_edit.text().strip()

class AIChatUIManager(QObject):
    applyFixRequested = pyqtSignal(dict)
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.mw = main_window

        self.ai_chat_display: QTextBrowser | None = None
        self.ai_chat_input: QLineEdit | None = None
        self.ai_chat_send_button: QPushButton | None = None
        self.ai_chat_status_label: QLabel | None = None
        self.original_send_button_icon: QIcon | None = None
        self.ai_agent_mode_cb: QCheckBox | None = None
        
        self._code_snippet_cache: Dict[str, str] = {}
        self._last_copy_feedback_timer: QTimer | None = None
        self._pending_status_update: tuple[AIStatus, str] | None = None
        self._original_status_text: str = ""
        self._original_status_stylesheet: str = ""
        self._last_proposed_action_id: str | None = None
        self._inline_request_targets: Dict[str, QWidget] = {}
        self.md_parser = MarkdownIt("commonmark", {"breaks": True, "html": False})
        
        self._connect_ai_chatbot_signals()

    def connect_signals(self):
        """Connects UI actions to manager slots. Called after UI is created."""
        settings_action = getattr(self.mw, 'openai_settings_action', None)
        if settings_action:
            settings_action.triggered.connect(self.on_ai_settings)
        
        ask_fsm_action = getattr(self.mw, 'ask_ai_to_generate_fsm_action', None)
        if ask_fsm_action:
            ask_fsm_action.triggered.connect(self.on_ask_ai_to_generate_fsm)
        
        clear_chat_action = getattr(self.mw, 'clear_ai_chat_action', None)
        if clear_chat_action:
            clear_chat_action.triggered.connect(self.on_clear_ai_chat_history)

    def _connect_ai_chatbot_signals(self):
        if self.mw.ai_chatbot_manager:
            self.mw.ai_chatbot_manager.statusUpdate.connect(self.update_status_display)
            self.mw.ai_chatbot_manager.errorOccurred.connect(self.handle_ai_error)
            self.mw.ai_chatbot_manager.fsmDataReceived.connect(self.handle_fsm_data_from_ai)
            self.mw.ai_chatbot_manager.plainResponseReady.connect(self.handle_plain_ai_response)
            self.mw.ai_chatbot_manager.ai_action_proposed.connect(self.on_ai_action_proposed)
            self.mw.ai_chatbot_manager.inlineResponseReady.connect(self.handle_inline_ai_response)

    def create_dock_widget_contents(self) -> QWidget:
        ai_chat_widget = QWidget()
        ai_chat_layout = QVBoxLayout(ai_chat_widget)
        ai_chat_layout.setContentsMargins(4,4,4,4)
        ai_chat_layout.setSpacing(4)

        self.ai_chat_display = QTextBrowser()
        self.ai_chat_display.setReadOnly(True)
        self.ai_chat_display.setAcceptRichText(True)        
        self.ai_chat_display.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.ai_chat_display.setOpenLinks(False) 
        self.ai_chat_display.setObjectName("AIChatDisplay");
        self.ai_chat_display.setPlaceholderText("AI chat history will appear here...")
        self.ai_chat_display.anchorClicked.connect(self.on_chat_anchor_clicked)
        ai_chat_layout.addWidget(self.ai_chat_display, 1)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(4)
        self.ai_chat_input = QLineEdit(); self.ai_chat_input.setObjectName("AIChatInput")
        self.ai_chat_input.setPlaceholderText("Type your message to the AI...")
        self.ai_chat_input.returnPressed.connect(self.on_send_ai_chat_message)
        input_layout.addWidget(self.ai_chat_input, 1)

        self.ai_chat_send_button = QPushButton()
        self.original_send_button_icon = get_standard_icon(QStyle.StandardPixmap.SP_ArrowRight, "SndAI")
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

        agent_mode_layout = QHBoxLayout()
        self.ai_agent_mode_cb = QCheckBox("Agent Task Mode")
        self.ai_agent_mode_cb.setToolTip("Enable to give the AI high-level tasks to complete using tools.")
        self.ai_agent_mode_cb.toggled.connect(self.mw.ai_chatbot_manager.set_agent_mode)
        agent_mode_layout.addStretch()
        agent_mode_layout.addWidget(self.ai_agent_mode_cb)
        ai_chat_layout.addLayout(agent_mode_layout)

        return ai_chat_widget

    # ... (the rest of the AIChatUIManager methods: update_status_display, _format_code_block,
    # _render_tokens_to_styled_html, _append_to_chat_display, on_ai_settings,
    # on_chat_anchor_clicked, handle_ai_error, etc., remain here as they were)
    @pyqtSlot(AIStatus, str)
    def update_status_display(self, status_enum: AIStatus, status_text: str):
        if not self.ai_chat_status_label: return

        if self._last_copy_feedback_timer and self._last_copy_feedback_timer.isActive():
            self._pending_status_update = (status_enum, status_text)
            return
        self._pending_status_update = None

        self.ai_chat_status_label.setText(status_text)

        base_style = f"font-size: {config.APP_FONT_SIZE_SMALL}; padding: 1px 3px; border-radius: 2px;"
        can_send_message = False
        is_thinking_ui = False

        if status_enum in [AIStatus.API_KEY_REQUIRED, AIStatus.API_KEY_ERROR, AIStatus.INACTIVE, AIStatus.AUTHENTICATION_ERROR, AIStatus.PROVIDER_NOT_SET]:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: white; background-color: {theme_config.COLOR_ACCENT_ERROR}; font-weight: bold;")
        elif status_enum == AIStatus.OFFLINE or status_enum == AIStatus.CONNECTION_ERROR:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {theme_config.COLOR_TEXT_PRIMARY}; background-color: {theme_config.COLOR_ACCENT_WARNING};")
        elif status_enum == AIStatus.ERROR or status_enum == AIStatus.CONTENT_BLOCKED or status_enum == AIStatus.RATE_LIMIT:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: white; background-color: {theme_config.COLOR_ACCENT_ERROR}; font-weight: bold;")
        elif status_enum in [AIStatus.THINKING, AIStatus.INITIALIZING, AIStatus.AGENT_THINKING]:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {theme_config.COLOR_TEXT_PRIMARY}; background-color: {QColor(theme_config.COLOR_ACCENT_SECONDARY).lighter(130).name()}; font-style: italic;")
            is_thinking_ui = True
        elif status_enum == AIStatus.READY or status_enum == AIStatus.ACTION_PROPOSED:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: white; background-color: {theme_config.COLOR_ACCENT_SUCCESS};")
            can_send_message = True
        elif status_enum == AIStatus.HISTORY_CLEARED:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {theme_config.COLOR_TEXT_SECONDARY}; background-color: {QColor(theme_config.COLOR_BACKGROUND_MEDIUM).lighter(105).name()};")
            if self.mw.ai_chatbot_manager and self.mw.ai_chatbot_manager.get_current_ai_status() == AIStatus.READY:
                 can_send_message = True
        else:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {theme_config.COLOR_TEXT_SECONDARY}; background-color: {theme_config.COLOR_BACKGROUND_MEDIUM};")

        if self.ai_chat_send_button:
            self.ai_chat_send_button.setEnabled(can_send_message)
            self.ai_agent_mode_cb.setEnabled(can_send_message)
            if is_thinking_ui:
                self.ai_chat_send_button.setText("...")
                self.ai_chat_send_button.setIcon(QIcon())
            else:
                self.ai_chat_send_button.setText("")
                self.ai_chat_send_button.setIcon(self.original_send_button_icon)

        if self.ai_chat_input:
            self.ai_chat_input.setEnabled(can_send_message)
            self.ai_agent_mode_cb.setEnabled(can_send_message)
            if can_send_message and self.mw and hasattr(self.mw, 'ai_chatbot_dock') and self.mw.ai_chatbot_dock and self.mw.ai_chatbot_dock.isVisible() and self.mw.isActiveWindow():
                self.ai_chat_input.setFocus()

        if hasattr(self.mw, 'ask_ai_to_generate_fsm_action'):
            self.mw.ask_ai_to_generate_fsm_action.setEnabled(can_send_message)

    def _format_code_block(self, code_content: str, language: str = "") -> str:
        bg_color = theme_config.COLOR_BACKGROUND_EDITOR_DARK
        text_color = theme_config.COLOR_TEXT_EDITOR_DARK_PRIMARY
        border_color = QColor(bg_color).lighter(130).name()

        code_id = str(uuid.uuid4())
        self._code_snippet_cache[code_id] = code_content

        lang_display = f"<span style='color: {theme_config.COLOR_TEXT_SECONDARY}; font-size: 7pt; margin-bottom: 3px; display: block;'>{html.escape(language)}</span>" if language else ""

        copy_button_bg_color = QColor(theme_config.COLOR_BACKGROUND_DIALOG).lighter(105 if QColor(theme_config.COLOR_BACKGROUND_DIALOG).lightnessF() > 0.5 else 115).name()
        copy_button_text_color = theme_config.COLOR_TEXT_PRIMARY
        copy_button_border_color = theme_config.COLOR_BORDER_MEDIUM

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
        """
        Renders a token stream from markdown-it to styled HTML suitable for QTextBrowser.
        """
        inline_code_style = f"background-color:{QColor(theme_config.COLOR_BACKGROUND_MEDIUM).lighter(105).name()}; color:{theme_config.COLOR_ACCENT_PRIMARY}; padding:1px 4px; border-radius:3px; font-family:Consolas,monospace; font-size: 0.9em;"
        blockquote_style = f"border-left: 2px solid {theme_config.COLOR_BORDER_MEDIUM}; margin-left: 5px; padding-left: 10px; color: {theme_config.COLOR_TEXT_SECONDARY}; font-style: italic;"
        
        original_fence_renderer = self.md_parser.renderer.rules.get("fence")
        def render_fence(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            token = tokens_list[idx]
            lang = token.info.strip().split(" ")[0] if token.info else ""
            return self._format_code_block(token.content, lang)
        self.md_parser.renderer.rules["fence"] = render_fence

        original_code_inline_renderer = self.md_parser.renderer.rules.get("code_inline")
        def render_code_inline(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            return f'<code style="{inline_code_style}">{html.escape(tokens_list[idx].content)}</code>'
        self.md_parser.renderer.rules["code_inline"] = render_code_inline
        
        original_blockquote_open_renderer = self.md_parser.renderer.rules.get("blockquote_open")
        def render_blockquote_open(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            return f'<blockquote style="{blockquote_style}">'
        self.md_parser.renderer.rules["blockquote_open"] = render_blockquote_open

        rendered_html = self.md_parser.renderer.render(tokens, self.md_parser.options, {})
        
        if original_fence_renderer: self.md_parser.renderer.rules["fence"] = original_fence_renderer
        if original_code_inline_renderer: self.md_parser.renderer.rules["code_inline"] = original_code_inline_renderer
        if original_blockquote_open_renderer: self.md_parser.renderer.rules["blockquote_open"] = original_blockquote_open_renderer
             
        return rendered_html

    def _append_to_chat_display(self, sender: str, message: str):
        if not self.ai_chat_display: return
        timestamp = QTime.currentTime().toString('hh:mm:ss')

        sender_color = theme_config.COLOR_ACCENT_PRIMARY
        sender_name_raw = sender
        if sender == "You": sender_color = theme_config.COLOR_ACCENT_SECONDARY
        elif sender == "System Error": sender_color = theme_config.COLOR_ACCENT_ERROR; sender_name_raw = f"<b>{html.escape(sender)}</b>"
        elif sender == "System": sender_color = QColor(theme_config.COLOR_TEXT_SECONDARY)
        elif sender in ["Diagram", "Validation Helper", "IDE", "You (Inline Request)"]:
            sender_color = QColor(theme_config.COLOR_ACCENT_SUCCESS).darker(110)

        sender_color_str = sender_color.name() if isinstance(sender_color, QColor) else sender_color
        sender_name_html = sender_name_raw if sender in ["System Error"] else html.escape(sender)

        tokens = self.md_parser.parse(message)
        final_message_html = self._render_tokens_to_styled_html(tokens)

        bg_msg_color = QColor(sender_color_str).lighter(185).name()
        if sender == "System Error": bg_msg_color = QColor(theme_config.COLOR_ACCENT_ERROR).lighter(180).name()
        elif sender == "System": bg_msg_color = QColor(theme_config.COLOR_BACKGROUND_MEDIUM).lighter(105).name()
        elif sender in ["Diagram", "Validation Helper", "IDE", "You (Inline Request)"]: bg_msg_color = QColor(sender_color_str).lighter(190).name()


        html_to_append = (f"<div style='margin-bottom: 10px; padding: 6px 8px; border-left: 3px solid {sender_color_str}; background-color: {bg_msg_color}; border-radius: 4px;'>"
                          f"<div style='margin-bottom: 3px;'>"
                          f"<strong style='color:{sender_color_str}; font-size: 9pt;'>{sender_name_html}</strong>"
                          f"<span style='font-size:7pt; color:{theme_config.COLOR_TEXT_SECONDARY}; margin-left: 6px;'>[{timestamp}]</span> "
                          f"</div>"
                          f"<div style='padding-left: 2px; line-height:1.4; font-size: 9pt;'>{final_message_html}</div></div>")

        self.ai_chat_display.append(html_to_append)
        self.ai_chat_display.ensureCursorVisible()

    

    @pyqtSlot()
    def on_ai_settings(self):
        logger.info("AIChatUI: SLOT on_ai_settings CALLED!")
        if not self.mw.ai_chatbot_manager or not hasattr(self.mw, 'settings_manager'):
            QMessageBox.warning(self.mw, "AI Error", "AI or Settings Manager is not initialized.")
            return

        current_provider = self.mw.settings_manager.get("ai_provider", "Gemini (Google AI)")
        dialog = AISettingsDialog(self.mw.settings_manager, current_provider, self.mw)

        if dialog.exec():
            provider_name = dialog.get_selected_provider()
            api_key = dialog.get_key()
            logger.info(f"AIChatUI: AI Settings dialog accepted. Provider: '{provider_name}'")
            
            key_setting_name = f"ai_api_key_{provider_name.replace(' ', '_').lower()}"
            
            # Save provider and key settings
            self.mw.settings_manager.set("ai_provider", provider_name)
            self.mw.settings_manager.set(key_setting_name, api_key)
            
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
                    self.ai_chat_status_label.setStyleSheet(f"font-size: {config.APP_FONT_SIZE_SMALL}; padding: 1px 3px; border-radius: 2px; color: {theme_config.COLOR_TEXT_ON_ACCENT}; background-color: {theme_config.COLOR_ACCENT_SUCCESS}; font-weight:bold;")

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
        else:
            if url.scheme() in ['http', 'https', 'file']:
                if hasattr(QDesktopServices, 'openUrl') and callable(QDesktopServices.openUrl):
                    QDesktopServices.openUrl(url)
                else:
                    logger.warning(f"QDesktopServices.openUrl not available. Cannot open: {url.toString()}")


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

        msg_box = QMessageBox(self.mw); msg_box.setIcon(QMessageBox.Icon.Question); msg_box.setWindowTitle("Add AI Generated FSM")
        msg_box.setText("AI has generated an FSM. Do you want to clear the current diagram before adding the new FSM, or add to the existing one?")
        clear_btn = msg_box.addButton("Clear and Add", QMessageBox.ButtonRole.YesRole)
        add_btn = msg_box.addButton("Add to Existing", QMessageBox.ButtonRole.NoRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole); msg_box.setDefaultButton(cancel_btn)
        msg_box.exec()

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

    # --- NEW: Slot for inline AI responses ---
    @pyqtSlot(str, str, str)
    def handle_inline_ai_response(self, code_snippet: str, source_prompt: str, request_id: str):
        """Handles code snippets generated for inline requests (from dialogs)."""
        logger.info(f"AIChatUI: Received INLINE AI response for request ID: {request_id}")
        
        # Display the interaction in the main chat for context and history
        self._append_to_chat_display("You (Inline Request)", source_prompt)
        self._append_to_chat_display("AI", code_snippet)

        # Find the target widget using the request ID
        target_widget = self._inline_request_targets.pop(request_id, None)

        if target_widget and isinstance(target_widget, (QTextEdit, QLineEdit)):
            logger.info(f"Injecting AI-generated code directly into widget: {target_widget.objectName()}")
            # Extract only the code from the response
            code_match = re.search(r"```(?:\w+\n)?(.*?)\n?```", code_snippet, re.DOTALL)
            code_to_insert = code_match.group(1).strip() if code_match else code_snippet.strip()
            target_widget.insertPlainText(code_to_insert)
        else:
            # Fallback message if the target widget is gone
            QMessageBox.information(self.mw, "AI Code Generated", "AI code snippet generated. Copy from the main chat window.")
        
        # Bring the AI dock to the front for context
        if hasattr(self.mw, 'ai_chatbot_dock'):
            self.mw.ai_chatbot_dock.setVisible(True)
            self.mw.ai_chatbot_dock.raise_()

    @pyqtSlot()
    def on_send_ai_chat_message(self):
        if not self.ai_chat_input or not self.ai_chat_send_button.isEnabled(): return
        message = self.ai_chat_input.text().strip()
        if not message: return
        self.ai_chat_input.clear(); self._append_to_chat_display("You", message)
        if self.mw.ai_chatbot_manager:
            self.mw.ai_chatbot_manager.send_message(message)
        else:
            err_msg = "AI Chatbot Manager not initialized. Cannot send message."
            self.handle_ai_error(AIStatus.ERROR, err_msg)
            self.update_status_display(AIStatus.ERROR, f"Status: Error - {err_msg}")


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

    # --- NEW: Slot for Documentation Generation ---
    @pyqtSlot()
    def on_generate_docs_with_ai(self):
        """Handles the user request to generate documentation for the current diagram."""
        editor = self.mw.current_editor()
        if not editor:
            QMessageBox.warning(self.mw, "No Diagram", "Please open a diagram to generate documentation for.")
            return

        self._append_to_chat_display("Diagram", "Requesting documentation generation from AI...")
        self.mw.ai_chatbot_manager.generate_documentation()
    # --- END NEW ---

    @pyqtSlot()
    def on_clear_ai_chat_history(self):
        logger.info("AIChatUI: on_clear_ai_chat_history CALLED!")
        if self.mw.ai_chatbot_manager:
            reply = QMessageBox.question(self.mw, "Clear Chat History",
                                         "Are you sure you want to clear the entire AI chat history?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.mw.ai_chatbot_manager.clear_conversation_history()
                if self.ai_chat_display:
                    self.ai_chat_display.clear()
                    self.ai_chat_display.setPlaceholderText("AI chat history will appear here...")
                logger.info("AIChatUI: Chat history cleared by user.")
                self._append_to_chat_display("System", "Chat history cleared.")
                self._code_snippet_cache.clear()
            else:
                logger.info("AIChatUI: User cancelled clearing chat history.")
        else:
            self.handle_ai_error(AIStatus.ERROR, "AI Chatbot Manager not initialized.")
            
    # --- NEW: Slot for handling AI action proposals ---
    @pyqtSlot(dict)
    def on_ai_action_proposed(self, action_data: dict):
        """Presents the AI's proposed action to the user for confirmation."""
        if not isinstance(action_data, dict):
            return

        # Generate a simple ID for the action to prevent re-confirmation spam
        action_id = json.dumps(action_data, sort_keys=True)
        if action_id == self._last_proposed_action_id:
            logger.debug("Ignoring duplicate AI action proposal.")
            return
        self._last_proposed_action_id = action_id

        action_type = action_data.get("action", "unknown").replace("_", " ").title()
        details = action_data.get("details", {})
        
        # Create a human-readable summary of the action
        summary = f"<b>Action:</b> {action_type}<br>"
        for key, value in details.items():
            summary += f"&nbsp;&nbsp;<b>{key.capitalize()}:</b> {html.escape(str(value))}<br>"
        
        # Use a QMessageBox for confirmation
        msg_box = QMessageBox(self.mw)
        msg_box.setWindowTitle("AI Action Proposed")
        msg_box.setText("The AI assistant has proposed the following change to your diagram:")
        msg_box.setInformativeText(summary)
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        approve_button = msg_box.addButton("Approve", QMessageBox.ButtonRole.YesRole)
        reject_button = msg_box.addButton("Reject", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(reject_button)

        # Append a message to the chat log
        self._append_to_chat_display("AI", f"I have a suggestion to modify the diagram:\n{summary.replace('<br>', '\n')}")

        ret = msg_box.exec()

        if msg_box.clickedButton() == approve_button:
            logger.info(f"User approved AI action: {action_data}")
            self.append_to_action_log([f"User approved AI action: {action_type}"])
            # Use the same signal/slot as the "Apply Fix" button
            self.applyFixRequested.emit(action_data)
        else:
            logger.info(f"User rejected AI action: {action_data}")
            self.append_to_action_log([f"User rejected AI action."])

    # --- NEW: Method to handle inline requests from dialogs ---
    def handle_inline_ai_request(self, prompt: str, language: str, target_widget: QWidget = None):
        """Sends a request to the AI manager specifically for an inline code snippet."""
        logger.info(f"AIChatUI: Handling INLINE AI request for language '{language}': '{prompt[:50]}...'")
        
        # Generate a unique ID for this request so we can find the target widget later
        request_id = f"inline_req_{uuid.uuid4()}"
        self._inline_request_targets[request_id] = target_widget

        if self.mw.ai_chatbot_manager:
            self.mw.ai_chatbot_manager.generate_inline_code_snippet(prompt, request_id)
        else:
            self.handle_ai_error(AIStatus.ERROR, "AI Chatbot Manager not initialized for inline request.")

    # --- NEW: Slot for displaying refinement requests ---
    def on_refine_selection_request(self, instruction: str, selection_data: list):
        """Displays the user's refinement request in the chat window."""
        num_items = len(selection_data)
        item_types = ", ".join(sorted(list(set(d['item_type'] for d in selection_data))))
        
        self._append_to_chat_display(
            "Diagram",
            f"Requesting AI refinement for {num_items} selected item(s) ({item_types}):\n> {instruction}"
        )

# --- FIX: The `refine_diagram_selection` method belongs to `AIChatbotManager`, not `AIChatUIManager` ---
class AIChatbotManager(QObject):
    statusUpdate = pyqtSignal(AIStatus, str)
    errorOccurred = pyqtSignal(AIStatus, str)
    fsmDataReceived = pyqtSignal(dict, str)
    plainResponseReady = pyqtSignal(str)
    ai_action_proposed = pyqtSignal(dict)
    inlineResponseReady = pyqtSignal(str, str, str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings_manager = self.parent_window.settings_manager if hasattr(self.parent_window, 'settings_manager') else None
        
        # --- MODIFIED: Provider Management ---
        self.available_providers = {p.get_name(): p for p in [cls() for cls in get_available_providers().values()]}
        self.current_provider: AIProvider | None = None
        
        # --- Other attributes ---
        self.chatbot_worker: ChatbotWorker | None = None
        self.chatbot_thread: QThread | None = None
        self.last_fsm_request_description: str | None = None
        self._is_inline_request_pending = False
        self._last_inline_prompt = ""
        self._last_inline_request_id = ""
        self._last_plain_response = ""
        self._current_ai_status = AIStatus.INACTIVE
        
        self._setup_worker() 
        
        if self.settings_manager:
            QTimer.singleShot(100, self._load_settings_and_configure)
            
    def _load_settings_and_configure(self):
        """Load last used provider and its key, then configure."""
        provider_name = self.settings_manager.get("ai_provider", list(self.available_providers.keys())[0] if self.available_providers else "")
        if not provider_name:
            self.errorOccurred.emit(AIStatus.PROVIDER_NOT_SET, "No AI providers found or configured.")
            return

        key_setting_name = f"ai_api_key_{provider_name.replace(' ', '_').lower()}"
        api_key = self.settings_manager.get(key_setting_name, "")
        self.configure_provider(provider_name, api_key)

    def _update_current_ai_status(self, new_status_enum: AIStatus, status_text: str):
        self._current_ai_status = new_status_enum
        self.statusUpdate.emit(new_status_enum, status_text)
        logger.debug(f"MGR_STATUS_UPDATE: Enum={new_status_enum.name}, Text='{status_text}'")

    @pyqtSlot(AIStatus, str)
    def _handle_worker_error_with_status(self, error_status: AIStatus, error_message: str):
        logger.error(f"MGR_WORKER_ERROR (Status: {error_status.name}): {error_message}")
        self.errorOccurred.emit(error_status, error_message)


    def get_available_tools_json(self) -> str:
        """Returns a JSON string describing available tools for the AI agent."""
        tools = [
            {"name": "add_state", "description": "Adds a new state to the diagram.", "parameters": {"name": "string", "x": "number", "y": "number"}},
            {"name": "add_transition", "description": "Adds a transition between two states.", "parameters": {"source": "string", "target": "string", "event": "string"}},
            {"name": "rename_state", "description": "Renames an existing state.", "parameters": {"old_name": "string", "new_name": "string"}},
            {"name": "delete_item", "description": "Deletes a state or transition.", "parameters": {"name": "string"}},
            {"name": "get_diagram_data", "description": "Returns the current FSM structure as JSON.", "parameters": {}},
        ]
        return json.dumps(tools)

    def get_current_ai_status(self) -> AIStatus:
        return self._current_ai_status
        
    def is_configured(self) -> bool:
        """Checks if the chatbot has a configured and ready provider."""
        # FIX: Check the worker's provider, not a non-existent attribute
        return bool(self.chatbot_worker and self.chatbot_worker.provider and self.chatbot_worker.provider.is_configured())


    def _cleanup_existing_worker_and_thread(self):
        logger.debug("MGR_CLEANUP: CALLED.")
        if self.chatbot_thread and self.chatbot_thread.isRunning():
            logger.debug("MGR_CLEANUP: Attempting to quit existing thread...")
            if self.chatbot_worker:
                QMetaObject.invokeMethod(self.chatbot_worker, "stop_processing_slot", Qt.ConnectionType.BlockingQueuedConnection if QThread.currentThread() != self.chatbot_thread else Qt.ConnectionType.DirectConnection)
                logger.debug("MGR_CLEANUP: stop_processing_slot invoked on worker.")

            self.chatbot_thread.quit()
            if not self.chatbot_thread.wait(300):
                logger.warning("MGR_CLEANUP: Thread did not quit gracefully. Terminating.")
                self.chatbot_thread.terminate()
                self.chatbot_thread.wait(200)
            logger.debug("MGR_CLEANUP: Existing thread stopped.")
        self.chatbot_thread = None

        if self.chatbot_worker:
            logger.debug("MGR_CLEANUP: Disconnecting signals and scheduling old worker for deletion.")
            try: self.chatbot_worker.responseReady.disconnect(self._handle_worker_response)
            except (TypeError, RuntimeError): pass
            try: self.chatbot_worker.errorOccurred.disconnect(self._handle_worker_error_with_status)
            except (TypeError, RuntimeError): pass
            try: self.chatbot_worker.statusUpdate.disconnect(self._update_current_ai_status)
            except (TypeError, RuntimeError): pass
            self.chatbot_worker.deleteLater()
            logger.debug("MGR_CLEANUP: Old worker scheduled for deletion.")
        self.chatbot_worker = None
        logger.debug("MGR_CLEANUP: Finished. Worker and thread are None.")

    def _setup_worker(self):
        self._cleanup_existing_worker_and_thread()

        logger.info("MGR_SETUP_WORKER: Setting up new worker and thread.")
        self.chatbot_thread = QThread(self)
        self.chatbot_worker = ChatbotWorker(parent=None)
        self.chatbot_worker.moveToThread(self.chatbot_thread)

        self.chatbot_worker.responseReady.connect(self._handle_worker_response)
        self.chatbot_worker.errorOccurred.connect(self._handle_worker_error_with_status)
        self.chatbot_worker.statusUpdate.connect(self._update_current_ai_status)
        self.chatbot_worker.tool_call_request.connect(self.on_tool_call_requested)

        self.chatbot_thread.start()
        logger.info("MGR_SETUP_WORKER: New AI Chatbot worker thread started.")
        self._update_current_ai_status(AIStatus.INITIALIZING, "Status: AI Initializing...")

    def configure_provider(self, provider_name: str, api_key: str):
        """Configures the selected provider with its API key."""
        logger.info(f"MGR_CONFIGURE: Attempting to configure provider '{provider_name}'")

        if not self.chatbot_worker or not self.chatbot_thread or not self.chatbot_thread.isRunning():
            self._setup_worker()
            QTimer.singleShot(50, lambda: self.configure_provider(provider_name, api_key))
            return
            
        provider_class = get_available_providers().get(provider_name)
        if not provider_class:
            msg = f"AI Provider '{provider_name}' not found."
            self._update_current_ai_status(AIStatus.PROVIDER_NOT_SET, f"Status: Error - {msg}")
            self.errorOccurred.emit(AIStatus.PROVIDER_NOT_SET, msg)
            return

        self.current_provider = provider_class()

        try:
            is_configured = self.current_provider.configure(api_key)
            if is_configured:
                # Pass the configured provider instance to the worker
                QMetaObject.invokeMethod(self.chatbot_worker, "set_provider_slot", Qt.ConnectionType.QueuedConnection, Q_ARG(AIProvider, self.current_provider))
            else:
                self._update_current_ai_status(AIStatus.API_KEY_REQUIRED, f"Status: API Key required for {provider_name}.")
                # Note: Do not emit an error here, it's just a state of needing a key
        except Exception as e:
            logger.error(f"Error configuring provider {provider_name}: {e}", exc_info=True)
            self.errorOccurred.emit(AIStatus.API_KEY_ERROR, str(e))
            self._update_current_ai_status(AIStatus.API_KEY_ERROR, f"Status: Error setting up {provider_name}.")
    
    def configure_api(self, api_key: str | None):
        """Reconfigures the AI worker with a new API key."""
        logger.info(f"MGR_CONFIGURE_API: Key {'SET' if api_key else 'NONE'}")

        # This method might be deprecated in favor of configure_provider, but keeping for compatibility.
        if not self.chatbot_worker or not self.chatbot_thread or not self.chatbot_thread.isRunning():
            logger.info("MGR_CONFIGURE_API: Worker/thread not ready. Setting up first.")
            self._setup_worker()
            QTimer.singleShot(50, lambda: self.configure_api(api_key))
            return
            
        QMetaObject.invokeMethod(self.chatbot_worker, "configure_api_key_slot", Qt.ConnectionType.QueuedConnection,
                                  Q_ARG(str, api_key or ""))
        
    @pyqtSlot(str, bool)
    def _handle_worker_response(self, ai_response_content: str, was_fsm_generation_attempt: bool):
        logger.info(f"MGR_HANDLE_WORKER_RESPONSE: Received from worker. Was FSM attempt: {was_fsm_generation_attempt}")
        
        # --- MODIFIED to check for pending inline request ---
        if self._is_inline_request_pending:
            self._is_inline_request_pending = False
            # Emit the new signal with the request ID
            self.inlineResponseReady.emit(ai_response_content, self._last_inline_prompt, self._last_inline_request_id)
            self._last_inline_prompt = ""
            self._last_inline_request_id = ""
            return
        if was_fsm_generation_attempt:
            try:
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", ai_response_content, re.DOTALL | re.IGNORECASE)
                if match:
                    cleaned_json_str = match.group(1)
                    logger.debug("MGR_HANDLE_WORKER_RESPONSE: Extracted JSON via regex.")
                else:
                    if "```" not in ai_response_content:
                        logger.debug("MGR_HANDLE_WORKER_RESPONSE: No ```json``` block found, trying to parse directly.")
                        cleaned_json_str = ai_response_content.strip()
                    else:
                        logger.warning("MGR_HANDLE_WORKER_RESPONSE: Markdown ``` found, but not a recognized JSON block. Treating as plain text.")
                        raise json.JSONDecodeError("Markdown ``` found, but not a recognized JSON block.", ai_response_content, 0)

                fsm_data = json.loads(cleaned_json_str)
                if isinstance(fsm_data, dict) and ('states' in fsm_data or 'transitions' in fsm_data):
                    logger.info("MGR_HANDLE_WORKER_RESPONSE: Parsed FSM JSON successfully. Emitting fsmDataReceived.")
                    source_desc = self.last_fsm_request_description or "AI Generated FSM"
                    self.fsmDataReceived.emit(fsm_data, source_desc)
                    return
                else:
                    err_msg = "AI returned JSON, but it's not a valid FSM structure. Displaying as text."
                    logger.warning("MGR_HANDLE_WORKER_RESPONSE: " + err_msg)
                    self.errorOccurred.emit(AIStatus.ERROR, err_msg)
                    self._update_current_ai_status(AIStatus.ERROR, "Status: Invalid FSM JSON from AI.")
            except json.JSONDecodeError as e:
                err_msg = f"AI response for FSM generation was not valid JSON. Raw response (see chat for full):\n{ai_response_content[:200]}..."
                logger.warning(f"MGR_HANDLE_WORKER_RESPONSE: Failed to parse AI response as JSON: {e}. Treating as plain text.", exc_info=True)
                self.errorOccurred.emit(AIStatus.ERROR, err_msg)
                self._update_current_ai_status(AIStatus.ERROR, "Status: AI response was not valid FSM JSON.")

        # --- NEW: Check for a conversational action command ---
        elif ai_response_content.strip().startswith('{') and ai_response_content.strip().endswith('}'):
             try:
                action_data = json.loads(ai_response_content)
                if isinstance(action_data, dict) and "action" in action_data and "details" in action_data:
                    logger.info(f"MGR_HANDLE_WORKER_RESPONSE: Detected AI action proposal: {action_data['action']}")
                    self._update_current_ai_status(AIStatus.ACTION_PROPOSED, f"Status: AI has a suggestion.")
                    self.ai_action_proposed.emit(action_data)
                    return # Stop processing, this is not a plain response
             except json.JSONDecodeError:
                # Not a valid JSON, so treat it as plain text.
                pass

        # Prevent spamming the same plain response over and over
        if self._last_plain_response == ai_response_content:
            logger.debug("MGR_HANDLE_WORKER_RESPONSE: Ignoring duplicate plain text response.")
            return
        self._last_plain_response = ai_response_content
        logger.debug("MGR_HANDLE_WORKER_RESPONSE: Emitting plainResponseReady.")
        self.plainResponseReady.emit(ai_response_content)


    @pyqtSlot(str, str, dict)
    def on_tool_call_requested(self, message_id: str, tool_name: str, tool_args: dict):
        """Handles a tool call request from the AI worker."""
        self._update_current_ai_status(AIStatus.AGENT_THINKING, f"Status: Agent wants to run tool: {tool_name}")
        
        # In a real implementation, you would now execute the tool.
        # For this foundation, we will simulate a success response.
        logger.info(f"AGENT: Simulating execution of tool '{tool_name}' with args {tool_args}")
        
        # This part would call methods on the ActionHandler or Scene
        tool_result = f"Successfully executed tool {tool_name}."

        # Send the result back to the worker to continue the loop
        if self.chatbot_worker:
            QMetaObject.invokeMethod(self.chatbot_worker, "process_tool_response_slot", Qt.ConnectionType.QueuedConnection,
                                     Q_ARG(str, message_id),
                                     Q_ARG(str, tool_result))

    def _prepare_and_send_to_worker(self, user_message_text: str, is_fsm_gen_specific: bool = False, is_inline_code_request: bool = False, inline_request_id: str = ""):
        logger.info(f"MGR_PREP_SEND: For: '{user_message_text[:30]}...', FSM_specific_req: {is_fsm_gen_specific}, Inline: {is_inline_code_request}, ID: {inline_request_id}")

        # --- FIX: Use the correct method to check if the worker is configured ---
        if not self.chatbot_worker or not self.chatbot_worker.provider or not self.chatbot_worker.provider.is_configured():
            err_msg = "AI Assistant not configured. Please select a provider and set the API Key in Settings."
            logger.warning(f"MGR_PREP_SEND: AI provider not configured. Aborting send.")
            self.errorOccurred.emit(AIStatus.API_KEY_REQUIRED, err_msg)
            if self.parent_window and hasattr(self.parent_window, 'ai_chat_ui_manager'):
                self.parent_window.ai_chat_ui_manager._append_to_chat_display("System Error", err_msg)
            return

        if not self.chatbot_worker or not self.chatbot_thread or not self.chatbot_thread.isRunning():
            logger.warning("MGR_PREP_SEND: Worker/Thread not ready.")
            if self.chatbot_worker: 
                 logger.info("MGR_PREP_SEND: Attempting to re-setup worker because it's not running.")
                 self._setup_worker()
                 QTimer.singleShot(50, self._load_settings_and_configure)

            if not self.chatbot_worker or not self.chatbot_thread or not self.chatbot_thread.isRunning():
                err_msg = "AI Assistant is not ready. Please wait or check settings."
                self.errorOccurred.emit(AIStatus.ERROR, err_msg)
                self._update_current_ai_status(AIStatus.ERROR, "Status: AI Assistant Not Ready.")
                if self.parent_window and hasattr(self.parent_window, 'ai_chat_ui_manager') and self.parent_window.ai_chat_ui_manager:
                    self.parent_window.ai_chat_ui_manager._append_to_chat_display("System Error", err_msg)
                return

        if is_fsm_gen_specific:
            self.last_fsm_request_description = user_message_text
        else:
            self.last_fsm_request_description = None

        self._is_inline_request_pending = is_inline_code_request
        if is_inline_code_request:
            self._last_inline_prompt = user_message_text
            self._last_inline_request_id = inline_request_id

        diagram_json_str: str | None = None
        current_editor = self.parent_window.current_editor()
        if current_editor and hasattr(current_editor, 'scene'):
            try:
                diagram_data = current_editor.scene.get_diagram_data()
                lean_diagram_data = {
                    "states": [{"name": s.get("name"), "is_initial": s.get("is_initial"), "is_final": s.get("is_final")}
                               for s in diagram_data.get("states", [])],
                    "transitions": [{"source": t.get("source"), "target": t.get("target"), "event": t.get("event")}
                                    for t in diagram_data.get("transitions", [])]
                }
                diagram_json_str = json.dumps(lean_diagram_data)
                logger.debug(f"MGR_PREP_SEND: Lean diagram context (first 100 chars): {diagram_json_str[:100]}")
            except Exception as e:
                logger.error(f"MGR_PREP_SEND: Error getting/processing diagram data: {e}", exc_info=True)
                diagram_json_str = json.dumps({"error": "Could not retrieve diagram context."})
        else:
             diagram_json_str = json.dumps({"error": "Diagram context unavailable (no active editor)."})

        if self.chatbot_worker:
            effective_diagram_json_str = diagram_json_str if diagram_json_str is not None else ""
            QMetaObject.invokeMethod(self.chatbot_worker, "set_diagram_context_slot", Qt.ConnectionType.QueuedConnection,
                                     Q_ARG(str, effective_diagram_json_str))
            
            is_fsm_attempt_for_worker = is_fsm_gen_specific and not is_inline_code_request

            QMetaObject.invokeMethod(self.chatbot_worker, "process_message_slot", Qt.ConnectionType.QueuedConnection,
                                     Q_ARG(str, user_message_text),
                                     Q_ARG(bool, is_fsm_attempt_for_worker))
            logger.debug("MGR_PREP_SEND: Methods queued for worker.")
        else:
            logger.error("MGR_PREP_SEND: Chatbot worker is None, cannot queue methods.")
            err_msg = "AI Assistant encountered an internal error (worker missing). Please try restarting AI features."
            self.errorOccurred.emit(AIStatus.ERROR, err_msg)
            self._update_current_ai_status(AIStatus.ERROR, "Status: Internal Error (Worker Missing).")

    def send_message(self, user_message_text: str):
        self._prepare_and_send_to_worker(user_message_text, is_fsm_gen_specific=False)

    def generate_fsm_from_description(self, description: str):
         self._prepare_and_send_to_worker(description, is_fsm_gen_specific=True)
         
    # --- NEW: Documentation Generation Method ---
    def generate_documentation(self):
        """Sends the current diagram to the AI to generate Markdown documentation."""
        prompt = (
            "You are a technical writer specializing in software and systems engineering. "
            "Based on the following FSM diagram provided in JSON format, generate a comprehensive and "
            "well-structured Markdown document that explains the state machine's functionality. "
            "The documentation should include:\n"
            "1. A brief, high-level summary of the FSM's purpose.\n"
            "2. A 'States' section with a bulleted list describing each state's purpose, entry, during, and exit actions.\n"
            "3. A 'Transitions' section describing the logic for moving between states (event, condition, and action).\n"
            "Format the output clearly using Markdown headings, lists, and code blocks for actions/conditions."
        )
        self._prepare_and_send_to_worker(prompt, is_fsm_gen_specific=False)
    
    
    
    def generate_inline_code_snippet(self, prompt: str, request_id: str):
        """Sends a prompt specifically for generating an inline code snippet."""
        self._prepare_and_send_to_worker(prompt, is_fsm_gen_specific=False, is_inline_code_request=True, inline_request_id=request_id)

    @pyqtSlot(bool)
    def set_agent_mode(self, is_agent_mode: bool):
        """Sets whether the AI is in conversational agent mode."""
        if self.chatbot_worker:
            tools_json = self.get_available_tools_json() if is_agent_mode else ""
            QMetaObject.invokeMethod(self.chatbot_worker, "set_agent_mode_slot", Qt.ConnectionType.QueuedConnection, Q_ARG(bool, is_agent_mode), Q_ARG(str, tools_json))

    def clear_conversation_history(self):
        logger.info("MGR: clear_conversation_history CALLED.")
        if self.chatbot_worker and self.chatbot_thread and self.chatbot_thread.isRunning():
            QMetaObject.invokeMethod(self.chatbot_worker, "clear_history_slot", Qt.ConnectionType.QueuedConnection)
            logger.debug("MGR: clear_history invoked on worker.")
            if self.parent_window and hasattr(self.parent_window, 'ai_chat_ui_manager'):
                self.parent_window.ai_chat_ui_manager._code_snippet_cache.clear()
        else:
            if not self.is_configured():
                self._update_current_ai_status(AIStatus.API_KEY_REQUIRED, "Status: API Key required. Chat inactive.")
            else:
                self._update_current_ai_status(AIStatus.INACTIVE, "Status: Chatbot not active.")
            logger.warning("MGR: Chatbot not active, cannot clear history from worker.")


    def stop_chatbot(self):
        logger.info("MGR_STOP: stop_chatbot CALLED.")
        self._cleanup_existing_worker_and_thread()
        self._update_current_ai_status(AIStatus.INACTIVE, "Status: AI Assistant Stopped.")
        logger.info("MGR_STOP: Chatbot stopped and cleaned up.")

    def set_online_status(self, is_online: bool):
        logger.info(f"MGR_NET_STATUS: Online status changed to: {is_online}")

        current_status = self.get_current_ai_status()

        if not is_online:
            self._update_current_ai_status(AIStatus.OFFLINE, "Status: Offline. AI features unavailable.")
            return

        if current_status == AIStatus.OFFLINE:
            logger.info("MGR_NET_STATUS: Internet connection restored. Re-checking AI configuration.")
            self._load_settings_and_configure()
        else:
            logger.debug("MGR_NET_STATUS: Internet status is online, no AI status change required from network check.")
    
    
    
    
    
    
    
    
    
        
    def refine_diagram_selection(self, instruction: str, selection_data: list):
        """
        Sends a selection of the diagram and a user instruction to the AI for refinement.

        Args:
            instruction: The natural language command from the user (e.g., "add a timeout").
            selection_data: A list of dictionaries representing the selected items' data.
        """
        # First, display the user's prompt in the chat for context and history.
        # This gives the user feedback that their request has been received.
        if self.parent_window and hasattr(self.parent_window, 'ai_chat_ui_manager'):
            self.parent_window.ai_chat_ui_manager.on_refine_selection_request(instruction, selection_data)

        # Serialize the selection data into a JSON string for the prompt.
        selection_json = json.dumps(selection_data, indent=2)

        # Construct the detailed prompt for the AI.
        prompt = f"""You are an expert FSM design assistant. The user has selected a portion of their diagram and wants to refine it. Your task is to generate one or more `[BSM_FIX]` JSON blocks to accomplish this.

User's instruction: "{instruction}"

The JSON for the currently selected items is:
```json
{selection_json}
```"""
        # --- FIX: The incomplete method is causing the ImportError. Complete it. ---
        self._prepare_and_send_to_worker(prompt, is_fsm_gen_specific=False)