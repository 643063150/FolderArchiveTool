"""
通用设置页面 — Material Design 3 精修版
"""

import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
    QFormLayout, QComboBox, QSpinBox, QGraphicsDropShadowEffect,
    QFrame, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from qmaterialwidgets import (
    FilledPushButton, OutlinedPushButton, TonalPushButton,
    OutlinedCardWidget, CheckBox, SwitchButton,
    BodyLabel, SubtitleLabel,
)

from core.config_manager import ConfigManager
from core.auto_start import AutoStartManager
from assets.styles.material_colors import Colors


# ── 工具 ──────────────────────────────────────────────

def _shadow(w):
    s = QGraphicsDropShadowEffect(w)
    s.setBlurRadius(16); s.setXOffset(0); s.setYOffset(2)
    s.setColor(QColor(0, 0, 0, 18))
    w.setGraphicsEffect(s)


def _make_section_card(title_icon: str, title_text: str) -> tuple:
    """创建设置区卡片，返回 (card, layout)"""
    card = OutlinedCardWidget()
    _shadow(card)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(16)

    header = QHBoxLayout()
    icon = BodyLabel(title_icon)
    icon.setStyleSheet("font-size: 18px;")
    header.addWidget(icon)
    header.addSpacing(6)
    label = BodyLabel(title_text)
    label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.on_surface};")
    header.addWidget(label)
    header.addStretch()
    layout.addLayout(header)

    return card, layout


# ── 主页面 ────────────────────────────────────────────

class PageSettings(QWidget):
    def __init__(self, config, service, scheduler, parent=None):
        super().__init__(parent)
        self._config = config
        self._auto_start = AutoStartManager()
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ═══ 页面标题 ═══════════════════════════════════
        header = QHBoxLayout()
        title = SubtitleLabel("通用设置")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Colors.on_surface};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        desc = BodyLabel("管理程序行为、压缩选项与安全设置")
        desc.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
        layout.addWidget(desc)

        # ═══ 基础设置卡片 ═══════════════════════════════
        basic_card, basic_layout = _make_section_card("⚙️", "基础设置")
        basic_form = QFormLayout()
        basic_form.setSpacing(14)
        basic_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # 开机自启
        autostart_row = QHBoxLayout()
        autostart_row.setSpacing(8)
        self._chk_auto_start = SwitchButton(self)
        self._chk_auto_start.setChecked(self._auto_start.is_task_scheduler_enabled())
        autostart_row.addWidget(self._chk_auto_start)
        autostart_row.addWidget(BodyLabel("开机自动启动"))
        autostart_row.addStretch()
        basic_form.addRow("启动：", autostart_row)

        # 最小化到托盘
        tray_row = QHBoxLayout()
        tray_row.setSpacing(8)
        self._chk_tray = SwitchButton(self)
        tray_row.addWidget(self._chk_tray)
        tray_row.addWidget(BodyLabel("最小化到系统托盘"))
        tray_row.addStretch()
        basic_form.addRow("托盘：", tray_row)

        # 压缩格式
        self._combo_format = QComboBox()
        self._combo_format.addItems(["zip", "7z"])
        self._combo_format.setFixedWidth(140)
        self._combo_format.setStyleSheet(f"""
            QComboBox {{
                background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
                border-radius: 8px; padding: 10px 14px; min-height: 20px;
            }}
        """)
        basic_form.addRow("压缩格式：", self._combo_format)

        # 压缩级别
        self._spin_level = QSpinBox()
        self._spin_level.setRange(0, 9)
        self._spin_level.setFixedWidth(100)
        self._spin_level.setStyleSheet(f"""
            QSpinBox {{
                background: {Colors.surface}; border: 1px solid {Colors.outline_variant};
                border-radius: 8px; padding: 10px 14px;
            }}
        """)
        basic_form.addRow("压缩级别：", self._spin_level)

        basic_layout.addLayout(basic_form)
        layout.addWidget(basic_card)

        # ═══ 安全设置卡片 ═══════════════════════════════
        safety_card, safety_layout = _make_section_card("🛡️", "安全设置")

        safety_form = QFormLayout()
        safety_form.setSpacing(14)
        safety_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        confirm_row = QHBoxLayout()
        confirm_row.setSpacing(8)
        self._chk_confirm = SwitchButton(self)
        confirm_row.addWidget(self._chk_confirm)
        confirm_row.addWidget(BodyLabel("删除前二次确认"))
        confirm_row.addStretch()
        safety_form.addRow("确认：", confirm_row)

        safety_layout.addLayout(safety_form)
        layout.addWidget(safety_card)

        # ═══ 操作按钮 ═══════════════════════════════════
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_save = FilledPushButton("💾 保存设置", self)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        btn_export = TonalPushButton("📤 导出配置", self)
        btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(btn_export)

        btn_import = OutlinedPushButton("📥 导入配置", self)
        btn_import.clicked.connect(self._on_import)
        btn_row.addWidget(btn_import)

        btn_reset = OutlinedPushButton("↺ 恢复默认", self)
        btn_reset.clicked.connect(self._on_reset)
        btn_row.addWidget(btn_reset)

        btn_row.addStretch()

        self._status_label = BodyLabel("")
        self._status_label.setStyleSheet(f"color: {Colors.on_surface_variant}; font-size: 13px;")
        btn_row.addWidget(self._status_label)

        layout.addLayout(btn_row)
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
                self._status_label.setText("✅ 开机自启已启用（任务计划程序）")
                log.info("[设置] 开机自启已启用并验证成功")
            else:
                log.info("[设置] 任务计划程序创建失败，尝试注册表方式...")
                if self._auto_start.enable_registry():
                    self._status_label.setText("✅ 开机自启已启用（注册表方式）")
                else:
                    self._status_label.setText("❌ 开机自启启用失败")
        else:
            log.info("[设置] 用户禁用开机自启")
            self._auto_start.disable_task_scheduler()
            self._auto_start.disable_registry()
            self._status_label.setText("✅ 开机自启已禁用")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出配置", "config.json", "JSON (*.json)")
        if path:
            self._config.export_config(path)
            self._status_label.setText(f"📤 已导出: {path}")

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON (*.json)")
        if path:
            try:
                self._config.import_config(path)
                main_window = self.window()
                if hasattr(main_window, 'refresh_all_pages'):
                    main_window.refresh_all_pages()
                self._load_config()
                self._status_label.setText("📥 已导入")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", str(e))

    def _on_reset(self):
        reply = QMessageBox.question(self, "确认", "恢复默认配置？所有当前设置将丢失。",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._config.reset_to_default()
            self._load_config()
            self._status_label.setText("↺ 已恢复默认")
