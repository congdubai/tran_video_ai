"""
Package xử lý âm thanh, ghép nối track thuyết minh và trộn âm thanh (Mixing & Ducking).
"""
from .track_builder import build_full_voice_track
from .mixer import mix_video_and_audio

__all__ = [
    "build_full_voice_track",
    "mix_video_and_audio"
]
