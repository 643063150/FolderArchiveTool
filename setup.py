"""
cx_Freeze 打包脚本
使用: python setup.py build
"""

import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": [
        "os", "sys", "json", "logging", "threading", "ctypes", "subprocess",
        "PySide6", "qmaterialwidgets", "apscheduler", "cryptography", "win32timezone",
    ],
    "excludes": ["tkinter", "unittest"],
    "include_files": [
        ("assets", "assets"),
        ("config_default.json", "config_default.json"),
    ],
}

base = None
if sys.platform == "win32":
    base = "gui"  # cx_Freeze 8.x 使用 "gui" 而不是 "Win32GUI"

executables = [
    Executable(
        script="main.py",
        base=base,
        target_name="FolderArchiveTool",
        # icon="assets/icons/app_icon.ico",  # 如果有图标
    )
]

setup(
    name="FolderArchiveTool",
    version="1.0.0",
    description="月度文件压缩归档工具",
    options={"build_exe": build_exe_options},
    executables=executables,
)
