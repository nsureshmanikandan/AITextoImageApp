import { useState, useCallback, useEffect, KeyboardEvent } from 'react';
import { usePresets } from '@/hooks/usePresets';
import type { Preset } from '@/types';

const MAX_PROMPT_LENGTH = 2000;

// Social media format definitions — aspect ratios match export ad sizes exactly
// Generation uses Flux-compatible pixel counts; export modal rescales to industry standard px
const SOCIAL_FORMATS = [
  { id: 'square',   label: 'Square',          ratio: '1:1',    platform: 'Instagram · Facebook Square', w: 1024, h: 1024, exportPx: '1080×1080' },
  { id: 'facebook', label: 'Facebook/LinkedIn',ratio: '1.9:1',  platform: 'Facebook Feed · LinkedIn',    w: 1216, h: 640,  exportPx: '1200×628'  },
  { id: 'wide',     label: 'Wide',             ratio: '16:9',   platform: 'YouTube · Google Display',    w: 1280, h: 720,  exportPx: '1280×720'  },
  { id: 'portrait', label: 'Portrait',         ratio: '2:3',    platform: 'Pinterest',                   w: 832,  h: 1248, exportPx: '1000×1500' },
  { id: 'story',    label: 'Story',            ratio: '9:16',   platform: 'Instagram Stories · TikTok',  w: 720,  h: 1280, exportPx: '1080×1920' },
] as const;

type FormatId = (typeof SOCIAL_FORMATS)[number]['id'];

// All 5 formats selected by default
const DEFAULT_MULTI_FORMATS: FormatId[] = ['square', 'facebook', 'wide', 'portrait', 'story'];

interface PromptInputProps {
  onSubmit: (prompt: string, numVariations: number, presetId?: string, imageFormats?: string[]) => void;
  isLoading?: boolean;
  disabled?: boolean;
  externalPrompt?: string;
  onPromptChange?: (prompt: string) => void;
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" aria-hidden="true" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function SparkleIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v1m0 16v1M4.22 4.22l.7.7m12.16 12.16.7.7M3 12h1m16 0h1M4.22 19.78l.7-.7M18.36 5.64l.7-.7" />
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
}

export function PromptInput({ onSubmit, isLoading = false, disabled = false, externalPrompt, onPromptChange }: PromptInputProps) {
  const [prompt, setPrompt] = useState('');
  const [selectedFormats, setSelectedFormats] = useState<FormatId[]>([...DEFAULT_MULTI_FORMATS]);

  useEffect(() => {
    if (externalPrompt) {
      setPrompt(externalPrompt);
      setError(null);
    }
  }, [externalPrompt]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const { data: presets } = usePresets();

  const validate = useCallback((): boolean => {
    if (!prompt.trim()) {
      setError('Prompt cannot be empty.');
      return false;
    }
    if (prompt.length > MAX_PROMPT_LENGTH) {
      setError(`Prompt must be at most ${MAX_PROMPT_LENGTH} characters.`);
      return false;
    }
    setError(null);
    return true;
  }, [prompt]);

  const toggleFormat = useCallback((id: FormatId) => {
    setSelectedFormats((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]
    );
  }, []);

  const handleSubmit = useCallback(() => {
    if (!validate()) return;
    const formats = selectedFormats.length > 0 ? selectedFormats : undefined;
    const count = formats ? formats.length : 1;
    onSubmit(prompt.trim(), count, selectedPresetId || undefined, formats);
  }, [prompt, selectedPresetId, selectedFormats, validate, onSubmit]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  const charCount = prompt.length;
  const isOverLimit = charCount > MAX_PROMPT_LENGTH;
  const pct = Math.min(charCount / MAX_PROMPT_LENGTH, 1);
  const circumference = 2 * Math.PI * 10;

  return (
    <div className="space-y-4">
      {/* Textarea */}
      <div>
        <label htmlFor="prompt-input" className="block text-sm font-medium text-slate-300 mb-2">
          Describe your image
        </label>
        <textarea
          id="prompt-input"
          value={prompt}
          onChange={(e) => { setPrompt(e.target.value); onPromptChange?.(e.target.value); if (error) setError(null); }}
          onKeyDown={handleKeyDown}
          placeholder="A serene mountain landscape at sunset with vibrant purple and orange clouds..."
          rows={4}
          disabled={isLoading || disabled}
          aria-describedby="prompt-char-count prompt-error"
          aria-invalid={!!error || isOverLimit}
          className={`w-full px-4 py-3 bg-surface-2 border rounded-lg resize-none text-slate-200 placeholder-slate-600 text-sm leading-relaxed transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent ${
            error || isOverLimit ? 'border-red-500/60' : 'border-white/8 hover:border-white/15'
          }`}
        />

        {/* Char counter row */}
        <div className="flex items-center justify-between mt-2 gap-2">
          <div id="prompt-error" aria-live="polite">
            {error && (
              <p className="text-xs text-red-400">{error}</p>
            )}
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <span
              id="prompt-char-count"
              className={`text-xs tabular-nums ${isOverLimit ? 'text-red-400 font-semibold' : 'text-slate-600'}`}
            >
              {charCount}/{MAX_PROMPT_LENGTH}
            </span>
            {/* Circular progress */}
            <svg className="w-5 h-5 -rotate-90" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="10" fill="none" stroke="#1E1E2A" strokeWidth="3" />
              <circle
                cx="12" cy="12" r="10" fill="none"
                stroke={isOverLimit ? '#f87171' : pct > 0.85 ? '#f59e0b' : '#7C3AED'}
                strokeWidth="3"
                strokeDasharray={circumference}
                strokeDashoffset={circumference * (1 - pct)}
                strokeLinecap="round"
                style={{ transition: 'stroke-dashoffset 0.2s, stroke 0.2s' }}
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Options row */}
      <div className="flex flex-wrap gap-4 items-end">
        {/* Social Media Format selector — always visible */}
        <div className="space-y-2 flex-1 min-w-[280px]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              Social Media Sizes
            </span>
            <span className="text-[10px] text-slate-600">
              {selectedFormats.length === 0
                ? 'Select at least one size'
                : `${selectedFormats.length} size${selectedFormats.length > 1 ? 's' : ''} selected — ${selectedFormats.length} image${selectedFormats.length > 1 ? 's' : ''} will be generated`}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {SOCIAL_FORMATS.map((fmt) => {
              const active = selectedFormats.includes(fmt.id);
              return (
                <button
                  key={fmt.id}
                  type="button"
                  onClick={() => toggleFormat(fmt.id)}
                  disabled={isLoading || disabled}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-all cursor-pointer disabled:opacity-40 ${
                    active
                      ? 'bg-pink-600/15 border-pink-600/50 text-pink-200'
                      : 'bg-surface-2 border-white/8 text-slate-400 hover:border-white/20 hover:text-slate-200'
                  }`}
                >
                  {/* Aspect ratio visual */}
                  <span className={`inline-flex items-center justify-center border rounded shrink-0 ${
                    fmt.id === 'square'   ? 'w-5 h-5'   :
                    fmt.id === 'facebook' ? 'w-6 h-4'   :
                    fmt.id === 'portrait' ? 'w-4 h-6'   :
                    fmt.id === 'story'    ? 'w-3 h-5'   :
                                           'w-6 h-3.5'
                  } ${active ? 'border-pink-400 bg-pink-600/20' : 'border-slate-600 bg-white/5'}`} />
                  <span className="space-y-0">
                    <span className="block text-[11px] font-semibold leading-tight">
                      {fmt.label} <span className="font-mono font-normal opacity-60">{fmt.ratio}</span>
                    </span>
                    <span className="block text-[10px] opacity-60">{fmt.platform}</span>
                    <span className="block text-[9px] font-mono opacity-40">Export: {fmt.exportPx}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Preset selector */}
        {presets && presets.length > 0 && (
          <div className="flex-1 min-w-[180px]">
            <label htmlFor="preset-select" className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wider">
              Preset
            </label>
            <select
              id="preset-select"
              value={selectedPresetId}
              onChange={(e) => setSelectedPresetId(e.target.value)}
              disabled={isLoading || disabled}
              className="w-full px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer appearance-none"
            >
              <option value="">No preset</option>
              {presets.map((preset: Preset) => (
                <option key={preset.id} value={preset.id}>{preset.name}</option>
              ))}
            </select>
          </div>
        )}

        {/* Generate button */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isLoading || disabled || !prompt.trim() || isOverLimit}
          aria-label="Generate image"
          className="ml-auto px-6 py-2.5 bg-gradient-brand text-white rounded-lg font-semibold text-sm transition-all duration-150 cursor-pointer hover:opacity-90 hover:glow-violet focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-surface disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isLoading ? (
            <><SpinnerIcon /> Generating…</>
          ) : (
            <><SparkleIcon /> Generate</>
          )}
        </button>
      </div>

      <p className="text-xs text-slate-700">
        Tip: <kbd className="px-1 py-0.5 bg-surface-3 rounded text-slate-500 font-mono text-[10px]">Ctrl+Enter</kbd> to submit
      </p>
    </div>
  );
}
