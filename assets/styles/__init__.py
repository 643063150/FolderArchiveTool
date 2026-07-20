"""
样式模块
提供加载 QSS 样式表和 Material 配色的工具函数
"""

import os
from pathlib import Path


def load_stylesheet(filename: str = "main.qss") -> str:
    """
    加载 QSS 样式表文件

    Args:
        filename: 样式表文件名

    Returns:
        QSS 内容字符串，加载失败返回空字符串
    """
    # 支持多种路径查找
    search_paths = [
        Path(__file__).parent / filename,
        Path("assets/styles") / filename,
        Path("../assets/styles") / filename,
    ]

    # PyInstaller 打包后资源在 sys._MEIPASS
    if hasattr(__import__("sys"), "_MEIPASS"):
        search_paths.insert(0, Path(__import__("sys")._MEIPASS) / "assets" / "styles" / filename)

    for path in search_paths:
        if path.exists():
            return path.read_text(encoding="utf-8")

    return ""


def get_theme_css(**overrides) -> str:
    """
    动态生成主题 CSS（可用于运行时主题切换）

    Args:
        **overrides: 覆盖默认颜色值
    """
    from .material_colors import Colors

    colors = {
        "primary": Colors.primary,
        "on_primary": Colors.on_primary,
        "primary_container": Colors.primary_container,
        "secondary": Colors.secondary,
        "error": Colors.error,
        "background": Colors.background,
        "surface": Colors.surface,
        "on_surface": Colors.on_surface,
        "outline": Colors.outline,
    }
    colors.update(overrides)

    return f"""
    QWidget {{
        background: {colors['background']};
        color: {colors['on_surface']};
    }}
    QPushButton {{
        background: {colors['primary']};
        color: {colors['on_primary']};
    }}
    """
