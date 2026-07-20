"""
Material Design 3 卡片控件
支持: Elevated, Filled, Outlined
带高度阴影和状态层
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter

from assets.styles.material_colors import Colors
from assets.styles.animations import Easing, Duration


class MaterialCard(QFrame):
    """Material Design 3 卡片"""

    ELEVATED = "elevated"    # 带阴影
    FILLED = "filled"        # 填充色
    OUTLINED = "outlined"    # 带边框

    def __init__(self, card_type: str = ELEVATED, parent=None):
        super().__init__(parent)
        self._card_type = card_type
        self._hover_progress = 0.0
        self._elevation_level = 1 if card_type == self.ELEVATED else 0

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(12)

        self._setup_elevation()
        self._setup_animation()
        self._apply_style()

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout

    def add_widget(self, widget):
        self._layout.addWidget(widget)

    def add_layout(self, layout):
        self._layout.addLayout(layout)

    def add_stretch(self, stretch: int = 1):
        self._layout.addStretch(stretch)

    # ── 高度 ──────────────────────────────────────────

    def _setup_elevation(self):
        """MD3 高度阴影系统"""
        if self._elevation_level == 0:
            return
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(3 + self._elevation_level * 3)
        shadow.setXOffset(0)
        shadow.setYOffset(self._elevation_level)
        shadow.setColor(QColor(0, 0, 0, 20 + self._elevation_level * 10))
        self.setGraphicsEffect(shadow)

    def _setup_animation(self):
        self._hover_anim = QPropertyAnimation(self, b"hover_progress")
        self._hover_anim.setDuration(Duration.SHORT3)
        self._hover_anim.setEasingCurve(Easing.STANDARD)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, v):
        self._hover_progress = v
        # 悬浮时增加阴影
        if self.graphicsEffect():
            blur = 3 + int(v * 4)
            self.graphicsEffect().setBlurRadius(blur)

    hover_progress = Property(float, get_hover_progress, set_hover_progress)

    def _apply_style(self):
        if self._card_type == self.ELEVATED:
            self.setStyleSheet(f"""
                MaterialCard {{
                    background: {Colors.surface_container_low};
                    border: none;
                    border-radius: 12px;
                }}
            """)
        elif self._card_type == self.FILLED:
            self.setStyleSheet(f"""
                MaterialCard {{
                    background: {Colors.surface_container_highest};
                    border: none;
                    border-radius: 12px;
                }}
            """)
        else:  # OUTLINED
            self.setStyleSheet(f"""
                MaterialCard {{
                    background: {Colors.surface};
                    border: 1px solid {Colors.outline_variant};
                    border-radius: 12px;
                }}
            """)

    def enterEvent(self, event):
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()

    def leaveEvent(self, event):
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
