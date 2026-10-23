import React, { useState } from 'react';
import { VideoInfo } from '../types';
import { Film, Eye, Play, Sliders, CheckCircle2, ArrowRight } from 'lucide-react';

interface StepVideoProps {
  videoPath: string;
  setVideoPath: (path: string) => void;
  videoInfo: VideoInfo | null;
  onFetchInfo: (path: string) => void;
  region: [number, number];
  setRegion: (region: [number, number]) => void;
  previewUrl: string | null;
  onGeneratePreview: () => void;
  onNext: () => void;
  loading: boolean;
}

export const StepVideo: React.FC<StepVideoProps> = ({
  videoPath,
  setVideoPath,
  videoInfo,
  onFetchInfo,
  region,
  setRegion,
  previewUrl,
  onGeneratePreview,
  onNext,
  loading,
}) => {
  const [quickSamples] = useState([
    'sample_test.mp4',
    'final_test.mp4',
    'test_sample.mp4'
  ]);

  return (
    <div className="space-y-6">
      {/* Video Path & Quick Select */}
      <div className="glass-panel p-6">
        <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
          <Film className="w-5 h-5 text-indigo-400" />
          1. Chọn File Video Đầu Vào
        </h3>
        <p className="text-sm text-slate-400 mb-4">
          Nhập đường dẫn file video có phụ đề tiếng Trung in cứng (hardsub) trên máy tính của bạn.
        </p>

        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              value={videoPath}
              onChange={(e) => setVideoPath(e.target.value)}
              placeholder="Ví dụ: D:\video_dubbing_tool\sample_test.mp4"
              className="input-text font-mono text-sm"
            />
          </div>
          <button
            onClick={() => onFetchInfo(videoPath)}
            disabled={!videoPath || loading}
            className="btn btn-secondary whitespace-nowrap"
          >
            Đọc Thông Số Video
          </button>
        </div>

        {/* Quick select samples */}
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
          <span>File có sẵn:</span>
          {quickSamples.map((sample) => (
            <button
              key={sample}
              onClick={() => {
                setVideoPath(sample);
                onFetchInfo(sample);
              }}
              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 font-mono transition-colors border border-white/5"
            >
              {sample}
            </button>
          ))}
        </div>

        {/* Video metadata card */}
        {videoInfo && (
          <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-slate-900/80 border border-indigo-500/20">
            <div>
              <span className="text-xs text-slate-400 block">Độ phân giải</span>
              <span className="text-sm font-bold text-indigo-300 font-mono">
                {videoInfo.width} × {videoInfo.height}
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block">Khung hình / giây</span>
              <span className="text-sm font-bold text-indigo-300 font-mono">
                {videoInfo.fps.toFixed(2)} FPS
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block">Thời lượng</span>
              <span className="text-sm font-bold text-indigo-300 font-mono">
                {videoInfo.duration.toFixed(1)}s ({Math.floor(videoInfo.duration / 60)}p {Math.floor(videoInfo.duration % 60)}s)
              </span>
            </div>
            <div>
              <span className="text-xs text-slate-400 block">Âm thanh gốc</span>
              <span className="text-sm font-bold text-emerald-400">
                {videoInfo.has_audio ? '✓ Có Audio' : '✕ Không có'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Region Selector & Live Preview */}
      <div className="glass-panel p-6">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            2. Cấu Hình Vùng Nhận Diện Phụ Đề (OCR Region)
          </h3>
          <button
            onClick={onGeneratePreview}
            disabled={!videoPath || loading}
            className="btn btn-primary !py-2 !px-4 text-xs"
          >
            <Eye className="w-4 h-4" />
            Tạo Ảnh Xem Trước Vùng OCR
          </button>
        </div>
        <p className="text-sm text-slate-400 mb-6">
          Chỉ định vùng dọc màn hình chứa phụ đề tiếng Trung để tối ưu tốc độ OCR và tránh nhận diện nhầm logo hoặc tiêu đề trên cao.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div className="space-y-5 p-4 rounded-xl bg-slate-900/60 border border-white/5">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300 font-medium">Bắt đầu từ đỉnh (Y-Min):</span>
                <span className="font-mono text-cyan-400 font-bold">{Math.round(region[0] * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="0.9"
                step="0.05"
                value={region[0]}
                onChange={(e) => setRegion([parseFloat(e.target.value), region[1]])}
                className="w-full accent-cyan-400 cursor-pointer"
              />
              <span className="text-xs text-slate-500">Mặc định 0.60 (chiếm 40% phần dưới cùng video)</span>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300 font-medium">Kết thúc ở đáy (Y-Max):</span>
                <span className="font-mono text-cyan-400 font-bold">{Math.round(region[1] * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={region[1]}
                onChange={(e) => setRegion([region[0], parseFloat(e.target.value)])}
                className="w-full accent-cyan-400 cursor-pointer"
              />
              <span className="text-xs text-slate-500">Mặc định 0.95 (tránh sát viền dưới màn hình)</span>
            </div>

            <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-500/20 text-xs text-indigo-300">
              💡 <strong>Mẹo:</strong> Khung chữ nhật màu xanh lục trong ảnh xem trước chính là phạm vi OCR quét chữ và cũng là vùng sẽ làm mờ chữ gốc.
            </div>
          </div>

          {/* Preview Image Box */}
          <div className="flex flex-col items-center justify-center p-3 rounded-xl bg-black/50 border border-white/10 min-h-[220px]">
            {previewUrl ? (
              <div className="relative rounded-lg overflow-hidden border border-cyan-500/40 shadow-lg shadow-cyan-500/10 max-h-[300px]">
                <img
                  src={previewUrl}
                  alt="OCR Region Preview"
                  className="max-h-[280px] w-auto object-contain mx-auto"
                />
                <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 text-[11px] text-cyan-300 font-mono">
                  Vùng quét [{Math.round(region[0]*100)}% - {Math.round(region[1]*100)}%]
                </span>
              </div>
            ) : (
              <div className="text-center text-slate-500 p-6">
                <Eye className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">Chưa có ảnh xem trước</p>
                <p className="text-xs mt-1">Bấm nút "Tạo Ảnh Xem Trước" để kiểm tra khung quét</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Next */}
      <div className="flex justify-end">
        <button
          onClick={onNext}
          disabled={!videoPath}
          className="btn btn-primary !px-6 !py-3 text-base shadow-lg shadow-indigo-500/20"
        >
          Sang Bước 2: Quét Phụ Đề OCR
          <ArrowRight className="w-5 h-5 ml-1" />
        </button>
      </div>
    </div>
  );
};
