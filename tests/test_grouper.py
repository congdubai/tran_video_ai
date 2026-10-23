"""
Unit test kiểm tra thuật toán gom câu (group_cues) trong src/ocr/grouper.py.
Dành cho người mới làm quen Python & Pytest:
- Viết test bên Python với pytest rất đơn giản: chỉ cần viết các hàm bắt đầu bằng `test_...`
- Dùng từ khóa `assert` trực tiếp, không cần assertEquals hay assertThat dài dòng như Java JUnit.
"""

import sys
import os
import pytest

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import FrameOCRResult, OCRBox
from src.ocr.grouper import group_cues, calculate_similarity


def test_calculate_similarity():
    """Kiểm tra hàm đo độ tương đồng chuỗi difflib."""
    assert calculate_similarity("你好世界", "你好世界") == 1.0
    assert calculate_similarity("你好世界", "你好") >= 0.60
    assert calculate_similarity("今天天气很好", "今天天气真好") >= 0.80
    assert calculate_similarity("苹果", "香蕉") < 0.30
    assert calculate_similarity("", "") == 1.0


def test_group_cues_identical_frames():
    """Kiểm tra gom các khung hình giống nhau hoàn toàn thành 1 câu."""
    # Giả lập 4 khung hình liên tiếp (fps=4 => mỗi khung cách nhau 0.25s)
    box = OCRBox(x1=100, y1=600, x2=400, y2=640)
    frames = [
        FrameOCRResult(timestamp=0.00, frame_index=0, text="你好世界", boxes=[box]),
        FrameOCRResult(timestamp=0.25, frame_index=1, text="你好世界", boxes=[box]),
        FrameOCRResult(timestamp=0.50, frame_index=2, text="你好世界", boxes=[box]),
        FrameOCRResult(timestamp=0.75, frame_index=3, text="你好世界", boxes=[box]),
    ]

    cues = group_cues(frames, fps=4.0, sim_threshold=0.75, min_consecutive_frames=2)
    assert len(cues) == 1
    cue = cues[0]
    assert cue.id == 1
    assert cue.start == 0.00
    assert cue.end == 1.00  # 0.75 + (1/4) = 1.00
    assert cue.text_zh == "你好世界"
    assert len(cue.boxes) == 4


def test_group_cues_with_one_missing_empty_frame():
    """
    Kiểm tra tính năng: cho phép lỡ 1 mẫu trống mà không bị tách thành 2 câu.
    (Ví dụ frame 1 bị lỡ nhận diện rỗng "").
    """
    box = OCRBox(x1=100, y1=600, x2=400, y2=640)
    frames = [
        FrameOCRResult(timestamp=0.00, frame_index=0, text="今天天气很好", boxes=[box]),
        FrameOCRResult(timestamp=0.25, frame_index=1, text="", boxes=[]), # Bị lỡ 1 frame
        FrameOCRResult(timestamp=0.50, frame_index=2, text="今天天气很好", boxes=[box]),
        FrameOCRResult(timestamp=0.75, frame_index=3, text="今天天气很好", boxes=[box]),
    ]

    cues = group_cues(frames, fps=4.0, sim_threshold=0.75, min_consecutive_frames=2)
    assert len(cues) == 1
    assert cues[0].text_zh == "今天天气很好"
    assert cues[0].start == 0.00
    assert cues[0].end == 1.00


def test_group_cues_drop_noise():
    """Kiểm tra loại bỏ câu chỉ xuất hiện dưới 2 mẫu (nhiễu/chớp nháy)."""
    box = OCRBox(x1=100, y1=600, x2=400, y2=640)
    frames = [
        # Câu 1: Xuất hiện đúng 1 frame -> Nhiễu -> Phải bị loại
        FrameOCRResult(timestamp=0.00, frame_index=0, text="这是噪声", boxes=[box]),
        FrameOCRResult(timestamp=0.25, frame_index=1, text="", boxes=[]),
        FrameOCRResult(timestamp=0.50, frame_index=2, text="", boxes=[]),

        # Câu 2: Xuất hiện 3 frame -> Hợp lệ -> Phải giữ lại
        FrameOCRResult(timestamp=1.00, frame_index=4, text="这是正常字幕", boxes=[box]),
        FrameOCRResult(timestamp=1.25, frame_index=5, text="这是正常字幕", boxes=[box]),
        FrameOCRResult(timestamp=1.50, frame_index=6, text="这是正常字幕", boxes=[box]),
    ]

    cues = group_cues(frames, fps=4.0, sim_threshold=0.75, min_consecutive_frames=2)
    assert len(cues) == 1
    assert cues[0].text_zh == "这是正常字幕"
    assert cues[0].start == 1.00
    assert cues[0].end == 1.75


def test_group_cues_majority_voting():
    """
    Kiểm tra cơ chế bầu chọn (voting): Nếu có 1 frame bị nhận diện sai 1 chữ
    thì câu cuối cùng vẫn lấy theo số đông xuất hiện nhiều nhất.
    """
    box = OCRBox(x1=100, y1=600, x2=400, y2=640)
    frames = [
        FrameOCRResult(timestamp=0.00, frame_index=0, text="今天天气很好", boxes=[box]),
        FrameOCRResult(timestamp=0.25, frame_index=1, text="今天天气很好", boxes=[box]),
        FrameOCRResult(timestamp=0.50, frame_index=2, text="今天天气真好", boxes=[box]), # Lệch 1 chữ nhưng ratio >= 0.75
        FrameOCRResult(timestamp=0.75, frame_index=3, text="今天天气很好", boxes=[box]),
    ]

    cues = group_cues(frames, fps=4.0, sim_threshold=0.75, min_consecutive_frames=2)
    assert len(cues) == 1
    # "今天天气很好" xuất hiện 3 lần, "今天天气真好" xuất hiện 1 lần -> Chọn số đông
    assert cues[0].text_zh == "今天天气很好"
