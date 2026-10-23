import React, { useState, useEffect, useRef } from 'react';
import { Terminal, ChevronUp, ChevronDown, Trash2 } from 'lucide-react';

interface LogTerminalProps {
  logs: Array<{ time: string; msg: string }>;
  onClear: () => void;
}

export const LogTerminal: React.FC<LogTerminalProps> = ({ logs, onClear }) => {
  const [isOpen, setIsOpen] = useState<boolean>(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isOpen]);

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-[#090d16]/95 backdrop-blur-md border-t border-white/10 transition-all duration-300">
      {/* Header bar */}
      <div
        className="flex items-center justify-between px-6 py-2 cursor-pointer hover:bg-white/5 border-b border-white/5"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-slate-200">Nhật Ký Xử Lý (Server Logs)</span>
          <span className="text-[11px] px-2 py-0.2 rounded bg-slate-800 text-slate-400">
            {logs.length} dòng
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            title="Xoá logs"
            className="p-1 hover:text-rose-400 text-slate-500 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button className="text-slate-400">
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Terminal content */}
      {isOpen && (
        <div className="p-4 max-h-48 overflow-y-auto font-mono text-xs space-y-1 bg-black/60 selection:bg-indigo-500/30">
          {logs.length === 0 ? (
            <p className="text-slate-600 italic">Chưa có nhật ký hoạt động nào...</p>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="flex gap-2 leading-relaxed">
                <span className="text-slate-500 select-none">[{log.time}]</span>
                <span className={log.msg.includes('LỖI') || log.msg.includes('error') ? 'text-rose-400' : log.msg.includes('HOÀN TẤT') ? 'text-emerald-400' : 'text-slate-300'}>
                  {log.msg}
                </span>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
};
