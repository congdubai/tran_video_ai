import React, { useState } from 'react';
import { PipelineStatus } from '../types';
import { Volume2, Sliders, CheckCircle, Download, ArrowLeft, Play, Sparkles, Film } from 'lucide-react';

interface StepRenderProps {
  status: PipelineStatus;
  onRunRender: (params: any) => void;
  onPrev: () => void;
  loading: boolean;
}

export const StepRender: React.FC<StepRenderProps> = ({
  status,
  onRunRender,
  onPrev,
  loading,
}) => {
  const [ttsType, setTtsType] = useState<'silent' | 'edge-tts' | 'kokoro'>('edge-tts');
  const [voice, setVoice] = useState<string>('vi-VN-HoaiMyNeural');
  const [keepVol, setKeepVol] = useState<number>(0.15);
  const [duck, setDuck] = useState<boolean>(true);
  const [maskSigma, setMaskSigma] = useState<number>(30);
  const [font, setFont] = useState<string>('Arial');
  const [fontSize, setFontSize] = useState<string>('');
  const [maxTempo, setMaxTempo] = useState<number>(1.35);
  const [outputPath, setOutputPath] = useState<string>('output.mp4');

  const isRendering = status.step === 'render';
  const isDone = status.step === 'done';

  const handleStartRender = () => {
    onRunRender({
      tts: ttsType,
      voice,
      keep_original: keepVol,
      duck,
      mask_sigma: maskSigma,
      font,
      font_size: fontSize ? parseInt(fontSize, 10) : null,
      max_tempo: maxTempo,
      output: outputPath,
    });
  };

  return (
    <div className="space-y-6">
      {/* Settings Grid */}
      <div className="glass-panel p-6">
        <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-indigo-400" />
          Cấu Hình Thuyết Minh (TTS) & Kết Xuất Video
        </h3>
        <p className="text-sm text-slate-400 mb-6">
          Tổng hợp giọng đọc tiếng Việt theo đúng mốc thời gian phụ đề, co giãn tốc độ mượt mà và làm mờ dòng chữ Trung gốc.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Column 1: Audio & Voice */}
          <div className="space-y-4 p-4 rounded-xl bg-slate-900/60 border border-white/5">
            <h4 className="text-sm font-semibold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
              <Volume2 className="w-4 h-4" /> 1. Âm Thanh & Giọng Thuyết Minh
            </h4>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Công cụ giọng đọc (TTS Engine)</label>
              <select
                value={ttsType}
                onChange={(e) => {
                  const val = e.target.value as any;
                  setTtsType(val);
                  if (val === 'edge-tts') setVoice('vi-VN-HoaiMyNeural');
                  else if (val === 'kokoro') setVoice('ngoc_huyen');
                }}
                disabled={isRendering}
                className="select-input font-medium"
              >
                <option value="edge-tts">Edge TTS (Microsoft AI Giọng Tự Nhiên - Rất mượt)</option>
                <option value="kokoro">Kokoro TTS (Local Voice AI chạy trên CPU/GPU)</option>
                <option value="silent">Silent (Không đọc - Chỉ làm mờ & gắn sub Việt)</option>
              </select>
            </div>

            {ttsType === 'edge-tts' && (
              <div>
                <label className="text-xs text-slate-400 block mb-1">Giọng đọc Microsoft</label>
                <select
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  disabled={isRendering}
                  className="select-input font-medium"
                >
                  <option value="vi-VN-HoaiMyNeural">Hoài My (Nữ miền Bắc, truyền cảm)</option>
                  <option value="vi-VN-NamMinhNeural">Nam Minh (Nam miền Bắc, ấm áp)</option>
                </select>
              </div>
            )}

            {ttsType === 'kokoro' && (
              <div>
                <label className="text-xs text-slate-400 block mb-1">Voice Kokoro</label>
                <input
                  type="text"
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  disabled={isRendering}
                  placeholder="ngoc_huyen / minh_quang"
                  className="input-text font-mono text-sm"
                />
              </div>
            )}

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300 font-medium">Âm lượng video gốc:</span>
                <span className="font-mono text-cyan-400 font-bold">{Math.round(keepVol * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="0.5"
                step="0.05"
                value={keepVol}
                disabled={isRendering}
                onChange={(e) => setKeepVol(parseFloat(e.target.value))}
                className="w-full accent-indigo-400 cursor-pointer"
              />
              <span className="text-[11px] text-slate-500">Giữ nhỏ tiếng nền gốc (15% tạo cảm giác phim tài liệu)</span>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <input
                type="checkbox"
                id="ducking"
                checked={duck}
                disabled={isRendering}
                onChange={(e) => setDuck(e.target.checked)}
                className="w-4 h-4 rounded accent-indigo-500 cursor-pointer"
              />
              <label htmlFor="ducking" className="text-xs text-slate-300 cursor-pointer select-none">
                <strong>Audio Ducking</strong> (Tự động hạ nhỏ tiếng gốc khi có giọng đọc)
              </label>
            </div>
          </div>

          {/* Column 2: Subtitle & Video render */}
          <div className="space-y-4 p-4 rounded-xl bg-slate-900/60 border border-white/5">
            <h4 className="text-sm font-semibold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
              <Film className="w-4 h-4" /> 2. Phụ Đề & Làm Mờ (Blur Box)
            </h4>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Font phụ đề ASS</label>
                <input
                  type="text"
                  value={font}
                  onChange={(e) => setFont(e.target.value)}
                  disabled={isRendering}
                  className="input-text font-mono text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Cỡ chữ (px)</label>
                <input
                  type="number"
                  placeholder="Tự động"
                  value={fontSize}
                  onChange={(e) => setFontSize(e.target.value)}
                  disabled={isRendering}
                  className="input-text font-mono text-sm"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300 font-medium">Độ mờ vùng che chữ gốc (Sigma):</span>
                <span className="font-mono text-cyan-400 font-bold">{maskSigma}px</span>
              </div>
              <input
                type="range"
                min="10"
                max="60"
                step="5"
                value={maskSigma}
                disabled={isRendering}
                onChange={(e) => setMaskSigma(parseInt(e.target.value, 10))}
                className="w-full accent-cyan-400 cursor-pointer"
              />
              <span className="text-[11px] text-slate-500">30px là mức che hoàn toàn chữ Trung mà viền vẫn êm</span>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Tên file video xuất ra</label>
              <input
                type="text"
                value={outputPath}
                onChange={(e) => setOutputPath(e.target.value)}
                disabled={isRendering}
                className="input-text font-mono text-sm"
              />
            </div>

            <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/20 text-xs text-emerald-300">
              ✓ Bộ mã hóa FFmpeg tích hợp NVENC / Libx264 đảm bảo chất lượng hình ảnh sắc nét.
            </div>
          </div>
        </div>

        {/* Big Start Render Button */}
        <div className="mt-6 pt-4 border-t border-white/5">
          <button
            onClick={handleStartRender}
            disabled={isRendering || loading}
            className="btn btn-primary w-full !py-4 text-base font-bold shadow-xl shadow-indigo-500/30 flex items-center justify-center gap-2"
          >
            <Sparkles className={`w-5 h-5 ${isRendering ? 'animate-spin' : ''}`} />
            {isRendering ? `Đang kết xuất video... (${status.progress}%)` : 'BẮT ĐẦU KẾT XUẤT VIDEO (START RENDER)'}
          </button>
        </div>

        {/* Progress Display */}
        {isRendering && (
          <div className="mt-5 p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/40">
            <div className="flex justify-between text-sm mb-2 text-indigo-200">
              <span className="font-semibold flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                Đang xử lý: Làm mờ sub cũ → Ghép track giọng đọc → Burn ASS sub mới
              </span>
              <span className="font-mono font-bold text-cyan-300">{status.progress}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 h-3 rounded-full transition-all duration-300"
                style={{ width: `${status.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Done & Video Player Preview */}
      {isDone && (
        <div className="glass-panel p-6 border-emerald-500/40 shadow-xl shadow-emerald-500/10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/40">
              <CheckCircle className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-lg font-bold text-white">Xuất Video Thành Công!</h4>
              <p className="text-xs text-slate-400 font-mono">File: {outputPath}</p>
            </div>
          </div>

          <div className="rounded-xl overflow-hidden bg-black/80 border border-white/10 mb-4 max-w-2xl mx-auto shadow-2xl">
            <video
              controls
              src={`/api/download-output?path=${encodeURIComponent(outputPath)}`}
              className="w-full max-h-[380px] object-contain mx-auto"
            />
          </div>

          <div className="flex justify-center gap-3">
            <a
              href={`/api/download-output?path=${encodeURIComponent(outputPath)}`}
              download
              className="btn btn-primary !px-6 !py-3 flex items-center gap-2 text-sm shadow-lg shadow-emerald-500/30"
            >
              <Download className="w-4 h-4" />
              Tải Xuống Video Thành Phẩm (.mp4)
            </a>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between items-center">
        <button onClick={onPrev} className="btn btn-secondary !px-5 !py-2.5">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Quay lại Bước 3 (Bản dịch)
        </button>
      </div>
    </div>
  );
};
