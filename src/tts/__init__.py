"""
Package Text-To-Speech (TTS) đa provider cho hệ thống thuyết minh tiếng Việt.
"""
from .base import BaseTTS
from .silent import SilentTTS
from .kokoro import KokoroTTS
from .edge import EdgeTTS
from .speed import adjust_audio_speed

__all__ = [
    "BaseTTS",
    "SilentTTS",
    "KokoroTTS",
    "EdgeTTS",
    "adjust_audio_speed"
]
