"""
定时任务调度模块
基于 APScheduler，支持 cron 表达式
"""

import uuid
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError


class ArchiveScheduler:
    """归档任务调度器"""

    def __init__(self, config_manager=None):
        self._scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,          # 合并错过的触发，只执行一次
                'max_instances': 1,         # 单实例
                'misfire_grace_time': 3600  # 1小时内的 misfire 可容忍
            }
        )
        self._job_func: Optional[Callable] = None
        self._config = config_manager
        self._is_triggering = False

    def set_job_function(self, func: Callable):
        """设置任务执行函数"""
        self._job_func = func
        import logging
        logging.getLogger("FolderArchiveTool").info("[定时] 任务执行函数已设置")

    def _save_jobs(self):
        """持久化任务到配置文件"""
        if not self._config:
            return
        jobs = []
        for job in self._scheduler.get_jobs():
            trigger_str = str(job.trigger)
            cron_expr = self._extract_cron_from_trigger(trigger_str)
            job_type = self._detect_job_type(job)
            jobs.append({
                "id": job.id,
                "name": job.name,
                "trigger": trigger_str,
                "cron": cron_expr,
                "job_type": job_type,
            })
        self._config.set("schedule.jobs", jobs)
        self._config.save()

    @staticmethod
    def _detect_job_type(job) -> str:
        """检测任务类型"""
        trigger_str = str(job.trigger)
        name = job.name or ""
        if "每月归档" in name:
            return "monthly"
        elif "每周归档" in name:
            return "weekly"
        elif "每天归档" in name:
            return "daily"
        else:
            return "custom"

    @staticmethod
    def _extract_cron_from_trigger(trigger_str: str) -> str:
        """从 trigger 字符串提取 cron 表达式"""
        try:
            if "cron[" not in trigger_str:
                return ""
            inner = trigger_str.split("cron[")[1].rstrip("]")
            parts = {}
            for kv in inner.split(", "):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    parts[k.strip()] = v.strip("'\"")
            minute = parts.get("minute", "0")
            hour = parts.get("hour", "0")
            day = parts.get("day", "*")
            month = parts.get("month", "*")
            dow = parts.get("day_of_week", "*")
            return f"{minute} {hour} {day} {month} {dow}"
        except Exception:
            return ""

    def load_jobs(self):
        """从配置文件恢复任务（不清除已有任务，同名替换）"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        if not self._config:
            return
        jobs = self._config.get("schedule.jobs", [])
        loaded = 0
        for job_info in jobs:
            try:
                job_id = job_info.get("id", "")
                name = job_info.get("name", "")
                cron_expr = job_info.get("cron", "")
                job_type = job_info.get("job_type", "")

                if not cron_expr:
                    logger.warning(f"[定时] 任务 {job_id} 缺少 cron 表达式，跳过")
                    continue

                if not job_type:
                    job_type = self._infer_job_type(cron_expr)

                parts = cron_expr.split()
                if job_type == "monthly" and len(parts) >= 3:
                    self.add_monthly_job(day=int(parts[2]), hour=int(parts[1]), minute=int(parts[0]), job_id=job_id, save=False)
                elif job_type == "weekly" and len(parts) >= 5:
                    dow_map = {"sun": "sun", "mon": "mon", "tue": "tue", "wed": "wed", "thu": "thu", "fri": "fri", "sat": "sat"}
                    dow = dow_map.get(parts[4], parts[4])
                    self.add_weekly_job(day_of_week=dow, hour=int(parts[1]), minute=int(parts[0]), job_id=job_id, save=False)
                elif job_type == "daily" and len(parts) >= 2:
                    self.add_custom_cron(f"{parts[0]} {parts[1]} * * *", job_id=job_id, save=False)
                else:
                    self.add_custom_cron(cron_expr, job_id=job_id, save=False)

                loaded += 1
            except Exception as e:
                logger.warning(f"[定时] 恢复任务失败: {e}", exc_info=True)
        if loaded > 0:
            logger.info(f"[定时] 从配置恢复了 {loaded} 个定时任务")

    @staticmethod
    def _infer_job_type(cron_expr: str) -> str:
        """从 cron 表达式推断任务类型"""
        parts = cron_expr.split()
        if len(parts) != 5:
            return "custom"
        minute, hour, day, month, dow = parts
        if day != "*" and month == "*" and dow == "*":
            return "monthly"
        if dow != "*" and day == "*" and month == "*":
            return "weekly"
        if day == "*" and month == "*" and dow == "*":
            return "daily"
        return "custom"

    def add_monthly_job(self, day: int = 1, hour: int = 2, minute: int = 0, job_id: str = None, save: bool = True) -> str:
        """添加每月定时任务"""
        import logging
        if not job_id:
            job_id = f"monthly_{uuid.uuid4().hex[:8]}"
        trigger = CronTrigger(day=day, hour=hour, minute=minute)
        self._scheduler.add_job(
            self._execute_job,
            trigger=trigger,
            id=job_id,
            name=f"每月归档({day}日 {hour:02d}:{minute:02d})",
            replace_existing=True,
        )
        if save:
            self._save_jobs()
            logging.getLogger("FolderArchiveTool").info(f"[定时] 添加每月任务: {day}日 {hour:02d}:{minute:02d}, ID={job_id}")
        return job_id

    def add_weekly_job(self, day_of_week: str = "sun", hour: int = 3, minute: int = 0, job_id: str = None, save: bool = True) -> str:
        """添加每周定时任务"""
        import logging
        if not job_id:
            job_id = f"weekly_{uuid.uuid4().hex[:8]}"
        trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
        self._scheduler.add_job(
            self._execute_job,
            trigger=trigger,
            id=job_id,
            name=f"每周归档({day_of_week} {hour:02d}:{minute:02d})",
            replace_existing=True,
        )
        if save:
            self._save_jobs()
            logging.getLogger("FolderArchiveTool").info(f"[定时] 添加每周任务: {day_of_week} {hour:02d}:{minute:02d}, ID={job_id}")
        return job_id

    def add_custom_cron(self, cron_expr: str, job_id: str = None, save: bool = True) -> str:
        """添加自定义 cron 任务"""
        if not job_id:
            job_id = f"custom_{uuid.uuid4().hex[:8]}"
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError("cron 表达式必须包含 5 个字段: 分 时 日 月 周")
        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)
        self._scheduler.add_job(
            self._execute_job,
            trigger=trigger,
            id=job_id,
            name=f"自定义({cron_expr})",
            replace_existing=True,
        )
        if save:
            self._save_jobs()
            import logging
            logging.getLogger("FolderArchiveTool").info(f"[定时] 添加自定义任务: {cron_expr}, ID={job_id}")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        try:
            self._scheduler.remove_job(job_id)
            self._save_jobs()
            logger.info(f"[定时] 移除任务: {job_id}")
            return True
        except JobLookupError:
            logger.warning(f"[定时] 移除任务失败（未找到）: {job_id}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"[定时] 暂停任务: {job_id}")
            return True
        except JobLookupError:
            logger.warning(f"[定时] 暂停任务失败（未找到）: {job_id}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"[定时] 恢复任务: {job_id}")
            return True
        except JobLookupError:
            logger.warning(f"[定时] 恢复任务失败（未找到）: {job_id}")
            return False

    def list_jobs(self) -> list:
        """列出所有任务 — 优先从运行中的调度器读取，否则从配置文件读取"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")

        # 如果调度器在运行，从 APScheduler 读取
        if self._scheduler.running:
            return self._list_live_jobs()

        # 调度器未运行，从配置文件读取
        return self._list_config_jobs()

    def _list_live_jobs(self) -> list:
        """从 APScheduler 实时读取任务列表"""
        jobs = []
        for job in self._scheduler.get_jobs():
            next_run = "未调度"
            try:
                nrt = getattr(job, 'next_run_time', None)
                if nrt:
                    try:
                        next_run = nrt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        next_run = str(nrt)
                else:
                    next_run = "未调度"
            except Exception:
                next_run = "未知"
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run,
                "trigger": str(job.trigger),
            })
        return jobs

    def _list_config_jobs(self) -> list:
        """从配置文件读取任务列表（调度器未运行时）"""
        if not self._config:
            return []
        jobs_config = self._config.get("schedule.jobs", [])
        result = []
        for j in jobs_config:
            result.append({
                "id": j.get("id", ""),
                "name": j.get("name", "未命名任务"),
                "next_run": "调度器未运行",
                "trigger": j.get("cron", ""),
            })
        return result

    def start(self):
        """启动调度器 — 确保任务已加载"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        if not self._scheduler.running:
            # 启动前先加载任务
            self.load_jobs()
            self._scheduler.start()
            logger.info("[定时] 调度器已启动")
            for job in self._scheduler.get_jobs():
                nrt = getattr(job, 'next_run_time', None)
                logger.info(f"[定时] 已调度任务: {job.name}, 下次执行: {nrt}")
        else:
            logger.info("[定时] 调度器已在运行中")

    def stop(self, timeout=10):
        """安全停止调度器（等待运行中任务完成）"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("[定时] 调度器已停止（任务配置已持久化）")

    def is_running(self) -> bool:
        """调度器是否运行中"""
        return self._scheduler.running

    def trigger_now(self):
        """立即触发一次任务"""
        import threading
        import logging
        logger = logging.getLogger("FolderArchiveTool")

        if self._is_triggering:
            logger.info("[定时] 已有正在执行的任务，跳过")
            return
        self._is_triggering = True
        logger.info("[定时] 手动触发立即执行")

        def _safe_run():
            try:
                if self._job_func:
                    self._job_func()
            except Exception as e:
                logger.error(f"[定时] 立即执行失败: {e}", exc_info=True)
            finally:
                self._is_triggering = False

        t = threading.Thread(target=_safe_run, daemon=True)
        t.start()

    def _execute_job(self):
        """内部执行任务"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        logger.info("[定时] 定时任务触发，开始执行归档...")
        if self._job_func:
            try:
                self._job_func()
                logger.info("[定时] 定时任务执行完成")
            except Exception as e:
                logger.error(f"[定时] 定时任务执行失败: {e}", exc_info=True)
        else:
            logger.error("[定时] 定时任务失败: _job_func 未设置！")
