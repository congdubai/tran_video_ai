"""
Script tạo video mẫu thử nghiệm (Synthetic Test Video) có phụ đề tiếng Trung in cứng.
Dùng PIL để vẽ chữ tiếng Trung chuẩn xác vào từng khung hình,
sau đó dùng FFmpeg ghép thành video MP4 có cả âm thanh nền để kiểm thử toàn bộ đường ống.
"""

import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageFont

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def create_sample_video(output_mp4: str = "sample_test.mp4", duration: int = 6):
    width, height = 640, 360
    fps = 25
    total_frames = duration * fps

    # Thử tìm font hỗ trợ tiếng Trung trên Windows
    font_candidates = [
        "C:/Windows/Fonts/msyh.ttc",    # Microsoft YaHei
        "C:/Windows/Fonts/simsun.ttc",   # SimSun
        "C:/Windows/Fonts/simhei.ttf",   # SimHei
        "C:/Windows/Fonts/arial.ttf"
    ]
    font_path = None
    for fc in font_candidates:
        if os.path.exists(fc):
            font_path = fc
            break

    try:
        font = ImageFont.truetype(font_path, 26) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    frames_dir = "temp_test_frames"
    os.makedirs(frames_dir, exist_ok=True)

    print(f"[*] Đang vẽ {total_frames} khung hình video mẫu (640x360)...")

    for f_idx in range(total_frames):
        sec = f_idx / fps

        # Xác định câu phụ đề hiển thị theo thời gian
        if 0.5 <= sec < 3.0:
            sub_text = "你好世界欢迎来到这里"  # "Xin chào thế giới chào mừng đến đây"
        elif 3.5 <= sec < 5.8:
            sub_text = "今天的天气真好"          # "Thời tiết hôm nay thật đẹp"
        else:
            sub_text = ""

        # Tạo ảnh nền màu tối gradient / navy
        img = Image.new("RGB", (width, height), color=(20, 35, 60))
        draw = ImageDraw.Draw(img)

        # Vẽ một vài chi tiết chuyển động nhẹ để video sinh động
        bar_x = int((f_idx * 4) % width)
        draw.rectangle([bar_x, 50, bar_x + 30, 80], fill=(70, 130, 180))

        # Vẽ phụ đề tiếng Trung ở đáy màn hình (y = 80% chiều cao)
        if sub_text:
            sub_y = int(height * 0.82)
            # Lấy kích thước chữ để căn giữa
            bbox = draw.textbbox((0, 0), sub_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_x = (width - text_w) // 2

            # Vẽ viền đen nhẹ quanh chữ
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                draw.text((text_x + dx, sub_y + dy), sub_text, font=font, fill=(0, 0, 0))
            # Vẽ chữ màu trắng
            draw.text((text_x, sub_y), sub_text, font=font, fill=(255, 255, 255))

        img_path = os.path.join(frames_dir, f"f_{f_idx:05d}.png")
        img.save(img_path)

    print("[*] Đang dùng FFmpeg ghép khung hình và tạo âm thanh nền mẫu...")
    # FFmpeg ghép ảnh thành video và thêm âm thanh sine wave 440Hz nhẹ làm nhạc nền
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "f_%05d.png"),
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_mp4
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    # Dọn dẹp ảnh tạm
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    os.rmdir(frames_dir)

    print(f"[+] ĐÃ TẠO VIDEO MẪU THÀNH CÔNG: {output_mp4}")


if __name__ == "__main__":
    create_sample_video("sample_test.mp4", duration=6)
