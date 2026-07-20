"""
Material Design 3 文本输入框
Outlined 和 Filled 两种样式
带浮动标签效果
"""

from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget, QLabel, QApplication
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QFont

from assets.styles.material_colors import Colors
from assets.styles.animations import Easing, Duration


class MaterialTextField(QWidget):
    """
    MD3 文本输入框（Outlined 样式）
    带浮动标签动画
    """

    def __init__(self, label: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        self._label_text = label
        self._placeholder = placeholder
        self._focused = False

        self._init_ui()
        self._setup_animations()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 浮动标签
        self._label = QLabel(self._label_text, self)
        self._label.setStyleSheet(f"""
            color: {Colors.on_surface_variant};
            font-size: 12px;
            padding: 0 4px;
            background: {Colors.surface};
        """)
        self._label.setFixedHeight(16)
        self._label.move(12, -8)
        layout.addWidget(self._label, alignment=Qt.AlignTop)

        # 输入框
        self._input = QLineEdit(self)
        self._input.setPlaceholderText(self._placeholder)
        self._input.setMinimumHeight(56)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: 1px solid {Colors.outline};
                border-radius: 4px;
                padding: 16px 16px 8px 16px;
                font-size: 16px;
                color: {Colors.on_surface};
            }}
            QLineEdit:focus {{
                border: 2px solid {Colors.primary};
                padding: 15px 15px 7px 15px;
            }}
        """)
        self._input.focusInEvent = lambda e: self._on_focus_in(e)
        self._input.focusOutEvent = lambda e: self._on_focus_out(e)
        layout.addWidget(self._input)

    def _setup_animations(self):
        self._label_anim = QPropertyAnimation(self._label, b"pos")
        self._label_anim.setDuration(Duration.SHORT4)
        self._label_anim.setEasingCurve(Easing.STANDARD)

    def _on_focus_in(self, event):
        self._focused = True
        self._animate_label(up=True)
        QLineEdit.focusInEvent(self._input, event)

    def _on_focus_out(self, event):
        self._focused = False
        if not self._input.text():
            self._animate_label(up=False)
        QLineEdit.focusOutEvent(self._input, event)

    def _animate_label(self, up: bool):
        if up:
            self._label_anim.setEndValue(QPoint(12, -8))
            self._label.setStyleSheet(f"""
                color: {Colors.primary};
                font-size: 12px;
                padding: 0 4px;
                background: {Colors.surface};
            """)
        else:
            self._label_anim.setEndValue(QPoint(16, 18))
            self._label.setStyleSheet(f"""
                color: {Colors.on_surface_variant};
                font-size: 16px;
                padding: 0 4px;
                background: {Colors.surface};
            """)
        self._label_anim.start()

    def text(self) -> str:
        return self._input.text()

    def setText(self, text: str):
        self._input.setText(text)

    def clear(self):
        self._input.clear()


class MaterialLineEdit(QLineEdit):
    """简化版 MD3 输入框（带边框效果）"""

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(40)
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {Colors.surface_container_highest};
                border: 1px solid {Colors.outline};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: {Colors.on_surface};
                selection-background-color: {Colors.primary_container};
            }}
            QLineEdit:focus {{
                border: 2px solid {Colors.primary};
            }}
            QLineEdit:hover {{
                border-color: {Colors.on_surface_variant};
            }}
        """)
