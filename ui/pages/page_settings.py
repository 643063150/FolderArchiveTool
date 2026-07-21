"""
通用设置页面 - Material Design 3 风格
"""

import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
    QFormLayout, QComboBox, QSpinBox,
)
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, CheckBox, SwitchButton,
    BodyLabel, SubtitleLabel,
)

from core.config_manager import ConfigManager
from core.auto_start import AutoStartManager


class PageSettings(QWidget):
    def __init__(self, config, service, scheduler, parent=None):
        super().__init__(parent)
        self._config = config
        self._auto_start = AutoStartManager()
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        title = SubtitleLabel("通用设置", self)
        layout.addWidget(title)

        # 基础设置卡片
        basic_card = OutlinedCardWidget(self)
        basic_layout = QFormLayout(basic_card)
        basic_layout.setContentsMargins(20, 20, 20, 20)

        # 开机自启
        self._chk_auto_start = CheckBox("开机自动启动", self)
        self._chk_auto_start.setChecked(self._auto_start.is_task_scheduler_enabled())
        basic_layout.addRow("启动：", self._chk_auto_start)

        self._chk_tray = CheckBox("最小化到系统托盘", self)
        basic_layout.addRow("托盘：", self._chk_tray)

        self._combo_format = QComboBox()
        self._combo_format.addItems(["zip", "7z"])
        basic_layout.addRow("压缩格式：", self._combo_format)

        self._spin_level = QSpinBox()
        self._spin_level.setRange(0, 9)
        basic_layout.addRow("压缩级别：", self._spin_level)

        layout.addWidget(basic_card)

        # 安全设置卡片
        safety_card = OutlinedCardWidget(self)
        safety_layout = QFormLayout(safety_card)
        safety_layout.setContentsMargins(20, 20, 20, 20)

        self._chk_confirm = CheckBox("删除前二次确认", self)
        safety_layout.addRow("确认：", self._chk_confirm)

        layout.addWidget(safety_card)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_save = FilledPushButton("保存设置", self)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)
        btn_export = TonalPushButton("导出配置", self)
        btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(btn_export)
        btn_import = OutlinedPushButton("导入配置", self)
        btn_import.clicked.connect(self._on_import)
        btn_row.addWidget(btn_import)
        btn_reset = OutlinedPushButton("恢复默认", self)
        btn_reset.clicked.connect(self._on_reset)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._status_label = BodyLabel("", self)
        self._status_label.setStyleSheet("color: #616161; font-size: 13px;")
        layout.addWidget(self._status_label)
        layout.addStretch()

    def _load_config(self):
        self._chk_auto_start.setChecked(self._auto_start.is_task_scheduler_enabled())
        self._chk_tray.setChecked(self._config.get("general.minimize_to_tray", True))
        self._combo_format.setCurrentText(self._config.get("general.compression_format", "zip"))
        self._spin_level.setValue(self._config.get("general.compression_level", 6))
        self._chk_confirm.setChecked(self._config.get("general.delete_confirm", True))

    def _on_save(self):
        import logging
        log = logging.getLogger("FolderArchiveTool")

        self._config.set("general.minimize_to_tray", self._chk_tray.isChecked())
        self._config.set("general.compression_format", self._combo_format.currentText())
        self._config.set("general.compression_level", self._spin_level.value())
        self._config.set("general.delete_confirm", self._chk_confirm.isChecked())
        self._config.save()
        log.info("[设置] 配置已保存")

        # 处理开机自启
        if self._chk_auto_start.isChecked():
            log.info("[设置] 用户启用开机自启，尝试创建任务计划程序...")
            if self._auto_start.enable_task_scheduler():
                # 验证是否真的创建成功
                if self._auto_start.is_task_scheduler_enabled():
                    self._status_label.setText("[OK] 开机自启已启用（任务计划程序）")
                    log.info("[设置] 开机自启已启用并验证成功")
                else:
                    self._status_label.setText("[WARN] 任务创建但验证失败，尝试注册表方式...")
                    log.warning("[设置] 任务计划程序创建后验证失败")
                    if self._auto_start.enable_registry():
                        self._status_label.setText("[OK] 开机自启已启用（注册表方式）")
                    else:
                        self._status_label.setText("[FAIL] 所有方式均失败")
            else:
                log.info("[设置] 任务计划程序创建失败，尝试注册表方式...")
                if self._auto_start.enable_registry():
                    self._status_label.setText("[OK] 开机自启已启用（注册表方式）")
                else:
                    self._status_label.setText("[FAIL] 开机自启启用失败")
        else:
            log.info("[设置] 用户禁用开机自启")
            self._auto_start.disable_task_scheduler()
            self._auto_start.disable_registry()
            self._status_label.setText("[OK] 开机自启已禁用")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出配置", "config.json", "JSON (*.json)")
        if path:
            self._config.export_config(path)
            self._status_label.setText(f"已导出: {path}")

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON (*.json)")
        if path:
            try:
                self._config.import_config(path)
                # 刷新主窗口所有页面
                main_window = self.window()
                if hasattr(main_window, 'refresh_all_pages'):
                    main_window.refresh_all_pages()
                self._status_label.setText("已导入")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", str(e))

    def _on_reset(self):
        reply = QMessageBox.question(self, "确认", "恢复默认配置？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._config.reset_to_default()
            self._load_config()
            self._status_label.setText("已恢复默认")
