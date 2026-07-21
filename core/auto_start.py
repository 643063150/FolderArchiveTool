"""
开机自启管理模块
支持：注册表 Run 键、任务计划程序（推荐）
"""

import os
import sys
import ctypes
import subprocess
import logging

logger = logging.getLogger("FolderArchiveTool")


class AutoStartManager:
    """开机自启管理器"""

    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "FolderArchiveTool"

    # ── 注册表方式（普通权限） ─────────────────────────

    def enable_registry(self) -> bool:
        """启用开机自启（注册表方式）"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH, 0, winreg.KEY_SET_VALUE
            )
            app_path = self._get_app_path()
            winreg.SetValueEx(key, self.APP_NAME, 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
            logger.info(f"[自启] 注册表方式已启用: {app_path}")
            return True
        except Exception as e:
            logger.error(f"[自启] 注册表方式启用失败: {e}", exc_info=True)
            return False

    def disable_registry(self) -> bool:
        """禁用开机自启（注册表方式）"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH, 0, winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, self.APP_NAME)
            winreg.CloseKey(key)
            logger.info("[自启] 注册表方式已禁用")
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.error(f"[自启] 注册表方式禁用失败: {e}", exc_info=True)
            return False

    def is_registry_enabled(self) -> bool:
        """检查注册表方式是否启用"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH, 0, winreg.KEY_READ
            )
            winreg.QueryValueEx(key, self.APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    # ── 任务计划程序方式（推荐） ──────────

    def enable_task_scheduler(self) -> bool:
        """
        启用开机自启（任务计划程序方式）
        使用 runas 申请管理员权限创建任务
        """
        try:
            app_path = self._get_app_path()
            logger.info(f"[自启] 尝试创建任务计划程序，exe路径: {app_path}")

            # 创建 XML 任务定义
            xml_content = self._get_task_xml(app_path)

            # 写入临时 XML 文件
            xml_path = os.path.join(os.getenv("TEMP"), "FolderArchiveTool_task.xml")
            with open(xml_path, "w", encoding="utf-16") as f:
                f.write(xml_content)
            logger.info(f"[自启] 任务XML已写入: {xml_path}")

            # 使用powershell Start-Process runas 创建任务（等待完成）
            ps_cmd = (
                f"Start-Process schtasks -ArgumentList "
                f"'/create','/tn','{self.APP_NAME}','/xml','\"{xml_path}\"','/f' "
                f"-Verb RunAs -Wait -WindowStyle Hidden; "
                f"if ($LASTEXITCODE -eq 0) {{ Write-Host 'SUCCESS' }} else {{ Write-Host \"FAILED:$LASTEXITCODE\" }}"
            )

            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=60
            )

            logger.info(f"[自启] schtasks stdout: {result.stdout.strip()}")
            logger.info(f"[自启] schtasks stderr: {result.stderr.strip()}")
            logger.info(f"[自启] schtasks returncode: {result.returncode}")

            # 清理临时文件
            try:
                os.remove(xml_path)
            except Exception:
                pass

            # 验证是否创建成功
            if "SUCCESS" in result.stdout:
                logger.info("[自启] 任务计划程序创建成功")
                return True
            else:
                logger.error("[自启] 任务计划程序创建失败")
                return False

        except subprocess.TimeoutExpired:
            logger.error("[自启] 任务计划程序创建超时（用户可能拒绝了UAC）")
            return False
        except Exception as e:
            logger.error(f"[自启] 任务计划程序创建异常: {e}", exc_info=True)
            return False

    def disable_task_scheduler(self) -> bool:
        """禁用任务计划程序方式"""
        try:
            result = subprocess.run(
                ["schtasks", "/delete", "/tn", self.APP_NAME, "/f"],
                capture_output=True, text=True, timeout=30
            )
            logger.info(f"[自启] 删除任务 returncode: {result.returncode}")
            return result.returncode == 0
        except Exception as e:
            logger.error(f"[自启] 删除任务失败: {e}", exc_info=True)
            return False

    def is_task_scheduler_enabled(self) -> bool:
        """检查任务计划程序方式是否启用"""
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", self.APP_NAME],
                capture_output=True, text=True, timeout=10
            )
            enabled = result.returncode == 0
            logger.debug(f"[自启] 任务计划程序状态: {'存在' if enabled else '不存在'}")
            return enabled
        except Exception as e:
            logger.error(f"[自启] 查询任务状态失败: {e}", exc_info=True)
            return False

    # ── 工具方法 ─────────────────────────────────────

    @staticmethod
    def _get_app_path() -> str:
        """获取当前可执行文件路径"""
        if getattr(sys, "frozen", False):
            return sys.executable
        else:
            # 开发模式：返回 pythonw + main.py（无控制台窗口）
            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            main_py = os.path.join(os.path.dirname(__file__), "..", "main.py")
            main_py = os.path.abspath(main_py)
            return f'"{pythonw}" "{main_py}"'

    @staticmethod
    def _get_task_xml(app_path: str) -> str:
        """生成任务计划程序 XML 定义"""
        return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FolderArchiveTool 月度文件归档工具自动启动</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{app_path}</Command>
    </Exec>
  </Actions>
</Task>"""
