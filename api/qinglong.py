from urllib.parse import urljoin
import aiohttp
from enum import Enum
from typing import Union
from utils.tools import send_request
from api.base_qinglong import BaseQlApi


class QlUri(Enum):
    user_login = "api/user/login"
    envs = "api/envs"
    envs_enable = "api/envs/enable"
    envs_disable = "api/envs/disable"


class QlOpenUri(Enum):
    auth_token = "open/auth/token"
    envs = "open/envs"
    envs_enable = "open/envs/enable"
    envs_disable = "open/envs/disable"


class QlApi(BaseQlApi):
    """
    青龙面板API类
    """

    def __init__(self, url: str):
        super().__init__(url, QlUri)

    def login_by_token(self, token: str):
        """
        使用token登录

        Args:
            token: 登录token
        """
        headers = {"Content-Type": "application/json"}
        self.token = token
        headers["Authorization"] = self.token
        self.headers = headers

    async def login_by_username(self, user: str, password: str):
        """
        使用用户名密码登录

        Args:
            user: 用户名
            password: 密码

        Returns:
            登录响应结果
        """
        data = {"username": user, "password": password}
        headers = {"Content-Type": "application/json"}
        response = await send_request(
            url=urljoin(self.url, QlUri.user_login.value),
            method="post",
            headers=headers,
            data=data,
        )
        if response["code"] == 200:
            self.token = "Bearer " + response["data"]["token"]
            headers["Authorization"] = self.token
            self.headers = headers
        return response


class QlOpenApi(BaseQlApi):
    """
    青龙面板开放API类
    """

    def __init__(self, url: str):
        super().__init__(url, QlOpenUri)

    async def login(self, client_id: str, client_secret: str):
        """
        使用client_id和client_secret登录

        Args:
            client_id: 客户端ID
            client_secret: 客户端密钥

        Returns:
            登录响应结果
        """
        headers = {"Content-Type": "application/json"}
        params = {"client_id": client_id, "client_secret": client_secret}
        response = await send_request(
            url=urljoin(self.url, QlOpenUri.auth_token.value),
            method="get",
            headers=headers,
            params=params,
        )
        if response["code"] == 200:
            self.token = "Bearer " + response["data"]["token"]
            headers["Authorization"] = self.token
            self.headers = headers
        return response
