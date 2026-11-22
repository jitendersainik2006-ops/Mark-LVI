"""
core/floating_companion.py — J.A.R.V.I.S. Floating AI Desktop Companion Widget

Provides a lightweight, draggable, borderless floating companion window inspired
by modern desktop AI companions (Stonic / Cybernetic HUD):
- States: IDLE, LISTENING, THINKING, SPEAKING, WORKING
- Live audio reactivity: reactive energy ring and waveform particles
- Draggable and dockable anywhere on the Windows screen
- Right-click context menu: Push-to-Talk, Daily Briefing, Mute, Dashboard, Settings, Quit
- Hotkey integration and state reflection
- Software rendered via PyQt6 (zero GPU/OpenGL requirements)
"""

from __future__ import annotations

import math
import sys
from typing import Optional

try:
    from PyQt6.QtCore import QPoint, QPointF, QRectF, QTimer, Qt
    from PyQt6.QtGui import (
        QAction,
        QBrush,
        QColor,
        QFont,
        QLinearGradient,
        QPainter,
        QPen,
        QRadialGradient,
    )
    from PyQt6.QtWidgets import QApplication, QMenu, QWidget
    _PYQT_AVAILABLE = True
except ImportError:
    _PYQT_AVAILABLE = False


class FloatingCompanionWidget(QWidget if _PYQT_AVAILABLE else object):
    """Floating Desktop Assistant Widget with animated cybernetic avatar states."""

    STATE_COLORS = {
        "IDLE": QColor(0, 244, 255) if _PYQT_AVAILABLE else "#00f4ff",       # Cyan
        "LISTENING": QColor(0, 255, 128) if _PYQT_AVAILABLE else "#00ff80",  # Spring Green
        "THINKING": QColor(255, 200, 0) if _PYQT_AVAILABLE else "#ffc800",   # Amber
        "SPEAKING": QColor(255, 0, 180) if _PYQT_AVAILABLE else "#ff00b4",   # Neon Magenta
        "WORKING": QColor(255, 100, 0) if _PYQT_AVAILABLE else "#ff6400",    # Orange
        "ERROR": QColor(255, 0, 51) if _PYQT_AVAILABLE else "#ff0033",       # Crimson Red
        "HAPPY": QColor(34, 211, 238) if _PYQT_AVAILABLE else "#22d3ee",
        "CHEERFUL": QColor(56, 189, 248) if _PYQT_AVAILABLE else "#38bdf8",
        "CALM": QColor(52, 211, 153) if _PYQT_AVAILABLE else "#34d399",
        "CURIOUS": QColor(129, 140, 248) if _PYQT_AVAILABLE else "#818cf8",
        "EXCITED": QColor(244, 63, 94) if _PYQT_AVAILABLE else "#f43f5e",
        "THOUGHTFUL": QColor(167, 139, 250) if _PYQT_AVAILABLE else "#a78bfa",
        "CONFIDENT": QColor(0, 244, 255) if _PYQT_AVAILABLE else "#00f4ff",
        "CONCERNED": QColor(251, 191, 36) if _PYQT_AVAILABLE else "#fbbf24",
        "EMPATHETIC": QColor(244, 114, 182) if _PYQT_AVAILABLE else "#f472b6",
        "PLAYFUL": QColor(236, 72, 153) if _PYQT_AVAILABLE else "#ec4899",
        "FOCUSED": QColor(6, 182, 212) if _PYQT_AVAILABLE else "#06b6d4",
        "PAUSED": QColor(148, 163, 184) if _PYQT_AVAILABLE else "#94a3b8",
        "SUCCESS": QColor(34, 197, 94) if _PYQT_AVAILABLE else "#22c55e",
    }

    THEMES = {
        "CYAN": QColor(0, 244, 255) if _PYQT_AVAILABLE else "#00f4ff",
        "GOLD": QColor(255, 183, 0) if _PYQT_AVAILABLE else "#ffb700",
        "GREEN": QColor(0, 255, 102) if _PYQT_AVAILABLE else "#00ff66",
        "PURPLE": QColor(168, 85, 247) if _PYQT_AVAILABLE else "#a855f7",
        "CRIMSON": QColor(255, 42, 42) if _PYQT_AVAILABLE else "#ff2a2a",
    }

    def __init__(self, parent=None, size: int = 140):
        if not _PYQT_AVAILABLE:
            raise RuntimeError("PyQt6 is required for FloatingCompanionWidget.")
        super().__init__(parent)
        self.widget_size = size
        self.state = "IDLE"
        self.audio_level = 0.0
        self.phase = 0.0
        self.drag_position = QPoint()
        self.current_theme = "CYAN"
        self.always_on_top = True
        self.auto_hide_fullscreen = True
        self.show_rings = True
        self.show_aura = True
        self.show_pulse = True
        self.show_label = True
        self._hidden_by_fullscreen = False
        self.character_presentation = "NEUTRAL"
        self.wholesome_decorations = ["flowers", "hearts", "soft_bokeh"]
        self.animation_enabled = True
        self.intensity = 0.8
        self.current_emotion = "IDLE"

        # Window styling: Frameless, transparent background, always on top
        self._update_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(self.widget_size, self.widget_size)

        # 60 FPS animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_tick)
        self.anim_timer.start(16)

        # Fullscreen detection timer (every 1.5s)
        self.fullscreen_timer = QTimer(self)
        self.fullscreen_timer.timeout.connect(self._check_fullscreen_app)
        self.fullscreen_timer.start(1500)

    def _update_window_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def set_always_on_top(self, enable: bool):
        self.always_on_top = bool(enable)
        was_visible = self.isVisible()
        self._update_window_flags()
        if was_visible:
            self.show()

    def set_theme(self, theme_name: str):
        tn = str(theme_name).upper()
        if tn in self.THEMES:
            self.current_theme = tn
            if self.state == "IDLE":
                self.STATE_COLORS["IDLE"] = self.THEMES[tn]
            self.update()

    def set_visual_effect(self, effect_name: str, enabled: bool):
        en = bool(enabled)
        if effect_name == "rings":
            self.show_rings = en
        elif effect_name == "aura":
            self.show_aura = en
        elif effect_name == "pulse":
            self.show_pulse = en
        elif effect_name == "label":
            self.show_label = en
        self.update()

    def _check_fullscreen_app(self):
        """Auto-hide during fullscreen applications and games when enabled."""
        if not self.auto_hide_fullscreen:
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd or hwnd == int(self.winId()):
                return

            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)

            # Check if foreground window covers or exceeds the primary screen
            win_w = rect.right - rect.left
            win_h = rect.bottom - rect.top
            is_fullscreen = (win_w >= screen_w and win_h >= screen_h and rect.left <= 0 and rect.top <= 0)

            if is_fullscreen and not self._hidden_by_fullscreen and self.isVisible():
                self._hidden_by_fullscreen = True
                self.hide()
            elif not is_fullscreen and self._hidden_by_fullscreen:
                self._hidden_by_fullscreen = False
                self.show()
        except Exception:
            pass

    def set_character(self, character):
        if hasattr(character, "presentation"):
            self.character_presentation = character.presentation
            self.wholesome_decorations = getattr(character, "wholesome_decorations", [])
            self.animation_enabled = getattr(character, "animation_enabled", True)
            self.intensity = getattr(character, "intensity", 0.8)
        elif isinstance(character, dict):
            self.character_presentation = character.get("presentation", "NEUTRAL")
            self.wholesome_decorations = character.get("wholesome_decorations", [])
            self.animation_enabled = character.get("animation_enabled", True)
            self.intensity = character.get("intensity", 0.8)
        self.update()

    def set_emotion(self, emotion: str, intensity: Optional[float] = None):
        emo = str(emotion).upper()
        if emo in self.STATE_COLORS:
            self.current_emotion = emo
            self.state = emo
            if intensity is not None:
                self.intensity = max(0.0, min(1.0, float(intensity)))
            self.update()

    def set_animation_enabled(self, enabled: bool):
        self.animation_enabled = bool(enabled)
        self.update()

    def set_intensity(self, intensity: float):
        self.intensity = max(0.0, min(1.0, float(intensity)))
        self.update()

    def set_state(self, new_state: str):
        st = str(new_state).upper()
        if st in self.STATE_COLORS:
            self.state = st
            self.current_emotion = st
            self.update()

    def set_audio_level(self, level: float):
        self.audio_level = max(0.0, min(1.0, float(level)))

    def _on_tick(self):
        if not self.animation_enabled:
            return
        speed_mult = 1.0
        try:
            from core.character_manager import EMOTION_REGISTRY
            if self.state in EMOTION_REGISTRY:
                speed_mult = EMOTION_REGISTRY[self.state].pulse_speed
        except Exception:
            pass
        self.phase += 0.05 * speed_mult * self.intensity
        if self.phase > 1000.0:
            self.phase = 0.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0b111e;
                color: #e0f2fe;
                border: 1px solid #00f4ff;
                padding: 6px;
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1e293b;
                color: #00f4ff;
            }
        """)

        act_briefing = menu.addAction("🎙️ Daily Briefing")
        act_ptt = menu.addAction("🗣️ Push-to-Talk")
        menu.addSeparator()

        # Window & Behavior Submenu
        act_aot = menu.addAction("📌 Always on Top")
        act_aot.setCheckable(True)
        act_aot.setChecked(self.always_on_top)

        act_fs = menu.addAction("🎮 Auto-Hide in Fullscreen")
        act_fs.setCheckable(True)
        act_fs.setChecked(self.auto_hide_fullscreen)

        # Themes Submenu
        theme_menu = menu.addMenu("🎨 Themes")
        for tname in self.THEMES:
            t_act = theme_menu.addAction(f"Theme: {tname.capitalize()}")
            if self.current_theme == tname:
                t_act.setCheckable(True)
                t_act.setChecked(True)

        # Effects Submenu
        fx_menu = menu.addMenu("✨ Visual Effects")
        act_fx_rings = fx_menu.addAction("Orbital Rings")
        act_fx_rings.setCheckable(True)
        act_fx_rings.setChecked(self.show_rings)

        act_fx_aura = fx_menu.addAction("Glow Aura")
        act_fx_aura.setCheckable(True)
        act_fx_aura.setChecked(self.show_aura)

        act_fx_pulse = fx_menu.addAction("Audio Pulse")
        act_fx_pulse.setCheckable(True)
        act_fx_pulse.setChecked(self.show_pulse)

        act_fx_lbl = fx_menu.addAction("State Label")
        act_fx_lbl.setCheckable(True)
        act_fx_lbl.setChecked(self.show_label)

        menu.addSeparator()
        act_dash = menu.addAction("🖥️ Open Dashboard")
        act_mute = menu.addAction("🔇 Toggle Mic Mute")
        menu.addSeparator()
        act_hide = menu.addAction("❌ Hide Companion")

        action = menu.exec(pos)
        if action == act_briefing:
            self._trigger_daily_briefing()
        elif action == act_aot:
            self.set_always_on_top(not self.always_on_top)
        elif action == act_fs:
            self.auto_hide_fullscreen = not self.auto_hide_fullscreen
        elif action == act_fx_rings:
            self.set_visual_effect("rings", not self.show_rings)
        elif action == act_fx_aura:
            self.set_visual_effect("aura", not self.show_aura)
        elif action == act_fx_pulse:
            self.set_visual_effect("pulse", not self.show_pulse)
        elif action == act_fx_lbl:
            self.set_visual_effect("label", not self.show_label)
        elif action and action.text().startswith("Theme: "):
            chosen = action.text().replace("Theme: ", "").upper()
            self.set_theme(chosen)
        elif action == act_dash:
            import webbrowser
            webbrowser.open("http://127.0.0.1:8000/app")
        elif action == act_hide:
            self.hide()

    def _trigger_daily_briefing(self):
        try:
            from core.daily_briefing import daily_briefing_engine
            report = daily_briefing_engine.generate_briefing_text()
            print(f"[Companion] Daily Briefing:\n{report}")
        except Exception as e:
            print(f"[Companion] Briefing notice: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        base_radius = (min(self.width(), self.height()) / 2.0) - 15.0

        accent_color = self.STATE_COLORS.get(self.state, QColor(0, 244, 255))

        # 1. Outer Glow Aura (Optional)
        if self.show_aura:
            glow_grad = QRadialGradient(center_x, center_y, base_radius + 12.0)
            glow_alpha = int(40 + 70 * (self.audio_level if self.state in ("LISTENING", "SPEAKING") else 0.3))
            col_with_alpha = QColor(accent_color)
            col_with_alpha.setAlpha(glow_alpha)
            glow_grad.setColorAt(0.0, col_with_alpha)
            glow_grad.setColorAt(0.8, QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 10))
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(base_radius + 12), int(base_radius + 12))

        # 2. Cybernetic Core Orb
        core_grad = QRadialGradient(center_x, center_y, base_radius)
        core_grad.setColorAt(0.0, QColor(10, 20, 35, 230))
        core_grad.setColorAt(0.7, QColor(5, 12, 24, 245))
        core_grad.setColorAt(1.0, QColor(2, 6, 14, 255))
        painter.setBrush(QBrush(core_grad))
        painter.setPen(QPen(accent_color, 1.8))
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(base_radius), int(base_radius))

        # 3. Rotating Orbital Ring Segments (Optional)
        if self.show_rings:
            painter.save()
            painter.translate(center_x, center_y)
            rotation_speed = 3.0 if self.state == "THINKING" else (1.5 if self.state == "WORKING" else 0.8)
            painter.rotate(self.phase * 20.0 * rotation_speed)

            ring_pen = QPen(accent_color, 2.2)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            num_arcs = 4
            arc_span = 55
            for i in range(num_arcs):
                start_angle = int((i * (360 / num_arcs) + self.phase * 10) * 16)
                painter.drawArc(
                    QRectF(-base_radius + 4, -base_radius + 4, (base_radius - 4) * 2, (base_radius - 4) * 2),
                    start_angle,
                    arc_span * 16,
                )
            painter.restore()

        # 4. Animated Center Symbol / Voice Pulse (Optional)
        if self.show_pulse:
            pulse = math.sin(self.phase * 3.0) * 4.0 + (self.audio_level * 12.0)
            inner_r = max(6.0, 16.0 + pulse)
        else:
            inner_r = 16.0
        inner_glow = QColor(accent_color)
        inner_glow.setAlpha(180)
        painter.setBrush(QBrush(inner_glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(inner_r), int(inner_r))

        # 5. Wholesome Decorative Vector Accents (Flowers / Hearts / Motivational Sparkles)
        if (self.character_presentation == "FEMALE" or
            self.state in ("HAPPY", "CHEERFUL", "EMPATHETIC", "PLAYFUL")):
            painter.save()
            painter.translate(center_x, center_y)
            deco_color = QColor(accent_color)
            deco_color.setAlpha(int(150 * self.intensity))
            painter.setPen(QPen(deco_color, 1.2))
            painter.setBrush(QBrush(deco_color))
            num_petals = 6
            for p_i in range(num_petals):
                angle = (p_i * (360.0 / num_petals) + (self.phase * 8.0 if self.animation_enabled else 0.0)) * math.pi / 180.0
                pr = base_radius + 5.0
                px = pr * math.cos(angle)
                py = pr * math.sin(angle)
                painter.drawEllipse(QPointF(px, py), 2.2, 2.2)
            painter.restore()

        # 6. State Text Label (Optional)
        if self.show_label:
            painter.setPen(QColor(220, 245, 255, 220))
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
            painter.setFont(font)
            text_rect = QRectF(0, center_y + base_radius - 22, self.width(), 16)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.state)


_COMPANION_INSTANCE: Optional[FloatingCompanionWidget] = None


def get_floating_companion(size: int = 140) -> Optional[FloatingCompanionWidget]:
    """Returns singleton instance of FloatingCompanionWidget."""
    global _COMPANION_INSTANCE
    if not _PYQT_AVAILABLE:
        return None
    app = QApplication.instance()
    if not app:
        return None
    if _COMPANION_INSTANCE is None:
        _COMPANION_INSTANCE = FloatingCompanionWidget(size=size)
    return _COMPANION_INSTANCE


def main():
    if not _PYQT_AVAILABLE:
        print("[FloatingCompanion] PyQt6 is not available. Please install PyQt6.")
        return
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS Floating Companion")
    widget = FloatingCompanionWidget()
    widget.show()
    print("[FloatingCompanion] Widget displayed on screen.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

