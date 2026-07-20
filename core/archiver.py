"""
压缩打包模块
支持 zip 格式（标准库），可选 7z 格式（内嵌 7zr）
"""

import os
import zipfile
import time
import subprocess
from pathlib import Path
from typing import Optional, Callable


class Archiver:
    """压缩引擎 —— 支持 zip 和 7z"""

    def __init__(self, seven_zip_path: str = None):
        """
        Args:
            seven_zip_path: 7zr.exe 路径，None 则使用内嵌路径
        """
        self._7z_path = seven_zip_path or self._find_7zr()

    def _find_7zr(self) -> Optional[str]:
        """查找内嵌的 7zr.exe"""
        candidates = [
            Path("assets/7zr.exe"),
            Path("7zr.exe"),
            Path(__file__).parent.parent / "assets" / "7zr.exe",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    def create_archive(
        self,
        file_list: list,
        output_path: str,
        archive_name: str = None,
        compression_level: int = 6,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """
        创建 zip 压缩包

        Args:
            file_list: 文件信息列表（来自 FileScanner）
            output_path: 输出目录
            archive_name: 压缩包名称（不含扩展名），None 则自动生成
            compression_level: 压缩级别 0-9
            progress_callback: 进度回调(current, total, filename)

        Returns:
            {
                'success': bool,
                'archive_path': str,
                'file_count': int,
                'total_size': int,
                'archive_size': int,
                'crc_map': {filename: crc32},
                'duration_seconds': float,
                'error': str,
            }
        """
        start_time = time.time()
        result = {
            "success": False,
            "archive_path": "",
            "file_count": 0,
            "total_size": 0,
            "archive_size": 0,
            "crc_map": {},
            "duration_seconds": 0,
            "error": "",
        }

        try:
            os.makedirs(output_path, exist_ok=True)

            if archive_name is None:
                date_key = file_list[0]["date_key"] if file_list else "archive"
                archive_name = f"archive_{date_key}"

            archive_path = os.path.join(output_path, f"{archive_name}.zip")
            result["archive_path"] = archive_path

            # 压缩方式
            compression = zipfile.ZIP_DEFLATED if compression_level > 0 else zipfile.ZIP_STORED

            total = len(file_list)
            crc_map = {}
            total_size = 0

            # 先写入临时文件，完成后重命名，避免中断导致压缩包损坏
            temp_path = archive_path + ".tmp"

            with zipfile.ZipFile(temp_path, "w", compression, compresslevel=compression_level) as zf:
                for idx, file_info in enumerate(file_list):
                    filepath = file_info["path"]
                    arcname = file_info["name"]  # 压缩包内使用原始文件名

                    if os.path.exists(filepath):
                        # 获取 CRC32
                        crc = self._calc_crc32(filepath)
                        crc_map[arcname] = crc

                        # 写入压缩包
                        zf.write(filepath, arcname)

                        total_size += file_info.get("size", 0)
                        result["file_count"] += 1

                    if progress_callback:
                        progress_callback(idx + 1, total, file_info["name"])

            result["total_size"] = total_size
            result["crc_map"] = crc_map
            result["success"] = True

            # 写入完成后，原子重命名（避免中断导致损坏）
            if os.path.exists(archive_path):
                os.remove(archive_path)
            os.rename(temp_path, archive_path)
            result["archive_size"] = os.path.getsize(archive_path)

        except Exception as e:
            result["error"] = str(e)
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        result["duration_seconds"] = round(time.time() - start_time, 2)
        return result

    def create_archive_7z(
        self,
        file_list: list,
        output_path: str,
        archive_name: str = None,
        compression_level: int = 6,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """
        使用内嵌 7zr 创建 7z 压缩包（更高压缩比）
        如果 7zr 不存在则回退到 zip
        """
        if not self._7z_path:
            return self.create_archive(file_list, output_path, archive_name, compression_level, progress_callback)

        start_time = time.time()
        result = {
            "success": False,
            "archive_path": "",
            "file_count": 0,
            "total_size": 0,
            "archive_size": 0,
            "crc_map": {},
            "duration_seconds": 0,
            "error": "",
        }

        try:
            os.makedirs(output_path, exist_ok=True)

            if archive_name is None:
                date_key = file_list[0]["date_key"] if file_list else "archive"
                archive_name = f"archive_{date_key}"

            archive_path = os.path.join(output_path, f"{archive_name}.7z")
            result["archive_path"] = archive_path

            # 创建临时文件列表
            list_file = os.path.join(output_path, "._7z_filelist.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for file_info in file_list:
                    f.write(file_info["path"] + "\n")

            # 执行 7zr 命令
            cmd = [
                self._7z_path,
                "a",                           # 添加到压缩包
                f"-mx={compression_level}",    # 压缩级别
                "-y",                          # 自动确认
                archive_path,
                f"@{list_file}",               # 从文件列表读取
            ]

            proc = subprocess.run(cmd, capture_output=True, text=True)

            os.remove(list_file)

            if proc.returncode == 0:
                result["success"] = True
                result["file_count"] = len(file_list)
                result["archive_size"] = os.path.getsize(archive_path)
                result["total_size"] = sum(f.get("size", 0) for f in file_list)
            else:
                result["error"] = proc.stderr or "7z 压缩失败"

        except Exception as e:
            result["error"] = str(e)

        result["duration_seconds"] = round(time.time() - start_time, 2)
        return result

    @staticmethod
    def _calc_crc32(filepath: str) -> int:
        """计算文件 CRC32 值"""
        import zlib
        crc = 0
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                crc = zlib.crc32(chunk, crc)
        return crc & 0xFFFFFFFF

    @staticmethod
    def estimate_archive_size(file_list: list, ratio: float = 0.5) -> int:
        """预估压缩后体积（默认按 50% 压缩率估算）"""
        total = sum(f.get("size", 0) for f in file_list)
        return int(total * ratio)
