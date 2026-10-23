# AUTO SUB-TO-DUB: CÔNG CỤ DỊCH VÀ THUYẾT MINH VIDEO PHỤ ĐỀ TIẾNG TRUNG SANG TIẾNG VIỆT

Công cụ dòng lệnh (CLI) chạy hoàn toàn **cục bộ (Local)** trên máy tính cá nhân.
Tự động quét phụ đề tiếng Trung in cứng trên video bằng OCR -> Dịch sang tiếng Việt bằng LLM -> Làm mờ dải phụ đề cũ -> Chèn phụ đề tiếng Việt chuẩn toạ độ -> Đọc thuyết minh bằng giọng tiếng Việt (Kokoro / Edge-TTS) đè lên âm thanh gốc đã hạ nhỏ.

---

## MỤC LỤC
1. [Luồng hoạt động (Pipeline)](#1-luồng-hoạt-động-pipeline)
2. [Cấu trúc thư mục dự án](#2-cấu-trúc-thư-mục-dự-án)
3. [Yêu cầu hệ thống](#3-yêu-cầu-hệ-thống)
4. [Hướng dẫn cài đặt từng bước](#4-hướng-dẫn-cài-đặt-từng-bước)
5. [Hướng dẫn sử dụng chi tiết](#5-hướng-dẫn-sử-dụng-chi-tiết)
6. [Bảng tham số dòng lệnh (CLI Options)](#6-bảng-tham-số-dòng-lệnh-cli-options)
7. [Chạy Unit Test kiểm thử](#7-chạy-unit-test-kiểm-thử)
8. [Xử lý lỗi thường gặp (Troubleshooting)](#8-xử-lý-lỗi-thường-gặp-troubleshooting)

---

## 1. LUỒNG HOẠT ĐỘNG (PIPELINE)

```
[Video gốc có chữ Trung]
        │
        ▼ (Bước 1 & 2)
  [FFmpeg Crop & FPS=4] ──> [RapidOCR trên CPU] ──> [Lọc Watermark & Sort]
        │
        ▼ (Bước 3)
  [Gom câu bằng Difflib + Majority Vote] ──> Lưu cache: work/cues.json
        │
        ▼ (Bước 4)
  [Dịch thuật Batch 15 câu + 3 Context + Ràng buộc max_words] ──> Lưu cache: work/cues_vi.json
  (Ollama Qwen 2.5 7B / Gemini REST API / Echo test)
        │
        ├────────────────────────────────┬────────────────────────────────┐
        ▼ (Bước 5 & 6)                   ▼ (Bước 7)                       ▼ (Bước 8)
  [Tính Percentile 2% & 98%]       [TTS Kokoro: giọng Ngọc Huyền]    [FFmpeg Filter Complex]
  [Sinh file subtitles.ass]        [Tăng tốc atempo (max 1.35x)]     - Gaussian Blur chữ cũ (sigma 30)
  (Toạ độ \an5\pos chính giữa)     [Ghép full track WAV 24000Hz]     - Overlay phụ đề ASS tiếng Việt
        │                                │                           - Giữ tiếng gốc (hạ nhỏ 15%)
        │                                │                           - Tuỳ chọn --duck tự giảm nhạc nền
        └────────────────────────────────┴───────────────────────────┘
                                         │
                                         ▼
                            [Video MP4 Hoàn Thành]
```

---

## 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
D:\video_dubbing_tool/
├── dub.py                  # Entrypoint CLI chạy chương trình chính
├── requirements.txt        # Danh sách thư viện Python cần cài
├── README.md               # Tài liệu hướng dẫn sử dụng tiếng Việt
├── .gitignore              # Bỏ qua các file rác và thư mục cache media
├── src/
│   ├── config.py           # Dataclasses cấu hình và dữ liệu phụ đề
│   ├── video_utils.py      # Tiện ích FFprobe lấy metadata và FFmpeg preview
│   ├── ocr/
│   │   ├── engine.py       # Engine RapidOCR (CPU, crop dải & frame-diff skip)
│   │   ├── filter.py       # Lọc watermark Douyin regex & sắp xếp toạ độ
│   │   └── grouper.py      # Thuật toán gom cụm câu difflib & voting
│   ├── translation/
│   │   ├── base.py         # Interface trừu tượng BaseTranslator
│   │   ├── echo.py         # Provider giả lập (Mock/Echo) để test không cần model
│   │   ├── ollama.py       # Provider cục bộ gọi Ollama REST (qwen2.5:7b)
│   │   ├── gemini.py       # Provider trực tuyến gọi Gemini REST API
│   │   ├── parser.py       # Bóc tách JSON chống lỗi Markdown (Robust parser)
│   │   └── batch.py        # Điều phối dịch 15 câu/lô + ngữ cảnh + max_words
│   ├── subtitles/
│   │   ├── mask.py         # Tính toạ độ vùng làm mờ theo percentile 2 & 98
│   │   ├── ass_generator.py# Sinh file phụ đề .ass căn giữa \an5\pos
│   │   └── blur.py         # FFmpeg filter gblur và ass overlay
│   ├── tts/
│   │   ├── base.py         # Interface trừu tượng BaseTTS
│   │   ├── silent.py       # Provider âm thanh im lặng (test không cần model)
│   │   ├── kokoro.py       # Provider Kokoro-Vietnamese (giọng ngoc_huyen, 24000Hz)
│   │   ├── edge.py         # Provider Microsoft Edge-TTS dự phòng
│   │   └── speed.py        # Co giãn tốc độ bằng FFmpeg atempo (max 1.35x)
│   └── audio/
│       ├── track_builder.py# Ghép toàn bộ câu thành track 24000Hz mono không chồng chéo
│       └── mixer.py        # Trộn hình ảnh mờ + phụ đề ASS + âm thanh gốc + thuyết minh (--duck)
└── tests/
    ├── test_filter.py      # Test lọc regex watermark & sắp xếp dòng
    ├── test_grouper.py     # Test thuật toán gom câu, lỡ frame, voting
    ├── test_translation.py  # Test robust JSON parser, batching, max_words
    ├── test_subtitles.py   # Test percentile làm mờ và sinh file ASS
    └── test_audio.py       # Test SilentTTS, atempo co giãn và track builder
```

---

## 3. YÊU CẦU HỆ THỐNG
- **Hệ điều hành**: Windows 10/11 hoặc Linux (Ubuntu 20.04+).
- **Phần cứng**:
  + **GPU**: NVIDIA RTX 3050 (6GB VRAM) hoặc tương đương (dành trọn VRAM để chạy model dịch Ollama Qwen 2.5 7B).
  + **RAM**: Tối thiểu 8GB (khuyến nghị 16GB).
  + **CPU**: Chạy OCR (RapidOCR) và TTS (Kokoro) hoàn toàn trên CPU để tiết kiệm VRAM.
- **Phần mềm**:
  + **Python**: Phiên bản 3.10 hoặc 3.11 (64-bit).
  + **FFmpeg**: Đã cài đặt và đã thêm vào biến môi trường `PATH`.

---

## 4. HƯỚNG DẪN CÀI ĐẶT TỪNG BƯỚC

### Bước 4.1: Kiểm tra Python và FFmpeg
Mở terminal (PowerShell trên Windows hoặc Bash trên Linux) và kiểm tra:
```bash
python --version
ffmpeg -version
```
*Lưu ý: Nếu chưa có FFmpeg, tải bản build Windows tại [gyan.dev/ffmpeg](https://www.gyan.dev/ffmpeg/builds/) và thêm thư mục `bin` vào biến môi trường `PATH`.*

### Bước 4.2: Tạo môi trường ảo (Virtual Environment)
Tại thư mục dự án `D:\video_dubbing_tool`:
```bash
cd D:\video_dubbing_tool
python -m venv venv

# Kích hoạt trên Windows PowerShell:
.\venv\Scripts\Activate.ps1

# (Hoặc kích hoạt trên Windows CMD):
.\venv\Scripts\activate.bat
```

### Bước 4.3: Cài đặt các thư viện phụ thuộc
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 4.4: Cài đặt Kokoro-Vietnamese
Cài đặt thư viện giọng đọc tiếng Việt Kokoro từ GitHub của tác giả Đinh Thuận:
```bash
pip install git+https://github.com/iamdinhthuan/Kokoro-Vietnamese.git
```
*(Hoặc clone trực tiếp thư mục repo vào máy nếu muốn xem mã nguồn).*

### Bước 4.5: Cài đặt và cấu hình Ollama (Bộ máy dịch cục bộ)
1. Tải và cài đặt Ollama từ trang chủ: [https://ollama.com/download](https://ollama.com/download).
2. Sau khi cài đặt, mở terminal và tải model **Qwen 2.5 7B** (rất xuất sắc khi dịch Trung - Việt, bản Q4 chạy tốn khoảng 4.5GB VRAM):
```bash
ollama pull qwen2.5:7b
```
3. Đảm bảo dịch vụ Ollama đang hoạt động (gõ `ollama list` để kiểm tra model đã sẵn sàng).

---

## 5. HƯỚNG DẪN SỬ DỤNG CHI TIẾT

Quy trình làm việc chuẩn gồm 3 giai đoạn giúp bạn kiểm soát 100% chất lượng sản phẩm:

### Giai đoạn 1: Xem trước và tinh chỉnh vùng phụ đề
Chạy lệnh preview để kiểm tra xem khung chữ nhật đỏ có bao trọn dòng chữ tiếng Trung không:
```bash
python dub.py video.mp4 --preview-region
```
- Mở file ảnh `work/preview_region.jpg` lên xem.
- Nếu khung đỏ hơi cao hoặc hơi thấp, điều chỉnh bằng `--region`:
```bash
# Ví dụ lấy từ 65% đến 92% chiều cao màn hình:
python dub.py video.mp4 --preview-region --region 0.65,0.92
```

### Giai đoạn 2: OCR và kiểm tra danh sách câu
```bash
python dub.py video.mp4 --region 0.65,0.92 --stop-after ocr
```
- Chương trình quét phụ đề và gom thành các câu hoàn chỉnh lưu tại `work/cues.json`.
- Bạn có thể mở `work/cues.json` để kiểm tra xem có câu nào bị nhận diện sai chữ không.

### Giai đoạn 3: Dịch thuật và trau chuốt bản dịch tiếng Việt
```bash
python dub.py video.mp4 --translate ollama --stop-after translate
```
- Chương trình dịch toàn bộ câu theo lô 15 câu và lưu vào `work/cues_vi.json`.
- **CỰC KỲ TIỆN LỢI**: Bạn có thể mở `work/cues_vi.json` bằng VS Code / Notepad để sửa lại câu từ cho mượt mà, thuần Việt hơn. Khi chạy lại, chương trình **tự động dùng lại file này mà không cần dịch lại**!

### Giai đoạn 4: Chạy toàn bộ (Làm mờ + Phụ đề ASS + Thuyết minh Kokoro)
```bash
python dub.py video.mp4 --translate ollama --tts kokoro --voice ngoc_huyen --keep-original 0.15 --duck --out video_thuyet_minh.mp4
```
Chương trình sẽ tự động:
1. Nạp bản dịch từ `work/cues_vi.json`.
2. Tạo dải Gaussian Blur làm mờ phụ đề cũ.
3. Sinh file phụ đề tiếng Việt `.ass` căn giữa chính xác.
4. Kokoro đọc bản dịch thành giọng Ngọc Huyền 24000Hz, tự tăng tốc nếu câu dài.
5. Trộn giọng Việt lên trên video, tự động hạ nhỏ âm thanh gốc khi có thuyết minh (`--duck`).
6. Xuất video cuối cùng: `video_thuyet_minh.mp4`.

---

## 6. BẢNG THAM SỐ DÒNG LỆNH (CLI OPTIONS)

| Tham số | Mặc định | Ý nghĩa & Mô tả |
| :--- | :---: | :--- |
| `video` | *(Bắt buộc)* | Đường dẫn file video đầu vào (.mp4, .mkv, .mov...). |
| `--out` | `output.mp4` | Đường dẫn file video kết quả đầu ra. |
| `--work` | `work` | Thư mục lưu các file tạm thời và cache trung gian. |
| `--preview-region`| `False` | Xuất ảnh một khung hình có vẽ khung chữ nhật đỏ rồi dừng lại. |
| `--stop-after` | `None` | Dừng sau bước `ocr` hoặc `translate` để kiểm tra/sửa tay file JSON. |
| `--region` | `0.60,0.95` | Tỉ lệ chiều cao vùng phụ đề `y_min,y_max` (từ 0.0 đến 1.0). |
| `--fps` | `4.0` | Số khung hình trích xuất mỗi giây để OCR (4 khung/giây là chuẩn nhất). |
| `--min-conf` | `0.6` | Độ tin cậy tối thiểu của ký tự OCR (0.0 đến 1.0). |
| `--ignore` | `抖音,douyin,@\w+` | Các biểu thức chính quy (Regex) để loại trừ watermark kênh. |
| `--translate` | `ollama` | Bộ máy dịch: `ollama` (cục bộ), `gemini` (REST API), `echo` (test). |
| `--model` | `None` | Tên model dịch (`qwen2.5:7b` cho ollama, `gemini-1.5-flash` cho gemini). |
| `--mask-rect` | `None` | Ghi đè toạ độ vùng làm mờ thủ công: `x1,y1,x2,y2`. |
| `--mask-sigma` | `30` | Độ mờ Gaussian Blur (sigma càng cao thì càng mờ nhoè). |
| `--font` | `Arial` | Tên font chữ phụ đề tiếng Việt (Arial hỗ trợ 100% tiếng Việt có dấu). |
| `--font-size` | `None` | Cỡ chữ phụ đề (nếu để None sẽ tự động tính theo chiều cao video). |
| `--tts` | `kokoro` | Bộ máy đọc giọng: `kokoro`, `edge-tts` (dự phòng), `silent` (test). |
| `--voice` | `ngoc_huyen` | Tên giọng đọc của Kokoro (mặc định giọng nữ Ngọc Huyền). |
| `--tts-device` | `cpu` | Thiết bị chạy TTS (`cpu` hoặc `cuda`). Mặc định CPU để dành VRAM. |
| `--max-tempo` | `1.35` | Tốc độ nói tối đa cho phép tăng tốc khi câu đọc dài hơn khung hình. |
| `--keep-original`| `0.15` | Âm lượng giữ lại của âm thanh gốc (0.15 = 15%). |
| `--duck` | `False` | Bật Sidechain compression: âm gốc tự nhỏ khi có thuyết minh và to lại khi ngắt câu. |

---

## 7. CHẠY UNIT TEST KIỂM THỬ

Dự án đi kèm bộ kiểm thử toàn diện bằng `pytest` không phụ thuộc vào model AI hay GPU:
```bash
pytest -v tests/
```
Các kịch bản được kiểm tra:
1. `test_filter.py`: Lọc sạch watermark Douyin/TikTok và sắp xếp toạ độ dòng chữ từ trên xuống.
2. `test_grouper.py`: Gom câu bằng difflib (ngưỡng 0.75), lỡ 1 frame trống, lọc nhiễu < 2 frame, bầu chọn số đông.
3. `test_translation.py`: Parse JSON chuẩn/lỗi Markdown, tính toán max_words theo thời lượng, kiểm thử EchoTranslator.
4. `test_subtitles.py`: Tính vùng làm mờ percentile 2 và 98 chẵn pixel, sinh file ASS `\an5\pos` chuẩn dấu tiếng Việt.
5. `test_audio.py`: Sinh WAV 24000Hz SilentTTS, co giãn tốc độ atempo và ghép nối track không chồng chéo.

---

## 8. XỬ LÝ LỖI THƯỜNG GẶP (TROUBLESHOOTING)

### Lỗi 1: `Không thể kết nối đến máy chủ Ollama tại http://localhost:11434`
- **Nguyên nhân**: Phần mềm Ollama chưa được bật hoặc service bị tắt.
- **Cách khắc phục**:
  + Mở ứng dụng Ollama trên máy tính.
  + Hoặc mở terminal gõ: `ollama serve`.

### Lỗi 2: `Model 'qwen2.5:7b' chưa được tải trong Ollama`
- **Nguyên nhân**: Bạn chưa tải trọng số model về máy.
- **Cách khắc phục**: Mở terminal chạy lệnh:
  ```bash
  ollama pull qwen2.5:7b
  ```

### Lỗi 3: `Chưa tìm thấy biến môi trường 'GEMINI_API_KEY'` (Khi dùng `--translate gemini`)
- **Nguyên nhân**: Chưa gán khoá API của Google Gemini.
- **Cách khắc phục**:
  + Trên PowerShell: `$env:GEMINI_API_KEY = "AIzaSy..."`
  + Trên CMD: `set GEMINI_API_KEY=AIzaSy...`
  + Trên Linux: `export GEMINI_API_KEY="AIzaSy..."`

### Lỗi 4: `Chưa tìm thấy lệnh 'ffmpeg' hoặc 'ffprobe'`
- **Nguyên nhân**: Chưa cài FFmpeg hoặc chưa thêm vào biến môi trường `PATH`.
- **Cách khắc phục**: Tải FFmpeg, giải nén vào thư mục `C:\ffmpeg`, sau đó thêm `C:\ffmpeg\bin` vào `Environment Variables -> System PATH` của Windows.

### Lỗi 5: Cảnh báo `Câu bị tràn thời lượng (Giọng đọc > Khoảng trống)`
- **Hiện tượng**: Giọng thuyết minh hơi dài so với thời gian nhân vật nói.
- **Cơ chế xử lý tự động**: Hệ thống đã tự động kích hoạt `atempo` (tối đa 1.35x) và cho phép giọng nói lấn nhẹ sang khoảng lặng kế tiếp mà **không bị cắt cụt** và **không nói đè lên câu sau**.
- **Cách tối ưu bằng tay**:
  Mở file `work/cues_vi.json`, tìm câu tương ứng và chỉnh sửa từ ngữ ngắn gọn, súc tích hơn rồi chạy lại lệnh.
