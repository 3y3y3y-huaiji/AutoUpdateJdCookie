"""
京东Cookie自动获取项目 - 主程序

本程序用于自动获取京东Cookie并更新到青龙面板。
"""

import aiohttp
import argparse
import asyncio
from api.qinglong import QlApi, QlOpenApi
from api.send import SendApi
from utils.ck import get_invalid_ck_ids
from config import (
    qinglong_data,
    user_datas,
    global_config,
    notification_config,
    proxy_config,
)
import json
from loguru import logger
import os
from playwright.async_api import Playwright, async_playwright
from playwright._impl._errors import TimeoutError
import traceback
from typing import Union
from utils.tools import send_msg, filter_cks, extract_pt_pin, desensitize_account
from core.login import get_jd_pt_key
from core.captcha import auto_move_slide, auto_move_slide_v2, auto_shape

logger.add(sink="main.log", level="DEBUG")

# 账号是否脱敏的开关
enable_desensitize = global_config.enable_desensitize


async def get_ql_api(ql_data):
    """
    封装了QL的登录
    """
    logger.info("开始获取QL登录态......")

    # 优化client_id和client_secret
    client_id = ql_data.get("client_id")
    client_secret = ql_data.get("client_secret")
    if client_id and client_secret:
        logger.info("使用client_id和client_secret登录......")
        qlapi = QlOpenApi(ql_data["url"])
        response = await qlapi.login(client_id=client_id, client_secret=client_secret)
        if response["code"] == 200:
            logger.info("client_id和client_secret正常可用......")
            return qlapi
        else:
            logger.info("client_id和client_secret异常......")

    qlapi = QlApi(ql_data["url"])

    # 其次用token
    token = ql_data.get("token")
    if token:
        logger.info("已设置TOKEN,开始检测TOKEN状态......")
        qlapi.login_by_token(token)

        # 如果token失效，就用账号密码登录
        response = await qlapi.get_envs()
        if response["code"] == 401:
            logger.info("Token已失效, 正使用账号密码获取QL登录态......")
            response = await qlapi.login_by_username(
                ql_data.get("username"), ql_data.get("password")
            )
            if response["code"] != 200:
                logger.error(f"账号密码登录失败. response: {response}")
                raise Exception(f"账号密码登录失败. response: {response}")
        else:
            logger.info("Token正常可用......")
    else:
        # 最后用账号密码
        logger.info("正使用账号密码获取QL登录态......")
        response = await qlapi.login_by_username(
            ql_data.get("username"), ql_data.get("password")
        )
        if response["code"] != 200:
            logger.error(f"账号密码登录失败.response: {response}")
            raise Exception(f"账号密码登录失败.response: {response}")
    return qlapi


async def main(mode: str = None):
    """
    :param mode 运行模式, 当mode = cron时，sms_func为 manual_input时，将自动传成no
    """
    try:
        qlapi = await get_ql_api(qinglong_data)
        send_api = SendApi("ql")
        # 拿到禁用的用户列表
        response = await qlapi.get_envs()
        if response["code"] == 200:
            logger.info("获取环境变量成功")
        else:
            logger.error(f"获取环境变量失败， response: {response}")
            raise Exception(f"获取环境变量失败， response: {response}")

        env_data = response["data"]
        # 获取值为JD_COOKIE的环境变量
        jd_ck_env_datas = filter_cks(env_data, name="JD_COOKIE")
        # 从value中过滤出pt_pin, 注意只支持单行单pt_pin
        jd_ck_env_datas = [
            {**x, "pt_pin": extract_pt_pin(x["value"])}
            for x in jd_ck_env_datas
            if extract_pt_pin(x["value"])
        ]

        try:
            logger.info("检测CK任务开始")
            # 先获取启用中的env_data
            up_jd_ck_list = filter_cks(jd_ck_env_datas, status=0, name="JD_COOKIE")
            # 这一步会去检测这些JD_COOKIE
            invalid_cks_id_list = await get_invalid_ck_ids(up_jd_ck_list)
            if invalid_cks_id_list:
                # 禁用QL的失效环境变量
                ck_ids_datas = bytes(json.dumps(invalid_cks_id_list), "utf-8")
                await qlapi.envs_disable(data=ck_ids_datas)
                # 更新jd_ck_env_datas
                jd_ck_env_datas = [
                    (
                        {**x, "status": 1}
                        if x.get("id") in invalid_cks_id_list
                        or x.get("_id") in invalid_cks_id_list
                        else x
                    )
                    for x in jd_ck_env_datas
                ]
            logger.info("检测CK任务完成")
        except Exception as e:
            traceback.print_exc()
            logger.error(f"检测CK任务失败, 跳过检测, 报错原因为{e}")

        # 获取需强制更新pt_pin
        force_update_pt_pins = [
            user_datas[key]["pt_pin"]
            for key in user_datas
            if user_datas[key].get("force_update") is True
        ]
        # 获取禁用和需要强制更新的users
        forbidden_users = [
            x
            for x in jd_ck_env_datas
            if (x["status"] == 1 or x["pt_pin"] in force_update_pt_pins)
        ]

        if not forbidden_users:
            logger.info("所有COOKIE环境变量正常，无需更新")
            return

        # 获取需要的字段
        from utils.tools import filter_forbidden_users, get_forbidden_users_dict

        filter_users_list = filter_forbidden_users(
            forbidden_users, ["_id", "id", "value", "remarks", "name"]
        )

        # 生成字典
        user_dict = get_forbidden_users_dict(filter_users_list, user_datas)
        if not user_dict:
            logger.info("失效的CK信息未配置在user_datas内，无需更新")
            return

        # 登录JD获取pt_key
        async with async_playwright() as playwright:
            for user in user_dict:
                logger.info(f"开始更新{desensitize_account(user, enable_desensitize)}")
                user_config = user_datas[user]
                pt_key = await get_jd_pt_key(
                    playwright,
                    user,
                    user_config["password"],
                    user_config.get("user_type", "jd"),
                    user_config["pt_pin"],
                    user_config.get("auto_switch", True),
                    mode,
                    user_config.get("sms_func", "no"),
                    user_config.get("sms_webhook"),
                    user_config.get("voice_func", "no"),
                )
                if pt_key is None:
                    logger.error(f"获取pt_key失败")
                    await send_msg(
                        send_api,
                        send_type=1,
                        msg=f"{desensitize_account(user, enable_desensitize)} 更新失败",
                    )
                    continue

                req_data = user_dict[user]
                req_data["value"] = (
                    f"pt_key={pt_key};pt_pin={user_datas[user]['pt_pin']};"
                )
                logger.info(f"更新内容为{req_data}")
                data = json.dumps(req_data)
                response = await qlapi.set_envs(data=data)
                if response["code"] == 200:
                    logger.info(
                        f"{desensitize_account(user, enable_desensitize)}更新成功"
                    )
                else:
                    logger.error(
                        f"{desensitize_account(user, enable_desensitize)}更新失败, response: {response}"
                    )
                    await send_msg(
                        send_api,
                        send_type=1,
                        msg=f"{desensitize_account(user, enable_desensitize)} 更新失败",
                    )
                    continue

                req_id = (
                    f"[{req_data['id']}]"
                    if "id" in req_data.keys()
                    else f'["{req_data["_id"]}"]'
                )
                data = bytes(req_id, "utf-8")
                response = await qlapi.envs_enable(data=data)
                if response["code"] == 200:
                    logger.info(
                        f"{desensitize_account(user, enable_desensitize)}启用成功"
                    )
                    await send_msg(
                        send_api,
                        send_type=0,
                        msg=f"{desensitize_account(user, enable_desensitize)} 更新成功",
                    )
                else:
                    logger.error(
                        f"{desensitize_account(user, enable_desensitize)}启用失败, response: {response}"
                    )

    except Exception as e:
        traceback.print_exc()


def parse_args():
    """
    解析参数
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m", "--mode", choices=["cron"], help="运行的main的模式(例如: 'cron')"
    )
    return parser.parse_args()


if __name__ == "__main__":
    # 使用解析参数的函数
    args = parse_args()
    asyncio.run(main(mode=args.mode))
