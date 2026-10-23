"""
Bộ máy dịch trực tuyến sử dụng Gemini REST API của Google.
Giải thích cho người mới:
- Dùng REST API trực tiếp qua thư viện `requests`, không phụ thuộc vào SDK nặng.
- Đọc khoá API từ biến môi trường `GEMINI_API_KEY` (bảo mật, không lưu cứng vào code).
- Model mặc định: `gemini-1.5-flash` (tốc độ cao, rẻ và hỗ trợ trả JSON chuẩn).
"""

import os
import requests
from .base import BaseTranslator


class GeminiTranslator(BaseTranslator):
    def __init__(self, model: str = None, api_key: str = None):
        # Tên model đọc từ tham số hoặc mặc định gemini-1.5-flash, không gõ cứng
        self.model = model or "gemini-1.5-flash"
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    @property
    def name(self) -> str:
        return f"Gemini ({self.model})"

    def translate_prompt(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(
                "Chưa tìm thấy biến môi trường 'GEMINI_API_KEY'.\n"
                "=> Trên Windows PowerShell: $env:GEMINI_API_KEY = 'khoa_api_cua_ban'\n"
                "=> Trên Windows CMD: set GEMINI_API_KEY=khoa_api_cua_ban\n"
                "=> Hoặc trên Linux: export GEMINI_API_KEY=khoa_api_cua_ban"
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",  # Ép Gemini trả JSON
                "temperature": 0.2
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 400:
                raise RuntimeError(f"Lỗi cú pháp yêu cầu Gemini API (400): {response.text}")
            elif response.status_code in (401, 403):
                raise RuntimeError("GEMINI_API_KEY không hợp lệ hoặc không có quyền truy cập.")
            elif response.status_code == 429:
                raise RuntimeError("Hết hạn mức truy vấn Gemini API (Rate limit / Quota exceeded).")
            response.raise_for_status()

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini không trả về kết quả nào (bị filter an toàn).")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise RuntimeError("Phản hồi của Gemini rỗng.")

            return parts[0].get("text", "")

        except requests.exceptions.Timeout:
            raise RuntimeError(f"Gemini API phản hồi quá thời gian (Timeout 60s) với model '{self.model}'.")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Lỗi khi gọi Gemini API: {str(e)}")
