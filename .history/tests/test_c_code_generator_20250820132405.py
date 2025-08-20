# tests/test_c_code_generator.py
import pytest
import json
import re
from pathlib import Path
from fsm_designer_project.codegen import generate_c_code_content, sanitize_c_identifier

# Define paths relative to the test file for robustness
TEST_DATA_DIR = Path(__file__).parent / "test_data"
GOLDEN_FILES_DIR = Path(__file__).parent / "golden_files"

def test_sanitize_c_identifier():
    assert sanitize_c_identifier("State Name 1") == "State_Name_1"
    assert sanitize_c_identifier("1_State", prefix="s_") == "s_1_State"
    assert sanitize_c_identifier("if") == "fsm_if"
    assert sanitize_c_identifier("") == "s_Unnamed"

@pytest.fixture
def simple_toggle_fsm_data():
    """Loads the canonical simple_toggle.bsm data."""
    bsm_file = TEST_DATA_DIR / "simple_toggle.bsm"
    assert bsm_file.exists(), "Test data file simple_toggle.bsm is missing."
    with open(bsm_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def strip_timestamps(code_content: str) -> str:
    """Removes generated timestamps to allow for stable file comparisons."""
    # This regex is more robust and will match different timestamp formats
    timestamp_pattern = re.compile(r"Generated on:.*", re.IGNORECASE)
    return timestamp_pattern.sub("Generated on: TIMESTAMP", code_content)

def test_c_code_generation_matches_golden_file(simple_toggle_fsm_data):
    """
    Tests that C code generation output exactly matches the pre-approved golden files.
    This prevents accidental regressions in the code generation logic.
    """
    # 1. Generate the code from the test data
    generated_code = generate_c_code_content(
        diagram_data=simple_toggle_fsm_data,
        fsm_name="simple_toggle",
        target_platform="Generic C (Header/Source Pair)"
    )
    
    generated_h = generated_code.get('h', '')
    generated_c = generated_code.get('c', '')

    # 2. Load the golden files
    golden_h_path = GOLDEN_FILES_DIR / "simple_toggle.h"
    golden_c_path = GOLDEN_FILES_DIR / "simple_toggle.c"

    assert golden_h_path.exists(), "Golden header file is missing!"
    assert golden_c_path.exists(), "Golden source file is missing!"

    # Normalize line endings and strip timestamps for comparison
    golden_h = strip_timestamps(golden_h_path.read_text(encoding='utf-8').replace('\r\n', '\n'))
    golden_c = strip_timestamps(golden_c_path.read_text(encoding='utf-8').replace('\r\n', '\n'))
    generated_h = strip_timestamps(generated_h.replace('\r\n', '\n'))
    generated_c = strip_timestamps(generated_c.replace('\r\n', '\n'))

    # 3. Compare the generated code to the golden files
    assert generated_h == golden_h, "Generated .h file does not match the golden version."
    assert generated_c == golden_c, "Generated .c file does not match the golden version."

def test_generate_c_code_empty_fsm():
    with pytest.raises(ValueError, match="Cannot generate code: No states defined"):
        generate_c_code_content({}, "empty_fsm", "Generic C (Header/Source Pair)")