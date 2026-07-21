"""
归档操作页面 — Material Design 3 精修版
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QComboBox, QSizePolicy,
    QGraphicsDropShadowEffect, QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, ElevatedCardWidget,
    CheckBox, ProgressBar, SubtitleLabel, BodyLabel,
    InfoBar, InfoBarPosition, FluentIcon,
)

from core.config_manager import ConfigManager
from core.archive_service import ArchiveService
from core.scheduler import ArchiveScheduler
from assets.styles.material_colors import Colors


class MD3CheckBox(QWidget):
    """Material Design 3 风格复选框 — 自绘，和字号匹配"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = True
        self.setFixedSize(18, 18)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        self._checked = checked
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.update()
            parent_table = self.parent()
            while parent_table and not isinstance(parent_table, QTableWidget):
                parent_table = parent_table.parent()
            if parent_table:
                parent_table.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        s = 16
        x = (self.width() - s) // 2
        y = (self.height() - s) // 2
        rect = QRect(x, y, s, s)

        if self._checked:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(Colors.primary))
            painter.drawRoundedRect(rect, 2, 2)
            painter.setPen(QPen(QColor(Colors.on_primary), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPolyline([
                QPoint(x + 3, y + 8),
                QPoint(x + 6, y + 11),
                QPoint(x + 12, y + 5),
            ])
        else:
            painter.setPen(QPen(QColor(Colors.outline), 1.5))
            painter.setBrush(QColor(Colors.surface))
            painter.drawRoundedRect(rect, 2, 2)

        painter.end()


# ── 工具函数 ──────────────────────────────────────────

def _apply_card_shadow(widget, blur=18, offset=2, color=QColor(0, 0, 0, 20)):
    """给卡片添加 MD3 阴影"""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(offset)
    shadow.setColor(color)
    widget.setGraphicsEffect(shadow)


def _create_section_title(text: str) -> SubtitleLabel:
    """创建带左侧指示条的小标题"""
    label = SubtitleLabel(text)
    label.setStyleSheet(f"""
        font-size: 16px; font-weight: 600;
        color: {Colors.on_surface};
        padding-left: 0px;
        margin-bottom: 4px;
    """)
    return label


def _make_card_widget(title: str = None) -> tuple:
    """创建 ElevateCardWidget + layout，可选标题"""
    card = ElevatedCardWidget()
    _apply_card_shadow(card)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(16)
    if title:
        title_label = SubtitleLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 18px; font-weight: 700;
            color: {Colors.on_surface}; margin-bottom: 4px;
        """)
        layout.addWidget(title_label)
    return card, layout


# ── 工作线程 ──────────────────────────────────────────

class ScanWorker(QThread):
    """文件扫描工作线程"""
    finished_with_result = Signal(dict)

    def __init__(self, service):
        super().__init__()
        self._service = service

    def run(self):
        try:
            result = self._service.scan_files()
        except Exception as e:
            result = {"success": False, "error": f"扫描异常: {e}", "groups": {}, "total_files": 0, "total_size": 0}
        self.finished_with_result.emit(result)


class ArchiveWorker(QThread):
    """归档工作线程"""
    progress = Signal(str, int, int, str)
    status = Signal(str)
    finished_with_result = Signal(dict)

    def __init__(self, service, target_month=None):
        super().__init__()
        self._service = service
        self._target_month = target_month

    def run(self):
        result = self._service.run_full_archive(
            target_month=self._target_month,
            progress_callback=lambda s, c, t, m: self.progress.emit(s, c, t, m),
            status_callback=lambda m: self.status.emit(m),
        )
        self.finished_with_result.emit(result)


# ── 主页面 ────────────────────────────────────────────

class PageArchive(QWidget):
    def __init__(self, config, service, scheduler=None, parent=None):
        super().__init__(parent)
        self._config = config
        self._service = service
        self._worker = None
        self._scan_groups = {}
        self._scan_file_list = {}
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ═══ 页面标题 ═══════════════════════════════════
        header = QHBoxLayout()
        title = SubtitleLabel("归档操作")
        title.setStyleSheet(f"""
            font-size: 24px; font-weight: 700;
            color: {Colors.on_surface}; letter-spacing: -0.3px;
        """)
        header.addWidget(title)
        header.addStretch()
        # 步骤提示
        step_hint = BodyLabel("扫描 → 打包 → CRC32 校验 → 安全删除")
        step_hint.setStyleSheet(f"""
            color: {Colors.on_surface_variant}; font-size: 13px;
            padding: 6px 16px;
            background: {Colors.surface_container};
            border-radius: 20px;
        """)
        header.addWidget(step_hint)
        layout.addLayout(header)

        # ═══ 路径配置卡片 ═══════════════════════════════
        path_card, path_layout = _make_card_widget()
        path_layout.setSpacing(14)

        # 源目录
        src_row = QHBoxLayout()
        src_row.setSpacing(10)
        src_icon = BodyLabel("📂")
        src_icon.setStyleSheet("font-size: 18px; padding-right: 4px;")
        src_row.addWidget(src_icon)
        src_label = BodyLabel("源目录")
        src_label.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 14px; min-width: 48px;")
        src_row.addWidget(src_label)
        self._input_source = QLineEdit(self)
        self._input_source.setPlaceholderText("选择包含日期格式文件的目录...")
        self._input_source.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._input_source.setStyleSheet(f"""
            QLineEdit {{ background: {Colors.surface_container}; border: 2px solid transparent; border-radius: 10px;
                         padding: 12px 16px; font-size: 14px; color: {Colors.on_surface}; }}
            QLineEdit:focus {{ border: 2px solid {Colors.primary}; background: {Colors.surface}; }}
        """)
        src_row.addWidget(self._input_source)
        btn_src = TonalPushButton("浏览", self)
        btn_src.clicked.connect(self._browse_source)
        src_row.addWidget(btn_src)
        path_layout.addLayout(src_row)

        # 输出目录
        out_row = QHBoxLayout()
        out_row.setSpacing(10)
        out_icon = BodyLabel("💾")
        out_icon.setStyleSheet("font-size: 18px; padding-right: 4px;")
        out_row.addWidget(out_icon)
        out_label = BodyLabel("输出")
        out_label.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 14px; min-width: 48px;")
        out_row.addWidget(out_label)
        self._input_output = QLineEdit(self)
        self._input_output.setPlaceholderText("压缩包存放目录...")
        self._input_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._input_output.setStyleSheet(self._input_source.styleSheet())
        out_row.addWidget(self._input_output)
        btn_out = TonalPushButton("浏览", self)
        btn_out.clicked.connect(self._browse_output)
        out_row.addWidget(btn_out)
        path_layout.addLayout(out_row)

        # 选项行
        opt_row = QHBoxLayout()
        opt_row.setSpacing(16)
        opt_row.addWidget(BodyLabel("文件模式:"))
        self._combo_pattern = QComboBox(self)
        self._combo_pattern.setEditable(True)
        self._combo_pattern.addItems(["*.*", "*.log", "*.csv", "*.txt"])
        self._combo_pattern.setFixedWidth(130)
        opt_row.addWidget(self._combo_pattern)
        opt_row.addSpacing(8)
        self._chk_recursive = CheckBox("递归子目录", self)
        opt_row.addWidget(self._chk_recursive)
        opt_row.addStretch()
        path_layout.addLayout(opt_row)

        layout.addWidget(path_card)

        # ═══ 扫描结果卡片 ═══════════════════════════════
        result_card, result_layout = _make_card_widget()

        # 标题行
        result_header = QHBoxLayout()
        result_icon = BodyLabel("📋")
        result_icon.setStyleSheet("font-size: 18px;")
        result_header.addWidget(result_icon)
        result_header.addSpacing(6)
        result_title_label = BodyLabel("扫描结果")
        result_title_label.setStyleSheet(f"""
            font-size: 16px; font-weight: 600; color: {Colors.on_surface};
        """)
        result_header.addWidget(result_title_label)
        result_header.addStretch()
        self._label_summary = BodyLabel("")
        self._label_summary.setStyleSheet(f"""
            color: {Colors.on_surface_variant}; font-size: 13px;
            padding: 4px 12px;
            background: {Colors.surface_container};
            border-radius: 12px;
        """)
        result_header.addWidget(self._label_summary)
        result_layout.addLayout(result_header)

        # 选择按钮行
        select_row = QHBoxLayout()
        select_row.setSpacing(8)
        self._btn_select_all = TonalPushButton("全选", self)
        self._btn_select_all.clicked.connect(self._select_all)
        select_row.addWidget(self._btn_select_all)
        self._btn_deselect_all = TonalPushButton("全不选", self)
        self._btn_deselect_all.clicked.connect(self._deselect_all)
        select_row.addWidget(self._btn_deselect_all)
        select_row.addStretch()
        result_layout.addLayout(select_row)

        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["选择", "月份", "文件数", "总大小", "压缩包", "状态"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 32)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(200)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {Colors.surface};
                border: 1px solid {Colors.outline_variant};
                border-radius: 12px;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {Colors.surface_container};
            }}
            QHeaderView::section {{
                background: {Colors.surface_container};
                border: none;
                border-bottom: 2px solid {Colors.outline_variant};
                padding: 12px 16px;
                font-weight: 600;
                font-size: 12px;
                color: {Colors.on_surface_variant};
            }}
        """)
        result_layout.addWidget(self._table)

        layout.addWidget(result_card)

        # ═══ 操作按钮行 ═════════════════════════════════
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._btn_scan = FilledPushButton("🔍  扫描文件", self)
        self._btn_scan.clicked.connect(self._on_scan)
        action_row.addWidget(self._btn_scan)

        self._btn_archive = FilledPushButton("📦  手动归档", self)
        self._btn_archive.clicked.connect(self._on_manual_archive)
        self._btn_archive.setEnabled(False)
        action_row.addWidget(self._btn_archive)

        self._btn_clean = TonalPushButton("🧹  清理原文件", self)
        self._btn_clean.clicked.connect(self._on_manual_clean)
        self._btn_clean.setEnabled(False)
        action_row.addWidget(self._btn_clean)

        self._btn_verify = OutlinedPushButton("✓  校验", self)
        self._btn_verify.clicked.connect(self._on_verify_only)
        action_row.addWidget(self._btn_verify)

        action_row.addStretch()

        # 进度信息组
        progress_group = QHBoxLayout()
        progress_group.setSpacing(12)
        self._progress = ProgressBar(self)
        self._progress.setFixedHeight(6)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: {Colors.surface_container_highest};
                border: none; border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.primary}, stop:1 #5B9EEE);
                border-radius: 3px;
            }}
        """)
        progress_group.addWidget(self._progress, 1)

        self._status_label = BodyLabel("")
        self._status_label.setStyleSheet(f"""
            color: {Colors.on_surface_variant}; font-size: 13px;
            padding: 6px 12px;
        """)
        progress_group.addWidget(self._status_label)

        action_row.addLayout(progress_group)

        layout.addLayout(action_row)
        layout.addStretch()

    def _load_config(self):
        self._input_source.setText(self._config.get("general.source_dir", ""))
        self._input_output.setText(self._config.get("general.output_dir", ""))
        self._combo_pattern.setCurrentText(self._config.get("general.file_pattern", "*.*"))
        self._chk_recursive.setChecked(self._config.get("general.recursive", False))

    def _save_paths(self):
        self._config.set("general.source_dir", self._input_source.text())
        self._config.set("general.output_dir", self._input_output.text())
        self._config.set("general.file_pattern", self._combo_pattern.currentText())
        self._config.set("general.recursive", self._chk_recursive.isChecked())
        self._config.save()

    def _browse_source(self):
        path = QFileDialog.getExistingDirectory(self, "选择源目录")
        if path:
            self._input_source.setText(path)
            self._save_paths()

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self._input_output.setText(path)
            self._save_paths()

    def _select_all(self):
        for row in range(self._table.rowCount()):
            cell = self._table.cellWidget(row, 0)
            if cell and hasattr(cell, 'setChecked'):
                cell.setChecked(True)
                self._table.update()

    def _deselect_all(self):
        for row in range(self._table.rowCount()):
            cell = self._table.cellWidget(row, 0)
            if cell and hasattr(cell, 'setChecked'):
                cell.setChecked(False)
                self._table.update()

    def _on_scan(self):
        source = self._input_source.text().strip()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "提示", "请先选择有效的源目录")
            return
        self._save_paths()
        self._set_busy(True)
        self._status_label.setText("正在扫描...")
        self._scan_worker = ScanWorker(self._service)
        self._scan_worker.finished_with_result.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_finished(self, result):
        self._set_busy(False)
        if result["success"]:
            self._scan_groups = result["groups"]
            self._scan_file_list = result["groups"]
            self._refresh_table()
            total = result['total_files']
            months = len(result['groups'])
            self._label_summary.setText(f"📎 {total} 个文件 · {months} 个月份")
            self._status_label.setText(f"✅ 扫描完成：{total} 个文件")
            self._btn_archive.setEnabled(True)
            self._btn_clean.setEnabled(True)
        else:
            QMessageBox.critical(self, "扫描失败", result.get("error", "未知错误"))
            self._status_label.setText("❌ 扫描失败")

    def _on_manual_archive(self):
        selected = self._get_selected_months()
        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一个月份")
            return
        file_count = sum(len(self._scan_file_list.get(m, [])) for m in selected)
        reply = QMessageBox.question(
            self, "确认归档",
            f"将归档 {len(selected)} 个月份，共 {file_count} 个文件\n\n确认开始？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        target = selected[0] if len(selected) == 1 else None
        self._run_archive(target)

    def _run_archive(self, target_month=None):
        self._save_paths()
        self._set_busy(True)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._worker = ArchiveWorker(self._service, target_month)
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.finished_with_result.connect(self._on_archive_finished)
        self._worker.start()

    def _on_progress(self, stage, current, total, message):
        stage_icons = {
            "scan": "🔍", "archive": "📦", "validate": "✓",
            "clean": "🧹", "mail": "✉️", "complete": "✅"
        }
        stage_names = {
            "scan": "扫描中", "archive": "压缩中", "validate": "校验中",
            "clean": "清理中", "mail": "发送邮件", "complete": "完成"
        }
        icon = stage_icons.get(stage, "")
        name = stage_names.get(stage, stage)
        if total > 0:
            self._progress.setValue(min(int(current / total * 100), 100))
        self._status_label.setText(f"{icon} [{name}] {message}")

    def _on_status(self, message):
        self._status_label.setText(message)

    def _on_archive_finished(self, result):
        self._set_busy(False)
        self._progress.setVisible(False)
        if result.get("success"):
            self._status_label.setText("✅ 归档任务完成！")
            InfoBar.success(self, "完成", "归档任务完成！", position=InfoBarPosition.TOP, duration=3000)
            self._on_scan()
        else:
            err = result.get("error", "归档失败")
            self._status_label.setText(f"❌ {err}")
            InfoBar.error(self, "失败", err, position=InfoBarPosition.TOP, duration=5000)

    def _on_manual_clean(self):
        InfoBar.info(self, "提示", "清理操作将在归档校验通过后自动执行", position=InfoBarPosition.TOP, duration=3000)

    def _on_verify_only(self):
        output_dir = self._input_output.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "提示", "请先设置输出目录")
            return
        import glob
        zip_files = glob.glob(os.path.join(output_dir, "archive_*.zip"))
        if not zip_files:
            QMessageBox.information(self, "提示", "输出目录中没有找到压缩包")
            return
        from core.validator import Validator
        validator = Validator()
        results = []
        for f in sorted(zip_files):
            is_valid = validator.verify_zip_integrity(f)
            name = os.path.basename(f)
            icon = "✅" if is_valid else "❌"
            results.append(f"{icon} {name}")
        QMessageBox.information(
            self, "校验结果",
            "\n".join(results)
        )

    def _refresh_table(self):
        self._table.setRowCount(0)
        output_dir = self._input_output.text().strip()
        from core.file_scanner import FileScanner
        for month, files in self._scan_groups.items():
            row = self._table.rowCount()
            self._table.insertRow(row)
            # 勾选框（自绘 MD3 风格）
            chk = MD3CheckBox(self)
            chk.setChecked(True)
            self._table.setCellWidget(row, 0, chk)
            # 月份
            month_item = QTableWidgetItem(month)
            month_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 1, month_item)
            # 文件数
            count_item = QTableWidgetItem(str(len(files)))
            count_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 2, count_item)
            # 总大小
            total_size = sum(f.get("size", 0) for f in files)
            size_item = QTableWidgetItem(FileScanner._human_size(total_size))
            size_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 3, size_item)
            # 压缩包和状态
            archive_path = os.path.join(output_dir, f"archive_{month}.zip") if output_dir else ""
            if archive_path and os.path.exists(archive_path):
                asize = os.path.getsize(archive_path)
                self._table.setItem(row, 4, QTableWidgetItem(FileScanner._human_size(asize)))
                status_item = QTableWidgetItem("✅ 已归档")
                status_item.setForeground(QColor("#2E7D32"))
                self._table.setItem(row, 5, status_item)
            else:
                self._table.setItem(row, 4, QTableWidgetItem("-"))
                status_item = QTableWidgetItem("⏳ 待归档")
                status_item.setForeground(QColor("#E65100"))
                self._table.setItem(row, 5, status_item)

    def _get_selected_months(self):
        months = []
        for row in range(self._table.rowCount()):
            chk = self._table.cellWidget(row, 0)
            if chk and chk.isChecked():
                item = self._table.item(row, 1)
                if item:
                    months.append(item.text())
        return months

    def _set_busy(self, busy):
        self._btn_scan.setEnabled(not busy)
        self._btn_archive.setEnabled(not busy and bool(self._scan_groups))
        self._btn_clean.setEnabled(not busy and bool(self._scan_groups))
        self._btn_verify.setEnabled(not busy)
        if busy:
            self._status_label.setStyleSheet(f"color: {Colors.primary}; font-size: 13px;")
        else:
            self._status_label.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
