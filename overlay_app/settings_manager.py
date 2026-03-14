from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import winreg

LOGGER = logging.getLogger("overlay.settings")


class SettingsManager:
    """Manages application settings with persistence."""

    DEFAULT_SETTINGS = {
        "roi_width": 1200,
        "roi_height": 800,
        "poll_ms": 75,
        "skip_frames": 7,
        "ocr_region": "0,0,0,0",
        "debug": False,
        "auto_start": False,
        "hotkey_modifier": "shift",
        "hotkey_key": "e",
        "minimize_to_tray": True,
        "show_notifications": True,
    }

    def __init__(self):
        self._settings: dict[str, Any] = {}
        self._config_path = self._get_config_path()
        self.load()

    def _get_config_path(self) -> Path:
        """Get config file path in AppData."""
        app_data = Path(os.environ.get("APPDATA", ""))
        config_dir = app_data / "BazaarOverlay"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "settings.json"

    def load(self) -> None:
        """Load settings from file."""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._settings = {**self.DEFAULT_SETTINGS, **loaded}
                    LOGGER.info("Settings loaded from %s", self._config_path)
            except Exception as e:
                LOGGER.warning("Failed to load settings: %s, using defaults", e)
                self._settings = self.DEFAULT_SETTINGS.copy()
        else:
            self._settings = self.DEFAULT_SETTINGS.copy()
            LOGGER.info("Using default settings")

    def save(self) -> None:
        """Save settings to file."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
            LOGGER.info("Settings saved to %s", self._config_path)
        except Exception as e:
            LOGGER.error("Failed to save settings: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self._settings[key] = value

    def get_all(self) -> dict[str, Any]:
        """Get all settings."""
        return self._settings.copy()

    def set_auto_start(self, enabled: bool) -> None:
        """Enable or disable auto-start with Windows."""
        self._settings["auto_start"] = enabled
        
        app_path = Path(sys.executable).resolve()
        app_name = "BazaarOverlay"
        
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                if enabled:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, str(app_path))
                    LOGGER.info("Auto-start enabled")
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                        LOGGER.info("Auto-start disabled")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            LOGGER.error("Failed to set auto-start: %s", e)

    def get_auto_start(self) -> bool:
        """Check if auto-start is enabled."""
        app_name = "BazaarOverlay"
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, app_name)
                return True
        except FileNotFoundError:
            return False


import sys
