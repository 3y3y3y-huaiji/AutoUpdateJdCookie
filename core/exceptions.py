"""
京东Cookie自动获取项目 - 自定义异常模块

本模块定义了项目中使用的所有自定义异常类，用于统一异常处理机制。
"""


class BaseException(Exception):
    """
    基础异常类，所有自定义异常都继承自此类
    """
    
    def __init__(self, message: str, code: int = 500):
        """
        初始化异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为500
        """
        self.message = message
        self.code = code
        super().__init__(self.message)
    
    def __str__(self):
        """
        返回异常字符串表示
        """
        return f"[{self.code}] {self.message}"


class ConfigError(BaseException):
    """
    配置错误异常，用于处理配置相关的错误
    """
    
    def __init__(self, message: str, code: int = 400):
        """
        初始化配置错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为400
        """
        super().__init__(message, code)


class NetworkError(BaseException):
    """
    网络错误异常，用于处理网络请求相关的错误
    """
    
    def __init__(self, message: str, code: int = 503):
        """
        初始化网络错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为503
        """
        super().__init__(message, code)


class LoginError(BaseException):
    """
    登录错误异常，用于处理登录相关的错误
    """
    
    def __init__(self, message: str, code: int = 401):
        """
        初始化登录错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为401
        """
        super().__init__(message, code)


class CaptchaError(BaseException):
    """
    验证码错误异常，用于处理验证码相关的错误
    """
    
    def __init__(self, message: str, code: int = 403):
        """
        初始化验证码错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为403
        """
        super().__init__(message, code)


class CookieError(BaseException):
    """
    Cookie错误异常，用于处理Cookie相关的错误
    """
    
    def __init__(self, message: str, code: int = 400):
        """
        初始化Cookie错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为400
        """
        super().__init__(message, code)


class QinglongError(BaseException):
    """
    青龙面板错误异常，用于处理青龙面板相关的错误
    """
    
    def __init__(self, message: str, code: int = 502):
        """
        初始化青龙面板错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为502
        """
        super().__init__(message, code)


class SMSVerificationError(BaseException):
    """
    短信验证错误异常，用于处理短信验证相关的错误
    """
    
    def __init__(self, message: str, code: int = 403):
        """
        初始化短信验证错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为403
        """
        super().__init__(message, code)


class VoiceVerificationError(BaseException):
    """
    语音验证错误异常，用于处理语音验证相关的错误
    """
    
    def __init__(self, message: str, code: int = 403):
        """
        初始化语音验证错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为403
        """
        super().__init__(message, code)


class TaskError(BaseException):
    """
    任务错误异常，用于处理定时任务相关的错误
    """
    
    def __init__(self, message: str, code: int = 500):
        """
        初始化任务错误异常
        
        Args:
            message: 异常消息
            code: 异常代码，默认为500
        """
        super().__init__(message, code)
