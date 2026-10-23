"""
Unit test kiểm tra hệ thống TTS (SilentTTS, adjust_audio_speed, build_full_voice_track).
"""

import sys
import os
import wave
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import SubtitleCue
from src.tts.silent import SilentTTS
from src.tts.speed import adjust_audio_speed, get_wav_duration
from src.audio.track_builder import build_full_voice_track


def test_silent_tts(tmp_path):
    """Kiểm tra SilentTTS sinh file WAV 24000Hz đúng cấu trúc."""
    out_wav = str(tmp_path / "silent_test.wav")
    tts = SilentTTS(sample_rate=24000, words_per_second=4.0)

    duration = tts.synthesize("Một hai ba bốn năm sáu bảy tám", out_wav)
    assert duration > 1.0
    assert os.path.exists(out_wav)

    with wave.open(out_wav, "rb") as wf:
        assert wf.getnchannels() == 1  # Mono
        assert wf.getframerate() == 24000
        assert wf.getsampwidth() == 2  # 16-bit


def test_adjust_audio_speed_no_speedup_needed(tmp_path):
    """Kiểm tra khi câu đọc ngắn hơn khung thời gian cho phép thì giữ nguyên."""
    wav1 = str(tmp_path / "cue1.wav")
    wav_out = str(tmp_path / "cue1_adj.wav")

    tts = SilentTTS(sample_rate=24000)
    dur = tts.synthesize("Xin chào bạn", wav1)

    # Khung thời gian rộng rãi 5.0s (dài hơn thời lượng câu)
    new_dur, is_overflow = adjust_audio_speed(
        input_wav=wav1,
        output_wav=wav_out,
        available_window=5.0,
        max_tempo=1.35
    )

    assert is_overflow is False
    assert abs(new_dur - dur) < 0.1


def test_adjust_audio_speed_overflow_detection(tmp_path):
    """Kiểm tra phát hiện tràn câu khi thời lượng vượt quá max_tempo (1.35x)."""
    wav1 = str(tmp_path / "long_cue.wav")
    wav_out = str(tmp_path / "long_cue_adj.wav")

    tts = SilentTTS(sample_rate=24000, words_per_second=2.0)
    # Câu dài khoảng 4.0s
    dur = tts.synthesize("Đây là một câu rất rất dài mà khung thời gian chỉ có một giây thôi", wav1)

    # Khung thời gian quá hẹp (1.0s) -> cần tăng tốc 4x > 1.35x -> Tràn câu
    new_dur, is_overflow = adjust_audio_speed(
        input_wav=wav1,
        output_wav=wav_out,
        available_window=1.0,
        max_tempo=1.35
    )

    assert is_overflow is True


def test_build_full_voice_track(tmp_path):
    """Kiểm tra ghép nối các câu thành track tổng 24000Hz chính xác."""
    tts = SilentTTS(sample_rate=24000)
    wav1 = str(tmp_path / "c1.wav")
    wav2 = str(tmp_path / "c2.wav")

    d1 = tts.synthesize("Câu thứ nhất", wav1)
    d2 = tts.synthesize("Câu thứ hai", wav2)

    cues = [
        SubtitleCue(id=1, start=1.0, end=2.0, text_zh="一", audio_path=wav1, audio_duration=d1),
        SubtitleCue(id=2, start=3.0, end=4.0, text_zh="二", audio_path=wav2, audio_duration=d2)
    ]

    master_wav = str(tmp_path / "master.wav")
    build_full_voice_track(
        cues=cues,
        total_video_duration=10.0,
        output_track_path=master_wav,
        sample_rate=24000
    )

    assert os.path.exists(master_wav)
    with wave.open(master_wav, "rb") as wf:
        assert wf.getframerate() == 24000
        assert wf.getnchannels() == 1
        total_dur = wf.getnframes() / float(wf.getframerate())
        assert abs(total_dur - 10.0) < 0.1
