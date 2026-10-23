"""
Module Engine OCR: Nhận diện ký tự chữ Hán trong khung hình bằng RapidOCR (ONNXRuntime).
Giải thích cho người mới:
- RapidOCR là thư viện OCR dựa trên PaddleOCR nhưng chạy bằng ONNXRuntime nên rất nhẹ,
  chạy tốt trên CPU mà không đòi hỏi GPU hay cài đặt CUDA phức tạp.
- Khi trích xuất ảnh, ta chỉ cắt (crop) dải phụ đề ở dưới đáy video để tăng tốc.
- Bounding Box nhận được từ ảnh cắt sẽ được cộng bù toạ độ `y_crop_offset` để quy về toạ độ
  video gốc 100%.
- Cơ chế phát hiện khung hình không đổi (Frame Diff): So sánh ảnh hiện tại với ảnh trước.
  Nếu sai khác trung bình dưới ngưỡng (threshold), ta bỏ qua inference OCR và dùng lại kết quả cũ.
"""

import os
import glob
import subprocess
from typing import List, Tuple, Optional
from ..config import OCRBox, OCRDetection, FrameOCRResult, AppConfig
from .filter import filter_and_sort_detections, merge_detections_to_text


class OCREngine:
    def __init__(self, min_conf: float = 0.6, ignore_patterns: List[str] = None):
        self.min_conf = min_conf
        self.ignore_patterns = ignore_patterns or [r"抖音", r"douyin", r"@\w+"]
        self._engine = None

    def _get_engine(self):
        """Khởi tạo lazy RapidOCR để không làm chậm lúc khởi động CLI."""
        if self._engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                # Chạy trên CPU để tiết kiệm VRAM theo yêu cầu
                self._engine = RapidOCR()
            except ImportError:
                raise RuntimeError(
                    "Chưa cài đặt thư viện 'rapidocr-onnxruntime'.\n"
                    "Vui lòng chạy lệnh: pip install rapidocr-onnxruntime\n"
                    "(Thư viện này đã có sẵn pre-trained model tiếng Trung, chạy mượt trên CPU)."
                )
        return self._engine

    def recognize_frame(
        self,
        image_input,
        y_crop_offset: int = 0
    ) -> List[OCRDetection]:
        """
        Nhận diện văn bản trên một ảnh (hoặc mảng ảnh / đường dẫn file ảnh).
        y_crop_offset: Số pixel đã bị cắt ở cạnh trên của video gốc.
        """
        engine = self._get_engine()

        # RapidOCR chấp nhận đường dẫn file, numpy array hoặc bytes
        ocr_result, _ = engine(image_input)
        if not ocr_result:
            return []

        detections: List[OCRDetection] = []
        for item in ocr_result:
            # item có cấu trúc: [box_points, text, score]
            # box_points gồm 4 góc: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
            box_points, text, score = item
            score = float(score)

            xs = [pt[0] for pt in box_points]
            ys = [pt[1] for pt in box_points]

            bx1 = int(round(min(xs)))
            bx2 = int(round(max(xs)))
            # Cộng bù y_crop_offset để chuyển về toạ độ gốc của video
            by1 = int(round(min(ys))) + y_crop_offset
            by2 = int(round(max(ys))) + y_crop_offset

            box = OCRBox(x1=bx1, y1=by1, x2=bx2, y2=by2)
            detections.append(OCRDetection(text=text, confidence=score, box=box))

        return filter_and_sort_detections(
            detections,
            min_confidence=self.min_conf,
            ignore_patterns=self.ignore_patterns
        )


def is_frame_similar(prev_image_path: str, curr_image_path: str, threshold: float = 2.0) -> bool:
    """
    So sánh nhanh 2 khung hình xem có gần như giống hệt nhau không.
    Sử dụng PIL (Pillow) để tính Mean Absolute Difference.
    Nếu PIL chưa có, trả về False (vẫn OCR bình thường).
    """
    try:
        from PIL import Image, ImageChops, ImageStat
        im1 = Image.open(prev_image_path).convert("L") # Chuyển grayscale
        im2 = Image.open(curr_image_path).convert("L")
        diff = ImageChops.difference(im1, im2)
        stat = ImageStat.Stat(diff)
        diff_val = stat.mean[0] # Giá trị trung bình sai khác
        return diff_val < threshold
    except Exception:
        return False


def extract_cropped_frames_ffmpeg(
    video_path: str,
    output_dir: str,
    region: Tuple[float, float],
    fps: float = 4.0
) -> Tuple[int, int, int]:
    """
    Dùng FFmpeg trích xuất hàng loạt khung hình đã crop vào output_dir.
    Trả về: (full_width, full_height, y_crop_offset)
    """
    from ..video_utils import get_video_info
    info = get_video_info(video_path)
    width = info["width"]
    height = info["height"]

    y_min_ratio, y_max_ratio = region
    y1 = int(y_min_ratio * height)
    y2 = int(y_max_ratio * height)
    crop_h = max(10, y2 - y1)

    os.makedirs(output_dir, exist_ok=True)
    out_pattern = os.path.join(output_dir, "frame_%06d.jpg")

    # Filter: lấy fps khung hình mỗi giây, sau đó cắt vùng phụ đề
    vf = f"fps={fps},crop={width}:{crop_h}:0:{y1}"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vf", vf,
        "-q:v", "3",       # Chất lượng ảnh JPG tốt để OCR
        out_pattern
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return width, height, y1


def process_video_ocr(
    video_path: str,
    config: AppConfig
) -> List[FrameOCRResult]:
    """
    Quy trình Bước 1 & Bước 2 hoàn chỉnh:
    1. FFmpeg cắt khung hình vùng phụ đề theo config.fps và config.region.
    2. Duyệt từng khung hình: bỏ qua OCR nếu khung hình không đổi.
    3. OCR và lưu lại FrameOCRResult.
    """
    frames_dir = os.path.join(config.work_dir, "raw_frames")
    width, height, y_offset = extract_cropped_frames_ffmpeg(
        video_path=video_path,
        output_dir=frames_dir,
        region=config.region,
        fps=config.fps
    )

    frame_files = sorted(glob.glob(os.path.join(frames_dir, "frame_*.jpg")))
    ocr_engine = OCREngine(min_conf=config.min_conf, ignore_patterns=config.ignore_patterns)

    results: List[FrameOCRResult] = []
    prev_file = None
    prev_text = ""
    prev_boxes: List[OCRBox] = []

    print(f"[*] Bắt đầu OCR {len(frame_files)} khung hình (FPS = {config.fps})...")

    for idx, fpath in enumerate(frame_files):
        # Tính timestamp dựa trên frame index và fps
        timestamp = idx / config.fps

        # Tối ưu: Kiểm tra nếu khung hình tương tự khung trước thì tái sử dụng kết quả
        if prev_file is not None and is_frame_similar(prev_file, fpath, threshold=config.frame_diff_threshold):
            text = prev_text
            boxes = prev_boxes
        else:
            detections = ocr_engine.recognize_frame(fpath, y_crop_offset=y_offset)
            text = merge_detections_to_text(detections)
            boxes = [d.box for d in detections]
            prev_text = text
            prev_boxes = boxes

        prev_file = fpath
        results.append(
            FrameOCRResult(
                timestamp=timestamp,
                frame_index=idx,
                text=text,
                boxes=boxes
            )
        )

        if (idx + 1) % 20 == 0 or idx == len(frame_files) - 1:
            print(f"    - Tiến độ OCR: {idx + 1}/{len(frame_files)} frames...")

    return results
