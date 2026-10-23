"""
Module co giãn tốc độ âm thanh tự động (FFmpeg atempo) để khớp thời lượng video.
Giải thích cho người mới:
- Khi dịch tiếng Trung sang tiếng Việt, số âm tiết tiếng Việt thường dài hơn.
- Nếu giọng đọc dài hơn khoảng thời gian cho phép (từ lúc bắt đầu câu đến lúc câu kế tiếp xuất hiện),
  ta dùng bộ lọc `atempo` của FFmpeg để tăng tốc độ nói (tối đa --max-tempo, mặc định 1.35x).
- `atempo` có ưu điểm vượt trội: tăng tốc độ nói nhưng GIỮ NGUYÊN CAO ĐỘ (pitch),
  không làm giọng bị biến dạng the thé như tiếng sóc chuột.
- Nếu sau khi tăng tốc tối đa 1.35x mà vẫn bị dài, âm thanh được phép lấn sang khoảng lặng kế tiếp
  (không bị cắt cụt) và đánh dấu cảnh báo (overflow) để người dùng biết và rút gọn bản dịch.
"""

import os
import subprocess
import wave
from typing import Tuple


def get_wav_duration(wav_path: str) -> float:
    """Lấy thời lượng chính xác của file WAV (giây)."""
    with wave.open(wav_path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def adjust_audio_speed(
    input_wav: str,
    output_wav: str,
    available_window: float,
    max_tempo: float = 1.35,
    sample_rate: int = 24000
) -> Tuple[float, bool]:
    """
    Tự động tính toán và điều chỉnh tốc độ đọc nếu câu âm thanh dài hơn available_window.
    Trả về: (thời_lượng_mới, có_bị_tràn_hay_không)
    """
    orig_duration = get_wav_duration(input_wav)

    # Nếu câu đọc vừa vặn trong thời gian cho phép
    if orig_duration <= available_window or available_window <= 0.1:
        if input_wav != output_wav:
            import shutil
            shutil.copyfile(input_wav, output_wav)
        return orig_duration, False

    # Tính hệ số tăng tốc cần thiết
    target_tempo = orig_duration / available_window
    applied_tempo = min(target_tempo, max_tempo)
    is_overflow = target_tempo > max_tempo

    # Nếu hệ số tăng tốc quá nhỏ (< 1.03) thì không cần xử lý FFmpeg
    if applied_tempo <= 1.03:
        if input_wav != output_wav:
            import shutil
            shutil.copyfile(input_wav, output_wav)
        return orig_duration, False

    os.makedirs(os.path.dirname(os.path.abspath(output_wav)), exist_ok=True)
    temp_out = output_wav + ".tmp.wav"

    # FFmpeg atempo: tăng tốc âm thanh giữ nguyên cao độ giọng nói
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_wav,
        "-filter:a", f"atempo={applied_tempo:.3f}",
        "-ar", str(sample_rate),
        "-ac", "1",
        temp_out
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        # Nếu lỗi FFmpeg, giữ file gốc
        if input_wav != output_wav:
            import shutil
            shutil.copyfile(input_wav, output_wav)
        return orig_duration, is_overflow

    if os.path.exists(output_wav):
        os.remove(output_wav)
    os.rename(temp_out, output_wav)

    new_duration = get_wav_duration(output_wav)
    return new_duration, is_overflow
