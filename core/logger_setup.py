"""
日志配置模块
支持：文件日志 + 控制台日志 + UI 回调日志
关键：使用 pyqtSignal 实现线程安全的跨线程日志投递
"""

import os
import logging
import threading
from logging.handlers import RotatingFileHandler
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

# ── 线程安全的日志信号发射器 ──────────────────────────

class LogEmitter(QObject):
    """使用 pyqtSignal 将日志从后台线程安全投递到主线程"""
    log_signal = Signal(str, str)  # level, message

# 全局单例（在 main.py 中创建，确保在主线程）
_log_emitter: Optional[LogEmitter] = None
_ui_log_callback: Optional[Callable] = None
_callback_lock = threading.Lock()


def init_log_emitter():
    """初始化全局日志发射器（必须在主线程调用）"""
    global _log_emitter
    if _log_emitter is None:
        _log_emitter = LogEmitter()
    return _log_emitter


def set_ui_log_callback(callback: Callable):
    """设置 UI 日志回调（UI 层调用）"""
    global _ui_log_callback
    with _callback_lock:
        # 断开旧连接
        if _log_emitter and _ui_log_callback:
            try:
                _log_emitter.log_signal.disconnect(_ui_log_callback)
            except (TypeError, RuntimeError):
                pass
        _ui_log_callback = callback
        # 连接新信号到回调（Qt.QueuedConnection 确保跨线程安全）
        if _log_emitter and callback:
            _log_emitter.log_signal.connect(callback)


def get_ui_log_callback() -> Optional[Callable]:
    """获取当前 UI 日志回调"""
    with _callback_lock:
        return _ui_log_callback


class UILogHandler(logging.Handler):
    """将日志记录通过 pyqtSignal 转发到 UI（线程安全）"""

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            # 通过信号投递（线程安全，Qt 自动排队到主线程）
            if _log_emitter:
                _log_emitter.log_signal.emit(record.levelname, msg)
            else:
                # 未初始化信号时，直接调用（仅主线程场景）
                cb = get_ui_log_callback()
                if cb:
                    cb(record.levelname, msg)
        except Exception:
            pass  # 绝不从日志 Handler 抛出异常


def setup_logger(
    name: str = "FolderArchiveTool",
    log_dir: str = "logs",
    level: str = "INFO",
    max_file_size_mb: int = 10,
    backup_count: int = 5,
) -> logging.Logger:
    """
    配置并返回 logger
    - 文件输出：RotatingFileHandler（自动轮转）
    - 控制台输出：StreamHandler
    - UI 输出：UILogHandler（通过 pyqtSignal，线程安全）
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 日志格式
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件 Handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=max_file_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # UI Handler（通过 pyqtSignal 与 UI 通信，线程安全）
    ui_handler = UILogHandler()
    ui_handler.setFormatter(fmt)
    logger.addHandler(ui_handler)

    return logger


def get_logger(name: str = "FolderArchiveTool") -> logging.Logger:
    """获取已配置的 logger"""
    return logging.getLogger(name)
