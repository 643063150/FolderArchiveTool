"""
Material Design 3 按钮控件
支持: Filled, Outlined, Text, Elevated, Tonal, FAB
带阴影、悬浮态、涟漪效果
"""

from PySide6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QRectF, QPointF, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush, QRadialGradient,
    QConicalGradient,
)

from assets.styles.material_colors import Colors
from assets.styles.animations import Easing, Duration


class MaterialButton(QPushButton):
    """
    Material Design 3 按钮

    类型:
    - filled: 实心填充按钮（主操作）
    - tonal: 容器色填充（次操作）
    - outlined: 描边按钮
    - text: 文字按钮
    - elevated: 带阴影的浅色按钮
    - fab: 浮动操作按钮
    """

    FILLED = "filled"
    TONAL = "tonal"
    OUTLINED = "outlined"
    TEXT = "text"
    ELEVATED = "elevated"
    FAB = "fab"

    def __init__(self, text: str = "", button_type: str = FILLED, parent=None):
        super().__init__(text, parent)
        self._button_type = button_type
        self._ripple_progress = 0.0
        self._ripple_center = QPointF()
        self._hover_progress = 0.0
        self._press_progress = 0.0

        self.setMinimumHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

        # 动画
        self._ripple_anim = QPropertyAnimation(self, b"ripple_progress")
        self._ripple_anim.setDuration(Duration.LONG1)
        self._ripple_anim.setEasingCurve(Easing.STANDARD)

        self._hover_anim = QPropertyAnimation(self, b"hover_progress")
        self._hover_anim.setDuration(Duration.SHORT3)
        self._hover_anim.setEasingCurve(Easing.STANDARD)

        self._press_anim = QPropertyAnimation(self, b"press_progress")
        self._press_anim.setDuration(Duration.SHORT2)
        self._press_anim.setEasingCurve(Easing.STANDARD)

        self._setup_elevation()
        self._apply_style()

    # ── 属性（用于动画） ──────────────────────────────

    def get_ripple_progress(self):
        return self._ripple_progress

    def set_ripple_progress(self, v):
        self._ripple_progress = v
        self.update()

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, v):
        self._hover_progress = v
        self.update()

    def get_press_progress(self):
        return self._press_progress

    def set_press_progress(self, v):
        self._press_progress = v
        self.update()

    # 注册 Qt 属性
    ripple_progress = Property(float, get_ripple_progress, set_ripple_progress)
    hover_progress = Property(float, get_hover_progress, set_hover_progress)
    press_progress = Property(float, get_press_progress, set_press_progress)

    # ── 阴影 ──────────────────────────────────────────

    def _setup_elevation(self):
        """设置 MD3 高度阴影"""
        if self._button_type in (self.FILLED, self.TONAL, self.FAB):
            # 类型 1 高度（按钮默认）
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(3)
            shadow.setXOffset(0)
            shadow.setYOffset(1)
            shadow.setColor(QColor(0, 0, 0, 30))
            self.setGraphicsEffect(shadow)
        elif self._button_type == self.ELEVATED:
            # 类型 2 高度（卡片/浮动按钮）
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(6)
            shadow.setXOffset(0)
            shadow.setYOffset(2)
            shadow.setColor(QColor(0, 0, 0, 40))
            self.setGraphicsEffect(shadow)

    # ── 样式 ──────────────────────────────────────────

    def _apply_style(self):
        """应用基础样式"""
        if self._button_type == self.FAB:
            self.setFixedSize(56, 56)
            self.setStyleSheet("border-radius: 16px;")
        else:
            self.setStyleSheet("border-radius: 20px; padding: 10px 24px;")

    # ── 绘制 ──────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = 20 if self._button_type != self.FAB else 16

        # 背景色
        bg_color = self._get_background_color()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bg_color))
        painter.drawRoundedRect(rect, radius, radius)

        # 状态层（悬浮/按下）
        if self._hover_progress > 0 or self._press_progress > 0:
            state_alpha = max(self._hover_progress * 8, self._press_progress * 12)
            state_layer = QColor(0, 0, 0, int(state_alpha))
            if self._button_type in (self.OUTLINED, self.TEXT):
                state_layer = QColor(self._get_text_color())
                state_layer.setAlphaF(max(self._hover_progress * 0.08, self._press_progress * 0.12))
            painter.setBrush(state_layer)
            painter.drawRoundedRect(rect, radius, radius)

        # 涟漪效果
        if self._ripple_progress > 0:
            self._draw_ripple(painter, rect, radius)

        # 描边（outlined 类型）
        if self._button_type == self.OUTLINED:
            pen = QPen(QColor(Colors.outline), 1)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, radius, radius)

        # 文字
        text_color = self._get_text_color()
        painter.setPen(QColor(text_color))
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

        painter.end()

    def _get_background_color(self) -> str:
        if self._button_type == self.FILLED:
            return Colors.primary
        elif self._button_type == self.TONAL:
            return Colors.secondary_container
        elif self._button_type == self.ELEVATED:
            return Colors.surface_container_low
        else:
            return "transparent"

    def _get_text_color(self) -> str:
        if self._button_type == self.FILLED:
            return Colors.on_primary
        elif self._button_type == self.TONAL:
            return Colors.on_secondary_container
        elif self._button_type == self.ELEVATED:
            return Colors.primary
        else:
            return Colors.primary

    def _draw_ripple(self, painter: QPainter, rect: QRectF, radius: float):
        """绘制涟漪"""
        max_radius = max(rect.width(), rect.height())
        current_radius = max_radius * self._ripple_progress
        alpha = int((1 - self._ripple_progress) * 60)

        gradient = QRadialGradient(self._ripple_center, current_radius)
        gradient.setColorAt(0, QColor(255, 255, 255, alpha))
        gradient.setColorAt(1, QColor(255, 255, 255, 0))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self._ripple_center, current_radius, current_radius)

    # ── 事件 ──────────────────────────────────────────

    def enterEvent(self, event):
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()

    def leaveEvent(self, event):
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        self._press_anim.setStartValue(self._press_progress)
        self._press_anim.setEndValue(0.0)
        self._press_anim.start()

    def mousePressEvent(self, event):
        self._ripple_center = event.pos()
        self._ripple_anim.setStartValue(0.0)
        self._ripple_anim.setEndValue(1.0)
        self._ripple_anim.start()

        self._press_anim.setStartValue(self._press_progress)
        self._press_anim.setEndValue(1.0)
        self._press_anim.start()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_anim.setStartValue(self._press_progress)
        self._press_anim.setEndValue(0.0)
        self._press_anim.start()
        super().mouseReleaseEvent(event)
