"""
邮件配置页面 - Material Design 3 风格
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QAbstractItemView, QTextEdit, QLabel,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, CheckBox, SwitchButton,
    BodyLabel, StrongBodyLabel, SubtitleLabel,
)

from core.config_manager import ConfigManager
from core.mail_sender import MailSender


class MailTestWorker(QThread):
    finished_with_result = Signal(dict)

    def __init__(self, mail_sender, server_config):
        super().__init__()
        self._sender = mail_sender
        self._config = server_config

    def run(self):
        result = self._sender.test_connection(self._config)
        self.finished_with_result.emit(result)


class ServerEditDialog(QDialog):
    def __init__(self, server_config=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("邮件服务器配置")
        self.setMinimumWidth(420)
        self._config = server_config or {}
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        self._name = QLineEdit(self._config.get("name", ""))
        self._name.setPlaceholderText("服务器名称")
        layout.addRow("名称：", self._name)
        self._host = QLineEdit(self._config.get("smtp_host", ""))
        self._host.setPlaceholderText("如：smtp.company.com")
        layout.addRow("SMTP 地址：", self._host)
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(self._config.get("smtp_port", 25))
        layout.addRow("端口：", self._port)
        self._ssl = CheckBox("使用 SSL", self)
        self._ssl.setChecked(self._config.get("use_ssl", False))
        layout.addRow("", self._ssl)
        self._tls = CheckBox("使用 TLS", self)
        self._tls.setChecked(self._config.get("use_tls", False))
        layout.addRow("", self._tls)
        self._username = QLineEdit(self._config.get("username", ""))
        self._username.setPlaceholderText("邮箱账号")
        layout.addRow("用户名：", self._username)
        self._password = QLineEdit(self._config.get("password", ""))
        self._password.setEchoMode(QLineEdit.Password)
        self._password.setPlaceholderText("密码/授权码")
        layout.addRow("密码：", self._password)
        self._from_addr = QLineEdit(self._config.get("from_addr", ""))
        self._from_addr.setPlaceholderText("发件人地址")
        layout.addRow("发件人：", self._from_addr)
        self._is_primary = CheckBox("设为主服务器", self)
        self._is_primary.setChecked(self._config.get("is_primary", False))
        layout.addRow("", self._is_primary)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

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
            "is_primary": self._is_primary.isChecked(),
            "enabled": True,
        }


class MailSendWorker(QThread):
    """邮件发送工作线程"""
    finished_with_result = Signal(dict)

    def __init__(self, mail_sender, subject, body):
        super().__init__()
        self._sender = mail_sender
        self._subject = subject
        self._body = body

    def run(self):
        result = self._sender.send_notification(self._subject, self._body)
        self.finished_with_result.emit(result)


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
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        title = SubtitleLabel("邮件配置", self)
        layout.addWidget(title)

        # 启用开关
        enable_row = QHBoxLayout()
        self._chk_enable = CheckBox("启用邮件通知", self)
        enable_row.addWidget(self._chk_enable)
        enable_row.addSpacing(20)
        enable_row.addWidget(BodyLabel("发送模式：", self))
        self._combo_mode = QComboBox()
        self._combo_mode.addItems(["全部发送", "主备切换"])
        self._combo_mode.setFixedWidth(120)
        enable_row.addWidget(self._combo_mode)
        enable_row.addStretch()
        layout.addLayout(enable_row)

        # 服务器列表卡片
        server_card = OutlinedCardWidget(self)
        server_layout = QVBoxLayout(server_card)
        server_layout.setContentsMargins(20, 20, 20, 20)

        server_title = BodyLabel("服务器列表", self)
        server_title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        server_layout.addWidget(server_title)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["名称", "SMTP 地址", "端口", "主", "启用"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(150)
        server_layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_add = TonalPushButton("添加", self)
        btn_add.clicked.connect(self._on_add_server)
        btn_row.addWidget(btn_add)
        btn_edit = TonalPushButton("编辑", self)
        btn_edit.clicked.connect(self._on_edit_server)
        btn_row.addWidget(btn_edit)
        btn_del = TonalPushButton("删除", self)
        btn_del.clicked.connect(self._on_delete_server)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        server_layout.addLayout(btn_row)
        layout.addWidget(server_card)

        # 收件人
        recv_row = QHBoxLayout()
        recv_row.addWidget(BodyLabel("收件人：", self))
        self._input_recipients = QLineEdit()
        self._input_recipients.setPlaceholderText("多个收件人用逗号分隔")
        recv_row.addWidget(self._input_recipients)
        layout.addLayout(recv_row)

        # 通知选项
        self._chk_notify_success = CheckBox("归档成功时通知", self)
        layout.addWidget(self._chk_notify_success)
        self._chk_notify_failure = CheckBox("归档失败时通知", self)
        layout.addWidget(self._chk_notify_failure)

        # 操作按钮
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        self._btn_test = OutlinedPushButton("测试连接", self)
        self._btn_test.clicked.connect(self._on_test_mail)
        action_row.addWidget(self._btn_test)
        self._btn_send = FilledPushButton("发送测试邮件", self)
        self._btn_send.clicked.connect(self._on_send_test_mail)
        action_row.addWidget(self._btn_send)
        self._btn_save = FilledPushButton("保存配置", self)
        self._btn_save.clicked.connect(self._on_save)
        action_row.addWidget(self._btn_save)
        action_row.addStretch()
        layout.addLayout(action_row)

        self._status_label = BodyLabel("", self)
        self._status_label.setStyleSheet("color: #616161; font-size: 13px;")
        layout.addWidget(self._status_label)
        layout.addStretch()

    def _load_config(self):
        self._chk_enable.setChecked(self._config.get("mail.enabled", False))
        send_mode = self._config.get("mail.send_mode", "all")
        self._combo_mode.setCurrentIndex(0 if send_mode == "all" else 1)
        self._input_recipients.setText(", ".join(self._config.get("mail.recipients", [])))
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
            self._table.setItem(row, 3, QTableWidgetItem("✓" if server.get("is_primary") else ""))
            self._table.setItem(row, 4, QTableWidgetItem("✓" if server.get("enabled", True) else ""))

    def _on_add_server(self):
        dialog = ServerEditDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            servers = self._config.get("mail.servers", [])
            servers.append(dialog.get_config())
            self._config.set("mail.servers", servers)
            self._refresh_table()

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

    def _on_delete_server(self):
        row = self._table.currentRow()
        if row < 0:
            return
        servers = self._config.get("mail.servers", [])
        if row < len(servers):
            servers.pop(row)
            self._config.set("mail.servers", servers)
            self._refresh_table()

    def _on_test_mail(self):
        row = self._table.currentRow()
        servers = self._config.get("mail.servers", [])
        if row < 0 or row >= len(servers):
            QMessageBox.warning(self, "提示", "请先选择一个服务器")
            return
        self._status_label.setText("正在测试连接...")
        self._btn_test.setEnabled(False)
        self._test_worker = MailTestWorker(self._mail, servers[row])
        self._test_worker.finished_with_result.connect(self._on_test_finished)
        self._test_worker.start()

    def _on_test_finished(self, result):
        self._btn_test.setEnabled(True)
        if result["success"]:
            self._status_label.setText("成功：连接测试通过")
        else:
            self._status_label.setText(f"失败：{result['error']}")

    def _on_send_test_mail(self):
        """发送测试邮件 - 在后台线程执行，避免阻塞 UI"""
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

        self._status_label.setText("正在发送测试邮件...")
        self._btn_send.setEnabled(False)
        subject = "FolderArchiveTool 测试邮件"
        body = """<html><body style="font-family: 'Microsoft YaHei', Arial, sans-serif; color: #333;">
            <h2 style="color: #1976D2;">FolderArchiveTool</h2>
            <p>这是一封测试邮件。如果您收到此邮件，说明配置正确！</p>
            <hr style="border: none; border-top: 1px solid #eee;">
            <p style="color: #999; font-size: 12px;">此邮件由 FolderArchiveTool 自动发送</p>
        </body></html>"""
        # 在后台线程发送
        self._send_worker = MailSendWorker(self._mail, subject, body)
        self._send_worker.finished_with_result.connect(self._on_send_finished)
        self._send_worker.start()

    def _on_send_finished(self, result):
        self._btn_send.setEnabled(True)
        if result.get("success"):
            self._status_label.setText("成功：测试邮件已发送")
        else:
            failed_str = "; ".join(f"{s}: {e}" for s, e in result.get("failed", []))
            self._status_label.setText(f"失败：{failed_str}\n请查看日志页面获取详细信息")

    def _on_save(self):
        self._config.set("mail.enabled", self._chk_enable.isChecked())
        self._config.set("mail.send_mode", "all" if self._combo_mode.currentIndex() == 0 else "primary")
        recipients = [r.strip() for r in self._input_recipients.text().split(",") if r.strip()]
        self._config.set("mail.recipients", recipients)
        self._config.set("mail.notify_on_success", self._chk_notify_success.isChecked())
        self._config.set("mail.notify_on_failure", self._chk_notify_failure.isChecked())
        self._config.save()
        self._status_label.setText("已保存")
