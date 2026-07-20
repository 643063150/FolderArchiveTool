"""
开机自启管理模块
支持注册表 Run 键和任务计划程序两种方式
"""

import os
import sys
import ctypes
from pathlib import Path


class AutoStartManager:
    """开机自启管理器"""

    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "FolderArchiveTool"

    @staticmethod
    def _is_admin() -> bool:
        """检查是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def _get_app_path() -> str:
        """获取当前可执行文件路径"""
        if getattr(sys, "frozen", False):
            # PyInstaller 打包后
            return sys.executable
        else:
            # 开发模式：返回 pythonw + main.py
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            main_py = os.path.join(os.path.dirname(__file__), "..", "main.py")
            main_py = os.path.abspath(main_py)
            return f'"{pythonw}" "{main_py}"'

    def enable_auto_start(self) -> bool:
        """启用开机自启（写入注册表）"""
        try:
            import winreg
            app_path = self._get_app_path()
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, self.APP_NAME, 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def disable_auto_start(self) -> bool:
        """禁用开机自启（删除注册表项）"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.DeleteValue(key, self.APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return True  # 本来就不存在
        except Exception:
            return False

    def is_auto_start_enabled(self) -> bool:
        """检查是否已启用自启"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_READ,
            )
            winreg.QueryValueEx(key, self.APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def enable_with_task_scheduler(self, delay_minutes: int = 1) -> bool:
        """
        使用任务计划程序启用开机自启（支持延迟启动）
        需要管理员权限
        """
        if not self._is_admin():
            return False

        try:
            app_path = self._get_app_path()
            # 使用 schtasks 命令创建任务
            cmd = (
                f'schtasks /create /tn "{self.APP_NAME}" '
                f'/tr "{app_path}" '
                f'/sc onstart '
                f'/rl highest '
                f'/delay 000{delay_minutes}:00 '
                f'/f'
            )
            result = os.system(cmd)
            return result == 0
        except Exception:
            return False

    def disable_with_task_scheduler(self) -> bool:
        """使用任务计划程序禁用开机自启"""
        try:
            result = os.system(f'schtasks /delete /tn "{self.APP_NAME}" /f')
            return result == 0
        except Exception:
            return False
