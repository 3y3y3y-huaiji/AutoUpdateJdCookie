"""
京东Cookie自动获取项目 - Web数据模型模块

本模块定义了Web管理界面使用的所有数据模型，基于Pydantic实现数据验证。
主要功能包括：
1. 定义账号配置模型
2. 定义青龙面板配置模型
3. 定义全局配置模型
4. 定义通知配置模型
5. 定义代理配置模型
6. 定义任务状态模型
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
import re


class AccountConfig(BaseModel):
    """
    账号配置模型
    用于定义单个京东账号的登录和验证码处理配置
    """

    username: str = Field(..., description="用户名（手机号或QQ号）")
    password: str = Field(..., description="密码")
    pt_pin: str = Field(..., description="京东pt_pin")
    user_type: Literal["jd", "qq"] = Field(default="jd", description="账号类型")
    force_update: bool = Field(default=False, description="是否强制更新")
    auto_switch: bool = Field(default=True, description="是否自动处理验证码")
    sms_func: Optional[Literal["no", "manual_input", "webhook"]] = Field(
        default=None, description="短信验证码处理方式"
    )
    sms_webhook: Optional[str] = Field(
        default=None, description="短信验证码webhook地址"
    )
    voice_func: Optional[Literal["no", "manual_input"]] = Field(
        default=None, description="语音验证码处理方式"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """
        验证用户名不为空

        Args:
            v: 用户名

        Returns:
            str: 验证通过的用户名

        Raises:
            ValueError: 用户名为空时抛出异常
        """
        if not v:
            raise ValueError("用户名不能为空")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not v:
            raise ValueError("密码不能为空")
        return v

    @field_validator("pt_pin")
    @classmethod
    def validate_pt_pin(cls, v):
        if not v:
            raise ValueError("pt_pin不能为空")
        return v


class QinglongConfig(BaseModel):
    """
    青龙面板配置模型
    用于配置青龙面板的连接信息
    """

    url: str = Field(..., description="青龙面板URL")
    client_id: Optional[str] = Field(default="", description="client_id")
    client_secret: Optional[str] = Field(default="", description="client_secret")
    token: Optional[str] = Field(default="", description="token")
    username: Optional[str] = Field(default="", description="青龙用户名")
    password: Optional[str] = Field(default="", description="青龙密码")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v:
            raise ValueError("青龙面板URL不能为空")
        return v.rstrip("/")


class GlobalConfig(BaseModel):
    """
    全局配置模型
    用于定义应用的全局配置项
    """

    headless: bool = Field(default=True, description="是否启用无头模式")
    cron_expression: str = Field(default="15 0 * * *", description="定时任务Cron表达式")
    user_agent: Optional[str] = Field(default=None, description="User-Agent")
    enable_desensitize: bool = Field(default=False, description="是否启用日志脱敏")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v):
        if not v:
            raise ValueError("Cron表达式不能为空")
        return v


class NotificationConfig(BaseModel):
    """
    通知配置模型
    用于定义各种通知方式的配置
    """

    is_send_msg: bool = Field(default=False, description="是否启用消息通知")
    is_send_success_msg: bool = Field(default=True, description="更新成功后通知")
    is_send_fail_msg: bool = Field(default=True, description="更新失败后通知")
    send_wecom: List[str] = Field(default_factory=list, description="企业微信通知地址")
    send_webhook: List[str] = Field(
        default_factory=list, description="自定义Webhook地址"
    )
    send_dingtalk: List[str] = Field(default_factory=list, description="钉钉通知地址")
    send_feishu: List[str] = Field(default_factory=list, description="飞书通知地址")
    send_pushplus: List[str] = Field(
        default_factory=list, description="PushPlus通知地址"
    )
    send_serverchan: List[str] = Field(
        default_factory=list, description="Server酱通知地址"
    )


class ProxyConfig(BaseModel):
    """
    代理配置模型
    用于定义HTTP代理的配置信息
    """

    server: Optional[str] = Field(default=None, description="代理服务器地址")
    username: Optional[str] = Field(default=None, description="代理用户名")
    password: Optional[str] = Field(default=None, description="代理密码")

    @field_validator("server")
    @classmethod
    def validate_server(cls, v):
        if v and v != "http://":
            url_pattern = re.compile(
                r"^(http|https|socks5)://"
                r"(?:(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,6}|"
                r"\d{1,3}\.\d{1,3}\.\d{1,3})"
                r"(?::\d+)?"
            )
            if not url_pattern.match(v):
                raise ValueError("代理server URL格式不正确")
        return v


class TaskStatus(BaseModel):
    """
    任务状态模型
    用于跟踪任务的执行状态
    """

    task_id: str
    status: Literal["pending", "running", "success", "failed"]
    message: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    logs: List[str] = Field(default_factory=list)


class AccountTestResult(BaseModel):
    """
    账号测试结果模型
    用于返回账号登录测试的结果
    """

    username: str
    success: bool
    message: str
    pt_key: Optional[str] = None


class QinglongTestResult(BaseModel):
    """
    青龙面板测试结果模型
    用于返回青龙面板连接测试的结果
    """

    success: bool
    message: str
    env_count: Optional[int] = None


class AppConfig(BaseModel):
    """
    应用配置模型
    包含所有应用配置的根模型
    """

    user_datas: Dict[str, AccountConfig] = Field(
        default_factory=dict, description="用户账号配置"
    )
    qinglong_data: QinglongConfig = Field(..., description="青龙面板配置")
    global_config: GlobalConfig = Field(
        default_factory=GlobalConfig, description="全局配置"
    )
    notification_config: NotificationConfig = Field(
        default_factory=NotificationConfig, description="通知配置"
    )
    proxy_config: Optional[ProxyConfig] = Field(default=None, description="代理配置")
