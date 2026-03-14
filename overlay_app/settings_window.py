from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .settings_manager import SettingsManager

LOGGER = logging.getLogger("overlay.settings_window")


class SettingsWindow(QDialog):
    """Settings dialog for Bazaar Overlay."""
    
    settings_changed = Signal(dict)
    
    def __init__(self, settings: SettingsManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self._original_settings = settings.get_all().copy()
        
        self.setWindowTitle("Bazaar Overlay - Settings")
        self.setMinimumWidth(450)
        self.setModal(True)
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Capture Settings
        capture_group = QGroupBox("Capture Settings")
        capture_layout = QFormLayout()
        
        self.roi_width = QSpinBox()
        self.roi_width.setRange(200, 2000)
        self.roi_width.setSuffix(" px")
        capture_layout.addRow("ROI Width:", self.roi_width)
        
        self.roi_height = QSpinBox()
        self.roi_height.setRange(200, 2000)
        self.roi_height.setSuffix(" px")
        capture_layout.addRow("ROI Height:", self.roi_height)
        
        self.poll_ms = QSpinBox()
        self.poll_ms.setRange(25, 500)
        self.poll_ms.setSuffix(" ms")
        capture_layout.addRow("Poll Interval:", self.poll_ms)
        
        self.skip_frames = QSpinBox()
        self.skip_frames.setRange(1, 10)
        capture_layout.addRow("Skip Frames:", self.skip_frames)
        
        self.ocr_region = QLineEdit()
        self.ocr_region.setPlaceholderText("x,y,width,height (e.g., 0,0,500,100)")
        capture_layout.addRow("OCR Region:", self.ocr_region)
        
        capture_group.setLayout(capture_layout)
        layout.addWidget(capture_group)
        
        # Hotkey Settings
        hotkey_group = QGroupBox("Hotkey")
        hotkey_layout = QFormLayout()
        
        hotkey_hint = QLabel("Current: Shift + E")
        hotkey_hint.setFont(QFont("", -1, QFont.Bold))
        hotkey_layout.addRow("Hotkey:", hotkey_hint)
        self._hotkey_label = hotkey_hint
        
        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)
        
        # General Settings
        general_group = QGroupBox("General")
        general_layout = QVBoxLayout()
        
        self.auto_start = QCheckBox("Start with Windows")
        general_layout.addWidget(self.auto_start)
        
        self.minimize_to_tray = QCheckBox("Minimize to system tray")
        general_layout.addWidget(self.minimize_to_tray)
        
        self.show_notifications = QCheckBox("Show notification when item detected")
        general_layout.addWidget(self.show_notifications)
        
        self.debug_mode = QCheckBox("Debug mode (shows OCR region)")
        general_layout.addWidget(self.debug_mode)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(self.reset_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def _load_settings(self) -> None:
        s = self._settings.get_all()
        
        self.roi_width.setValue(s.get("roi_width", 1200))
        self.roi_height.setValue(s.get("roi_height", 800))
        self.poll_ms.setValue(s.get("poll_ms", 75))
        self.skip_frames.setValue(s.get("skip_frames", 7))
        self.ocr_region.setText(s.get("ocr_region", "0,0,0,0"))
        self.auto_start.setChecked(s.get("auto_start", False))
        self.minimize_to_tray.setChecked(s.get("minimize_to_tray", True))
        self.show_notifications.setChecked(s.get("show_notifications", True))
        self.debug_mode.setChecked(s.get("debug", False))
    
    def _reset_to_defaults(self) -> None:
        self.roi_width.setValue(1200)
        self.roi_height.setValue(800)
        self.poll_ms.setValue(75)
        self.skip_frames.setValue(7)
        self.ocr_region.setText("0,0,0,0")
        self.auto_start.setChecked(False)
        self.minimize_to_tray.setChecked(True)
        self.show_notifications.setChecked(True)
        self.debug_mode.setChecked(False)
    
    def _save_settings(self) -> None:
        self._settings.set("roi_width", self.roi_width.value())
        self._settings.set("roi_height", self.roi_height.value())
        self._settings.set("poll_ms", self.poll_ms.value())
        self._settings.set("skip_frames", self.skip_frames.value())
        self._settings.set("ocr_region", self.ocr_region.text())
        self._settings.set("auto_start", self.auto_start.isChecked())
        self._settings.set("minimize_to_tray", self.minimize_to_tray.isChecked())
        self._settings.set("show_notifications", self.show_notifications.isChecked())
        self._settings.set("debug", self.debug_mode.isChecked())
        
        # Handle auto-start separately
        current_auto_start = self._settings.get_auto_start()
        if self.auto_start.isChecked() != current_auto_start:
            self._settings.set_auto_start(self.auto_start.isChecked())
        
        self._settings.save()
        self.settings_changed.emit(self._settings.get_all())
        self.accept()
