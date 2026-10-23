"""
Unit test kiểm tra lọc watermark, lọc độ tin cậy và sắp xếp dòng chữ OCR.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import OCRDetection, OCRBox
from src.ocr.filter import filter_and_sort_detections, is_ignored_text, merge_detections_to_text


def test_is_ignored_text():
    """Kiểm tra regex loại trừ watermark/kênh."""
    patterns = [r"抖音", r"douyin", r"@\w+"]
    assert is_ignored_text("抖音号：123456", patterns) is True
    assert is_ignored_text("关注我 @anh_ba_phim", patterns) is True
    assert is_ignored_text("www.douyin.com", patterns) is True
    assert is_ignored_text("你好，欢迎来到这里", patterns) is False
    assert is_ignored_text("", patterns) is True


def test_filter_and_sort():
    """Kiểm tra lọc confidence và sắp xếp dòng từ trên xuống dưới, trái qua phải."""
    ignore = [r"抖音", r"@\w+"]

    det1 = OCRDetection(text="Dòng 2 Trái", confidence=0.9, box=OCRBox(x1=50, y1=650, x2=150, y2=680))
    det2 = OCRDetection(text="Dòng 1", confidence=0.85, box=OCRBox(x1=100, y1=610, x2=300, y2=640))
    det3 = OCRDetection(text="Dòng 2 Phải", confidence=0.95, box=OCRBox(x1=200, y1=650, x2=350, y2=680))
    det_low_conf = OCRDetection(text="Nhiễu mờ", confidence=0.4, box=OCRBox(x1=10, y1=600, x2=50, y2=620))
    det_watermark = OCRDetection(text="抖音号123", confidence=0.99, box=OCRBox(x1=10, y1=600, x2=100, y2=620))

    raw = [det1, det_low_conf, det3, det_watermark, det2]
    filtered = filter_and_sort_detections(raw, min_confidence=0.6, ignore_patterns=ignore, row_tolerance_px=20)

    # Đã lọc bỏ det_low_conf và det_watermark -> còn 3 mục
    assert len(filtered) == 3
    # Thứ tự phải là: Dòng 1 (y=610) -> Dòng 2 Trái (y=650, x=50) -> Dòng 2 Phải (y=650, x=200)
    assert filtered[0].text == "Dòng 1"
    assert filtered[1].text == "Dòng 2 Trái"
    assert filtered[2].text == "Dòng 2 Phải"

    merged = merge_detections_to_text(filtered)
    assert merged == "Dòng 1Dòng 2 TráiDòng 2 Phải"
