export interface OCRBox {
  box: number[][]; // [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
  text: string;
  conf: number;
}

export interface SubtitleCue {
  id: number;
  start: number; // seconds
  end: number;   // seconds
  text_zh: string;
  text_vi?: string;
  confidence: number;
  boxes?: OCRBox[];
  audio_path?: string;
  audio_duration?: number;
}

export interface VideoInfo {
  width: number;
  height: number;
  fps: number;
  duration: number;
  has_audio: boolean;
  video_codec: string;
  audio_codec?: string;
}

export interface PipelineStatus {
  step: 'idle' | 'preview' | 'ocr' | 'ocr_done' | 'translate' | 'translate_done' | 'render' | 'done' | 'error';
  progress: number;
  message: string;
  logs: Array<{ time: string; msg: string }>;
  video_path: string | null;
  work_dir: string;
  config: Record<string, any>;
}
