"""
Material Design 3 Snackbar / Toast
带滑入滑出动画，遵循 MD3 运动规范
"""

from PySide6.QtWidgets import QLabel, QGraphicsDropShadowEffect, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor

from assets.styles.material_colors import Colors
from assets.styles.animations import Easing, Duration


class MaterialToast(QLabel):
    """MD3 Snackbar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 3000
        self.setWordWrap(True)
        self.setMinimumHeight(48)
        self.setMaximumWidth(560)
        self.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.setIndent(16)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # 阴影（高度 3）
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(6)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)

        # 动画
        self._slide_in = QPropertyAnimation(self, b"pos")
        self._slide_in.setDuration(Duration.MEDIUM2)
        self._slide_in.setEasingCurve(Easing.DECELERATE)

        self._slide_out = QPropertyAnimation(self, b"pos")
        self._slide_out.setDuration(Duration.MEDIUM1)
        self._slide_out.setEasingCurve(Easing.ACCELERATE)
        self._slide_out.finished.connect(self.hide)

        self.setStyleSheet(f"""
            QLabel {{
                background: {Colors.inverse_surface};
                color: {Colors.inverse_on_surface};
                border-radius: 4px;
                font-size: 14px;
                font-family: 'Microsoft YaHei', sans-serif;
            }}
        """)

    def show_message(self, message: str, duration: int = 3000, msg_type: str = "info"):
        self._duration = duration
        self.setText(message)
        self.adjustSize()

        # 根据类型选用颜色
        colors = {
            "info": (Colors.inverse_surface, Colors.inverse_on_surface),
            "success": (Colors.primary_container, Colors.on_primary_container),
            "warning": (Colors.tertiary_container, Colors.on_tertiary_container),
            "error": (Colors.error_container, Colors.on_error_container),
        }
        bg, fg = colors.get(msg_type, colors["info"])
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border-radius: 4px;
                font-size: 14px;
                font-family: 'Microsoft YaHei', sans-serif;
            }}
        """)

        # 定位
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            x = (pw - self.width()) // 2
            start_y = ph + 10
            end_y = ph - self.height() - 24
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            x = (screen.width() - self.width()) // 2
            start_y = screen.height() + 10
            end_y = screen.height() - self.height() - 60

        self.move(x, start_y)
        self.show()
        self.raise_()

        # 滑入
        self._slide_in.setStartValue(QPoint(x, start_y))
        self._slide_in.setEndValue(QPoint(x, end_y))
        self._slide_in.start()

        # 定时滑出
        QTimer.singleShot(duration, self._start_slide_out)

    def _start_slide_out(self):
        if self.parent():
            ph = self.parent().height()
        else:
            ph = QApplication.primaryScreen().availableGeometry().height()
        x = self.x()
        self._slide_out.setStartValue(QPoint(x, self.y()))
        self._slide_out.setEndValue(QPoint(x, ph + 10))
        self._slide_out.start()


def show_toast(parent, message: str, duration: int = 3000, msg_type: str = "info"):
    """便捷函数"""
    toast = MaterialToast(parent)
    toast.show_message(message, duration, msg_type)
    return toast
