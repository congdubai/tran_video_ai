"""
Bộ máy TTS im lặng (Silent TTS / Mock).
Dùng cho kiểm thử đơn vị (Unit Test), chạy thử luồng trộn âm thanh mà không cần tải model AI nặng.
Tạo file WAV rỗng (silent) hoàn toàn bằng thư viện chuẩn `wave` của Python.
"""

import os
import wave
from .base import BaseTTS


class SilentTTS(BaseTTS):
    def __init__(self, sample_rate: int = 24000, words_per_second: float = 4.0):
        self._sample_rate = sample_rate
        self.words_per_second = words_per_second

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def name(self) -> str:
        return "Silent (Mock TTS)"

    def synthesize(self, text: str, output_wav_path: str) -> float:
        """
        Ước lượng thời lượng đọc dựa trên số từ (khoảng 4 từ/giây).
        Sinh file WAV im lặng đúng bằng thời lượng đó.
        """
        word_count = len(text.strip().split())
        duration = max(0.5, word_count / self.words_per_second)

        num_frames = int(duration * self._sample_rate)
        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)

        # Ghi file WAV 16-bit Mono chuẩn 24000 Hz
        with wave.open(output_wav_path, "wb") as wf:
            wf.setnchannels(1)       # Mono
            wf.setsampwidth(2)       # 16-bit (2 bytes)
            wf.setframerate(self._sample_rate)
            # Dữ liệu âm thanh im lặng là các byte 0x00
            wf.writeframes(b"\x00" * (num_frames * 2))

        return duration
