"""
Material Design 3 动画引擎
基于 MD3 运动规范: https://m3.material.io/styles/motion/overview

缓动曲线（使用 PySide6 支持的内置类型）:
- Emphasized: InOutCubic（接近 MD3 cubic-bezier(0.2, 0, 0, 1)）
- Emphasized Decelerate: OutCubic（接近 MD3 cubic-bezier(0.05, 0.7, 0.1, 1)）
- Emphasized Accelerate: InCubic（接近 MD3 cubic-bezier(0.3, 0, 0.8, 0.15)）
- Standard: InOutQuad
- Linear: Linear

时长（MD3 规范）:
- Short1: 50ms, Short2: 100ms, Short3: 150ms, Short4: 200ms
- Medium1: 250ms, Medium2: 300ms, Medium3: 350ms, Medium4: 400ms
- Long1: 450ms, Long2: 500ms, Long3: 550ms, Long4: 600ms
"""

from PySide6.QtCore import (
    QEasingCurve, QPropertyAnimation, QParallelAnimationGroup,
    QSequentialAnimationGroup, QPoint, QRect, QSize,
)
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect


# ── 实际可用的缓动曲线（QPropertyAnimation 兼容）──────

class Easing:
    """MD3 动画缓动曲线（使用 PySide6 内置类型）"""
    # 接近 MD3 Emphasized: cubic-bezier(0.2, 0, 0, 1)
    EMPHASIZED = QEasingCurve(QEasingCurve.Type.InOutCubic)

    # 接近 MD3 Emphasized Decelerate: cubic-bezier(0.05, 0.7, 0.1, 1)
    DECELERATE = QEasingCurve(QEasingCurve.Type.OutCubic)

    # 接近 MD3 Emphasized Accelerate: cubic-bezier(0.3, 0, 0.8, 0.15)
    ACCELERATE = QEasingCurve(QEasingCurve.Type.InCubic)

    # 标准
    STANDARD = QEasingCurve(QEasingCurve.Type.InOutQuad)

    # 线性
    LINEAR = QEasingCurve(QEasingCurve.Type.Linear)

    # 弹性（用于涟漪等效果）
    SPRING = QEasingCurve(QEasingCurve.Type.OutBack)


# ── 动画时长 ──────────────────────────────────────────

class Duration:
    """MD3 动画时长"""
    SHORT1 = 50
    SHORT2 = 100
    SHORT3 = 150
    SHORT4 = 200
    MEDIUM1 = 250
    MEDIUM2 = 300
    MEDIUM3 = 350
    MEDIUM4 = 400
    LONG1 = 450
    LONG2 = 500
    LONG3 = 550
    LONG4 = 600


# ── 便捷动画函数 ──────────────────────────────────────

def fade_in(widget: QWidget, duration: int = Duration.MEDIUM2,
            easing=None) -> QPropertyAnimation:
    """淡入动画"""
    if easing is None:
        easing = Easing.EMPHASIZED
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


def fade_out(widget: QWidget, duration: int = Duration.MEDIUM1,
             easing=None) -> QPropertyAnimation:
    """淡出动画"""
    if easing is None:
        easing = Easing.ACCELERATE
    effect = widget.graphicsEffect()
    if not effect:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.setEasingCurve(easing)
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


def scale_in(widget: QWidget, duration: int = Duration.MEDIUM1,
             easing=None) -> QPropertyAnimation:
    """缩放进入动画"""
    if easing is None:
        easing = Easing.DECELERATE
    anim = QPropertyAnimation(widget, b"geometry")
    anim.setDuration(duration)
    anim.setEasingCurve(easing)

    rect = widget.geometry()
    center = rect.center()
    start_rect = QRect(0, 0, 0, 0)
    start_rect.moveCenter(center)

    anim.setStartValue(start_rect)
    anim.setEndValue(rect)
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


# ── 页面切换动画 ──────────────────────────────────────

def page_transition(new_widget: QWidget, old_widget: QWidget = None,
                    duration: int = Duration.MEDIUM2):
    """页面切换动画：新页面淡入 + 轻微上移"""
    group = QParallelAnimationGroup()
    fade_in_anim = fade_in(new_widget, duration)
    group.addAnimation(fade_in_anim)
    if old_widget:
        fade_out_anim = fade_out(old_widget, duration // 2)
        group.addAnimation(fade_out_anim)
    group.start(QPropertyAnimation.DeleteWhenStopped)
    return group
