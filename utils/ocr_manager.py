"""
京东Cookie自动获取项目 - OCR管理模块

本模块提供OCR实例的统一管理，避免重复创建OCR实例，提高性能。
"""

from loguru import logger
from utils.tools import get_ocr


class OcrManager:
    """
    OCR管理器类
    负责管理OCR实例的创建和复用
    """

    def __init__(self):
        """
        初始化OCR管理器
        """
        self._ocr = None
        self._det = None
        self._my_ocr = None

    def get_ocr(self, beta: bool = False):
        """
        获取OCR实例

        Args:
            beta: 是否使用beta模式

        Returns:
            OCR实例
        """
        if self._ocr is None:
            logger.info("创建OCR实例")
            self._ocr = get_ocr(beta=beta)
        return self._ocr

    def get_det(self):
        """
        获取检测OCR实例

        Returns:
            检测OCR实例
        """
        if self._det is None:
            logger.info("创建检测OCR实例")
            self._det = get_ocr(det=True)
        return self._det

    def get_my_ocr(self):
        """
        获取自定义OCR实例

        Returns:
            自定义OCR实例
        """
        if self._my_ocr is None:
            logger.info("创建自定义OCR实例")
            self._my_ocr = get_ocr(
                det=False,
                ocr=False,
                import_onnx_path="myocr_v1.onnx",
                charsets_path="charsets.json",
            )
        return self._my_ocr


_ocr_manager = None


def get_ocr_manager() -> OcrManager:
    """
    获取OCR管理器单例

    Returns:
        OcrManager: OCR管理器实例
    """
    global _ocr_manager
    if _ocr_manager is None:
        _ocr_manager = OcrManager()
    return _ocr_manager
