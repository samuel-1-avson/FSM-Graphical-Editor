# tests/conftest.py
import pytest
from PyQt5.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp_args():
    """Provides a QCoreApplication instance for tests that need it without a GUI."""
    return QApplication.instance() or QApplication([])