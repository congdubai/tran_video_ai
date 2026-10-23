"""
Module điều phối dịch theo lô (Batch Processing), quản lý ngữ cảnh và giới hạn độ dài từ.
Giải thích cho người mới:
- Nếu dịch từng câu một (15 câu = 15 request), tốc độ sẽ rất chậm và câu sau không hiểu ngữ cảnh câu trước.
- Dịch theo lô 15 câu giúp gộp request, đồng thời gửi kèm 3 câu trước đã dịch để model hiểu mạch phim.
- Quy tắc quan trọng: max_words = max(3, round(thời_lượng_giây * 5.5))
  Giúp câu dịch ngắn gọn, tránh tình trạng phụ đề hiển thị 1.5 giây mà câu dịch dài 15 từ,
  khiến giọng đọc thuyết minh bị đuổi không kịp hình.
"""

import json
import os
from typing import List, Dict, Any, Optional
from ..config import SubtitleCue, OCRBox
from .base import BaseTranslator
from .parser import parse_translation_response


def calculate_max_words(start: float, end: float, words_per_sec: float = 5.5) -> int:
    """
    Tính số từ tối đa cho câu dịch dựa trên thời lượng hiển thị trên màn hình.
    Tối thiểu là 3 từ để câu có nghĩa đầy đủ.
    """
    duration = max(0.5, end - start)
    return max(3, int(round(duration * words_per_sec)))


def build_system_prompt() -> str:
    """System prompt hướng dẫn AI dịch đúng văn phong thuyết minh và tuân thủ định dạng JSON."""
    return (
        "Bạn là chuyên gia dịch thuật phụ đề phim và thuyết minh video ngắn từ tiếng Trung sang tiếng Việt.\n"
        "Quy tắc tối quan trọng:\n"
        "1. Dịch chuẩn xác, tự nhiên, thuần Việt, đúng văn cảnh đối thoại/thuyết minh.\n"
        "2. ĐẶC BIỆT LƯU Ý: Mỗi câu có tham số 'max_words'. Độ dài bản dịch tiếng Việt KHÔNG ĐƯỢC VƯỢT QUÁ 'max_words' "
        "để giọng thuyết minh đọc kịp thời lượng video.\n"
        "3. Tuyệt đối CHỈ TRẢ VỀ JSON hợp lệ duy nhất theo định dạng:\n"
        '{"items": [{"id": 1, "vi": "bản dịch tiếng Việt"}]}\n'
        "Không thêm bất kỳ lời dẫn hay giải thích nào ngoài chuỗi JSON."
    )


def build_user_prompt(
    batch_cues: List[SubtitleCue],
    context_cues: List[SubtitleCue]
) -> str:
    """
    Tạo nội dung user prompt gửi model gồm:
    - 3 câu trước làm ngữ cảnh (nếu có)
    - Danh sách câu hiện tại cần dịch kèm id, text và max_words
    """
    context_items = []
    for c in context_cues:
        if c.text_vi:
            context_items.append({
                "id": c.id,
                "zh": c.text_zh,
                "vi": c.text_vi
            })

    current_items = []
    for c in batch_cues:
        max_w = calculate_max_words(c.start, c.end)
        current_items.append({
            "id": c.id,
            "text": c.text_zh,
            "max_words": max_w
        })

    prompt_data = {
        "context_previous_translated": context_items,
        "sentences_to_translate": current_items
    }

    return (
        "Hãy dịch danh sách các câu tiếng Trung sau sang tiếng Việt, tuân thủ giới hạn max_words cho từng câu:\n"
        + json.dumps(prompt_data, ensure_ascii=False, indent=2)
    )


def translate_cues_in_batches(
    cues: List[SubtitleCue],
    translator: BaseTranslator,
    batch_size: int = 15,
    context_count: int = 3
) -> List[SubtitleCue]:
    """
    Dịch toàn bộ danh sách SubtitleCue theo lô batch_size.
    - Gửi kèm context_count câu đã dịch trước đó.
    - Bắt lỗi và thử lại (retry) nếu model bỏ sót câu.
    - Nếu vẫn lỗi, giữ nguyên text gốc và in cảnh báo.
    """
    if not cues:
        return []

    print(f"[*] Bắt đầu dịch {len(cues)} câu bằng [{translator.name}]...")
    print(f"[*] Kích thước lô: {batch_size} câu/lần | Ngữ cảnh gửi kèm: {context_count} câu trước.")

    system_prompt = build_system_prompt()
    translated_cues = list(cues)  # Tạo bản sao danh sách

    for i in range(0, len(translated_cues), batch_size):
        batch = translated_cues[i:i + batch_size]
        batch_ids = {c.id for c in batch}

        # Lấy tối đa context_count câu vừa dịch ngay trước đó
        context_start = max(0, i - context_count)
        context = translated_cues[context_start:i]

        user_prompt = build_user_prompt(batch, context)

        print(f"  -> Đang dịch lô câu id {min(batch_ids)} đến {max(batch_ids)}...")

        try:
            raw_response = translator.translate_prompt(system_prompt, user_prompt)
            result_map = parse_translation_response(raw_response)
        except Exception as e:
            print(f"     [!] Cảnh báo lỗi lô: {str(e)}. Đang thử lại từng câu...")
            result_map = {}

        # Kiểm tra những câu bị thiếu trong kết quả trả về
        missing_cues = [c for c in batch if c.id not in result_map or not result_map[c.id].strip()]

        if missing_cues:
            print(f"     [!] Có {len(missing_cues)} câu chưa nhận được bản dịch. Đang thử lại (Retry)...")
            retry_prompt = build_user_prompt(missing_cues, context)
            try:
                raw_retry = translator.translate_prompt(system_prompt, retry_prompt)
                retry_map = parse_translation_response(raw_retry)
                result_map.update(retry_map)
            except Exception as retry_err:
                print(f"     [!] Retry thất bại: {retry_err}")

        # Gán bản dịch vào các câu trong batch
        for cue in batch:
            if cue.id in result_map and result_map[cue.id].strip():
                cue.text_vi = result_map[cue.id].strip()
            else:
                # Nếu vẫn lỗi, giữ nguyên bản gốc và in cảnh báo
                cue.text_vi = cue.text_zh
                print(f"     [CẢNH BÁO] Không thể dịch câu #{cue.id} ('{cue.text_zh}'). Giữ nguyên văn bản gốc.")

    print(f"[+] Hoàn thành dịch {len(translated_cues)} câu.")
    return translated_cues


def save_cues_vi(cues: List[SubtitleCue], file_path: str):
    """Lưu danh sách câu đã dịch sang file work/cues_vi.json."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    data = []
    for c in cues:
        data.append({
            "id": c.id,
            "start": c.start,
            "end": c.end,
            "text_zh": c.text_zh,
            "text_vi": c.text_vi or c.text_zh,
            "boxes": [{"x1": b.x1, "y1": b.y1, "x2": b.x2, "y2": b.y2} for b in c.boxes]
        })

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_cues_vi(file_path: str) -> List[SubtitleCue]:
    """Tải lại danh sách câu đã dịch từ file work/cues_vi.json để tái sử dụng."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cues = []
    for item in data:
        boxes = [
            OCRBox(x1=b["x1"], y1=b["y1"], x2=b["x2"], y2=b["y2"])
            for b in item.get("boxes", [])
        ]
        cues.append(
            SubtitleCue(
                id=item["id"],
                start=item["start"],
                end=item["end"],
                text_zh=item["text_zh"],
                text_vi=item.get("text_vi", item["text_zh"]),
                boxes=boxes
            )
        )
    return cues
