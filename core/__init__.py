"""
核心业务逻辑层 —— 不依赖任何 UI 框架
所有进度回调通过 callable 参数传入，保持与 UI 解耦
"""

from .config_manager import ConfigManager
from .logger_setup import setup_logger, get_logger
from .file_scanner import FileScanner
from .archiver import Archiver
from .validator import Validator
from .file_cleaner import FileCleaner
from .mail_sender import MailSender
from .scheduler import ArchiveScheduler
from .auto_start import AutoStartManager
from .archive_service import ArchiveService

__all__ = [
    "ConfigManager",
    "setup_logger",
    "get_logger",
    "FileScanner",
    "Archiver",
    "Validator",
    "FileCleaner",
    "MailSender",
    "ArchiveScheduler",
    "AutoStartManager",
    "ArchiveService",
]
