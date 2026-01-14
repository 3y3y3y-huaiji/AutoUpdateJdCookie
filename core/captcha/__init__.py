"""
京东Cookie自动获取项目 - 验证码处理入口模块

本模块提供统一的验证码处理入口，方便其他模块调用验证码处理功能。
"""

from playwright.async_api import Page
from core.captcha.slider import auto_move_slide, auto_move_slide_v2
from core.captcha.shape import auto_shape

__all__ = ["auto_move_slide", "auto_move_slide_v2", "auto_shape"]
