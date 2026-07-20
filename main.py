"""
FolderArchiveTool 程序入口
使用 QMaterialWidgets Material Design 3 组件库
"""

import sys
import os
import traceback

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    # ── 初始化配置 ──────────────────────────────────
    from core.config_manager import ConfigManager
    config = ConfigManager()

    # ── 初始化日志 ──────────────────────────────────
    from core.logger_setup import setup_logger, init_log_emitter
    logger = setup_logger(
        level=config.get("log.level", "INFO"),
        max_file_size_mb=config.get("log.max_file_size_mb", 10),
        backup_count=config.get("log.backup_count", 5),
    )
    logger.info("=" * 50)
    logger.info("FolderArchiveTool 启动")
    logger.info(f"工作目录: {os.getcwd()}")

    # ── 启动 Qt 应用 ────────────────────────────────
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)

        # 初始化日志信号发射器（必须在主线程、QApplication 创建后）
        init_log_emitter()

        # 设置 Material Design 主题
        from qmaterialwidgets import setTheme, Theme
        setTheme(Theme.LIGHT)

        app.setApplicationName("FolderArchiveTool")
        app.setApplicationVersion("1.0.0")

        # ── 创建主窗口 ──────────────────────────────
        from ui.main_window import MainWindow
        window = MainWindow(config=config)
        window.show()

        logger.info("主窗口已创建")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"启动失败: {e}")
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
