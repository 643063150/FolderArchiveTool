"""
Windows 服务模块
使用 pywin32 注册为系统服务，防止被手动关闭

使用方法:
    python core/windows_service.py install     # 安装服务
    python core/windows_service.py remove      # 移除服务
    python core/windows_service.py start       # 启动服务
    python core/windows_service.py stop        # 停止服务
    python core/windows_service.py debug       # 调试模式运行
"""

import os
import sys
import time
import logging

# 确保工作目录是项目根目录
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("FolderArchiveTool")


def run_scheduler():
    """运行调度器（服务模式，无 GUI）"""
    from core.config_manager import ConfigManager
    from core.archive_service import ArchiveService
    from core.scheduler import ArchiveScheduler
    from core.logger_setup import setup_logger

    log = setup_logger()
    log.info("[服务] FolderArchiveTool 服务启动")

    config = ConfigManager()
    service = ArchiveService(config)
    scheduler = ArchiveScheduler(config_manager=config)
    scheduler.set_job_function(lambda: service.run_full_archive(mode="auto"))
    scheduler.load_jobs()

    if config.get("schedule.enabled", False):
        scheduler.start()
        log.info("[服务] 调度器已启动")
    else:
        log.info("[服务] 调度器未启用")

    return scheduler


try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    class FolderArchiveToolService(win32serviceutil.ServiceFramework):
        _svc_name_ = "FolderArchiveTool"
        _svc_display_name_ = "FolderArchiveTool - 月度文件归档服务"
        _svc_description_ = "按月压缩归档日期格式文件，支持定时任务和邮件通知"

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.scheduler = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.scheduler:
                self.scheduler.stop()

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, "")
            )
            self.main()

        def main(self):
            try:
                self.scheduler = run_scheduler()
                # 等待停止信号
                while True:
                    rc = win32event.WaitForSingleObject(self.stop_event, 5000)
                    if rc == win32event.WAIT_OBJECT_0:
                        break
            except Exception as e:
                logger.error(f"[服务] 服务异常: {e}", exc_info=True)

    def install_service():
        """安装 Windows 服务"""
        try:
            win32serviceutil.HandleCommandLine(FolderArchiveToolService, argv=["", "install"])
            print("✅ 服务安装成功！")
            print("服务名称: FolderArchiveTool")
            print("可通过 'services.msc' 管理，或执行:")
            print("  python core/windows_service.py start   # 启动")
            print("  python core/windows_service.py stop    # 停止")
        except Exception as e:
            print(f"❌ 服务安装失败: {e}")

except ImportError:
    def install_service():
        print("❌ 未安装 pywin32，无法注册 Windows 服务")
        print("请执行: pip install pywin32")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "debug":
            # 调试模式
            scheduler = run_scheduler()
            print("按 Ctrl+C 停止...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                scheduler.stop()
                print("服务已停止")
        elif cmd == "install":
            install_service()
        elif cmd in ("remove", "stop", "start"):
            try:
                win32serviceutil.HandleCommandLine(FolderArchiveToolService, argv=["", cmd])
            except Exception as e:
                print(f"操作失败: {e}")
        else:
            print(f"未知命令: {cmd}")
            print("可用: install, remove, start, stop, debug")
    else:
        # 默认进入调试模式
        scheduler = run_scheduler()
        print("按 Ctrl+C 停止...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            print("服务已停止")
