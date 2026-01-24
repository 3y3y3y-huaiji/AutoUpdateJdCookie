"""
京东Cookie自动获取项目 - 登录模块

本模块提供京东账号登录功能，包括账号密码登录、QQ登录、验证码处理等。
"""

from playwright.async_api import Playwright, Page
import asyncio
import random
from loguru import logger
from typing import Union, Optional
import traceback
from utils.consts import jd_login_url, user_agent as default_user_agent
from config import global_config, proxy_config
from core.captcha import auto_move_slide, auto_shape
from utils.tools import validate_proxy_config, desensitize_account
from api.send import SendApi
from utils.tools import send_msg


async def check_notice(page: Page):
    """
    检查登录是否报错

    Args:
        page: Playwright页面对象
    """
    try:
        logger.info("检查登录是否报错")
        notice = await page.wait_for_function(
            """
            () => {
                const notice = document.querySelectorAll('.notice')[1];
                return notice && notice.textContent.trim() !== '' ? notice.textContent.trim() : false;
            }
            """,
            timeout=3000,
        )
        raise RuntimeError(notice)
    except Exception:
        logger.info("登录未发现报错")
        return


async def sms_recognition(
    page: Page, user: str, mode: str, sms_func: str, sms_webhook: Optional[str]
):
    """
    短信验证码识别

    Args:
        page: Playwright页面对象
        user: 用户名
        mode: 运行模式
        sms_func: 短信验证码处理方式
        sms_webhook: 短信验证码webhook地址
    """
    from utils.tools import send_request, is_valid_verification_code
    from utils.consts import supported_sms_func

    if sms_func not in supported_sms_func:
        raise Exception(f"sms_func只支持{supported_sms_func}")

    if mode == "cron" and sms_func == "manual_input":
        sms_func = "no"

    if sms_func == "no":
        raise Exception("sms_func为no关闭, 跳过短信验证码识别环节")

    logger.info("点击【获取验证码】中")
    await page.click("button.getMsg-btn")
    await asyncio.sleep(1)
    # 自动识别滑块
    await auto_move_slide(page, retry_times=5)
    await auto_shape(page, retry_times=30)

    # 识别是否成功发送验证码
    await page.wait_for_selector('button.getMsg-btn:has-text("重新发送")', timeout=3000)
    logger.info("发送短信验证码成功")

    # 手动输入
    # 用户在60S内，手动在终端输入验证码
    if sms_func == "manual_input":
        logger.info("启用手动输入验证码模式")
        from inputimeout import inputimeout, TimeoutOccurred

        try:
            verification_code = inputimeout(prompt="请输入验证码：", timeout=60)
        except TimeoutOccurred:
            return

    # 通过调用web_hook的方式来实现全自动输入验证码
    elif sms_func == "webhook":
        logger.info("启用webhook获取验证码模式")

        if sms_webhook is None:
            raise Exception(f"sms_webhook未配置")

        headers = {
            "Content-Type": "application/json",
        }
        data = {"phone_number": user}
        response = await send_request(
            url=sms_webhook, method="post", headers=headers, data=data
        )
        verification_code = response["data"]["code"]

    await asyncio.sleep(1)
    if not is_valid_verification_code(verification_code):
        logger.error(f"验证码需为6位数字, 输入的验证码为{verification_code}, 异常")
        raise Exception(f"验证码异常")

    logger.info("填写验证码中...")
    verification_code_input = page.locator("input.acc-input.msgCode")
    for v in verification_code:
        await verification_code_input.type(v, no_wait_after=True)
        await asyncio.sleep(random.random() / 10)

    logger.info("点击提交中...")
    await page.click("a.btn")


async def voice_verification(page: Page, user: str, mode: str, voice_func: str):
    """
    语音验证码识别

    Args:
        page: Playwright页面对象
        user: 用户名
        mode: 运行模式
        voice_func: 语音验证码处理方式
    """
    from utils.consts import supported_voice_func
    from utils.tools import is_valid_verification_code

    if voice_func not in supported_voice_func:
        raise Exception(f"voice_func只支持{supported_voice_func}")

    if mode == "cron" and voice_func == "manual_input":
        voice_func = "no"

    if voice_func == "no":
        raise Exception("voice_func为no关闭, 跳过手机语音识别")

    logger.info("点击获取验证码中")
    await page.click('button.getMsg-btn:has-text("点击获取验证码")')
    await asyncio.sleep(1)
    # 自动识别滑块
    await auto_move_slide(page, retry_times=5, slider_selector="#slider")
    await auto_shape(page, retry_times=30)

    # 识别是否成功发送验证码
    await page.wait_for_selector('button.getMsg-btn:has-text("重新发送")', timeout=3000)
    logger.info("发送手机语音识别验证码成功")

    # 手动输入
    # 用户在60S内，手动在终端输入验证码
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

    logger.info("填写验证码中...")
    verification_code_input = page.locator("input.acc-input.msgCode")
    for v in verification_code:
        await verification_code_input.type(v, no_wait_after=True)
        await asyncio.sleep(random.random() / 10)

    logger.info("点击提交中...")
    await page.click("a.btn")


async def check_dialog(page: Page):
    """
    弹窗检测

    Args:
        page: Playwright页面对象
    """
    logger.info("开始弹窗检测")
    try:
        # 等待 dialog 出现
        await page.wait_for_selector(".dialog", timeout=4000)
    except Exception as e:
        logger.info("未找到弹框, 退出弹框检测")
        return
    # 获取 dialog-des 的文本内容
    dialog_text = await page.locator(".dialog-des").text_content()
    if dialog_text == "您的账号存在风险，为了账号安全需实名认证，是否继续？":
        raise Exception("检测到实名认证弹窗，请前往移动端做实名认证")

    else:
        raise Exception("检测到不支持的弹窗, 更新异常")


async def get_jd_pt_key(
    playwright: Playwright,
    user: str,
    password: str,
    user_type: str,
    pt_pin: str,
    auto_switch: bool,
    mode: str,
    sms_func: str = "no",
    sms_webhook: Optional[str] = None,
    voice_func: str = "no",
) -> Union[str, None]:
    """
    获取京东pt_key

    Args:
        playwright: Playwright实例
        user: 用户名
        password: 密码
        user_type: 用户类型
        pt_pin: 京东pt_pin
        auto_switch: 是否自动处理验证码
        mode: 运行模式
        sms_func: 短信验证码处理方式
        sms_webhook: 短信验证码webhook地址
        voice_func: 语音验证码处理方式

    Returns:
        Union[str, None]: 京东pt_key，获取失败返回None
    """
    import random

    headless = global_config.headless
    args = (
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-software-rasterizer",
        "--disable-gpu",
    )

    # 检查代理配置
    proxy = None
    if proxy_config:
        is_proxy_valid, msg = validate_proxy_config(
            proxy_config.model_dump(exclude_none=True)
        )
        if not is_proxy_valid:
            logger.error(msg)
        else:
            proxy = proxy_config.model_dump(exclude_none=True)
            logger.info(f"使用代理: {proxy['server']}")
    else:
        logger.info("未配置代理")

    browser = await playwright.chromium.launch(
        headless=headless, args=args, proxy=proxy
    )
    
    desensitized_user = desensitize_account(user, global_config.enable_desensitize)
    
    try:
        # 使用配置的UA或默认UA
        user_agent = global_config.user_agent or default_user_agent
        context = await browser.new_context(user_agent=user_agent)

        try:
            page = await context.new_page()
            await page.set_viewport_size({"width": 360, "height": 640})
            
            # 添加页面异常处理
            page.on("pageerror", lambda error: logger.error(f"页面错误: {error}"))
            page.on("requestfailed", lambda request: logger.warning(f"请求失败: {request.url} - {request.failure}"))
            
            logger.info(f"开始登录京东，访问登录页面: {jd_login_url}")
            await page.goto(jd_login_url, wait_until="networkidle", timeout=30000)

            if user_type == "qq":
                await page.get_by_role("checkbox").check(timeout=5000)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # 点击QQ登录
                qq_login_locators = ["a.quick-qq", ".qq-login-btn", "[data-type='qq']"]
                qq_login_found = False
                for qq_loc in qq_login_locators:
                    if await page.locator(qq_loc).count() > 0:
                        await page.locator(qq_loc).click()
                        qq_login_found = True
                        break
                
                if not qq_login_found:
                    logger.error(f"{desensitized_user} 未找到QQ登录按钮")
                    return None
                    
                await asyncio.sleep(random.uniform(1, 2))

                # 等待 iframe 加载完成
                await page.wait_for_selector("#ptlogin_iframe", state="visible", timeout=10000)
                # 切换到 iframe
                iframe = page.frame(name="ptlogin_iframe")
                if not iframe:
                    logger.error(f"{desensitized_user} 未找到登录iframe")
                    return None

                # 通过 id 选择 "密码登录" 链接并点击
                try:
                    await iframe.locator("#switcher_plogin").click(timeout=5000)
                    await asyncio.sleep(random.uniform(1, 2))
                except Exception as e:
                    logger.warning(f"{desensitized_user} 点击密码登录失败，可能已在密码登录页面: {e}")
                    
                # 填写账号
                username_input = iframe.locator("#u")
                if await username_input.count() == 0:
                    logger.error(f"{desensitized_user} 未找到QQ账号输入框")
                    return None
                    
                for u in user:
                    await username_input.type(u, no_wait_after=True)
                    await asyncio.sleep(random.random() / 10)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # 填写密码
                password_input = iframe.locator("#p")
                if await password_input.count() == 0:
                    logger.error(f"{desensitized_user} 未找到QQ密码输入框")
                    return None
                    
                for p in password:
                    await password_input.type(p, no_wait_after=True)
                    await asyncio.sleep(random.random() / 10)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # 点击登录按钮
                login_button = iframe.locator("#login_button")
                if await login_button.count() == 0:
                    logger.error(f"{desensitized_user} 未找到QQ登录按钮")
                    return None
                    
                await login_button.click()
                await asyncio.sleep(random.uniform(1, 3))
                
                # 这里检测安全验证
                try:
                    new_vcode_area = iframe.locator("div#newVcodeArea")
                    style = await new_vcode_area.get_attribute("style")
                    if style and "display: block" in style:
                        if await new_vcode_area.get_by_text("安全验证").count() > 0:
                            logger.error(
                                f"{desensitized_user} QQ号需要安全验证, 登录失败，请使用其它账号类型"
                            )
                            raise Exception(
                                f"QQ号{desensitized_user}需要安全验证, 登录失败，请使用其它账号类型"
                            )
                except Exception as e:
                    logger.warning(f"{desensitized_user} 检测QQ安全验证失败: {e}")

            else:
                try:
                    # 尝试多种登录方式选择器
                    login_method_selectors = [
                        "text=账号密码登录", ".account-login-btn", "[data-type='account']"
                    ]
                    
                    for selector in login_method_selectors:
                        if await page.locator(selector).count() > 0:
                            await page.locator(selector).click(timeout=5000)
                            break
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    logger.warning(f"{desensitized_user} 切换账号密码登录失败，可能已在账号密码登录页面: {e}")

                # 填写账号
                username_input = page.locator("#username")
                if await username_input.count() == 0:
                    logger.error(f"{desensitized_user} 未找到账号输入框")
                    return None
                    
                for u in user:
                    await username_input.type(u, no_wait_after=True)
                    await asyncio.sleep(random.random() / 10)
                await asyncio.sleep(random.uniform(0.5, 1.5))

                # 填写密码
                password_input = page.locator("#pwd")
                if await password_input.count() == 0:
                    logger.error(f"{desensitized_user} 未找到密码输入框")
                    return None
                    
                for p in password:
                    await password_input.type(p, no_wait_after=True)
                    await asyncio.sleep(random.random() / 10)
                await asyncio.sleep(random.uniform(0.5, 1.5))

                # 勾选协议
                try:
                    policy_checkbox = page.locator(".policy_tip-checkbox")
                    if await policy_checkbox.count() > 0:
                        await policy_checkbox.click()
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                except Exception as e:
                    logger.warning(f"{desensitized_user} 勾选协议失败，可能已勾选: {e}")

                # 点击登录按钮
                login_button = page.locator(".btn.J_ping.active")
                if await login_button.count() == 0:
                    login_button = page.locator(".login-btn")
                
                if await login_button.count() == 0:
                    logger.error(f"{desensitized_user} 未找到登录按钮")
                    return None
                    
                await login_button.click()
                await page.wait_for_load_state("networkidle", timeout=10000)

                if auto_switch:
                    try:
                        # 自动识别移动滑块验证码
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        await auto_move_slide(page, retry_times=30)

                        # 自动验证形状验证码
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        await auto_shape(page, retry_times=30)
                        await page.wait_for_load_state("networkidle", timeout=10000)

                        # 进行短信验证识别
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        if await page.locator('text="手机短信验证"').count() != 0:
                            logger.info(f"{desensitized_user} 开始短信验证码识别环节")
                            await sms_recognition(page, user, mode, sms_func, sms_webhook)
                            await page.wait_for_load_state("networkidle", timeout=10000)

                        # 进行手机语音验证识别
                        if (
                            await page.locator(
                                'div#header .text-header:has-text("手机语音验证")'
                            ).count()
                            > 0
                        ):
                            logger.info(f"{desensitized_user} 检测到手机语音验证页面,开始识别")
                            await voice_verification(page, user, mode, voice_func)
                            await page.wait_for_load_state("networkidle", timeout=10000)

                        # 弹窗检测
                        await check_dialog(page)

                        # 检查警告,如账号存在风险或账密不正确等
                        await check_notice(page)
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        
                    except Exception as e:
                        logger.error(f"{desensitized_user} 验证码处理失败: {e}")
                        traceback.print_exc()
                        return None

                else:
                    logger.info("自动过验证码开关已关, 请手动操作")
                    await page.wait_for_timeout(60000)  # 给用户足够时间手动操作

            # 等待验证码通过和页面加载完成
            logger.info(f"{desensitized_user} 等待获取cookie...")
            
            # 尝试多种成功标识
            success_selectors = [
                "#msShortcutMenu", ".user-avatar", "#J_UserInfo", ".nickname"
            ]
            success_found = False
            
            for selector in success_selectors:
                try:
                    await page.wait_for_selector(selector, state="visible", timeout=120000)
                    success_found = True
                    logger.info(f"{desensitized_user} 登录成功标识找到: {selector}")
                    break
                except Exception:
                    continue
            
            if not success_found:
                logger.warning(f"{desensitized_user} 未找到登录成功标识，尝试直接获取cookie")
            
            # 获取所有cookie
            cookies = await context.cookies()
            for cookie in cookies:
                if cookie["name"] == "pt_key":
                    pt_key = cookie["value"]
                    logger.info(f"{desensitized_user} 成功获取到pt_key")
                    return pt_key

            logger.warning(f"{desensitized_user} 未在cookie中找到pt_key")
            return None

        except Exception as e:
            logger.error(f"{desensitized_user} 登录过程中发生错误: {e}")
            traceback.print_exc()
            return None

        finally:
            await context.close()
    except Exception as e:
        logger.error(f"{desensitized_user} 浏览器操作过程中发生错误: {e}")
        traceback.print_exc()
        return None
    finally:
        await browser.close()
