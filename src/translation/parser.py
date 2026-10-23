"""
Module phân tích phản hồi JSON từ LLM một cách an toàn và chắc chắn (Robust JSON Parser).
Giải thích cho người mới:
- Các model AI (kể cả khi yêu cầu trả JSON) thỉnh thoảng vẫn kèm thêm dấu Markdown:
  ```json ... ``` hoặc lời chào mở đầu / kết bài.
- Module này sử dụng các kỹ thuật làm sạch chuỗi và regex bóc tách JSON
  để không bao giờ bị văng lỗi Crash (JSONDecodeError).
"""

import json
import re
from typing import Dict, Any, List


def clean_markdown_fences(text: str) -> str:
    """Loại bỏ các block Markdown ```json và ``` nếu LLM trả về."""
    clean = text.strip()
    # Bỏ ```json hoặc ``` ở đầu
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
    # Bỏ ``` ở cuối
    clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def extract_json_block(text: str) -> str:
    """
    Trích xuất đoạn chứa chuỗi JSON hợp lệ nhất (nằm giữa cặp {} hoặc []).
    Tránh các đoạn văn bản rác bên ngoài do LLM tự ý thêm vào.
    """
    text = clean_markdown_fences(text)

    # Thử tìm từ ngoặc nhọn đầu tiên đến ngoặc nhọn cuối cùng
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1]

    # Thử tìm ngoặc vuông [] nếu model trả trực tiếp một mảng
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket != -1 and last_bracket > first_bracket:
        return text[first_bracket:last_bracket + 1]

    return text


def parse_translation_response(raw_text: str) -> Dict[int, str]:
    """
    Phân tích chuỗi phản hồi thô từ LLM thành từ điển: {cue_id: text_vi}.
    Hỗ trợ cả 2 dạng phản hồi:
      1. {"items": [{"id": 1, "vi": "xin chào"}, ...]}
      2. [{"id": 1, "vi": "xin chào"}, ...]
    """
    cleaned_text = extract_json_block(raw_text)

    try:
        data = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        # Nếu vẫn không parse được JSON chuẩn, dùng regex trích xuất từng cặp "id" và "vi"
        fallback_map = {}
        pattern = r'\{\s*"id"\s*:\s*(\d+)\s*,\s*"(?:vi|text_vi)"\s*:\s*"([^"]+)"\s*\}'
        matches = re.findall(pattern, raw_text)
        for cid_str, vi_str in matches:
            fallback_map[int(cid_str)] = vi_str.strip()

        if fallback_map:
            return fallback_map

        raise ValueError(f"Không thể phân tích phản hồi JSON từ AI: {str(e)}\nNội dung thô: {raw_text[:200]}...")

    # Chuyển đổi dữ liệu đã nạp thành map {id: vi}
    result_map: Dict[int, str] = {}

    items = []
    if isinstance(data, dict):
        # Trường hợp chuẩn: {"items": [...]}
        items = data.get("items", [])
        if not items and "translations" in data:
            items = data["translations"]
    elif isinstance(data, list):
        # Trường hợp trả trực tiếp mảng JSON: [{...}, {...}]
        items = data

    for item in items:
        if isinstance(item, dict) and "id" in item:
            try:
                cid = int(item["id"])
                vi_text = item.get("vi", item.get("text_vi", "")).strip()
                result_map[cid] = vi_text
            except (ValueError, TypeError):
                continue

    return result_map
