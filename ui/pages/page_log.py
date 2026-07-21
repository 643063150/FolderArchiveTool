"""
运行日志页面 — Material Design 3 精修版
"""

import os
import re
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox,
    QLineEdit, QFileDialog, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QColor
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, BodyLabel, StrongBodyLabel,
)

from core.config_manager import ConfigManager
from assets.styles.material_colors import Colors


class PageLog(QWidget):
    """日志查看页面 — MD3 精修版"""

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
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ═══ 页面标题 ═══════════════════════════════════
        header = QHBoxLayout()
        title = StrongBodyLabel("运行日志")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Colors.on_surface};")
        header.addWidget(title)
        header.addStretch()

        # 统计信息
        self._status = BodyLabel("就绪")
        self._status.setStyleSheet(f"""
            color: {Colors.on_surface_variant}; font-size: 12px;
            padding: 4px 14px; background: {Colors.surface_container};
            border-radius: 12px;
        """)
        header.addWidget(self._status)

        layout.addLayout(header)

        desc = BodyLabel("实时日志输出 — 支持过滤、搜索、导出")
        desc.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
        layout.addWidget(desc)

        # ═══ 工具栏 ═════════════════════════════════════
        toolbar = QWidget()
        toolbar.setStyleSheet(f"""
            QWidget {{
                background: {Colors.surface_container};
                border-radius: 12px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 10, 16, 10)
        toolbar_layout.setSpacing(10)

        # 级别过滤
        level_label = BodyLabel("📊 级别:")
        level_label.setStyleSheet(f"color: {Colors.on_surface_variant}; background: transparent;")
        toolbar_layout.addWidget(level_label)

        self._combo_level = QComboBox(self)
        self._combo_level.addItems(["全部", "INFO", "WARNING", "ERROR", "DEBUG", "定时任务"])
        self._combo_level.setFixedWidth(110)
        self._combo_level.currentTextChanged.connect(self._filter_logs)
        self._combo_level.setStyleSheet(f"""
            QComboBox {{
                background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
                border-radius: 8px; padding: 6px 12px; min-height: 20px;
            }}
        """)
        toolbar_layout.addWidget(self._combo_level)

        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {Colors.outline_variant}; max-width: 1px;")
        toolbar_layout.addWidget(sep)

        # 搜索
        search_icon = BodyLabel("🔍")
        search_icon.setStyleSheet("background: transparent;")
        toolbar_layout.addWidget(search_icon)
        self._input_search = QLineEdit(self)
        self._input_search.setPlaceholderText("搜索关键词...")
        self._input_search.setMinimumWidth(160)
        self._input_search.textChanged.connect(self._filter_logs)
        self._input_search.setStyleSheet(f"""
            QLineEdit {{
                background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
                border-radius: 8px; padding: 6px 14px; min-height: 20px;
            }}
            QLineEdit:focus {{ border: 2px solid {Colors.primary}; }}
        """)
        toolbar_layout.addWidget(self._input_search)

        toolbar_layout.addStretch()

        # 操作按钮
        btn_refresh = OutlinedPushButton("🔄 刷新", self)
        btn_refresh.setToolTip("刷新日志")
        btn_refresh.clicked.connect(self._refresh)
        toolbar_layout.addWidget(btn_refresh)

        btn_clear = OutlinedPushButton("🗑 清空", self)
        btn_clear.setToolTip("清空日志")
        btn_clear.clicked.connect(self._clear)
        toolbar_layout.addWidget(btn_clear)

        btn_export = TonalPushButton("📤 导出", self)
        btn_export.clicked.connect(self._export)
        toolbar_layout.addWidget(btn_export)

        layout.addWidget(toolbar)

        # ═══ 日志显示区 ═════════════════════════════════
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background: #1A1C1E;
                color: #E6E1E5;
                border: 1px solid #2F3134;
                border-radius: 14px;
                padding: 16px;
                font-family: "Cascadia Code", "JetBrains Mono", "Consolas", monospace;
                font-size: 13px;
                line-height: 1.7;
                selection-background-color: #1565C0;
            }}
        """)
        layout.addWidget(self._text)

    def on_log_message(self, level: str, message: str):
        """日志回调（pyqtSignal 线程安全）"""
        with self._logs_lock:
            self._all_logs.append((level, message))
            if len(self._all_logs) > self._max_lines:
                self._all_logs = self._all_logs[-self._max_lines:]
            if self._matches_filter(level, message):
                self._append_log(level, message)
            count = len(self._all_logs)
        self._status.setText(f"📋 共 {count} 条日志")

    def _append_log(self, level, message):
        """带颜色标记的日志行"""
        log_colors = {
            "INFO": "#80CBC4",
            "WARNING": "#FFD54F",
            "ERROR": "#EF9A9A",
            "DEBUG": "#B0BEC5",
        }
        color = log_colors.get(level, "#ECEFF1")
        safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        timestamp = ""
        time_colors = {"INFO": "#546E7A", "WARNING": "#8D6E63", "ERROR": "#BF360C", "DEBUG": "#455A64"}
        tc = time_colors.get(level, "#546E7A")
        # 尝试提取时间戳
        match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', safe_msg)
        if match:
            ts = match.group(1)
            rest = safe_msg[len(ts):]
            html = (
                f'<span style="color: {tc};">{ts}</span>'
                f'<span style="color: {color};">{rest}</span>'
            )
        else:
            html = f'<span style="color: {color};">[{level}]</span> {safe_msg}'

        self._text.insertHtml(html + "<br>")
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._text.setTextCursor(cursor)

        # 自动滚动到底部
        scrollbar = self._text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _matches_filter(self, level, message):
        lvl = self._combo_level.currentText()
        search = self._input_search.text().lower()
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
        self._status.setText("🗑 已清空")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "app.log", "Text (*.txt)")
        if path:
            with self._logs_lock:
                logs_copy = self._all_logs.copy()
            with open(path, "w", encoding="utf-8") as f:
                for level, message in logs_copy:
                    f.write(f"[{level}] {message}\n")
            self._status.setText(f"📤 已导出: {path}")

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
            count = len(new_logs)
            self._status.setText(f"📋 已加载 {count} 条日志")
        except Exception as e:
            self._status.setText(f"⚠️ 加载失败: {e}")
