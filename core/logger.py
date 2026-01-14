"""
京东Cookie自动获取项目 - 日志配置模块

本模块提供统一的日志配置功能，所有模块都应该通过本模块获取logger实例。
"""

from loguru import logger
import os
from config import global_config

# 确保日志目录存在
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 移除默认的控制台输出
logger.remove()

# 配置控制台输出
logger.add(
    sink=lambda msg: print(msg, end=""),  # 使用lambda确保日志输出正确
    level=global_config.log_level or "INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)

# 配置文件输出
logger.add(
    sink=os.path.join(LOG_DIR, "app.log"),
    level=global_config.log_level or "INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="1 week",  # 每周轮换一次日志文件
    retention="4 weeks",  # 保留4周的日志文件
    compression="zip",  # 压缩旧日志文件
    encoding="utf-8"
)

# 配置错误日志输出
logger.add(
    sink=os.path.join(LOG_DIR, "error.log"),
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
    rotation="1 week",
    retention="4 weeks",
    compression="zip",
    encoding="utf-8"
)

# 导出logger实例
__all__ = ["logger"]
