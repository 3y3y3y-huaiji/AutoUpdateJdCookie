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
    retry_times: int = 2,
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
    for i in range(retry_times + 1):
        try:
            # 查找小图
            await page.wait_for_selector("#slot_img", state="visible", timeout=3000)
        except Exception as e:
            # 未找到元素，认为成功，退出循环
            logger.info("未找到滑块,退出滑块验证")
            break

        # 滑块验证失败了
        if i + 1 == retry_times + 1:
            raise Exception("滑块验证失败了")

        logger.info(f"第{i + 1}次尝试自动移动滑块中...")
        # 获取 src 属性
        small_src = await page.locator("#slot_img").get_attribute("src")
        background_src = await page.locator("#main_img").get_attribute("src")

        # 获取 bytes
        small_img_bytes = get_img_bytes(small_src)
        background_img_bytes = get_img_bytes(background_src)

        # 保存小图
        small_img_path = save_img("small_img", small_img_bytes)
        small_img_width = await page.evaluate(
            '() => { return document.getElementById("slot_img").clientWidth; }'
        )  # 获取网页的图片尺寸
        small_img_height = await page.evaluate(
            '() => { return document.getElementById("slot_img").clientHeight; }'
        )  # 获取网页的图片尺寸

        # 保存大图
        background_img_path = save_img("background_img", background_img_bytes)
        background_img_width = await page.evaluate(
            '() => { return document.getElementById("main_img").clientWidth; }'
        )  # 获取网页的图片尺寸
        background_img_height = await page.evaluate(
            '() => { return document.getElementById("main_img").clientHeight; }'
        )  # 获取网页的图片尺寸

        # 获取滑块
        slider = page.locator(slider_selector)
        await asyncio.sleep(1)

        # 这里是一个标准算法偏差
        slide_difference = 10

        if move_solve_type == "old":
            # 用于调试
            distance = ddddocr_find_bytes_pic(small_img_bytes, background_img_bytes)
            await asyncio.sleep(1)
            await solve_slider_captcha(page, slider, distance, slide_difference)
            await asyncio.sleep(1)
            continue
        # 获取要移动的长度
        distance = ddddocr_find_files_pic(small_img_path, background_img_path)
        await asyncio.sleep(1)
        # 移动滑块
        await new_solve_slider_captcha(page, slider, distance, slide_difference)
        await asyncio.sleep(1)


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
