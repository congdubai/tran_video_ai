import React, { useState } from 'react';
import { SubtitleCue, PipelineStatus } from '../types';
import { ScanText, ArrowRight, ArrowLeft, CheckCircle2, Clock, Check, Sparkles } from 'lucide-react';

interface StepOcrProps {
  cues: SubtitleCue[];
  status: PipelineStatus;
  onRunOcr: (fps: number, minConf: number) => void;
  onNext: () => void;
  onPrev: () => void;
  loading: boolean;
}

export const StepOcr: React.FC<StepOcrProps> = ({
  cues,
  status,
  onRunOcr,
  onNext,
  onPrev,
  loading,
}) => {
  const [fps, setFps] = useState<number>(4.0);
  const [minConf, setMinConf] = useState<number>(0.6);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const ms = Math.floor((secs % 1) * 1000);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  const isOcrRunning = status.step === 'ocr';

  return (
    <div className="space-y-6">
      {/* OCR Control Panel */}
      <div className="glass-panel p-6">
        <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
          <ScanText className="w-5 h-5 text-indigo-400" />
          Quét Khung Hình & Nhận Diện Chữ Tiếng Trung (PaddleOCR)
        </h3>
        <p className="text-sm text-slate-400 mb-6">
          Trích xuất các khung hình video theo chu kỳ, lọc logo Douyin / ID TikTok và gom các khung hình liên tiếp thành từng câu thoại hoàn chỉnh.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5">
            <label className="text-xs text-slate-400 block mb-1">Tần số quét (FPS)</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="10"
                step="0.5"
                value={fps}
                disabled={isOcrRunning}
                onChange={(e) => setFps(parseFloat(e.target.value) || 4.0)}
                className="input-text font-mono text-sm !py-1.5"
              />
              <span className="text-xs text-slate-400 font-mono">khung/s</span>
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Khuyên dùng: 3.0 - 5.0</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5">
            <label className="text-xs text-slate-400 block mb-1">Độ tin cậy tối thiểu</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0.1"
                max="0.99"
                step="0.05"
                value={minConf}
                disabled={isOcrRunning}
                onChange={(e) => setMinConf(parseFloat(e.target.value) || 0.6)}
                className="input-text font-mono text-sm !py-1.5"
              />
              <span className="text-xs text-slate-400 font-mono">{Math.round(minConf * 100)}%</span>
            </div>
            <span className="text-[11px] text-slate-500 mt-1 block">Lọc nhiễu ảnh và bóng chữ</span>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => onRunOcr(fps, minConf)}
              disabled={isOcrRunning || loading}
              className="btn btn-primary w-full !py-3 shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2"
            >
              <ScanText className={`w-4 h-4 ${isOcrRunning ? 'animate-spin' : ''}`} />
              {isOcrRunning ? `Đang quét OCR... (${status.progress}%)` : (cues.length > 0 ? 'Quét Lại Từ Đầu' : 'Bắt Đầu Quét OCR')}
            </button>
          </div>
        </div>

        {/* Progress bar during OCR */}
        {isOcrRunning && (
          <div className="mt-4 p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30">
            <div className="flex justify-between text-xs mb-1.5 text-indigo-300">
              <span className="font-semibold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                Đang xử lý PaddleOCR trên GPU RTX 3050...
              </span>
              <span className="font-mono font-bold text-cyan-400">{status.progress}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-indigo-500 to-cyan-400 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${status.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Cues Result List */}
      <div className="glass-panel p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h4 className="text-base font-bold text-white flex items-center gap-2">
              Danh Sách Câu Phụ Đề Nhận Diện
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
                {cues.length} câu thoại
              </span>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Các đoạn chữ đã được gom thời gian bắt đầu và kết thúc chuẩn xác.
            </p>
          </div>
        </div>

        {cues.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-white/10 rounded-xl bg-slate-900/30 text-slate-500">
            <ScanText className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">Chưa có dữ liệu câu thoại</p>
            <p className="text-xs mt-1">Bấm "Bắt Đầu Quét OCR" ở trên để chạy nhận diện</p>
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[420px] rounded-xl border border-white/10">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-slate-900/90 text-xs text-slate-400 uppercase sticky top-0 backdrop-blur-md">
                <tr>
                  <th className="py-3 px-4 w-12 text-center">#</th>
                  <th className="py-3 px-4 w-48">Thời gian (Start → End)</th>
                  <th className="py-3 px-4 w-24">Thời lượng</th>
                  <th className="py-3 px-4">Nội dung Tiếng Trung (OCR)</th>
                  <th className="py-3 px-4 w-28 text-center">Độ tin cậy</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 bg-slate-950/40">
                {cues.map((cue, idx) => {
                  const duration = (cue.end - cue.start).toFixed(2);
                  return (
                    <tr key={cue.id || idx} className="hover:bg-indigo-500/5 transition-colors">
                      <td className="py-3 px-4 text-center font-mono text-xs text-slate-500">
                        {idx + 1}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-cyan-300">
                        {formatTime(cue.start)} → {formatTime(cue.end)}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-slate-400">
                        {duration}s
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-100 text-base">
                        {cue.text_zh}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          {Math.round(cue.confidence * 100)}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center">
        <button onClick={onPrev} className="btn btn-secondary !px-5 !py-2.5">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Quay lại Bước 1
        </button>
        <button
          onClick={onNext}
          disabled={cues.length === 0}
          className="btn btn-primary !px-6 !py-3 text-base shadow-lg shadow-indigo-500/20"
        >
          Sang Bước 3: Dịch Thuật & Hiệu Đính
          <ArrowRight className="w-5 h-5 ml-1" />
        </button>
      </div>
    </div>
  );
};
