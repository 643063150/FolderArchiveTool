"""
确认对话框
Material Design 风格的确认/警告/危险对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QPixmap


class ConfirmDialog(QDialog):
    """Material Design 确认对话框"""

    # 对话框类型
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
        self.setFixedSize(420, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._dialog_type = dialog_type
        self._init_ui(title, message, confirm_text, cancel_text, show_cancel)

    def _init_ui(self, title, message, confirm_text, cancel_text, show_cancel):
        self.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # 图标 + 标题
        header = QHBoxLayout()
        icon_label = QLabel()
        icons = {
            self.INFO: "ℹ️",
            self.WARNING: "⚠️",
            self.DANGER: "🚫",
            self.SUCCESS: "✅",
        }
        icon_label.setText(icons.get(self._dialog_type, "ℹ️"))
        icon_label.setStyleSheet("font-size: 32px;")
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setStyleSheet("color: #212121;")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        # 消息
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #616161; font-size: 14px; line-height: 1.5;")
        layout.addWidget(msg_label)

        layout.addStretch()

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if show_cancel:
            btn_cancel = QPushButton(cancel_text)
            btn_cancel.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #616161;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background: #F5F5F5;
                }
            """)
            btn_cancel.clicked.connect(self.reject)
            btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton(confirm_text)
        colors = {
            self.INFO: "#1976D2",
            self.WARNING: "#FF9800",
            self.DANGER: "#F44336",
            self.SUCCESS: "#4CAF50",
        }
        bg = colors.get(self._dialog_type, "#1976D2")
        btn_confirm.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 500;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
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
    """便捷函数：显示确认对话框，返回是否确认"""
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
