"""
Module lọc và sắp xếp kết quả OCR thô.
Giải thích cho người mới:
- Khi OCR nhận diện các dòng chữ, toạ độ trả về có thể xáo trộn ngẫu nhiên.
- Ta cần sắp xếp các dòng theo thứ tự tự nhiên (từ trên xuống dưới, từ trái sang phải).
- Đồng thời lọc bỏ các ký tự watermark rác (Douyin, TikTok, ID tài khoản...).
"""

import re
from typing import List
from ..config import OCRDetection, OCRBox


def is_ignored_text(text: str, ignore_patterns: List[str]) -> bool:
    """
    Kiểm tra xem chuỗi có khớp với danh sách regex loại trừ (watermark, ID kênh...) hay không.
    Ví dụ: '抖音', 'douyin', '@user123'
    """
    clean_text = text.strip()
    if not clean_text:
        return True

    for pattern in ignore_patterns:
        if re.search(pattern, clean_text, re.IGNORECASE):
            return True
    return False


def filter_and_sort_detections(
    detections: List[OCRDetection],
    min_confidence: float = 0.6,
    ignore_patterns: List[str] = None,
    row_tolerance_px: int = 15
) -> List[OCRDetection]:
    """
    1. Lọc bỏ các kết quả có độ tin cậy < min_confidence
    2. Lọc bỏ các kết quả chứa từ khoá watermark theo regex
    3. Sắp xếp lại danh sách: dòng trên xếp trước, nếu cùng dòng thì xếp từ trái sang phải.
       (row_tolerance_px: khoảng cách lệch trục Y tối đa để vẫn coi là cùng 1 dòng).
    """
    if ignore_patterns is None:
        ignore_patterns = [r"抖音", r"douyin", r"@\w+"]

    valid = []
    for d in detections:
        if d.confidence < min_confidence:
            continue
        if is_ignored_text(d.text, ignore_patterns):
            continue
        valid.append(d)

    # Sắp xếp theo dòng: gom các box có y1 xấp xỉ nhau vào cùng 1 hàng rồi sắp x1
    def sort_key(item: OCRDetection):
        row_bucket = item.box.y1 // row_tolerance_px
        return (row_bucket, item.box.x1)

    valid.sort(key=sort_key)
    return valid


def merge_detections_to_text(detections: List[OCRDetection]) -> str:
    """
    Nối danh sách các dòng chữ đã qua lọc thành 1 chuỗi văn bản hoàn chỉnh.
    Tiếng Trung viết liền nhau không có dấu cách nên ghép trực tiếp.
    """
    texts = [d.text.strip() for d in detections if d.text.strip()]
    return "".join(texts)
