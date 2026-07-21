"""
Windows 服务模块
使用 sc.exe 注册为系统服务，防止被手动关闭

使用方法:
    python core/windows_service.py install     # 安装服务
    python core/windows_service.py remove      # 移除服务
    python core/windows_service.py start       # 启动服务
    python core/windows_service.py stop        # 停止服务
"""

import os
import sys
import subprocess
import logging

# 确保工作目录是项目根目录
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("FolderArchiveTool")

SERVICE_NAME = "FolderArchiveTool"


def get_script_path():
    """获取当前脚本绝对路径"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(__file__)


def get_python_exe():
    """获取 Python 解释器路径"""
    return sys.executable


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


def install_service():
    """安装 Windows 服务（使用 sc.exe）"""
    import traceback
    python_exe = get_python_exe()
    script_path = get_script_path()

    print(f"[DEBUG] Python: {python_exe}")
    print(f"[DEBUG] Script: {script_path}")
    print(f"[DEBUG] Frozen: {getattr(sys, 'frozen', False)}")

    # 构建服务 binPath
    if getattr(sys, "frozen", False):
        bin_path = f'"{script_path}"'
    else:
        bin_path = f'"{python_exe}" "{script_path}"'

    print(f"[DEBUG] binPath: {bin_path}")

    try:
        # 先检查是否已存在
        check = subprocess.run(
            ["sc", "query", SERVICE_NAME],
            capture_output=True, text=True, timeout=10
        )
        print(f"[DEBUG] sc query stdout: {check.stdout}")
        print(f"[DEBUG] sc query stderr: {check.stderr}")
        print(f"[DEBUG] sc query returncode: {check.returncode}")

        if check.returncode == 0 and SERVICE_NAME in check.stdout:
            print("[INFO] 服务已存在，先删除旧服务...")
            subprocess.run(["sc", "stop", SERVICE_NAME],
                           capture_output=True, text=True, timeout=30)
            subprocess.run(["sc", "delete", SERVICE_NAME],
                           capture_output=True, text=True, timeout=30)

        # 创建服务
        cmd = ["sc", "create", SERVICE_NAME,
               "binPath=", bin_path,
               "start=", "auto",
               "DisplayName=", "FolderArchiveTool - 月度文件归档服务"]
        print(f"[DEBUG] 执行命令: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        print(f"[DEBUG] sc create stdout: {result.stdout}")
        print(f"[DEBUG] sc create stderr: {result.stderr}")
        print(f"[DEBUG] sc create returncode: {result.returncode}")

        if result.returncode == 0 or "已存在" in result.stdout:
            # 设置服务描述
            desc_result = subprocess.run(
                ["sc", "description", SERVICE_NAME,
                 "按月压缩归档日期格式文件，支持定时任务和邮件通知"],
                capture_output=True, text=True, timeout=10
            )
            print(f"[DEBUG] sc description returncode: {desc_result.returncode}")

            # 配置失败操作（服务崩溃时自动重启）
            fail_result = subprocess.run(
                ["sc", "failure", SERVICE_NAME,
                 "reset=", "0",
                 "actions=", "restart/60000/restart/60000/restart/60000"],
                capture_output=True, text=True, timeout=10
            )
            print(f"[DEBUG] sc failure returncode: {fail_result.returncode}")

            print("[OK] 系统服务注册成功！")
            print(f"服务名称: {SERVICE_NAME}")
            print("可通过 'services.msc' 管理")
        else:
            print(f"[FAIL] 服务注册失败")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            print(f"  returncode: {result.returncode}")
            print("请确保以管理员身份运行")
    except Exception as e:
        print(f"[FAIL] 服务注册异常: {e}")
        traceback.print_exc()


def remove_service():
    """移除 Windows 服务"""
    try:
        # 先停止服务
        subprocess.run(["sc", "stop", SERVICE_NAME],
                       capture_output=True, text=True, timeout=30)
        # 删除服务
        result = subprocess.run(
            ["sc", "delete", SERVICE_NAME],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("[OK] 系统服务已移除")
        else:
            print(f"[FAIL] 移除失败: {result.stdout} {result.stderr}")
    except Exception as e:
        print(f"[FAIL] 移除失败: {e}")


def start_service():
    """启动服务"""
    try:
        result = subprocess.run(
            ["sc", "start", SERVICE_NAME],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("[OK] 服务已启动")
        else:
            print(f"[FAIL] 启动失败: {result.stdout} {result.stderr}")
    except Exception as e:
        print(f"[FAIL] 启动失败: {e}")


def stop_service():
    """停止服务"""
    try:
        result = subprocess.run(
            ["sc", "stop", SERVICE_NAME],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("[OK] 服务已停止")
        else:
            print(f"[FAIL] 停止失败: {result.stdout} {result.stderr}")
    except Exception as e:
        print(f"[FAIL] 停止失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "debug":
            # 调试模式（前台运行调度器）
            print("调试模式 - 运行调度器（按 Ctrl+C 停止）...")
            try:
                run_scheduler()
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                print("已停止")
        elif cmd == "install":
            install_service()
        elif cmd == "remove":
            remove_service()
        elif cmd == "start":
            start_service()
        elif cmd == "stop":
            stop_service()
        else:
            print(f"未知命令: {cmd}")
            print("可用: install, remove, start, stop, debug")
    else:
        print("Windows 服务管理")
        print("用法: python core/windows_service.py <install|remove|start|stop|debug>")
