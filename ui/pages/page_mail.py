"""
邮件配置页面 — Material Design 3 精修版
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QAbstractItemView, QTextEdit, QLabel, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, CheckBox, SwitchButton,
    BodyLabel, StrongBodyLabel, SubtitleLabel,
)

from core.config_manager import ConfigManager
from core.mail_sender import MailSender
from assets.styles.material_colors import Colors


# ── 工具函数 ──────────────────────────────────────────

def _make_card_shadow(widget, blur=16, offset=2):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(offset)
    shadow.setColor(QColor(0, 0, 0, 18))
    widget.setGraphicsEffect(shadow)


# ── 对话框 ────────────────────────────────────────────

class ServerEditDialog(QDialog):
    def __init__(self, server_config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("邮件服务器配置")
        self.setMinimumWidth(480)
        self._config = server_config or {}
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {Colors.surface_container_low};
                border-radius: 20px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("📧 服务器设置")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.on_surface};")
        layout.addWidget(title)

        # 表单
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._name = QLineEdit(self._config.get("name", ""))
        self._name.setPlaceholderText("如：腾讯企业邮")
        self._name.setStyleSheet(_INPUT_STYLE)
        form.addRow("名称", self._name)

        self._host = QLineEdit(self._config.get("smtp_host", ""))
        self._host.setPlaceholderText("如：smtp.exmail.qq.com")
        self._host.setStyleSheet(_INPUT_STYLE)
        form.addRow("SMTP 地址", self._host)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(self._config.get("smtp_port", 25))
        self._port.setFixedWidth(120)
        self._port.setStyleSheet(_SPIN_STYLE)
        form.addRow("端口", self._port)

        self._ssl = CheckBox("使用 SSL", self)
        self._ssl.setChecked(self._config.get("use_ssl", False))
        form.addRow("", self._ssl)

        self._tls = CheckBox("使用 TLS", self)
        self._tls.setChecked(self._config.get("use_tls", False))
        form.addRow("", self._tls)

        self._username = QLineEdit(self._config.get("username", ""))
        self._username.setPlaceholderText("邮箱账号")
        self._username.setStyleSheet(_INPUT_STYLE)
        form.addRow("用户名", self._username)

        self._password = QLineEdit(self._config.get("password", ""))
        self._password.setEchoMode(QLineEdit.Password)
        self._password.setPlaceholderText("密码 / 授权码")
        self._password.setStyleSheet(_INPUT_STYLE)
        form.addRow("密码", self._password)

        self._from_addr = QLineEdit(self._config.get("from_addr", ""))
        self._from_addr.setPlaceholderText("发件人地址")
        self._from_addr.setStyleSheet(_INPUT_STYLE)
        form.addRow("发件人", self._from_addr)

        self._sender_name = QLineEdit(self._config.get("sender_name", ""))
        self._sender_name.setPlaceholderText("如：归档系统通知")
        self._sender_name.setStyleSheet(_INPUT_STYLE)
        form.addRow("发件人名称", self._sender_name)

        self._is_primary = CheckBox("设为主服务器", self)
        self._is_primary.setChecked(self._config.get("is_primary", False))
        form.addRow("", self._is_primary)

        layout.addLayout(form)
        layout.addSpacing(8)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = OutlinedPushButton("取消", self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_ok = FilledPushButton("保存", self)
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def get_config(self):
        return {
            "name": self._name.text().strip(),
            "smtp_host": self._host.text().strip(),
            "smtp_port": self._port.value(),
            "use_ssl": self._ssl.isChecked(),
            "use_tls": self._tls.isChecked(),
            "username": self._username.text().strip(),
            "password": self._password.text(),
            "from_addr": self._from_addr.text().strip(),
            "sender_name": self._sender_name.text().strip(),
            "is_primary": self._is_primary.isChecked(),
            "enabled": True,
        }


# ── 样式常量 ──────────────────────────────────────────

_INPUT_STYLE = f"""
    QLineEdit {{
        background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
        border-radius: 8px; padding: 10px 14px; font-size: 14px;
        color: {Colors.on_surface};
    }}
    QLineEdit:focus {{ border: 2px solid {Colors.primary}; background: {Colors.surface_bright}; padding: 9px 13px; }}
    QLineEdit::placeholder {{ color: {Colors.outline}; }}
"""

_SPIN_STYLE = f"""
    QSpinBox {{
        background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
        border-radius: 8px; padding: 10px 14px; font-size: 14px;
        color: {Colors.on_surface};
    }}
    QSpinBox:focus {{ border: 2px solid {Colors.primary}; }}
"""


# ── 工作线程 ──────────────────────────────────────────

class MailTestWorker(QThread):
    finished_with_result = Signal(dict)

    def __init__(self, mail_sender, server_config):
        super().__init__()
        self._sender = mail_sender
        self._config = server_config

    def run(self):
        result = self._sender.test_connection(self._config)
        self.finished_with_result.emit(result)


class MailSendWorker(QThread):
    finished_with_result = Signal(dict)

    def __init__(self, mail_sender, subject, body):
        super().__init__()
        self._sender = mail_sender
        self._subject = subject
        self._body = body

    def run(self):
        result = self._sender.send_notification(self._subject, self._body)
        self.finished_with_result.emit(result)


# ── 主页面 ────────────────────────────────────────────

class PageMail(QWidget):
    def __init__(self, config, service, scheduler, parent=None):
        super().__init__(parent)
        self._config = config
        self._mail = MailSender(config)
        self._test_worker = None
        self._send_worker = None
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ═══ 页面标题 ═══════════════════════════════════
        header = QHBoxLayout()
        title = SubtitleLabel("邮件配置")
        title.setStyleSheet(f"""
            font-size: 24px; font-weight: 700;
            color: {Colors.on_surface};
        """)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        desc = BodyLabel("支持多邮件服务器（第三方 + 自建），可同时发送或主备切换")
        desc.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
        layout.addWidget(desc)

        # ═══ 启用与模式 ═════════════════════════════════
        enable_card = OutlinedCardWidget(self)
        _make_card_shadow(enable_card)
        enable_layout = QHBoxLayout(enable_card)
        enable_layout.setContentsMargins(24, 16, 24, 16)

        self._chk_enable = CheckBox("启用邮件通知", self)
        enable_layout.addWidget(self._chk_enable)
        enable_layout.addSpacing(24)
        enable_layout.addWidget(BodyLabel("发送模式：", self))
        self._combo_mode = QComboBox()
        self._combo_mode.addItems(["🌐 全部发送", "🔄 主备切换"])
        self._combo_mode.setFixedWidth(150)
        self._combo_mode.setStyleSheet(f"""
            QComboBox {{
                background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
                border-radius: 8px; padding: 8px 14px; min-height: 20px;
            }}
            QComboBox:focus {{ border: 2px solid {Colors.primary}; }}
        """)
        enable_layout.addWidget(self._combo_mode)
        enable_layout.addStretch()
        layout.addWidget(enable_card)

        # ═══ 服务器列表卡片 ═════════════════════════════
        server_card = OutlinedCardWidget(self)
        _make_card_shadow(server_card)
        server_layout = QVBoxLayout(server_card)
        server_layout.setContentsMargins(24, 20, 24, 20)
        server_layout.setSpacing(12)

        server_header = QHBoxLayout()
        server_icon = BodyLabel("📡")
        server_icon.setStyleSheet("font-size: 18px;")
        server_header.addWidget(server_icon)
        server_header.addSpacing(6)
        server_title = BodyLabel("服务器列表")
        server_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.on_surface};")
        server_header.addWidget(server_title)
        server_header.addStretch()
        server_layout.addLayout(server_header)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["名称", "SMTP 地址", "端口", "主服务器", "启用"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(150)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {Colors.surface};
                border: 1px solid {Colors.outline_variant};
                border-radius: 12px;
            }}
            QTableWidget::item {{
                padding: 10px 16px;
                border-bottom: 1px solid {Colors.surface_container};
            }}
            QHeaderView::section {{
                background: {Colors.surface_container};
                border: none;
                border-bottom: 2px solid {Colors.outline_variant};
                padding: 10px 16px;
                font-weight: 600; font-size: 12px;
                color: {Colors.on_surface_variant};
            }}
        """)
        server_layout.addWidget(self._table)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_add = TonalPushButton("＋ 添加", self)
        btn_add.clicked.connect(self._on_add_server)
        btn_row.addWidget(btn_add)
        btn_edit = TonalPushButton("✎ 编辑", self)
        btn_edit.clicked.connect(self._on_edit_server)
        btn_row.addWidget(btn_edit)
        btn_del = TonalPushButton("🗑 删除", self)
        btn_del.clicked.connect(self._on_delete_server)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        server_layout.addLayout(btn_row)
        layout.addWidget(server_card)

        # ═══ 收件人 ═════════════════════════════════════
        recv_card = OutlinedCardWidget(self)
        _make_card_shadow(recv_card)
        recv_layout = QHBoxLayout(recv_card)
        recv_layout.setContentsMargins(24, 16, 24, 16)
        recv_icon = BodyLabel("📨")
        recv_icon.setStyleSheet("font-size: 18px;")
        recv_layout.addWidget(recv_icon)
        recv_layout.addSpacing(8)
        recv_layout.addWidget(BodyLabel("收件人：", self))
        self._input_recipients = QLineEdit()
        self._input_recipients.setPlaceholderText("多个收件人用逗号分隔")
        self._input_recipients.setStyleSheet(_INPUT_STYLE)
        recv_layout.addWidget(self._input_recipients, 1)
        layout.addWidget(recv_card)

        # ═══ 通知选项 ═══════════════════════════════════
        notify_card = OutlinedCardWidget(self)
        _make_card_shadow(notify_card)
        notify_layout = QHBoxLayout(notify_card)
        notify_layout.setContentsMargins(24, 16, 24, 16)
        notify_icon = BodyLabel("🔔")
        notify_icon.setStyleSheet("font-size: 18px;")
        notify_layout.addWidget(notify_icon)
        notify_layout.addSpacing(8)
        self._chk_notify_success = CheckBox("归档成功时通知", self)
        notify_layout.addWidget(self._chk_notify_success)
        notify_layout.addSpacing(16)
        self._chk_notify_failure = CheckBox("归档失败时通知", self)
        notify_layout.addWidget(self._chk_notify_failure)
        notify_layout.addStretch()
        layout.addWidget(notify_card)

        # ═══ 操作按钮 ═══════════════════════════════════
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        self._btn_test = OutlinedPushButton("🔌 测试连接", self)
        self._btn_test.clicked.connect(self._on_test_mail)
        action_row.addWidget(self._btn_test)

        self._btn_send = FilledPushButton("✉️ 发送测试邮件", self)
        self._btn_send.clicked.connect(self._on_send_test_mail)
        action_row.addWidget(self._btn_send)

        self._btn_save = FilledPushButton("💾 保存配置", self)
        self._btn_save.clicked.connect(self._on_save)
        action_row.addWidget(self._btn_save)

        action_row.addStretch()

        self._status_label = BodyLabel("")
        self._status_label.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
        action_row.addWidget(self._status_label)

        layout.addLayout(action_row)
        layout.addStretch()

    def _load_config(self):
        self._chk_enable.setChecked(self._config.get("mail.enabled", False))
        send_mode = self._config.get("mail.send_mode", "all")
        self._combo_mode.setCurrentIndex(0 if send_mode == "all" else 1)
        recipients = self._config.get("mail.recipients", [])
        self._input_recipients.setText(", ".join(recipients) if isinstance(recipients, list) else str(recipients))
        self._chk_notify_success.setChecked(self._config.get("mail.notify_on_success", True))
        self._chk_notify_failure.setChecked(self._config.get("mail.notify_on_failure", True))
        self._refresh_table()

    def _refresh_table(self):
        servers = self._config.get("mail.servers", [])
        self._table.setRowCount(0)
        for server in servers:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(server.get("name", "")))
            self._table.setItem(row, 1, QTableWidgetItem(server.get("smtp_host", "")))
            self._table.setItem(row, 2, QTableWidgetItem(str(server.get("smtp_port", ""))))
            self._table.setItem(row, 3, QTableWidgetItem("⭐" if server.get("is_primary") else ""))
            self._table.setItem(row, 4, QTableWidgetItem("✅" if server.get("enabled", True) else ""))

    def _on_add_server(self):
        dialog = ServerEditDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            servers = self._config.get("mail.servers", [])
            servers.append(dialog.get_config())
            self._config.set("mail.servers", servers)
            self._refresh_table()
            self._status_label.setText("✅ 已添加服务器")

    def _on_edit_server(self):
        row = self._table.currentRow()
        if row < 0:
            return
        servers = self._config.get("mail.servers", [])
        if row >= len(servers):
            return
        dialog = ServerEditDialog(servers[row], parent=self)
        if dialog.exec() == QDialog.Accepted:
            servers[row] = dialog.get_config()
            self._config.set("mail.servers", servers)
            self._refresh_table()
            self._status_label.setText("✅ 已更新服务器")

    def _on_delete_server(self):
        row = self._table.currentRow()
        if row < 0:
            return
        servers = self._config.get("mail.servers", [])
        if row < len(servers):
            reply = QMessageBox.question(self, "确认删除", f"确定删除服务器「{servers[row].get('name', '')}」？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                servers.pop(row)
                self._config.set("mail.servers", servers)
                self._refresh_table()
                self._status_label.setText("✅ 已删除服务器")

    def _on_test_mail(self):
        row = self._table.currentRow()
        servers = self._config.get("mail.servers", [])
        if row < 0 or row >= len(servers):
            QMessageBox.warning(self, "提示", "请先选择一个服务器")
            return
        self._status_label.setText("🔌 正在测试连接...")
        self._btn_test.setEnabled(False)
        self._test_worker = MailTestWorker(self._mail, servers[row])
        self._test_worker.finished_with_result.connect(self._on_test_finished)
        self._test_worker.start()

    def _on_test_finished(self, result):
        self._btn_test.setEnabled(True)
        if result["success"]:
            self._status_label.setText("✅ 连接测试通过")
        else:
            self._status_label.setText(f"❌ 失败：{result['error']}")

    def _on_send_test_mail(self):
        recipients = [r.strip() for r in self._input_recipients.text().split(",") if r.strip()]
        self._config.set("mail.enabled", True)
        self._config.set("mail.send_mode", "all" if self._combo_mode.currentIndex() == 0 else "primary")
        self._config.set("mail.recipients", recipients)
        self._config.set("mail.notify_on_success", self._chk_notify_success.isChecked())
        self._config.set("mail.notify_on_failure", self._chk_notify_failure.isChecked())
        self._config.save()

        servers = self._config.get("mail.servers", [])
        if not servers:
            QMessageBox.warning(self, "提示", "请先添加邮件服务器")
            return
        if not recipients:
            QMessageBox.warning(self, "提示", "请先填写收件人地址")
            return

        self._status_label.setText("✉️ 正在发送测试邮件...")
        self._btn_send.setEnabled(False)
        subject = "FolderArchiveTool 测试邮件"
        body = """<html><body style="font-family: 'Microsoft YaHei', Arial, sans-serif; color: #333;">
            <h2 style="color: #1976D2;">FolderArchiveTool</h2>
            <p>这是一封测试邮件。如果您收到此邮件，说明配置正确！</p>
            <hr style="border: none; border-top: 1px solid #eee;">
            <p style="color: #999; font-size: 12px;">此邮件由 FolderArchiveTool 自动发送</p>
        </body></html>"""
        self._send_worker = MailSendWorker(self._mail, subject, body)
        self._send_worker.finished_with_result.connect(self._on_send_finished)
        self._send_worker.start()

    def _on_send_finished(self, result):
        self._btn_send.setEnabled(True)
        if result.get("success"):
            self._status_label.setText("✅ 测试邮件已发送")
        else:
            failed_str = "; ".join(f"{s}: {e}" for s, e in result.get("failed", []))
            self._status_label.setText(f"❌ 发送失败：{failed_str}")

    def _on_save(self):
        self._config.set("mail.enabled", self._chk_enable.isChecked())
        self._config.set("mail.send_mode", "all" if self._combo_mode.currentIndex() == 0 else "primary")
        recipients = [r.strip() for r in self._input_recipients.text().split(",") if r.strip()]
        self._config.set("mail.recipients", recipients)
        self._config.set("mail.notify_on_success", self._chk_notify_success.isChecked())
        self._config.set("mail.notify_on_failure", self._chk_notify_failure.isChecked())
        self._config.save()
        self._status_label.setText("💾 已保存")
