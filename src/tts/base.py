"""
Interface trừu tượng cho các nhà cung cấp giọng đọc TTS (Text-To-Speech Provider).
Dành cho người mới quen Java/TypeScript:
- Tương tự như 'interface TTSProvider' bên Java.
- Mọi provider (Kokoro, Edge-TTS, Silent...) phải triển khai hàm `synthesize(text, output_wav_path) -> float`
  trả về thời lượng thực tế (tính bằng giây) của file âm thanh WAV sinh ra.
"""

from abc import ABC, abstractmethod


class BaseTTS(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_wav_path: str) -> float:
        """
        Chuyển văn bản thành file âm thanh WAV.
        Trả về: Thời lượng âm thanh (giây).
        """
        pass

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Tần số lấy mẫu âm thanh (Sample Rate), mặc định chuẩn 24000 Hz."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên của provider để in log."""
        pass
