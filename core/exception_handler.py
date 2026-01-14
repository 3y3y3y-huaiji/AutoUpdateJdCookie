"""
京东Cookie自动获取项目 - 统一异常处理模块

本模块提供统一的异常处理功能，用于捕获和处理项目中抛出的异常。
"""

import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from core.logger import logger
from core.exceptions import (
    BaseException as AppBaseException,
    ConfigError,
    NetworkError,
    LoginError,
    CaptchaError,
    CookieError,
    QinglongError,
    SMSVerificationError,
    VoiceVerificationError,
    TaskError
)


def setup_exception_handlers(app):
    """
    设置FastAPI应用的异常处理器
    
    Args:
        app: FastAPI应用实例
    """
    
    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException):
        """
        处理应用自定义异常
        """
        logger.error(f"应用异常: {exc} | {traceback.format_exc()}")
        return JSONResponse(
            status_code=exc.code,
            content={"error": exc.message, "code": exc.code}
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        处理HTTP异常
        """
        logger.error(f"HTTP异常: {exc.detail} | {traceback.format_exc()}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "code": exc.status_code}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        处理所有其他未捕获的异常
        """
        logger.error(f"未捕获的异常: {str(exc)} | {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": "内部服务器错误", "code": 500}
        )


def handle_exception(func):
    """
    装饰器，用于捕获和处理函数中的异常
    
    Args:
        func: 要装饰的函数
    
    Returns:
        装饰后的函数
    """
    
    async def wrapper(*args, **kwargs):
        """
        装饰器包装函数
        """
        try:
            return await func(*args, **kwargs)
        except AppBaseException as e:
            logger.error(f"应用异常: {e} | {traceback.format_exc()}")
            raise
        except Exception as e:
            logger.error(f"未捕获的异常: {str(e)} | {traceback.format_exc()}")
            raise AppBaseException(f"内部服务器错误: {str(e)}", 500) from e
    
    return wrapper


def sync_handle_exception(func):
    """
    装饰器，用于捕获和处理同步函数中的异常
    
    Args:
        func: 要装饰的同步函数
    
    Returns:
        装饰后的函数
    """
    
    def wrapper(*args, **kwargs):
        """
        装饰器包装函数
        """
        try:
            return func(*args, **kwargs)
        except AppBaseException as e:
            logger.error(f"应用异常: {e} | {traceback.format_exc()}")
            raise
        except Exception as e:
            logger.error(f"未捕获的异常: {str(e)} | {traceback.format_exc()}")
            raise AppBaseException(f"内部服务器错误: {str(e)}", 500) from e
    
    return wrapper
