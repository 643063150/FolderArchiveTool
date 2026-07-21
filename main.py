"""
FolderArchiveTool 程序入口
使用 QMaterialWidgets Material Design 3 组件库
"""

import sys
import os
import ctypes
import traceback

# 确保工作目录是 exe 所在目录（UAC 提升后工作目录会变成 System32）
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 再次确认（防止 UAC 提升后工作目录变化）
exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
if os.path.exists(exe_dir):
    os.chdir(exe_dir)


def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin():
    """请求管理员权限（UAC 弹窗）"""
    if not is_admin():
        # 以管理员身份重新运行
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)


def run_service_mode():
    """服务模式运行（无 GUI）"""
    from core.config_manager import ConfigManager
    from core.archive_service import ArchiveService
    from core.scheduler import ArchiveScheduler
    from core.logger_setup import setup_logger

    log = setup_logger()
    log.info("[服务] FolderArchiveTool 服务模式启动")

    config = ConfigManager()
    service = ArchiveService(config)
    scheduler = ArchiveScheduler(config_manager=config)
    scheduler.set_job_function(lambda: service.run_full_archive(mode="auto"))
    scheduler.load_jobs()

    if config.get("schedule.enabled", False):
        scheduler.start()
        log.info("[服务] 调度器已启动，服务运行中...")
        # 保持运行
        import time
        while True:
            time.sleep(10)
    else:
        log.info("[服务] 调度器未启用，服务空闲")


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


def ensure_single_instance():
    """确保只运行一个实例。返回 True 表示是第一个实例"""
    import ctypes
    mutex_name = "Global\\FolderArchiveTool_SingleInstance_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()

    if last_error == 183:  # ERROR_ALREADY_EXISTS — 已有实例
        # 尝试找到已有窗口并激活
        try:
            import ctypes.windll.user32 as user32
            hwnd = user32.FindWindowW(None, "FolderArchiveTool v1.0")
            if hwnd:
                # 还原窗口（如果最小化）
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        return False
    return True


if __name__ == "__main__":
    # 检查是否作为服务运行（带 /SERVICE 参数）
    if "/SERVICE" in sys.argv or "--service" in sys.argv:
        run_service_mode()
        sys.exit(0)

    # 单实例检查
    if not ensure_single_instance():
        print("FolderArchiveTool 已在运行，已激活已有窗口。")
        sys.exit(0)
    # 请求管理员权限（注册/移除系统服务需要）
    request_admin()
    main()
