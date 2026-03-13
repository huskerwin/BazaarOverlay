from __future__ import annotations

import logging

import numpy as np
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .config import OverlayConfig
from .models import OverlayPayload

LOGGER = logging.getLogger("overlay.ui")

try:
    import win32con
    import win32gui
except Exception:
    win32con = None
    win32gui = None


class OverlayWindow(QWidget):
    def __init__(self, config: OverlayConfig):
        super().__init__()
        self._config = config

        self._title = ""
        self._body = ""
        self._confidence = ""
        self._matched = False
        self._debug_image: np.ndarray | None = None
        self._ocr_region: tuple[int, int, int, int] | None = None

        self._padding = 12
        self._line_gap = 6

        self._title_font = QFont("Segoe UI", 10, QFont.Bold)
        self._body_font = QFont("Segoe UI", 9)
        self._confidence_font = QFont("Consolas", 8)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.resize(self._config.width, self._config.min_height)
        self.hide()

    def show_payload(self, payload: OverlayPayload) -> None:
        self._title = payload.title
        self._body = payload.body
        self._confidence = payload.confidence_text
        self._matched = payload.matched
        self._debug_image = payload.debug_image
        self._ocr_region = payload.ocr_region

        self._recompute_size()
        self._move_near_cursor(payload.cursor_pos)

        if not self.isVisible():
            self.show()
        self.raise_()
        self.update()

    def hide_overlay(self) -> None:
        self.hide()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_click_through()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        background = QColor(14, 18, 24, 225)
        border = QColor(90, 190, 110, 220) if self._matched else QColor(225, 175, 85, 220)
        title_color = QColor(206, 244, 210, 240) if self._matched else QColor(255, 229, 181, 240)
        body_color = QColor(230, 236, 245, 235)
        confidence_color = QColor(176, 188, 204, 220)

        painter.setBrush(background)
        painter.setPen(QPen(border, 1.25))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

        text_width = self.width() - (self._padding * 2)
        y = self._padding

        painter.setFont(self._title_font)
        painter.setPen(title_color)
        title_rect = painter.boundingRect(
            self._padding,
            y,
            text_width,
            1000,
            int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop),
            self._title,
        )
        painter.drawText(title_rect, int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop), self._title)
        y = title_rect.bottom() + 1 + self._line_gap

        painter.setFont(self._body_font)
        painter.setPen(body_color)
        body_rect = painter.boundingRect(
            self._padding,
            y,
            text_width,
            1000,
            int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop),
            self._body,
        )
        painter.drawText(body_rect, int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop), self._body)
        y = body_rect.bottom() + 1 + self._line_gap

        painter.setFont(self._confidence_font)
        painter.setPen(confidence_color)
        conf_rect = painter.boundingRect(
            self._padding,
            y,
            text_width,
            1000,
            int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop),
            self._confidence,
        )
        painter.drawText(
            conf_rect,
            int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop),
            self._confidence,
        )

    def _recompute_size(self) -> None:
        text_width = self._config.width - (self._padding * 2)
        flags = int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop)

        title_h = QFontMetrics(self._title_font).boundingRect(
            0, 0, text_width, 1000, flags, self._title
        ).height()
        body_h = QFontMetrics(self._body_font).boundingRect(
            0, 0, text_width, 1000, flags, self._body
        ).height()
        confidence_h = QFontMetrics(self._confidence_font).boundingRect(
            0, 0, text_width, 1000, flags, self._confidence
        ).height()

        content_h = (
            self._padding
            + title_h
            + self._line_gap
            + body_h
            + self._line_gap
            + confidence_h
            + self._padding
        )
        target_h = max(self._config.min_height, content_h)
        self.resize(self._config.width, target_h)

    def _move_near_cursor(self, cursor_pos: tuple[int, int]) -> None:
        target_x = cursor_pos[0] + self._config.x_offset
        target_y = cursor_pos[1] + self._config.y_offset

        screen = QGuiApplication.screenAt(QPoint(cursor_pos[0], cursor_pos[1]))
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.move(target_x, target_y)
            return

        geometry = screen.availableGeometry()
        max_x = geometry.x() + geometry.width() - self.width()
        max_y = geometry.y() + geometry.height() - self.height()

        clamped_x = max(geometry.x(), min(target_x, max_x))
        clamped_y = max(geometry.y(), min(target_y, max_y))
        self.move(clamped_x, clamped_y)

    def _apply_click_through(self) -> None:
        if win32con is None or win32gui is None:
            return

        try:
            hwnd = int(self.winId())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style |= win32con.WS_EX_LAYERED
            style |= win32con.WS_EX_TRANSPARENT
            style |= win32con.WS_EX_TOOLWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
        except Exception:
            LOGGER.exception("Unable to apply click-through window style.")


class DebugOverlayWindow(QWidget):
    hide_debug_signal = Signal()
    
    def __init__(self):
        super().__init__()
        self._debug_image: np.ndarray | None = None
        self._ocr_region: tuple[int, int, int, int] | None = None

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.hide_debug_signal.connect(self.hide_debug, Qt.QueuedConnection)
        
        self.resize(300, 250)
        self.hide()

    def show_debug(self, debug_image: np.ndarray | None, ocr_region: tuple[int, int, int, int] | None, cursor_pos: tuple[int, int]) -> None:
        self._debug_image = debug_image
        self._ocr_region = ocr_region

        h, w = 250, 300
        if debug_image is not None and debug_image.size > 0:
            ih, iw = debug_image.shape[:2]
            if ih > 0 and iw > 0:
                h = min(ih + 20, 300)
                w = min(iw + 20, 400)
        
        self.resize(w, h)
        self._move_near_cursor(cursor_pos)

        if not self.isVisible():
            self.show()
        self.raise_()
        self.update()

    def hide_debug(self) -> None:
        self.hide()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._debug_image is not None and self._debug_image.size > 0:
            h, w = self._debug_image.shape[:2]
            if h > 0 and w > 0:
                rgb_image = self._debug_image[:, :, ::-1].copy()
                qimg = QImage(rgb_image.data, w, h, w * 3, QImage.Format_RGB888)
                scaled = qimg.scaled(self.width() - 10, self.height() - 10, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawImage(5, 5, scaled)
                
                if self._ocr_region:
                    rx, ry, rw, rh = self._ocr_region
                    scale_x = scaled.width() / w
                    scale_y = scaled.height() / h
                    rect_x = int(rx * scale_x) + 5
                    rect_y = int(ry * scale_y) + 5
                    rect_w = int(rw * scale_x)
                    rect_h = int(rh * scale_y)
                    painter.setPen(QPen(QColor(255, 0, 0), 3))
                    painter.drawRect(rect_x, rect_y, rect_w, rect_h)
                    
                    painter.setPen(QColor(255, 0, 0))
                    painter.setFont(QFont("Consolas", 9))
                    painter.drawText(rect_x, rect_y - 5, f"OCR: +{rx},+{ry}")

    def _move_near_cursor(self, cursor_pos: tuple[int, int]) -> None:
        target_x = cursor_pos[0] + 20
        target_y = cursor_pos[1] + 20

        screen = QGuiApplication.screenAt(QPoint(cursor_pos[0], cursor_pos[1]))
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.move(target_x, target_y)
            return

        geometry = screen.availableGeometry()
        max_x = geometry.x() + geometry.width() - self.width()
        max_y = geometry.y() + geometry.height() - self.height()

        clamped_x = max(geometry.x(), min(target_x, max_x))
        clamped_y = max(geometry.y(), min(target_y, max_y))
        self.move(clamped_x, clamped_y)
