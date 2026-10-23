import React from 'react';
import { Sparkles, RefreshCw, Film, Volume2 } from 'lucide-react';
import { PipelineStatus } from '../types';

interface HeaderProps {
  status: PipelineStatus;
  onReset: () => void;
}

export const Header: React.FC<HeaderProps> = ({ status, onReset }) => {
  const getStatusBadge = () => {
    switch (status.step) {
      case 'ocr':
      case 'translate':
      case 'render':
        return (
          <span className="flex items-center gap-2 px-3 py-1 text-xs font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
            Đang xử lý ({status.progress}%)
          </span>
        );
      case 'done':
        return (
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            ✓ Hoàn tất xuất sắc
          </span>
        );
      case 'error':
        return (
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40">
            ✕ Có lỗi xảy ra
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-slate-500/20 text-slate-300 border border-slate-500/30">
            Sẵn sàng
          </span>
        );
    }
  };

  return (
    <header className="border-b border-white/10 bg-[#0f172a]/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Sub-to-Dub Studio <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 font-mono">v1.0 AI</span>
              </h1>
            </div>
            <p className="text-xs text-slate-400">
              OCR phụ đề Trung in cứng → Dịch chuẩn Việt → Làm mờ mượt mà → Lồng tiếng AI thuyết minh
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {getStatusBadge()}
          <button
            onClick={onReset}
            title="Reset trạng thái"
            className="btn btn-secondary !py-2 !px-3 text-xs flex items-center gap-1.5 hover:border-slate-500"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Làm mới
          </button>
        </div>
      </div>
    </header>
  );
};
