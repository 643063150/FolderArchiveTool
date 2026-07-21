"""
打包脚本
使用 PyInstaller 将项目打包为单文件 exe
"""

import os
import sys
import shutil


def build():
    """执行打包"""

    # 清理旧的打包输出（保留 logs 目录）
    for d in ["build", "dist"]:
        if os.path.exists(d):
            # 只删除文件，保留 logs 目录
            for item in os.listdir(d):
                item_path = os.path.join(d, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path) and item != "logs":
                        shutil.rmtree(item_path)
                except Exception:
                    pass
            print(f"已清理 {d}/")

    # PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=FolderArchiveTool",
        "--onedir",
        "--windowed",  # GUI 程序（无控制台窗口）
        "--uac-admin",
        "--noconfirm",
        # 数据文件
        "--add-data=assets;assets",
        "--add-data=config_default.json;.",
        # 隐藏导入
        "--hidden-import=win32timezone",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtNetwork",
        # 包含 PySide6 插件路径
        "--paths", r"C:\Users\64306\AppData\Roaming\Python\Python314\site-packages\PySide6",
        # 包含 Qt 平台插件
        "--add-data", r"C:\Users\64306\AppData\Roaming\Python\Python314\site-packages\PySide6\plugins;PySide6/plugins",
        # 不添加 manifest（避免打包问题）
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
