"""
京东Cookie自动获取项目 - 验证码识别器模块

本模块提供了模块化的验证码识别功能，包括滑块验证、形状验证、颜色验证、文字验证和图像验证。
主要功能：
1. 滑块验证码识别和自动滑动
2. 二次验证码识别（形状、颜色、文字、图像）
3. 改进的错误处理和重试机制
4. 支持自定义OCR模型
"""

import asyncio
import random
from typing import Optional, Tuple, List
from loguru import logger
from playwright.async_api import Page
import cv2
import numpy as np
from PIL import Image
import ddddocr


class CaptchaSolver:
    def __init__(self):
        self.ocr = None
        self.det = None
        self.custom_ocr = None

    def init_models(self):
        try:
            self.ocr = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
            self.det = ddddocr.DdddOcr(det=True, show_ad=False)
            try:
                self.custom_ocr = ddddocr.DdddOcr(
                    det=False,
                    ocr=False,
                    import_onnx_path="myocr_v1.onnx",
                    charsets_path="charsets.json",
                    show_ad=False,
                )
                logger.info("自定义OCR模型加载成功")
            except Exception as e:
                logger.warning(f"自定义OCR模型加载失败: {e}, 使用默认模型")
                self.custom_ocr = self.ocr
        except Exception as e:
            logger.error(f"OCR模型初始化失败: {e}")
            raise

    async def solve_slider_captcha(
        self,
        page: Page,
        retry_times: int = 5,
        slider_selector: str = "img.move-img",
        move_solve_type: str = "",
    ) -> bool:
        for i in range(retry_times):
            logger.info(f"第{i + 1}次滑块验证尝试")
            try:
                await page.wait_for_selector("#slot_img", state="visible", timeout=3000)
            except Exception:
                logger.info("未找到滑块，退出滑块验证")
                return True

            try:
                small_src = await page.locator("#slot_img").get_attribute("src")
                background_src = await page.locator("#main_img").get_attribute("src")

                small_img_bytes = self._get_img_bytes(small_src)
                background_img_bytes = self._get_img_bytes(background_src)

                small_img_path = self._save_img("small_img", small_img_bytes)
                background_img_path = self._save_img(
                    "background_img", background_img_bytes
                )

                small_img_width = await page.evaluate(
                    '() => { return document.getElementById("slot_img").clientWidth; }'
                )
                small_img_height = await page.evaluate(
                    '() => { return document.getElementById("slot_img").clientHeight; }'
                )

                small_image = Image.open(small_img_path)
                resized_small_image = small_image.resize(
                    (small_img_width, small_img_height)
                )
                resized_small_image.save(small_img_path)

                background_img_width = await page.evaluate(
                    '() => { return document.getElementById("main_img").clientWidth; }'
                )
                background_img_height = await page.evaluate(
                    '() => { return document.getElementById("main_img").clientHeight; }'
                )

                background_image = Image.open(background_img_path)
                resized_background_image = background_image.resize(
                    (background_img_width, background_img_height)
                )
                resized_background_image.save(background_img_path)

                slider = page.locator(slider_selector)
                await asyncio.sleep(1)

                slide_difference = 10

                if move_solve_type == "old":
                    distance = self._ddddocr_find_bytes_pic(
                        small_img_bytes, background_img_bytes
                    )
                    await asyncio.sleep(1)
                    await self._solve_slider_captcha(
                        page, slider, distance, slide_difference
                    )
                    await asyncio.sleep(1)
                else:
                    distance = self._ddddocr_find_files_pic(
                        small_img_path, background_img_path
                    )
                    await asyncio.sleep(1)
                    await self._new_solve_slider_captcha(
                        page, slider, distance, slide_difference
                    )
                    await asyncio.sleep(1)

                await asyncio.sleep(2)
                captcha_drop_visible = await page.is_visible(".captcha_drop")
                if not captcha_drop_visible:
                    logger.info("滑块验证成功")
                    return True

                if i < retry_times - 1:
                    logger.info("滑块验证失败，刷新重试")
                    await page.wait_for_selector(
                        ".captcha_drop", state="visible", timeout=3000
                    )
                    sign_locator = page.locator("#header").locator(".text-header")
                    sign_locator_box = await sign_locator.bounding_box()
                    sign_locator_left_x = sign_locator_box["x"]
                    sign_locator_left_y = sign_locator_box["y"]
                    await page.mouse.click(sign_locator_left_x, sign_locator_left_y)
                    await asyncio.sleep(1)
                    submit_locator = page.locator(".btn.J_ping.active")
                    await submit_locator.click()
                    await asyncio.sleep(1)
                    continue
                return

            except Exception as e:
                logger.error(f"滑块验证异常: {e}")
                if i < retry_times - 1:
                    await asyncio.sleep(2)
                    continue

        logger.error("滑块验证失败")
        return False

    async def solve_shape_captcha(self, page: Page, retry_times: int = 5) -> bool:
        if not self.ocr or not self.det or not self.custom_ocr:
            self.init_models()

        logger.info("开始二次验证")
        for i in range(retry_times + 1):
            try:
                await page.wait_for_selector(
                    "div.captcha_footer img", state="visible", timeout=3000
                )
            except Exception:
                logger.info("未找到二次验证图，退出二次验证识别")
                return True

            if i + 1 == retry_times + 1:
                logger.error("二次验证失败")
                return False

            logger.info(f"第{i + 1}次自动识别形状中...")

            try:
                tmp_dir = "./tmp"
                background_img_path = f"{tmp_dir}/background_img.png"
                background_locator = page.locator("#cpc_img")
                backend_bounding_box = await background_locator.bounding_box()
                await page.screenshot(
                    path=background_img_path, clip=backend_bounding_box
                )

                word_img_src = await page.locator(
                    "div.captcha_footer img"
                ).get_attribute("src")
                button = page.locator("div.captcha_footer button#submit-btn")
                refresh_button = page.locator(".jcap_refresh")

                word_img_bytes = self._get_img_bytes(word_img_src)
                rgba_word_img_path = self._save_img("rgba_word_img", word_img_bytes)

                if await page.locator(
                    "div.sp_msg.tip_text", has_text="请点击上图中的"
                ).is_visible():
                    logger.info("检测为图像，开始图像识别")
                    success = await self._solve_image_captcha(
                        page,
                        rgba_word_img_path,
                        background_img_path,
                        backend_bounding_box,
                        refresh_button,
                    )
                    if success:
                        await asyncio.sleep(random.uniform(2, 4))
                        continue

                rgb_word_img_path = self._rgba2rgb("rgb_word_img", rgba_word_img_path)
                word = self._get_word(self.ocr, rgb_word_img_path)

                if "色" in word:
                    success = await self._solve_color_captcha(
                        page,
                        word,
                        background_img_path,
                        backend_bounding_box,
                        button,
                        refresh_button,
                    )
                    if success:
                        continue

                elif "依次" in word or "按照次序点选" in word:
                    success = await self._solve_text_captcha(
                        page,
                        word,
                        background_img_path,
                        backend_bounding_box,
                        button,
                        refresh_button,
                    )
                    if success:
                        continue
                else:
                    success = await self._solve_shape_captcha(
                        page,
                        word,
                        background_img_path,
                        backend_bounding_box,
                        button,
                        refresh_button,
                    )
                    if success:
                        continue

            except Exception as e:
                logger.error(f"二次验证异常: {e}")
                if i < retry_times:
                    await asyncio.sleep(2)
                    continue

        return False

    def _get_img_bytes(self, img_src: str) -> bytes:
        import re
        import base64

        img_base64 = re.search(r"base64,(.*)", img_src)
        if img_base64:
            base64_code = img_base64.group(1)
            img_bytes = base64.b64decode(base64_code)
            return img_bytes
        raise ValueError("image is empty")

    def _save_img(self, img_name: str, img_bytes: bytes) -> str:
        import os
        from PIL import Image
        import io

        tmp_dir = "./tmp"
        os.makedirs(tmp_dir, exist_ok=True)
        img_path = f"{tmp_dir}/{img_name}.png"
        with Image.open(io.BytesIO(img_bytes)) as img:
            img.save(img_path)
        return img_path

    def _ddddocr_find_files_pic(self, target_file: str, background_file: str) -> int:
        with open(target_file, "rb") as f:
            target_bytes = f.read()
        with open(background_file, "rb") as f:
            background_bytes = f.read()
        return self._ddddocr_find_bytes_pic(target_bytes, background_bytes)

    def _ddddocr_find_bytes_pic(
        self, target_bytes: bytes, background_bytes: bytes
    ) -> int:
        det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
        res = det.slide_match(target_bytes, background_bytes, simple_target=True)
        return res["target"][0]

    async def _solve_slider_captcha(
        self, page: Page, slider, distance: int, slide_difference: int
    ):
        box = await slider.bounding_box()
        from_x = box["x"] + box["width"] / 2
        to_y = from_y = box["y"] + box["height"] / 2

        await page.mouse.move(from_x, from_y)
        await page.mouse.down()

        to_x = from_x + distance + slide_difference
        await self._human_like_mouse_move(page, from_x, to_x, to_y)

        await page.mouse.up()

    async def _new_solve_slider_captcha(
        self, page: Page, slider, distance: int, slide_difference: int
    ):
        distance = distance + slide_difference
        box = await slider.bounding_box()
        await page.mouse.move(box["x"] + 10, box["y"] + 10)
        await page.mouse.down()
        await page.mouse.move(
            box["x"] + distance + random.uniform(8, 10), box["y"], steps=5
        )
        await asyncio.sleep(random.randint(1, 5) / 10)
        await page.mouse.move(box["x"] + distance, box["y"], steps=10)
        await page.mouse.up()
        await asyncio.sleep(3)

    async def _human_like_mouse_move(
        self, page: Page, from_x: float, to_x: float, y: float
    ):
        fast_duration = 0.28
        fast_steps = 50
        fast_target_x = from_x + (to_x - from_x) * 0.8
        fast_dx = (fast_target_x - from_x) / fast_steps

        for _ in range(fast_steps):
            from_x += fast_dx
            await page.mouse.move(from_x, y)
            await asyncio.sleep(fast_duration / fast_steps)

        slow_duration = random.randint(20, 31) / 1000
        slow_steps = 10
        slow_target_x = from_x + (to_x - from_x) * 0.9
        slow_dx = (slow_target_x - from_x) / slow_steps

        for _ in range(slow_steps):
            from_x += slow_dx
            await page.mouse.move(from_x, y)
            await asyncio.sleep(slow_duration / slow_steps)

        final_duration = 0.3
        final_steps = 20
        final_dx = (to_x - from_x) / final_steps

        for _ in range(final_steps):
            from_x += final_dx
            await page.mouse.move(from_x, y)
            await asyncio.sleep(final_duration / final_steps)

    def _rgba2rgb(
        self, img_name: str, rgba_img_path: str, tmp_dir: str = "./tmp"
    ) -> str:
        import os
        from PIL import Image

        os.makedirs(tmp_dir, exist_ok=True)
        rgba_image = Image.open(rgba_img_path)
        rgb_image = Image.new("RGB", rgba_image.size, (255, 255, 255))
        rgb_image.paste(rgba_image, (0, 0), rgba_image)
        rgb_image_path = f"{tmp_dir}/{img_name}.png"
        rgb_image.save(rgb_image_path)
        return rgb_image_path

    def _get_word(self, ocr, img_path: str) -> str:
        image_bytes = open(img_path, "rb").read()
        result = ocr.classification(image_bytes, png_fix=True)
        return result

    async def _solve_image_captcha(
        self,
        page: Page,
        rgba_word_img_path: str,
        background_img_path: str,
        backend_bounding_box: dict,
        refresh_button,
    ) -> bool:
        try:
            from utils.tools import crop_center_contour, ddddocr_find_files_pic_v2

            tmp_dir = "./tmp"
            small_img_path = f"{tmp_dir}/small_img.png"
            slide_difference = 10

            result = crop_center_contour(
                rgba_word_img_path, small_img_path, min_area=100, padding=1
            )
            if result is None:
                raise IndexError("截图异常")

            target_dict = self._ddddocr_find_files_pic_v2(
                small_img_path, background_img_path
            )
            x1, y1, x2, y2 = target_dict["target"]
            center_x = (x1 + slide_difference + x2) // 2
            center_y = (y1 + y2) // 2
            await asyncio.sleep(random.uniform(0, 1))

            logger.info("已检测到图像，尝试点击")
            x, y = (
                backend_bounding_box["x"] + center_x,
                backend_bounding_box["y"] + center_y,
            )
            await page.mouse.click(x, y)
            return True
        except IndexError:
            logger.info("识别图像出错，刷新中")
            await refresh_button.click()
            return False

    def _ddddocr_find_files_pic_v2(
        self, target_file: str, background_file: str
    ) -> dict:
        with open(target_file, "rb") as f:
            target_bytes = f.read()
        with open(background_file, "rb") as f:
            background_bytes = f.read()
        det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
        res = det.slide_match(target_bytes, background_bytes, simple_target=True)
        return res

    async def _solve_color_captcha(
        self,
        page: Page,
        word: str,
        background_img_path: str,
        backend_bounding_box: dict,
        button,
        refresh_button,
    ) -> bool:
        from utils.consts import supported_colors
        from utils.tools import get_shape_location_by_color

        target_color = word.split("请选出图中")[1].split("的图形")[0]
        if target_color not in supported_colors:
            logger.info(f"不支持{target_color}，刷新中")
            await refresh_button.click()
            await asyncio.sleep(random.uniform(2, 4))
            return False

        logger.info(f"正在点击中...")
        center_x, center_y = get_shape_location_by_color(
            background_img_path, target_color
        )
        if center_x is None and center_y is None:
            logger.info(f"识别失败，刷新中")
            await refresh_button.click()
            await asyncio.sleep(random.uniform(2, 4))
            return False

        x, y = (
            backend_bounding_box["x"] + center_x,
            backend_bounding_box["y"] + center_y,
        )
        await page.mouse.click(x, y)
        await asyncio.sleep(random.uniform(1, 4))
        await button.click()
        await asyncio.sleep(random.uniform(2, 4))
        return True

    async def _solve_text_captcha(
        self,
        page: Page,
        word: str,
        background_img_path: str,
        backend_bounding_box: dict,
        button,
        refresh_button,
    ) -> bool:
        import re
        from utils.tools import (
            get_shape_location_by_type,
            expand_coordinates,
            cv2_save_img,
        )

        try:
            if "依次" in word:
                target_char_list = list(re.findall(r"[\u4e00-\u9fff]+", word)[1])
            elif "按照次序点选" in word:
                target_char_list = list(word.split("请按照次序点选")[1])
            else:
                raise IndexError("无法解析文字验证码")

            target_char_len = len(target_char_list)
            if target_char_len < 4:
                logger.info(f"识别的字数小于4，刷新中")
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                return False

            target_char_list = target_char_list[:4]
            target_list = [[x, []] for x in target_char_list]

            background_locator = page.locator("#cpc_img")
            background_locator_src = await background_locator.get_attribute("src")
            background_locator_bytes = self._get_img_bytes(background_locator_src)
            bboxes = self.det.detection(background_locator_bytes)

            count = 0
            im = cv2.imread(background_img_path)
            for bbox in bboxes:
                x1, y1, x2, y2 = bbox
                expanded_x1, expanded_y1, expanded_x2, expanded_y2 = expand_coordinates(
                    x1, y1, x2, y2, 10
                )
                im2 = im[expanded_y1:expanded_y2, expanded_x1:expanded_x2]
                img_path = cv2_save_img("word", im2)
                image_bytes = open(img_path, "rb").read()
                result = self.custom_ocr.classification(image_bytes)
                if result in target_char_list:
                    for index, target in enumerate(target_list):
                        if result == target[0] and target[0] is not None:
                            x = x1 + (x2 - x1) / 2
                            y = y1 + (y2 - y1) / 2
                            target_list[index][1] = [x, y]
                            count += 1

            if count != target_char_len:
                logger.info(f"文字识别失败，刷新中")
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                return False

            await asyncio.sleep(random.uniform(0, 1))
            try:
                for char in target_list:
                    center_x = char[1][0]
                    center_y = char[1][1]
                    x, y = (
                        backend_bounding_box["x"] + center_x,
                        backend_bounding_box["y"] + center_y,
                    )
                    await page.mouse.click(x, y)
                    await asyncio.sleep(random.uniform(1, 4))
                await button.click()
                await asyncio.sleep(random.uniform(2, 4))
                return True
            except IndexError:
                logger.info(f"识别文字出错，刷新中")
                await refresh_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                return False

        except Exception as e:
            logger.error(f"文字验证异常: {e}")
            await refresh_button.click()
            await asyncio.sleep(random.uniform(2, 4))
            return False

    async def _solve_shape_captcha(
        self,
        page: Page,
        word: str,
        background_img_path: str,
        backend_bounding_box: dict,
        button,
        refresh_button,
    ) -> bool:
        from utils.consts import supported_types
        from utils.tools import get_shape_location_by_type

        shape_type = word.split("请选出图中的")[1]
        if shape_type not in supported_types:
            logger.info(f"不支持{shape_type}，刷新中")
            await refresh_button.click()
            await asyncio.sleep(random.uniform(2, 4))
            return False

        logger.info(f"已找到图形，点击中...")
        if shape_type == "圆环":
            shape_type = shape_type.replace("圆环", "圆形")

        center_x, center_y = get_shape_location_by_type(background_img_path, shape_type)
        if center_x is None and center_y is None:
            logger.info(f"识别失败，刷新中")
            await refresh_button.click()
            await asyncio.sleep(random.uniform(2, 4))
            return False

        x, y = (
            backend_bounding_box["x"] + center_x,
            backend_bounding_box["y"] + center_y,
        )
        await page.mouse.click(x, y)
        await asyncio.sleep(random.uniform(1, 4))
        await button.click()
        await asyncio.sleep(random.uniform(2, 4))
        return True


captcha_solver = CaptchaSolver()
