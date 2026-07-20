"""
关于对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 FolderArchiveTool")
        self.setModal(True)
        self.setFixedSize(400, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(12)

        # 图标
        icon = QLabel("📦")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        # 应用名
        name = QLabel("FolderArchiveTool")
        name.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        name.setStyleSheet("color: #1976D2;")
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)

        # 版本
        version = QLabel("版本 1.0.0")
        version.setStyleSheet("color: #616161; font-size: 13px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # 描述
        desc = QLabel(
            "月度文件压缩归档工具\n\n"
            "自动识别日期格式文件，按月打包压缩，\n"
            "CRC 校验后安全删除原文件。\n"
            "支持多邮件服务器通知、定时任务、开机自启。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #424242; font-size: 13px; line-height: 1.6;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch()

        # 关闭按钮
        btn = QPushButton("关闭")
        btn.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
            }
            QPushButton:hover { background: #1565C0; }
        """)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
