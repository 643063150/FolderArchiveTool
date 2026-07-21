"""
主窗口
MD3 Navigation Rail + 内容区
支持系统托盘、平滑动画
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QSystemTrayIcon,
    QMenu, QApplication, QStyle, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QColor, QAction

from core.config_manager import ConfigManager
from core.logger_setup import set_ui_log_callback
from core.archive_service import ArchiveService
from core.scheduler import ArchiveScheduler

from assets.styles import load_stylesheet
from assets.styles.material_colors import Colors
from assets.styles.animations import Easing, Duration

from .pages.page_archive import PageArchive
from .pages.page_mail import PageMail
from .pages.page_schedule import PageSchedule
from .pages.page_settings import PageSettings
from .pages.page_log import PageLog


class NavigationButton(QWidget):
    """MD3 Navigation Rail 按钮 - 自定义绘制，完美居中"""

    clicked = None  # 将在下方定义信号

    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_text = icon_text
        self._label = label
        self._checked = False
        self._hovered = False
        self.setFixedSize(100, 68)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

    def setChecked(self, checked: bool):
        self._checked = checked
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._clicked_callback = True

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, '_clicked_callback', False):
            self._clicked_callback = False
            self.update()
            # 发出点击信号
            if hasattr(self, '_click_handler') and self._click_handler:
                self._click_handler()
        else:
            self._clicked_callback = False
            self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QFont, QPainterPath

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # 背景状态层
        if self._checked:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(Colors.primary_container))
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 16, 16)
        elif self._hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(Colors.surface_container_high))
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 16, 16)

        # 选中指示器（左侧圆角条）
        if self._checked:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(Colors.primary))
            painter.drawRoundedRect(4, 22, 3, 24, 1.5, 1.5)

        # 文字颜色
        text_color = QColor(Colors.on_primary_container if self._checked else Colors.on_surface_variant)

        # 图标（使用 emoji 字体）
        icon_font = QFont("Segoe UI Emoji", 20)
        painter.setFont(icon_font)
        painter.setPen(text_color)
        painter.drawText(rect.adjusted(0, 6, 0, -28), Qt.AlignCenter, self._icon_text)

        # 标签文字
        label_font = QFont("Microsoft YaHei UI", 12)
        if self._checked:
            label_font.setBold(True)
        painter.setFont(label_font)
        painter.drawText(rect.adjusted(0, 36, 0, -6), Qt.AlignCenter, self._label)

        painter.end()


class MainWindow(QMainWindow):
    """MD3 主窗口"""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._service = ArchiveService(config)
        self._scheduler = ArchiveScheduler(config_manager=config)

        self._init_ui()
        self._init_tray()
        self._init_scheduler()
        self._inject_log_callback()

    def _init_ui(self):
        self.setWindowTitle("FolderArchiveTool v1.0")
        self.setMinimumSize(1080, 700)
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 左侧导航栏 (Navigation Rail) ───────────────
        nav = QWidget()
        nav.setObjectName("navRail")
        nav.setFixedWidth(120)
        nav.setStyleSheet(f"""
            QWidget#navRail {{
                background: {Colors.surface_container_low};
                border-right: 1px solid {Colors.outline_variant};
            }}
        """)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(10, 20, 10, 16)
        nav_layout.setSpacing(6)

        # 顶部品牌图标
        brand = QLabel("📦")
        brand.setStyleSheet("font-size: 36px; padding: 16px 0;")
        brand.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(brand)

        nav_layout.addSpacing(8)

        # 导航按钮
        self._nav_buttons = []
        self._stack = QStackedWidget()

        nav_items = [
            ("📁", "归档", PageArchive),
            ("✉️", "邮件", PageMail),
            ("⏰", "定时", PageSchedule),
            ("⚙️", "设置", PageSettings),
            ("📋", "日志", PageLog),
        ]

        # 创建页面列表
        pages = []
        for icon_text, label, page_class in nav_items:
            btn = NavigationButton(icon_text, label)
            nav_layout.addWidget(btn, alignment=Qt.AlignHCenter)
            self._nav_buttons.append(btn)

            # 创建页面
            page = page_class(
                config=self._config,
                service=self._service,
                scheduler=self._scheduler,
            )
            self._stack.addWidget(page)
            pages.append(page)

        nav_layout.addStretch()

        # 版本号
        version = QLabel("v1.0")
        version.setStyleSheet(f"color: {Colors.outline}; font-size: 10px; padding: 8px 0;")
        version.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(version)

        layout.addWidget(nav)

        # ── 右侧内容区 ──────────────────────────────────
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._stack)

        layout.addWidget(content)

        # 连接导航信号（使用自定义回调）
        for i, btn in enumerate(self._nav_buttons):
            btn._click_handler = lambda idx=i: self._switch_page(idx)

        # 保存页面引用以便刷新
        self._pages = pages

        # 默认选中第一个
        self._nav_buttons[0].setChecked(True)

    def _switch_page(self, index: int):
        """切换页面"""
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
        self._stack.setCurrentIndex(index)

        # 确保当前页面可见（不使用 opacity 动画，避免页面空白）
        current = self._stack.currentWidget()
        if current:
            current.setVisible(True)
            current.show()

    def _init_tray(self):
        """系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self._tray.setToolTip("FolderArchiveTool - 月度文件归档")

        tray_menu = QMenu()
        action_show = QAction("显示主窗口", self)
        action_show.triggered.connect(self.show_normal)
        action_scan = QAction("快速扫描", self)
        action_scan.triggered.connect(lambda: self._service.scan_files())
        action_quit = QAction("退出", self)
        action_quit.triggered.connect(QApplication.quit)

        tray_menu.addAction(action_show)
        tray_menu.addAction(action_scan)
        tray_menu.addSeparator()
        tray_menu.addAction(action_quit)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(
            lambda r: self.show_normal() if r == QSystemTrayIcon.Trigger else None
        )
        self._tray.show()

    def refresh_all_pages(self):
        """配置导入后刷新所有页面"""
        # 重新加载定时任务
        self._scheduler.load_jobs()
        for page in self._pages:
            if hasattr(page, '_load_config'):
                page._load_config()
            if hasattr(page, '_refresh_jobs'):
                page._refresh_jobs()

    def _init_scheduler(self):
        self._scheduler.set_job_function(self._on_scheduled_run)
        # 恢复持久化的定时任务
        self._scheduler.load_jobs()
        # 刷新定时任务页面显示
        for page in self._pages:
            if hasattr(page, '_refresh_jobs'):
                page._refresh_jobs()
        if self._config.get("schedule.enabled", False):
            self._scheduler.start()

    def _inject_log_callback(self):
        """动态查找 PageLog 页面并连接日志回调（通过 pyqtSignal，线程安全）"""
        for i in range(self._stack.count()):
            page = self._stack.widget(i)
            if isinstance(page, PageLog):
                set_ui_log_callback(page.on_log_message)
                return
        import logging
        logging.getLogger("FolderArchiveTool").warning("[UI] 未找到 PageLog 页面")

    def _on_scheduled_run(self):
        """定时任务触发（在后台线程中运行）"""
        self._service.run_full_archive(
            mode="auto",
            status_callback=lambda msg: None  # 静默模式，不更新 UI 避免线程问题
        )

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.activateWindow()

    def closeEvent(self, event):
        if self._config.get("general.minimize_to_tray", True) and hasattr(self, "_tray") and self._tray.isVisible():
            self.hide()
            self._tray.showMessage(
                "FolderArchiveTool",
                "已最小化到系统托盘",
                QSystemTrayIcon.Information,
                2000,
            )
            event.ignore()
        else:
            # 安全停止调度器（等待运行中任务完成）
            self._scheduler.stop(timeout=15)
            # 断开日志回调，防止关闭期间还有日志
            set_ui_log_callback(None)
            event.accept()
