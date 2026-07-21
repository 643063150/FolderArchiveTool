"""
关于对话框 — Material Design 3 风格
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from assets.styles.material_colors import Colors


class AboutDialog(QDialog):
    """关于对话框 — MD3"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 FolderArchiveTool")
        self.setModal(True)
        self.setFixedSize(400, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {Colors.surface_container_low};
                border-radius: 24px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(10)

        # 图标
        icon = QLabel("📦")
        icon.setStyleSheet(f"font-size: 52px; background: transparent;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        # 应用名
        name = QLabel("FolderArchiveTool")
        name.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        name.setStyleSheet(f"color: {Colors.primary}; background: transparent;")
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)

        # 版本
        version = QLabel("v1.1")
        version.setStyleSheet(f"color: {Colors.primary}; font-size: 14px; font-weight: 600; background: transparent;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {Colors.outline_variant}; max-height: 1px; margin: 4px 20px;")
        layout.addWidget(sep)

        # 描述
        desc = QLabel(
            "月度文件压缩归档工具\n\n"
            "自动识别日期格式文件，按月打包压缩，\n"
            "CRC32 双重校验后安全删除原文件。\n"
            "支持多邮件服务器通知、定时任务、开机自启。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px; line-height: 1.6; background: transparent;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch()

        # 关闭按钮
        btn = QPushButton("关闭")
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.primary};
                color: {Colors.on_primary};
                border: none;
                border-radius: 20px;
                padding: 10px 40px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background: #1976D2; }}
        """)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
