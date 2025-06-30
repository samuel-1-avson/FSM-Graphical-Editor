# bsm_designer_project/ai_chatbot.py
# --- MODIFIED FOR MULTI-MODEL AI PROVIDER SUPPORT ---

from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTime, QTimer, Qt, QMetaObject, pyqtSlot, Q_ARG, QSize, QUrl
import json
import re
import logging
from enum import Enum, auto
import html
import uuid
from typing import Dict, List, Tuple

# --- NEW: Import the provider system ---
from .ai_providers import get_available_providers, get_provider_by_name
from .ai_providers.base import AIProvider
# --- END NEW ---

from PyQt5.QtGui import QMovie, QIcon, QColor, QDesktopServices
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextBrowser, QHBoxLayout, QLineEdit,
                             QPushButton, QLabel, QStyle, QMessageBox, QInputDialog, QAction, QApplication,
                             QDialog, QFormLayout, QDialogButtonBox, QComboBox)

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from .config import ( 
    APP_FONT_SIZE_SMALL, COLOR_BACKGROUND_MEDIUM, COLOR_ACCENT_WARNING,
    COLOR_ACCENT_PRIMARY, COLOR_ACCENT_SECONDARY, COLOR_TEXT_PRIMARY,
    COLOR_PY_SIM_STATE_ACTIVE, COLOR_ACCENT_ERROR, COLOR_TEXT_SECONDARY,
    COLOR_BACKGROUND_EDITOR_DARK, COLOR_TEXT_EDITOR_DARK_PRIMARY, COLOR_BORDER_LIGHT,
    COLOR_TEXT_ON_ACCENT, COLOR_ACCENT_SUCCESS, COLOR_BACKGROUND_DIALOG,
    COLOR_BORDER_MEDIUM
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
    PROVIDER_NOT_SET = auto() # New status

class ChatbotWorker(QObject):
    responseReady = pyqtSignal(str, bool)
    errorOccurred = pyqtSignal(AIStatus, str)
    statusUpdate = pyqtSignal(AIStatus, str)

    def __init__(self, api_key, model_name="gemini-1.5-flash-latest", parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model_name = model_name
        self.client: genai.GenerativeModel | None = None
        self.conversation_history = []
        self.current_diagram_context_json_str: str | None = None
        self._current_processing_had_error = False
        self._is_stopped = False
        self._initialize_client()
        logger.info(f"ChatbotWorker initialized (Gemini API Key {'SET' if api_key else 'NOT SET'}).")

    def _initialize_client(self):
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                self.client = genai.GenerativeModel(self.model_name, safety_settings=safety_settings)
                logger.info(f"Gemini client initialized for model {self.model_name}.")
            except Exception as e:
                self.client = None
                logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)
        else:
            self.client = None
            logger.info("Gemini client not initialized (no API key).")

    @pyqtSlot(str)
    def set_api_key_slot(self, api_key: str):
        logger.info(f"WORKER: set_api_key_slot called (new key {'SET' if api_key else 'NOT SET'}).")
        self.api_key = api_key
        self._initialize_client()

        if not self.api_key:
            self.statusUpdate.emit(AIStatus.API_KEY_REQUIRED, "Status: API Key cleared. AI Assistant inactive.")
        elif self.client:
             self.statusUpdate.emit(AIStatus.READY, "Status: API Key set and AI Assistant ready.")
        else:
            self.errorOccurred.emit(AIStatus.API_KEY_ERROR, "Failed to initialize Gemini client with the new API key.")
            self.statusUpdate.emit(AIStatus.API_KEY_ERROR, "Status: API Key Error.")

    @pyqtSlot(str)
    def set_diagram_context_slot(self, diagram_json_str: str):
        if not diagram_json_str:
            logger.debug(f"WORKER: Setting diagram context to None (received empty string).")
            self.current_diagram_context_json_str = None
        else:
            self.current_diagram_context_json_str = diagram_json_str


    @pyqtSlot(str, bool)
    def process_message_slot(self, user_message: str, force_fsm_generation: bool):
        if self._is_stopped:
            logger.info("WORKER_PROCESS: Worker is stopped, ignoring message.")
            return

        logger.info(f"WORKER_PROCESS: process_message_slot CALLED for: '{user_message[:50]}...' (force_fsm_generation={force_fsm_generation})")
        self._current_processing_had_error = False

        if not self.api_key:
            error_msg = "Gemini API key not set. Please set it in AI Assistant Settings."
            logger.warning("process_message: %s", error_msg)
            self.errorOccurred.emit(AIStatus.API_KEY_REQUIRED, error_msg)
            self.statusUpdate.emit(AIStatus.API_KEY_REQUIRED, "Status: API Key required.")
            self._current_processing_had_error = True
            return

        if not self.client:
            error_msg = "Gemini client not initialized. This might be due to an invalid API key or a network issue during initialization."
            logger.warning("process_message: %s", error_msg)
            self.errorOccurred.emit(AIStatus.API_KEY_ERROR, error_msg)
            self.statusUpdate.emit(AIStatus.API_KEY_ERROR, "Status: API Client Error.")
            self._current_processing_had_error = True
            return

        if self._is_stopped:
            logger.info("WORKER_PROCESS: Worker stopped before API call.")
            return

        self.statusUpdate.emit(AIStatus.THINKING, "Status: Thinking...")

        is_fsm_generation_attempt = False
        if force_fsm_generation:
            is_fsm_generation_attempt = True
        else:
            keywords_for_generation = [
                "generate fsm", "create fsm", "generate an fsm model",
                "generate state machine", "create state machine", "design state machine",
                "model fsm", "model state machine",
                "draw fsm", "draw state machine", "make an fsm", "fsm design for",
                "/generate_fsm"
            ]
            user_msg_lower = user_message.lower()
            is_fsm_generation_attempt = any(re.search(r'\b' + re.escape(keyword) + r'\b', user_msg_lower) for keyword in keywords_for_generation)

        is_embedded_code_request = False
        if not is_fsm_generation_attempt:
            embedded_keywords = [
                "arduino", "raspberry pi", "rpi", "esp32", "stm32",
                "microcontroller", "embedded c", "gpio", "pwm", "adc",
                "i2c", "spi", "sensor code", "actuator code", "mechatronics code",
                "robotics code", "control system code", "firmware snippet"
            ]
            user_msg_lower_for_embedded = user_message.lower()
            if any(re.search(r'\b' + re.escape(keyword) + r'\b', user_msg_lower_for_embedded) for keyword in embedded_keywords):
                is_embedded_code_request = True
                logger.debug(f"WORKER_PROCESS: Detected embedded code request keywords in '{user_message[:50]}...'")

        logger.debug(f"WORKER_PROCESS: is_fsm_generation_attempt = {is_fsm_generation_attempt} for '{user_message[:50]}...'")

        system_prompt_content = "You are a helpful assistant for designing Finite State Machines."
        if self.current_diagram_context_json_str:
            try:
                diagram = json.loads(self.current_diagram_context_json_str)
                if "error" not in diagram:
                    num_states = len(diagram.get("states", []))
                    num_transitions = len(diagram.get("transitions", []))
                    if num_states > 0:
                        # --- FIX for BUG-04 ---
                        # Instead of joining state names, provide a safe, descriptive summary.
                        context_summary = (
                            f" The current diagram has {num_states} state(s) and {num_transitions} transition(s)."
                        )
                        # --- END FIX ---
                        system_prompt_content += context_summary
                    else:
                        system_prompt_content += " The current diagram is empty."
            except json.JSONDecodeError:
                logger.warning("WORKER_PROCESS_CTX_ERROR: JSONDecodeError processing diagram context.", exc_info=True)
                system_prompt_content += " (Error reading diagram context in worker)."
            except Exception as e_ctx:
                logger.error(f"WORKER_PROCESS_CTX_ERROR: Error processing diagram context: {e_ctx}", exc_info=True)
                system_prompt_content += " (Issue with diagram context string)."
        else:
             system_prompt_content += " No diagram context was provided for this request."

        if is_fsm_generation_attempt:
            # --- AI IMPROVEMENT: Enhanced FSM Generation Prompt ---
            system_prompt_content += (
                " When asked to generate an FSM, you MUST respond with ONLY a valid JSON object. "
                "First, think step-by-step about the states and transitions needed. Then, based on your reasoning, construct the final JSON. "
                "The entire response MUST be just the single JSON object, parseable by json.loads().\n"
                "The root of the JSON is an object. It should have a 'description' (string), a 'states' list, and a 'transitions' list. "
                "Each state object in 'states' must have a 'name' (string, unique). Optional keys: 'is_initial' (boolean), 'entry_action' (string), etc. "
                "Each transition object in 'transitions' must have 'source' and 'target' (strings matching state names). Optional keys: 'event', 'condition', 'action'.\n"
                "Here is a simple example. User request: 'generate a simple toggle switch'. Your response MUST be ONLY this JSON:\n"
                '```json\n'
                '{\n'
                '  "description": "A simple on/off toggle switch.",\n'
                '  "states": [\n'
                '    {"name": "Off", "is_initial": true, "entry_action": "print(\\"is OFF\\")"},\n'
                '    {"name": "On", "entry_action": "print(\\"is ON\\")"}\n'
                '  ],\n'
                '  "transitions": [\n'
                '    {"source": "Off", "target": "On", "event": "toggle"},\n'
                '    {"source": "On", "target": "Off", "event": "toggle"}\n'
                '  ]\n'
                '}\n'
                '```\n'
                "Do not include comments, explanations, or any other text outside the main JSON object."
            )
        else:
            if is_embedded_code_request:
                system_prompt_content += (
                    " You are also an expert assistant for mechatronics and embedded systems programming. "
                    "If the user asks for Arduino code, structure it with `void setup() {}` and `void loop() {}`. "
                    "If for Raspberry Pi, provide Python code, using `RPi.GPIO` for GPIO tasks if appropriate, or other common libraries like `smbus` for I2C. "
                    "For other microcontrollers like ESP32 or STM32, provide C/C++ code in a typical embedded style (e.g., using Arduino framework for ESP32 if common, or HAL/LL for STM32 if specified). "
                    "Provide clear, well-commented code snippets. "
                    "If including explanations, clearly separate the code block using markdown (e.g., ```c or ```python or ```cpp). "
                    "Focus on the specific request and aim for functional, copy-pasteable code where possible. "
                    "For general mechatronics algorithms (e.g., PID, kinematics), pseudocode or Python is often suitable unless a specific language is requested."
                )
            else:
                 system_prompt_content += " For general conversation, provide helpful and concise answers."

        api_contents = []
        if system_prompt_content:
            api_contents.append({"role": "user", "parts": [{"text": system_prompt_content}]})
            api_contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions carefully."}]})

        history_context_limit = -6
        if self.conversation_history:
            for msg in self.conversation_history[history_context_limit:]:
                if isinstance(msg, dict) and "role" in msg and "parts" in msg:
                    if msg["role"] in ["user", "model"]:
                        if api_contents and api_contents[-1]["role"] == msg["role"]:
                            dummy_role = "model" if msg["role"] == "user" else "user"
                            api_contents.append({"role": dummy_role, "parts": [{"text": "Okay."}]})
                        api_contents.append(msg)
                    else:
                        logger.warning(f"Skipping malformed history message with invalid role: {msg.get('role')}")
                else:
                    logger.warning(f"Skipping malformed history message: {msg}")

        if api_contents and api_contents[-1]["role"] == "user":
            api_contents.append({"role": "model", "parts": [{"text": "Acknowledged."}]})

        api_contents.append({"role": "user", "parts": [{"text": user_message}]})

        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
        )
        if is_fsm_generation_attempt:
            generation_config.response_mime_type = "application/json"
            logger.info("WORKER_PROCESS: Requesting JSON object format from Gemini.")

        try:
            if self._is_stopped:
                logger.info("WORKER_PROCESS: Worker stopped just before creating completion.")
                return

            generation_args = {"contents": api_contents, "generation_config": generation_config}

            logger.debug(f"WORKER_PROCESS: Sending to Gemini. Contents (first part text len, role):")
            for i, item_content in enumerate(api_contents):
                first_part_text = item_content.get("parts", [{}])[0].get("text", "")
                preview = first_part_text[:80].replace('\n', ' ') + ('...' if len(first_part_text) > 80 else '')
                logger.debug(f"  Part {i}: Role '{item_content.get('role', 'N/A')}', Text Len: {len(first_part_text)}, Preview: '{preview}'")

            response = self.client.generate_content(**generation_args)

            if self._is_stopped:
                logger.info("WORKER_PROCESS: Worker stopped during/after API call, discarding response.")
                return

            ai_response_content = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                ai_response_content = response.candidates[0].content.parts[0].text
            elif hasattr(response, 'text'):
                ai_response_content = response.text
            else:
                feedback = response.prompt_feedback if hasattr(response, 'prompt_feedback') else "No feedback."
                finish_reason = response.candidates[0].finish_reason if response.candidates else "Unknown reason."
                error_msg = f"Gemini response was empty or blocked. Finish Reason: {finish_reason}. Feedback: {feedback}"
                logger.error(error_msg)
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    block_reason_msg = getattr(response.prompt_feedback, 'block_reason_message', None)
                    if block_reason_msg: error_msg += f" Block Reason Message: {block_reason_msg}"
                    for rating in response.prompt_feedback.safety_ratings:
                        if rating.blocked:
                             error_msg += f" Safety Blocked: Category {rating.category}, Probability {rating.probability.name}"
                self.errorOccurred.emit(AIStatus.CONTENT_BLOCKED, error_msg)
                self._current_processing_had_error = True
                self.statusUpdate.emit(AIStatus.ERROR, f"Status: Error - {error_msg[:50]}...")
                return


            self.conversation_history.append({"role": "user", "parts": [{"text": user_message}]})
            self.conversation_history.append({"role": "model", "parts": [{"text": ai_response_content}]})
            logger.debug("WORKER_PROCESS: AI response received and added to history.")
            self.responseReady.emit(ai_response_content, is_fsm_generation_attempt)

        except google.api_core.exceptions.ServiceUnavailable as e:
            err_str = f"API Connection Error: {str(e)[:200]}"
            logger.error("Gemini API Connection/Service Error: %s", err_str, exc_info=True)
            self.errorOccurred.emit(AIStatus.CONNECTION_ERROR, err_str)
            self.statusUpdate.emit(AIStatus.OFFLINE, "Status: Offline/Connection Error.")
            self._current_processing_had_error = True
        except google.api_core.exceptions.ResourceExhausted as e:
            err_str = f"Rate Limit Exceeded: {str(e)[:200]}"
            logger.error("Gemini Rate Limit Exceeded: %s", err_str, exc_info=True)
            self.errorOccurred.emit(AIStatus.RATE_LIMIT, err_str)
            self.statusUpdate.emit(AIStatus.ERROR, "Status: Rate Limit Exceeded.")
            self._current_processing_had_error = True
        except (google.api_core.exceptions.PermissionDenied, google.auth.exceptions.RefreshError, google.auth.exceptions.DefaultCredentialsError) as e:
            err_str = f"Authentication Error (Invalid API Key?): {str(e)[:200]}"
            logger.error("Gemini Authentication/Permission Error: %s", err_str, exc_info=True)
            self.errorOccurred.emit(AIStatus.AUTHENTICATION_ERROR, err_str)
            self.statusUpdate.emit(AIStatus.API_KEY_ERROR, "Status: API Key Error.")
            self._current_processing_had_error = True
        except google.api_core.exceptions.GoogleAPIError as e:
            error_detail = str(e)
            if hasattr(e, 'message') and e.message: error_detail = e.message
            err_str = f"Google API Error: {type(e).__name__} - {error_detail[:250]}"
            logger.error("Gemini API Error: %s - %s", type(e).__name__, error_detail[:250], exc_info=True)
            self.errorOccurred.emit(AIStatus.ERROR, err_str)
            self.statusUpdate.emit(AIStatus.ERROR, f"Status: API Error - {type(e).__name__}.")
            self._current_processing_had_error = True
        except (genai.types.BlockedPromptException, genai.types.StopCandidateException) as e:
            error_msg = f"Gemini content generation blocked or stopped: {e}"
            logger.error("WORKER_PROCESS: %s", error_msg, exc_info=True)
            self.errorOccurred.emit(AIStatus.CONTENT_BLOCKED, error_msg)
            self.statusUpdate.emit(AIStatus.ERROR, "Status: Content Blocked.")
            self._current_processing_had_error = True
        except Exception as e:
            error_msg = f"Unexpected error in AI worker: {type(e).__name__} - {str(e)[:150]}"
            logger.error("WORKER_PROCESS: %s", error_msg, exc_info=True)
            self.errorOccurred.emit(AIStatus.ERROR, error_msg)
            self.statusUpdate.emit(AIStatus.ERROR, "Status: Unexpected Error.")
            self._current_processing_had_error = True
        finally:
            if not self._current_processing_had_error and self.client and not self._is_stopped:
                self.statusUpdate.emit(AIStatus.READY, "Status: Ready.")

    @pyqtSlot()
    def clear_history_slot(self):
        self.conversation_history = []
        logger.info("Conversation history cleared.")
        self.statusUpdate.emit(AIStatus.HISTORY_CLEARED, "Status: Chat history cleared.")

    @pyqtSlot()
    def stop_processing_slot(self):
        logger.info("WORKER: stop_processing_slot called.")
        self._is_stopped = True


class AIChatUIManager(QObject):
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

        # --- NEW: markdown-it instance ---
        self.md_parser = MarkdownIt("commonmark", {"breaks": True, "html": False})
        # --- END NEW ---

        self._connect_actions_to_manager_slots()
        self._connect_ai_chatbot_signals()

    def _connect_actions_to_manager_slots(self):
        logger.info("AIChatUIManager._connect_actions_to_manager_slots CALLED.")

        settings_action = getattr(self.mw, 'openai_settings_action', None)
        if settings_action is not None and isinstance(settings_action, QAction):
            logger.info("AIChatUIManager: SUCCESS - Found 'openai_settings_action' of type QAction. Connecting...")
            try:
                settings_action.triggered.disconnect(self.on_gemini_settings)
            except TypeError:
                pass
            try:
                settings_action.triggered.connect(self.on_gemini_settings)
                logger.info("AIChatUIManager: Connection to on_gemini_settings SUCCEEDED.")
            except Exception as e:
                logger.error(f"AIChatUIManager: FAILED to connect 'openai_settings_action.triggered' to 'on_gemini_settings': {e}", exc_info=True)
        elif settings_action is not None:
            logger.error(f"AIChatUIManager: Found 'openai_settings_action' but it's not a QAction. Type: {type(settings_action)}")
        else:
            logger.error("AIChatUIManager: CRITICAL - 'openai_settings_action' NOT FOUND on MainWindow (self.mw).")

        ask_fsm_action = getattr(self.mw, 'ask_ai_to_generate_fsm_action', None)
        if ask_fsm_action and isinstance(ask_fsm_action, QAction):
            logger.debug("AIChatUI: Found 'ask_ai_to_generate_fsm_action', connecting to on_ask_ai_to_generate_fsm.")
            try: ask_fsm_action.triggered.disconnect(self.on_ask_ai_to_generate_fsm)
            except TypeError: pass
            ask_fsm_action.triggered.connect(self.on_ask_ai_to_generate_fsm)
        else:
            logger.error("AIChatUIManager: Could not find 'ask_ai_to_generate_fsm_action' or it's not a QAction on MainWindow to connect.")

        clear_chat_action = getattr(self.mw, 'clear_ai_chat_action', None)
        if clear_chat_action and isinstance(clear_chat_action, QAction):
            logger.debug("AIChatUI: Found 'clear_ai_chat_action', connecting to on_clear_ai_chat_history.")
            try: clear_chat_action.triggered.disconnect(self.on_clear_ai_chat_history)
            except TypeError: pass
            clear_chat_action.triggered.connect(self.on_clear_ai_chat_history)
        else:
            logger.error("AIChatUIManager: Could not find 'clear_ai_chat_action' or it's not a QAction on MainWindow to connect.")


    def _connect_ai_chatbot_signals(self):
        if self.mw.ai_chatbot_manager:
            self.mw.ai_chatbot_manager.statusUpdate.connect(self.update_status_display)
            self.mw.ai_chatbot_manager.errorOccurred.connect(self.handle_ai_error)
            self.mw.ai_chatbot_manager.fsmDataReceived.connect(self.handle_fsm_data_from_ai)
            self.mw.ai_chatbot_manager.plainResponseReady.connect(self.handle_plain_ai_response)

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

        if status_enum in [AIStatus.API_KEY_REQUIRED, AIStatus.API_KEY_ERROR, AIStatus.INACTIVE, AIStatus.AUTHENTICATION_ERROR]:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: white; background-color: {COLOR_ACCENT_ERROR}; font-weight: bold;")
        elif status_enum == AIStatus.OFFLINE or status_enum == AIStatus.CONNECTION_ERROR:
            self.ai_chat_status_label.setStyleSheet(f"{base_style} color: {COLOR_TEXT_PRIMARY}; background-color: {COLOR_ACCENT_WARNING};")
        elif status_enum == AIStatus.ERROR or status_enum == AIStatus.CONTENT_BLOCKED or status_enum == AIStatus.RATE_LIMIT:
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
        """
        Renders a token stream from markdown-it to styled HTML suitable for QTextBrowser.
        """
        inline_code_style = f"background-color:{QColor(COLOR_BACKGROUND_MEDIUM).lighter(105).name()}; color:{COLOR_ACCENT_PRIMARY}; padding:1px 4px; border-radius:3px; font-family:Consolas,monospace; font-size: 0.9em;"
        blockquote_style = f"border-left: 2px solid {COLOR_BORDER_MEDIUM}; margin-left: 5px; padding-left: 10px; color: {COLOR_TEXT_SECONDARY}; font-style: italic;"
        
        # --- FIX for BUG-03: Refactor rendering to use markdown-it token stream ---
        # Temporarily override renderers to inject our custom formatting
        
        # Override for ```code``` blocks
        original_fence_renderer = self.md_parser.renderer.rules.get("fence")
        def render_fence(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            token = tokens_list[idx]
            lang = token.info.strip().split(" ")[0] if token.info else ""
            return self._format_code_block(token.content, lang)
        self.md_parser.renderer.rules["fence"] = render_fence

        # Override for `code` inline
        original_code_inline_renderer = self.md_parser.renderer.rules.get("code_inline")
        def render_code_inline(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            return f'<code style="{inline_code_style}">{html.escape(tokens_list[idx].content)}</code>'
        self.md_parser.renderer.rules["code_inline"] = render_code_inline
        
        # Override for > blockquote
        original_blockquote_open_renderer = self.md_parser.renderer.rules.get("blockquote_open")
        def render_blockquote_open(tokens_list: list, idx: int, options: dict, env: dict) -> str:
            return f'<blockquote style="{blockquote_style}">'
        self.md_parser.renderer.rules["blockquote_open"] = render_blockquote_open

        rendered_html = self.md_parser.renderer.render(tokens, self.md_parser.options, {})
        
        # Restore original renderers to avoid side-effects if instance is reused elsewhere
        if original_fence_renderer: self.md_parser.renderer.rules["fence"] = original_fence_renderer
        if original_code_inline_renderer: self.md_parser.renderer.rules["code_inline"] = original_code_inline_renderer
        if original_blockquote_open_renderer: self.md_parser.renderer.rules["blockquote_open"] = original_blockquote_open_renderer
        # --- END FIX for BUG-03 ---
             
        return rendered_html

    def _append_to_chat_display(self, sender: str, message: str):
        if not self.ai_chat_display: return
        timestamp = QTime.currentTime().toString('hh:mm:ss')

        sender_color = COLOR_ACCENT_PRIMARY
        sender_name_raw = sender
        if sender == "You": sender_color = COLOR_ACCENT_SECONDARY
        elif sender == "System Error": sender_color = COLOR_ACCENT_ERROR; sender_name_raw = f"<b>{html.escape(sender)}</b>"
        elif sender == "System": sender_color = QColor(COLOR_TEXT_SECONDARY)

        sender_color_str = sender_color.name() if isinstance(sender_color, QColor) else sender_color
        sender_name_html = sender_name_raw if sender in ["System Error"] else html.escape(sender)

        # --- FIX for BUG-03: Use the new robust markdown rendering logic ---
        tokens = self.md_parser.parse(message)
        final_message_html = self._render_tokens_to_styled_html(tokens)
        # --- END FIX for BUG-03 ---

        bg_msg_color = QColor(sender_color_str).lighter(185).name()
        if sender == "System Error": bg_msg_color = QColor(COLOR_ACCENT_ERROR).lighter(180).name()
        elif sender == "System": bg_msg_color = QColor(COLOR_BACKGROUND_MEDIUM).lighter(105).name()

        html_to_append = (f"<div style='margin-bottom: 10px; padding: 6px 8px; border-left: 3px solid {sender_color_str}; background-color: {bg_msg_color}; border-radius: 4px;'>"
                          f"<div style='margin-bottom: 3px;'>"
                          f"<strong style='color:{sender_color_str}; font-size: 9pt;'>{sender_name_html}</strong>"
                          f"<span style='font-size:7pt; color:{COLOR_TEXT_SECONDARY}; margin-left: 6px;'>[{timestamp}]</span> "
                          f"</div>"
                          f"<div style='padding-left: 2px; line-height:1.4; font-size: 9pt;'>{final_message_html}</div></div>")

        self.ai_chat_display.append(html_to_append)
        self.ai_chat_display.ensureCursorVisible()

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

        msg_box = QMessageBox(self.mw); msg_box.setIcon(QMessageBox.Question); msg_box.setWindowTitle("Add AI Generated FSM")
        msg_box.setText("AI has generated an FSM. Do you want to clear the current diagram before adding the new FSM, or add to the existing one?")
        clear_btn = msg_box.addButton("Clear and Add", QMessageBox.YesRole)
        add_btn = msg_box.addButton("Add to Existing", QMessageBox.NoRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole); msg_box.setDefaultButton(cancel_btn)
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

    @pyqtSlot()
    def on_gemini_settings(self):
        logger.info("AIChatUI: SLOT on_gemini_settings CALLED!")
        if not self.mw.ai_chatbot_manager:
            logger.warning("AIChatUI: AI Chatbot Manager not available for settings within on_gemini_settings.")
            QMessageBox.warning(self.mw, "AI Error", "AI Chatbot Manager is not initialized. Cannot open settings.")
            return

        current_key = self.mw.ai_chatbot_manager.api_key or ""
        key, ok = QInputDialog.getText(
            self.mw,
            "Google AI API Key (Gemini)",
            "Enter your Google AI API Key for Gemini (leave blank to clear):",
            QLineEdit.PasswordEchoOnEdit,
            current_key
        )
        if ok:
            new_key_value = key.strip()
            logger.info(f"AIChatUI: Google AI API Key dialog returned. OK: {ok}, Key: {'SET' if new_key_value else 'EMPTY'}")
            self.mw.ai_chatbot_manager.set_api_key(new_key_value if new_key_value else None)
        else:
            logger.debug("AIChatUI: Google AI API Key dialog cancelled by user.")

    @pyqtSlot()
    def on_clear_ai_chat_history(self):
        logger.info("AIChatUI: on_clear_ai_chat_history CALLED!")
        if self.mw.ai_chatbot_manager:
            reply = QMessageBox.question(self.mw, "Clear Chat History",
                                         "Are you sure you want to clear the entire AI chat history?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
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

class AIChatbotManager(QObject):
    statusUpdate = pyqtSignal(AIStatus, str)
    errorOccurred = pyqtSignal(AIStatus, str)
    fsmDataReceived = pyqtSignal(dict, str)
    plainResponseReady = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.api_key: str | None = None
        self.chatbot_worker: ChatbotWorker | None = None
        self.chatbot_thread: QThread | None = None
        self.last_fsm_request_description: str | None = None
        logger.info("AIChatbotManager initialized.")
        self._current_ai_status = AIStatus.INITIALIZING

    def _update_current_ai_status(self, new_status_enum: AIStatus, status_text: str):
        self._current_ai_status = new_status_enum
        self.statusUpdate.emit(new_status_enum, status_text)
        logger.debug(f"MGR_STATUS_UPDATE: Enum={new_status_enum.name}, Text='{status_text}'")

    @pyqtSlot(AIStatus, str)
    def _handle_worker_error_with_status(self, error_status: AIStatus, error_message: str):
        logger.error(f"MGR_WORKER_ERROR (Status: {error_status.name}): {error_message}")
        self.errorOccurred.emit(error_status, error_message)


    def get_current_ai_status(self) -> AIStatus:
        return self._current_ai_status

    def _cleanup_existing_worker_and_thread(self):
        logger.debug("MGR_CLEANUP: CALLED.")
        if self.chatbot_thread and self.chatbot_thread.isRunning():
            logger.debug("MGR_CLEANUP: Attempting to quit existing thread...")
            if self.chatbot_worker:
                QMetaObject.invokeMethod(self.chatbot_worker, "stop_processing_slot", Qt.BlockingQueuedConnection if QThread.currentThread() != self.chatbot_thread else Qt.DirectConnection)
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


    def set_api_key(self, api_key: str | None):
        old_key_status = 'SET' if self.api_key else 'NONE'
        new_key_status = 'SET' if api_key else 'NONE'
        logger.info(f"MGR_SET_API_KEY (Gemini): New key: '{new_key_status}', Old key: '{old_key_status}'")

        old_api_key_val = self.api_key
        self.api_key = api_key

        if old_api_key_val != self.api_key or \
           (self.api_key and (not self.chatbot_worker or not self.chatbot_thread or not self.chatbot_thread.isRunning())):
            self._cleanup_existing_worker_and_thread()
            if self.api_key:
                self._setup_worker()
            else:
                self._update_current_ai_status(AIStatus.API_KEY_REQUIRED, "Status: Gemini API Key cleared. AI Assistant inactive.")
        elif self.chatbot_worker and self.api_key and self.chatbot_thread and self.chatbot_thread.isRunning():
             QMetaObject.invokeMethod(self.chatbot_worker, "set_api_key_slot", Qt.QueuedConnection,
                                      Q_ARG(str, self.api_key))
        elif not self.api_key:
            self._update_current_ai_status(AIStatus.API_KEY_REQUIRED, "Status: Gemini API Key required.")


    def _setup_worker(self):
        if not self.api_key:
            logger.warning("MGR_SETUP_WORKER: Cannot setup - API key is not set.")
            self._update_current_ai_status(AIStatus.API_KEY_REQUIRED, "Status: API Key required.")
            return

        if self.chatbot_worker or (self.chatbot_thread and self.chatbot_thread.isRunning()):
            logger.info("MGR_SETUP_WORKER: Worker/thread exists or is running. Cleaning up first.")
            self._cleanup_existing_worker_and_thread()

        logger.info("MGR_SETUP_WORKER: Setting up new worker and thread.")
        self.chatbot_thread = QThread(self)
        self.chatbot_worker = ChatbotWorker(self.api_key, parent=None) # Workers in threads should not have a QObject parent on another thread
        self.chatbot_worker.moveToThread(self.chatbot_thread)

        self.chatbot_worker.responseReady.connect(self._handle_worker_response)
        self.chatbot_worker.errorOccurred.connect(self._handle_worker_error_with_status)
        self.chatbot_worker.statusUpdate.connect(self._update_current_ai_status)

        self.chatbot_thread.start()
        logger.info("MGR_SETUP_WORKER: New AI Chatbot worker thread started.")
        self._update_current_ai_status(AIStatus.INITIALIZING, "Status: AI Assistant Initializing...")
        QMetaObject.invokeMethod(self.chatbot_worker, "set_api_key_slot", Qt.QueuedConnection,
                                      Q_ARG(str, self.api_key))


    @pyqtSlot(str, bool)
    def _handle_worker_response(self, ai_response_content: str, was_fsm_generation_attempt: bool):
        logger.info(f"MGR_HANDLE_WORKER_RESPONSE: Received from worker. Was FSM attempt: {was_fsm_generation_attempt}")

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

        logger.debug("MGR_HANDLE_WORKER_RESPONSE: Emitting plainResponseReady.")
        self.plainResponseReady.emit(ai_response_content)


    def _prepare_and_send_to_worker(self, user_message_text: str, is_fsm_gen_specific: bool = False):
        logger.info(f"MGR_PREP_SEND: For: '{user_message_text[:30]}...', FSM_specific_req: {is_fsm_gen_specific}")

        if not self.api_key:
            err_msg = "Gemini API Key not set. Configure in Settings."
            logger.warning("MGR_PREP_SEND: API Key not set.")
            self.errorOccurred.emit(AIStatus.API_KEY_REQUIRED, err_msg)
            self._update_current_ai_status(AIStatus.API_KEY_REQUIRED, "Status: API Key required.")
            if self.parent_window and hasattr(self.parent_window, 'ai_chat_ui_manager') and self.parent_window.ai_chat_ui_manager:
                self.parent_window.ai_chat_ui_manager._append_to_chat_display("System Error", err_msg)
            return

        if not self.chatbot_worker or not self.chatbot_thread or not self.chatbot_thread.isRunning():
            logger.warning("MGR_PREP_SEND: Worker/Thread not ready.")
            if self.api_key and (not self.chatbot_thread or not self.chatbot_thread.isRunning()):
                 logger.info("MGR_PREP_SEND: Attempting to re-setup worker because it's not running.")
                 self._setup_worker()

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
            QMetaObject.invokeMethod(self.chatbot_worker, "set_diagram_context_slot", Qt.QueuedConnection,
                                     Q_ARG(str, effective_diagram_json_str))
            QMetaObject.invokeMethod(self.chatbot_worker, "process_message_slot", Qt.QueuedConnection,
                                     Q_ARG(str, user_message_text),
                                     Q_ARG(bool, is_fsm_gen_specific))
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

    def clear_conversation_history(self):
        logger.info("MGR: clear_conversation_history CALLED.")
        if self.chatbot_worker and self.chatbot_thread and self.chatbot_thread.isRunning():
            QMetaObject.invokeMethod(self.chatbot_worker, "clear_history_slot", Qt.QueuedConnection)
            logger.debug("MGR: clear_history invoked on worker.")
            if self.parent_window and hasattr(self.parent_window, 'ai_chat_ui_manager'):
                self.parent_window.ai_chat_ui_manager._code_snippet_cache.clear()
        else:
            if not self.api_key:
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
        logger.info(f"MGR_NET_STATUS: Online status: {is_online}")
        if not self.api_key:
            if is_online:
                self._update_current_ai_status(AIStatus.API_KEY_REQUIRED, "Status: Online, Gemini API Key required.")
            else:
                self._update_current_ai_status(AIStatus.OFFLINE, "Status: Offline, Gemini API Key required.")
            return

        if is_online:
            if not self.chatbot_thread or not self.chatbot_thread.isRunning():
                logger.info("MGR_NET_STATUS: Network online, API key present, attempting worker setup.")
                self._setup_worker()
            else:
                if self.chatbot_worker and self.chatbot_worker.client:
                    self._update_current_ai_status(AIStatus.READY, "Status: Online and Ready.")
                elif self.chatbot_worker and not self.chatbot_worker.client:
                    self._update_current_ai_status(AIStatus.API_KEY_ERROR, "Status: Online, API Key Error.")
                else:
                    self._update_current_ai_status(AIStatus.INITIALIZING, "Status: Online, Initializing...")
        else:
            self._update_current_ai_status(AIStatus.OFFLINE, "Status: Offline. Gemini AI features unavailable.")