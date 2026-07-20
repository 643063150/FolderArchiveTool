"""
压缩包校验模块
双重校验：文件数量/名称比对 + CRC32 逐文件比对
"""

import os
import zipfile
import zlib
from typing import Optional


class Validator:
    """压缩包校验器"""

    def validate_archive(
        self,
        archive_path: str,
        original_crc_map: dict,
        original_file_list: list,
    ) -> dict:
        """
        双重校验压缩包完整性

        Args:
            archive_path: 压缩包路径
            original_crc_map: 原始文件 CRC32 映射 {filename: crc32}
            original_file_list: 原始文件信息列表

        Returns:
            {
                'valid': bool,
                'errors': [str, ...],
                'details': {
                    'file_count_match': bool,
                    'crc_match_count': int,
                    'crc_mismatch': list,
                    'missing_files': list,
                    'extra_files': list,
                }
            }
        """
        result = {
            "valid": False,
            "errors": [],
            "details": {
                "file_count_match": False,
                "crc_match_count": 0,
                "crc_mismatch": [],
                "missing_files": [],
                "extra_files": [],
            },
        }

        # 1. 检查压缩包是否存在且未损坏
        if not os.path.exists(archive_path):
            result["errors"].append(f"压缩包不存在: {archive_path}")
            return result

        if not self.verify_zip_integrity(archive_path):
            result["errors"].append("压缩包损坏或格式错误")
            return result

        # 2. 提取压缩包内文件列表和 CRC
        try:
            archive_crc_map = self.extract_crc_map(archive_path)
        except Exception as e:
            result["errors"].append(f"读取压缩包 CRC 失败: {e}")
            return result

        # 3. 文件数量比对
        original_names = set(original_crc_map.keys())
        archive_names = set(archive_crc_map.keys())

        result["details"]["file_count_match"] = len(original_names) == len(archive_names)

        # 4. 缺失/多余文件
        result["details"]["missing_files"] = list(original_names - archive_names)
        result["details"]["extra_files"] = list(archive_names - original_names)

        if result["details"]["missing_files"]:
            result["errors"].append(
                f"缺失文件: {result['details']['missing_files']}"
            )
        if result["details"]["extra_files"]:
            result["errors"].append(
                f"多余文件: {result['details']['extra_files']}"
            )

        # 5. CRC 逐文件比对
        match_count = 0
        for filename, orig_crc in original_crc_map.items():
            if filename in archive_crc_map:
                if archive_crc_map[filename] == orig_crc:
                    match_count += 1
                else:
                    result["details"]["crc_mismatch"].append(filename)

        result["details"]["crc_match_count"] = match_count

        if result["details"]["crc_mismatch"]:
            result["errors"].append(
                f"CRC 不匹配文件数: {len(result['details']['crc_mismatch'])}"
            )

        # 6. 最终判定
        result["valid"] = (
            result["details"]["file_count_match"]
            and len(result["details"]["missing_files"]) == 0
            and len(result["details"]["crc_mismatch"]) == 0
        )

        return result

    def verify_zip_integrity(self, archive_path: str) -> bool:
        """测试 zip 包是否损坏"""
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                # testzip 返回第一个损坏的文件名，None 表示全部正常
                bad_file = zf.testzip()
                return bad_file is None
        except (zipfile.BadZipFile, Exception):
            return False

    def extract_crc_map(self, archive_path: str) -> dict:
        """
        从 zip 中提取所有文件的 CRC32
        return: {filename: crc32}
        """
        crc_map = {}
        with zipfile.ZipFile(archive_path, "r") as zf:
            for info in zf.infolist():
                if not info.is_dir():
                    crc_map[info.filename] = info.CRC
        return crc_map

    def extract_crc_map_manual(self, archive_path: str) -> dict:
        """
        手动计算 zip 内每个文件的 CRC32（更严格，逐字节读取解压后内容）
        用于对内置 CRC 不放心时的二次校验
        """
        crc_map = {}
        with zipfile.ZipFile(archive_path, "r") as zf:
            for info in zf.infolist():
                if not info.is_dir():
                    crc = 0
                    with zf.open(info.filename) as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            crc = zlib.crc32(chunk, crc)
                    crc_map[info.filename] = crc & 0xFFFFFFFF
        return crc_map
