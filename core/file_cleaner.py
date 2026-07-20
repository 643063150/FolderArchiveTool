"""
安全删除模块
校验通过后的安全删除，支持回收站模式和备份模式
"""

import os
import shutil
import time
from pathlib import Path
from typing import Optional, Callable


class FileCleaner:
    """安全文件删除器"""

    def __init__(self, use_recycle_bin: bool = False):
        """
        Args:
            use_recycle_bin: 是否使用回收站（需要 pywin32）
        """
        self._use_recycle_bin = use_recycle_bin
        self._shell = None

        if use_recycle_bin:
            try:
                import win32com.client
                self._shell = win32com.client.Dispatch("Shell.Application")
            except Exception:
                self._shell = None

    def safe_delete(
        self,
        file_list: list,
        validator_result: dict,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """
        安全删除：仅删除校验通过的文件

        Args:
            file_list: 文件信息列表
            validator_result: Validator.validate_archive 的返回值
            progress_callback: 进度回调(current, total, filename)

        Returns:
            {
                'deleted': [str, ...],
                'failed': [(str, str), ...],  # (path, error)
                'skipped': [str, ...],
            }
        """
        result = {"deleted": [], "failed": [], "skipped": []}

        if not validator_result.get("valid", False):
            # 校验未通过，全部跳过
            result["skipped"] = [f["path"] for f in file_list]
            return result

        total = len(file_list)
        for idx, file_info in enumerate(file_list):
            filepath = file_info["path"]

            try:
                if os.path.exists(filepath):
                    if self._use_recycle_bin and self._shell:
                        self._move_to_recycle_bin(filepath)
                    else:
                        os.remove(filepath)
                    result["deleted"].append(filepath)
                else:
                    result["skipped"].append(filepath)
            except Exception as e:
                result["failed"].append((filepath, str(e)))

            if progress_callback:
                progress_callback(idx + 1, total, file_info["name"])

        return result

    def safe_delete_with_backup(
        self,
        file_list: list,
        backup_dir: str,
        validator_result: dict,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """
        保险模式：先复制到备份目录，再删除原文件

        Args:
            file_list: 文件信息列表
            backup_dir: 备份目录
            validator_result: 校验结果
            progress_callback: 进度回调

        Returns:
            同 safe_delete，额外返回 'backup_dir'
        """
        result = self.safe_delete(file_list, validator_result, progress_callback)
        result["backup_dir"] = ""

        if not validator_result.get("valid", False):
            return result

        # 复制到备份目录
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_subdir = os.path.join(backup_dir, f"backup_{timestamp}")
            os.makedirs(backup_subdir, exist_ok=True)

            for file_info in file_list:
                src = file_info["path"]
                dst = os.path.join(backup_subdir, file_info["name"])
                if os.path.exists(src):
                    try:
                        shutil.copy2(src, dst)
                    except Exception:
                        pass

            result["backup_dir"] = backup_subdir

        return result

    def _move_to_recycle_bin(self, filepath: str):
        """使用 Windows API 移入回收站"""
        if self._shell:
            folder = self._shell.NameSpace(0)
            item = folder.ParseName(filepath)
            if item:
                item.InvokeVerb("delete")
            else:
                os.remove(filepath)
        else:
            os.remove(filepath)

    def cleanup_old_backups(self, backup_dir: str, keep_days: int = 7):
        """清理超过保留天数的备份"""
        if not os.path.exists(backup_dir):
            return

        cutoff = time.time() - keep_days * 86400
        backup_path = Path(backup_dir)

        for item in backup_path.iterdir():
            if item.is_dir() and item.stat().st_mtime < cutoff:
                try:
                    shutil.rmtree(item)
                except Exception:
                    pass
