"""
File cấu hình và dữ liệu (Data Classes) cho toàn bộ hệ thống Sub-to-Dub.
Dành cho người mới làm quen Python:
- @dataclass giống như POJO/DTO bên Java hoặc interface/type bên TypeScript:
  tự động tạo constructor, toString/repr, equals.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class OCRBox:
    """Toạ độ hộp bao quanh chữ trên video gốc."""
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class OCRDetection:
    """Kết quả OCR của một dòng chữ trong khung hình."""
    text: str
    confidence: float
    box: OCRBox


@dataclass
class FrameOCRResult:
    """Kết quả OCR tổng hợp của một khung hình tại thời điểm timestamp."""
    timestamp: float        # Thời điểm (giây) trong video
    frame_index: int        # Số thứ tự khung hình
    text: str               # Các dòng chữ đã gộp lại (từ trên xuống dưới, trái sang phải)
    boxes: List[OCRBox] = field(default_factory=list)


@dataclass
class SubtitleCue:
    """
    Một câu phụ đề hoàn chỉnh sau khi gom các khung hình liên tiếp.
    Tương đương với 1 dòng trong file SRT hoặc ASS.
    """
    id: int
    start: float            # Thời điểm bắt đầu (giây)
    end: float              # Thời điểm kết thúc (giây)
    text_zh: str            # Câu tiếng Trung gốc
    text_vi: Optional[str] = None  # Bản dịch tiếng Việt
    boxes: List[OCRBox] = field(default_factory=list) # Danh sách các bounding box qua các khung
    audio_path: Optional[str] = None # Đường dẫn file WAV giọng đọc tiếng Việt
    audio_duration: Optional[float] = None # Thời lượng file âm thanh (giây)


@dataclass
class AppConfig:
    """
    Toàn bộ cấu hình hệ thống nhận từ tham số dòng lệnh (CLI Arguments).
    """
    # Đường dẫn file
    video_path: str
    output_path: str = "output.mp4"
    work_dir: str = "work"

    # Bước 1 & 2: Trích khung hình & OCR
    region: Tuple[float, float] = (0.60, 0.95)  # y_min, y_max theo tỉ lệ (0.0 -> 1.0)
    fps: float = 4.0
    min_conf: float = 0.6
    ignore_patterns: List[str] = field(default_factory=lambda: [r"抖音", r"douyin", r"@\w+"])
    frame_diff_threshold: float = 2.0  # Ngưỡng phát hiện khung hình thay đổi để bỏ qua OCR

    # Bước 3: Gom câu (Clustering)
    sim_threshold: float = 0.75  # Độ tương đồng chuỗi difflib
    min_consecutive_frames: int = 2  # Bỏ qua câu xuất hiện < 2 mẫu (lọc nhiễu)

    # Bước 4: Dịch thuật
    translator_type: str = "ollama"  # "ollama", "gemini", "echo"
    model_name: Optional[str] = None
    src_lang: str = "zh"
    batch_size: int = 15

    # Bước 5 & 6: Làm mờ & Phụ đề ASS
    mask_rect: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2) đè thủ công
    mask_sigma: int = 30  # Độ mờ Gaussian Blur
    font_name: str = "Arial"
    font_size: Optional[int] = None
    fonts_dir: Optional[str] = None

    # Bước 7 & 8: TTS & Trộn âm thanh
    tts_type: str = "kokoro"  # "kokoro", "edge-tts", "silent"
    voice: str = "ngoc_huyen"
    tts_device: str = "cpu"
    max_tempo: float = 1.35
    keep_original_vol: float = 0.15
    use_ducking: bool = False

    # Chế độ kiểm tra nhanh
    preview_region: bool = False
    stop_after: Optional[str] = None  # "ocr", "translate"
