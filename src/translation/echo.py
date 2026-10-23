"""
Bộ máy dịch giả lập (Echo / Mock Translator).
Dùng để chạy Unit Test hoặc kiểm thử toàn bộ đường ống mà không cần mạng hoặc model thật.
"""

import json
import re
from .base import BaseTranslator


class EchoTranslator(BaseTranslator):
    """
    Provider giả: nhận câu nào trả về '[Dịch] ' + câu đó.
    Tự động sinh cấu trúc JSON chuẩn `{"items":[{"id":..., "vi":"..."}]}`.
    """

    @property
    def name(self) -> str:
        return "Echo (Mock / Testing)"

    def translate_prompt(self, system_prompt: str, user_prompt: str) -> str:
        # Tìm danh sách ID và text từ user_prompt
        # Cấu trúc gửi đi thường có dạng: {"id": 1, "text": "...", "max_words": ...}
        items = []

        # Dùng regex trích xuất các object {"id": ..., "text": "..."}
        pattern = r'\{\s*"id":\s*(\d+),\s*"text":\s*"([^"]+)"'
        matches = re.findall(pattern, user_prompt)

        if matches:
            for cue_id_str, text_zh in matches:
                cue_id = int(cue_id_str)
                items.append({
                    "id": cue_id,
                    "vi": f"[Dịch {cue_id}] {text_zh}"
                })
        else:
            # Fallback nếu user_prompt không khớp regex chuẩn
            items.append({"id": 1, "vi": "[Echo] Câu dịch thử nghiệm"})

        return json.dumps({"items": items}, ensure_ascii=False)
