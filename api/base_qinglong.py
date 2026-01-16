"""
京东Cookie自动获取项目 - 青龙API基类模块

本模块提供青龙API的基类，用于消除QlApi和QlOpenApi之间的重复代码。
"""

from urllib.parse import urljoin
import aiohttp
from typing import Union


class BaseQlApi:
    """
    青龙API基类
    提供通用的API请求方法
    """

    def __init__(self, url: str, uri_class):
        """
        初始化青龙API基类

        Args:
            url: 青龙面板URL
            uri_class: URI枚举类
        """
        self.url = url
        self.uri_class = uri_class
        self.token = None
        self.headers = None
        self._session = None

    async def _get_session(self):
        """
        获取或创建 aiohttp session
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """
        关闭 session
        """
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_envs(self):
        """
        获取环境变量列表
        """
        session = await self._get_session()
        async with session.get(
            url=urljoin(self.url, self.uri_class.envs.value), headers=self.headers
        ) as response:
            return await response.json()

    async def set_envs(self, data: Union[str, None] = None):
        """
        设置环境变量

        Args:
            data: 环境变量数据
        """
        session = await self._get_session()
        async with session.put(
            url=urljoin(self.url, self.uri_class.envs.value),
            data=data,
            headers=self.headers,
        ) as response:
            return await response.json()

    async def envs_enable(self, data: bytes):
        """
        启用环境变量

        Args:
            data: 环境变量ID数据
        """
        session = await self._get_session()
        async with session.put(
            url=urljoin(self.url, self.uri_class.envs_enable.value),
            data=data,
            headers=self.headers,
        ) as response:
            return await response.json()

    async def envs_disable(self, data: bytes):
        """
        禁用环境变量

        Args:
            data: 环境变量ID数据
        """
        session = await self._get_session()
        async with session.put(
            url=urljoin(self.url, self.uri_class.envs_disable.value),
            data=data,
            headers=self.headers,
        ) as response:
            return await response.json()
