"""
Bộ máy phát âm tiếng Việt dự phòng sử dụng Microsoft Edge-TTS (Chất lượng cao, miễn phí).
Rất thích hợp khi chưa cài đặt kịp Kokoro hoặc cần kiểm thử nhanh giọng đọc tiếng Việt mượt mà.
"""

import asyncio
import os
import subprocess
import wave
from .base import BaseTTS


class EdgeTTS(BaseTTS):
    def __init__(self, voice: str = "vi-VN-HoaiMyNeural"):
        # Ánh xạ tên giọng nếu người dùng vẫn để mặc định ngoc_huyen
        if voice in ("ngoc_huyen", "default", "female"):
            self.voice = "vi-VN-HoaiMyNeural"
        elif voice in ("nam", "male"):
            self.voice = "vi-VN-NamMinhNeural"
        else:
            self.voice = voice

        self._sample_rate = 24000

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def name(self) -> str:
        return f"Edge-TTS (Giọng: {self.voice})"

    def synthesize(self, text: str, output_wav_path: str) -> float:
        """
        Gọi edge-tts tải âm thanh MP3 từ Microsoft, sau đó dùng FFmpeg chuyển sang WAV 24000Hz Mono.
        """
        clean_text = text.strip()
        if not clean_text:
            from .silent import SilentTTS
            return SilentTTS(sample_rate=self._sample_rate).synthesize("...", output_wav_path)

        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
        temp_mp3 = output_wav_path + ".tmp.mp3"

        async def _run_edge():
            try:
                import edge_tts
            except ImportError:
                raise RuntimeError(
                    "Chưa cài đặt thư viện 'edge-tts'.\n"
                    "Vui lòng cài đặt bằng lệnh: pip install edge-tts"
                )
            communicate = edge_tts.Communicate(clean_text, self.voice)
            await communicate.save(temp_mp3)

        # Chạy coroutine asyncio
        try:
            asyncio.run(_run_edge())
        except Exception as e:
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)
            raise RuntimeError(f"Edge-TTS lỗi kết nối: {str(e)}")

        # Dùng FFmpeg chuyển đổi MP3 sang WAV 24000Hz Mono
        cmd = [
            "ffmpeg",
            "-y",
            "-i", temp_mp3,
            "-ar", str(self._sample_rate),
            "-ac", "1",  # Mono
            output_wav_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)

        if result.returncode != 0:
            raise RuntimeError("FFmpeg thất bại khi chuyển đổi định dạng âm thanh Edge-TTS.")

        with wave.open(output_wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)

        return duration
