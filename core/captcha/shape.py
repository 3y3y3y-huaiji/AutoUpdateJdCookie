"""
京东Cookie自动获取项目 - 形状验证码处理模块

本模块提供形状验证码的自动识别和处理功能。
"""

from playwright.async_api import Page
import asyncio
import os
import random
import re
import cv2
from loguru import logger
from utils.tools import (
    save_img,
    get_img_bytes,
    get_shape_location_by_type,
    get_shape_location_by_color,
    rgba2rgb,
    expand_coordinates,
    cv2_save_img,
    get_tmp_dir,
    get_word,
    ddddocr_find_files_pic,
)
from utils.consts import supported_types, supported_colors
from utils.ocr_manager import get_ocr_manager


async def auto_shape(page: Page, retry_times: int = 5):
    """
    自动识别形状验证码

    Args:
        page: Playwright页面对象
        retry_times: 重试次数
    """
    logger.info("开始二次验证")
    ocr_manager = get_ocr_manager()
    ocr = ocr_manager.get_ocr(beta=True)
    det = ocr_manager.get_det()
    my_ocr = ocr_manager.get_my_ocr()

    for i in range(retry_times + 1):
        try:
            # 查找小图
            await page.wait_for_selector(
                "div.captcha_footer img", state="visible", timeout=3000
            )
        except Exception as e:
            # 未找到元素，认为成功，退出循环
            logger.info("未找到二次验证图,退出二次验证识别")
            break

        # 二次验证失败了
        if i + 1 == retry_times + 1:
            raise Exception("二次验证失败了")

        logger.info(f"第{i + 1}次自动识别形状中...")
        tmp_dir = get_tmp_dir()

        background_img_path = os.path.join(tmp_dir, f"background_img.png")
        # 获取大图元素
        background_locator = page.locator("#cpc_img")
        # 获取元素的位置和尺寸
        backend_bounding_box = await background_locator.bounding_box()
        backend_top_left_x = backend_bounding_box["x"]
        backend_top_left_y = backend_bounding_box["y"]

        # 截取元素区域
        await page.screenshot(path=background_img_path, clip=backend_bounding_box)

        # 获取 图片的src 属性和button按键
        word_img_src = await page.locator("div.captcha_footer img").get_attribute("src")
        button = page.locator("div.captcha_footer button#submit-btn")

        # 找到刷新按钮
        refresh_button = page.locator(".jcap_refresh")

        # 获取文字图并保存
        word_img_bytes = get_img_bytes(word_img_src)
        rgba_word_img_path = save_img("rgba_word_img", word_img_bytes)

        # 图像识别的解法，东哥求放过啊，写不动了
        if page.locator("div.sp_msg.tip_text", has_text="请点击上图中的").is_visible():
            logger.info("检测为图像, 开始图像识别......")
            from utils.tools import crop_center_contour

            small_img_path = os.path.join(tmp_dir, f"small_img.png")
            # 这里是一个标准算法偏差
            slide_difference = 10

            try:
                # 将中间的图截取出来，才能更好的识别
                result = crop_center_contour(
                    rgba_word_img_path, small_img_path, min_area=100, padding=1
                )
                if result is None:
                    raise IndexError("截图异常")
                # 获取要移动的长度
                target_dict = ddddocr_find_files_pic(
                    small_img_path, background_img_path, return_dict=True
                )
                # 提取坐标
                x1, y1, x2, y2 = target_dict["target"]
                center_x = (x1 + slide_difference + x2) // 2
                center_y = (y1 + y2) // 2
                await asyncio.sleep(random.uniform(0, 1))

                logger.info("已检测到图像，尝试点击中")
                x, y = backend_top_left_x + center_x, backend_top_left_y + center_y
                # 点击图片
                await page.mouse.click(x, y)
            except IndexError:
                logger.info(f"识别图像出错,刷新中......")
                await refresh_button.click()

            await asyncio.sleep(random.uniform(2, 4))
            continue

        # 文字图是RGBA的，有蒙板识别不了，需要转成RGB
        rgb_word_img_path = rgba2rgb("rgb_word_img", rgba_word_img_path)

        # 获取问题的文字
        word = get_word(ocr, rgb_word_img_path)

        if word.find("色") > 0:
            target_color = word.split("请选出图中")[1].split("的图形")[0]
            if target_color in supported_colors:
                logger.info(f"正在点击中......")
                # 获取点的中心点
                center_x, center_y = get_shape_location_by_color(
                    background_img_path, target_color
                )
                if center_x is None and center_y is None:
                    logger.info(f"识别失败,刷新中......")
                    await refresh_button.click()
                    await asyncio.sleep(random.uniform(2, 4))
                    continue
                # 得到网页上的中心点
                x, y = backend_top_left_x + center_x, backend_top_left_y + center_y
                # 点击图片
                await page.mouse.click(x, y)
                await asyncio.sleep(random.uniform(1, 4))
                # 点击确定
                await button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue
            else:
                logger.info(f"不支持{target_color},刷新中......")
                # 刷新
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue

        # 这里是文字验证码了
        elif word.find("依次") > 0 or word.find("按照次序点选") > 0:
            logger.info(f"开始文字识别,点击中......")
            # 获取文字的顺序列表
            try:
                if word.find("依次") > 0:
                    target_char_list = list(re.findall(r"[\u4e00-\u9fff]+", word)[1])
                if word.find("按照次序点选") > 0:
                    target_char_list = list(word.split("请按照次序点选")[1])
            except IndexError:
                logger.info(f"识别文字出错,刷新中......")
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue

            target_char_len = len(target_char_list)

            # 识别字数不对
            if target_char_len < 4:
                logger.info(f"识别的字数小于4,刷新中......")
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue

            # 取前4个的文字
            target_char_list = target_char_list[:4]

            # 定义【文字, 坐标】的列表
            target_list = [[x, []] for x in target_char_list]

            # 获取大图的二进制
            background_locator = page.locator("#cpc_img")
            background_locator_src = await background_locator.get_attribute("src")
            background_locator_bytes = get_img_bytes(background_locator_src)
            bboxes = det.detection(background_locator_bytes)

            count = 0
            im = cv2.imread(background_img_path)
            for bbox in bboxes:
                # 左上角
                x1, y1, x2, y2 = bbox
                # 做了一下扩大
                expanded_x1, expanded_y1, expanded_x2, expanded_y2 = expand_coordinates(
                    x1, y1, x2, y2, 10
                )
                im2 = im[expanded_y1:expanded_y2, expanded_x1:expanded_x2]
                img_path = cv2_save_img("word", im2)
                image_bytes = open(img_path, "rb").read()
                result = my_ocr.classification(image_bytes)
                if result in target_char_list:
                    for index, target in enumerate(target_list):
                        if result == target[0] and target[0] is not None:
                            x = x1 + (x2 - x1) / 2
                            y = y1 + (y2 - y1) / 2
                            target_list[index][1] = [x, y]
                            count += 1

            if count != target_char_len:
                logger.info(f"文字识别失败,刷新中......")
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue

            await asyncio.sleep(random.uniform(0, 1))
            try:
                for char in target_list:
                    center_x = char[1][0]
                    center_y = char[1][1]
                    # 得到网页上的中心点
                    x, y = backend_top_left_x + center_x, backend_top_left_y + center_y
                    # 点击图片
                    await page.mouse.click(x, y)
                    await asyncio.sleep(random.uniform(1, 4))
            except IndexError:
                logger.info(f"识别文字出错,刷新中......")
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue
            # 点击确定
            await button.click()
            await asyncio.sleep(random.uniform(2, 4))

        else:
            shape_type = word.split("请选出图中的")[1]
            if shape_type in supported_types:
                logger.info(f"已找到图形,点击中......")
                if shape_type == "圆环":
                    shape_type = shape_type.replace("圆环", "圆形")
                # 获取点的中心点
                center_x, center_y = get_shape_location_by_type(
                    background_img_path, shape_type
                )
                if center_x is None and center_y is None:
                    logger.info(f"识别失败,刷新中......")
                    await refresh_button.click()
                    await asyncio.sleep(random.uniform(2, 4))
                    continue
                # 得到网页上的中心点
                x, y = backend_top_left_x + center_x, backend_top_left_y + center_y
                # 点击图片
                await page.mouse.click(x, y)
                await asyncio.sleep(random.uniform(1, 4))
                # 点击确定
                await button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue
            else:
                logger.info(f"不支持{shape_type},刷新中......")
                # 刷新
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                continue
