"""
配置管理模块
负责配置文件的加载、保存、读写
敏感信息（密码）使用 Fernet 对称加密存储
"""

import json
import os
import base64
import threading
from pathlib import Path
from typing import Any, Optional
from cryptography.fernet import Fernet

_save_lock = threading.Lock()


class ConfigManager:
    """配置管理器 —— 单例模式"""

    _instance = None
    _config_file = "config.json"
    _default_config_file = "config_default.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._config: dict = {}
        self._fernet: Optional[Fernet] = None
        self._load()

    # ── 加密相关 ──────────────────────────────────────────

    def _get_fernet(self) -> Fernet:
        """获取或创建 Fernet 加密器（基于机器特征生成密钥）"""
        if self._fernet is None:
            key_path = Path("config.key")
            if key_path.exists():
                key = key_path.read_bytes()
            else:
                key = Fernet.generate_key()
                key_path.write_bytes(key)
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt_password(self, plain: str) -> str:
        """加密密码"""
        if not plain:
            return ""
        f = self._get_fernet()
        return f.encrypt(plain.encode()).decode()

    def decrypt_password(self, encrypted: str) -> str:
        """解密密码"""
        if not encrypted:
            return ""
        try:
            f = self._get_fernet()
            return f.decrypt(encrypted.encode()).decode()
        except Exception:
            return ""

    # ── 配置读写 ──────────────────────────────────────────

    def _load(self):
        """加载配置文件，不存在则从默认配置创建"""
        config_path = Path(self._config_file)
        default_path = Path(self._default_config_file)

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        elif default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            self.save()
        else:
            self._config = {}

    def save(self):
        """保存配置到文件（线程安全）"""
        with _save_lock:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项，支持点号路径
        例: get("mail.servers.0.smtp_host")
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list):
                try:
                    value = value[int(key)]
                except (IndexError, ValueError):
                    return default
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key_path: str, value: Any):
        """设置配置项，支持点号路径"""
        keys = key_path.split(".")
        config = self._config
        for key in keys[:-1]:
            if key not in config or not isinstance(config[key], dict):
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    def get_all(self) -> dict:
        """获取完整配置"""
        return self._config.copy()

    def reset_to_default(self):
        """恢复默认配置"""
        default_path = Path(self._default_config_file)
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            self.save()

    def export_config(self, path: str):
        """导出配置文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=4)

    def import_config(self, path: str):
        """导入配置文件"""
        with open(path, "r", encoding="utf-8") as f:
            self._config = json.load(f)
        self.save()
