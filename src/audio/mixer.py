"""
Module xuất video hoàn chỉnh: Làm mờ phụ đề cũ, phủ phụ đề ASS mới, và trộn âm thanh thuyết minh.
Giải thích cho người mới:
- Đây là bước cuối cùng kết hợp toàn bộ các thành phần: Hình ảnh (Video) + Phụ đề (ASS) + Giọng đọc (WAV).
- Xử lý âm thanh đa dạng:
  + Nếu video không có tiếng: Tự động dùng track thuyết minh làm âm thanh chính.
  + Nếu video có tiếng gốc:
    * Chế độ chuẩn: Hạ âm lượng gốc (mặc định 0.15 = 15%) rồi trộn với giọng đọc bằng `amix`.
    * Chế độ Ducking (--duck): Sử dụng bộ lọc cao cấp `sidechaincompress`.
      Âm thanh gốc sẽ tự động giảm nhỏ khi người thuyết minh bắt đầu nói,
      và tự động tăng to trở lại trong các khoảng lặng giữa hai câu đối thoại.
- Giữ nguyên 100% độ phân giải, tỉ lệ khung hình và độ dài của video gốc.
"""

import os
import subprocess
from typing import Tuple, Optional
from ..video_utils import get_video_info


def mix_video_and_audio(
    video_path: str,
    voice_track_wav: str,
    ass_path: str,
    blur_rect: Tuple[int, int, int, int],
    output_path: str,
    work_dir: str,
    mask_sigma: int = 30,
    keep_original_vol: float = 0.15,
    use_ducking: bool = False,
    fonts_dir: Optional[str] = None
) -> str:
    """
    Tạo video MP4 hoàn thiện (libx264, aac) với phụ đề mờ, phụ đề Việt và âm thanh thuyết minh chuẩn.
    """
    abs_video_path = os.path.abspath(video_path)
    abs_voice_path = os.path.abspath(voice_track_wav)
    abs_output_path = os.path.abspath(output_path)
    abs_work_dir = os.path.abspath(work_dir)
    os.makedirs(abs_work_dir, exist_ok=True)

    info = get_video_info(abs_video_path)
    has_audio = info.get("has_audio", False)
    x, y, w, h = blur_rect

    ass_filename = os.path.basename(ass_path)
    if fonts_dir:
        abs_fonts_dir = os.path.abspath(fonts_dir).replace("\\", "/")
        ass_filter = f"ass=filename='{ass_filename}':fontsdir='{abs_fonts_dir}'"
    else:
        ass_filter = f"ass=filename='{ass_filename}'"

    # Xây dựng nhánh lọc Video: Crop -> Blur -> Overlay -> ASS
    video_filter = (
        f"[0:v]split[base][sub];"
        f"[sub]crop={w}:{h}:{x}:{y},"
        f"gblur=sigma={mask_sigma}:steps=2,"
        f"eq=brightness=-0.08:saturation=0.9[blurred];"
        f"[base][blurred]overlay={x}:{y}[masked];"
        f"[masked]{ass_filter}[outv]"
    )

    # Xây dựng nhánh lọc Audio
    if not has_audio:
        # Trường hợp 1: Video gốc câm (không có audio stream)
        audio_filter = "[1:a]aformat=channel_layouts=stereo:sample_rates=44100[outa]"
    elif use_ducking:
        # Trường hợp 2: Bật Ducking (Sidechain compression tự động hạ nhạc nền khi có lời)
        audio_filter = (
            f"[0:a][1:a]sidechaincompress=threshold=0.08:ratio=5:attack=15:release=300[ducked_orig];"
            f"[ducked_orig]volume={max(0.05, keep_original_vol * 1.5):.2f}[bg];"
            f"[bg][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[outa]"
        )
    else:
        # Trường hợp 3: Hạ âm lượng gốc cố định (mặc định 0.15) và amix
        audio_filter = (
            f"[0:a]volume={keep_original_vol:.3f}[orig_low];"
            f"[orig_low][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[outa]"
        )

    full_filter_complex = f"{video_filter};{audio_filter}"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", abs_video_path,
        "-i", abs_voice_path,
        "-filter_complex", full_filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        abs_output_path
    ]

    print("=" * 60)
    print("[*] Đang kết xuất video cuối cùng (Mã hoá H.264 CRF 20, âm thanh AAC 192k)...")
    if has_audio:
        mode_str = "Sidechain Ducking tự động" if use_ducking else f"Hạ cố định ({keep_original_vol * 100:.0f}%)"
        print(f"[*] Chế độ trộn âm thanh: Giữ tiếng gốc [{mode_str}] + Thuyết minh tiếng Việt")
    else:
        print("[*] Video không có âm thanh gốc -> Đặt track thuyết minh làm âm thanh chính.")

    result = subprocess.run(
        cmd,
        cwd=abs_work_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg thất bại khi kết xuất video:\n{result.stderr[-1000:]}")

    print(f"[+] KẾT XUẤT THÀNH CÔNG: {abs_output_path}")
    return abs_output_path
