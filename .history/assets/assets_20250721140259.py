# fsm_designer_project/assets.py
import json

# ==============================================================================
# BUILT-IN MECHATRONICS CODE SNIPPETS
# ==============================================================================
# This dictionary contains pre-defined code snippets for common FSM
# actions, conditions, and events tailored to different target environments.

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
            "GPIO Set High": "import RPi.GPIO as GPIO\\nGPIO.setmode(GPIO.BCM) # or GPIO.BOARD\\nGPIO.setup(17, GPIO.OUT)\\nGPIO.output(17, GPIO.HIGH)",
            "GPIO Set Low": "import RPi.GPIO as GPIO\\nGPIO.output(17, GPIO.LOW)",
            "Print Message": "print('RPi FSM action')",
        },
        "conditions": {
            "GPIO Read High": "import RPi.GPIO as GPIO\\nGPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)\\nGPIO.input(18) == GPIO.HIGH",
        },
        "events": {
            "Button Press RPi": "rpi_button_event",
        }
    },
    "MicroPython": {
        "actions": {
            "Pin On": "from machine import Pin\\nled = Pin(2, Pin.OUT)\\nled.on()",
            "Pin Off": "from machine import Pin\\nled = Pin(2, Pin.OUT)\\nled.off()",
            "Toggle Pin": "from machine import Pin\\nled = Pin(2, Pin.OUT)\\nled.value(not led.value())",
        },
        "conditions": {
            "Pin Value High": "from machine import Pin\\nbutton = Pin(0, Pin.IN, Pin.PULL_UP)\\nbutton.value() == 1",
        },
        "events": {
            "IRQ Triggered MicroPy": "micropy_irq_flag_event",
        }
    },
    "Text": { # For comments or generic text fields
        "actions": {}, "conditions": {}, "events": {}
    }
}


# ==============================================================================
# BUILT-IN FSM TEMPLATES
# ==============================================================================
# This contains the JSON structure for pre-defined FSM templates that can be
# dragged onto the canvas.

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
            {"name": "LedOff", "is_initial": true, "entry_action": "set_led_off()\\\\nstart_timer(OFF_DURATION)"},
            {"name": "LedOn", "entry_action": "set_led_on()\\\\nstart_timer(ON_DURATION)"}
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
    # Fallback to an empty dict if JSON is malformed, preventing a crash.
    FSM_TEMPLATES_BUILTIN = {}