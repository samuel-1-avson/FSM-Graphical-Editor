# bsm_designer_project/config.py
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
import json

# --- Configuration ---
APP_VERSION = "1.9.0" # Version updated for Theme Manager and bugfixes
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
    # Add other environments like RaspberryPi, MicroPython with relevant snippets
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

for key in THEME_KEYS:
    globals()[key] = ""

# Initialize theme color globals with light theme as default to avoid undefined errors
for key, value in THEME_DATA_LIGHT.items():
    globals()[key] = value

# Ensure COLOR_BACKGROUND_APP is defined for stylesheet generation
if "COLOR_BACKGROUND_APP" not in globals() or not globals()["COLOR_BACKGROUND_APP"]:
    COLOR_BACKGROUND_APP = THEME_DATA_LIGHT["COLOR_BACKGROUND_APP"]

# Ensure COLOR_TEXT_PRIMARY is defined for stylesheet generation
if "COLOR_TEXT_PRIMARY" not in globals() or not globals()["COLOR_TEXT_PRIMARY"]:
    COLOR_TEXT_PRIMARY = THEME_DATA_LIGHT["COLOR_TEXT_PRIMARY"]

# Ensure COLOR_BACKGROUND_MEDIUM is defined for stylesheet generation
if "COLOR_BACKGROUND_MEDIUM" not in globals() or not globals()["COLOR_BACKGROUND_MEDIUM"]:
    COLOR_BACKGROUND_MEDIUM = THEME_DATA_LIGHT["COLOR_BACKGROUND_MEDIUM"]

COLOR_ITEM_STATE_SELECTION_BG = ""
COLOR_ITEM_STATE_SELECTION_BORDER = ""
COLOR_ITEM_TRANSITION_SELECTION = ""
COLOR_SNAP_GUIDELINE = QColor(Qt.red)
COLOR_PY_SIM_STATE_ACTIVE = QColor("#4CAF50")
COLOR_PY_SIM_STATE_ACTIVE_PEN_WIDTH = 2.5


def DYNAMIC_UPDATE_COLORS_FROM_THEME(theme_data: dict):
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
        background-color: {QColor(COLOR_BACKGROUND_MEDIUM).darker(105).name()};
        padding: 6px 10px;
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-bottom: 2px solid {COLOR_ACCENT_PRIMARY};
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
    QDockWidget::close-button, QDockWidget::float-button {{
        subcontrol-position: top right;
        subcontrol-origin: margin;
        position: absolute;
        top: 1px; right: 4px; padding: 1px;
        border-radius: 2px;
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
        background-color: {QColor(COLOR_BACKGROUND_MEDIUM).lighter(105).name()};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_MEDIUM};
        padding: 6px 15px;
        border-radius: 4px;
        min-height: 22px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {QColor(COLOR_BACKGROUND_MEDIUM).name()};
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
    QDialogButtonBox QPushButton[text="Save"]
    {{
        background-color: {COLOR_ACCENT_PRIMARY};
        color: {COLOR_TEXT_ON_ACCENT};
        border-color: {QColor(COLOR_ACCENT_PRIMARY).darker(120).name()};
        font-weight: bold;
    }}
    QDialogButtonBox QPushButton[text="OK"]:hover, QDialogButtonBox QPushButton[text="OK & Save"]:hover, QDialogButtonBox QPushButton[text="Apply & Close"]:hover,
    QDialogButtonBox QPushButton[text="Save"]:hover
    {{
        background-color: {QColor(COLOR_ACCENT_PRIMARY).lighter(110).name()};
    }}
    QDialogButtonBox QPushButton[text="Cancel"], QDialogButtonBox QPushButton[text="Discard"],
    QDialogButtonBox QPushButton[text="Close"]
    {{
        background-color: {COLOR_BACKGROUND_MEDIUM};
        color: {COLOR_TEXT_PRIMARY};
        border-color: {COLOR_BORDER_MEDIUM};
    }}
    QDialogButtonBox QPushButton[text="Cancel"]:hover, QDialogButtonBox QPushButton[text="Discard"]:hover,
    QDialogButtonBox QPushButton[text="Close"]:hover
    {{
        background-color: {QColor(COLOR_BACKGROUND_MEDIUM).darker(110).name()};
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
        background-color: {COLOR_BACKGROUND_MEDIUM};
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