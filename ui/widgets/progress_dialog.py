"""
Material Design 3 进度对话框
带环形/线性进度指示器
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar,
    QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter

from assets.styles.material_colors import Colors
from assets.styles.animations import Easing, Duration


class MaterialCircularProgress(QWidget):
    """MD3 环形进度指示器（不确定进度）"""

    def __init__(self, size: int = 48, parent=None):
        super().__init__(parent)
        self._size = size
        self._angle = 0
        self.setFixedSize(size, size)

        self._timer = None
        self._anim = QPropertyAnimation(self, b"angle")
        self._anim.setDuration(1000)
        self._anim.setStartValue(0)
        self._anim.setEndValue(360)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def get_angle(self):
        return self._angle

    def set_angle(self, v):
        self._angle = v
        self.update()

    angle = property(get_angle, set_angle)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen_size = 4
        pen = QPen()
        pen.setWidth(pen_size)
        pen.setCapStyle(Qt.RoundCap)
        pen.setColor(QColor(Colors.primary))
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        rect = self.rect().adjusted(pen_size, pen_size, -pen_size, -pen_size)
        start_angle = -self._angle * 16
        span_angle = 270 * 16
        painter.drawArc(rect, start_angle, span_angle)

        painter.end()


class ProgressDialog(QDialog):
    """MD3 进度对话框"""

    cancelled = None  # 信号占位

    def __init__(self, title: str = "处理中", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(360, 180)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._is_cancelled = False
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {Colors.surface_container_high};
                border-radius: 28px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # 标题
        self._title = QLabel("正在处理...")
        self._title.setStyleSheet(f"""
            color: {Colors.on_surface};
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(self._title)

        # 信息
        self._info = QLabel("")
        self._info.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
        layout.addWidget(self._info)

        # 线性进度条
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: {Colors.surface_container_highest};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {Colors.primary};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self._progress)

        # 取消按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.primary};
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {Colors.primary_container};
            }}
        """)
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)
        layout.addLayout(btn_row)

    def set_title(self, text: str):
        self._title.setText(text)

    def set_info(self, text: str):
        self._info.setText(text)

    def set_progress(self, value: int):
        self._progress.setValue(value)

    def _on_cancel(self):
        self._is_cancelled = True
        self.reject()

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled
