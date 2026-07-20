# FolderArchiveTool v1.0

📦 月度文件压缩归档工具 — Windows 平台

## 功能特性

- **文件扫描**：自动识别 `2026-07-20` 格式命名的文件，按年月分组
- **压缩归档**：按月打包为 zip，支持手动/定时执行
- **安全校验**：CRC32 双重校验，校验通过才删除原文件
- **邮件通知**：支持多邮件服务器（第三方 + 自建），可自定义发件人名称
- **定时任务**：基于 APScheduler，支持 cron 表达式
- **开机自启**：支持注册表和任务计划程序
- **系统服务**：可注册为 Windows 服务，防止被手动关闭
- **Material Design 3**：使用 QMaterialWidgets 组件库

## 架构设计

```
┌──────────────────────────────────────────────────┐
│                   UI 层 (PySide6)                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │ 归档操作 │ │ 邮件配置 │ │ 定时任务 │ │ 设置   │ │
│  └─────────┘ └─────────┘ └─────────┘ └────────┘ │
│              QMaterialWidgets MD3 组件             │
├──────────────────────────────────────────────────┤
│               Service 层 (业务编排)                │
│  ArchiveService.run_full_archive()                │
│    扫描 → 压缩 → 校验 → 删除 → 邮件通知           │
├──────────────────────────────────────────────────┤
│                Core 层 (纯业务逻辑)                │
│  FileScanner │ Archiver │ Validator │ Cleaner     │
│  MailSender  │ Scheduler│ AutoStart │ Config      │
└──────────────────────────────────────────────────┘
```

## 目录结构

```
FolderArchiveTool/
├── main.py                      # 程序入口
├── build.py                     # PyInstaller 打包脚本
├── config_default.json          # 默认配置模板
├── requirements.txt             # 依赖
├── README.md
│
├── core/                        # 核心业务层（零 UI 依赖）
│   ├── config_manager.py        # 配置管理 + 密码加密
│   ├── file_scanner.py          # 文件扫描 + 按月分组
│   ├── archiver.py              # zip/7z 压缩引擎
│   ├── validator.py             # CRC32 双重校验
│   ├── file_cleaner.py          # 安全删除（回收站/备份）
│   ├── mail_sender.py           # 多服务器邮件发送
│   ├── scheduler.py             # APScheduler 定时调度
│   ├── auto_start.py            # 开机自启管理
│   ├── archive_service.py       # 完整流程编排
│   └── logger_setup.py          # 日志系统（线程安全）
│
├── ui/                          # UI 层
│   ├── main_window.py           # 主窗口 + 导航
│   ├── pages/                   # 功能页面
│   │   ├── page_archive.py      # 归档操作
│   │   ├── page_mail.py         # 邮件配置
│   │   ├── page_schedule.py     # 定时任务
│   │   ├── page_settings.py     # 通用设置
│   │   └── page_log.py          # 日志查看
│   ├── widgets/                 # 自定义控件
│   └── dialogs/                 # 对话框
│
└── assets/                      # 静态资源
    ├── styles/                  # QSS 样式 + MD3 配色
    └── icons/                   # 图标
```

## 安装运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py

# 打包为 exe
python build.py
```

## 系统服务

将程序注册为 Windows 服务，即使无人登录也会运行：

```bash
# 安装服务（需要管理员权限）
python core/windows_service.py install

# 启动/停止服务
python core/windows_service.py start
python core/windows_service.py stop

# 移除服务
python core/windows_service.py remove

# 调试模式（前台运行）
python core/windows_service.py debug
```

安装后可在 `services.msc` 中管理。

## 依赖

| 包 | 用途 |
|---|---|
| PySide6 | Qt UI 框架 |
| QMaterialWidgets | Material Design 3 组件 |
| APScheduler | 定时任务调度 |
| pywin32 | Windows API（回收站、注册表、服务） |
| cryptography | 密码加密 |

## 线程模型

| 操作 | 线程 | 说明 |
|---|---|---|
| 文件扫描 | ScanWorker(QThread) | 避免大目录阻塞 UI |
| 压缩归档 | ArchiveWorker(QThread) | 带进度回调 |
| 邮件发送 | MailSendWorker(QThread) | 避免网络阻塞 |
| 定时任务 | APScheduler 线程池 | 后台自动执行 |
| 日志更新 | pyqtSignal | 线程安全投递到主线程 |

## 安全机制

> **校验不通过 → 绝不删除原文件**

- CRC32 逐文件比对
- 文件数量/名称比对
- 校验失败发送告警邮件
- 可选回收站模式（可恢复）
- 可选备份模式（保留副本）

## 版本

- **v1.0** — 初始版本
