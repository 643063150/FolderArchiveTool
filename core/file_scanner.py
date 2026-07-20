"""
文件扫描模块
识别日期格式文件，按年月分组
"""

import os
import re
from pathlib import Path
from typing import Optional, Callable


class FileScanner:
    """文件扫描器 —— 识别日期格式文件并按月分组"""

    # 支持的日期格式：2026-07-20
    DEFAULT_DATE_PATTERNS = [
        (r'(\d{4})-(\d{2})-(\d{2})', '{0}-{1}'),       # 2026-07-20
    ]

    def __init__(self, date_regex: str = None):
        """
        Args:
            date_regex: 自定义日期正则，None 则使用默认模式逐一匹配
        """
        self._custom_pattern = None
        if date_regex:
            try:
                self._custom_pattern = re.compile(date_regex)
            except re.error:
                self._custom_pattern = None

    def scan(
        self,
        directory: str,
        file_pattern: str = "*.*",
        recursive: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """
        扫描目录，返回按月分组的文件信息

        Args:
            directory: 源目录
            file_pattern: 文件通配符
            recursive: 是否递归子目录
            progress_callback: 进度回调(current, total, filepath)

        Returns:
            {
                '2026-07': [FileInfo, ...],
                '2026-06': [FileInfo, ...],
            }
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        # 收集所有匹配文件
        if recursive:
            all_files = list(directory.rglob(file_pattern))
        else:
            all_files = list(directory.glob(file_pattern))

        all_files = [f for f in all_files if f.is_file()]
        result = {}
        total = len(all_files)

        for idx, filepath in enumerate(all_files):
            date_key = self._extract_date_key(filepath.name)
            if date_key:
                info = self._build_file_info(filepath, date_key)
                result.setdefault(date_key, []).append(info)

            if progress_callback:
                progress_callback(idx + 1, total, str(filepath))

        # 按月份排序（新→旧）
        return dict(sorted(result.items(), key=lambda x: x[0], reverse=True))

    def scan_specific_month(
        self,
        directory: str,
        year: int,
        month: int,
        file_pattern: str = "*.*",
        recursive: bool = False,
    ) -> list:
        """扫描指定年月的文件"""
        target_key = f"{year:04d}-{month:02d}"
        all_groups = self.scan(directory, file_pattern, recursive)
        return all_groups.get(target_key, [])

    def _extract_date_key(self, filename: str) -> Optional[str]:
        """从文件名中提取日期键（年月）"""
        if self._custom_pattern:
            m = self._custom_pattern.search(filename)
            if m:
                groups = m.groups()
                if len(groups) >= 2:
                    return f"{groups[0]}-{groups[1]}"
            return None

        for pattern, fmt in self.DEFAULT_DATE_PATTERNS:
            m = re.search(pattern, filename)
            if m:
                return fmt.format(*m.groups()[:2])
        return None

    def _build_file_info(self, filepath: Path, date_key: str) -> dict:
        """构建文件信息字典"""
        stat = filepath.stat()
        return {
            "path": str(filepath),
            "name": filepath.name,
            "size": stat.st_size,
            "size_human": self._human_size(stat.st_size),
            "modified": stat.st_mtime,
            "date_key": date_key,
        }

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """字节转可读大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
