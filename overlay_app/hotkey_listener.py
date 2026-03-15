from __future__ import annotations

import logging
import threading
from typing import Callable

from pynput import keyboard

LOGGER = logging.getLogger("overlay.hotkey")


class HoldHotkeyListener:
    def __init__(self, on_state_change: Callable[[bool], None], trigger_key: str = "e"):
        self._on_state_change = on_state_change
        self._trigger_key = trigger_key.lower()
        self._shift_down = False
        self._trigger_down = False
        self._active = False
        self._lock = threading.Lock()
        self._listener: keyboard.Listener | None = None

    def start(self) -> None:
        # Create new listener each time (listeners can't be restarted)
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        LOGGER.info("Listening for Shift+%s hold.", self._trigger_key.upper())

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        with self._lock:
            if self._is_shift_key(key):
                self._shift_down = True
            if self._is_trigger_key(key):
                self._trigger_down = True
            self._emit_state_if_changed()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        with self._lock:
            if self._is_shift_key(key):
                self._shift_down = False
            if self._is_trigger_key(key):
                self._trigger_down = False
            self._emit_state_if_changed()

    def _emit_state_if_changed(self) -> None:
        next_state = self._shift_down and self._trigger_down
        if next_state == self._active:
            return

        self._active = next_state
        try:
            self._on_state_change(next_state)
        except Exception:  # pragma: no cover - callback boundary
            LOGGER.exception("Hotkey state callback failed.")

    def _is_trigger_key(self, key: keyboard.Key | keyboard.KeyCode) -> bool:
        if isinstance(key, keyboard.KeyCode):
            if key.char is None:
                return False
            return key.char.lower() == self._trigger_key
        return False

    @staticmethod
    def _is_shift_key(key: keyboard.Key | keyboard.KeyCode) -> bool:
        return key in (
            keyboard.Key.shift,
            keyboard.Key.shift_l,
            keyboard.Key.shift_r,
        )
