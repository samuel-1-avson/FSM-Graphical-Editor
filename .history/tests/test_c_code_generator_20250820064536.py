# tests/test_c_code_generator.py
import pytest
import json
from pathlib import Path
from fsm_designer_project.codegen import generate_c_code_content

# Define paths relative to the test file
TEST_DATA_DIR = Path(__file__).parent / "test_data"
GOLDEN_FILES_DIR = Path(__file__).parent / "golden_files"

@pytest.fixture
def simple_toggle_fsm_data():
    """Loads the canonical simple_toggle.bsm data."""
    with open(TEST_DATA_DIR / "simple_toggle.bsm", 'r') as f:
        return json.load(f)

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

    golden_h = golden_h_path.read_text().replace('\r\n', '\n')
    golden_c = golden_c_path.read_text().replace('\r\n', '\n')

    # 3. Compare the generated code to the golden files
    # We ignore the timestamp line for a stable comparison.
    
    def strip_timestamp(code):
        import re
        return re.sub(r"Generated on:.*", "Generated on: TIMESTAMP", code)

    generated_h_no_ts = strip_timestamp(generated_h)
    golden_h_no_ts = strip_timestamp(golden_h)
    
    assert generated_h_no_ts == golden_h_no_ts, "Generated .h file does not match the golden version."

    generated_c_no_ts = strip_timestamp(generated_c)
    golden_c_no_ts = strip_timestamp(golden_c)
    
    assert generated_c_no_ts == golden_c_no_ts, "Generated .c file does not match the golden version."