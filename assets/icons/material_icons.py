"""
Material Design Icons 矢量图标系统
使用 SVG path 数据绘制，支持任意缩放、着色
数据来源: Material Symbols (Apache 2.0 License)
"""

from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QSize, QByteArray, QPointF, QRectF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QPixmap,
    QIcon, QIconEngine,
)


# ── Material Symbols SVG Path 数据 ─────────────────────
# 每个图标对应 24x24 viewBox 的标准 SVG path

ICON_PATHS = {
    # 导航图标
    "archive": "M5 21V8.7c0-.5.1-.9.4-1.3.3-.4.7-.7 1.1-.9l6-2.7c.3-.1.7-.1 1 0l6 2.7c.4.2.8.5 1.1.9.3.4.4.8.4 1.3V21M5 21h14M5 21H3m16 0h2M9 21v-4h6v4m-6-8h.01M15 13h.01",
    "mail": "M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v.01L12 13l8-7V6H4z",
    "schedule": "M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z",
    "settings": "M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.488.488 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 00-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z",
    "description": "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
    "folder": "M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z",

    # 操作图标
    "search": "M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z",
    "delete": "M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z",
    "play_arrow": "M8 5v14l11-7z",
    "pause": "M6 19h4V5H6v14zm8-14v14h4V5h-4z",
    "add": "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z",
    "close": "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    "check": "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
    "edit": "M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z",
    "refresh": "M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
    "send": "M2.01 21L23 12 2.01 3 2 10l15 2-15 2z",
    "save": "M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z",
    "upload": "M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z",
    "download": "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
    "visibility": "M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z",
    "more_vert": "M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z",

    # 状态图标
    "info": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z",
    "warning": "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
    "error_icon": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z",
    "success": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",

    # 界面图标
    "chevron_right": "M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z",
    "chevron_left": "M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z",
    "expand_more": "M16.59 8.59L12 13.17 7.41 8.59 6 10l6 6 6-6z",
    "expand_less": "M12 8l-6 6 1.41 1.41L12 10.83l4.59 4.58L18 14z",
    "menu": "M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z",
    "home": "M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z",
}


def create_svg_icon(name: str, size: int = 24, color: str = "#000000") -> str:
    """
    生成 SVG 字符串

    Args:
        name: 图标名称（对应 ICON_PATHS 的 key）
        size: 图标尺寸
        color: 图标颜色

    Returns:
        SVG 字符串
    """
    path_data = ICON_PATHS.get(name, ICON_PATHS["info"])
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}"
     viewBox="0 0 24 24" fill="{color}">
    <path d="{path_data}"/>
</svg>'''


def create_icon_pixmap(name: str, size: int = 24, color: str = "#000000") -> QPixmap:
    """创建图标 QPixmap"""
    svg_str = create_svg_icon(name, size, color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


class MaterialIcon(QLabel):
    """
    Material Design 图标控件
    支持运行时变色、缩放
    """

    def __init__(self, name: str = "info", size: int = 24, color: str = "#000000", parent=None):
        super().__init__(parent)
        self._icon_name = name
        self._icon_size = size
        self._color = color
        self.setFixedSize(size, size)
        self.setScaledContents(False)
        self._render()

    def _render(self):
        """渲染图标"""
        pixmap = create_icon_pixmap(self._icon_name, self._icon_size, self._color)
        self.setPixmap(pixmap)

    def set_color(self, color: str):
        """设置图标颜色"""
        self._color = color
        self._render()

    def set_icon(self, name: str):
        """设置图标"""
        self._icon_name = name
        self._render()

    def set_size(self, size: int):
        """设置图标大小"""
        self._icon_size = size
        self.setFixedSize(size, size)
        self._render()


class IconButton(QWidget):
    """
    图标按钮 - 带涟漪效果
    """

    clicked = None  # 将在下方定义信号

    def __init__(self, icon_name: str = "menu", size: int = 24,
                 color: str = "#000000", parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._icon_size = size
        self._color = color
        self._hovered = False
        self._pressed = False
        self._ripple_radius = 0

        self.setFixedSize(48, 48)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPainterPath, QBrush, QColor, QPen, QRadialGradient

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景（悬浮态）
        if self._hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 20))
            painter.drawEllipse(self.rect())

        # 图标居中
        cx = self.width() // 2
        cy = self.height() // 2
        icon_size = self._icon_size

        svg_str = create_svg_icon(self._icon_name, icon_size, self._color)
        renderer = QSvgRenderer(QByteArray(svg_str.encode()))
        x = cx - icon_size // 2
        y = cy - icon_size // 2
        renderer.render(painter, QRectF(x, y, icon_size, icon_size))

        painter.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self._pressed = False
        self.update()

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        if self.rect().contains(event.pos()):
            if hasattr(self, '_clicked_callback') and self._clicked_callback:
                self._clicked_callback()


def get_icon_pixmap(name: str, size: int = 24, color: str = "#000000") -> QPixmap:
    """便捷函数：获取图标"""
    return create_icon_pixmap(name, size, color)
