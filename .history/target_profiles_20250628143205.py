# bsm_designer_project/target_profiles.py (NEW FILE)

# A simple dictionary to store target device profiles.
# This could be expanded into a more complex system (e.g., loaded from JSON/XML files).
TARGET_PROFILES = {
    "Arduino Uno": {
        "name": "Arduino Uno / Nano",
        "description": "AVR ATmega328P based board.",
        "arch": "AVR8",
        "cpu_mhz": 16,
        "flash_kb": 32,
        "sram_b": 2048
    },
    "ESP32 DevKitC": {
        "name": "ESP32 DevKitC",
        "description": "Xtensa LX6 based MCU with WiFi/BT.",
        "arch": "Xtensa LX6",
        "cpu_mhz": 240,
        "flash_kb": 4096,
        "sram_b": 520 * 1024 # 520 KB
    },
    "Raspberry Pi Pico": {
        "name": "Raspberry Pi Pico",
        "description": "RP2040 (ARM Cortex-M0+) based MCU.",
        "arch": "ARM Cortex-M0+",
        "cpu_mhz": 133,
        "flash_kb": 2048,
        "sram_b": 264 * 1024 # 264 KB
    },
    "Generic 32-bit MCU (Medium)": {
        "name": "Generic 32-bit MCU (Medium)",
        "description": "Represents a typical mid-range ARM Cortex-M4/M7.",
        "arch": "ARM32",
        "cpu_mhz": 180,
        "flash_kb": 1024,
        "sram_b": 256 * 1024 # 256 KB
    }
}