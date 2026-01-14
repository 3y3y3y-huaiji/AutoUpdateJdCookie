"""
京东Cookie自动获取项目 - Cookie管理模块

本模块提供Cookie的检测、管理和处理功能，用于处理京东Cookie的有效性检测和管理。
"""

import asyncio
from enum import Enum
import random
from utils.tools import send_request, sanitize_header_value, extract_pt_pin
from typing import List, Dict, Any, Optional
from core.logger import logger


class CheckCkCode(Enum):
    """
    Cookie检测状态码枚举
    """
    SUCCESS = 0
    NOT_LOGIN = 1001
    INVALID_COOKIE = 1002
    NETWORK_ERROR = 1003
    UNKNOWN_ERROR = 1004


async def check_ck(cookie: str) -> Dict[str, Any]:
    """
    检测JD_COOKIE是否失效
    
    Args:
        cookie: 京东Cookie字符串
    
    Returns:
        Dict[str, Any]: 检测结果字典，包含以下键：
            - success: bool, 检测是否成功
            - code: int, 状态码
            - message: str, 状态消息
            - data: Any, 检测返回的数据
            - pt_pin: Optional[str], 从Cookie中提取的pt_pin
    """
    url = "https://me-api.jd.com/user_new/info/GetJDUserInfoUnion"
    method = "get"
    headers = {
        "Host": "me-api.jd.com",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Cookie": sanitize_header_value(cookie),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.42",
        "Accept-Language": "zh-cn",
        "Referer": "https://home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&",
        "Accept-Encoding": "gzip, deflate, br",
    }
    
    try:
        r = await send_request(url, method, headers)
        # 检测这里太快了, sleep一会儿, 避免FK
        await asyncio.sleep(random.uniform(0.5, 2))
        
        pt_pin = extract_pt_pin(cookie)
        
        if r.get("retcode") == str(CheckCkCode.NOT_LOGIN.value):
            logger.info(f"Cookie检测失败: 账号未登录，pt_pin={pt_pin}")
            return {
                "success": False,
                "code": CheckCkCode.NOT_LOGIN.value,
                "message": "账号未登录",
                "data": r,
                "pt_pin": pt_pin,
            }
        
        logger.info(f"Cookie检测成功: 账号正常，pt_pin={pt_pin}")
        return {
            "success": True,
            "code": CheckCkCode.SUCCESS.value,
            "message": "账号正常",
            "data": r,
            "pt_pin": pt_pin,
        }
    except Exception as e:
        pt_pin = extract_pt_pin(cookie)
        logger.error(f"Cookie检测异常: pt_pin={pt_pin}, 错误信息: {str(e)}")
        return {
            "success": False,
            "code": CheckCkCode.NETWORK_ERROR.value,
            "message": f"网络错误: {str(e)}",
            "data": None,
            "pt_pin": pt_pin,
        }


async def check_ck_list(ck_list: List[str]) -> List[Dict[str, Any]]:
    """
    批量检测JD_COOKIE是否失效
    
    Args:
        ck_list: 京东Cookie字符串列表
    
    Returns:
        List[Dict[str, Any]]: 检测结果列表，每个元素是check_ck函数的返回值
    """
    logger.info(f"开始批量检测Cookie，共{len(ck_list)}个")
    
    # 使用异步并发检测，提高效率
    tasks = [check_ck(ck) for ck in ck_list]
    results = await asyncio.gather(*tasks)
    
    logger.info(f"Cookie批量检测完成")
    return results


async def get_invalid_cks(jd_ck_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    传入CK列表，过滤失效CK列表
    
    Args:
        jd_ck_list: 包含Cookie信息的字典列表，每个字典应包含"value"键
    
    Returns:
        List[Dict[str, Any]]: 失效的Cookie列表
    """
    logger.info(f"开始检测失效Cookie，共{len(jd_ck_list)}个")
    
    invalid_cks = []
    for jd_ck in jd_ck_list:
        cookie = jd_ck["value"]
        result = await check_ck(cookie)
        
        if not result["success"]:
            invalid_cks.append(jd_ck)
            logger.info(f"发现失效Cookie: pt_pin={result['pt_pin']}")
    
    logger.info(f"失效Cookie检测完成，共发现{len(invalid_cks)}个失效Cookie")
    return invalid_cks


async def get_invalid_ck_ids(env_data: List[Dict[str, Any]]) -> List[str]:
    """
    获取失效CK的ID列表
    
    Args:
        env_data: 包含Cookie信息的环境变量列表
    
    Returns:
        List[str]: 失效Cookie的ID列表
    """
    # 检测CK是否失效
    invalid_cks_list = await get_invalid_cks(env_data)
    
    invalid_cks_id_list = [
        ck["id"] if "id" in ck.keys() else ck["_id"] for ck in invalid_cks_list
    ]
    
    logger.info(f"获取失效Cookie ID列表，共{len(invalid_cks_id_list)}个ID")
    return invalid_cks_id_list


async def filter_valid_cks(jd_ck_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    过滤出有效的CK列表
    
    Args:
        jd_ck_list: 包含Cookie信息的字典列表，每个字典应包含"value"键
    
    Returns:
        List[Dict[str, Any]]: 有效的Cookie列表
    """
    logger.info(f"开始过滤有效Cookie，共{len(jd_ck_list)}个")
    
    valid_cks = []
    for jd_ck in jd_ck_list:
        cookie = jd_ck["value"]
        result = await check_ck(cookie)
        
        if result["success"]:
            valid_cks.append(jd_ck)
            logger.info(f"发现有效Cookie: pt_pin={result['pt_pin']}")
    
    logger.info(f"有效Cookie过滤完成，共发现{len(valid_cks)}个有效Cookie")
    return valid_cks


def parse_cookie(cookie_str: str) -> Dict[str, str]:
    """
    解析Cookie字符串为字典格式
    
    Args:
        cookie_str: Cookie字符串
    
    Returns:
        Dict[str, str]: 解析后的Cookie字典
    """
    cookie_dict = {}
    if not cookie_str:
        return cookie_dict
    
    for item in cookie_str.split(";"):
        item = item.strip()
        if not item:
            continue
        
        parts = item.split("=", 1)
        if len(parts) == 2:
            key, value = parts
            cookie_dict[key] = value
    
    return cookie_dict


def format_cookie(cookie_dict: Dict[str, str]) -> str:
    """
    将Cookie字典格式化为Cookie字符串
    
    Args:
        cookie_dict: Cookie字典
    
    Returns:
        str: 格式化后的Cookie字符串
    """
    return "; ".join([f"{key}={value}" for key, value in cookie_dict.items()])


def extract_ck_value(cookie_str: str, key: str) -> Optional[str]:
    """
    从Cookie字符串中提取指定键的值
    
    Args:
        cookie_str: Cookie字符串
        key: 要提取的键名
    
    Returns:
        Optional[str]: 提取的值，若不存在则返回None
    """
    cookie_dict = parse_cookie(cookie_str)
    return cookie_dict.get(key)
