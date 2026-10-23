"""
Module tính toán hình chữ nhật làm mờ phụ đề cũ (Blur Mask Rectangle).
Giải thích cho người mới:
- Khi OCR nhận diện hàng nghìn khung hình, thỉnh thoảng có vài box bị lệch toạ độ (outlier).
- Thay vì lấy min/max tuyệt đối (dễ bị phình to do vài box rác), ta dùng phân vị Percentile 2% và 98%.
- Sau đó đệm thêm lề (padding) trên dưới trái phải để bao trọn chữ và đảm bảo
  chiều cao vùng làm mờ đủ chứa ít nhất 2 dòng phụ đề tiếng Việt.
- Kích thước w và h bắt buộc phải là số chẵn vì bộ mã hoá video yuv420p yêu cầu kích thước chia hết cho 2.
"""

from typing import List, Tuple, Optional
from ..config import OCRBox


def compute_percentile(values: List[int], p: float) -> int:
    """
    Tính phân vị thứ p (0 đến 100) bằng thuật toán chuẩn (không phụ thuộc vào numpy).
    """
    if not values:
        return 0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    d = k - f
    return int(round(sorted_v[f] + d * (sorted_v[c] - sorted_v[f])))


def make_even(n: int) -> int:
    """Làm tròn số nguyên về số chẵn gần nhất (FFmpeg yêu cầu chẵn pixel)."""
    return n if n % 2 == 0 else n + 1


def calculate_blur_rect(
    boxes: List[OCRBox],
    video_width: int,
    video_height: int,
    font_size: int,
    manual_rect: Optional[Tuple[int, int, int, int]] = None
) -> Tuple[int, int, int, int]:
    """
    Tính toán toạ độ hình chữ nhật (x, y, w, h) để làm mờ.
    Nếu manual_rect được chỉ định (x1, y1, x2, y2), sẽ dùng trực tiếp toạ độ đó.
    """
    if manual_rect:
        mx1, my1, mx2, my2 = manual_rect
        x = max(0, min(mx1, mx2))
        y = max(0, min(my1, my2))
        w = make_even(max(10, abs(mx2 - mx1)))
        h = make_even(max(10, abs(my2 - my1)))
        return x, y, min(w, video_width - x), min(h, video_height - y)

    # Nếu không có box nào phát hiện được, mặc định lấy dải 15% ở đáy video
    if not boxes:
        default_h = make_even(int(video_height * 0.15))
        default_y = make_even(int(video_height * 0.80))
        return 0, default_y, video_width, default_h

    # Thu thập toạ độ các góc từ tất cả các bounding box
    all_x1 = [b.x1 for b in boxes]
    all_y1 = [b.y1 for b in boxes]
    all_x2 = [b.x2 for b in boxes]
    all_y2 = [b.y2 for b in boxes]

    # Tính percentile 2 và 98
    p2_x1 = compute_percentile(all_x1, 2)
    p2_y1 = compute_percentile(all_y1, 2)
    p98_x2 = compute_percentile(all_x2, 98)
    p98_y2 = compute_percentile(all_y2, 98)

    # Đệm thêm lề (padding)
    pad_x = int(video_width * 0.03)   # Đệm ngang 3%
    pad_y = int(video_height * 0.015) # Đệm dọc 1.5%

    x1 = max(0, p2_x1 - pad_x)
    y1 = max(0, p2_y1 - pad_y)
    x2 = min(video_width, p98_x2 + pad_x)
    y2 = min(video_height, p98_y2 + pad_y)

    # Đảm bảo chiều cao vùng làm mờ đủ chứa ít nhất 2 dòng phụ đề tiếng Việt
    min_required_height = int(font_size * 2.8)
    current_h = y2 - y1

    if current_h < min_required_height:
        diff = min_required_height - current_h
        # Mở rộng đều lên trên và xuống dưới
        y1 = max(0, y1 - diff // 2)
        y2 = min(video_height, y1 + min_required_height)

    # Căn chỉnh chẵn số pixel
    x = make_even(x1)
    y = make_even(y1)
    w = make_even(x2 - x1)
    h = make_even(y2 - y1)

    # Đảm bảo không tràn màn hình
    if x + w > video_width:
        w = video_width - x
    if y + h > video_height:
        h = video_height - y

    return x, y, w, h
