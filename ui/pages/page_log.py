"""
运行日志页面 - Material Design 3 风格
"""

import os
import re
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox,
    QLineEdit, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, BodyLabel, StrongBodyLabel,
)

from core.config_manager import ConfigManager


class PageLog(QWidget):
    """日志查看页面 - MD3 风格"""

    def __init__(self, config: ConfigManager, service, scheduler, parent=None):
        super().__init__(parent)
        self._config = config
        self._max_lines = config.get("log.ui_max_lines", 1000)
        self._all_logs = []
        self._logs_lock = threading.Lock()
        self._init_ui()
        self._load_log_file()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # 标题
        title = StrongBodyLabel("运行日志", self)
        layout.addWidget(title)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(BodyLabel("级别:", self))
        self._combo_level = QComboBox(self)
        self._combo_level.addItems(["全部", "INFO", "WARNING", "ERROR", "DEBUG", "定时任务"])
        self._combo_level.setFixedWidth(100)
        self._combo_level.currentTextChanged.connect(self._filter_logs)
        toolbar.addWidget(self._combo_level)

        toolbar.addSpacing(8)
        toolbar.addWidget(BodyLabel("搜索:", self))
        self._input_search = QLineEdit(self)
        self._input_search.setPlaceholderText("输入关键词...")
        self._input_search.setMinimumWidth(180)
        self._input_search.textChanged.connect(self._filter_logs)
        toolbar.addWidget(self._input_search)

        toolbar.addStretch()

        btn_refresh = FilledPushButton("刷新", self)
        btn_refresh.clicked.connect(self._refresh)
        toolbar.addWidget(btn_refresh)

        btn_clear = TonalPushButton("清空", self)
        btn_clear.clicked.connect(self._clear)
        toolbar.addWidget(btn_clear)

        btn_export = OutlinedPushButton("导出", self)
        btn_export.clicked.connect(self._export)
        toolbar.addWidget(btn_export)

        layout.addLayout(toolbar)

        # 日志显示区
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        layout.addWidget(self._text)

        # 状态栏
        self._status = BodyLabel("就绪", self)
        self._status.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(self._status)

    def on_log_message(self, level: str, message: str):
        """日志回调（由 pyqtSignal 从主线程调用，线程安全）"""
        with self._logs_lock:
            self._all_logs.append((level, message))
            if len(self._all_logs) > self._max_lines:
                self._all_logs = self._all_logs[-self._max_lines:]
            if self._matches_filter(level, message):
                self._append_log(level, message)
            count = len(self._all_logs)
        self._status.setText(f"共 {count} 条日志")

    def _append_log(self, level, message):
        log_colors = {"INFO": "#80CBC4", "WARNING": "#FFD54F", "ERROR": "#EF9A9A", "DEBUG": "#B0BEC5"}
        color = log_colors.get(level, "#ECEFF1")
        safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = f'<span style="color: {color};">[{level}]</span> {safe_msg}<br>'
        self._text.insertHtml(html)
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._text.setTextCursor(cursor)

    def _matches_filter(self, level, message):
        lvl = self._combo_level.currentText()
        search = self._input_search.text().lower()
        # 定时任务专用过滤
        if lvl == "定时任务":
            return "[定时]" in message
        if lvl != "全部" and level != lvl:
            return False
        if search and search not in message.lower():
            return False
        return True

    def _filter_logs(self):
        self._text.clear()
        with self._logs_lock:
            logs_copy = self._all_logs.copy()
        for level, message in logs_copy:
            if self._matches_filter(level, message):
                self._append_log(level, message)

    def _refresh(self):
        self._filter_logs()

    def _clear(self):
        self._text.clear()
        with self._logs_lock:
            self._all_logs.clear()
        self._status.setText("已清空")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "app.log", "Text (*.txt)")
        if path:
            with self._logs_lock:
                logs_copy = self._all_logs.copy()
            with open(path, "w", encoding="utf-8") as f:
                for level, message in logs_copy:
                    f.write(f"[{level}] {message}\n")
            self._status.setText(f"已导出: {path}")

    def _load_log_file(self):
        log_path = os.path.join("logs", "app.log")
        if not os.path.exists(log_path):
            return
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            pattern = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[(\w+)\] (.*)$')
            new_logs = []
            for line in lines:
                m = pattern.match(line.strip())
                if m:
                    new_logs.append((m.group(1), m.group(2)))
            if len(new_logs) > self._max_lines:
                new_logs = new_logs[-self._max_lines:]
            with self._logs_lock:
                self._all_logs = new_logs
            self._filter_logs()
            self._status.setText(f"已加载 {len(new_logs)} 条")
        except Exception as e:
            self._status.setText(f"加载失败: {e}")
