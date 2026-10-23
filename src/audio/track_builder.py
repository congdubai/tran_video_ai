"""
Module ghép nối tất cả các câu thuyết minh thành một track WAV duy nhất (24000 Hz, mono).
Giải thích cho người mới:
- Track thuyết minh phải có tổng thời lượng dài đúng bằng video gốc.
- Các khoảng thời gian không có lời thoại sẽ được chèn âm thanh tĩnh (im lặng/silence).
- Thuật toán chống chồng chéo giọng (Non-overlapping):
  Nếu câu trước bị đọc dài lấn sang khoảng lặng, câu sau sẽ tự động bắt đầu ngay sau khi câu trước kết thúc
  (cộng thêm khoảng đệm tự nhiên 50ms), tuyệt đối không để 2 câu nói đè lên nhau cùng lúc.
"""

import array
import os
import wave
from typing import List, Tuple
from ..config import SubtitleCue


def build_full_voice_track(
    cues: List[SubtitleCue],
    total_video_duration: float,
    output_track_path: str,
    sample_rate: int = 24000
) -> str:
    """
    Tạo 1 file WAV hoàn chỉnh (24000 Hz, 16-bit, Mono) chứa toàn bộ giọng thuyết minh
    tại đúng các mốc thời gian của từng câu.
    """
    total_samples = int(round(max(1.0, total_video_duration) * sample_rate))
    # Khởi tạo mảng PCM 16-bit toàn số 0 (im lặng) bằng thư viện chuẩn array
    master_buffer = array.array("h", [0]) * total_samples

    current_cursor_sec = 0.0

    for cue in cues:
        if not cue.audio_path or not os.path.exists(cue.audio_path):
            continue

        # Câu sau phải bắt đầu muộn nhất là sau khi câu trước nói xong (chống chồng giọng)
        actual_start_sec = max(cue.start, current_cursor_sec)
        start_sample = int(actual_start_sec * sample_rate)

        # Đọc dữ liệu PCM từ file WAV của câu này
        with wave.open(cue.audio_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw_data = wf.readframes(n_frames)

        # Chuyển đổi dữ liệu byte sang mảng int16
        cue_samples = array.array("h")
        cue_samples.frombytes(raw_data)

        # Nếu file gốc stereo thì lấy kênh trái
        if n_channels == 2:
            cue_samples = cue_samples[::2]

        # Ghi đè vào master_buffer
        available_slots = total_samples - start_sample
        samples_to_copy = min(len(cue_samples), max(0, available_slots))

        if samples_to_copy > 0:
            for i in range(samples_to_copy):
                master_buffer[start_sample + i] = cue_samples[i]

        actual_duration_sec = samples_to_copy / float(sample_rate)
        # Di chuyển con trỏ thời gian + khoảng dừng nhỏ 50ms giữa 2 câu
        current_cursor_sec = actual_start_sec + actual_duration_sec + 0.05

    os.makedirs(os.path.dirname(os.path.abspath(output_track_path)), exist_ok=True)

    # Xuất file WAV master
    with wave.open(output_track_path, "wb") as wf:
        wf.setnchannels(1)       # Mono
        wf.setsampwidth(2)       # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(master_buffer.tobytes())

    return output_track_path
