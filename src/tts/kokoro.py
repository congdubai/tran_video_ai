"""
Bộ máy phát âm tiếng Việt chất lượng cao sử dụng Kokoro-Vietnamese.
Tham chiếu: Repo https://github.com/iamdinhthuan/Kokoro-Vietnamese
Tác giả repo: Đinh Thuận (iamdinhthuan)

GIẢ ĐỊNH VỀ API (Được nêu rõ ràng theo yêu cầu):
- Lớp khởi tạo: `KokoroVietnamese(device=device, voice=voice)`
- Hàm đọc: `synthesize(text)` trả về tuple: `(audio_data, phonemes)`
- Tần số âm thanh đầu ra: 24000 Hz.
- `audio_data` là mảng numpy hoặc tensor 1D biểu diễn sóng âm thanh float [-1.0, 1.0].
- Dùng `soundfile.write(output_path, audio_data, 24000)` để ghi file WAV.
"""

import os
import wave
from typing import Optional
from .base import BaseTTS


class KokoroTTS(BaseTTS):
    def __init__(self, voice: str = "ngoc_huyen", device: str = "cpu"):
        self.voice = voice or "ngoc_huyen"
        self.device = device or "cpu"
        self._sample_rate = 24000
        self._model = None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def name(self) -> str:
        return f"Kokoro-Vietnamese (Giọng: {self.voice}, Thiết bị: {self.device})"

    def _get_model(self):
        """Khởi tạo lazy model để chỉ tốn RAM khi bắt đầu đọc."""
        if self._model is None:
            try:
                # Thử import từ thư viện kokoro_vietnamese
                from kokoro_vietnamese import KokoroVietnamese
                self._model = KokoroVietnamese(device=self.device, voice=self.voice)
            except ImportError:
                try:
                    # Thử import trực tiếp nếu người dùng clone repo vào thư mục cùng cấp
                    from kokoro import KokoroVietnamese
                    self._model = KokoroVietnamese(device=self.device, voice=self.voice)
                except ImportError:
                    raise RuntimeError(
                        "Chưa tìm thấy thư viện Kokoro-Vietnamese.\n"
                        "Vui lòng cài đặt theo hướng dẫn:\n"
                        "  pip install git+https://github.com/iamdinhthuan/Kokoro-Vietnamese.git\n"
                        "Hoặc clone repo về máy:\n"
                        "  git clone https://github.com/iamdinhthuan/Kokoro-Vietnamese.git\n"
                        "(Bạn có thể dùng tạm --tts edge-tts hoặc --tts silent để chạy thử ngay mà không cần cài Kokoro)."
                    )
        return self._model

    def synthesize(self, text: str, output_wav_path: str) -> float:
        """
        Đọc đoạn văn bản bằng Kokoro-Vietnamese và lưu ra file WAV 24000Hz.
        Trả về thời lượng âm thanh (giây).
        """
        clean_text = text.strip()
        if not clean_text:
            # Tạo 0.5s im lặng nếu văn bản rỗng
            from .silent import SilentTTS
            return SilentTTS(sample_rate=self._sample_rate).synthesize("...", output_wav_path)

        model = self._get_model()

        # Gọi hàm tổng hợp giọng đọc theo API giả định
        result = model.synthesize(clean_text)
        if isinstance(result, tuple):
            audio_data = result[0]
        else:
            audio_data = result

        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)

        # Lưu audio ra file WAV bằng soundfile
        try:
            import soundfile as sf
            sf.write(output_wav_path, audio_data, self._sample_rate)
        except ImportError:
            raise RuntimeError(
                "Thiếu thư viện 'soundfile' để ghi âm thanh WAV.\n"
                "Vui lòng cài đặt: pip install soundfile"
            )

        # Đọc chính xác thời lượng từ header file WAV vừa ghi
        with wave.open(output_wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        return duration
