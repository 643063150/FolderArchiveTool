"""
确认对话框 — Material Design 3 风格
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QPixmap
from assets.styles.material_colors import Colors


class ConfirmDialog(QDialog):
    """MD3 确认对话框"""

    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    SUCCESS = "success"

    def __init__(
        self,
        title: str = "确认",
        message: str = "",
        dialog_type: str = INFO,
        parent=None,
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        show_cancel: bool = True,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(440, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._dialog_type = dialog_type
        self._init_ui(title, message, confirm_text, cancel_text, show_cancel)

    def _init_ui(self, title, message, confirm_text, cancel_text, show_cancel):
        self.setStyleSheet(f"""
            QDialog {{
                background: {Colors.surface};
                border-radius: 24px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # 标题行（含图标）
        header = QHBoxLayout()
        header.setSpacing(10)
        icons = {
            self.INFO: "ℹ️",
            self.WARNING: "⚠️",
            self.DANGER: "🚫",
            self.SUCCESS: "✅",
        }
        icon_label = QLabel(icons.get(self._dialog_type, "ℹ️"))
        icon_label.setStyleSheet("font-size: 28px; background: transparent;")
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setStyleSheet(f"color: {Colors.on_surface}; background: transparent;")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        # 消息
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            color: {Colors.on_surface_variant};
            font-size: 14px;
            line-height: 1.5;
            background: transparent;
            padding-left: 38px;
        """)
        layout.addWidget(msg_label)

        layout.addStretch()

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        if show_cancel:
            btn_cancel = QPushButton(cancel_text)
            btn_cancel.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {Colors.on_surface_variant};
                    border: 1px solid {Colors.outline};
                    border-radius: 20px;
                    padding: 10px 24px;
                    font-size: 14px;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background: {Colors.surface_container};
                }}
            """)
            btn_cancel.clicked.connect(self.reject)
            btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton(confirm_text)
        confirm_colors = {
            self.INFO: Colors.primary,
            self.WARNING: "#FF9800",
            self.DANGER: "#F44336",
            self.SUCCESS: "#4CAF50",
        }
        bg = confirm_colors.get(self._dialog_type, Colors.primary)
        btn_confirm.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background: #1976D2;
            }}
        """)
        btn_confirm.clicked.connect(self.accept)
        btn_row.addWidget(btn_confirm)

        layout.addLayout(btn_row)


def show_confirm(
    parent,
    title: str,
    message: str,
    dialog_type: str = ConfirmDialog.INFO,
    confirm_text: str = "确认",
    cancel_text: str = "取消",
) -> bool:
    """便捷函数：显示 MD3 确认对话框，返回是否确认"""
    dialog = ConfirmDialog(
        title=title,
        message=message,
        dialog_type=dialog_type,
        parent=parent,
        confirm_text=confirm_text,
        cancel_text=cancel_text,
        show_cancel=True,
    )
    return dialog.exec() == QDialog.Accepted
