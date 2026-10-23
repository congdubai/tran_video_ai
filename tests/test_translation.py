"""
Unit test kiểm tra hệ thống Dịch thuật (Robust JSON parsing, Batching, Echo provider).
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import SubtitleCue
from src.translation.parser import (
    clean_markdown_fences,
    extract_json_block,
    parse_translation_response
)
from src.translation.batch import (
    calculate_max_words,
    translate_cues_in_batches
)
from src.translation.echo import EchoTranslator


def test_clean_markdown_fences():
    """Kiểm tra loại bỏ code block markdown ```json."""
    raw1 = "```json\n{\"items\": []}\n```"
    assert clean_markdown_fences(raw1) == "{\"items\": []}"

    raw2 = "```JSON\n{\"items\": []}\n```"
    assert clean_markdown_fences(raw2) == "{\"items\": []}"

    raw3 = "{\"items\": []}"
    assert clean_markdown_fences(raw3) == "{\"items\": []}"


def test_extract_json_block_with_conversational_text():
    """Kiểm tra trích xuất JSON khi AI nói chuyện thêm trước và sau JSON."""
    raw = (
        "Chào bạn, dưới đây là kết quả dịch sang tiếng Việt:\n\n"
        "```json\n"
        "{\n"
        '  "items": [\n'
        '    {"id": 1, "vi": "Xin chào thế giới"},\n'
        '    {"id": 2, "vi": "Hôm nay trời đẹp"}\n'
        "  ]\n"
        "}\n"
        "```\n"
        "Chúc bạn một ngày tốt lành!"
    )
    extracted = extract_json_block(raw)
    result_map = parse_translation_response(extracted)
    assert result_map[1] == "Xin chào thế giới"
    assert result_map[2] == "Hôm nay trời đẹp"


def test_parse_translation_response_array_format():
    """Kiểm tra nếu AI trả về trực tiếp mảng JSON [{...}, {...}]."""
    raw = '[{"id": 10, "vi": "Câu mười"}, {"id": 11, "vi": "Câu mười một"}]'
    result_map = parse_translation_response(raw)
    assert result_map[10] == "Câu mười"
    assert result_map[11] == "Câu mười một"


def test_calculate_max_words():
    """Kiểm tra tính số từ tối đa dựa trên thời lượng câu."""
    # Câu 1.0 giây -> round(1.0 * 5.5) = 6 từ
    assert calculate_max_words(0.0, 1.0) == 6

    # Câu rất ngắn (0.2 giây) -> vẫn đảm bảo tối thiểu 3 từ
    assert calculate_max_words(0.0, 0.2) == 3

    # Câu dài 4.0 giây -> round(4.0 * 5.5) = 22 từ
    assert calculate_max_words(1.0, 5.0) == 22


def test_echo_translator_batching():
    """Kiểm tra quy trình dịch theo lô với EchoTranslator."""
    cues = [
        SubtitleCue(id=1, start=0.0, end=2.0, text_zh="你好"),
        SubtitleCue(id=2, start=2.0, end=4.0, text_zh="欢迎光临"),
        SubtitleCue(id=3, start=4.0, end=6.0, text_zh="谢谢")
    ]

    translator = EchoTranslator()
    translated = translate_cues_in_batches(cues, translator, batch_size=2, context_count=1)

    assert len(translated) == 3
    assert translated[0].text_vi == "[Dịch 1] 你好"
    assert translated[1].text_vi == "[Dịch 2] 欢迎光临"
    assert translated[2].text_vi == "[Dịch 3] 谢谢"
