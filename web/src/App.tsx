import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { StepVideo } from './components/StepVideo';
import { StepOcr } from './components/StepOcr';
import { StepTranslate } from './components/StepTranslate';
import { StepRender } from './components/StepRender';
import { LogTerminal } from './components/LogTerminal';
import { PipelineStatus, SubtitleCue, VideoInfo } from './types';
import { Film, ScanText, Languages, Volume2, CheckCircle2 } from 'lucide-react';

export const App: React.FC = () => {
  // Stepper state (1: Video, 2: OCR, 3: Translate, 4: Render)
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Video State
  const [videoPath, setVideoPath] = useState<string>('sample_test.mp4');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [region, setRegion] = useState<[number, number]>([0.60, 0.95]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Pipeline State
  const [status, setStatus] = useState<PipelineStatus>({
    step: 'idle',
    progress: 0,
    message: '',
    logs: [],
    video_path: null,
    work_dir: 'work',
    config: {},
  });

  // Cues data
  const [cues, setCues] = useState<SubtitleCue[]>([]);
  const [cuesVi, setCuesVi] = useState<SubtitleCue[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // Polling pipeline status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          const data: PipelineStatus = await res.json();
          setStatus(data);

          // Tự động tải kết quả cues khi hoàn tất OCR
          if (data.step === 'ocr_done' && cues.length === 0) {
            fetchCues();
          }
          // Tự động tải cues_vi khi hoàn tất Dịch
          if (data.step === 'translate_done' && cuesVi.length === 0) {
            fetchCuesVi();
          }
        }
      } catch (err) {
        // Backend có thể chưa chạy
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 1500);
    return () => clearInterval(interval);
  }, [cues.length, cuesVi.length]);

  // Lấy info video
  const fetchVideoInfo = async (path: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/video-info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: path }),
      });
      const data = await res.json();
      if (res.ok) {
        setVideoInfo(data);
      } else {
        alert(`Lỗi đọc video: ${data.error}`);
      }
    } catch (err: any) {
      alert(`Không kết nối được server: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Tạo ảnh preview
  const handleGeneratePreview = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/preview-region', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath, region }),
      });
      if (res.ok) {
        setPreviewUrl(`/api/preview-image?work_dir=work&t=${Date.now()}`);
      } else {
        const data = await res.json();
        alert(`Lỗi preview: ${data.error}`);
      }
    } catch (err: any) {
      alert(`Lỗi: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Chạy OCR
  const handleRunOcr = async (fps: number, minConf: number) => {
    setLoading(true);
    try {
      const res = await fetch('/api/run-ocr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: videoPath,
          region,
          fps,
          min_conf: minConf,
        }),
      });
      const data = await res.json();
      if (data.cues) {
        setCues(data.cues);
      }
    } catch (err: any) {
      alert(`Lỗi OCR: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchCues = async () => {
    try {
      const res = await fetch('/api/cues');
      if (res.ok) {
        const data = await res.json();
        setCues(data);
      }
    } catch (e) {}
  };

  const fetchCuesVi = async () => {
    try {
      const res = await fetch('/api/cues-vi');
      if (res.ok) {
        const data = await res.json();
        setCuesVi(data);
      }
    } catch (e) {}
  };

  // Chạy Dịch
  const handleRunTranslate = async (translator: string, model: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/run-translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ translator, model }),
      });
      const data = await res.json();
      if (data.cues_vi) {
        setCuesVi(data.cues_vi);
      }
    } catch (err: any) {
      alert(`Lỗi Dịch: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Lưu bản dịch đã chỉnh sửa
  const handleSaveCuesVi = async (updated: SubtitleCue[]) => {
    setLoading(true);
    try {
      const res = await fetch('/api/cues-vi', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cues: updated }),
      });
      if (res.ok) {
        alert('✓ Đã lưu bản dịch thành công!');
      }
    } catch (err: any) {
      alert(`Lỗi lưu: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Chạy Render
  const handleRunRender = async (params: any) => {
    setLoading(true);
    try {
      const res = await fetch('/api/run-render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...params,
          video_path: videoPath,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        alert(`Lỗi render: ${data.error}`);
      }
    } catch (err: any) {
      alert(`Lỗi: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Reset
  const handleReset = async () => {
    if (confirm('Bạn có chắc muốn đặt lại toàn bộ trạng thái không?')) {
      await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clear_files: false }),
      });
      setCues([]);
      setCuesVi([]);
      setCurrentStep(1);
    }
  };

  const steps = [
    { id: 1, name: '1. Video & Vùng Quét', icon: Film, done: !!videoInfo },
    { id: 2, name: '2. Quét Phụ Đề OCR', icon: ScanText, done: cues.length > 0 },
    { id: 3, name: '3. Dịch & Hiệu Đính', icon: Languages, done: cuesVi.length > 0 },
    { id: 4, name: '4. Thuyết Minh & Xuất', icon: Volume2, done: status.step === 'done' },
  ];

  return (
    <div className="min-h-screen pb-44 flex flex-col">
      <Header status={status} onReset={handleReset} />

      {/* Main Container */}
      <main className="max-w-6xl mx-auto w-full px-6 pt-8 flex-1">
        {/* Stepper Navigation */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {steps.map((step) => {
            const Icon = step.icon;
            const isActive = currentStep === step.id;
            return (
              <div
                key={step.id}
                onClick={() => setCurrentStep(step.id)}
                className={`step-item ${isActive ? 'active' : ''} ${step.done ? 'completed' : ''}`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : step.done
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {step.done ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>
                <div>
                  <span className={`text-xs font-semibold block ${isActive ? 'text-white' : 'text-slate-300'}`}>
                    {step.name}
                  </span>
                  <span className="text-[11px] text-slate-500">
                    {step.done ? 'Đã hoàn thành' : isActive ? 'Đang thực hiện' : 'Chưa chạy'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Current Step Content */}
        {currentStep === 1 && (
          <StepVideo
            videoPath={videoPath}
            setVideoPath={setVideoPath}
            videoInfo={videoInfo}
            onFetchInfo={fetchVideoInfo}
            region={region}
            setRegion={setRegion}
            previewUrl={previewUrl}
            onGeneratePreview={handleGeneratePreview}
            onNext={() => setCurrentStep(2)}
            loading={loading}
          />
        )}

        {currentStep === 2 && (
          <StepOcr
            cues={cues}
            status={status}
            onRunOcr={handleRunOcr}
            onNext={() => setCurrentStep(3)}
            onPrev={() => setCurrentStep(1)}
            loading={loading}
          />
        )}

        {currentStep === 3 && (
          <StepTranslate
            cuesVi={cuesVi}
            setCuesVi={setCuesVi}
            status={status}
            onRunTranslate={handleRunTranslate}
            onSaveCuesVi={handleSaveCuesVi}
            onNext={() => setCurrentStep(4)}
            onPrev={() => setCurrentStep(2)}
            loading={loading}
          />
        )}

        {currentStep === 4 && (
          <StepRender
            status={status}
            onRunRender={handleRunRender}
            onPrev={() => setCurrentStep(3)}
            loading={loading}
          />
        )}
      </main>

      {/* Persistent Terminal Log Drawer at Bottom */}
      <LogTerminal logs={status.logs} onClear={() => setStatus((p) => ({ ...p, logs: [] }))} />
    </div>
  );
};
