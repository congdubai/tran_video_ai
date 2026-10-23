#!/usr/bin/env python3
"""
Flask API Server cho giao diện Web UI của hệ thống Sub-to-Dub.
Cung cấp các endpoint REST để frontend React gọi từng bước trong pipeline.
"""

import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path

# Cấu hình UTF-8 cho Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

# Đảm bảo import được module src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.config import AppConfig, SubtitleCue, OCRBox
from src.video_utils import get_video_info, generate_preview_region
from src.ocr.engine import process_video_ocr
from src.ocr.grouper import group_cues, cues_to_json_dict, json_dict_to_cues
from src.translation import EchoTranslator, OllamaTranslator, GeminiTranslator, translate_cues_in_batches
from src.translation.batch import save_cues_vi, load_cues_vi
from src.subtitles import calculate_blur_rect, generate_ass_file
from src.tts import SilentTTS, KokoroTTS, EdgeTTS, adjust_audio_speed
from src.audio import build_full_voice_track, mix_video_and_audio

app = Flask(__name__, static_folder="web/dist", static_url_path="")
CORS(app)

# ====== Trạng thái toàn cục ======
pipeline_status = {
    "step": "idle",           # idle, preview, ocr, translate, render, done, error
    "progress": 0,            # 0 - 100
    "message": "",
    "logs": [],
    "video_path": None,
    "work_dir": "work",
    "config": {}
}
pipeline_lock = threading.Lock()


def log_msg(msg: str):
    """Ghi log và in ra console."""
    pipeline_status["logs"].append({"time": time.strftime("%H:%M:%S"), "msg": msg})
    # Chỉ giữ 200 dòng log gần nhất
    if len(pipeline_status["logs"]) > 200:
        pipeline_status["logs"] = pipeline_status["logs"][-200:]
    print(msg)


# ====== API Endpoints ======

@app.route("/")
def index():
    """Phục vụ React SPA."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/status")
def get_status():
    """Trả về trạng thái hiện tại của pipeline."""
    return jsonify(pipeline_status)


@app.route("/api/video-info", methods=["POST"])
def api_video_info():
    """Lấy thông tin metadata video."""
    data = request.json or {}
    video_path = data.get("video_path", "")
    if not video_path or not os.path.exists(video_path):
        return jsonify({"error": f"Không tìm thấy file: {video_path}"}), 400
    try:
        info = get_video_info(video_path)
        pipeline_status["video_path"] = video_path
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/preview-region", methods=["POST"])
def api_preview_region():
    """Tạo ảnh xem trước vùng OCR."""
    data = request.json or {}
    video_path = data.get("video_path", pipeline_status.get("video_path", ""))
    region = data.get("region", [0.60, 0.95])
    work_dir = data.get("work_dir", "work")

    if not video_path or not os.path.exists(video_path):
        return jsonify({"error": "Chưa chọn file video"}), 400

    try:
        os.makedirs(work_dir, exist_ok=True)
        out_path = os.path.join(work_dir, "preview_region.jpg")
        generate_preview_region(video_path, tuple(region), out_path)
        return jsonify({"preview_path": out_path, "message": "Đã tạo ảnh xem trước"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/preview-image")
def api_preview_image():
    """Trả về file ảnh preview."""
    work_dir = request.args.get("work_dir", "work")
    img_path = os.path.join(work_dir, "preview_region.jpg")
    if os.path.exists(img_path):
        return send_file(os.path.abspath(img_path), mimetype="image/jpeg")
    return jsonify({"error": "Chưa có ảnh preview"}), 404


@app.route("/api/run-ocr", methods=["POST"])
def api_run_ocr():
    """Chạy OCR và gom câu (chạy nền)."""
    data = request.json or {}
    video_path = data.get("video_path", pipeline_status.get("video_path", ""))
    work_dir = data.get("work_dir", "work")
    region = data.get("region", [0.60, 0.95])
    fps = data.get("fps", 4.0)
    min_conf = data.get("min_conf", 0.6)
    ignore = data.get("ignore", [r"抖音", r"douyin", r"@\w+"])

    if not video_path or not os.path.exists(video_path):
        return jsonify({"error": "Chưa chọn file video"}), 400

    cues_file = os.path.join(work_dir, "cues.json")
    # Kiểm tra cache
    if os.path.exists(cues_file):
        with open(cues_file, "r", encoding="utf-8") as f:
            cues_data = json.load(f)
        pipeline_status["step"] = "ocr_done"
        pipeline_status["progress"] = 100
        log_msg(f"Đã tải {len(cues_data)} câu từ cache {cues_file}")
        return jsonify({"cues": cues_data, "from_cache": True})

    def run_ocr_task():
        try:
            pipeline_status["step"] = "ocr"
            pipeline_status["progress"] = 10
            log_msg("Bắt đầu trích xuất và OCR khung hình...")

            config = AppConfig(
                video_path=video_path,
                work_dir=work_dir,
                region=tuple(region),
                fps=fps,
                min_conf=min_conf,
                ignore_patterns=ignore
            )

            frame_results = process_video_ocr(video_path, config)
            pipeline_status["progress"] = 70
            log_msg(f"OCR hoàn tất {len(frame_results)} khung hình. Đang gom câu...")

            cues = group_cues(frame_results, fps=fps)
            cues_data = cues_to_json_dict(cues)

            os.makedirs(work_dir, exist_ok=True)
            with open(cues_file, "w", encoding="utf-8") as f:
                json.dump(cues_data, f, ensure_ascii=False, indent=2)

            pipeline_status["step"] = "ocr_done"
            pipeline_status["progress"] = 100
            log_msg(f"Phát hiện {len(cues)} câu phụ đề. Đã lưu vào {cues_file}")
        except Exception as e:
            pipeline_status["step"] = "error"
            pipeline_status["message"] = str(e)
            log_msg(f"LỖI OCR: {str(e)}")

    thread = threading.Thread(target=run_ocr_task, daemon=True)
    thread.start()
    return jsonify({"message": "Đang chạy OCR...", "async": True})


@app.route("/api/cues", methods=["GET"])
def api_get_cues():
    """Đọc danh sách câu phụ đề (cues.json)."""
    work_dir = request.args.get("work_dir", "work")
    cues_file = os.path.join(work_dir, "cues.json")
    if not os.path.exists(cues_file):
        return jsonify({"error": "Chưa có file cues.json. Hãy chạy OCR trước."}), 404
    with open(cues_file, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/cues-vi", methods=["GET"])
def api_get_cues_vi():
    """Đọc danh sách câu đã dịch (cues_vi.json)."""
    work_dir = request.args.get("work_dir", "work")
    cues_file = os.path.join(work_dir, "cues_vi.json")
    if not os.path.exists(cues_file):
        return jsonify({"error": "Chưa có bản dịch. Hãy chạy bước Dịch trước."}), 404
    with open(cues_file, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/cues-vi", methods=["PUT"])
def api_save_cues_vi():
    """Lưu lại câu dịch đã chỉnh sửa thủ công từ UI."""
    data = request.json or {}
    work_dir = data.get("work_dir", "work")
    cues_data = data.get("cues", [])
    cues_file = os.path.join(work_dir, "cues_vi.json")
    os.makedirs(work_dir, exist_ok=True)
    with open(cues_file, "w", encoding="utf-8") as f:
        json.dump(cues_data, f, ensure_ascii=False, indent=2)
    log_msg(f"Đã lưu {len(cues_data)} câu dịch đã chỉnh sửa vào {cues_file}")
    return jsonify({"message": f"Đã lưu {len(cues_data)} câu"})


@app.route("/api/run-translate", methods=["POST"])
def api_run_translate():
    """Chạy bước dịch thuật (chạy nền)."""
    data = request.json or {}
    work_dir = data.get("work_dir", "work")
    translator_type = data.get("translator", "echo")
    model_name = data.get("model", None)

    cues_file = os.path.join(work_dir, "cues.json")
    cues_vi_file = os.path.join(work_dir, "cues_vi.json")

    if os.path.exists(cues_vi_file):
        with open(cues_vi_file, "r", encoding="utf-8") as f:
            return jsonify({"cues_vi": json.load(f), "from_cache": True})

    if not os.path.exists(cues_file):
        return jsonify({"error": "Chưa có cues.json. Chạy OCR trước."}), 400

    def run_translate_task():
        try:
            pipeline_status["step"] = "translate"
            pipeline_status["progress"] = 10
            log_msg(f"Bắt đầu dịch thuật bằng [{translator_type}]...")

            with open(cues_file, "r", encoding="utf-8") as f:
                cues_data = json.load(f)
            cues = json_dict_to_cues(cues_data)

            if translator_type == "ollama":
                translator = OllamaTranslator(model=model_name or "qwen2.5:7b")
            elif translator_type == "gemini":
                translator = GeminiTranslator(model=model_name)
            else:
                translator = EchoTranslator()

            translated = translate_cues_in_batches(cues, translator, batch_size=15, context_count=3)
            save_cues_vi(translated, cues_vi_file)

            pipeline_status["step"] = "translate_done"
            pipeline_status["progress"] = 100
            log_msg(f"Dịch hoàn tất {len(translated)} câu. Đã lưu vào {cues_vi_file}")
        except Exception as e:
            pipeline_status["step"] = "error"
            pipeline_status["message"] = str(e)
            log_msg(f"LỖI DỊCH: {str(e)}")

    thread = threading.Thread(target=run_translate_task, daemon=True)
    thread.start()
    return jsonify({"message": "Đang dịch thuật...", "async": True})


@app.route("/api/run-render", methods=["POST"])
def api_run_render():
    """Chạy bước cuối: Làm mờ + ASS + TTS + Trộn âm thanh + Xuất video (chạy nền)."""
    data = request.json or {}
    video_path = data.get("video_path", pipeline_status.get("video_path", ""))
    work_dir = data.get("work_dir", "work")
    output_path = data.get("output", "output.mp4")
    tts_type = data.get("tts", "silent")
    voice = data.get("voice", "ngoc_huyen")
    keep_vol = data.get("keep_original", 0.15)
    duck = data.get("duck", False)
    mask_sigma = data.get("mask_sigma", 30)
    font_name = data.get("font", "Arial")
    font_size = data.get("font_size", None)
    max_tempo = data.get("max_tempo", 1.35)

    cues_vi_file = os.path.join(work_dir, "cues_vi.json")
    if not os.path.exists(cues_vi_file):
        return jsonify({"error": "Chưa có bản dịch cues_vi.json"}), 400

    def run_render_task():
        try:
            pipeline_status["step"] = "render"
            pipeline_status["progress"] = 5
            log_msg("Bắt đầu kết xuất video...")

            # 1. Tải cues_vi
            translated_cues = load_cues_vi(cues_vi_file)
            info = get_video_info(video_path)
            w, h = info["width"], info["height"]
            duration = info["duration"]
            fs = font_size or max(18, int(h * 0.042))

            # 2. Tính vùng làm mờ
            all_boxes = [b for c in translated_cues for b in c.boxes]
            blur_rect = calculate_blur_rect(all_boxes, w, h, fs)
            pipeline_status["progress"] = 10
            log_msg(f"Vùng làm mờ: x={blur_rect[0]}, y={blur_rect[1]}, w={blur_rect[2]}, h={blur_rect[3]}")

            # 3. TTS
            pipeline_status["progress"] = 15
            log_msg(f"Đang tổng hợp giọng đọc [{tts_type}]...")

            if tts_type == "kokoro":
                tts = KokoroTTS(voice=voice, device="cpu")
            elif tts_type == "edge-tts":
                tts = EdgeTTS(voice=voice)
            else:
                tts = SilentTTS()

            audio_dir = os.path.join(work_dir, "audio")
            os.makedirs(audio_dir, exist_ok=True)

            for idx, cue in enumerate(translated_cues):
                text = (cue.text_vi or cue.text_zh).strip()
                raw_wav = os.path.join(audio_dir, f"cue_{cue.id:04d}_raw.wav")
                adj_wav = os.path.join(audio_dir, f"cue_{cue.id:04d}.wav")

                if not os.path.exists(raw_wav):
                    tts.synthesize(text, raw_wav)

                if idx + 1 < len(translated_cues):
                    avail = translated_cues[idx + 1].start - cue.start
                else:
                    avail = max(1.0, cue.end - cue.start)

                new_dur, _ = adjust_audio_speed(raw_wav, adj_wav, avail, max_tempo, tts.sample_rate)
                cue.audio_path = adj_wav
                cue.audio_duration = new_dur

                pct = 15 + int((idx + 1) / len(translated_cues) * 40)
                pipeline_status["progress"] = pct

            log_msg("TTS hoàn tất. Đang ghép track thuyết minh...")

            # 4. Track builder
            master_wav = os.path.join(work_dir, "full_voice_track.wav")
            build_full_voice_track(translated_cues, duration, master_wav, tts.sample_rate)
            pipeline_status["progress"] = 60

            # 5. ASS
            ass_file = os.path.join(work_dir, "subtitles.ass")
            generate_ass_file(translated_cues, w, h, blur_rect, ass_file, font_name, fs)
            pipeline_status["progress"] = 65
            log_msg("Đã tạo file phụ đề ASS. Đang kết xuất video...")

            # 6. Mix & render
            mix_video_and_audio(
                video_path=video_path,
                voice_track_wav=master_wav,
                ass_path=ass_file,
                blur_rect=blur_rect,
                output_path=output_path,
                work_dir=work_dir,
                mask_sigma=mask_sigma,
                keep_original_vol=keep_vol,
                use_ducking=duck
            )

            pipeline_status["step"] = "done"
            pipeline_status["progress"] = 100
            log_msg(f"HOÀN TẤT! Video thành phẩm: {os.path.abspath(output_path)}")
        except Exception as e:
            pipeline_status["step"] = "error"
            pipeline_status["message"] = str(e)
            log_msg(f"LỖI RENDER: {traceback.format_exc()}")

    thread = threading.Thread(target=run_render_task, daemon=True)
    thread.start()
    return jsonify({"message": "Đang kết xuất video...", "async": True})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset trạng thái pipeline."""
    data = request.json or {}
    work_dir = data.get("work_dir", "work")
    clear_files = data.get("clear_files", False)

    pipeline_status["step"] = "idle"
    pipeline_status["progress"] = 0
    pipeline_status["message"] = ""
    pipeline_status["logs"] = []

    if clear_files:
        import shutil
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)
        log_msg(f"Đã xoá thư mục {work_dir}")

    return jsonify({"message": "Đã reset"})


@app.route("/api/download-output")
def api_download():
    """Tải về video thành phẩm."""
    output = request.args.get("path", "output.mp4")
    if os.path.exists(output):
        return send_file(os.path.abspath(output), as_attachment=True)
    return jsonify({"error": "Chưa có file output"}), 404


# Catch-all: phục vụ React SPA cho mọi route khác
@app.route("/<path:path>")
def catch_all(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    print("=" * 60)
    print("SUB-TO-DUB WEB UI SERVER")
    print("Mở trình duyệt tại: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
