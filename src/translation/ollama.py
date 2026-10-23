"""
Bộ máy dịch cục bộ sử dụng Ollama (Local LLM, ví dụ: Qwen 2.5 7B).
Giải thích cho người mới:
- Ollama là công cụ chạy các model mã nguồn mở (như Llama, Qwen, Mistral) ngay trên máy bạn.
- Ollama mở một máy chủ HTTP REST tại cổng 11434 (`http://localhost:11434/api/chat`).
- Qwen 2.5 rất mạnh về tiếng Trung và tiếng Việt, phiên bản 7B chạy mượt với 6GB VRAM (Q4_K_M).
"""

import json
import requests
from .base import BaseTranslator


class OllamaTranslator(BaseTranslator):
    def __init__(self, model: str = "qwen2.5:7b", host: str = "http://localhost:11434"):
        self.model = model or "qwen2.5:7b"
        self.host = host.rstrip("/")

    @property
    def name(self) -> str:
        return f"Ollama ({self.model})"

    def translate_prompt(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "format": "json",  # Ép Ollama luôn trả định dạng JSON hợp lệ
            "stream": False,
            "options": {
                "temperature": 0.2  # Nhiệt độ thấp để bản dịch ổn định và bám sát ngữ cảnh
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=90)
            if response.status_code == 404:
                raise RuntimeError(
                    f"Model '{self.model}' chưa được tải trong Ollama.\n"
                    f"=> Hãy mở terminal và chạy lệnh: ollama pull {self.model}"
                )
            response.raise_for_status()

            data = response.json()
            message = data.get("message", {})
            return message.get("content", "")

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Không thể kết nối đến máy chủ Ollama tại " + self.host + ".\n"
                "=> Vui lòng mở phần mềm Ollama trên máy tính hoặc gõ lệnh: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Ollama xử lý quá thời gian (Timeout 90s) với model '{self.model}'.")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Lỗi khi gọi Ollama API: {str(e)}")
