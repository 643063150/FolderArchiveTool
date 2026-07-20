"""
打包脚本
使用 PyInstaller 将项目打包为单文件 exe
"""

import os
import sys
import shutil


def build():
    """执行打包"""

    # 清理旧的打包输出
    for d in ["build", "dist"]:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"已清理 {d}/")

    # PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=FolderArchiveTool",
        "--onefile",
        "--windowed",
        "--noconfirm",
        # 数据文件
        "--add-data=assets;assets",
        "--add-data=config_default.json;.",
        # 隐藏导入
        "--hidden-import=win32timezone",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        # 图标（如果有的话）
        # "--icon=assets/icons/app_icon.ico",
        "main.py"
    ]

    print("开始打包...")
    print(" ".join(cmd))
    os.system(" ".join(cmd))

    print("\n打包完成！")
    print(f"输出文件: {os.path.join('dist', 'FolderArchiveTool.exe')}")


if __name__ == "__main__":
    build()
