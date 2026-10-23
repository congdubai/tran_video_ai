"""
Module gom cụm các khung hình OCR liên tiếp thành từng câu phụ đề hoàn chỉnh.
Giải thích cho người mới:
- Khi trích xuất ở fps=4, một câu phụ đề hiển thị 2 giây sẽ xuất hiện trong khoảng 8 khung hình.
- Do nhiễu hình ảnh, chữ nhận diện qua các khung có thể hơi khác nhau một vài ký tự.
- Ta dùng thư viện chuẩn `difflib.SequenceMatcher` để so sánh độ tương đồng chuỗi.
- Nếu độ tương đồng >= 0.75, coi như là cùng một câu.
- Thuật toán cho phép lỡ tối đa 1 khung hình trống (giả sử OCR bị miss 1 frame).
- Sau khi gom nhóm:
  + start: Thời điểm bắt đầu của khung đầu tiên trong nhóm.
  + end: Thời điểm kết thúc của khung cuối cùng (+ thời gian 1 frame).
  + text: Bầu chọn (majority vote) câu xuất hiện nhiều lần nhất trong nhóm.
  + Lọc nhiễu: Bỏ các câu chỉ xuất hiện < 2 mẫu (thường là khung chớp nháy hoặc rác).
"""

from collections import Counter
import difflib
from typing import List, Dict, Any
from ..config import FrameOCRResult, SubtitleCue, OCRBox


def calculate_similarity(s1: str, s2: str) -> float:
    """Tính độ tương đồng giữa hai chuỗi ký tự theo tỉ lệ [0.0, 1.0]."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def group_cues(
    frame_results: List[FrameOCRResult],
    fps: float = 4.0,
    sim_threshold: float = 0.75,
    min_consecutive_frames: int = 2
) -> List[SubtitleCue]:
    """
    Gom các FrameOCRResult liên tiếp thành danh sách SubtitleCue.
    """
    if not frame_results:
        return []

    frame_duration = 1.0 / fps if fps > 0 else 0.25

    clusters: List[List[FrameOCRResult]] = []
    current_cluster: List[FrameOCRResult] = []
    consecutive_empty = 0

    for res in frame_results:
        clean_text = res.text.strip()

        if clean_text:
            if not current_cluster:
                current_cluster = [res]
                consecutive_empty = 0
            else:
                # Lấy text phổ biến nhất trong cluster hiện tại để so sánh
                texts = [r.text.strip() for r in current_cluster]
                rep_text = Counter(texts).most_common(1)[0][0]

                sim = calculate_similarity(rep_text, clean_text)
                if sim >= sim_threshold:
                    current_cluster.append(res)
                    consecutive_empty = 0
                else:
                    # Chuỗi mới khác biệt hoàn toàn -> đóng cụm cũ và mở cụm mới
                    clusters.append(current_cluster)
                    current_cluster = [res]
                    consecutive_empty = 0
        else:
            # Khung hình rỗng (không phát hiện chữ)
            if current_cluster:
                consecutive_empty += 1
                if consecutive_empty > 1:
                    # Đã trống liên tiếp quá 1 khung hình -> chốt cụm phụ đề
                    clusters.append(current_cluster)
                    current_cluster = []
                    consecutive_empty = 0

    if current_cluster:
        clusters.append(current_cluster)

    # Lọc và tạo SubtitleCue
    cues: List[SubtitleCue] = []
    cue_id = 1

    for cluster in clusters:
        # Bỏ qua cụm chỉ xuất hiện dưới min_consecutive_frames mẫu (chống nhiễu)
        if len(cluster) < min_consecutive_frames:
            continue

        start_time = round(cluster[0].timestamp, 3)
        end_time = round(cluster[-1].timestamp + frame_duration, 3)

        # Bầu chọn câu văn bản đại diện xuất hiện nhiều nhất
        text_counts = Counter(r.text.strip() for r in cluster)
        best_text = text_counts.most_common(1)[0][0]

        # Thu thập toàn bộ bounding box
        all_boxes: List[OCRBox] = []
        for r in cluster:
            all_boxes.extend(r.boxes)

        cues.append(
            SubtitleCue(
                id=cue_id,
                start=start_time,
                end=end_time,
                text_zh=best_text,
                boxes=all_boxes
            )
        )
        cue_id += 1

    return cues


def cues_to_json_dict(cues: List[SubtitleCue]) -> List[Dict[str, Any]]:
    """Chuyển đổi danh sách SubtitleCue sang dạng dict để ghi file JSON."""
    result = []
    for c in cues:
        result.append({
            "id": c.id,
            "start": c.start,
            "end": c.end,
            "text_zh": c.text_zh,
            "text_vi": c.text_vi,
            "boxes": [{"x1": b.x1, "y1": b.y1, "x2": b.x2, "y2": b.y2} for b in c.boxes]
        })
    return result


def json_dict_to_cues(data: List[Dict[str, Any]]) -> List[SubtitleCue]:
    """Khôi phục danh sách SubtitleCue từ dữ liệu file JSON (để tái sử dụng cache)."""
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
                text_vi=item.get("text_vi"),
                boxes=boxes
            )
        )
    return cues
