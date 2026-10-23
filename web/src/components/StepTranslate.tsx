import React, { useState } from 'react';
import { SubtitleCue, PipelineStatus } from '../types';
import { Languages, Save, ArrowRight, ArrowLeft, Bot, Sparkles, Check } from 'lucide-react';

interface StepTranslateProps {
  cuesVi: SubtitleCue[];
  setCuesVi: React.Dispatch<React.SetStateAction<SubtitleCue[]>>;
  status: PipelineStatus;
  onRunTranslate: (translator: string, model: string) => void;
  onSaveCuesVi: (updated: SubtitleCue[]) => void;
  onNext: () => void;
  onPrev: () => void;
  loading: boolean;
}

export const StepTranslate: React.FC<StepTranslateProps> = ({
  cuesVi,
  setCuesVi,
  status,
  onRunTranslate,
  onSaveCuesVi,
  onNext,
  onPrev,
  loading,
}) => {
  const [translator, setTranslator] = useState<'echo' | 'ollama' | 'gemini'>('echo');
  const [model, setModel] = useState<string>('qwen2.5:7b');
  const [hasChanges, setHasChanges] = useState<boolean>(false);

  const isTranslating = status.step === 'translate';

  const handleTextViChange = (idx: number, newText: string) => {
    setCuesVi((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], text_vi: newText };
      return copy;
    });
    setHasChanges(true);
  };

  const handleSave = () => {
    onSaveCuesVi(cuesVi);
    setHasChanges(false);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const ms = Math.floor((secs % 1) * 1000);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  return (
    <div className="space-y-6">
      {/* Translation Settings Panel */}
      <div className="glass-panel p-6">
        <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
          <Languages className="w-5 h-5 text-indigo-400" />
          Cấu Hình Công Cụ Dịch Thuật
        </h3>
        <p className="text-sm text-slate-400 mb-6">
          Dịch từ tiếng Trung sang tiếng Việt tự nhiên theo ngữ cảnh (Batch Translation với Sliding Window).
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Phương thức dịch</label>
            <select
              value={translator}
              onChange={(e) => {
                const val = e.target.value as any;
                setTranslator(val);
                if (val === 'ollama') setModel('qwen2.5:7b');
                else if (val === 'gemini') setModel('gemini-1.5-flash');
                else setModel('');
              }}
              disabled={isTranslating}
              className="select-input font-medium"
            >
              <option value="echo">Echo (Giữ nguyên text để test tốc độ)</option>
              <option value="ollama">Ollama (Chạy mô hình AI cục bộ trên máy)</option>
              <option value="gemini">Gemini API (Google Cloud AI)</option>
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Mô hình (Model Name)</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={isTranslating || translator === 'echo'}
              placeholder={translator === 'ollama' ? 'qwen2.5:7b' : 'gemini-1.5-flash'}
              className="input-text font-mono text-sm"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={() => onRunTranslate(translator, model)}
              disabled={isTranslating || loading}
              className="btn btn-primary w-full !py-2.5 shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2"
            >
              <Sparkles className={`w-4 h-4 ${isTranslating ? 'animate-spin' : ''}`} />
              {isTranslating ? 'Đang dịch thuật AI...' : (cuesVi.length > 0 ? 'Dịch Lại Toàn Bộ' : 'Bắt Đầu Dịch Thuật')}
            </button>
          </div>
        </div>

        {/* Translation Progress */}
        {isTranslating && (
          <div className="mt-4 p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30">
            <div className="flex justify-between text-xs mb-1.5 text-indigo-300">
              <span className="font-semibold flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                Đang dịch batch theo từng cụm câu...
              </span>
              <span className="font-mono font-bold text-cyan-400">{status.progress}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${status.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Bilingual Subtitle Editor */}
      <div className="glass-panel p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h4 className="text-base font-bold text-white flex items-center gap-2">
              Trình Soát Lỗi & Hiệu Đính Bản Dịch Song Ngữ
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-mono">
                {cuesVi.length} câu
              </span>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Bạn có thể nhấp chuột vào cột tiếng Việt để tự sửa đổi câu từ cho mượt mà trước khi tạo giọng đọc.
            </p>
          </div>

          <button
            onClick={handleSave}
            disabled={!hasChanges || loading}
            className={`btn ${hasChanges ? 'btn-primary shadow-lg shadow-indigo-500/30' : 'btn-secondary'} !py-2 !px-4 text-xs flex items-center gap-1.5`}
          >
            <Save className="w-3.5 h-3.5" />
            {hasChanges ? 'Lưu Thay Đổi (Có bản sửa)' : 'Đã Lưu Mới Nhất'}
          </button>
        </div>

        {cuesVi.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-white/10 rounded-xl bg-slate-900/30 text-slate-500">
            <Languages className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">Chưa có bản dịch tiếng Việt</p>
            <p className="text-xs mt-1">Bấm nút "Bắt Đầu Dịch Thuật" ở trên để dịch phụ đề</p>
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[480px] rounded-xl border border-white/10">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-slate-900/90 text-xs text-slate-400 uppercase sticky top-0 backdrop-blur-md">
                <tr>
                  <th className="py-3 px-4 w-12 text-center">#</th>
                  <th className="py-3 px-4 w-40">Thời gian</th>
                  <th className="py-3 px-4 w-5/12">Tiếng Trung Gốc</th>
                  <th className="py-3 px-4 w-6/12">Tiếng Việt (Có thể chỉnh sửa)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 bg-slate-950/40">
                {cuesVi.map((cue, idx) => (
                  <tr key={cue.id || idx} className="hover:bg-indigo-500/5 transition-colors">
                    <td className="py-3 px-4 text-center font-mono text-xs text-slate-500">
                      {idx + 1}
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-cyan-300">
                      {formatTime(cue.start)} <br />
                      <span className="text-slate-500">→ {formatTime(cue.end)}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-medium text-sm leading-relaxed">
                      {cue.text_zh}
                    </td>
                    <td className="py-2 px-3">
                      <textarea
                        rows={2}
                        value={cue.text_vi ?? cue.text_zh}
                        onChange={(e) => handleTextViChange(idx, e.target.value)}
                        placeholder="Nhập bản dịch tiếng Việt..."
                        className="textarea-input font-medium text-emerald-300 border-indigo-500/20 focus:border-emerald-400 bg-slate-900/80"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center">
        <button onClick={onPrev} className="btn btn-secondary !px-5 !py-2.5">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Quay lại Bước 2 (OCR)
        </button>
        <button
          onClick={onNext}
          disabled={cuesVi.length === 0}
          className="btn btn-primary !px-6 !py-3 text-base shadow-lg shadow-indigo-500/20"
        >
          Sang Bước 4: Thuyết Minh & Xuất Video
          <ArrowRight className="w-5 h-5 ml-1" />
        </button>
      </div>
    </div>
  );
};
