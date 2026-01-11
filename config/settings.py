"""
京东Cookie自动获取项目 - 配置管理模块

本模块提供应用配置的加载、保存和管理功能，使用JSON文件存储配置。
主要功能包括：
1. 配置文件的加载和保存
2. 账号配置的增删改查
3. 青龙面板配置管理
4. 全局配置管理
5. 通知配置管理
6. 代理配置管理
"""

import json
import os
from pathlib import Path
from typing import Optional
from web.models import AppConfig, AccountConfig, QinglongConfig, GlobalConfig, NotificationConfig, ProxyConfig

class ConfigManager:
    """
    配置管理器类
    负责管理应用的所有配置，包括加载、保存和更新操作
    """

    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为config.json
        """
        self.config_path = Path(config_path)
        self._config: Optional[AppConfig] = None

    def load_config(self) -> AppConfig:
        """
        加载配置文件

        Returns:
            AppConfig: 应用配置对象

        Raises:
            RuntimeError: 配置文件加载失败时抛出异常

        说明:
            如果配置文件不存在，则创建默认配置
            如果配置已加载，则直接返回缓存的配置
        """
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            self._config = AppConfig(
                qinglong_data=QinglongConfig(url="http://127.0.0.1:5700")
            )
            self.save_config()
            return self._config

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._config = AppConfig(**data)
                return self._config
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}")
    def save_config(self):
        """
        保存配置文件

        Raises:
            RuntimeError: 配置文件保存失败时抛出异常
        """
        if self._config is None:
            raise RuntimeError("配置未初始化")
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config.model_dump(mode='json'), f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"保存配置文件失败: {e}")
    def update_config(self, config: AppConfig):
        """
        更新完整配置

        Args:
            config: 新的配置对象
        """
        self._config = config
        self.save_config()
    def add_account(self, username: str, account: AccountConfig):
        """
        添加账号配置

        Args:
            username: 用户名
            account: 账号配置对象
        """
        if self._config is None:
            self.load_config()
        self._config.user_datas[username] = account
        self.save_config()
    def remove_account(self, username: str):
        """
        删除账号配置

        Args:
            username: 用户名
        """
        if self._config is None:
            self.load_config()
        if username in self._config.user_datas:
            del self._config.user_datas[username]
            self.save_config()
    def update_account(self, username: str, account: AccountConfig):
        """
        更新账号配置

        Args:
            username: 用户名
            account: 账号配置对象
        """
        if self._config is None:
            self.load_config()
        self._config.user_datas[username] = account
        self.save_config()
    def update_qinglong_config(self, config: QinglongConfig):
        """
        更新青龙面板配置

        Args:
            config: 青龙面板配置对象
        """
        if self._config is None:
            self.load_config()
        self._config.qinglong_data = config
        self.save_config()
    def update_global_config(self, config: GlobalConfig):
        """
        更新全局配置

        Args:
            config: 全局配置对象
        """
        if self._config is None:
            self.load_config()
        self._config.global_config = config
        self.save_config()
    def update_notification_config(self, config: NotificationConfig):
        """
        更新通知配置

        Args:
            config: 通知配置对象
        """
        if self._config is None:
            self.load_config()
        self._config.notification_config = config
        self.save_config()
    def update_proxy_config(self, config: Optional[ProxyConfig]):
        """
        更新代理配置

        Args:
            config: 代理配置对象，None表示清除代理
        """
        if self._config is None:
            self.load_config()
        self._config.proxy_config = config
        self.save_config()
    def get_config(self) -> AppConfig:
        """
        获取当前配置

        Returns:
            AppConfig: 应用配置对象
        """
        if self._config is None:
            self.load_config()
        return self._config

_config_manager: Optional[ConfigManager] = None

def get_config_manager(config_path: str = "config.json") -> ConfigManager:
    """
    获取配置管理器单例

    Args:
        config_path: 配置文件路径

    Returns:
        ConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager