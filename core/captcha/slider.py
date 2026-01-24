"""
京东Cookie自动获取项目 - 滑块验证码处理模块

本模块提供滑块验证码的自动识别和处理功能。
"""

from playwright.async_api import Page
import asyncio
from loguru import logger
from utils.tools import (
    get_img_bytes,
    save_img,
    ddddocr_find_files_pic,
    ddddocr_find_bytes_pic,
    new_solve_slider_captcha,
    solve_slider_captcha,
)


async def auto_move_slide(
    page: Page,
    retry_times: int = 3,
    slider_selector: str = "img.move-img",
    move_solve_type: str = "",
):
    """
    自动识别移动滑块验证码

    Args:
        page: Playwright页面对象
        retry_times: 重试次数
        slider_selector: 滑块选择器
        move_solve_type: 移动解决类型
    """
    logger.info("开始滑块验证")
    
    # 尝试不同的滑块和背景图选择器
    slot_selectors = ["#slot_img", ".slider-img", ".captcha-slider-img"]
    main_selectors = ["#main_img", ".slider-background", ".captcha-background"]
    slider_selectors = [slider_selector, ".slider-btn", ".captcha-slider-btn"]
    
    for i in range(retry_times + 1):
        try:
            # 尝试找到滑块元素
            slot_found = False
            slot_locator = None
            main_locator = None
            
            for slot_sel in slot_selectors:
                try:
                    await page.wait_for_selector(slot_sel, state="visible", timeout=2000)
                    slot_locator = page.locator(slot_sel)
                    slot_found = True
                    break
                except Exception:
                    continue
            
            if not slot_found:
                # 未找到元素，认为成功或不需要滑块验证，退出循环
                logger.info("未找到滑块,退出滑块验证")
                break

            # 滑块验证失败了
            if i + 1 == retry_times + 1:
                raise Exception("滑块验证失败了")

            logger.info(f"第{i + 1}次尝试自动移动滑块中...")
            
            # 查找背景图
            main_found = False
            for main_sel in main_selectors:
                try:
                    await page.wait_for_selector(main_sel, state="visible", timeout=2000)
                    main_locator = page.locator(main_sel)
                    main_found = True
                    break
                except Exception:
                    continue
            
            if not main_found:
                logger.warning("未找到滑块背景图，重试")
                await asyncio.sleep(1)
                continue
            
            # 获取 src 属性
            small_src = await slot_locator.get_attribute("src")
            background_src = await main_locator.get_attribute("src")
            
            if not small_src or not background_src:
                logger.warning("无法获取滑块图片URL，重试")
                await asyncio.sleep(1)
                continue

            # 获取 bytes
            small_img_bytes = get_img_bytes(small_src)
            background_img_bytes = get_img_bytes(background_src)
            
            if not small_img_bytes or not background_img_bytes:
                logger.warning("无法获取滑块图片内容，重试")
                await asyncio.sleep(1)
                continue

            # 保存小图
            small_img_path = save_img("small_img", small_img_bytes)
            # 保存大图
            background_img_path = save_img("background_img", background_img_bytes)

            # 查找滑块元素
            slider = None
            slider_found = False
            for slider_sel in slider_selectors:
                try:
                    slider = page.locator(slider_sel)
                    if await slider.count() > 0:
                        await slider.wait_for(state="visible", timeout=2000)
                        slider_found = True
                        break
                except Exception:
                    continue
            
            if not slider_found:
                logger.warning("未找到滑块按钮，重试")
                await asyncio.sleep(1)
                continue
            
            await asyncio.sleep(0.5)

            # 优化滑块识别算法，使用多种方法尝试
            distance = 0
            try:
                # 尝试使用文件识别
                distance = ddddocr_find_files_pic(small_img_path, background_img_path)
                logger.debug(f"文件识别滑块距离: {distance}")
            except Exception as e:
                logger.debug(f"文件识别失败，尝试字节识别: {e}")
                try:
                    # 尝试使用字节识别
                    distance = ddddocr_find_bytes_pic(small_img_bytes, background_img_bytes)
                    logger.debug(f"字节识别滑块距离: {distance}")
                except Exception as e2:
                    logger.error(f"滑块识别失败: {e2}")
                    await asyncio.sleep(1)
                    continue
            
            # 添加随机偏差，模拟人类操作
            slide_difference = 10 + random.uniform(-2, 2)
            
            # 优化移动轨迹，使用更自然的曲线
            if move_solve_type == "old":
                # 用于调试
                await asyncio.sleep(0.5)
                await solve_slider_captcha(page, slider, distance, slide_difference)
                await asyncio.sleep(1)
                continue
            
            # 移动滑块，使用优化的轨迹算法
            await asyncio.sleep(0.5)
            await new_solve_slider_captcha(page, slider, distance, slide_difference)
            await asyncio.sleep(1)
            
            # 检查滑块是否成功
            try:
                # 等待滑块消失或成功提示
                await page.wait_for_selector(slot_sel, state="hidden", timeout=3000)
                logger.info("滑块验证成功")
                break
            except Exception:
                logger.info("滑块可能未完全成功，继续尝试")
                await asyncio.sleep(1)
                continue
                
        except Exception as e:
            logger.warning(f"滑块验证尝试 {i+1} 失败: {e}")
            if i + 1 < retry_times + 1:
                logger.info(f"等待 {2+i} 秒后重试")
                await asyncio.sleep(2 + i)
            else:
                raise Exception(f"滑块验证失败: {e}")


async def auto_move_slide_v2(
    page: Page,
    retry_times: int = 2,
    slider_selector: str = "img.move-img",
    move_solve_type: str = "",
):
    """
    自动识别移动滑块验证码（v2版本）

    Args:
        page: Playwright页面对象
        retry_times: 重试次数
        slider_selector: 滑块选择器
        move_solve_type: 移动解决类型
    """
    for i in range(retry_times):
        logger.info(f"第{i + 1}次开启滑块验证")
        # 查找小图
        try:
            # 查找小图
            await page.wait_for_selector(".captcha_drop", state="visible", timeout=3000)
        except Exception as e:
            logger.info("未找到验证码框, 退出滑块验证")
            return
        await auto_move_slide(
            page,
            retry_times=5,
            slider_selector=slider_selector,
            move_solve_type=move_solve_type,
        )

        # 判断是否一次过了滑块
        captcha_drop_visible = await page.is_visible(".captcha_drop")

        # 存在就重新滑一次
        if captcha_drop_visible:
            if i == retry_times - 1:
                return
            logger.info("一次过滑块失败, 再次尝试滑块验证")
            await page.wait_for_selector(".captcha_drop", state="visible", timeout=3000)
            # 点外键
            sign_locator = page.locator("#header").locator(".text-header")
            sign_locator_box = await sign_locator.bounding_box()
            sign_locator_left_x = sign_locator_box["x"]
            sign_locator_left_y = sign_locator_box["y"]
            await page.mouse.click(sign_locator_left_x, sign_locator_left_y)
            await asyncio.sleep(1)
            # 提交键
            submit_locator = page.locator(".btn.J_ping.active")
            await submit_locator.click()
            await asyncio.sleep(1)
            continue
        return
