#!/usr/bin/env python3
"""
Công cụ tự động chuyển đổi Video phụ đề tiếng Trung sang Thuyết minh tiếng Việt.
Tác giả: Senior Software Engineer (hướng dẫn cho dev Java/React).

Cách chạy mẫu:
    python dub.py video.mp4 --preview-region
    python dub.py video.mp4 --stop-after ocr
    python dub.py video.mp4 --stop-after translate
    python dub.py video.mp4 --translate ollama --tts kokoro --keep-original 0.15 --duck
    python dub.py video.mp4 --translate echo --tts silent --out test_output.mp4
"""

import argparse
import json
import os
import sys
from typing import List, Tuple

# Đảm bảo import được các module trong thư mục src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.config import AppConfig, SubtitleCue, OCRBox
from src.video_utils import get_video_info, generate_preview_region
from src.ocr.engine import process_video_ocr
from src.ocr.grouper import group_cues, cues_to_json_dict, json_dict_to_cues
from src.translation import (
    BaseTranslator,
    EchoTranslator,
    OllamaTranslator,
    GeminiTranslator,
    translate_cues_in_batches
)
from src.translation.batch import save_cues_vi, load_cues_vi
from src.subtitles import (
    calculate_blur_rect,
    generate_ass_file
)
from src.tts import (
    BaseTTS,
    SilentTTS,
    KokoroTTS,
    EdgeTTS,
    adjust_audio_speed
)
from src.audio import (
    build_full_voice_track,
    mix_video_and_audio
)


def parse_arguments() -> AppConfig:
    """Xử lý các tham số dòng lệnh (CLI Arguments)."""
    parser = argparse.ArgumentParser(
        description="Auto Sub-to-Dub: Dịch và Thuyết minh Video phụ đề tiếng Trung sang tiếng Việt",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # File vào/ra
    parser.add_argument("video", help="Đường dẫn file video đầu vào (.mp4, .mkv, .mov...)")
    parser.add_argument("--out", default="output.mp4", help="Đường dẫn file video kết quả đầu ra")
    parser.add_argument("--work", default="work", help="Thư mục lưu các file trung gian (cache)")

    # Tham số OCR
    parser.add_argument(
        "--region", default="0.60,0.95",
        help="Vùng phụ đề tính theo tỉ lệ chiều cao (y_min,y_max), ví dụ: 0.60,0.95"
    )
    parser.add_argument("--fps", type=float, default=4.0, help="Tần suất trích khung hình OCR mỗi giây")
    parser.add_argument("--min-conf", type=float, default=0.6, help="Độ tin cậy tối thiểu của ký tự OCR (0.0 - 1.0)")
    parser.add_argument(
        "--ignore", default=r"抖音,douyin,@\w+",
        help="Danh sách các regex loại trừ watermark/kênh (ngăn cách bằng dấu phẩy)"
    )

    # Chế độ xem trước & dừng kiểm tra
    parser.add_argument(
        "--preview-region", action="store_true",
        help="Xuất ảnh minh hoạ khung chữ nhật đỏ vùng OCR rồi dừng lại"
    )
    parser.add_argument(
        "--stop-after", choices=["ocr", "translate"],
        help="Dừng chương trình sau bước tương ứng để kiểm tra / sửa tay file JSON"
    )

    # Tham số Dịch thuật
    parser.add_argument(
        "--translate", choices=["ollama", "gemini", "echo"], default="ollama",
        help="Bộ máy dịch thuật (ollama / gemini / echo)"
    )
    parser.add_argument("--model", default=None, help="Tên model LLM (mặc định: qwen2.5:7b cho ollama, gemini-1.5-flash cho gemini)")
    parser.add_argument("--src", default="zh", help="Ngôn ngữ gốc của video")

    # Tham số Làm mờ & Phụ đề ASS
    parser.add_argument(
        "--mask-rect", default=None,
        help="Ghi đè toạ độ vùng làm mờ thủ công dạng 'x1,y1,x2,y2' (bỏ qua tính tự động)"
    )
    parser.add_argument("--mask-sigma", type=int, default=30, help="Độ nhoè Gaussian Blur để làm mờ phụ đề cũ")
    parser.add_argument("--font", default="Arial", help="Tên font chữ hiển thị phụ đề tiếng Việt (cần hỗ trợ Unicode dấu)")
    parser.add_argument("--font-size", type=int, default=None, help="Cỡ chữ phụ đề (nếu không set sẽ tự tính theo độ phân giải)")
    parser.add_argument("--fonts-dir", default=None, help="Thư mục chứa font tùy chọn")

    # Tham số TTS & Trộn âm thanh
    parser.add_argument(
        "--tts", choices=["kokoro", "edge-tts", "silent"], default="kokoro",
        help="Bộ máy đọc giọng tiếng Việt (kokoro / edge-tts / silent để test)"
    )
    parser.add_argument("--voice", default="ngoc_huyen", help="Tên giọng đọc (mặc định ngoc_huyen cho Kokoro)")
    parser.add_argument("--tts-device", default="cpu", choices=["cpu", "cuda"], help="Thiết bị chạy TTS (mặc định CPU)")
    parser.add_argument("--max-tempo", type=float, default=1.35, help="Tốc độ đọc tối đa cho phép tăng tốc khi câu dài")
    parser.add_argument(
        "--keep-original", type=float, default=0.15,
        help="Âm lượng giữ lại của âm thanh gốc (0.0 = tắt hẳn, 0.15 = nhỏ vừa đủ làm nền)"
    )
    parser.add_argument(
        "--duck", action="store_true",
        help="Bật hiệu ứng Ducking (Sidechain compression: âm thanh gốc tự nhỏ khi có thuyết minh và to lại khi ngắt câu)"
    )

    args = parser.parse_args()

    # Phân tích region
    region_str = args.region.replace(":", ",")
    r_parts = [float(p.strip()) for p in region_str.split(",") if p.strip()]
    if len(r_parts) != 2 or r_parts[0] >= r_parts[1]:
        raise ValueError("Tham số --region không hợp lệ. Vui lòng nhập dạng '0.60,0.95' với y_min < y_max.")
    region = (r_parts[0], r_parts[1])

    # Phân tích ignore regex
    ignore_list = [p.strip() for p in args.ignore.split(",") if p.strip()]

    # Phân tích mask_rect nếu có
    mask_rect = None
    if args.mask_rect:
        m_parts = [int(p.strip()) for p in args.mask_rect.replace(":", ",").split(",") if p.strip()]
        if len(m_parts) == 4:
            mask_rect = (m_parts[0], m_parts[1], m_parts[2], m_parts[3])

    return AppConfig(
        video_path=args.video,
        output_path=args.out,
        work_dir=args.work,
        region=region,
        fps=args.fps,
        min_conf=args.min_conf,
        ignore_patterns=ignore_list,
        preview_region=args.preview_region,
        stop_after=args.stop_after,
        translator_type=args.translate,
        model_name=args.model,
        src_lang=args.src,
        mask_rect=mask_rect,
        mask_sigma=args.mask_sigma,
        font_name=args.font,
        font_size=args.font_size,
        fonts_dir=args.fonts_dir,
        tts_type=args.tts,
        voice=args.voice,
        tts_device=args.tts_device,
        max_tempo=args.max_tempo,
        keep_original_vol=args.keep_original,
        use_ducking=args.duck
    )


def step_preview_region(config: AppConfig):
    """Xử lý chế độ --preview-region."""
    print("=" * 60)
    print("CHẾ ĐỘ XEM TRƯỚC VÙNG PHỤ ĐỀ (--preview-region)")
    print("=" * 60)
    info = get_video_info(config.video_path)
    print(f"[*] Video: {config.video_path}")
    print(f"[*] Kích thước: {info['width']}x{info['height']} | Thời lượng: {info['duration']:.2f}s | FPS: {info['fps']:.2f}")
    print(f"[*] Vùng phụ đề đã chọn (y_min={config.region[0]}, y_max={config.region[1]})")

    out_preview = os.path.join(config.work_dir, "preview_region.jpg")
    generate_preview_region(config.video_path, config.region, out_preview)
    print(f"[+] ĐÃ TẠO ẢNH XEM TRƯỚC: {out_preview}")
    print("[+] Hãy mở ảnh trên để kiểm tra khung đỏ có bao trọn dòng phụ đề tiếng Trung không.")
    print("[+] Nếu chưa chuẩn, hãy điều chỉnh lại bằng: --region 0.65,0.92")


def step_ocr_and_group(config: AppConfig) -> List[SubtitleCue]:
    """Xử lý Bước 1, Bước 2, Bước 3 (OCR và gom cụm câu). Có hỗ trợ đọc lại cache."""
    cues_file = os.path.join(config.work_dir, "cues.json")
    os.makedirs(config.work_dir, exist_ok=True)

    if os.path.exists(cues_file):
        print(f"[*] Tìm thấy file cache có sẵn: {cues_file}")
        print("[*] Đang tải lại danh sách câu phụ đề (bỏ qua OCR để tiết kiệm thời gian)...")
        with open(cues_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        cues = json_dict_to_cues(data)
        print(f"[+] Đã tải thành công {len(cues)} câu từ {cues_file}")
        return cues

    print("=" * 60)
    print("BƯỚC 1 - 3: TRÍCH KHUNG HÌNH, OCR VÀ GOM CÂU PHỤ ĐỀ")
    print("=" * 60)

    frame_results = process_video_ocr(config.video_path, config)

    print("[*] Đang gom cụm các khung hình liên tiếp và lọc nhiễu...")
    cues = group_cues(
        frame_results=frame_results,
        fps=config.fps,
        sim_threshold=config.sim_threshold,
        min_consecutive_frames=config.min_consecutive_frames
    )

    cues_data = cues_to_json_dict(cues)
    with open(cues_file, "w", encoding="utf-8") as f:
        json.dump(cues_data, f, ensure_ascii=False, indent=2)

    print(f"[+] Đã phát hiện {len(cues)} câu phụ đề hợp lệ.")
    print(f"[+] Đã lưu kết quả vào: {cues_file}")
    for c in cues[:5]:
        print(f"    [{c.start:.2f}s -> {c.end:.2f}s] {c.text_zh}")
    if len(cues) > 5:
        print(f"    ... và {len(cues) - 5} câu tiếp theo.")

    return cues


def get_translator(config: AppConfig) -> BaseTranslator:
    """Khởi tạo bộ máy dịch tương ứng theo tham số --translate."""
    t_type = config.translator_type.lower()
    if t_type == "ollama":
        model = config.model_name or "qwen2.5:7b"
        return OllamaTranslator(model=model)
    elif t_type == "gemini":
        model = config.model_name or "gemini-1.5-flash"
        return GeminiTranslator(model=model)
    elif t_type == "echo":
        return EchoTranslator()
    else:
        raise ValueError(f"Không hỗ trợ bộ máy dịch: '{config.translator_type}'. Chỉ chọn: ollama, gemini, echo.")


def step_translate(cues: List[SubtitleCue], config: AppConfig) -> List[SubtitleCue]:
    """Xử lý Bước 4 (Dịch thuật sang tiếng Việt). Hỗ trợ đọc lại cache cues_vi.json."""
    cues_vi_file = os.path.join(config.work_dir, "cues_vi.json")

    if os.path.exists(cues_vi_file):
        print(f"[*] Tìm thấy file bản dịch đã có: {cues_vi_file}")
        print("[*] Đang tải lại bản dịch tiếng Việt (bỏ qua gọi AI)...")
        translated_cues = load_cues_vi(cues_vi_file)
        print(f"[+] Đã tải thành công {len(translated_cues)} câu đã dịch từ {cues_vi_file}")
        return translated_cues

    print("=" * 60)
    print("BƯỚC 4: DỊCH THUẬT PHỤ ĐỀ SANG TIẾNG VIỆT")
    print("=" * 60)

    translator = get_translator(config)
    translated_cues = translate_cues_in_batches(
        cues=cues,
        translator=translator,
        batch_size=config.batch_size,
        context_count=3
    )

    save_cues_vi(translated_cues, cues_vi_file)
    print(f"[+] Đã lưu bản dịch tiếng Việt vào: {cues_vi_file}")

    for c in translated_cues[:5]:
        print(f"    [{c.start:.2f}s -> {c.end:.2f}s] ZH: {c.text_zh} => VI: {c.text_vi}")
    if len(translated_cues) > 5:
        print(f"    ... và {len(translated_cues) - 5} câu tiếp theo.")

    return translated_cues


def get_tts_engine(config: AppConfig) -> BaseTTS:
    """Khởi tạo bộ máy TTS tương ứng theo tham số --tts."""
    tts_type = config.tts_type.lower()
    if tts_type == "kokoro":
        return KokoroTTS(voice=config.voice, device=config.tts_device)
    elif tts_type == "edge-tts":
        return EdgeTTS(voice=config.voice)
    elif tts_type == "silent":
        return SilentTTS()
    else:
        raise ValueError(f"Không hỗ trợ bộ máy TTS: '{config.tts_type}'. Chỉ chọn: kokoro, edge-tts, silent.")


def step_tts_and_build_track(cues: List[SubtitleCue], config: AppConfig, total_duration: float) -> str:
    """
    Xử lý Bước 7:
    - Đọc từng câu bằng TTS.
    - Điều chỉnh tốc độ atempo nếu giọng dài hơn khung thời gian.
    - Ghép thành track âm thanh thuyết minh tổng 24000Hz Mono.
    """
    print("=" * 60)
    print("BƯỚC 7: TỔNG HỢP GIỌNG ĐỌC THUYẾT MINH (TTS) & KHỚP NHỊP")
    print("=" * 60)

    tts = get_tts_engine(config)
    print(f"[*] Sử dụng bộ máy TTS: [{tts.name}]")

    audio_dir = os.path.join(config.work_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    overflow_count = 0

    for idx, cue in enumerate(cues):
        text = (cue.text_vi or cue.text_zh).strip()
        raw_wav = os.path.join(audio_dir, f"cue_{cue.id:04d}_raw.wav")
        adjusted_wav = os.path.join(audio_dir, f"cue_{cue.id:04d}.wav")

        # 1. Đọc văn bản sang âm thanh WAV
        # Tái sử dụng file âm thanh nếu đã sinh trước đó
        if not os.path.exists(raw_wav):
            tts.synthesize(text, raw_wav)

        # 2. Tính khoảng thời gian cho phép trước khi câu kế tiếp bắt đầu
        if idx + 1 < len(cues):
            available_window = cues[idx + 1].start - cue.start
        else:
            available_window = max(1.0, cue.end - cue.start)

        # 3. Tăng tốc bằng atempo nếu cần
        new_duration, is_overflow = adjust_audio_speed(
            input_wav=raw_wav,
            output_wav=adjusted_wav,
            available_window=available_window,
            max_tempo=config.max_tempo,
            sample_rate=tts.sample_rate
        )

        cue.audio_path = adjusted_wav
        cue.audio_duration = new_duration

        if is_overflow:
            overflow_count += 1
            print(f"    [!] Câu #{cue.id} bị tràn: Giọng đọc ({new_duration:.2f}s) > Khoảng trống ({available_window:.2f}s). Đã cho lấn sang khoảng lặng.")

        if (idx + 1) % 5 == 0 or idx == len(cues) - 1:
            print(f"    - Tiến độ TTS: {idx + 1}/{len(cues)} câu...")

    if overflow_count > 0:
        print(f"\n[!] CẢNH BÁO TỔNG KẾT: Có {overflow_count}/{len(cues)} câu bị tràn thời lượng (vẫn đọc được nhờ cơ chế lấn khoảng lặng).")
        print(f"[!] Gợi ý: Bạn có thể mở file '{config.work_dir}/cues_vi.json' để rút gọn bớt từ ngữ cho các câu trên rồi chạy lại.\n")

    # 4. Ghép toàn bộ câu thành 1 track âm thanh master
    print("[*] Đang ghép nối toàn bộ câu thành track thuyết minh đồng bộ...")
    master_track = os.path.join(config.work_dir, "full_voice_track.wav")
    build_full_voice_track(
        cues=cues,
        total_video_duration=total_duration,
        output_track_path=master_track,
        sample_rate=tts.sample_rate
    )
    print(f"[+] Đã tạo track thuyết minh hoàn chỉnh: {master_track}")
    return master_track


def main():
    try:
        config = parse_arguments()
    except Exception as e:
        print(f"[LỖI THAM SỐ] {e}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(config.video_path):
        print(f"[LỖI] Không tìm thấy file video đầu vào: {config.video_path}", file=sys.stderr)
        sys.exit(1)

    # Lấy thông số kỹ thuật video
    video_info = get_video_info(config.video_path)

    # 1. Chế độ xem trước vùng OCR
    if config.preview_region:
        try:
            step_preview_region(config)
        except Exception as e:
            print(f"[LỖI PREVIEW] {e}", file=sys.stderr)
            sys.exit(1)
        return

    # 2. Chế độ OCR & Gom câu
    try:
        cues = step_ocr_and_group(config)
    except Exception as e:
        print(f"[LỖI OCR] {e}", file=sys.stderr)
        sys.exit(1)

    if config.stop_after == "ocr":
        print("=" * 60)
        print("[!] Đã dừng theo tham số --stop-after ocr.")
        print(f"[!] Bạn có thể mở file '{config.work_dir}/cues.json' để kiểm tra câu chữ.")
        print("=" * 60)
        return

    # 3. Chế độ Dịch thuật
    try:
        translated_cues = step_translate(cues, config)
    except Exception as e:
        print(f"[LỖI DỊCH THUẬT] {e}", file=sys.stderr)
        sys.exit(1)

    if config.stop_after == "translate":
        print("=" * 60)
        print("[!] Đã dừng theo tham số --stop-after translate.")
        print(f"[!] Bạn có thể mở file '{config.work_dir}/cues_vi.json' để trau chuốt lại câu dịch.")
        print("=" * 60)
        return

    # 4. Tính toán hình chữ nhật làm mờ phụ đề cũ
    print("=" * 60)
    print("BƯỚC 5: TÍNH TOÁN VÙNG LÀM MỜ PHỤ ĐỀ CŨ")
    print("=" * 60)
    all_boxes = [box for c in translated_cues for box in c.boxes]
    font_size = config.font_size or max(18, int(video_info["height"] * 0.042))
    blur_rect = calculate_blur_rect(
        boxes=all_boxes,
        video_width=video_info["width"],
        video_height=video_info["height"],
        font_size=font_size,
        manual_rect=config.mask_rect
    )
    print(f"[+] Toạ độ vùng làm mờ: x={blur_rect[0]}, y={blur_rect[1]}, w={blur_rect[2]}, h={blur_rect[3]}")

    # 5. Sinh giọng đọc TTS và tạo track thuyết minh 24000Hz
    voice_track_wav = step_tts_and_build_track(
        cues=translated_cues,
        config=config,
        total_duration=video_info["duration"]
    )

    # 6. Sinh file phụ đề ASS tiếng Việt (đặt ở tâm vùng làm mờ)
    print("=" * 60)
    print("BƯỚC 6: SINH FILE PHỤ ĐỀ ASS TIẾNG VIỆT")
    print("=" * 60)
    ass_file = os.path.join(config.work_dir, "subtitles.ass")
    generate_ass_file(
        cues=translated_cues,
        video_width=video_info["width"],
        video_height=video_info["height"],
        blur_rect=blur_rect,
        output_ass_path=ass_file,
        font_name=config.font_name,
        font_size=font_size
    )
    print(f"[+] Đã tạo file phụ đề ASS chuẩn Unicode tiếng Việt: {ass_file}")

    # 7. Trộn âm thanh và xuất video MP4 hoàn thiện
    try:
        mix_video_and_audio(
            video_path=config.video_path,
            voice_track_wav=voice_track_wav,
            ass_path=ass_file,
            blur_rect=blur_rect,
            output_path=config.output_path,
            work_dir=config.work_dir,
            mask_sigma=config.mask_sigma,
            keep_original_vol=config.keep_original_vol,
            use_ducking=config.use_ducking,
            fonts_dir=config.fonts_dir
        )
    except Exception as e:
        print(f"[LỖI XUẤT VIDEO] {e}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("HOÀN TẤT TOÀN BỘ ĐƯỜNG ỐNG TỰ ĐỘNG THUYẾT MINH VIDEO!")
    print(f"File video thành phẩm: {os.path.abspath(config.output_path)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
