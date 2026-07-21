"""
定时任务页面 — Material Design 3 精修版
"""

import threading
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QAbstractItemView, QComboBox, QSpinBox,
    QDialog, QFormLayout, QTimeEdit, QLineEdit, QLabel,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtGui import QColor
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, CheckBox, SwitchButton,
    BodyLabel, StrongBodyLabel, SubtitleLabel,
)

from core.config_manager import ConfigManager
from core.archive_service import ArchiveService
from core.scheduler import ArchiveScheduler
from assets.styles.material_colors import Colors


# ── 工具函数 ──────────────────────────────────────────

def _card_shadow(widget):
    s = QGraphicsDropShadowEffect(widget)
    s.setBlurRadius(16); s.setXOffset(0); s.setYOffset(2)
    s.setColor(QColor(0, 0, 0, 18))
    widget.setGraphicsEffect(s)


# ── 任务编辑对话框 ────────────────────────────────────

class JobEditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加定时任务")
        self.setMinimumWidth(480)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{ background: {Colors.surface_container_low}; border-radius: 20px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = SubtitleLabel("⏰ 新建任务")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.on_surface};")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        LABEL = f"color: {Colors.on_surface_variant}; font-size: 14px;"
        INPUT = f"""
            QLineEdit, QSpinBox, QTimeEdit {{
                background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
                border-radius: 8px; padding: 10px 14px; font-size: 14px;
                color: {Colors.on_surface};
            }}
            QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus {{
                border: 2px solid {Colors.primary};
            }}
        """

        self._name = QLineEdit()
        self._name.setPlaceholderText("如：每月归档任务")
        self._name.setStyleSheet(INPUT)
        form.addRow(QLabel("名称"), self._name)

        self._type = QComboBox()
        self._type.addItems(["📅 每月", "📆 每周", "📋 每天", "⚙️ Cron"])
        self._type.currentIndexChanged.connect(self._on_type_changed)
        self._type.setStyleSheet(f"""
            QComboBox {{ background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
            border-radius: 8px; padding: 10px 14px; min-height: 20px; }}
        """)
        form.addRow(QLabel("频率"), self._type)

        self._day = QSpinBox()
        self._day.setRange(1, 31); self._day.setValue(1)
        self._day.setStyleSheet(INPUT)
        form.addRow(QLabel("日期"), self._day)

        self._weekday = QComboBox()
        self._weekday.addItems(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        self._weekday.setStyleSheet(self._type.styleSheet())
        form.addRow(QLabel("星期"), self._weekday)

        self._time = QTimeEdit()
        self._time.setTime(QTime(2, 0))
        self._time.setDisplayFormat("HH:mm")
        self._time.setStyleSheet(INPUT)
        form.addRow(QLabel("时间"), self._time)

        self._cron = QLineEdit()
        self._cron.setPlaceholderText("0 2 1 * *")
        self._cron.setStyleSheet(INPUT)
        self._cron_label = QLabel("表达式：")
        self._cron_label.setStyleSheet(LABEL)
        form.addRow(self._cron_label, self._cron)
        self._cron_label.setVisible(False)
        self._cron.setVisible(False)

        # 默认隐藏每周行
        self._weekday_row = form.rowCount() - 4
        self._weekday.setVisible(False)

        self._enabled = CheckBox("立即启用", self)
        self._enabled.setChecked(True)
        form.addRow("", self._enabled)

        layout.addLayout(form)
        layout.addSpacing(8)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = OutlinedPushButton("取消", self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_ok = FilledPushButton("添加", self)
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

        self._on_type_changed(0)

    def _on_type_changed(self, index):
        is_monthly = index == 0
        is_weekly = index == 1
        is_cron = index == 3
        self._day.setVisible(is_monthly)
        self._weekday.setVisible(is_weekly)
        self._cron.setVisible(is_cron)
        self._cron_label.setVisible(is_cron)

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


# ── 主页面 ────────────────────────────────────────────

class PageSchedule(QWidget):
    def __init__(self, config, service, scheduler, parent=None):
        super().__init__(parent)
        self._config = config
        self._service = service
        self._scheduler = scheduler
        self._init_ui()
        self._refresh_jobs()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_jobs)
        self._timer.start(5000)  # 每 5 秒刷新减少开销

    def showEvent(self, event):
        self._refresh_jobs()
        super().showEvent(event)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ═══ 页面标题 ═══════════════════════════════════
        header = QHBoxLayout()
        title = SubtitleLabel("定时任务")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Colors.on_surface};")
        header.addWidget(title)
        header.addStretch()

        # 调度器开关
        toggle_group = QHBoxLayout()
        toggle_group.setSpacing(8)
        toggle_icon = BodyLabel("⏱")
        toggle_icon.setStyleSheet("font-size: 18px;")
        toggle_group.addWidget(toggle_icon)
        self._chk_enable = SwitchButton(self)
        self._chk_enable.setChecked(self._config.get("schedule.enabled", False))
        self._chk_enable.checkedChanged.connect(self._on_enable_toggle)
        toggle_group.addWidget(self._chk_enable)
        toggle_group.addWidget(BodyLabel("定时调度"))
        header.addLayout(toggle_group)

        layout.addLayout(header)

        desc = BodyLabel("支持每月 / 每周 / 每天 / 自定义 Cron 表达式，自动执行归档流程")
        desc.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
        layout.addWidget(desc)

        # ═══ 任务列表卡片 ═══════════════════════════════
        job_card = OutlinedCardWidget(self)
        _card_shadow(job_card)
        job_layout = QVBoxLayout(job_card)
        job_layout.setContentsMargins(24, 20, 24, 20)
        job_layout.setSpacing(12)

        job_header = QHBoxLayout()
        job_icon = BodyLabel("📋")
        job_icon.setStyleSheet("font-size: 18px;")
        job_header.addWidget(job_icon)
        job_header.addSpacing(6)
        job_title = BodyLabel("任务列表")
        job_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.on_surface};")
        job_header.addWidget(job_title)
        job_header.addStretch()
        job_layout.addLayout(job_header)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["名称", "调度规则", "下次执行", "剩余时间"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(180)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {Colors.surface};
                border: 1px solid {Colors.outline_variant};
                border-radius: 12px;
            }}
            QTableWidget::item {{
                padding: 12px 16px;
                border-bottom: 1px solid {Colors.surface_container};
            }}
            QTableWidget::item:selected {{
                background: {Colors.primary_container};
                color: {Colors.on_primary_container};
            }}
            QHeaderView::section {{
                background: {Colors.surface_container};
                border: none;
                border-bottom: 2px solid {Colors.outline_variant};
                padding: 12px 16px;
                font-weight: 600; font-size: 12px;
                color: {Colors.on_surface_variant};
            }}
        """)
        job_layout.addWidget(self._table)

        # 任务操作按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_add = FilledPushButton("＋ 添加任务", self)
        self._btn_add.clicked.connect(self._on_add_job)
        btn_row.addWidget(self._btn_add)

        self._btn_pause = TonalPushButton("⏸ 暂停", self)
        self._btn_pause.clicked.connect(self._on_pause_job)
        btn_row.addWidget(self._btn_pause)

        self._btn_resume = TonalPushButton("▶️ 恢复", self)
        self._btn_resume.clicked.connect(self._on_resume_job)
        btn_row.addWidget(self._btn_resume)

        self._btn_delete = OutlinedPushButton("🗑 删除", self)
        self._btn_delete.clicked.connect(self._on_delete_job)
        btn_row.addWidget(self._btn_delete)

        btn_row.addStretch()
        job_layout.addLayout(btn_row)
        layout.addWidget(job_card)

        # ═══ 立即执行 ═══════════════════════════════════
        run_row = QHBoxLayout()
        run_row.setSpacing(12)
        self._btn_run_now = FilledPushButton("▶️  立即执行归档", self)
        self._btn_run_now.clicked.connect(self._on_run_now)
        self._btn_run_now.setFixedHeight(44)
        run_row.addWidget(self._btn_run_now)

        self._status_label = BodyLabel("")
        self._status_label.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
        run_row.addWidget(self._status_label)
        run_row.addStretch()
        layout.addLayout(run_row)

        layout.addStretch()

    def _refresh_jobs(self):
        """刷新任务列表（保留选中状态）"""
        selected_id = self._get_selected_job_id()
        jobs = self._scheduler.list_jobs()
        self._table.setRowCount(0)
        now = datetime.now()

        for job in jobs:
            row = self._table.rowCount()
            self._table.insertRow(row)

            name = job.get("name", "")
            trigger = job.get("trigger", "")
            next_run = job.get("next_run", "")
            remaining = self._calc_remaining(next_run, now)

            name_item = QTableWidgetItem(name)
            name_font = name_item.font()
            name_font.setBold(True)
            name_item.setFont(name_font)
            self._table.setItem(row, 0, name_item)

            trigger_display = self._format_trigger(trigger)
            self._table.setItem(row, 1, QTableWidgetItem(trigger_display))

            next_item = QTableWidgetItem(next_run if next_run else "未调度")
            self._table.setItem(row, 2, next_item)

            remaining_item = QTableWidgetItem(remaining)
            if remaining == "执行中...":
                remaining_item.setForeground(QColor(Colors.primary))
            elif remaining and "分" in remaining and "时" not in remaining and "天" not in remaining:
                remaining_item.setForeground(QColor("#E65100"))
            self._table.setItem(row, 3, remaining_item)

        if selected_id:
            self._select_job_by_id(selected_id)

        if self._service.is_running:
            self._status_label.setText("⏳ 归档任务正在运行中...")

    def _format_trigger(self, trigger: str) -> str:
        """美化触发器显示"""
        if "cron[" in trigger:
            try:
                inner = trigger.split("cron[")[1].rstrip("]")
                parts = {}
                for kv in inner.split(", "):
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        parts[k.strip()] = v.strip("'\"")
                day = parts.get("day", "*")
                month = parts.get("month", "*")
                dow = parts.get("day_of_week", "*")
                hour = parts.get("hour", "0")
                minute = parts.get("minute", "0")
                if day != "*" and month == "*" and dow == "*":
                    return f"每月 {int(day)} 日 {int(hour):02d}:{int(minute):02d}"
                elif dow != "*" and day == "*":
                    dow_names = {"sun": "周日", "mon": "周一", "tue": "周二", "wed": "周三",
                                 "thu": "周四", "fri": "周五", "sat": "周六"}
                    d = dow_names.get(dow, dow)
                    return f"每 {d} {int(hour):02d}:{int(minute):02d}"
                elif day == "*" and month == "*" and dow == "*":
                    return f"每天 {int(hour):02d}:{int(minute):02d}"
                return f"{minute} {hour} {day} {month} {dow}"
            except Exception:
                pass
        if trigger.startswith("cron["):
            return trigger[5:-1]
        return trigger

    def _get_selected_job_id(self) -> str:
        row = self._table.currentRow()
        if row < 0:
            return ""
        jobs = self._scheduler.list_jobs()
        if row < len(jobs):
            return jobs[row].get("id", "")
        return ""

    def _select_job_by_id(self, job_id: str):
        jobs = self._scheduler.list_jobs()
        for i, job in enumerate(jobs):
            if job.get("id") == job_id:
                self._table.selectRow(i)
                break

    @staticmethod
    def _calc_remaining(next_run_str: str, now: datetime) -> str:
        """计算剩余时间（美化格式）"""
        if not next_run_str or next_run_str in ("未调度", "未知"):
            return "-"
        try:
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
            self._scheduler.start()       # start() 内部已调用 load_jobs()
            self._status_label.setText("✅ 定时调度已启用")
        else:
            self._scheduler.stop()
            self._status_label.setText("⏸ 定时调度已停止")
        # 开关后立即刷新列表，避免显示空白
        self._refresh_jobs()

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
                if jc.get("enabled"):
                    self._chk_enable.setChecked(True)
                    if not self._scheduler.is_running():
                        self._scheduler.start()
                self._refresh_jobs()
                self._status_label.setText(f"✅ 已添加: {jc['name']}")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def _on_pause_job(self):
        row = self._table.currentRow()
        if row < 0:
            return
        if not self._scheduler.is_running():
            QMessageBox.warning(self, "提示", "调度器未运行，请先启用定时调度")
            return
        jobs = self._scheduler.list_jobs()
        if row < len(jobs):
            self._scheduler.pause_job(jobs[row]["id"])
            self._refresh_jobs()
            self._status_label.setText("⏸ 已暂停")

    def _on_resume_job(self):
        row = self._table.currentRow()
        if row < 0:
            return
        if not self._scheduler.is_running():
            QMessageBox.warning(self, "提示", "调度器未运行，请先启用定时调度")
            return
        jobs = self._scheduler.list_jobs()
        if row < len(jobs):
            self._scheduler.resume_job(jobs[row]["id"])
            self._refresh_jobs()
            self._status_label.setText("▶️ 已恢复")

    def _on_delete_job(self):
        row = self._table.currentRow()
        if row < 0:
            return
        jobs = self._scheduler.list_jobs()
        if row < len(jobs):
            reply = QMessageBox.question(self, "确认", f"删除任务「{jobs[row].get('name', '')}」？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._scheduler.remove_job(jobs[row]["id"])
                self._refresh_jobs()
                # 删除后同步到配置
                self._config.set("schedule.enabled", self._chk_enable.isChecked())
                self._config.save()
                self._status_label.setText("🗑 已删除")

    def _on_run_now(self):
        self._status_label.setText("⏳ 触发归档任务...")
        self._scheduler.trigger_now()
        self._status_label.setText("✅ 已触发")
