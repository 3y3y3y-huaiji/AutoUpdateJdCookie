"""
京东Cookie自动获取项目 - OCR引擎工厂模块

本模块提供了OCR引擎的工厂模式，支持多种OCR引擎的动态切换。
主要功能：
1. 支持ddddocr引擎
2. 支持PaddleOCR引擎
3. 提供统一的OCR接口
4. 支持滑块匹配、文字识别、目标检测
"""

import os
from typing import Optional, Dict, Any
import cv2
import numpy as np
from loguru import logger


class OcrEngine:
    def __init__(self, engine_type: str = "ddddocr"):
        self.engine_type = engine_type
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        if self.engine_type == "ddddocr":
            self._init_ddddocr()
        elif self.engine_type == "paddleocr":
            self._init_paddleocr()
        else:
            logger.warning(f"不支持的OCR引擎: {self.engine_type}, 使用ddddocr")
            self._init_ddddocr()

    def _init_ddddocr(self):
        try:
            import ddddocr

            self._engine = ddddocr.DdddOcr(det=True, show_ad=False)
            logger.info("ddddocr引擎初始化成功")
        except ImportError:
            logger.error("ddddocr未安装，请运行: pip install ddddocr")
            raise

    def _init_paddleocr(self):
        try:
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(
                use_angle_cls=True, lang="ch", use_gpu=False, show_log=False
            )
            logger.info("PaddleOCR引擎初始化成功")
        except ImportError:
            logger.warning("PaddleOCR未安装，回退到ddddocr")
            self._init_ddddocr()

    def detect(self, image: np.ndarray) -> list:
        if self.engine_type == "ddddocr":
            return self._detect_ddddocr(image)
        elif self.engine_type == "paddleocr":
            return self._detect_paddleocr(image)
        else:
            return self._detect_ddddocr(image)

    def _detect_ddddocr(self, image: np.ndarray) -> list:
        _, buffer = cv2.imencode(".jpg", image)
        image_bytes = buffer.tobytes()
        return self._engine.detection(image_bytes)

    def _detect_paddleocr(self, image: np.ndarray) -> list:
        result = self._engine.ocr(image, cls=True)
        boxes = []
        for line in result:
            for word_info in line:
                box = word_info[0]
                x1, y1 = int(box[0][0]), int(box[0][1])
                x2, y2 = int(box[2][0]), int(box[2][1])
                boxes.append([x1, y1, x2, y2])
        return boxes

    def classify(self, image: np.ndarray) -> str:
        if self.engine_type == "ddddocr":
            return self._classify_ddddocr(image)
        elif self.engine_type == "paddleocr":
            return self._classify_paddleocr(image)
        else:
            return self._classify_ddddocr(image)

    def _classify_ddddocr(self, image: np.ndarray) -> str:
        _, buffer = cv2.imencode(".jpg", image)
        image_bytes = buffer.tobytes()
        return self._engine.classification(image_bytes, png_fix=True)

    def _classify_paddleocr(self, image: np.ndarray) -> str:
        result = self._engine.ocr(image, cls=True)
        if result and len(result) > 0 and len(result[0]) > 0:
            return result[0][0][0]
        return ""

    def slide_match(
        self, target: np.ndarray, background: np.ndarray, simple_target: bool = True
    ) -> Dict[str, Any]:
        if self.engine_type == "ddddocr":
            return self._slide_match_ddddocr(target, background, simple_target)
        else:
            return self._slide_match_ddddocr(target, background, simple_target)

    def _slide_match_ddddocr(
        self, target: np.ndarray, background: np.ndarray, simple_target: bool
    ) -> Dict[str, Any]:
        import ddddocr

        _, target_buffer = cv2.imencode(".jpg", target)
        target_bytes = target_buffer.tobytes()
        _, bg_buffer = cv2.imencode(".jpg", background)
        bg_bytes = bg_buffer.tobytes()
        det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
        return det.slide_match(target_bytes, bg_bytes, simple_target=simple_target)


class OcrEngineFactory:
    @staticmethod
    def create(engine_type: str = "ddddocr") -> OcrEngine:
        return OcrEngine(engine_type)

    @staticmethod
    def get_available_engines() -> list:
        engines = ["ddddocr"]
        try:
            from paddleocr import PaddleOCR

            engines.append("paddleocr")
        except ImportError:
            pass
        return engines


ocr_engine: Optional[OcrEngine] = None


def get_ocr_engine(engine_type: str = "ddddocr") -> OcrEngine:
    global ocr_engine
    if ocr_engine is None or ocr_engine.engine_type != engine_type:
        ocr_engine = OcrEngineFactory.create(engine_type)
    return ocr_engine
