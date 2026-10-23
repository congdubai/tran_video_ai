#!/usr/bin/env python3
"""
Công cụ tự động chuyển đổi Video phụ đề tiếng Trung sang Thuyết minh tiếng Việt.
Tác giả: Senior Software Engineer (hướng dẫn cho dev Java/React).

Cách chạy:
    python dub.py video.mp4 --preview-region
    python dub.py video.mp4 --stop-after ocr
    python dub.py video.mp4 --translate ollama --tts kokoro --keep-original 0.15
"""

import argparse
import json
import os
import sys

# Đảm bảo import được các module trong thư mục src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.config import AppConfig, SubtitleCue
from src.video_utils import get_video_info, generate_preview_region
from src.ocr.engine import process_video_ocr
from src.ocr.grouper import group_cues, cues_to_json_dict, json_dict_to_cues


def parse_arguments() -> AppConfig:
    """
    Xử lý các tham số dòng lệnh (CLI Arguments).
    Giống như CommandLineRunner / args[] trong Spring Boot hoặc process.argv trong Node.js.
    """
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

    # Phân tích region "0.60,0.95" hoặc "0.60:0.95"
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


def step_ocr_and_group(config: AppConfig) -> list:
    """Xử lý Bước 1, Bước 2, Bước 3 (OCR và gom cụm câu). Có hỗ trợ đọc lại cache."""
    cues_file = os.path.join(config.work_dir, "cues.json")
    os.makedirs(config.work_dir, exist_ok=True)

    # Kiểm tra cache cues.json đã tồn tại từ lần chạy trước chưa
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

    # 1. Trích xuất và OCR từng khung hình
    frame_results = process_video_ocr(config.video_path, config)

    # 2. Gom cụm các khung hình liên tiếp thành câu
    print("[*] Đang gom cụm các khung hình liên tiếp và lọc nhiễu...")
    cues = group_cues(
        frame_results=frame_results,
        fps=config.fps,
        sim_threshold=config.sim_threshold,
        min_consecutive_frames=config.min_consecutive_frames
    )

    # 3. Lưu lại file cues.json
    cues_data = cues_to_json_dict(cues)
    with open(cues_file, "w", encoding="utf-8") as f:
        json.dump(cues_data, f, ensure_ascii=False, indent=2)

    print(f"[+] Đã phát hiện {len(cues)} câu phụ đề hợp lệ.")
    print(f"[+] Đã lưu kết quả vào: {cues_file}")
    for c in cues[:5]:  # In thử 5 câu đầu
        print(f"    [{c.start:.2f}s -> {c.end:.2f}s] {c.text_zh}")
    if len(cues) > 5:
        print(f"    ... và {len(cues) - 5} câu tiếp theo.")

    return cues


def main():
    try:
        config = parse_arguments()
    except Exception as e:
        print(f"[LỖI THAM SỐ] {e}", file=sys.stderr)
        sys.exit(1)

    # Kiểm tra file video tồn tại
    if not os.path.exists(config.video_path):
        print(f"[LỖI] Không tìm thấy file video đầu vào: {config.video_path}", file=sys.stderr)
        sys.exit(1)

    # Chế độ 1: Xem trước vùng OCR
    if config.preview_region:
        try:
            step_preview_region(config)
        except Exception as e:
            print(f"[LỖI PREVIEW] {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Chế độ 2: Chạy OCR & Gom câu
    try:
        cues = step_ocr_and_group(config)
    except Exception as e:
        print(f"[LỖI OCR] {e}", file=sys.stderr)
        sys.exit(1)

    # Kiểm tra dừng sau OCR
    if config.stop_after == "ocr":
        print("=" * 60)
        print("[!] Đã dừng theo tham số --stop-after ocr.")
        print(f"[!] Bạn có thể mở file '{config.work_dir}/cues.json' để kiểm tra hoặc chỉnh sửa câu chữ.")
        print("[!] Sau đó chạy lại lệnh (hệ thống sẽ tự động dùng lại file này mà không cần OCR lại).")
        print("=" * 60)
        return

    print("\n[*] Tiếp tục các bước tiếp theo...")


if __name__ == "__main__":
    main()
