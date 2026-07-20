"""
归档服务（Service 层）
整合 FileScanner → Archiver → Validator → FileCleaner → MailSender
提供完整的归档流程编排，UI 层通过回调获取进度
"""

import os
import time
from typing import Optional, Callable
from datetime import datetime

from .config_manager import ConfigManager
from .file_scanner import FileScanner
from .archiver import Archiver
from .validator import Validator
from .file_cleaner import FileCleaner
from .mail_sender import MailSender
from .logger_setup import get_logger


class ArchiveService:
    """
    归档服务 —— 编排完整归档流程

    流程: 扫描 → 压缩 → 校验 → 删除 → 邮件通知

    进度回调签名:
        progress_callback(stage, current, total, message)
        stage: 'scan' | 'archive' | 'validate' | 'clean' | 'mail' | 'complete'
    """

    def __init__(self, config_manager: ConfigManager = None):
        self._config = config_manager or ConfigManager()
        self._scanner = FileScanner(
            date_regex=self._config.get("general.date_regex")
        )
        self._archiver = Archiver()
        self._validator = Validator()
        self._cleaner = FileCleaner(
            use_recycle_bin=self._config.get("general.use_recycle_bin", False)
        )
        self._mail = MailSender(self._config)
        self._logger = get_logger()
        self._is_running = False
        self._last_result: dict = {}

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_result(self) -> dict:
        return self._last_result

    def scan_files(
        self,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """
        执行文件扫描

        Returns:
            {
                'success': bool,
                'groups': {date_key: [file_info, ...]},
                'total_files': int,
                'total_size': int,
            }
        """
        self._logger.info("开始扫描文件...")

        source_dir = self._config.get("general.source_dir", "")
        if not source_dir or not os.path.exists(source_dir):
            return {"success": False, "groups": {}, "total_files": 0, "total_size": 0, "error": "源目录不存在"}

        try:
            groups = self._scanner.scan(
                directory=source_dir,
                file_pattern=self._config.get("general.file_pattern", "*.*"),
                recursive=self._config.get("general.recursive", False),
                progress_callback=lambda cur, total, path: (
                    progress_callback("scan", cur, total, path)
                    if progress_callback else None
                ),
            )

            total_files = sum(len(v) for v in groups.values())
            total_size = sum(
                f["size"] for files in groups.values() for f in files
            )

            self._logger.info(f"扫描完成：{total_files} 个文件，{len(groups)} 个月份")
            return {
                "success": True,
                "groups": groups,
                "total_files": total_files,
                "total_size": total_size,
            }
        except Exception as e:
            self._logger.error(f"扫描失败: {e}")
            return {"success": False, "groups": {}, "total_files": 0, "total_size": 0, "error": str(e)}

    def run_full_archive(
        self,
        target_month: str = None,
        progress_callback: Optional[Callable] = None,
        status_callback: Optional[Callable] = None,
        mode: str = "manual",
    ) -> dict:
        """
        执行完整归档流程

        Args:
            target_month: 目标月份（如 '2026-07'），None 则归档所有未归档月份
            progress_callback: 进度回调(stage, current, total, message)
            status_callback: 状态回调(message) —— 用于显示当前阶段描述
            mode: 'manual' 手动执行 | 'auto' 定时任务自动执行

        Returns:
            {
                'success': bool,
                'archive_result': dict,
                'validator_result': dict,
                'clean_result': dict,
                'mail_result': dict,
                'duration_seconds': float,
            }
        """
        if self._is_running:
            return {"success": False, "error": "已有归档任务正在运行"}

        self._is_running = True
        start_time = time.time()
        mode_tag = "[自动]" if mode == "auto" else "[手动]"

        def notify(stage, cur, total, msg):
            if progress_callback:
                progress_callback(stage, cur, total, msg)

        def status(msg):
            self._logger.info(f"{mode_tag} {msg}")
            if status_callback:
                status_callback(msg)

        try:
            status(f"开始归档任务 (模式: {'定时自动' if mode == 'auto' else '手动'})")
            # ── 1. 扫描文件 ──────────────────────────────
            status("正在扫描文件...")
            scan_result = self.scan_files(
                progress_callback=lambda stage, cur, total, msg: notify(stage, cur, total, msg)
            )
            if not scan_result["success"]:
                return {"success": False, "error": scan_result.get("error", "扫描失败")}

            groups = scan_result["groups"]

            # 确定要归档的月份
            if target_month:
                if target_month not in groups:
                    return {"success": False, "error": f"月份 {target_month} 无文件"}
                months_to_archive = {target_month: groups[target_month]}
            else:
                # 过滤：排除当月 + 排除已归档的月份
                from datetime import datetime
                current_month = datetime.now().strftime("%Y-%m")
                output_dir = self._config.get("general.output_dir", "")
                months_to_archive = {}
                for month, files in groups.items():
                    if month == current_month:
                        status(f"跳过当月 {month}（数据可能不完整）")
                        continue
                    archive_name = f"archive_{month}.zip"
                    if os.path.exists(os.path.join(output_dir, archive_name)):
                        status(f"跳过已归档月份 {month}")
                        continue
                    months_to_archive[month] = files

            if not months_to_archive:
                status("没有需要归档的月份")
                return {"success": True, "message": "没有需要归档的月份"}

            # ── 2. 逐月归档 ──────────────────────────────
            all_archive_results = []
            all_clean_results = []
            all_validator_results = []

            for month, files in months_to_archive.items():
                status(f"正在归档 {month}（{len(files)} 个文件）...")

                # 压缩
                output_dir = self._config.get("general.output_dir", "")
                archive_result = self._archiver.create_archive(
                    file_list=files,
                    output_path=output_dir,
                    archive_name=f"archive_{month}",
                    compression_level=self._config.get("general.compression_level", 6),
                    progress_callback=lambda c, t, p, m=month: notify("archive", c, t, f"[{month}] {p}"),
                )
                all_archive_results.append(archive_result)

                if not archive_result["success"]:
                    error_msg = archive_result.get('error', '未知错误')
                    self._logger.error(f"{mode_tag} {month} 压缩失败: {error_msg}")
                    status(f"{month} 压缩失败: {error_msg}")
                    continue

                # 校验
                status(f"正在校验 {month} 的压缩包...")
                validator_result = self._validator.validate_archive(
                    archive_path=archive_result["archive_path"],
                    original_crc_map=archive_result["crc_map"],
                    original_file_list=files,
                )
                all_validator_results.append(validator_result)

                if not validator_result["valid"]:
                    errors = validator_result.get("errors", [])
                    error_detail = "; ".join(errors) if errors else "未知校验错误"
                    self._logger.error(f"{mode_tag} {month} 校验未通过: {error_detail}")
                    status(f"{month} 校验未通过: {error_detail}")
                    notify("validate", 0, 0, f"[{month}] 校验未通过")
                    continue

                notify("validate", 1, 1, f"[{month}] 校验通过")

                # 安全删除
                status(f"正在安全删除 {month} 的原文件...")
                clean_result = self._cleaner.safe_delete(
                    file_list=files,
                    validator_result=validator_result,
                    progress_callback=lambda c, t, p, m=month: notify("clean", c, t, f"[{month}] {p}"),
                )
                all_clean_results.append(clean_result)

                # 检查删除结果
                if clean_result.get("failed"):
                    failed_files = clean_result["failed"]
                    self._logger.error(f"{mode_tag} {month} 删除失败 {len(failed_files)} 个文件: {failed_files}")
                    status(f"{month} 删除失败 {len(failed_files)} 个文件")

            # ── 3. 发送通知邮件 ──────────────────────────
            status("正在发送通知邮件...")
            notify("mail", 0, 1, "正在发送...")

            # 汇总结果
            combined_archive = {
                "success": all(r["success"] for r in all_archive_results) if all_archive_results else False,
                "archive_path": "; ".join(r.get("archive_path", "") for r in all_archive_results),
                "file_count": sum(r.get("file_count", 0) for r in all_archive_results),
                "total_size": sum(r.get("total_size", 0) for r in all_archive_results),
                "archive_size": sum(r.get("archive_size", 0) for r in all_archive_results),
                "duration_seconds": sum(r.get("duration_seconds", 0) for r in all_archive_results),
            }
            combined_clean = {
                "deleted": [f for r in all_clean_results for f in r.get("deleted", [])],
                "failed": [f for r in all_clean_results for f in r.get("failed", [])],
                "skipped": [f for r in all_clean_results for f in r.get("skipped", [])],
            }
            combined_validator = {
                "valid": all(r.get("valid", False) for r in all_validator_results),
                "details": {
                    "crc_match_count": sum(
                        r.get("details", {}).get("crc_match_count", 0)
                        for r in all_validator_results
                    ),
                },
            }

            mail_result = {"success": [], "failed": []}
            if self._config.get("mail.enabled", False):
                subject = f"归档报告 - {datetime.now().strftime('%Y-%m-%d')}"
                body = self._mail.build_archive_report(
                    combined_archive, combined_clean, combined_validator
                )
                mail_result = self._mail.send_notification(subject, body)

            notify("mail", 1, 1, "发送完成")
            notify("complete", 1, 1, "归档任务完成")

            duration = round(time.time() - start_time, 2)

            # 汇总错误信息
            error_months = [r for r in all_archive_results if not r["success"]]
            failed_validations = [v for v in all_validator_results if not v["valid"]]
            total_deleted = len(combined_clean["deleted"])
            total_failed_delete = len(combined_clean["failed"])

            if error_months or failed_validations or total_failed_delete > 0:
                self._logger.warning(
                    f"{mode_tag} 归档完成但有错误: "
                    f"压缩失败{len(error_months)}个月, "
                    f"校验失败{len(failed_validations)}个月, "
                    f"删除失败{total_failed_delete}个文件"
                )

            status(f"归档任务完成，耗时 {duration} 秒，删除 {total_deleted} 个文件，模式: {'定时自动' if mode == 'auto' else '手动'}")

            result = {
                "success": len(error_months) == 0 and len(failed_validations) == 0,
                "archive_result": combined_archive,
                "validator_result": combined_validator,
                "clean_result": combined_clean,
                "mail_result": mail_result,
                "duration_seconds": duration,
            }
            self._last_result = result
            return result

        except Exception as e:
            self._logger.error(f"{mode_tag} 归档任务异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

        finally:
            self._is_running = False

    def run_archive_for_month(
        self,
        year: int,
        month: int,
        progress_callback: Optional[Callable] = None,
        status_callback: Optional[Callable] = None,
    ) -> dict:
        """归档指定年月的便捷方法"""
        target = f"{year:04d}-{month:02d}"
        return self.run_full_archive(target, progress_callback, status_callback)
