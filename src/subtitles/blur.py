"""
Module làm mờ phụ đề cũ bằng FFmpeg và phủ phụ đề ASS mới lên video.
Giải thích cho người mới:
- Quy trình FFmpeg Filter Graph:
  1. `[0:v]split[base][sub]`: Tách luồng video làm 2 nhánh.
  2. `[sub]crop=w:h:x:y`: Cắt đúng vùng phụ đề cũ.
  3. `gblur=sigma=30:steps=2`: Áp dụng bộ lọc Gaussian Blur làm mờ chữ Trung Quốc.
  4. `eq=brightness=-0.08:saturation=0.9`: Hạ sáng nhẹ vùng mờ để làm nền tối tự nhiên cho chữ mới.
  5. `[base][blurred]overlay=x:y`: Đè lại vùng đã mờ vào đúng vị trí cũ trên khung hình.
  6. `ass=filename='subtitles.ass'`: Dùng libass vẽ phụ đề tiếng Việt lên trên cùng.
- QUY TẮC CỰC KỲ QUAN TRỌNG:
  Trên hệ điều hành Windows, đường dẫn tuyệt đối chứa dấu hai chấm ':' (ví dụ D:\video\sub.ass),
  dấu này gây xung đột nghiêm trọng với cú pháp filter của FFmpeg.
  Giải pháp chuẩn: Chạy subprocess với `cwd=work_dir` và truyền đường dẫn tương đối đơn giản `subtitles.ass`.
"""

import os
import subprocess
from typing import Tuple, Optional
from ..video_utils import get_video_info


def export_video_with_blurred_subtitles(
    video_path: str,
    ass_path: str,
    blur_rect: Tuple[int, int, int, int],
    output_path: str,
    work_dir: str,
    mask_sigma: int = 30,
    fonts_dir: Optional[str] = None
) -> str:
    """
    Xuất video mới có phụ đề cũ đã làm mờ và phụ đề tiếng Việt in cứng lên hình.
    (Phiên bản M3: giữ âm thanh gốc nếu có, chưa gắn thuyết minh).
    """
    abs_video_path = os.path.abspath(video_path)
    abs_output_path = os.path.abspath(output_path)
    abs_work_dir = os.path.abspath(work_dir)
    os.makedirs(abs_work_dir, exist_ok=True)

    info = get_video_info(abs_video_path)
    x, y, w, h = blur_rect

    # Lấy tên file ASS tương đối bên trong work_dir
    ass_filename = os.path.basename(ass_path)

    # Xây dựng filter ASS
    if fonts_dir:
        abs_fonts_dir = os.path.abspath(fonts_dir).replace("\\", "/")
        ass_filter = f"ass=filename='{ass_filename}':fontsdir='{abs_fonts_dir}'"
    else:
        ass_filter = f"ass=filename='{ass_filename}'"

    # Chuỗi Filter Complex kết hợp Crop + Gaussian Blur + Đổi độ sáng + Overlay + ASS
    filter_complex = (
        f"[0:v]split[base][sub];"
        f"[sub]crop={w}:{h}:{x}:{y},"
        f"gblur=sigma={mask_sigma}:steps=2,"
        f"eq=brightness=-0.08:saturation=0.9[blurred];"
        f"[base][blurred]overlay={x}:{y}[masked];"
        f"[masked]{ass_filter}[outv]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", abs_video_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
    ]

    # Nếu video gốc có âm thanh thì giữ nguyên luồng âm thanh
    if info.get("has_audio"):
        cmd.extend(["-map", "0:a?", "-c:a", "copy"])

    cmd.extend([
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "medium",
        abs_output_path
    ])

    print(f"[*] Đang thực thi FFmpeg xử lý làm mờ (sigma={mask_sigma}) và chèn phụ đề ASS...")
    # Chạy với cwd=abs_work_dir để tránh lỗi dấu hai chấm ':' trên Windows
    result = subprocess.run(
        cmd,
        cwd=abs_work_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg thất bại khi xuất video:\n{result.stderr[-1000:]}")

    print(f"[+] Đã xuất video hoàn tất tại: {abs_output_path}")
    return abs_output_path
