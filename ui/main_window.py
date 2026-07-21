"""
主窗口
MD3 Navigation Rail + 内容区
支持系统托盘、平滑动画、页面切换过渡
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QSystemTrayIcon,
    QMenu, QApplication, QStyle, QGraphicsDropShadowEffect,
    QFrame, QSizePolicy,
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    Signal, Property,
)
from PySide6.QtGui import QColor, QAction, QPainter, QFont, QPainterPath, QIcon

from assets.icons.material_icons import ICON_PATHS
from pathlib import Path
import sys

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
    """MD3 Navigation Rail 按钮 — 带平滑动画和 Material Ripple 效果"""

    clicked = Signal(int)

    def __init__(self, icon_name: str, label: str, index: int, parent=None):
        super().__init__(parent)
        self._icon_path = ICON_PATHS.get(icon_name, ICON_PATHS["folder"])
        self._label = label
        self._index = index
        self._checked = False
        self._hovered = False
        self._pressed = False
        self._anim_progress = 0.0  # 0 → 1 动画进度

        self.setFixedSize(100, 72)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

        # 颜色缓存 (避免重复构建 QColor)
        self._c_bg_checked = QColor(Colors.primary_container)
        self._c_bg_hover = QColor(Colors.surface_container_high)
        self._c_indicator = QColor(Colors.primary)
        self._c_text_active = QColor(Colors.on_primary_container)
        self._c_text_inactive = QColor(Colors.on_surface_variant)

        # 动画: 选中态背景从透明渐变色
        self._bg_anim = QPropertyAnimation(self, b"anim_progress", self)
        self._bg_anim.setDuration(220)
        self._bg_anim.setEasingCurve(QEasingCurve.OutCubic)

    # ── Qt 动画属性（QPropertyAnimation 需要 Qt 属性系统）──
    def get_anim_progress(self) -> float:
        return self._anim_progress

    def set_anim_progress(self, v: float):
        self._anim_progress = v
        self.update()

    anim_progress = Property(float, get_anim_progress, set_anim_progress)

    # ── 公共方法 ──
    def setChecked(self, checked: bool, animated: bool = True):
        self._checked = checked
        if animated:
            self._bg_anim.stop()
            self._bg_anim.setStartValue(self._anim_progress)
            self._bg_anim.setEndValue(1.0 if checked else 0.0)
            self._bg_anim.start()
        else:
            self._anim_progress = 1.0 if checked else 0.0
            self.update()

    def isChecked(self) -> bool:
        return self._checked

    # ── 事件 ──
    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self._pressed = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._pressed:
            self._pressed = False
            self.clicked.emit(self._index)
        self._pressed = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        w, h = rect.width(), rect.height()

        # ── 背景层 ──
        bg_color = self._mix_color(
            self._c_bg_hover if self._hovered else QColor(0, 0, 0, 0),
            self._c_bg_checked,
            self._anim_progress,
        )
        if bg_color.alpha() > 0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 18, 18)

        # ── 按压反馈 ──
        if self._pressed and not self._checked:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 18))
            painter.drawRoundedRect(rect.adjusted(4, 2, -4, -2), 18, 18)

        # ── 选中指示器 (左侧圆角条，渐进式出现) ──
        if self._anim_progress > 0.01:
            indicator_h = int(24 * self._anim_progress)
            ind_y = (h - indicator_h) // 2
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._c_indicator)
            path = QPainterPath()
            path.addRoundedRect(
                4, ind_y, 3, indicator_h, 1.5, 1.5
            )
            painter.drawPath(path)

        # ── 文字颜色 ──
        text_color = self._mix_color(
            self._c_text_inactive,
            self._c_text_active,
            self._anim_progress,
        )

        # ── 图标 (Material Design SVG Path) ──
        painter.save()
        painter.translate(rect.center().x() - 12, 14)
        painter.scale(1.0, 1.0)
        icon_path = QPainterPath()
        icon_path.addPath(self._svg_to_path(self._icon_path))
        painter.setPen(Qt.NoPen)
        painter.setBrush(text_color)
        painter.drawPath(icon_path)
        painter.restore()

        # ── 标签文字 ──
        label_font = QFont("Microsoft YaHei UI", 11)
        if self._anim_progress > 0.5:
            label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(text_color)
        painter.drawText(rect.adjusted(0, 34, 0, -6), Qt.AlignCenter, self._label)

        painter.end()

    @staticmethod
    def _svg_to_path(svg_d: str) -> QPainterPath:
        """解析 SVG path d 属性为 QPainterPath（支持 M/L/C/Z/H/V 命令）"""
        path = QPainterPath()
        try:
            import re
            # 正确的 SVG 数字拆分：每个数字可带符号、小数点和指数
            tokens = re.findall(
                r'[MmLlCcZzHhVvSsQqTtAa]|[-+]?\d*\.?\d+(?:[eE][-+]\d+)?',
                svg_d
            )
            i = 0
            cur = [0.0, 0.0]
            start = [0.0, 0.0]

            def n():
                nonlocal i
                i += 1
                return float(tokens[i - 1]) if i <= len(tokens) else 0.0

            def p():
                return n(), n()

            while i < len(tokens):
                cmd = tokens[i]; i += 1
                if cmd == 'M':
                    x, y = p(); path.moveTo(x, y); cur = [x, y]; start = [x, y]
                elif cmd == 'm':
                    x, y = p(); cur[0] += x; cur[1] += y
                    path.moveTo(cur[0], cur[1]); start = cur.copy()
                elif cmd in ('L', 'l'):
                    x, y = p()
                    if cmd == 'L': cur = [x, y]
                    else: cur[0] += x; cur[1] += y
                    path.lineTo(cur[0], cur[1])
                elif cmd in ('C', 'c'):
                    x1, y1 = p(); x2, y2 = p(); x, y = p()
                    if cmd == 'C':
                        c1, c2, end = [x1, y1], [x2, y2], [x, y]
                    else:
                        c1 = [cur[0] + x1, cur[1] + y1]
                        c2 = [cur[0] + x2, cur[1] + y2]
                        end = [cur[0] + x, cur[1] + y]
                    path.cubicTo(c1[0], c1[1], c2[0], c2[1], end[0], end[1])
                    cur = end
                elif cmd in ('Z', 'z'):
                    path.closeSubpath(); cur = start.copy()
                elif cmd in ('H', 'h'):
                    x = n()
                    if cmd == 'H': cur[0] = x
                    else: cur[0] += x
                    path.lineTo(cur[0], cur[1])
                elif cmd in ('V', 'v'):
                    y = n()
                    if cmd == 'V': cur[1] = y
                    else: cur[1] += y
                    path.lineTo(cur[0], cur[1])
        except Exception:
            # SVG 解析失败时返回一个空路径（图标不可见但不崩溃）
            pass
        return path

    @staticmethod
    def _mix_color(a: QColor, b: QColor, t: float) -> QColor:
        """线性插值两个 QColor"""
        t = max(0.0, min(1.0, t))
        return QColor(
            int(a.red() + (b.red() - a.red()) * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue() + (b.blue() - a.blue()) * t),
            int(a.alpha() + (b.alpha() - a.alpha()) * t),
        )


class MainWindow(QMainWindow):
    """MD3 主窗口 — 带过渡动画和系统托盘"""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._service = ArchiveService(config)
        self._scheduler = ArchiveScheduler(config_manager=config)

        # 页面切换动画追踪
        self._fade_anim = None
        self._quitting = False  # 从托盘退出时设为 True，跳过最小化逻辑

        self._init_ui()
        self._init_tray()
        self._init_scheduler()
        self._inject_log_callback()

    def _init_ui(self):
        self.setWindowTitle("FolderArchiveTool v1.0")
        self.setMinimumSize(1080, 700)
        self.resize(1280, 800)

        # ── 应用图标 ──
        app_icon = self._load_app_icon()
        if app_icon:
            self.setWindowIcon(app_icon)

        # ── 全局 QSS 样式表 ──
        qss = load_stylesheet("main.qss")
        if qss.strip():
            self.setStyleSheet(qss)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 左侧导航栏 ──
        nav = QWidget()
        nav.setObjectName("navRail")
        nav.setFixedWidth(120)
        # 用阴影增加深度
        nav_shadow = QGraphicsDropShadowEffect(nav)
        nav_shadow.setBlurRadius(12)
        nav_shadow.setXOffset(2)
        nav_shadow.setYOffset(0)
        nav_shadow.setColor(QColor(0, 0, 0, 30))
        nav.setGraphicsEffect(nav_shadow)

        nav.setStyleSheet(f"""
            QWidget#navRail {{
                background: {Colors.surface_container_low};
                border-right: 1px solid {Colors.outline_variant};
                border-radius: 0px;
            }}
        """)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(10, 24, 10, 16)
        nav_layout.setSpacing(2)

        # 顶部品牌区
        brand_frame = QFrame(nav)
        brand_frame.setFixedHeight(80)
        brand_layout = QVBoxLayout(brand_frame)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(2)

        brand_icon = QLabel("📦")
        brand_icon.setStyleSheet("font-size: 36px; background: transparent;")
        brand_icon.setAlignment(Qt.AlignCenter)
        brand_layout.addWidget(brand_icon)

        brand_name = QLabel("Archive")
        brand_name.setStyleSheet(f"""
            font-size: 12px; font-weight: 600;
            color: {Colors.primary}; background: transparent;
            letter-spacing: 1px;
        """)
        brand_name.setAlignment(Qt.AlignCenter)
        brand_layout.addWidget(brand_name)

        nav_layout.addWidget(brand_frame, alignment=Qt.AlignHCenter)
        nav_layout.addSpacing(12)

        # ── 分隔线 ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"""
            QFrame {{
                background: {Colors.outline_variant};
                border: none;
                max-height: 1px;
            }}
        """)
        nav_layout.addWidget(sep)
        nav_layout.addSpacing(8)

        # 导航按钮 & 页面
        self._nav_buttons = []
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {Colors.surface_bright};")

        nav_items = [
            ("archive", "归档", PageArchive),
            ("mail", "邮件", PageMail),
            ("schedule", "定时", PageSchedule),
            ("settings", "设置", PageSettings),
            ("description", "日志", PageLog),
        ]

        for idx, (icon_name, label, page_class) in enumerate(nav_items):
            btn = NavigationButton(icon_name, label, idx)
            btn.clicked.connect(self._switch_page)
            nav_layout.addWidget(btn, alignment=Qt.AlignHCenter)
            self._nav_buttons.append(btn)

            page = page_class(
                config=self._config,
                service=self._service,
                scheduler=self._scheduler,
            )
            self._stack.addWidget(page)

        nav_layout.addStretch()

        # 底部版本号
        version_frame = QFrame(nav)
        version_layout = QVBoxLayout(version_frame)
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_label = QLabel("v1.1")
        version_label.setStyleSheet(f"""
            color: {Colors.outline}; font-size: 11px;
            background: transparent; padding: 4px 0;
        """)
        version_label.setAlignment(Qt.AlignCenter)
        version_layout.addWidget(version_label)
        nav_layout.addWidget(version_frame, alignment=Qt.AlignHCenter)

        layout.addWidget(nav)

        # ── 右侧内容区 ──
        content = QWidget()
        content.setStyleSheet(f"background: {Colors.surface_bright};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._stack)
        layout.addWidget(content)

        # 默认选中第一个（无动画）
        self._nav_buttons[0].setChecked(True, animated=False)
        self._stack.setCurrentIndex(0)

    @staticmethod
    def _load_app_icon() -> QIcon:
        """加载应用图标，兼容开发模式和 PyInstaller 打包模式"""
        search = [
            Path("assets/icons/app_icon.ico"),
            Path(__file__).parent.parent / "assets" / "icons" / "app_icon.ico",
        ]
        if getattr(sys, "frozen", False):
            search.insert(0, Path(sys._MEIPASS) / "assets" / "icons" / "app_icon.ico")
        for p in search:
            if p.exists():
                return QIcon(str(p))
        return None

    def _switch_page(self, index: int):
        """切换页面 — 立即切换 + 轻量渐入"""
        if self._stack.currentIndex() == index:
            return

        # 停止上一轮动画并清理
        if self._fade_anim:
            self._fade_anim.stop()
            self._fade_anim = None

        old_widget = self._stack.currentWidget()
        if old_widget:
            old_widget.setGraphicsEffect(None)

        # 更新导航按钮
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index, animated=True)

        # 切换页面
        self._stack.setCurrentIndex(index)
        new_widget = self._stack.currentWidget()

        # 轻量渐入（仅首次动画）
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        effect = QGraphicsOpacityEffect(new_widget)
        effect.setOpacity(0.85)
        new_widget.setGraphicsEffect(effect)

        self._fade_anim = QPropertyAnimation(effect, b"opacity")
        self._fade_anim.setDuration(150)
        self._fade_anim.setStartValue(0.85)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.finished.connect(lambda: self._on_fade_done(new_widget))
        self._fade_anim.start()

    def _on_fade_done(self, widget):
        """动画完成后清理"""
        widget.setGraphicsEffect(None)
        if self._fade_anim:
            self._fade_anim = None

    def _init_tray(self):
        """系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self._tray = QSystemTrayIcon(self)
        tray_icon = self._load_app_icon()
        if tray_icon:
            self._tray.setIcon(tray_icon)
        else:
            self._tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self._tray.setToolTip("FolderArchiveTool - 月度文件归档")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(f"""
            QMenu {{
                background: {Colors.surface_container};
                border: 1px solid {Colors.outline_variant};
                border-radius: 12px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 28px;
                border-radius: 8px;
                font-size: 13px;
            }}
            QMenu::item:hover {{
                background: {Colors.surface_container_high};
            }}
            QMenu::separator {{
                height: 1px;
                background: {Colors.outline_variant};
                margin: 6px 12px;
            }}
        """)

        action_show = QAction("📂 显示主窗口", self)
        action_show.triggered.connect(self.show_normal)
        action_scan = QAction("🔍 快速扫描", self)
        action_scan.triggered.connect(lambda: self._service.scan_files())
        action_quit = QAction("🚪 退出", self)
        action_quit.triggered.connect(self._quit_application)

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
        self._scheduler.load_jobs()
        for page in self._pages:
            if hasattr(page, '_load_config'):
                page._load_config()
            if hasattr(page, '_refresh_jobs'):
                page._refresh_jobs()

    def _init_scheduler(self):
        self._scheduler.set_job_function(self._on_scheduled_run)
        self._scheduler.load_jobs()
        for page in self._pages:
            if hasattr(page, '_refresh_jobs'):
                page._refresh_jobs()
        if self._config.get("schedule.enabled", False):
            self._scheduler.start()

    def _inject_log_callback(self):
        """动态查找 PageLog 并连接日志回调"""
        for i in range(self._stack.count()):
            page = self._stack.widget(i)
            if isinstance(page, PageLog):
                set_ui_log_callback(page.on_log_message)
                return
        import logging
        logging.getLogger("FolderArchiveTool").warning("[UI] 未找到 PageLog 页面")

    def _on_scheduled_run(self):
        """定时任务触发（后台线程）"""
        self._service.run_full_archive(
            mode="auto",
            status_callback=lambda msg: None
        )

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.activateWindow()

    def _quit_application(self):
        """从托盘菜单退出 — 跳过最小化逻辑"""
        self._quitting = True
        self.close()

    def closeEvent(self, event):
        if self._quitting:
            self._scheduler.stop(timeout=15)
            set_ui_log_callback(None)
            if hasattr(self, "_tray"):
                self._tray.hide()
            event.accept()
            return

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
            self._scheduler.stop(timeout=15)
            set_ui_log_callback(None)
            event.accept()

    @property
    def _pages(self):
        """获取所有页面实例"""
        pages = []
        for i in range(self._stack.count()):
            pages.append(self._stack.widget(i))
        return pages
