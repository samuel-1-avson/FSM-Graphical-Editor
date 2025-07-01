# fsm_designer_project/resource_estimator.py (NEW FILE)

import logging
import re
from typing import Dict, Any, Tuple

# Assuming this file will be in the same package as other modules
try:
    from .target_profiles import TARGET_PROFILES
except ImportError:
    # Fallback for direct execution or testing
    TARGET_PROFILES = {
        "Arduino Uno": { "flash_kb": 32, "sram_b": 2048, "arch": "AVR8", "cpu_mhz": 16 },
        "Arduino Nano": { "flash_kb": 32, "sram_b": 2048, "arch": "AVR8", "cpu_mhz": 16 },
        "ESP32": { "flash_kb": 4096, "sram_b": 520 * 1024, "arch": "Xtensa LX6", "cpu_mhz": 240 },
        "RPi Pico": { "flash_kb": 2048, "sram_b": 264 * 1024, "arch": "ARM Cortex-M0+", "cpu_mhz": 133 }
    }

logger = logging.getLogger(__name__)

class ResourceEstimator:
    """
    Provides rough estimations for Flash and SRAM usage of an FSM on a target device.
    Note: These are heuristics and not a substitute for actual compilation.
    """

    # --- Constants for C-based Estimation ---
    # These are very rough and depend on compiler/architecture, but provide a baseline.
    AVR8_POINTER_SIZE = 2  # bytes for function pointers on AVR (e.g., Arduino Uno)
    ARM32_POINTER_SIZE = 4 # bytes for function pointers on 32-bit ARM (e.g., Pico, ESP32)

    BASE_FSM_STRUCT_SRAM = 20 # Rough bytes for FSM state variables, counters etc.
    SRAM_PER_STATE = 4        # Overhead for each state (e.g., in a state table)
    SRAM_PER_TRANSITION = 8   # Overhead for each transition

    BASE_FSM_CODE_FLASH = 250 # Rough bytes for the core FSM run/init logic
    FLASH_PER_ACTION_CHAR = 1.2 # Heuristic: each char of action code results in ~1.2 bytes of machine code
    FLASH_PER_STATE_LOGIC = 15  # Overhead for switch/case logic per state
    FLASH_PER_TRANSITION_LOGIC = 25 # Overhead for if/else logic per transition

    def __init__(self, target_profile_name: str = "Arduino Uno"):
        self.set_target(target_profile_name)

    def set_target(self, target_profile_name: str):
        self.target_profile = TARGET_PROFILES.get(target_profile_name)
        if not self.target_profile:
            logger.warning(f"ResourceEstimator: Target profile '{target_profile_name}' not found. Using Arduino Uno as fallback.")
            self.target_profile = TARGET_PROFILES["Arduino Uno"]
        
        self.arch = self.target_profile.get("arch", "AVR8")
        if "AVR" in self.arch:
            self.pointer_size = self.AVR8_POINTER_SIZE
        elif "ARM" in self.arch or "Xtensa" in self.arch:
            self.pointer_size = self.ARM32_POINTER_SIZE
        else:
            self.pointer_size = 4 # Default to 32-bit pointer size
        logger.info(f"ResourceEstimator: Target set to {target_profile_name} (arch: {self.arch}, ptr_size: {self.pointer_size})")

    def _count_function_pointers(self, diagram_data: Dict[str, Any]) -> int:
        """Counts actions/conditions that would likely become function pointers in C."""
        count = 0
        for state in diagram_data.get('states', []):
            if state.get('entry_action'): count += 1
            if state.get('during_action'): count += 1
            if state.get('exit_action'): count += 1
        for trans in diagram_data.get('transitions', []):
            if trans.get('action'): count += 1
            if trans.get('condition'): count += 1 # Conditions often become function pointers
        return count

    def _estimate_code_chars(self, diagram_data: Dict[str, Any]) -> int:
        """Counts the total number of characters in all code fields."""
        total_chars = 0
        for state in diagram_data.get('states', []):
            total_chars += len(state.get('entry_action', ''))
            total_chars += len(state.get('during_action', ''))
            total_chars += len(state.get('exit_action', ''))
        for trans in diagram_data.get('transitions', []):
            total_chars += len(trans.get('action', ''))
            total_chars += len(trans.get('condition', '')) # Conditions contribute to code size
        return total_chars
    
    def estimate(self, diagram_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Performs the estimation based on the current target profile and diagram data.
        Returns a dictionary with 'sram_b' and 'flash_b'.
        """
        if not self.target_profile:
            return {'sram_b': -1, 'flash_b': -1, 'error': 'No target profile selected'}

        num_states = len(diagram_data.get('states', []))
        num_transitions = len(diagram_data.get('transitions', []))

        # --- SRAM Estimation ---
        estimated_sram = self.BASE_FSM_STRUCT_SRAM
        estimated_sram += num_states * self.SRAM_PER_STATE
        estimated_sram += num_transitions * self.SRAM_PER_TRANSITION
        
        # Estimate SRAM for function pointers (e.g., in a state table)
        num_func_pointers = self._count_function_pointers(diagram_data)
        estimated_sram += num_func_pointers * self.pointer_size
        
        # This doesn't account for user-defined variables yet, which is a major simplification.

        # --- Flash Estimation ---
        estimated_flash = self.BASE_FSM_CODE_FLASH
        estimated_flash += num_states * self.FLASH_PER_STATE_LOGIC
        estimated_flash += num_transitions * self.FLASH_PER_TRANSITION_LOGIC

        code_chars = self._estimate_code_chars(diagram_data)
        estimated_flash += int(code_chars * self.FLASH_PER_ACTION_CHAR)
        
        return {
            'sram_b': estimated_sram,
            'flash_b': estimated_flash,
        }