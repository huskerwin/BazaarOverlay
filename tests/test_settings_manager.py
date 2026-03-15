"""Tests for overlay_app settings_manager."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.settings_manager import SettingsManager


@pytest.fixture
def mock_config_path(tmp_path):
    """Fixture to provide a temporary config path."""
    config_file = tmp_path / "settings.json"
    with patch.object(SettingsManager, '_get_config_path') as mock:
        mock.return_value = config_file
        yield config_file


class TestSettingsManagerDefaults:
    """Test default settings."""

    def test_default_settings_values(self, mock_config_path):
        """Test that default settings have correct values."""
        manager = SettingsManager()
        
        assert manager.get("roi_width") == 1200
        assert manager.get("roi_height") == 800
        assert manager.get("poll_ms") == 75
        assert manager.get("skip_frames") == 7
        assert manager.get("ocr_region") == "0,0,0,0"
        assert manager.get("debug") is False
        assert manager.get("auto_start") is False
        assert manager.get("hotkey_modifier") == "shift"
        assert manager.get("hotkey_key") == "e"
        assert manager.get("minimize_to_tray") is True
        assert manager.get("show_notifications") is True

    def test_get_all_returns_all_settings(self, mock_config_path):
        """Test get_all returns all settings."""
        manager = SettingsManager()
        all_settings = manager.get_all()
        
        assert isinstance(all_settings, dict)
        assert len(all_settings) > 0
        assert "roi_width" in all_settings
        assert "roi_height" in all_settings


class TestSettingsManagerGetSet:
    """Test get and set methods."""

    def test_get_with_default(self, mock_config_path):
        """Test get returns default for unknown key."""
        manager = SettingsManager()
        
        result = manager.get("nonexistent_key", "default_value")
        assert result == "default_value"

    def test_get_without_default_returns_none(self, mock_config_path):
        """Test get returns None for unknown key without default."""
        manager = SettingsManager()
        
        result = manager.get("nonexistent_key")
        assert result is None

    def test_set_updates_value(self, mock_config_path):
        """Test set updates a setting value."""
        manager = SettingsManager()
        
        manager.set("roi_width", 800)
        assert manager.get("roi_width") == 800

    def test_set_multiple_values(self, mock_config_path):
        """Test setting multiple values."""
        manager = SettingsManager()
        
        manager.set("poll_ms", 100)
        manager.set("debug", True)
        manager.set("skip_frames", 5)
        
        assert manager.get("poll_ms") == 100
        assert manager.get("debug") is True
        assert manager.get("skip_frames") == 5


class TestSettingsManagerSaveLoad:
    """Test save and load functionality."""

    def test_save_creates_file(self, tmp_path):
        """Test save creates a settings file."""
        config_file = tmp_path / "settings.json"
        
        with patch.object(SettingsManager, '_get_config_path') as mock_path:
            mock_path.return_value = config_file
            
            manager = SettingsManager()
            manager.set("roi_width", 1500)
            manager.save()
            
            assert config_file.exists()

    def test_load_reads_saved_settings(self, tmp_path):
        """Test load reads saved settings correctly."""
        config_file = tmp_path / "settings.json"
        config_file.write_text(json.dumps({"roi_width": 2000, "custom_key": "custom_value"}))
        
        with patch.object(SettingsManager, '_get_config_path') as mock_path:
            mock_path.return_value = config_file
            
            manager = SettingsManager()
            
            assert manager.get("roi_width") == 2000
            assert manager.get("custom_key") == "custom_value"

    def test_load_merges_with_defaults(self, tmp_path):
        """Test load merges saved settings with defaults."""
        config_file = tmp_path / "settings.json"
        config_file.write_text(json.dumps({"roi_width": 999}))
        
        with patch.object(SettingsManager, '_get_config_path') as mock_path:
            mock_path.return_value = config_file
            
            manager = SettingsManager()
            
            assert manager.get("roi_width") == 999
            assert manager.get("roi_height") == 800  # default

    def test_load_handles_invalid_json(self, tmp_path):
        """Test load handles invalid JSON gracefully."""
        config_file = tmp_path / "settings.json"
        config_file.write_text("invalid json {")
        
        with patch.object(SettingsManager, '_get_config_path') as mock_path:
            mock_path.return_value = config_file
            
            manager = SettingsManager()
            
            assert manager.get("roi_width") == 1200  # falls back to default


class TestSettingsManagerIsFirstRun:
    """Test is_first_run method."""

    def test_is_first_run_true_when_no_file(self, tmp_path):
        """Test is_first_run returns True when no settings file exists."""
        with patch.object(SettingsManager, '_get_config_path') as mock_path:
            config_file = tmp_path / "settings.json"
            mock_path.return_value = config_file
            
            manager = SettingsManager()
            
            assert manager.is_first_run() is True

    def test_is_first_run_false_when_file_exists(self, tmp_path):
        """Test is_first_run returns False when settings file exists."""
        config_file = tmp_path / "settings.json"
        config_file.write_text("{}")
        
        with patch.object(SettingsManager, '_get_config_path') as mock_path:
            mock_path.return_value = config_file
            
            manager = SettingsManager()
            
            assert manager.is_first_run() is False


class TestSettingsManagerAutoStart:
    """Test auto-start functionality (basic tests only)."""

    def test_set_auto_start_stores_value(self, tmp_path):
        """Test set_auto_start stores the value in settings."""
        config_file = tmp_path / "settings.json"
        
        with patch.object(SettingsManager, '_get_config_path') as mock_path:
            mock_path.return_value = config_file
            
            manager = SettingsManager()
            manager.set_auto_start(True)
            
            assert manager.get("auto_start") is True

    def test_get_auto_start_default(self, tmp_path):
        """Test get_auto_start returns default value."""
        config_file = tmp_path / "settings.json"
        
        with patch.object(SettingsManager, '_get_config_path') as mock_path:
            mock_path.return_value = config_file
            
            manager = SettingsManager()
            
            assert manager.get("auto_start") is False
