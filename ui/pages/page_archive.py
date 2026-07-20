"""
归档操作页面 - Material Design 3 (QMaterialWidgets)
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QComboBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, ElevatedCardWidget,
    CheckBox, ProgressBar, SubtitleLabel, BodyLabel,
    InfoBar, InfoBarPosition, FluentIcon,
)

from core.config_manager import ConfigManager
from core.archive_service import ArchiveService
from core.scheduler import ArchiveScheduler


class ScanWorker(QThread):
    """文件扫描工作线程 - 避免大目录阻塞 UI"""
    finished_with_result = Signal(dict)

    def __init__(self, service):
        super().__init__()
        self._service = service

    def run(self):
        result = self._service.scan_files()
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
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        # 标题
        title = SubtitleLabel("归档操作", self)
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        layout.addWidget(title)

        desc = BodyLabel("扫描日期格式文件 → 按月打包 → CRC32 校验 → 安全删除", self)
        desc.setStyleSheet("color: #616161;")
        layout.addWidget(desc)

        # 路径配置卡片
        path_card = ElevatedCardWidget(self)
        path_layout = QVBoxLayout(path_card)
        path_layout.setContentsMargins(20, 20, 20, 20)
        path_layout.setSpacing(12)

        src_row = QHBoxLayout()
        src_row.setSpacing(8)
        src_label = BodyLabel("源目录", self)
        src_label.setFixedWidth(64)
        src_row.addWidget(src_label)
        self._input_source = QLineEdit(self)
        self._input_source.setPlaceholderText("选择包含日期格式文件的目录...")
        self._input_source.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        src_row.addWidget(self._input_source)
        btn_src = TonalPushButton("浏览...", self)
        btn_src.clicked.connect(self._browse_source)
        src_row.addWidget(btn_src)
        path_layout.addLayout(src_row)

        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        out_label = BodyLabel("输出目录", self)
        out_label.setFixedWidth(64)
        out_row.addWidget(out_label)
        self._input_output = QLineEdit(self)
        self._input_output.setPlaceholderText("压缩包存放目录...")
        self._input_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        out_row.addWidget(self._input_output)
        btn_out = TonalPushButton("浏览...", self)
        btn_out.clicked.connect(self._browse_output)
        out_row.addWidget(btn_out)
        path_layout.addLayout(out_row)

        opt_row = QHBoxLayout()
        opt_row.setSpacing(12)
        opt_row.addWidget(BodyLabel("文件模式:", self))
        self._combo_pattern = QComboBox(self)
        self._combo_pattern.setEditable(True)
        self._combo_pattern.addItems(["*.*", "*.log", "*.csv", "*.txt"])
        self._combo_pattern.setFixedWidth(120)
        opt_row.addWidget(self._combo_pattern)
        opt_row.addSpacing(16)
        self._chk_recursive = CheckBox("递归子目录", self)
        opt_row.addWidget(self._chk_recursive)
        opt_row.addStretch()
        path_layout.addLayout(opt_row)

        layout.addWidget(path_card)

        # 扫描结果卡片
        result_card = ElevatedCardWidget(self)
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(20, 20, 20, 20)
        result_layout.setSpacing(12)

        result_header = QHBoxLayout()
        result_title = SubtitleLabel("扫描结果", self)
        result_header.addWidget(result_title)
        result_header.addStretch()
        self._label_summary = BodyLabel("", self)
        self._label_summary.setStyleSheet("color: #616161;")
        result_header.addWidget(self._label_summary)
        result_layout.addLayout(result_header)

        select_row = QHBoxLayout()
        self._btn_select_all = TonalPushButton("全选", self)
        self._btn_select_all.clicked.connect(self._select_all)
        select_row.addWidget(self._btn_select_all)
        self._btn_deselect_all = TonalPushButton("全不选", self)
        self._btn_deselect_all.clicked.connect(self._deselect_all)
        select_row.addWidget(self._btn_deselect_all)
        select_row.addStretch()
        result_layout.addLayout(select_row)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["选择", "月份", "文件数", "总大小", "压缩包", "状态"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(200)
        result_layout.addWidget(self._table)

        layout.addWidget(result_card)

        # 操作按钮
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        self._btn_scan = FilledPushButton("扫描文件", self)
        self._btn_scan.clicked.connect(self._on_scan)
        action_row.addWidget(self._btn_scan)
        self._btn_archive = FilledPushButton("手动归档", self)
        self._btn_archive.clicked.connect(self._on_manual_archive)
        self._btn_archive.setEnabled(False)
        action_row.addWidget(self._btn_archive)
        self._btn_clean = TonalPushButton("清理原文件", self)
        self._btn_clean.clicked.connect(self._on_manual_clean)
        self._btn_clean.setEnabled(False)
        action_row.addWidget(self._btn_clean)
        self._btn_verify = OutlinedPushButton("校验", self)
        self._btn_verify.clicked.connect(self._on_verify_only)
        action_row.addWidget(self._btn_verify)
        action_row.addStretch()
        layout.addLayout(action_row)

        self._progress = ProgressBar(self)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._status_label = BodyLabel("", self)
        self._status_label.setStyleSheet("color: #616161; font-size: 13px;")
        layout.addWidget(self._status_label)
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
            chk = self._table.cellWidget(row, 0)
            if chk:
                chk.setChecked(True)

    def _deselect_all(self):
        for row in range(self._table.rowCount()):
            chk = self._table.cellWidget(row, 0)
            if chk:
                chk.setChecked(False)

    def _on_scan(self):
        source = self._input_source.text().strip()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "提示", "请先选择有效的源目录")
            return
        self._save_paths()
        self._set_busy(True)
        self._status_label.setText("正在扫描...")
        # 在后台线程扫描，避免大目录阻塞 UI
        self._scan_worker = ScanWorker(self._service)
        self._scan_worker.finished_with_result.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_finished(self, result):
        self._set_busy(False)
        if result["success"]:
            self._scan_groups = result["groups"]
            self._scan_file_list = result["groups"]
            self._refresh_table()
            self._label_summary.setText(f"共 {result['total_files']} 个文件，{len(result['groups'])} 个月份")
            self._status_label.setText(f"扫描完成：{result['total_files']} 个文件")
            self._btn_archive.setEnabled(True)
            self._btn_clean.setEnabled(True)
        else:
            QMessageBox.critical(self, "扫描失败", result.get("error", "未知错误"))

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
        stage_names = {"scan": "扫描中", "archive": "压缩中", "validate": "校验中", "clean": "清理中", "mail": "发送邮件", "complete": "完成"}
        if total > 0:
            self._progress.setValue(min(int(current / total * 100), 100))
        self._status_label.setText(f"[{stage_names.get(stage, stage)}] {message}")

    def _on_status(self, message):
        self._status_label.setText(message)

    def _on_archive_finished(self, result):
        self._set_busy(False)
        self._progress.setVisible(False)
        if result.get("success"):
            InfoBar.success(self, "完成", "归档任务完成！", position=InfoBarPosition.TOP)
            self._on_scan()
        else:
            InfoBar.error(self, "失败", result.get("error", "归档失败"), position=InfoBarPosition.TOP)

    def _on_manual_clean(self):
        InfoBar.info(self, "提示", "清理操作将在归档校验通过后自动执行", position=InfoBarPosition.TOP)

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
            results.append(f"{'通过' if is_valid else '失败'} {name}")
        QMessageBox.information(self, "校验结果", "\n".join(results))

    def _refresh_table(self):
        self._table.setRowCount(0)
        output_dir = self._input_output.text().strip()
        from core.file_scanner import FileScanner
        for month, files in self._scan_groups.items():
            row = self._table.rowCount()
            self._table.insertRow(row)
            chk = CheckBox("", self)
            chk.setChecked(True)
            self._table.setCellWidget(row, 0, chk)
            self._table.setItem(row, 1, QTableWidgetItem(month))
            self._table.setItem(row, 2, QTableWidgetItem(str(len(files))))
            total_size = sum(f.get("size", 0) for f in files)
            self._table.setItem(row, 3, QTableWidgetItem(FileScanner._human_size(total_size)))
            archive_path = os.path.join(output_dir, f"archive_{month}.zip") if output_dir else ""
            if archive_path and os.path.exists(archive_path):
                asize = os.path.getsize(archive_path)
                self._table.setItem(row, 4, QTableWidgetItem(FileScanner._human_size(asize)))
                self._table.setItem(row, 5, QTableWidgetItem("已归档"))
            else:
                self._table.setItem(row, 4, QTableWidgetItem("-"))
                self._table.setItem(row, 5, QTableWidgetItem("待归档"))

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
