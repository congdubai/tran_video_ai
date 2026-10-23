"""
Unit test kiểm tra tính toán vùng làm mờ (mask.py) và sinh phụ đề ASS tiếng Việt (ass_generator.py).
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import OCRBox, SubtitleCue
from src.subtitles.mask import calculate_blur_rect, compute_percentile, make_even
from src.subtitles.ass_generator import seconds_to_ass_time, generate_ass_file


def test_make_even():
    """Kiểm tra hàm làm tròn số chẵn."""
    assert make_even(10) == 10
    assert make_even(11) == 12
    assert make_even(0) == 0


def test_compute_percentile():
    """Kiểm tra tính phân vị 2 và 98."""
    values = list(range(1, 101)) # 1 đến 100
    p2 = compute_percentile(values, 2)
    p98 = compute_percentile(values, 98)
    assert p2 <= 5
    assert p98 >= 95


def test_calculate_blur_rect():
    """Kiểm tra tính toạ độ vùng làm mờ từ danh sách box."""
    boxes = [
        OCRBox(x1=100, y1=600, x2=400, y2=640),
        OCRBox(x1=110, y1=605, x2=390, y2=635),
        OCRBox(x1=95, y1=595, x2=405, y2=645),
    ]

    x, y, w, h = calculate_blur_rect(
        boxes=boxes,
        video_width=720,
        video_height=1280,
        font_size=40
    )

    # Đảm bảo kích thước chẵn
    assert w % 2 == 0
    assert h % 2 == 0
    # Đảm bảo chiều cao đủ chứa 2 dòng font 40 (ít nhất 40 * 2.8 = 112px)
    assert h >= 112
    # Đảm bảo nằm trong màn hình
    assert x >= 0 and y >= 0
    assert x + w <= 720
    assert y + h <= 1280


def test_calculate_blur_rect_manual():
    """Kiểm tra ghi đè toạ độ thủ công."""
    manual = (50, 500, 450, 650)
    x, y, w, h = calculate_blur_rect(
        boxes=[],
        video_width=1080,
        video_height=1920,
        font_size=40,
        manual_rect=manual
    )
    assert x == 50
    assert y == 500
    assert w == 400
    assert h == 150


def test_seconds_to_ass_time():
    """Kiểm tra định dạng thời gian ASS: H:MM:SS.cs."""
    assert seconds_to_ass_time(0.0) == "0:00:00.00"
    assert seconds_to_ass_time(1.5) == "0:00:01.50"
    assert seconds_to_ass_time(65.34) == "0:01:05.34"
    assert seconds_to_ass_time(3665.12) == "1:01:05.12"


def test_generate_ass_file(tmp_path):
    """Kiểm tra sinh file ASS có đầy đủ PlayRes, an5/pos và dấu tiếng Việt."""
    cues = [
        SubtitleCue(
            id=1,
            start=1.0,
            end=3.5,
            text_zh="你好，世界",
            text_vi="Xin chào, thế giới tuyệt vời! Ă Â Đ Ê Ô Ơ Ư"
        )
    ]
    blur_rect = (100, 600, 400, 100) # center: x=300, y=650
    out_ass = str(tmp_path / "test.ass")

    generate_ass_file(
        cues=cues,
        video_width=1280,
        video_height=720,
        blur_rect=blur_rect,
        output_ass_path=out_ass,
        font_name="Arial",
        font_size=32
    )

    assert os.path.exists(out_ass)
    with open(out_ass, "r", encoding="utf-8-sig") as f:
        content = f.read()

    assert "PlayResX: 1280" in content
    assert "PlayResY: 720" in content
    assert r"{\an5\pos(300,650)}Xin chào, thế giới tuyệt vời! Ă Â Đ Ê Ô Ơ Ư" in content
    assert "0:00:01.00" in content
    assert "0:00:03.50" in content
