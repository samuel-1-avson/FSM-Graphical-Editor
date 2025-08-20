# tests/test_settings_manager.py
import pytest
from PyQt6.QtCore import QCoreApplication
from fsm_designer_project.managers.settings_manager import SettingsManager

@pytest.fixture
def settings_manager(qapp_args):
    # Use a unique org/app name for testing to not interfere with user settings
    QCoreApplication.setOrganizationName("BSM_Test_Org")
    QCoreApplication.setApplicationName("BSM_Test_App")
    sm = SettingsManager(app_name="BSM_Test_App")
    sm.settings.clear()  # Ensure a clean slate for each test
    yield sm
    sm.settings.clear()  # Cleanup after test

def test_settings_manager_defaults(settings_manager):
    assert settings_manager.get("view_show_grid") is True
    assert settings_manager.get("resource_monitor_interval_ms") == 2000
    assert settings_manager.get("recent_files") == []
    assert settings_manager.get("non_existent_key") is None
    assert settings_manager.get("non_existent_key", "fallback") == "fallback"

def test_settings_manager_set_get(settings_manager):
    settings_manager.set("view_show_grid", False)
    assert settings_manager.get("view_show_grid") is False

    settings_manager.set("resource_monitor_interval_ms", 5000)
    assert settings_manager.get("resource_monitor_interval_ms") == 5000
    
    test_list = ["/path/a", "/path/b"]
    settings_manager.set("recent_files", test_list)
    assert settings_manager.get("recent_files") == test_list

def test_setting_persists_after_reinitialization():
    """Verify that settings are actually saved to disk."""
    QCoreApplication.setOrganizationName("BSM_Test_Org")
    QCoreApplication.setApplicationName("BSM_Persist_Test_App")
    
    # First instance saves a value
    sm1 = SettingsManager(app_name="BSM_Persist_Test_App")
    sm1.settings.clear()
    sm1.set("appearance_theme", "Monochrome")
    sm1.save_settings() # Force sync to disk
    del sm1

    # Second instance should load that value
    sm2 = SettingsManager(app_name="BSM_Persist_Test_App")
    assert sm2.get("appearance_theme") == "Monochrome"
    sm2.settings.clear() # Cleanup

def test_settings_manager_signal(settings_manager, qtbot):
    with qtbot.waitSignal(settings_manager.settingChanged, timeout=1000) as blocker:
        settings_manager.set("view_snap_to_grid", False)

    assert blocker.args == ["view_snap_to_grid", False]

def test_reset_to_defaults(settings_manager, qtbot):
    # Change a setting from its default
    settings_manager.set("view_show_grid", False)
    assert settings_manager.get("view_show_grid") is False

    # Reset
    with qtbot.waitSignal(settings_manager.settingsReset, timeout=1000):
        settings_manager.reset_to_defaults()

    # Verify the setting has been reset
    assert settings_manager.get("view_show_grid") is True