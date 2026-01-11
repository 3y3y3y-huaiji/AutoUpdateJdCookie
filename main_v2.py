"""
京东Cookie自动获取项目 - 核心登录逻辑（重构版）

本模块是项目的核心登录逻辑，负责处理京东账号登录、验证码识别、Cookie获取等功能。
主要功能：
1. 支持京东账号和QQ账号登录
2. 自动处理滑块验证码
3. 自动处理二次验证码（形状、颜色、文字、图像）
4. 支持短信验证码和语音验证码
5. 改进的错误处理和重试机制
6. 支持代理配置
7. 支持Webhook获取验证码
"""

import aiohttp
import argparse
import asyncio
from api.qinglong import QlApi, QlOpenApi
from api.send import SendApi
from utils.ck import get_invalid_ck_ids
from config.settings import get_config_manager
import cv2
import json
from loguru import logger
import os
from playwright.async_api import Playwright, async_playwright
from playwright._impl._errors import TimeoutError
import random
import re
from PIL import Image
import traceback
from typing import Union
from utils.consts import (
    jd_login_url,
    supported_types,
    supported_colors,
    supported_sms_func
)
from utils.tools import (
    get_tmp_dir,
    get_img_bytes,
    get_forbidden_users_dict,
    filter_forbidden_users,
    save_img,
    rgba2rgb,
    send_msg,
    validate_proxy_config,
    is_valid_verification_code,
    filter_cks,
    extract_pt_pin,
    desensitize_account
)
from utils.captcha_solver import captcha_solver

logger.add(
    sink="main.log",
    level="DEBUG"
)

try:
    from config import enable_desensitize
except ImportError:
    enable_desensitize = False


async def download_image(url, filepath):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(filepath, 'wb') as f:
                    f.write(await response.read())
                logger.info(f"Image downloaded to {filepath}")
            else:
                logger.error(f"Failed to download image. Status code: {response.status}")


async def check_notice(page):
    try:
        logger.info("检查登录是否报错")
        notice = await page.wait_for_function(
            """
            () => {
                const notice = document.querySelectorAll('.notice')[1];
                return notice && notice.textContent.trim() !== '' ? notice.textContent.trim() : false;
            }
            """,
            timeout = 3000
        )
        raise RuntimeError(notice)
    except TimeoutError:
        logger.info("登录未发现报错")
        return


async def sms_recognition(page, user, mode):
    try:
        from config import sms_func
    except ImportError:
        sms_func = "no"

    config_manager = get_config_manager()
    config = config_manager.get_config()
    user_data = config.user_datas.get(user, {})
    sms_func = user_data.get("sms_func", sms_func)

    if sms_func not in supported_sms_func:
        raise Exception(f"sms_func只支持{supported_sms_func}")

    if mode == "cron" and sms_func == "manual_input":
        sms_func = "no"

    if sms_func == "no":
        raise Exception("sms_func为no关闭, 跳过短信验证码识别环节")

    logger.info('点击【获取验证码】中')
    await page.click('button.getMsg-btn')
    await asyncio.sleep(1)
    
    await captcha_solver.solve_slider_captcha(page, retry_times=5)
    await captcha_solver.solve_shape_captcha(page, retry_times=30)

    await page.wait_for_selector('button.getMsg-btn:has-text("重新发送")', timeout=3000)
    logger.info("发送短信验证码成功")

    if sms_func == "manual_input":
        logger.info("启用手动输入验证码模式")
        from inputimeout import inputimeout, TimeoutOccurred
        try:
            verification_code = inputimeout(prompt="请输入验证码：", timeout=60)
        except TimeoutOccurred:
            return

    elif sms_func == "webhook":
        logger.info("启用webhook获取验证码模式")
        from utils.tools import send_request
        sms_webhook = user_data.get("sms_webhook", "")
        if sms_webhook is None:
            raise Exception(f"sms_webhook未配置")

        headers = {
            'Content-Type': 'application/json',
        }
        data = {"phone_number": user}
        response = await send_request(url=sms_webhook, method="post", headers=headers, data=data)
        verification_code = response['data']['code']

    await asyncio.sleep(1)
    if not is_valid_verification_code(verification_code):
        logger.error(f"验证码需为6位数字, 输入的验证码为{verification_code}, 异常")
        raise Exception(f"验证码异常")

    logger.info('填写验证码中...')
    verification_code_input = page.locator('input.acc-input.msgCode')
    for v in verification_code:
        await verification_code_input.type(v, no_wait_after=True)
        await asyncio.sleep(random.random() / 10)

    logger.info('点击提交中...')
    await page.click('a.btn')


async def voice_verification(page, user, mode):
    from utils.consts import supported_voice_func
    try:
        from config import voice_func
    except ImportError:
        voice_func = "no"

    config_manager = get_config_manager()
    config = config_manager.get_config()
    user_data = config.user_datas.get(user, {})
    voice_func = user_data.get("voice_func", voice_func)

    if voice_func not in supported_voice_func:
        raise Exception(f"voice_func只支持{supported_voice_func}")

    if mode == "cron" and voice_func == "manual_input":
        voice_func = "no"

    if voice_func == "no":
        raise Exception("voice_func为no关闭, 跳过手机语音识别")

    logger.info('点击获取验证码中')
    await page.click('button.getMsg-btn:has-text("点击获取验证码")')
    await asyncio.sleep(1)
    
    await captcha_solver.solve_slider_captcha(page, retry_times=5, slider_selector='#slider')
    await captcha_solver.solve_shape_captcha(page, retry_times=30)

    await page.wait_for_selector('button.getMsg-btn:has-text("重新发送")', timeout=3000)
    logger.info("发送手机语音识别验证码成功")

    if voice_func == "manual_input":
        from inputimeout import inputimeout, TimeoutOccurred
        try:
            verification_code = inputimeout(prompt="请输入验证码：", timeout=60)
        except TimeoutOccurred:
            return

    await asyncio.sleep(1)
    if not is_valid_verification_code(verification_code):
        logger.error(f"验证码需为6位数字, 输入的验证码为{verification_code}, 异常")
        raise Exception(f"验证码异常")

    logger.info('填写验证码中...')
    verification_code_input = page.locator('input.acc-input.msgCode')
    for v in verification_code:
        await verification_code_input.type(v, no_wait_after=True)
        await asyncio.sleep(random.random() / 10)

    logger.info('点击提交中...')
    await page.click('a.btn')


async def check_dialog(page):
    logger.info("开始弹窗检测")
    try:
        await page.wait_for_selector(".dialog", timeout=4000)
    except Exception:
        logger.info('未找到弹框, 退出弹框检测')
        return
    dialog_text = await page.locator(".dialog-des").text_content()
    if dialog_text == "您的账号存在风险，为了账号安全需实名认证，是否继续？":
        raise Exception("检测到实名认证弹窗，请前往移动端做实名认证")
    else:
        raise Exception("检测到不支持的弹窗, 更新异常")


async def get_jd_pt_key(playwright: Playwright, user, mode) -> Union[str, None]:
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        user_data = config.user_datas.get(user, {})
        global_config = config.global_config

        headless = global_config.headless
        args = '--no-sandbox', '--disable-setuid-sandbox', '--disable-software-rasterizer', '--disable-gpu'

        proxy_config = config.proxy_config
        proxy = None
        if proxy_config and proxy_config.server and proxy_config.server != "http://":
            is_proxy_valid, msg = validate_proxy_config(proxy_config)
            if not is_proxy_valid:
                logger.error(msg)
            else:
                logger.info(msg)
                proxy = {
                    "server": proxy_config.server,
                    "username": proxy_config.username,
                    "password": proxy_config.password
                }
        else:
            logger.info("未配置代理")

        browser = await playwright.chromium.launch(headless=headless, args=args, proxy=proxy)
        
        try:
            user_agent = global_config.user_agent
        except AttributeError:
            from utils.consts import user_agent
            user_agent = user_agent

        context = await browser.new_context(user_agent=user_agent)

        page = await context.new_page()
        await page.set_viewport_size({"width": 360, "height": 640})
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await page.goto(jd_login_url, timeout=60000)
                logger.info(f"页面加载成功 (尝试 {attempt + 1}/{max_retries})")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"页面加载失败 (尝试 {attempt + 1}/{max_retries}): {e}, 重试中...")
                    await asyncio.sleep(2)
                else:
                    raise Exception(f"页面加载失败，已重试{max_retries}次: {e}")

        if user_data.get("user_type") == "qq":
            await page.get_by_role("checkbox").check()
            await asyncio.sleep(1)
            await page.locator("a.quick-qq").click()
            await asyncio.sleep(1)

            await page.wait_for_selector("#ptlogin_iframe")
            iframe = page.frame(name="ptlogin_iframe")

            await iframe.locator("#switcher_plogin").click()
            await asyncio.sleep(1)
            
            username_input = iframe.locator("#u")
            for u in user:
                await username_input.type(u, no_wait_after=True)
                await asyncio.sleep(random.random() / 10)
            await asyncio.sleep(1)
            
            password_input = iframe.locator("#p")
            password = user_data["password"]
            for p in password:
                await password_input.type(p, no_wait_after=True)
                await asyncio.sleep(random.random() / 10)
            await asyncio.sleep(1)
            
            await iframe.locator("#login_button").click()
            await asyncio.sleep(1)
            
            new_vcode_area = iframe.locator("div#newVcodeArea")
            style = await new_vcode_area.get_attribute("style")
            if style and "display: block" in style:
                if await new_vcode_area.get_by_text("安全验证").text_content() == "安全验证":
                    logger.error(f"QQ号{user}需要安全验证, 登录失败，请使用其它账号类型")
                    raise Exception(f"QQ号{user}需要安全验证, 登录失败，请使用其它账号类型")

        else:
            await page.get_by_text("账号密码登录").click()

            username_input = page.locator("#username")
            for u in user:
                await username_input.type(u, no_wait_after=True)
                await asyncio.sleep(random.random() / 10)

            password_input = page.locator("#pwd")
            password = user_data["password"]
            for p in password:
                await password_input.type(p, no_wait_after=True)
                await asyncio.sleep(random.random() / 10)

            await asyncio.sleep(random.random())
            await page.locator('.policy_tip-checkbox').click()
            await asyncio.sleep(random.random())
            await page.locator('.btn.J_ping.active').click()

            if user_data.get("auto_switch", True):
                await asyncio.sleep(1)
                
                slider_success = await captcha_solver.solve_slider_captcha(page, retry_times=30)
                if not slider_success:
                    logger.error("滑块验证失败")
                    return None

                await asyncio.sleep(1)
                
                shape_success = await captcha_solver.solve_shape_captcha(page, retry_times=30)
                if not shape_success:
                    logger.error("二次验证失败")
                    return None

                await asyncio.sleep(1)

                if await page.locator('text="手机短信验证"').count() != 0:
                    logger.info("开始短信验证码识别环节")
                    try:
                        await sms_recognition(page, user, mode)
                    except Exception as e:
                        logger.error(f"短信验证码识别失败: {e}")
                        return None

                if await page.locator('div#header .text-header:has-text("手机语音验证")').count() > 0:
                    logger.info("检测到手机语音验证页面,开始识别")
                    try:
                        await voice_verification(page, user, mode)
                    except Exception as e:
                        logger.error(f"语音验证码识别失败: {e}")
                        return None

                await check_dialog(page)
                await check_notice(page)
            else:
                logger.info("自动过验证码开关已关, 请手动操作")

        logger.info("等待获取cookie...")
        try:
            await page.wait_for_selector('#msShortcutMenu', state='visible', timeout=120000)
        except TimeoutError:
            logger.error("等待登录超时，可能验证码未通过")
            return None

        cookies = await context.cookies()
        for cookie in cookies:
            if cookie['name'] == 'pt_key':
                pt_key = cookie["value"]
                logger.info(f"成功获取pt_key: {pt_key[:10]}...")
                return pt_key

        logger.error("未找到pt_key")
        return None

    except Exception as e:
        logger.error(f"获取pt_key异常: {e}")
        logger.error(traceback.format_exc())
        return None

    finally:
        try:
            await context.close()
            await browser.close()
        except:
            pass


async def get_ql_api(ql_data):
    logger.info("开始获取QL登录态......")

    client_id = ql_data.get('client_id')
    client_secret = ql_data.get('client_secret')
    if client_id and client_secret:
        logger.info("使用client_id和client_secret登录......")
        qlapi = QlOpenApi(ql_data["url"])
        response = await qlapi.login(client_id=client_id, client_secret=client_secret)
        if response['code'] == 200:
            logger.info("client_id和client_secret正常可用......")
            return qlapi
        else:
            logger.info("client_id和client_secret异常......")

    qlapi = QlApi(ql_data["url"])

    token = ql_data.get('token')
    if token:
        logger.info("已设置TOKEN,开始检测TOKEN状态......")
        qlapi.login_by_token(token)
        response = await qlapi.get_envs()
        if response['code'] == 401:
            logger.info("Token已失效, 正使用账号密码获取QL登录态......")
            response = await qlapi.login_by_username(ql_data.get("username"), ql_data.get("password"))
            if response['code'] != 200:
                logger.error(f"账号密码登录失败. response: {response}")
                raise Exception(f"账号密码登录失败. response: {response}")
        else:
            logger.info("Token正常可用......")
    else:
        logger.info("正使用账号密码获取QL登录态......")
        response = await qlapi.login_by_username(ql_data.get("username"), ql_data.get("password"))
        if response['code'] != 200:
            logger.error(f"账号密码登录失败. response: {response}")
            raise Exception(f"账号密码登录失败.response: {response}")
    return qlapi


async def main(mode: str = None):
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        
        qlapi = await get_ql_api(config.qinglong_data.model_dump())
        send_api = SendApi("ql")
        
        response = await qlapi.get_envs()
        if response['code'] == 200:
            logger.info("获取环境变量成功")
        else:
            logger.error(f"获取环境变量失败， response: {response}")
            raise Exception(f"获取环境变量失败， response: {response}")

        env_data = response['data']
        jd_ck_env_datas = filter_cks(env_data, name='JD_COOKIE')
        jd_ck_env_datas = [ {**x, 'pt_pin': extract_pt_pin(x['value'])} for x in jd_ck_env_datas if extract_pt_pin(x['value'])]

        try:
            logger.info("检测CK任务开始")
            up_jd_ck_list = filter_cks(jd_ck_env_datas, status=0, name='JD_COOKIE')
            invalid_cks_id_list = await get_invalid_ck_ids(up_jd_ck_list)
            if invalid_cks_id_list:
                ck_ids_datas = bytes(json.dumps(invalid_cks_id_list), 'utf-8')
                await qlapi.envs_disable(data=ck_ids_datas)
                jd_ck_env_datas = [{**x, 'status': 1} if x.get('id') in invalid_cks_id_list or x.get('_id') in invalid_cks_id_list else x for x in jd_ck_env_datas]
            logger.info("检测CK任务完成")
        except Exception as e:
            logger.error(f"检测CK任务失败, 跳过检测, 报错原因为{e}")
            logger.error(traceback.format_exc())

        force_update_pt_pins = [config.user_datas[key]["pt_pin"] for key in config.user_datas if config.user_datas[key].get("force_update") is True]
        forbidden_users = [x for x in jd_ck_env_datas if (x['status'] == 1 or x['pt_pin'] in force_update_pt_pins)]

        if not forbidden_users:
            logger.info("所有COOKIE环境变量正常，无需更新")
            return

        filter_users_list = filter_forbidden_users(forbidden_users, ['_id', 'id', 'value', 'remarks', 'name'])
        user_dict = get_forbidden_users_dict(filter_users_list, config.user_datas)
        
        if not user_dict:
            logger.info("失效的CK信息未配置在user_datas内，无需更新")
            return

        async with async_playwright() as playwright:
            for user in user_dict:
                logger.info(f"开始更新{desensitize_account(user, enable_desensitize)}")
                pt_key = await get_jd_pt_key(playwright, user, mode)
                if pt_key is None:
                    logger.error(f"获取pt_key失败")
                    await send_msg(send_api, send_type=1, msg=f"{desensitize_account(user, enable_desensitize)} 更新失败")
                    continue

                req_data = user_dict[user]
                req_data["value"] = f"pt_key={pt_key};pt_pin={config.user_datas[user]['pt_pin']};"
                logger.info(f"更新内容为{req_data}")
                data = json.dumps(req_data)
                response = await qlapi.set_envs(data=data)
                if response['code'] == 200:
                    logger.info(f"{desensitize_account(user, enable_desensitize)}更新成功")
                else:
                    logger.error(f"{desensitize_account(user, enable_desensitize)}更新失败, response: {response}")
                    await send_msg(send_api, send_type=1, msg=f"{desensitize_account(user, enable_desensitize)} 更新失败")
                    continue

                req_id = f"[{req_data['id']}]" if 'id' in req_data.keys() else f'[\"{req_data["_id"]}\"]'
                data = bytes(req_id, 'utf-8')
                response = await qlapi.envs_enable(data=data)
                if response['code'] == 200:
                    logger.info(f"{desensitize_account(user, enable_desensitize)}启用成功")
                    await send_msg(send_api, send_type=0, msg=f"{desensitize_account(user, enable_desensitize)} 更新成功")
                else:
                    logger.error(f"{desensitize_account(user, enable_desensitize)}启用失败, response: {response}")

    except Exception as e:
        logger.error(f"主程序异常: {e}")
        logger.error(traceback.format_exc())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mode', choices=['cron'], help="运行的main的模式(例如: 'cron')")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    asyncio.run(main(mode=args.mode))