"""
定时任务页面 - Material Design 3 风格
"""

import threading
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QAbstractItemView, QComboBox, QSpinBox,
    QDialog, QDialogButtonBox, QFormLayout, QTimeEdit, QLineEdit, QLabel,
)
from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtGui import QFont
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, CheckBox, SwitchButton,
    BodyLabel, StrongBodyLabel, SubtitleLabel,
)

from core.config_manager import ConfigManager
from core.archive_service import ArchiveService
from core.scheduler import ArchiveScheduler


class JobEditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加定时任务")
        self.setMinimumWidth(440)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        self._name = QLineEdit()
        self._name.setPlaceholderText("如：每月归档任务")
        layout.addRow("名称：", self._name)
        self._type = QComboBox()
        self._type.addItems(["每月", "每周", "每天", "Cron"])
        self._type.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("频率：", self._type)
        self._day = QSpinBox()
        self._day.setRange(1, 31)
        self._day.setValue(1)
        layout.addRow("日期：", self._day)
        self._weekday = QComboBox()
        self._weekday.addItems(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        self._time = QTimeEdit()
        self._time.setTime(QTime(2, 0))
        self._time.setDisplayFormat("HH:mm")
        layout.addRow("时间：", self._time)
        self._cron = QLineEdit()
        self._cron.setPlaceholderText("0 2 1 * *")
        self._cron_label = QLabel("表达式：")
        layout.addRow(self._cron_label, self._cron)
        self._cron_label.setVisible(False)
        self._cron.setVisible(False)
        self._enabled = CheckBox("立即启用", self)
        self._enabled.setChecked(True)
        layout.addRow("", self._enabled)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self._on_type_changed(0)

    def _on_type_changed(self, index):
        self._day.setVisible(index == 0)
        self._cron.setVisible(index == 3)
        self._cron_label.setVisible(index == 3)

    def get_job_config(self):
        t = self._time.time()
        return {
            "name": self._name.text() or "定时任务",
            "type": ["monthly", "weekly", "daily", "cron"][self._type.currentIndex()],
            "day": self._day.value(),
            "hour": t.hour(),
            "minute": t.minute(),
            "cron": self._cron.text(),
            "enabled": self._enabled.isChecked(),
        }


class PageSchedule(QWidget):
    def __init__(self, config, service, scheduler, parent=None):
        super().__init__(parent)
        self._config = config
        self._service = service
        self._scheduler = scheduler
        self._init_ui()
        self._refresh_jobs()

        # 实时倒计时刷新器（每秒刷新）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_jobs)
        self._timer.start(1000)  # 1秒

    def showEvent(self, event):
        """页面显示时刷新"""
        self._refresh_jobs()
        super().showEvent(event)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        title = SubtitleLabel("定时任务", self)
        layout.addWidget(title)

        # 启用开关
        enable_row = QHBoxLayout()
        self._chk_enable = CheckBox("启用定时调度", self)
        self._chk_enable.setChecked(self._config.get("schedule.enabled", False))
        self._chk_enable.toggled.connect(self._on_enable_toggle)
        enable_row.addWidget(self._chk_enable)
        enable_row.addStretch()
        layout.addLayout(enable_row)

        # 任务列表卡片
        job_card = OutlinedCardWidget(self)
        job_layout = QVBoxLayout(job_card)
        job_layout.setContentsMargins(20, 20, 20, 20)

        job_title = BodyLabel("任务列表", self)
        job_title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        job_layout.addWidget(job_title)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["名称", "调度", "下次执行", "剩余时间"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(150)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        job_layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_add = FilledPushButton("添加任务", self)
        self._btn_add.clicked.connect(self._on_add_job)
        btn_row.addWidget(self._btn_add)
        self._btn_pause = TonalPushButton("暂停", self)
        self._btn_pause.clicked.connect(self._on_pause_job)
        btn_row.addWidget(self._btn_pause)
        self._btn_resume = TonalPushButton("恢复", self)
        self._btn_resume.clicked.connect(self._on_resume_job)
        btn_row.addWidget(self._btn_resume)
        self._btn_delete = OutlinedPushButton("删除", self)
        self._btn_delete.clicked.connect(self._on_delete_job)
        btn_row.addWidget(self._btn_delete)
        btn_row.addStretch()
        job_layout.addLayout(btn_row)
        layout.addWidget(job_card)

        # 立即执行
        run_row = QHBoxLayout()
        self._btn_run_now = FilledPushButton("立即执行归档", self)
        self._btn_run_now.clicked.connect(self._on_run_now)
        run_row.addWidget(self._btn_run_now)
        run_row.addStretch()
        layout.addLayout(run_row)

        self._status_label = BodyLabel("", self)
        self._status_label.setStyleSheet("color: #616161; font-size: 13px;")
        layout.addWidget(self._status_label)
        layout.addStretch()

    def _refresh_jobs(self):
        """刷新任务列表（含实时倒计时），保持选中状态"""
        # 保存当前选中的任务 ID
        selected_id = self._get_selected_job_id()

        jobs = self._scheduler.list_jobs()
        self._table.setRowCount(0)
        now = datetime.now()
        for job in jobs:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(job.get("name", "")))
            self._table.setItem(row, 1, QTableWidgetItem(job.get("trigger", "")))
            self._table.setItem(row, 2, QTableWidgetItem(job.get("next_run", "")))
            # 计算剩余时间
            remaining = self._calc_remaining(job.get("next_run", ""), now)
            self._table.setItem(row, 3, QTableWidgetItem(remaining))

        # 恢复选中状态
        if selected_id:
            self._select_job_by_id(selected_id)

        if self._service.is_running:
            self._status_label.setText("归档任务正在运行中...")

    def _get_selected_job_id(self) -> str:
        """获取当前选中行的任务 ID"""
        row = self._table.currentRow()
        if row < 0:
            return ""
        # 从 jobs 列表获取对应 ID
        jobs = self._scheduler.list_jobs()
        if row < len(jobs):
            return jobs[row].get("id", "")
        return ""

    def _select_job_by_id(self, job_id: str):
        """根据任务 ID 选中对应行"""
        jobs = self._scheduler.list_jobs()
        for i, job in enumerate(jobs):
            if job.get("id") == job_id:
                self._table.selectRow(i)
                break

    @staticmethod
    def _calc_remaining(next_run_str: str, now: datetime) -> str:
        """计算距离下次执行的剩余时间"""
        if not next_run_str or next_run_str in ("未调度", "未知"):
            return "-"
        try:
            # 解析时间字符串（可能带时区）
            # 格式: 2026-08-21 11:37:00+08:00
            if "+" in next_run_str:
                next_run_str = next_run_str[:next_run_str.rfind("+")]
            next_run = datetime.strptime(next_run_str, "%Y-%m-%d %H:%M:%S")
            delta = next_run - now
            if delta.total_seconds() <= 0:
                return "执行中..."
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0:
                return f"{days}天{hours}时{minutes}分"
            elif hours > 0:
                return f"{hours}时{minutes}分{seconds}秒"
            else:
                return f"{minutes}分{seconds}秒"
        except Exception:
            return "-"

    def _on_enable_toggle(self, enabled):
        self._config.set("schedule.enabled", enabled)
        self._config.save()
        if enabled:
            self._scheduler.start()
            self._status_label.setText("定时调度已启用")
        else:
            self._scheduler.stop()
            self._status_label.setText("定时调度已停止")

    def _on_add_job(self):
        dialog = JobEditDialog(self)
        if dialog.exec() == QDialog.Accepted:
            jc = dialog.get_job_config()
            try:
                if jc["type"] == "monthly":
                    jid = self._scheduler.add_monthly_job(day=jc["day"], hour=jc["hour"], minute=jc["minute"])
                elif jc["type"] == "weekly":
                    wday = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                    weekday_idx = dialog._weekday.currentIndex()
                    jid = self._scheduler.add_weekly_job(day_of_week=wday[weekday_idx], hour=jc["hour"], minute=jc["minute"])
                elif jc["type"] == "daily":
                    jid = self._scheduler.add_custom_cron(f"{jc['minute']} {jc['hour']} * * *")
                else:
                    jid = self._scheduler.add_custom_cron(jc["cron"])
                # 如果勾选了"立即启用"，自动启用调度器
                if jc.get("enabled"):
                    self._chk_enable.setChecked(True)
                    if not self._scheduler.is_running():
                        self._scheduler.start()
                self._refresh_jobs()
                self._status_label.setText(f"已添加: {jc['name']}")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _on_pause_job(self):
        row = self._table.currentRow()
        if row < 0: return
        jobs = self._scheduler.list_jobs()
        if row < len(jobs):
            self._scheduler.pause_job(jobs[row]["id"])
            self._refresh_jobs()

    def _on_resume_job(self):
        row = self._table.currentRow()
        if row < 0: return
        jobs = self._scheduler.list_jobs()
        if row < len(jobs):
            self._scheduler.resume_job(jobs[row]["id"])
            self._refresh_jobs()

    def _on_delete_job(self):
        row = self._table.currentRow()
        if row < 0: return
        jobs = self._scheduler.list_jobs()
        if row < len(jobs):
            self._scheduler.remove_job(jobs[row]["id"])
            self._refresh_jobs()

    def _on_run_now(self):
        self._status_label.setText("触发归档任务...")
        self._scheduler.trigger_now()
        self._status_label.setText("已触发")
