"""
Module tiện ích làm việc với Video thông qua FFmpeg và FFprobe.
Giải thích cho lập trình viên Java/React:
- FFmpeg là công cụ dòng lệnh xử lý multimedia mạnh mẽ nhất thế giới.
- Thay vì nạp cả video vào RAM (rất nặng), ta gọi lệnh FFmpeg dưới dạng subprocess
  (tương tự Runtime.getRuntime().exec() bên Java hoặc child_process.spawn bên Node.js).
- FFprobe dùng để lấy thông số kỹ thuật (metadata) như kích thước, thời lượng, âm thanh...
"""

import json
import os
import subprocess
from typing import Dict, Any, Tuple, Optional


def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Lấy thông tin chi tiết của video bằng ffprobe:
    - width, height: Độ phân giải
    - duration: Thời lượng (giây)
    - fps: Tốc độ khung hình
    - has_audio: Video có luồng âm thanh hay không
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")

    # Lệnh ffprobe trả về định dạng JSON cấu trúc các stream và format
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)
    except FileNotFoundError:
        raise RuntimeError("Không tìm thấy lệnh 'ffprobe'. Vui lòng kiểm tra đã cài FFmpeg và cấu hình PATH chưa.")
    except Exception as e:
        raise RuntimeError(f"Lỗi khi đọc metadata video '{video_path}': {str(e)}")

    video_stream = None
    has_audio = False

    for s in data.get("streams", []):
        codec_type = s.get("codec_type")
        if codec_type == "video" and video_stream is None:
            video_stream = s
        elif codec_type == "audio":
            has_audio = True

    if not video_stream:
        raise ValueError(f"File '{video_path}' không chứa luồng video hợp lệ.")

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    # Tính FPS từ r_frame_rate (ví dụ '30/1' hoặc '24000/1001')
    fps_str = video_stream.get("r_frame_rate", "25/1")
    try:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) > 0 else 25.0
    except Exception:
        fps = 25.0

    # Lấy duration từ format hoặc stream
    duration = float(data.get("format", {}).get("duration", video_stream.get("duration", 0.0)))

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "has_audio": has_audio
    }


def generate_preview_region(
    video_path: str,
    region: Tuple[float, float],
    output_image_path: str,
    time_offset: float = 1.0
) -> str:
    """
    Xuất 1 khung hình từ video và vẽ khung chữ nhật viền đỏ bao quanh vùng phụ đề cần OCR.
    Giúp người dùng dễ dàng kiểm tra tham số --region (y_min, y_max).

    Kỹ thuật FFmpeg:
    -ss {time_offset}: Nhảy nhanh đến giây thứ time_offset
    -vf drawbox=...: Dùng bộ lọc video vẽ hộp viền đỏ (red) dày 4px
    """
    info = get_video_info(video_path)
    width = info["width"]
    height = info["height"]

    # Đảm bảo time_offset không vượt quá thời lượng video
    if info["duration"] > 0 and time_offset >= info["duration"]:
        time_offset = max(0.0, info["duration"] / 2.0)

    y_min_ratio, y_max_ratio = region
    y1 = int(y_min_ratio * height)
    y2 = int(y_max_ratio * height)
    box_h = max(10, y2 - y1)

    os.makedirs(os.path.dirname(os.path.abspath(output_image_path)), exist_ok=True)

    # Filter FFmpeg: vẽ hộp đỏ ở toạ độ x=0, y=y1, w=width, h=box_h, thickness=4
    vf_filter = f"drawbox=x=0:y={y1}:w={width}:h={box_h}:color=red@0.9:t=4"

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(time_offset),
        "-i", video_path,
        "-vf", vf_filter,
        "-vframes", "1",
        "-update", "1",
        output_image_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg thất bại khi tạo preview: {result.stderr}")

    return output_image_path
