"""
京东Cookie自动获取项目 - 配置加载模块

本模块提供统一的配置加载功能，所有模块都可以通过本模块获取配置。
"""

from config.settings import get_config_manager
from models import (
    AppConfig,
    AccountConfig,
    QinglongConfig,
    GlobalConfig,
    NotificationConfig,
    ProxyConfig,
)
from typing import Optional

# 配置管理器实例
_config_manager = get_config_manager()

# 加载配置
_config = _config_manager.load_config()


def get_config() -> AppConfig:
    """
    获取完整配置

    Returns:
        AppConfig: 应用配置对象
    """
    return _config


def get_qinglong_config() -> QinglongConfig:
    """
    获取青龙面板配置

    Returns:
        QinglongConfig: 青龙面板配置对象
    """
    return _config.qinglong_data


def get_global_config() -> GlobalConfig:
    """
    获取全局配置

    Returns:
        GlobalConfig: 全局配置对象
    """
    return _config.global_config


def get_notification_config() -> NotificationConfig:
    """
    获取通知配置

    Returns:
        NotificationConfig: 通知配置对象
    """
    return _config.notification_config


def get_proxy_config() -> Optional[ProxyConfig]:
    """
    获取代理配置

    Returns:
        Optional[ProxyConfig]: 代理配置对象，None表示未配置代理
    """
    return _config.proxy_config


def get_account_configs() -> dict[str, AccountConfig]:
    """
    获取所有账号配置

    Returns:
        dict[str, AccountConfig]: 账号配置字典，key为用户名
    """
    return _config.user_datas


def get_account_config(username: str) -> Optional[AccountConfig]:
    """
    获取指定账号的配置

    Args:
        username: 用户名

    Returns:
        Optional[AccountConfig]: 账号配置对象，None表示未找到该账号配置
    """
    return _config.user_datas.get(username)


# 导出常用配置变量
qinglong_data = get_qinglong_config()
user_datas = get_account_configs()
global_config = get_global_config()
notification_config = get_notification_config()
proxy_config = get_proxy_config()
