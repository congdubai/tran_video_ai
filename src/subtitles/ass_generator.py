"""
Module sinh file phụ đề định dạng ASS (Advanced SubStation Alpha).
Giải thích cho người mới:
- File ASS là tiêu chuẩn vàng của phụ đề anime/phim vì cho phép định vị toạ độ chính xác theo pixel.
- `PlayResX` và `PlayResY`: Đặt đúng bằng độ phân giải video gốc để toạ độ khớp 1:1.
- Thẻ `{\\an5\\pos(X,Y)}`:
  + \\an5: Căn giữa theo cả 2 chiều (horizontal center + vertical center).
  + \\pos(X,Y): Đặt tâm câu phụ đề đúng ngay chính giữa vùng chữ nhật làm mờ.
- Font chữ: Mặc định Arial hỗ trợ đầy đủ Unicode tiếng Việt (có dấu: ă, â, đ, ê, ô, ơ, ư...).
- File lưu bằng mã hoá UTF-8 (kèm BOM utf-8-sig) để Windows và libass đọc chuẩn không bị lỗi font (mojibake).
"""

import os
from typing import List, Tuple
from ..config import SubtitleCue


def seconds_to_ass_time(seconds: float) -> str:
    """
    Chuyển đổi giây sang định dạng thời gian ASS: H:MM:SS.cs (cs là centiseconds / phần trăm giây).
    Ví dụ: 75.34 giây -> 0:01:15.34
    """
    total_cs = int(round(max(0.0, seconds) * 100))
    cs = total_cs % 100
    total_s = total_cs // 100
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_ass_file(
    cues: List[SubtitleCue],
    video_width: int,
    video_height: int,
    blur_rect: Tuple[int, int, int, int],
    output_ass_path: str,
    font_name: str = "Arial",
    font_size: int = None
) -> str:
    """
    Tạo file .ass hoàn chỉnh đặt chữ phụ đề tiếng Việt vào tâm vùng làm mờ.
    """
    mask_x, mask_y, mask_w, mask_h = blur_rect
    center_x = mask_x + (mask_w // 2)
    center_y = mask_y + (mask_h // 2)

    # Tính kích thước font theo chiều cao video nếu không chỉ định
    if font_size is None:
        font_size = max(18, int(video_height * 0.042))

    outline_size = max(2, int(font_size * 0.12))

    # Header của file ASS theo chuẩn v4.00+
    header = f"""[Script Info]
Title: Vietnamese Dubbing Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline_size},0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for idx, cue in enumerate(cues):
        text = (cue.text_vi or cue.text_zh).strip()
        if not text:
            continue

        start_sec = cue.start
        # Nếu câu có âm thanh thuyết minh thì kéo dài tới khi đọc xong, nhưng không chồng sang câu sau
        if cue.audio_duration and cue.audio_duration > 0:
            end_sec = start_sec + cue.audio_duration
        else:
            end_sec = cue.end

        # Không cho chồng lấn sang thời điểm bắt đầu của câu kế tiếp
        if idx + 1 < len(cues):
            next_start = cues[idx + 1].start
            if end_sec > next_start:
                end_sec = max(start_sec + 0.5, next_start - 0.05)

        start_str = seconds_to_ass_time(start_sec)
        end_str = seconds_to_ass_time(end_sec)

        # Định vị giữa vùng làm mờ bằng \an5\pos(center_x, center_y)
        dialogue_line = (
            f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,"
            f"{{\\an5\\pos({center_x},{center_y})}}{text}"
        )
        events.append(dialogue_line)

    content = header + "\n".join(events) + "\n"

    os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)
    # Ghi file với encoding utf-8-sig để hỗ trợ đầy đủ Windows Unicode
    with open(output_ass_path, "w", encoding="utf-8-sig") as f:
        f.write(content)

    return output_ass_path
