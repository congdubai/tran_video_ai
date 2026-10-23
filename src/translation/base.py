"""
Interface cơ sở cho các bộ máy dịch thuật (Translator Provider).
Dành cho người mới quen Java/TypeScript:
- Tương tự như 'interface Translator' hoặc 'abstract class BaseTranslator' bên Java.
- Mọi provider (Ollama, Gemini, Echo...) bắt buộc phải kế thừa class này
  và cài đặt phương thức `translate_prompt(prompt: str) -> str`.
"""

from abc import ABC, abstractmethod


class BaseTranslator(ABC):
    """Lớp trừu tượng định nghĩa chuẩn giao tiếp của dịch thuật."""

    @abstractmethod
    def translate_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """
        Gửi prompt đến model AI và nhận về chuỗi phản hồi thô (raw text response).
        - system_prompt: Định hình vai trò của AI (ví dụ: chuyên gia dịch phụ đề phim)
        - user_prompt: Nội dung danh sách câu kèm yêu cầu định dạng JSON
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên của provider để in log."""
        pass
