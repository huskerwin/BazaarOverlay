"""Tests for overlay_app hotkey_listener."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from overlay_app.hotkey_listener import HoldHotkeyListener


class TestHoldHotkeyListenerInit:
    """Test initialization."""

    def test_default_trigger_key(self):
        """Test default trigger key is 'e'."""
        callback_called = []
        
        def callback(state):
            callback_called.append(state)
        
        listener = HoldHotkeyListener(callback)
        
        assert listener._trigger_key == "e"
        assert listener._on_state_change is callback

    def test_custom_trigger_key(self):
        """Test custom trigger key."""
        callback_called = []
        
        def callback(state):
            callback_called.append(state)
        
        listener = HoldHotkeyListener(callback, trigger_key="q")
        
        assert listener._trigger_key == "q"

    def test_trigger_key_lowercase(self):
        """Test trigger key is converted to lowercase."""
        callback_called = []
        
        def callback(state):
            callback_called.append(state)
        
        listener = HoldHotkeyListener(callback, trigger_key="Q")
        
        assert listener._trigger_key == "q"

    def test_initial_state(self):
        """Test initial state values."""
        callback_called = []
        
        def callback(state):
            callback_called.append(state)
        
        listener = HoldHotkeyListener(callback)
        
        assert listener._shift_down is False
        assert listener._trigger_down is False
        assert listener._active is False
        assert listener._listener is None


class TestHoldHotkeyListenerStart:
    """Test start method."""

    @patch('overlay_app.hotkey_listener.keyboard')
    def test_start_creates_listener(self, mock_keyboard):
        """Test start creates a keyboard listener."""
        mock_listener = MagicMock()
        mock_keyboard.Listener.return_value = mock_listener
        
        callback_called = []
        
        def callback(state):
            callback_called.append(state)
        
        listener = HoldHotkeyListener(callback)
        listener.start()
        
        mock_keyboard.Listener.assert_called_once()
        mock_listener.start.assert_called_once()
        assert listener._listener is mock_listener


class TestHoldHotkeyListenerStop:
    """Test stop method."""

    @patch('overlay_app.hotkey_listener.keyboard')
    def test_stop_stops_listener(self, mock_keyboard):
        """Test stop stops the keyboard listener."""
        mock_listener = MagicMock()
        mock_keyboard.Listener.return_value = mock_listener
        
        callback_called = []
        
        def callback(state):
            callback_called.append(state)
        
        listener = HoldHotkeyListener(callback)
        listener.start()
        listener.stop()
        
        mock_listener.stop.assert_called_once()
        assert listener._listener is None


class TestHoldHotkeyListenerKeyDetection:
    """Test key detection logic."""

    def test_is_trigger_key_with_char(self):
        """Test trigger key detection with character."""
        from pynput import keyboard
        
        callback_called = []
        
        def callback(state):
            callback_called.append(state)
        
        listener = HoldHotkeyListener(callback, trigger_key="e")
        
        key = keyboard.KeyCode(char="e")
        assert listener._is_trigger_key(key) is True
        
        key = keyboard.KeyCode(char="E")
        assert listener._is_trigger_key(key) is True
        
        key = keyboard.KeyCode(char="a")
        assert listener._is_trigger_key(key) is False

    def test_is_trigger_key_with_none_char(self):
        """Test trigger key detection with special keys."""
        from pynput import keyboard
        
        callback_called = []
        
        def callback(state):
            callback_called.append(state)
        
        listener = HoldHotkeyListener(callback, trigger_key="e")
        
        key = keyboard.Key.ctrl
        assert listener._is_trigger_key(key) is False

    @staticmethod
    def test_is_shift_key():
        """Test shift key detection."""
        from pynput import keyboard
        
        listener = HoldHotkeyListener(lambda s: None)
        
        assert listener._is_shift_key(keyboard.Key.shift) is True
        assert listener._is_shift_key(keyboard.Key.shift_l) is True
        assert listener._is_shift_key(keyboard.Key.shift_r) is True
        assert listener._is_shift_key(keyboard.Key.ctrl) is False
        assert listener._is_shift_key(keyboard.KeyCode(char="a")) is False


class TestHoldHotkeyListenerStateChanges:
    """Test state change detection - basic tests only."""
    
    def test_initial_state_false(self):
        """Test initial state is False."""
        listener = HoldHotkeyListener(lambda s: None)
        
        assert listener._active is False

    def test_shift_down_tracks_state(self):
        """Test that shift key tracking works."""
        from pynput import keyboard
        
        listener = HoldHotkeyListener(lambda s: None)
        
        assert listener._shift_down is False
        
        key_shift = keyboard.Key.shift
        listener._on_press(key_shift)
        
        assert listener._shift_down is True
        
        listener._on_release(key_shift)
        
        assert listener._shift_down is False
