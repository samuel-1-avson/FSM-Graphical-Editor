# bsm_designer_project/config.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
import json

# --- Configuration ---
APP_VERSION = "2.0.0" # Version updated for new features
APP_NAME = "Brain State Machine Designer"
FILE_EXTENSION = ".bsm"
FILE_FILTER = f"Brain State Machine Files (*{FILE_EXTENSION});;All Files (*)"

# --- Execution Environments and Snippets ---
EXECUTION_ENV_PYTHON_GENERIC = "Python (Generic Simulation)"
EXECUTION_ENV_ARDUINO_CPP = "Arduino (C++)"
EXECUTION_ENV_RASPBERRYPI_PYTHON = "RaspberryPi (Python)"
EXECUTION_ENV_MICROPYTHON = "MicroPython"
EXECUTION_ENV_C_GENERIC = "C (Generic Embedded)"

MIME_TYPE_BSM_ITEMS = "application/x-bsm-designer-items"
MIME_TYPE_BSM_TEMPLATE = "application/x-bsm-template"
DEFAULT_EXECUTION_ENV = EXECUTION_ENV_PYTHON_GENERIC

MECHATRONICS_SNIPPETS = {
    "Python (Generic Simulation)": {
        "actions": {
            "Set Variable": "my_variable = 10",
            "Increment Counter": "counter = counter + 1",
            "Print Message": "print('Hello from FSM!')",
            "Log with Tick": "print(f'Current tick: {current_tick}, State: {sm.current_state.id if sm and sm.current_state else 'N/A'}')",
        },
        "conditions": {
            "Variable Equals": "my_variable == 10",
            "Counter Greater Than": "counter > 5",
        },
        "events": {
            "Timer Expired": "timer_expired",
            "Button Pressed": "button_pressed",
            "Sensor Detect": "sensor_detect_obj_A",
        }
    },
    "Arduino (C++)": {
        "actions": {
            "Digital Write HIGH": "digitalWrite(LED_PIN, HIGH);",
            "Digital Write LOW": "digitalWrite(LED_PIN, LOW);",
            "Analog Write": "analogWrite(MOTOR_PIN, speed_value);",
            "Serial Print": "Serial.println(\"Hello from Arduino FSM!\");",
            "Delay": "delay(1000); // 1 second delay"
        },
        "conditions": {
            "Digital Read HIGH": "digitalRead(BUTTON_PIN) == HIGH",
            "Analog Read Threshold": "analogRead(SENSOR_PIN) > 512",
            "Variable Check": "my_arduino_variable == SOME_VALUE"
        },
         "events": {
            "Timer Interrupt": "ISR_TIMER_EXPIRED_FLAG",
            "Button Change": "BUTTON_CHANGE_EVENT",
        }
    },
     "C (Generic Embedded)": {
        "actions": {
            "Set GPIO Pin High": "HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET); // Example for STM32 HAL",
            "Set GPIO Pin Low": "HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);",
            "Toggle GPIO Pin": "HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);",
            "Send UART Message": "HAL_UART_Transmit(&huart1, (uint8_t*)\"Msg\\r\\n\", 6, 100);",
            "Basic printf (if stdio redirected)": "printf(\"Event occurred\\n\");"
        },
        "conditions": {
            "Check GPIO Pin State": "HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_0) == GPIO_PIN_SET",
            "Check Flag Variable": "global_event_flag == 1",
        },
        "events": {
            "External Interrupt": "EXTI0_IRQ_FLAG",
            "Timer Overflow": "TIM2_UPDATE_FLAG",
        }
    },
    "RaspberryPi (Python)": {
        "actions": {
            "GPIO Set High": "import RPi.GPIO as GPIO\nGPIO.setmode(GPIO.BCM) # or GPIO.BOARD\nGPIO.setup(17, GPIO.OUT)\nGPIO.output(17, GPIO.HIGH)",
            "GPIO Set Low": "import RPi.GPIO as GPIO\nGPIO.output(17, GPIO.LOW)",
            "Print Message": "print('RPi FSM action')",
        },
        "conditions": {
            "GPIO Read High": "import RPi.GPIO as GPIO\nGPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)\nGPIO.input(18) == GPIO.HIGH",
        },
        "events": {
            "Button Press RPi": "rpi_button_event",
        }
    },
    "MicroPython": {
        "actions": {
            "Pin On": "from machine import Pin\nled = Pin(2, Pin.OUT)\nled.on()",
            "Pin Off": "from machine import Pin\nled = Pin(2, Pin.OUT)\nled.off()",
            "Toggle Pin": "from machine import Pin\nled = Pin(2, Pin.OUT)\nled.value(not led.value())",
        },
        "conditions": {
            "Pin Value High": "from machine import Pin\nbutton = Pin(0, Pin.IN, Pin.PULL_UP)\nbutton.value() == 1",
        },
        "events": {
            "IRQ Triggered MicroPy": "micropy_irq_flag_event",
        }
    },
    "Text": { # For comments or generic text fields
        "actions": {}, "conditions": {}, "events": {}
    }
}

FSM_TEMPLATES_BUILTIN_JSON_STR = """
{
    "DebounceLogic": {
        "name": "Debounce Logic",
        "description": "A simple debounce pattern for an input signal.",
        "icon_resource": ":/icons/debounce_icon.png",
        "states": [
            {"name": "Unstable", "description": "Input is currently unstable or bouncing."},
            {"name": "Waiting", "entry_action": "start_debounce_timer()"},
            {"name": "Stable", "description": "Input is considered stable."}
        ],
        "transitions": [
            {"source": "Unstable", "target": "Waiting", "event": "input_change"},
            {"source": "Waiting", "target": "Stable", "event": "debounce_timer_expired"},
            {"source": "Waiting", "target": "Unstable", "event": "input_change_while_waiting", "control_offset_y": 60},
            {"source": "Stable", "target": "Unstable", "event": "input_goes_unstable_again", "control_offset_y": -60}
        ],
        "comments": [
            {"text": "Debounce timer should be set appropriately for your hardware.", "width": 180}
        ]
    },
    "Blinker": {
        "name": "Simple Blinker",
        "description": "Alternates between On and Off states based on a timer.",
        "icon_resource": ":/icons/blinker_icon.png",
        "states": [
            {"name": "LedOff", "is_initial": true, "entry_action": "set_led_off()\\nstart_timer(OFF_DURATION)"},
            {"name": "LedOn", "entry_action": "set_led_on()\\nstart_timer(ON_DURATION)"}
        ],
        "transitions": [
            {"source": "LedOff", "target": "LedOn", "event": "timer_expired"},
            {"source": "LedOn", "target": "LedOff", "event": "timer_expired"}
        ],
        "comments": [
            {"text": "Define ON_DURATION and OFF_DURATION variables in your simulation environment.", "width": 200}
        ]
    }
}
"""
try:
    FSM_TEMPLATES_BUILTIN = json.loads(FSM_TEMPLATES_BUILTIN_JSON_STR)
except json.JSONDecodeError:
    FSM_TEMPLATES_BUILTIN = {}


# --- THEME AND COLOR CONFIGURATION ---

THEME_DATA_LIGHT = {
    "COLOR_BACKGROUND_APP": "#ECEFF1", "COLOR_BACKGROUND_LIGHT": "#FAFAFA",
    "COLOR_BACKGROUND_MEDIUM": "#E0E0E0", "COLOR_BACKGROUND_DARK": "#BDBDBD",
    "COLOR_BACKGROUND_EDITOR_DARK": "#263238", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#ECEFF1",
    "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#90A4AE", "COLOR_BACKGROUND_DIALOG": "#FFFFFF",
    "COLOR_TEXT_PRIMARY": "#212121", "COLOR_TEXT_SECONDARY": "#757575",
    "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#0277BD",
    "COLOR_ACCENT_PRIMARY_LIGHT": "#B3E5FC", "COLOR_ACCENT_SECONDARY": "#FF8F00",
    "COLOR_ACCENT_SUCCESS": "#4CAF50", "COLOR_ACCENT_WARNING": "#FFC107",
    "COLOR_ACCENT_ERROR": "#D32F2F", "COLOR_BORDER_LIGHT": "#CFD8DC",
    "COLOR_BORDER_MEDIUM": "#90A4AE", "COLOR_BORDER_DARK": "#607D8B",
    "COLOR_ITEM_STATE_DEFAULT_BG": "#E3F2FD", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#64B5F6",
    "COLOR_ITEM_TRANSITION_DEFAULT": "#00796B", "COLOR_ITEM_COMMENT_BG": "#FFF9C4",
    "COLOR_ITEM_COMMENT_BORDER": "#FFEE58", "COLOR_GRID_MINOR": "#ECEFF1",
    "COLOR_GRID_MAJOR": "#CFD8DC", "COLOR_DRAGGABLE_BUTTON_BG": "#E8EAF6",
    "COLOR_DRAGGABLE_BUTTON_BORDER": "#C5CAE9", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#B9D9EB",
    "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#0277BD", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#98BAD6"
}

THEME_DATA_DARK = {
    "COLOR_BACKGROUND_APP": "#263238", "COLOR_BACKGROUND_LIGHT": "#37474F",
    "COLOR_BACKGROUND_MEDIUM": "#455A64", "COLOR_BACKGROUND_DARK": "#546E7A",
    "COLOR_BACKGROUND_EDITOR_DARK": "#1A2428", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "#CFD8DC",
    "COLOR_TEXT_EDITOR_DARK_SECONDARY": "#78909C", "COLOR_BACKGROUND_DIALOG": "#37474F",
    "COLOR_TEXT_PRIMARY": "#ECEFF1", "COLOR_TEXT_SECONDARY": "#B0BEC5",
    "COLOR_TEXT_ON_ACCENT": "#FFFFFF", "COLOR_ACCENT_PRIMARY": "#4FC3F7",
    "COLOR_ACCENT_PRIMARY_LIGHT": "#81D4FA", "COLOR_ACCENT_SECONDARY": "#FFB74D",
    "COLOR_ACCENT_SUCCESS": "#81C784", "COLOR_ACCENT_WARNING": "#FFD54F",
    "COLOR_ACCENT_ERROR": "#E57373", "COLOR_BORDER_LIGHT": "#546E7A",
    "COLOR_BORDER_MEDIUM": "#78909C", "COLOR_BORDER_DARK": "#90A4AE",
    "COLOR_ITEM_STATE_DEFAULT_BG": "#4A6572", "COLOR_ITEM_STATE_DEFAULT_BORDER": "#78909C",
    "COLOR_ITEM_TRANSITION_DEFAULT": "#4DB6AC", "COLOR_ITEM_COMMENT_BG": "#424242",
    "COLOR_ITEM_COMMENT_BORDER": "#616161", "COLOR_GRID_MINOR": "#455A64",
    "COLOR_GRID_MAJOR": "#546E7A", "COLOR_DRAGGABLE_BUTTON_BG": "#37474F",
    "COLOR_DRAGGABLE_BUTTON_BORDER": "#546E7A", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "#546E7A",
    "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "#4FC3F7", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "#62757f"
}

THEME_KEYS = list(THEME_DATA_LIGHT.keys())
THEME_KEY_LABELS = {
    "COLOR_BACKGROUND_APP": "App: Main Background", "COLOR_BACKGROUND_LIGHT": "App: Light Background",
    "COLOR_BACKGROUND_MEDIUM": "App: Medium Background", "COLOR_BACKGROUND_DARK": "App: Dark Background",
    "COLOR_BACKGROUND_EDITOR_DARK": "Editor: Background", "COLOR_TEXT_EDITOR_DARK_PRIMARY": "Editor: Primary Text",
    "COLOR_TEXT_EDITOR_DARK_SECONDARY": "Editor: Secondary Text", "COLOR_BACKGROUND_DIALOG": "Dialog: Background",
    "COLOR_TEXT_PRIMARY": "Text: Primary", "COLOR_TEXT_SECONDARY": "Text: Secondary",
    "COLOR_TEXT_ON_ACCENT": "Text: On Accent", "COLOR_ACCENT_PRIMARY": "Accent: Primary",
    "COLOR_ACCENT_PRIMARY_LIGHT": "Accent: Primary Light", "COLOR_ACCENT_SECONDARY": "Accent: Secondary",
    "COLOR_ACCENT_SUCCESS": "Accent: Success", "COLOR_ACCENT_WARNING": "Accent: Warning",
    "COLOR_ACCENT_ERROR": "Accent: Error", "COLOR_BORDER_LIGHT": "Border: Light",
    "COLOR_BORDER_MEDIUM": "Border: Medium", "COLOR_BORDER_DARK": "Border: Dark",
    "COLOR_ITEM_STATE_DEFAULT_BG": "Item: State Background", "COLOR_ITEM_STATE_DEFAULT_BORDER": "Item: State Border",
    "COLOR_ITEM_TRANSITION_DEFAULT": "Item: Transition", "COLOR_ITEM_COMMENT_BG": "Item: Comment Background",
    "COLOR_ITEM_COMMENT_BORDER": "Item: Comment Border", "COLOR_GRID_MINOR": "Canvas: Minor Grid",
    "COLOR_GRID_MAJOR": "Canvas: Major Grid", "COLOR_DRAGGABLE_BUTTON_BG": "Drag Button: Background",
    "COLOR_DRAGGABLE_BUTTON_BORDER": "Drag Button: Border", "COLOR_DRAGGABLE_BUTTON_HOVER_BG": "Drag Button: Hover BG",
    "COLOR_DRAGGABLE_BUTTON_HOVER_BORDER": "Drag Button: Hover Border", "COLOR_DRAGGABLE_BUTTON_PRESSED_BG": "Drag Button: Pressed BG"
}

# --- CORRECTED: Initialize global color variables as empty strings ---
# These will be populated at runtime by DYNAMIC_UPDATE_COLORS_FROM_THEME
for key in THEME_KEYS:
    globals()[key] = ""

COLOR_ITEM_STATE_SELECTION_BG = ""
COLOR_ITEM_STATE_SELECTION_BORDER = ""
COLOR_ITEM_TRANSITION_SELECTION = ""
COLOR_SNAP_GUIDELINE = QColor(Qt.red)
COLOR_PY_SIM_STATE_ACTIVE = QColor("#4CAF50")
COLOR_PY_SIM_STATE_ACTIVE_PEN_WIDTH = 2.5


def DYNAMIC_UPDATE_COLORS_FROM_THEME(theme_data: dict):
    """
    Populates the global color variables in this module from a theme dictionary.
    This function is the single source of truth for setting theme colors at runtime.
    """
    global COLOR_PY_SIM_STATE_ACTIVE, COLOR_ITEM_STATE_SELECTION_BG, \
           COLOR_ITEM_STATE_SELECTION_BORDER, COLOR_ITEM_TRANSITION_SELECTION

    for key, value in theme_data.items():
        if key in globals():
            globals()[key] = value

    COLOR_PY_SIM_STATE_ACTIVE = QColor(globals().get("COLOR_ACCENT_SUCCESS"))
    
    accent_secondary_color = QColor(globals().get("COLOR_ACCENT_SECONDARY", "#FF8F00"))
    COLOR_ITEM_STATE_SELECTION_BG = accent_secondary_color.lighter(180 if accent_secondary_color.lightnessF() < 0.5 else 130).name()
    COLOR_ITEM_STATE_SELECTION_BORDER = accent_secondary_color.name()
    
    accent_primary_color = QColor(globals().get("COLOR_ACCENT_PRIMARY", "#0277BD"))
    COLOR_ITEM_TRANSITION_SELECTION = accent_primary_color.lighter(160 if accent_primary_color.lightnessF() < 0.5 else 130).name()

# Call once at import time to ensure variables are not empty before first theme application
DYNAMIC_UPDATE_COLORS_FROM_THEME(THEME_DATA_LIGHT)


APP_FONT_FAMILY = "Segoe UI, Arial, sans-serif"
APP_FONT_SIZE_STANDARD = "9pt"
APP_FONT_SIZE_SMALL = "8pt"
APP_FONT_SIZE_EDITOR = "10pt"
DEFAULT_STATE_SHAPE = "rectangle"
DEFAULT_STATE_BORDER_STYLE = Qt.SolidLine
DEFAULT_STATE_BORDER_WIDTH = 1.8
DEFAULT_TRANSITION_LINE_STYLE = Qt.SolidLine
DEFAULT_TRANSITION_LINE_WIDTH = 2.2
DEFAULT_TRANSITION_ARROWHEAD = "filled"


STYLE_SHEET_GLOBAL = "/* This string will be REBUILT by main.py when theme changes */"

def GET_CURRENT_STYLE_SHEET():
    """Generates the application-wide stylesheet based on current dynamic color variables."""
    # This function uses the dynamically set global variables (e.g., COLOR_BACKGROUND_APP)
    is_dark = QColor(COLOR_BACKGROUND_APP).lightnessF() < 0.5
    
    # Define gradient stops based on theme
    grad_stop_1 = QColor(COLOR_BACKGROUND_MEDIUM).lighter(105 if is_dark else 102).name()
    grad_stop_2 = QColor(COLOR_BACKGROUND_MEDIUM).darker(102 if is_dark else 98).name()

    return f"""
    QWidget {{
        font-family: {APP_FONT_FAMILY};
        font-size: {APP_FONT_SIZE_STANDARD};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QMainWindow {{
        background-color: {COLOR_BACKGROUND_APP};
    }}
    QDockWidget::title {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {grad_stop_1}, stop:1 {grad_stop_2});
        padding: 6px 10px 6px 48px;
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-bottom: 2px solid {globals().get("COLOR_ACCENT_PRIMARY", "#0277BD")};
        font-weight: bold;
        color: {COLOR_TEXT_PRIMARY};
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
    }}
    QDockWidget {{
        border: 1px solid {COLOR_BORDER_LIGHT};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QDockWidget QWidget {{
        color: {COLOR_TEXT_PRIMARY};
        background-color: {COLOR_BACKGROUND_APP};
    }}
    QDockWidget::close-button {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 6px;
        top: 4px;
    }}
    QDockWidget::float-button {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 26px;
        top: 4px;
    }}
    QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
        background-color: {COLOR_BACKGROUND_DARK};
    }}
    QToolBar {{
        background-color: {COLOR_BACKGROUND_MEDIUM};
        border-bottom: 1px solid {COLOR_BORDER_LIGHT};
        padding: 2px;
        spacing: 3px;
    }}
    QToolButton {{
        background-color: transparent;
        color: {COLOR_TEXT_PRIMARY};
        padding: 4px 6px;
        margin: 0px;
        border: 1px solid transparent;
        border-radius: 3px;
    }}
    QToolButton:hover, QDockWidget#ElementsPaletteDock QToolButton:hover {{
        background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
        border: 1px solid {COLOR_ACCENT_PRIMARY};
        color: {QColor(COLOR_ACCENT_PRIMARY).darker(130).name() if QColor(COLOR_ACCENT_PRIMARY_LIGHT).lightnessF() > 0.6 else COLOR_TEXT_ON_ACCENT};
    }}
    QToolButton:pressed, QDockWidget#ElementsPaletteDock QToolButton:pressed {{
        background-color: {COLOR_ACCENT_PRIMARY};
        color: {COLOR_TEXT_ON_ACCENT};
    }}
    QToolButton:checked, QDockWidget#ElementsPaletteDock QToolButton:checked {{
        background-color: {COLOR_ACCENT_PRIMARY};
        color: {COLOR_TEXT_ON_ACCENT};
        border: 1px solid {QColor(COLOR_ACCENT_PRIMARY).darker(120).name()};
    }}
    QToolBar QToolButton:disabled {{
        color: {COLOR_TEXT_SECONDARY};
        background-color: transparent;
    }}
    QMenuBar {{
        background-color: {COLOR_BACKGROUND_MEDIUM};
        color: {COLOR_TEXT_PRIMARY};
        border-bottom: 1px solid {COLOR_BORDER_LIGHT};
        padding: 2px;
    }}
    QMenuBar::item {{
        background-color: transparent;
        padding: 4px 10px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QMenuBar::item:selected {{
        background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
        color: {QColor(COLOR_ACCENT_PRIMARY).darker(130).name() if QColor(COLOR_ACCENT_PRIMARY_LIGHT).lightnessF() > 0.6 else COLOR_TEXT_PRIMARY};
    }}
    QMenuBar::item:pressed {{
        background-color: {COLOR_ACCENT_PRIMARY};
        color: {COLOR_TEXT_ON_ACCENT};
    }}
    QMenu {{
        background-color: {COLOR_BACKGROUND_DIALOG};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_MEDIUM};
        border-radius: 3px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 5px 25px 5px 25px;
        border-radius: 3px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QMenu::item:selected {{
        background-color: {COLOR_ACCENT_PRIMARY};
        color: {COLOR_TEXT_ON_ACCENT};
    }}
    QMenu::separator {{
        height: 1px;
        background: {COLOR_BORDER_LIGHT};
        margin: 4px 6px;
    }}
    QMenu::icon {{
        padding-left: 5px;
    }}
    QStatusBar {{
        background-color: {COLOR_BACKGROUND_MEDIUM};
        color: {COLOR_TEXT_PRIMARY};
        border-top: 1px solid {COLOR_BORDER_LIGHT};
        padding: 2px 4px;
    }}
    QStatusBar::item {{
        border: none;
        margin: 0 2px;
    }}
    QLabel#StatusLabel, QLabel#MatlabStatusLabel, QLabel#PySimStatusLabel, QLabel#AIChatStatusLabel, QLabel#InternetStatusLabel,
    QLabel#MainOpStatusLabel, QLabel#IdeFileStatusLabel,
    QMainWindow QLabel[objectName$="StatusLabel"],
    QLabel#ZoomStatusLabel, QLabel#InteractionModeStatusLabel
    {{
         padding: 1px 4px;
         font-size: {APP_FONT_SIZE_SMALL};
         border-radius: 2px;
         color: {COLOR_TEXT_SECONDARY};
    }}
    QLabel#CpuStatusLabel, QLabel#RamStatusLabel, QLabel#GpuStatusLabel {{
        font-size: {APP_FONT_SIZE_SMALL};
        padding: 1px 4px;
        min-width: 60px;
        border: 1px solid {COLOR_BORDER_LIGHT};
        background-color: {COLOR_BACKGROUND_APP};
        border-radius: 2px;
        color: {COLOR_TEXT_SECONDARY};
    }}
    QDialog {{
        background-color: {COLOR_BACKGROUND_DIALOG};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QDialog QLabel, QDialog QCheckBox, QDialog QRadioButton, QDialog QSpinBox, QDialog QDoubleSpinBox, QDialog QFontComboBox {{
        color: {COLOR_TEXT_PRIMARY};
    }}
    QLabel {{
        color: {COLOR_TEXT_PRIMARY};
        background-color: transparent;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {QColor(COLOR_BACKGROUND_DIALOG).lighter(102 if QColor(COLOR_BACKGROUND_DIALOG).lightnessF() > 0.5 else 115).name()};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_MEDIUM};
        border-radius: 3px;
        padding: 5px 7px;
        font-size: {APP_FONT_SIZE_STANDARD};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1.5px solid {COLOR_ACCENT_PRIMARY};
        outline: none;
    }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
        background-color: {COLOR_BACKGROUND_MEDIUM};
        color: {COLOR_TEXT_SECONDARY};
        border-color: {COLOR_BORDER_LIGHT};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 22px;
        border-left-width: 1px;
        border-left-color: {COLOR_BORDER_MEDIUM};
        border-left-style: solid;
        border-top-right-radius: 2px;
        border-bottom-right-radius: 2px;
        background-color: {QColor(COLOR_BACKGROUND_LIGHT).lighter(102 if QColor(COLOR_BACKGROUND_LIGHT).lightnessF() > 0.5 else 110).name()};
    }}
    QComboBox::drop-down:hover {{
        background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
    }}
    QComboBox::down-arrow {{
         image: url(:/icons/arrow_down.png);
         width: 10px; height:10px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLOR_BACKGROUND_DIALOG};
        border: 1px solid {COLOR_BORDER_MEDIUM};
        selection-background-color: {COLOR_ACCENT_PRIMARY};
        selection-color: {COLOR_TEXT_ON_ACCENT};
        border-radius: 2px;
        padding: 1px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QPushButton {{
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_MEDIUM};
        padding: 6px 15px;
        border-radius: 4px;
        min-height: 22px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {QColor(grad_stop_1).lighter(105).name()}, stop: 1 {QColor(grad_stop_2).lighter(105).name()});
        border-color: {COLOR_BORDER_DARK};
    }}
    QPushButton:pressed {{
        background-color: {QColor(COLOR_BACKGROUND_DARK).name()};
    }}
    QPushButton:disabled {{
        background-color: {QColor(COLOR_BACKGROUND_LIGHT).darker(102 if QColor(COLOR_BACKGROUND_LIGHT).lightnessF() < 0.5 else 95).name()};
        color: {COLOR_TEXT_SECONDARY};
        border-color: {COLOR_BORDER_LIGHT};
    }}
    QDialogButtonBox QPushButton {{
        min-width: 80px;
    }}
    QDialogButtonBox QPushButton[text="OK"], QDialogButtonBox QPushButton[text="OK & Save"], QDialogButtonBox QPushButton[text="Apply & Close"],
    QDialogButtonBox QPushButton[text="Save"], QDialogButtonBox QPushButton[text="Apply"]
    {{
        background-color: {COLOR_ACCENT_PRIMARY};
        color: {COLOR_TEXT_ON_ACCENT};
        border-color: {QColor(COLOR_ACCENT_PRIMARY).darker(120).name()};
        font-weight: bold;
    }}
    QDialogButtonBox QPushButton[text="OK"]:hover, QDialogButtonBox QPushButton[text="OK & Save"]:hover, QDialogButtonBox QPushButton[text="Apply & Close"]:hover,
    QDialogButtonBox QPushButton[text="Save"]:hover, QDialogButtonBox QPushButton[text="Apply"]:hover
    {{
        background-color: {QColor(COLOR_ACCENT_PRIMARY).lighter(110).name()};
    }}
    QDialogButtonBox QPushButton[text="Cancel"], QDialogButtonBox QPushButton[text="Discard"],
    QDialogButtonBox QPushButton[text="Close"]
    {{
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
        color: {COLOR_TEXT_PRIMARY};
        border-color: {COLOR_BORDER_MEDIUM};
    }}
    QDialogButtonBox QPushButton[text="Cancel"]:hover, QDialogButtonBox QPushButton[text="Discard"]:hover,
    QDialogButtonBox QPushButton[text="Close"]:hover
    {{
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {QColor(grad_stop_1).darker(105).name()}, stop: 1 {QColor(grad_stop_2).darker(105).name()});
    }}
    QGroupBox {{
        background-color: transparent;
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-radius: 4px;
        margin-top: 10px;
        padding: 10px 8px 8px 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 10px;
        background-color: {COLOR_BACKGROUND_APP};
        color: {COLOR_ACCENT_PRIMARY};
        font-weight: bold;
        border-radius: 2px;
    }}
    QTabWidget::pane {{
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-top: none;
        border-bottom-left-radius: 3px;
        border-bottom-right-radius: 3px;
        background-color: {COLOR_BACKGROUND_DIALOG};
        padding: 6px;
    }}
    QTabBar::tab {{
        background: {COLOR_BACKGROUND_MEDIUM};
        color: {COLOR_TEXT_SECONDARY};
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-bottom-color: {COLOR_BACKGROUND_DIALOG};
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
        padding: 6px 15px;
        margin-right: 1px;
        min-width: 70px;
    }}
    QTabBar::tab:selected {{
        background: {COLOR_BACKGROUND_DIALOG};
        color: {COLOR_TEXT_PRIMARY};
        font-weight: bold;
        border-bottom-color: {COLOR_BACKGROUND_DIALOG};
    }}
    QTabBar::tab:!selected:hover {{
        background: {COLOR_ACCENT_PRIMARY_LIGHT};
        color: {COLOR_TEXT_PRIMARY};
        border-bottom-color: {COLOR_BORDER_LIGHT};
    }}
    QCheckBox {{
        spacing: 8px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
    }}
    QCheckBox::indicator:unchecked {{
        border: 1px solid {COLOR_BORDER_MEDIUM};
        border-radius: 2px;
        background-color: {QColor(COLOR_BACKGROUND_DIALOG).lighter(102 if QColor(COLOR_BACKGROUND_DIALOG).lightnessF() > 0.5 else 110).name()};
    }}
    QCheckBox::indicator:unchecked:hover {{
        border: 1px solid {COLOR_ACCENT_PRIMARY};
    }}
    QCheckBox::indicator:checked {{
        border: 1px solid {QColor(COLOR_ACCENT_PRIMARY).darker(120).name()};
        border-radius: 2px;
        background-color: {COLOR_ACCENT_PRIMARY};
        image: url(:/icons/check.png);
    }}
    QCheckBox::indicator:checked:hover {{
        background-color: {QColor(COLOR_ACCENT_PRIMARY).lighter(110).name()};
    }}
    QTextEdit#LogOutputWidget, QTextEdit#PySimActionLog, QTextBrowser#AIChatDisplay,
    QPlainTextEdit#ActionCodeEditor, QTextEdit#IDEOutputConsole, QPlainTextEdit#StandaloneCodeEditor,
    QTextEdit#SubFSMJsonEditor, QPlainTextEdit#LivePreviewEditor
    {{
         font-family: Consolas, 'Courier New', monospace;
         font-size: {APP_FONT_SIZE_EDITOR};
         background-color: {COLOR_BACKGROUND_EDITOR_DARK};
         color: {COLOR_TEXT_EDITOR_DARK_PRIMARY};
         border: 1px solid {COLOR_BORDER_DARK};
         border-radius: 3px;
         padding: 6px;
         selection-background-color: {QColor(COLOR_ACCENT_PRIMARY).darker(110).name()};
         selection-color: {COLOR_TEXT_ON_ACCENT};
    }}
    QScrollBar:vertical {{
         border: 1px solid {COLOR_BORDER_LIGHT};
         background: {QColor(COLOR_BACKGROUND_LIGHT).lighter(102 if QColor(COLOR_BACKGROUND_LIGHT).lightnessF() > 0.5 else 110).name()};
         width: 14px;
         margin: 0px;
    }}
    QScrollBar::handle:vertical {{
         background: {COLOR_BORDER_DARK};
         min-height: 25px;
         border-radius: 7px;
    }}
    QScrollBar::handle:vertical:hover {{
         background: {QColor(COLOR_BORDER_DARK).lighter(120).name()};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
         height: 0px;
         background: transparent;
    }}
    QScrollBar:horizontal {{
         border: 1px solid {COLOR_BORDER_LIGHT};
         background: {QColor(COLOR_BACKGROUND_LIGHT).lighter(102 if QColor(COLOR_BACKGROUND_LIGHT).lightnessF() > 0.5 else 110).name()};
         height: 14px;
         margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
         background: {COLOR_BORDER_DARK};
         min-width: 25px;
         border-radius: 7px;
    }}
    QScrollBar::handle:horizontal:hover {{
         background: {QColor(COLOR_BORDER_DARK).lighter(120).name()};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
         width: 0px;
         background: transparent;
    }}

    /* Editor specific scrollbars */
    QTextEdit#LogOutputWidget QScrollBar:vertical, QTextEdit#PySimActionLog QScrollBar:vertical,
    QTextBrowser#AIChatDisplay QScrollBar:vertical, QPlainTextEdit#ActionCodeEditor QScrollBar:vertical,
    QTextEdit#IDEOutputConsole QScrollBar:vertical, QPlainTextEdit#StandaloneCodeEditor QScrollBar:vertical,
    QTextEdit#SubFSMJsonEditor QScrollBar:vertical
    {{
         border: 1px solid {COLOR_BORDER_DARK};
         background: {QColor(COLOR_BACKGROUND_EDITOR_DARK).lighter(110).name()};
    }}
    QTextEdit#LogOutputWidget QScrollBar::handle:vertical, QTextEdit#PySimActionLog QScrollBar::handle:vertical,
    QTextBrowser#AIChatDisplay QScrollBar::handle:vertical, QPlainTextEdit#ActionCodeEditor QScrollBar::handle:vertical,
    QTextEdit#IDEOutputConsole QScrollBar::handle:vertical, QPlainTextEdit#StandaloneCodeEditor QScrollBar::vertical,
    QTextEdit#SubFSMJsonEditor QScrollBar::handle:vertical
    {{
         background: {COLOR_TEXT_EDITOR_DARK_SECONDARY};
    }}
    QTextEdit#LogOutputWidget QScrollBar::handle:vertical:hover, QTextEdit#PySimActionLog QScrollBar::handle:vertical:hover,
    QTextBrowser#AIChatDisplay QScrollBar::handle:vertical:hover, QPlainTextEdit#ActionCodeEditor QScrollBar::handle:vertical:hover,
    QTextEdit#IDEOutputConsole QScrollBar::handle:vertical:hover, QPlainTextEdit#StandaloneCodeEditor QScrollBar::handle:vertical:hover,
    QTextEdit#SubFSMJsonEditor QScrollBar::handle:vertical:hover
    {{
         background: {QColor(COLOR_TEXT_EDITOR_DARK_SECONDARY).lighter(120).name()};
    }}

    QPushButton#SnippetButton {{
        background-color: {COLOR_ACCENT_SECONDARY};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {QColor(COLOR_ACCENT_SECONDARY).darker(130).name()};
        font-weight: normal;
        padding: 4px 8px;
        min-height: 0;
    }}
    QPushButton#SnippetButton:hover {{
        background-color: {QColor(COLOR_ACCENT_SECONDARY).lighter(110).name()};
    }}
    QPushButton#ColorButton, QPushButton#ColorButtonPropertiesDock {{
        border: 1px solid {COLOR_BORDER_MEDIUM}; min-height: 24px; padding: 3px;
    }}
    QPushButton#ColorButton:hover, QPushButton#ColorButtonPropertiesDock:hover {{
        border: 1px solid {COLOR_ACCENT_PRIMARY};
    }}
    QProgressBar {{
        border: 1px solid {COLOR_BORDER_MEDIUM}; border-radius: 3px;
        background-color: {COLOR_BACKGROUND_LIGHT}; text-align: center;
        color: {COLOR_TEXT_PRIMARY}; height: 12px;
    }}
    QProgressBar::chunk {{
        background-color: {COLOR_ACCENT_PRIMARY}; border-radius: 2px;
    }}
    QPushButton#DraggableToolButton {{
        background-color: {COLOR_DRAGGABLE_BUTTON_BG}; color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_DRAGGABLE_BUTTON_BORDER};
        padding: 5px 7px;
        text-align: left;
        font-weight: 500;
        min-height: 32px;
    }}
    QPushButton#DraggableToolButton:hover {{
        background-color: {QColor(COLOR_DRAGGABLE_BUTTON_HOVER_BG).name() if isinstance(COLOR_DRAGGABLE_BUTTON_HOVER_BG, QColor) else COLOR_DRAGGABLE_BUTTON_HOVER_BG};
        border-color: {COLOR_DRAGGABLE_BUTTON_HOVER_BORDER};
    }}
    QPushButton#DraggableToolButton:pressed {{ background-color: {QColor(COLOR_DRAGGABLE_BUTTON_PRESSED_BG).name() if isinstance(COLOR_DRAGGABLE_BUTTON_PRESSED_BG, QColor) else COLOR_DRAGGABLE_BUTTON_PRESSED_BG}; }}

    #PropertiesDock QLabel#PropertiesLabel {{
        padding: 6px; background-color: {COLOR_BACKGROUND_DIALOG};
        border: 1px solid {COLOR_BORDER_LIGHT}; border-radius: 3px;
        font-size: {APP_FONT_SIZE_STANDARD};
        color: {COLOR_TEXT_PRIMARY};
    }}
    #PropertiesDock QPushButton {{
        background-color: {COLOR_ACCENT_PRIMARY}; color: {COLOR_TEXT_ON_ACCENT};
        font-weight:bold;
    }}
    #PropertiesDock QPushButton:hover {{ background-color: {QColor(COLOR_ACCENT_PRIMARY).lighter(110).name()}; }}

    QDockWidget#ElementsPaletteDock QToolButton {{
        padding: 6px 8px; text-align: left;
        min-height: 34px;
        font-weight: 500;
    }}
    QDockWidget#ElementsPaletteDock QGroupBox {{
        color: {COLOR_TEXT_PRIMARY};
    }}
    QDockWidget#ElementsPaletteDock QGroupBox::title {{
        color: {COLOR_ACCENT_PRIMARY};
        background-color: {COLOR_BACKGROUND_APP};
    }}


    QDockWidget#PySimDock QPushButton {{
        padding: 5px 10px;
    }}
    QDockWidget#PySimDock QPushButton:disabled {{
        background-color: {COLOR_BACKGROUND_MEDIUM};
        color: {COLOR_TEXT_SECONDARY};
    }}
    QDockWidget#PySimDock QTableWidget {{
        alternate-background-color: {QColor(COLOR_BACKGROUND_APP).lighter(105 if QColor(COLOR_BACKGROUND_APP).lightnessF() > 0.5 else 115).name()};
        gridline-color: {COLOR_BORDER_LIGHT};
        background-color: {COLOR_BACKGROUND_DIALOG};
        color: {COLOR_TEXT_PRIMARY};
    }}
     QDockWidget#PySimDock QHeaderView::section,
     QTableWidget QHeaderView::section
     {{
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {grad_stop_1}, stop: 1 {grad_stop_2});
        padding: 4px;
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-bottom: 2px solid {COLOR_BORDER_DARK};
        font-weight: bold;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QDockWidget#AIChatbotDock QPushButton#AIChatSendButton,
    QDockWidget#PySimDock QPushButton[text="Trigger"]
    {{
        background-color: {COLOR_ACCENT_PRIMARY}; color: {COLOR_TEXT_ON_ACCENT};
        font-weight: bold;
        padding: 5px;
        min-width: 0;
    }}
    QDockWidget#AIChatbotDock QPushButton#AIChatSendButton:hover,
    QDockWidget#PySimDock QPushButton[text="Trigger"]:hover
    {{
        background-color: {QColor(COLOR_ACCENT_PRIMARY).lighter(110).name()};
    }}
    QDockWidget#AIChatbotDock QPushButton#AIChatSendButton:disabled,
    QDockWidget#PySimDock QPushButton[text="Trigger"]:disabled
    {{
        background-color: {COLOR_BACKGROUND_MEDIUM};
        color: {COLOR_TEXT_SECONDARY};
        border-color: {COLOR_BORDER_LIGHT};
    }}
    QLineEdit#AIChatInput, QLineEdit#PySimEventNameEdit
    {{
        padding: 6px 8px;
    }}
    QDockWidget#ProblemsDock QListWidget {{
        background-color: {COLOR_BACKGROUND_DIALOG};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QDockWidget#ProblemsDock QListWidget::item {{
        padding: 4px;
        border-bottom: 1px dotted {COLOR_BORDER_LIGHT};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QDockWidget#ProblemsDock QListWidget::item:selected {{
        background-color: {COLOR_ACCENT_PRIMARY_LIGHT};
        color: {QColor(COLOR_ACCENT_PRIMARY).darker(130).name() if QColor(COLOR_ACCENT_PRIMARY_LIGHT).lightnessF() > 0.6 else COLOR_TEXT_ON_ACCENT};
    }}
    QLabel#ErrorLabel {{
        color: {COLOR_ACCENT_ERROR};
        font-weight: bold;
    }}
    QLabel#HardwareHintLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-style: italic;
        font-size: 7.5pt;
    }}
    QLabel#SafetyNote {{
        color: {COLOR_TEXT_SECONDARY};
        font-style: italic;
        font-size: {APP_FONT_SIZE_SMALL};
    }}
    QGroupBox#IDEOutputGroup, QGroupBox#IDEToolbarGroup {{
    }}
       """

```

### `fsm_designer_project/ui_manager.py`
The old `WelcomeWidget` class is removed and replaced by an import of the new `ModernWelcomeScreen`, ensuring the main application will now use the modern version.

```python
# fsm_designer_project/ui_manager.py
import sip 
import os
import json
from PyQt5.QtWidgets import (
    QMainWindow, QDockWidget, QToolBox, QAction, QToolBar, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QStatusBar, QTextEdit, QPushButton, QListWidget, QMenu, QActionGroup, QStyle,
    QToolButton, QGroupBox, QComboBox, QProgressBar, QFormLayout, QGraphicsView,
    QMessageBox, QInputDialog, QLineEdit, QSizePolicy
)
from PyQt5.QtGui import QIcon, QKeySequence, QPalette, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QSize, QObject, QPointF

from .utils import get_standard_icon
from .custom_widgets import DraggableToolButton
from .config import (
    APP_VERSION, APP_NAME, FILE_FILTER, MIME_TYPE_BSM_TEMPLATE,
    FSM_TEMPLATES_BUILTIN, COLOR_TEXT_SECONDARY, APP_FONT_SIZE_SMALL,
    COLOR_ACCENT_PRIMARY, COLOR_BORDER_LIGHT
)
from .target_profiles import TARGET_PROFILES
from .code_editor import CodeEditor
from .graphics_items import GraphicsStateItem, GraphicsTransitionItem, GraphicsCommentItem
from . import config
from .graphics_scene import MinimapView # NEW: Import MinimapView
from .modern_welcome_screen import ModernWelcomeScreen as WelcomeWidget
import logging

logger = logging.getLogger(__name__)

class UIManager(QObject): 
    def __init__(self, main_window: QMainWindow):
        super().__init__(main_window) 
        self.mw = main_window

    def _safe_get_style_enum(self, attr_name, fallback_attr_name=None):
        try:
            return getattr(QStyle, attr_name)
        except AttributeError:
            if fallback_attr_name:
                try:
                    return getattr(QStyle, fallback_attr_name)
                except AttributeError:
                    pass
            return QStyle.SP_CustomBase

    def setup_ui(self):
        """Initializes the entire UI structure."""
        self.mw.setWindowIcon(get_standard_icon(QStyle.SP_DesktopIcon, "BSM"))
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_docks()
        self._create_status_bar()

    def populate_dynamic_docks(self):
        """Populates docks whose content is managed by other classes."""
        mw = self.mw
        if mw.py_sim_ui_manager and hasattr(mw, 'py_sim_dock'):
            py_sim_contents_widget = mw.py_sim_ui_manager.create_dock_widget_contents()
            mw.py_sim_dock.setWidget(py_sim_contents_widget)
        
        if mw.ai_chat_ui_manager and hasattr(mw, 'ai_chatbot_dock'):
            ai_chat_contents_widget = mw.ai_chat_ui_manager.create_dock_widget_contents()
            mw.ai_chatbot_dock.setWidget(ai_chat_contents_widget)
            
        self._populate_resource_estimation_dock()

    def _create_actions(self):
        mw = self.mw
        
        # --- FILE ---
        mw.new_action = QAction(get_standard_icon(QStyle.SP_FileIcon, "New"), "&New", mw, shortcut=QKeySequence.New, statusTip="Create a new diagram tab")
        mw.open_action = QAction(get_standard_icon(QStyle.SP_DialogOpenButton, "Opn"), "&Open...", mw, shortcut=QKeySequence.Open, statusTip="Open an existing file")
        mw.save_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "Sav"), "&Save", mw, shortcut=QKeySequence.Save, statusTip="Save the current diagram", enabled=False)
        mw.save_as_action = QAction(get_standard_icon(self._safe_get_style_enum("SP_DriveHDIcon", "SP_DialogSaveButton"), "SA"), "Save &As...", mw, shortcut=QKeySequence.SaveAs, statusTip="Save the current diagram with a new name")
        mw.exit_action = QAction(get_standard_icon(QStyle.SP_DialogCloseButton, "Exit"), "E&xit", mw, shortcut=QKeySequence.Quit, triggered=mw.close)

        # --- EXPORT ---
        mw.export_png_action = QAction("&PNG Image...", mw)
        mw.export_svg_action = QAction("&SVG Image...", mw)
        mw.export_simulink_action = QAction("&Simulink...", mw)
        mw.generate_c_code_action = QAction("Basic &C Code...", mw)
        mw.export_python_fsm_action = QAction("&Python FSM Class...", mw)
        mw.export_plantuml_action = QAction("&PlantUML...", mw)
        mw.export_mermaid_action = QAction("&Mermaid...", mw)

        # --- EDIT ---
        mw.undo_action = QAction(get_standard_icon(QStyle.SP_ArrowBack, "Un"), "&Undo", mw, shortcut=QKeySequence.Undo)
        mw.redo_action = QAction(get_standard_icon(QStyle.SP_ArrowForward, "Re"), "&Redo", mw, shortcut=QKeySequence.Redo)
        mw.delete_action = QAction(get_standard_icon(QStyle.SP_TrashIcon, "Del"), "&Delete", mw, shortcut=QKeySequence.Delete)
        mw.select_all_action = QAction("Select &All", mw, shortcut=QKeySequence.SelectAll)
        mw.find_item_action = QAction("&Find Item...", mw, shortcut=QKeySequence.Find)
        mw.save_selection_as_template_action = QAction("Save Selection as Template...", mw, enabled=False) # New action
        mw.manage_snippets_action = QAction("Manage Custom Snippets...", mw)
        mw.preferences_action = QAction(get_standard_icon(QStyle.SP_FileDialogDetailedView, "Prefs"), "&Preferences...", mw)
        
        # --- INTERACTION MODE ---
        mw.mode_action_group = QActionGroup(mw); mw.mode_action_group.setExclusive(True)
        def create_mode_action(name, text, icon_name, shortcut):
            action = QAction(get_standard_icon(getattr(QStyle, icon_name), shortcut), text, mw, checkable=True)
            action.setShortcut(shortcut); action.setToolTip(f"Activate {text} mode ({shortcut})")
            mw.mode_action_group.addAction(action)
            return action
        mw.select_mode_action = create_mode_action("select", "Select/Move", "SP_ArrowRight", "S")
        mw.add_state_mode_action = create_mode_action("state", "Add State", "SP_FileDialogNewFolder", "A")
        mw.add_transition_mode_action = create_mode_action("transition", "Add Transition", "SP_ArrowForward", "T")
        mw.add_comment_mode_action = create_mode_action("comment", "Add Comment", "SP_MessageBoxInformation", "C")
        mw.select_mode_action.setChecked(True)

        # --- ALIGN/DISTRIBUTE ---
        mw.align_left_action = QAction("Align Left", mw)
        mw.align_center_h_action = QAction("Align Center Horizontally", mw)
        mw.align_right_action = QAction("Align Right", mw)
        mw.align_top_action = QAction("Align Top", mw)
        mw.align_middle_v_action = QAction("Align Middle Vertically", mw)
        mw.align_bottom_action = QAction("Align Bottom", mw)
        mw.distribute_h_action = QAction("Distribute Horizontally", mw)
        mw.distribute_v_action = QAction("Distribute Vertically", mw)
        mw.align_actions = [mw.align_left_action, mw.align_center_h_action, mw.align_right_action, mw.align_top_action, mw.align_middle_v_action, mw.align_bottom_action]
        mw.distribute_actions = [mw.distribute_h_action, mw.distribute_v_action]
        for action in mw.align_actions + mw.distribute_actions: action.setEnabled(False)

        # --- VIEW ---
        mw.zoom_in_action = QAction("Zoom In", mw, shortcut="Ctrl++")
        mw.zoom_out_action = QAction("Zoom Out", mw, shortcut="Ctrl+-")
        mw.reset_zoom_action = QAction("Reset Zoom/View", mw, shortcut="Ctrl+0")
        mw.zoom_to_selection_action = QAction("Zoom to Selection", mw, enabled=False)
        mw.fit_diagram_action = QAction("Fit Diagram in View", mw)
        mw.auto_layout_action = QAction("Auto-Layout Diagram", mw, shortcut="Ctrl+L")
        mw.show_grid_action = QAction("Show Grid", mw, checkable=True, checked=True)
        mw.snap_to_objects_action = QAction("Snap to Objects", mw, checkable=True, checked=True)
        mw.snap_to_grid_action = QAction("Snap to Grid", mw, checkable=True, checked=True)
        mw.show_snap_guidelines_action = QAction("Show Dynamic Snap Guidelines", mw, checkable=True, checked=True)

        # --- SIMULATION ---
        mw.start_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "Py▶"), "&Start Python Simulation", mw)
        mw.stop_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaStop, "Py■"), "S&top Python Simulation", mw, enabled=False)
        mw.reset_py_sim_action = QAction(get_standard_icon(QStyle.SP_MediaSkipBackward, "Py«"), "&Reset Python Simulation", mw, enabled=False)
        mw.matlab_settings_action = QAction(get_standard_icon(QStyle.SP_ComputerIcon, "Cfg"), "&MATLAB Settings...", mw)
        mw.run_simulation_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "Run"), "&Run Simulation (MATLAB)...", mw)
        mw.generate_matlab_code_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "CdeM"), "Generate &Code (C/C++ via MATLAB)...", mw)
        
        # --- GIT ---
        mw.git_commit_action = QAction("Commit...", mw)
        mw.git_push_action = QAction("Push", mw)
        mw.git_pull_action = QAction("Pull", mw)
        mw.git_show_changes_action = QAction("Show Changes...", mw)
        mw.git_actions = [mw.git_commit_action, mw.git_push_action, mw.git_pull_action, mw.git_show_changes_action]
        for action in mw.git_actions: action.setEnabled(False)

        # --- TOOLS (IDE & Other) ---
        mw.ide_new_file_action = QAction(get_standard_icon(QStyle.SP_FileIcon, "IDENew"), "New Script", mw)
        mw.ide_open_file_action = QAction(get_standard_icon(QStyle.SP_DialogOpenButton, "IDEOpn"), "Open Script...", mw)
        mw.ide_save_file_action = QAction(get_standard_icon(QStyle.SP_DialogSaveButton, "IDESav"), "Save Script", mw)
        mw.ide_save_as_file_action = QAction("Save Script As...", mw)
        mw.ide_run_script_action = QAction(get_standard_icon(QStyle.SP_MediaPlay, "IDERunPy"), "Run Python Script", mw)
        mw.ide_analyze_action = QAction("Analyze with AI", mw)
        # AI IMPROVEMENT: New action for analyzing selection
        mw.ide_analyze_selection_action = QAction("Analyze Selection with AI", mw)

        mw.show_resource_estimation_action = QAction("Resource Estimation", mw, checkable=True)
        mw.show_live_preview_action = QAction("Live Code Preview", mw, checkable=True)

        # --- AI ---
        mw.ask_ai_to_generate_fsm_action = QAction("Generate FSM from Description...", mw)
        mw.clear_ai_chat_action = QAction("Clear Chat History", mw)
        mw.openai_settings_action = QAction("AI Assistant Settings...", mw)
        
        # --- HELP ---
        mw.quick_start_action = QAction(get_standard_icon(QStyle.SP_MessageBoxQuestion, "QS"), "&Quick Start Guide", mw)
        mw.about_action = QAction(get_standard_icon(QStyle.SP_DialogHelpButton, "?"), "&About", mw)
        
        logger.debug("UIManager: Actions created.")
        
    def _create_menus(self):
        mw = self.mw; mb = mw.menuBar()
        # --- FILE MENU ---
        file_menu = mb.addMenu("&File")
        file_menu.addActions([mw.new_action, mw.open_action])
        mw.recent_files_menu = file_menu.addMenu("Open &Recent")
        mw.recent_files_menu.aboutToShow.connect(mw._populate_recent_files_menu)
        file_menu.addSeparator()
        example_menu = file_menu.addMenu("Open E&xample")
        mw.open_example_traffic_action = example_menu.addAction("Traffic Light FSM")
        mw.open_example_toggle_action = example_menu.addAction("Simple Toggle FSM")
        export_menu = file_menu.addMenu("E&xport"); export_menu.addActions([mw.export_png_action, mw.export_svg_action]); export_menu.addSeparator()
        export_menu.addActions([mw.export_simulink_action, mw.generate_c_code_action, mw.export_python_fsm_action])
        export_menu.addSeparator(); export_menu.addActions([mw.export_plantuml_action, mw.export_mermaid_action])
        file_menu.addSeparator(); file_menu.addActions([mw.save_action, mw.save_as_action]); file_menu.addSeparator(); file_menu.addAction(mw.exit_action)
        # --- EDIT MENU ---
        edit_menu = mb.addMenu("&Edit")
        edit_menu.addActions([mw.undo_action, mw.redo_action]); edit_menu.addSeparator()
        edit_menu.addActions([mw.delete_action, mw.select_all_action]); edit_menu.addSeparator()
        edit_menu.addAction(mw.find_item_action); edit_menu.addSeparator()
        edit_menu.addAction(mw.save_selection_as_template_action); edit_menu.addSeparator()
        edit_menu.addMenu("Interaction Mode").addActions(mw.mode_action_group.actions())
        align_menu = edit_menu.addMenu("Align & Distribute"); align_menu.addMenu("Align").addActions(mw.align_actions); align_menu.addMenu("Distribute").addActions(mw.distribute_actions)
        edit_menu.addSeparator(); edit_menu.addAction(mw.manage_snippets_action); edit_menu.addSeparator(); edit_menu.addAction(mw.preferences_action)
        # --- VIEW MENU ---
        mw.view_menu = mb.addMenu("&View")
        zoom_menu = mw.view_menu.addMenu("Zoom"); zoom_menu.addActions([mw.zoom_in_action, mw.zoom_out_action, mw.reset_zoom_action]); zoom_menu.addSeparator(); zoom_menu.addActions([mw.zoom_to_selection_action, mw.fit_diagram_action])
        mw.view_menu.addSeparator(); mw.view_menu.addAction(mw.auto_layout_action)
        mw.view_menu.addSeparator();
        mw.view_menu.addAction(mw.show_grid_action)
        snap_menu = mw.view_menu.addMenu("Snapping"); snap_menu.addActions([mw.snap_to_grid_action, mw.snap_to_objects_action, mw.show_snap_guidelines_action])
        mw.view_menu.addSeparator(); mw.toolbars_menu = mw.view_menu.addMenu("Toolbars"); mw.docks_menu = mw.view_menu.addMenu("Docks & Panels")
        mw.view_menu.addSeparator()
        mw.perspectives_menu = mw.view_menu.addMenu("Perspectives")
        mw.perspectives_action_group = QActionGroup(mw)
        mw.save_perspective_action = QAction("Save Current As...", mw); mw.reset_perspectives_action = QAction("Reset to Defaults", mw)
        
        # --- GIT MENU ---
        git_menu = mb.addMenu("&Git")
        git_menu.addActions(mw.git_actions)
        
        # --- SIMULATION, TOOLS, AI, HELP MENUS ---
        sim_menu = mb.addMenu("&Simulation")
        sim_menu.addMenu("Python Simulation").addActions([mw.start_py_sim_action, mw.stop_py_sim_action, mw.reset_py_sim_action])
        sim_menu.addMenu("MATLAB/Simulink").addActions([mw.run_simulation_action, mw.generate_matlab_code_action, mw.matlab_settings_action])
        tools_menu = mb.addMenu("&Tools")
        ide_menu = tools_menu.addMenu("Standalone Code IDE")
        ide_menu.addActions([mw.ide_new_file_action, mw.ide_open_file_action, mw.ide_save_file_action, mw.ide_save_as_file_action])
        ide_menu.addSeparator()
        ide_menu.addAction(mw.ide_run_script_action)
        ide_menu.addSeparator()
        # AI IMPROVEMENT: Add new action to menu
        ide_menu.addActions([mw.ide_analyze_action, mw.ide_analyze_selection_action])

        tools_menu.addMenu("Development Tools").addActions([mw.show_resource_estimation_action, mw.show_live_preview_action])
        ai_menu = mb.addMenu("&AI Assistant")
        ai_menu.addActions([mw.ask_ai_to_generate_fsm_action, mw.clear_ai_chat_action]); ai_menu.addSeparator(); ai_menu.addAction(mw.openai_settings_action)
        help_menu = mb.addMenu("&Help"); help_menu.addActions([mw.quick_start_action, mw.about_action])
        logger.debug("UIManager: Menus created.")

    def _create_toolbars(self):
        mw = self.mw
        for tb in mw.findChildren(QToolBar): mw.removeToolBar(tb); tb.deleteLater() # Clear old toolbars
        tb = mw.addToolBar("Main"); tb.setObjectName("MainToolbar"); tb.setIconSize(QSize(20, 20)); tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        tb.addActions([mw.new_action, mw.open_action, mw.save_action]); tb.addSeparator()
        tb.addActions([mw.undo_action, mw.redo_action, mw.delete_action]); tb.addSeparator()
        tb.addActions(mw.mode_action_group.actions()); tb.addSeparator()
        tb.addAction(mw.auto_layout_action)
        align_btn = QToolButton(mw); align_btn.setIcon(get_standard_icon(QStyle.SP_FileDialogDetailedView, "Align")); align_btn.setToolTip("Align & Distribute"); align_btn.setPopupMode(QToolButton.InstantPopup)
        align_menu = QMenu(mw); align_sub = align_menu.addMenu("Align"); align_sub.addActions(mw.align_actions); dist_sub = align_menu.addMenu("Distribute"); dist_sub.addActions(mw.distribute_actions)
        align_btn.setMenu(align_menu); tb.addWidget(align_btn)
        
        # Add Git button to toolbar
        git_btn = QToolButton(mw)
        git_btn.setIcon(get_standard_icon(QStyle.SP_ToolBarHorizontalExtensionButton, "Git")) # A generic icon for now
        git_btn.setToolTip("Git Actions")
        git_btn.setPopupMode(QToolButton.InstantPopup)
        git_menu_for_button = QMenu(mw)
        git_menu_for_button.addActions(mw.git_actions)
        git_btn.setMenu(git_menu_for_button)
        tb.addWidget(git_btn)
        
        tb.addSeparator()
        
        tb.addActions([mw.zoom_in_action, mw.zoom_out_action, mw.reset_zoom_action, mw.fit_diagram_action]); tb.addSeparator()
        tb.addActions([mw.start_py_sim_action, mw.stop_py_sim_action, mw.reset_py_sim_action]); tb.addSeparator()
        export_btn = QToolButton(mw); export_btn.setIcon(get_standard_icon(QStyle.SP_DialogSaveButton, "Export")); export_btn.setToolTip("Export & Generate Code"); export_btn.setPopupMode(QToolButton.InstantPopup)
        export_menu = QMenu(mw); export_menu.addActions([mw.export_png_action, mw.export_svg_action]); export_menu.addSeparator(); export_menu.addActions([mw.export_simulink_action, mw.generate_c_code_action, mw.export_python_fsm_action, mw.generate_matlab_code_action]); export_menu.addSeparator(); export_menu.addActions([mw.export_plantuml_action, mw.export_mermaid_action])
        export_btn.setMenu(export_menu); tb.addWidget(export_btn)
        mw.toolbars_menu.clear(); mw.toolbars_menu.addAction(tb.toggleViewAction())
        logger.debug("UIManager: Toolbar created.")

    def _create_docks(self):
        mw = self.mw
        mw.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowTabbedDocks | QMainWindow.AllowNestedDocks)
        
        docks_to_create = {
            "elements_palette_dock": ("ElementsPaletteDock", "Elements"),
            "properties_dock": ("PropertiesDock", "Properties"),
            "log_dock": ("LogDock", "Log"),
            "problems_dock": ("ProblemsDock", "Validation Issues"),
            "py_sim_dock": ("PySimDock", "Python Simulation"),
            "ai_chatbot_dock": ("AIChatbotDock", "AI Chatbot"),
            "ide_dock": ("IDEDock", "Code IDE"),
            "resource_estimation_dock": ("ResourceEstimationDock", "Resource Estimation"),
            "live_preview_dock": ("LivePreviewDock", "Live Code Preview"),
            "minimap_dock": ("MinimapDock", "Navigator") # NEW: Minimap dock
        }
        
        for attr_name, (object_name, title) in docks_to_create.items():
            setattr(mw, attr_name, QDockWidget(title, mw, objectName=object_name))
        
        self._populate_elements_palette_dock()
        self._populate_properties_dock()
        self._populate_live_preview_dock()
        
        mw.log_output = QTextEdit(); mw.log_output.setReadOnly(True); mw.log_output.setObjectName("LogOutputWidget"); mw.log_dock.setWidget(mw.log_output)
        
        problems_widget = QWidget()
        problems_layout = QVBoxLayout(problems_widget)
        problems_layout.setContentsMargins(0,0,0,0)
        problems_layout.setSpacing(4)
        mw.problems_list_widget = QListWidget(); mw.problems_list_widget.setObjectName("ProblemsListWidget")
        mw.problems_list_widget.itemDoubleClicked.connect(mw.on_problem_item_double_clicked)
        mw.problems_list_widget.currentItemChanged.connect(lambda current, prev: mw.problems_ask_ai_btn.setEnabled(current is not None))
        problems_layout.addWidget(mw.problems_list_widget)
        mw.problems_ask_ai_btn = QPushButton("Ask AI for help on this issue...")
        mw.problems_ask_ai_btn.setIcon(get_standard_icon(QStyle.SP_MessageBoxQuestion, "AIHelp"))
        mw.problems_ask_ai_btn.setEnabled(False)
        problems_layout.addWidget(mw.problems_ask_ai_btn)
        mw.problems_dock.setWidget(problems_widget)
        
        # --- NEW: Minimap Dock Setup ---
        mw.minimap_view = MinimapView()
        mw.minimap_dock.setWidget(mw.minimap_view)
        
        mw.docks_menu.clear()
        dock_list = [getattr(mw, attr_name) for attr_name in docks_to_create.keys()]
        mw.docks_menu.addActions([d.toggleViewAction() for d in dock_list if d])

        mw.resource_estimation_dock.visibilityChanged.connect(mw.show_resource_estimation_action.setChecked)
        mw.show_resource_estimation_action.triggered.connect(mw.resource_estimation_dock.setVisible)
        mw.live_preview_dock.visibilityChanged.connect(mw.show_live_preview_action.setChecked)
        mw.show_live_preview_action.triggered.connect(mw.live_preview_dock.setVisible)
        
    def _populate_elements_palette_dock(self):
        mw = self.mw
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # --- NEW: Search Bar ---
        self.palette_search_bar = QLineEdit()
        self.palette_search_bar.setPlaceholderText("Filter elements...")
        self.palette_search_bar.setClearButtonEnabled(True)
        layout.addWidget(self.palette_search_bar)
        
        self.drag_elements_group = QGroupBox("Drag Elements")
        drag_layout = QVBoxLayout()
        drag_layout.setSpacing(4)
        drag_items = {
            "State": ("State", "SP_ToolBarHorizontalExtensionButton"),
            "Initial State": ("Initial State", "SP_ArrowRight"),
            "Final State": ("Final State", "SP_DialogOkButton"),
            "Comment": ("Comment", "SP_MessageBoxInformation")
        }
        for text, (data, icon_name_str) in drag_items.items():
            icon_enum = getattr(QStyle, icon_name_str, QStyle.SP_CustomBase)
            btn = DraggableToolButton(text, "application/x-bsm-tool", data)
            btn.setIcon(get_standard_icon(icon_enum, text[:2]))
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            drag_layout.addWidget(btn)
        
        self.drag_elements_group.setLayout(drag_layout)
        layout.addWidget(self.drag_elements_group)
        
        self.templates_group = QGroupBox("FSM Templates")
        template_layout = QVBoxLayout()
        mw.template_buttons_container = QWidget()
        mw.template_buttons_layout = QVBoxLayout(mw.template_buttons_container)
        mw.template_buttons_layout.setContentsMargins(0,0,0,0)
        self._load_and_display_templates()
        template_layout.addWidget(mw.template_buttons_container)
        
        manage_templates_btn = QPushButton("Manage Snippets...")
        manage_templates_btn.clicked.connect(self.mw.action_handler.on_manage_snippets)
        template_layout.addWidget(manage_templates_btn)

        self.templates_group.setLayout(template_layout)
        layout.addWidget(self.templates_group)
        layout.addStretch()
        mw.elements_palette_dock.setWidget(widget)
        
        # Connect search bar signal
        self.palette_search_bar.textChanged.connect(self._filter_palette_elements)
        
    def _filter_palette_elements(self, text):
        """Filters draggable buttons in the palette based on search text."""
        text = text.lower()
        # Filter drag elements
        for button in self.drag_elements_group.findChildren(DraggableToolButton):
            matches = text in button.text().lower()
            button.setVisible(matches)
        
        # Filter template elements
        for button in self.templates_group.findChildren(DraggableToolButton):
            matches = text in button.text().lower() or text in button.toolTip().lower()
            button.setVisible(matches)


    def _load_and_display_templates(self):
        mw = self.mw; layout = mw.template_buttons_layout
        while layout.count(): 
            item = layout.takeAt(0)
            if item and item.widget(): 
                item.widget().deleteLater()
        
        for key, data in FSM_TEMPLATES_BUILTIN.items():
            btn = DraggableToolButton(data['name'], MIME_TYPE_BSM_TEMPLATE, json.dumps(data))
            btn.setIcon(QIcon(data.get('icon_resource', ':/icons/default.png')))
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setToolTip(data.get('description',''))
            layout.addWidget(btn)

        if hasattr(mw, 'custom_snippet_manager'):
            custom_templates = mw.custom_snippet_manager.get_custom_templates()
            for name, data in custom_templates.items():
                btn = DraggableToolButton(name, MIME_TYPE_BSM_TEMPLATE, json.dumps(data))
                btn.setIcon(get_standard_icon(QStyle.SP_FileLinkIcon, "CustomTpl"))
                btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                btn.setToolTip(data.get('description', f"Custom template: {name}"))
                layout.addWidget(btn)

    def _populate_properties_dock(self):
        mw = self.mw
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8,8,8,8)
        layout.setSpacing(6)

        mw.properties_placeholder_label = QLabel("<i>Select an item...</i>")
        mw.properties_placeholder_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(mw.properties_placeholder_label)

        mw.properties_editor_container = QWidget()
        mw.properties_editor_layout = QFormLayout(mw.properties_editor_container)
        mw.properties_editor_layout.setContentsMargins(0,0,0,0)
        mw.properties_editor_container.setHidden(True)
        layout.addWidget(mw.properties_editor_container)
        
        mw.properties_multi_select_container = QWidget()
        mw.properties_multi_layout = QVBoxLayout(mw.properties_multi_select_container)
        mw.properties_multi_layout.setContentsMargins(0,0,0,0)
        mw.properties_multi_select_container.setHidden(True)
        layout.addWidget(mw.properties_multi_select_container)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        mw.properties_revert_button = QPushButton("Revert")
        mw.properties_apply_button = QPushButton("Apply")
        btn_layout.addWidget(mw.properties_revert_button)
        btn_layout.addStretch()
        btn_layout.addWidget(mw.properties_apply_button)
        layout.addLayout(btn_layout)

        mw.properties_edit_dialog_button = QPushButton("Advanced Edit...")
        layout.addWidget(mw.properties_edit_dialog_button)
        
        mw.properties_dock.setWidget(widget)


    def _populate_resource_estimation_dock(self):
        mw = self.mw; widget = QWidget(); layout = QVBoxLayout(widget)
        target_group = QGroupBox("Target Device"); target_layout = QFormLayout(target_group)
        mw.target_device_combo = QComboBox(); target_layout.addRow("Profile:", mw.target_device_combo)
        for profile in TARGET_PROFILES: mw.target_device_combo.addItem(profile, TARGET_PROFILES[profile])
        layout.addWidget(target_group)
        usage_group = QGroupBox("Estimated Usage"); usage_layout = QFormLayout(usage_group)
        mw.flash_usage_bar = QProgressBar(); mw.sram_usage_bar = QProgressBar(); usage_layout.addRow("Flash/Code:", mw.flash_usage_bar); usage_layout.addRow("SRAM/Data:", mw.sram_usage_bar)
        layout.addWidget(usage_group); disclaimer = QLabel("<small><i>Estimates are heuristics.</i></small>"); disclaimer.setWordWrap(True); layout.addWidget(disclaimer); layout.addStretch(); mw.resource_estimation_dock.setWidget(widget)

    def _populate_live_preview_dock(self):
        """Creates the contents of the live code preview dock."""
        mw = self.mw
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QToolBar("Live Preview Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        toolbar.addWidget(QLabel(" Language: "))
        mw.live_preview_combo = QComboBox()
        mw.live_preview_combo.addItems(["Python FSM", "C Code", "PlantUML", "Mermaid"])
        toolbar.addWidget(mw.live_preview_combo)
        
        layout.addWidget(toolbar)
        
        mw.live_preview_editor = CodeEditor()
        mw.live_preview_editor.setReadOnly(True)
        mw.live_preview_editor.setObjectName("LivePreviewEditor") # For styling
        mw.live_preview_editor.setPlaceholderText("Edit the diagram to see a live code preview...")
        layout.addWidget(mw.live_preview_editor, 1)

        mw.live_preview_dock.setWidget(widget)

    def _create_status_bar(self):
        mw = self.mw; status_bar = QStatusBar(mw); mw.setStatusBar(status_bar)
        
        mw.main_op_status_label = QLabel("Ready"); status_bar.addWidget(mw.main_op_status_label, 1)
        
        def create_status_segment(icon_enum, icon_alt, text, tooltip, obj_name):
            container = QWidget()
            layout = QHBoxLayout(container); layout.setContentsMargins(4,0,4,0); layout.setSpacing(3)
            icon_label = QLabel(); icon_label.setPixmap(get_standard_icon(icon_enum, icon_alt).pixmap(QSize(12,12)))
            text_label = QLabel(text); text_label.setObjectName(obj_name)
            layout.addWidget(icon_label); layout.addWidget(text_label)
            container.setToolTip(tooltip)
            status_bar.addPermanentWidget(container)
            return text_label, icon_label

        mw.mode_status_label, mw.mode_icon_label = create_status_segment(QStyle.SP_ArrowRight, "Sel", "Select", "Interaction Mode", "InteractionModeStatusLabel")
        mw.zoom_status_label, mw.zoom_icon_label = create_status_segment(QStyle.SP_FileDialogInfoView, "Zoom", "100%", "Zoom Level", "ZoomStatusLabel")
        mw.pysim_status_label, mw.pysim_icon_label = create_status_segment(QStyle.SP_MediaStop, "PySim", "Idle", "Python Sim Status", "PySimStatusLabel")
        mw.matlab_status_label, mw.matlab_icon_label = create_status_segment(QStyle.SP_MessageBoxWarning, "MATLAB", "Not Conn.", "MATLAB Status", "MatlabStatusLabel")
        mw.net_status_label, mw.net_icon_label = create_status_segment(QStyle.SP_MessageBoxQuestion, "Net", "Checking...", "Internet Status", "InternetStatusLabel")

        mw.resource_monitor_widget = QWidget()
        res_layout = QHBoxLayout(mw.resource_monitor_widget); res_layout.setContentsMargins(4,0,4,0); res_layout.setSpacing(5)
        mw.cpu_status_label = QLabel("CPU: --%"); res_layout.addWidget(mw.cpu_status_label)
        mw.ram_status_label = QLabel("RAM: --%"); res_layout.addWidget(mw.ram_status_label)
        mw.gpu_status_label = QLabel("GPU: N/A"); res_layout.addWidget(mw.gpu_status_label)
        status_bar.addPermanentWidget(mw.resource_monitor_widget)
        mw.resource_monitor_widget.setVisible(False)
        
        mw.progress_bar = QProgressBar(); mw.progress_bar.setRange(0,0); mw.progress_bar.hide(); mw.progress_bar.setMaximumWidth(120); mw.progress_bar.setTextVisible(False)
        status_bar.addPermanentWidget(mw.progress_bar)

    def update_undo_redo_state(self):
        """Updates the enable state and text of the global Undo/Redo actions."""
        mw = self.mw
        editor = mw.current_editor()
        
        can_undo = editor and editor.undo_stack.canUndo()
        can_redo = editor and editor.undo_stack.canRedo()
        
        if hasattr(mw, 'undo_action'):
            mw.undo_action.setEnabled(can_undo)
            undo_text = editor.undo_stack.undoText() if can_undo else ""
            mw.undo_action.setText(f"&Undo{(' ' + undo_text) if undo_text else ''}")
            mw.undo_action.setToolTip(f"Undo: {undo_text}" if undo_text else "Undo")
        
        if hasattr(mw, 'redo_action'):
            mw.redo_action.setEnabled(can_redo)
            redo_text = editor.undo_stack.redoText() if can_redo else ""
            mw.redo_action.setText(f"&Redo{(' ' + redo_text) if redo_text else ''}")
            mw.redo_action.setToolTip(f"Redo: {redo_text}" if redo_text else "Redo")

    def update_save_actions_state(self):
        """Updates the enabled state of the Save action based on the current editor's dirty status."""
        mw = self.mw
        if hasattr(mw, 'save_action'):
            mw.save_action.setEnabled(mw.current_editor() and mw.current_editor().is_dirty())