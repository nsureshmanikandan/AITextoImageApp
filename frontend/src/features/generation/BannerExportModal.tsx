import { useState, useEffect, useRef, useCallback } from 'react';
import {
  AD_SIZES,
  BannerConfig,
  drawFrame,
  exportGif,
  exportWebM,
  exportHtml5Banner,
} from './bannerAnimator';

/** One entry per generated image — formatId matches SOCIAL_FORMATS ids */
export interface GeneratedImageEntry {
  formatId: string;
  imageUrl: string;
}

interface BannerExportModalProps {
  imageUrl: string;
  logoDataUrl: string | null;
  logoFileName?: string | null;
  badgeText: string;
  ctaText: string;
  onClose: () => void;
  sourceFormatId?: string;
  /** All generated images from this session — used to switch preview when ad size changes */
  allImages?: GeneratedImageEntry[];
}

type ExportFormat = 'gif' | 'webm' | 'html5';

const FORMAT_OPTIONS: { id: ExportFormat; label: string; ext: string; desc: string; badge?: string }[] = [
  { id: 'webm',  label: 'WebM Video',     ext: '.webm', desc: 'Full HD quality — Facebook, LinkedIn, YouTube, Google Display', badge: 'Best Quality' },
  { id: 'html5', label: 'HTML5 Banner',   ext: '.html', desc: 'Crisp at any size — Google Display Network, rich media ad servers' },
  { id: 'gif',   label: 'Animated GIF',   ext: '.gif',  desc: 'Universal — email, web, ad networks (lower colour quality for photos)' },
];

const DURATION_OPTIONS = [3000, 5000, 8000, 10000, 15000];
const FPS_OPTIONS      = [12, 15, 24];

function XIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  );
}

async function loadImg(src: string): Promise<HTMLImageElement> {
  return new Promise((res, rej) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => res(img);
    img.onerror = rej;
    img.src = src;
  });
}

function bestSizeIdx(formatId?: string): number {
  if (!formatId) return 0;
  const map: Record<string, number> = {
    square:    0,  // Instagram Square
    facebook:  1,  // Facebook Feed
    landscape: 1,
    wide:      3,  // YouTube / Display
    portrait:  4,  // Pinterest Portrait
    story:     5,  // Instagram Stories
  };
  return map[formatId] ?? 0;
}

export function BannerExportModal({
  imageUrl, logoDataUrl, badgeText, ctaText, onClose, sourceFormatId, allImages = [],
}: BannerExportModalProps) {
  const [sizeIdx,    setSizeIdx]    = useState(() => bestSizeIdx(sourceFormatId));

  // Resolve which image URL to use: prefer the one generated for the selected ad size's genFormat
  const activeImageUrl = (() => {
    if (allImages.length === 0) return imageUrl;
    const genFmt = AD_SIZES[sizeIdx]?.genFormat;
    const match = allImages.find((e) => e.formatId === genFmt);
    return match?.imageUrl ?? imageUrl;
  })();
  const [format,     setFormat]     = useState<ExportFormat>('webm');
  const [durationMs, setDurationMs] = useState(5000);
  const [fps,        setFps]        = useState(15);
  const [exporting,  setExporting]  = useState(false);
  const [progress,   setProgress]   = useState(0);
  const [error,      setError]      = useState<string | null>(null);

  const previewRef   = useRef<HTMLCanvasElement>(null);
  const rafRef       = useRef<number>(0);
  const startTimeRef = useRef<number>(0);
  const baseImgRef   = useRef<HTMLImageElement | null>(null);
  const logoImgRef   = useRef<HTMLImageElement | null>(null);

  const size = AD_SIZES[sizeIdx];

  // ── Load images — reload whenever the active image changes (ad size switch) ──
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [base, logo] = await Promise.all([
        loadImg(activeImageUrl),
        logoDataUrl ? loadImg(logoDataUrl) : Promise.resolve(null),
      ]);
      if (!cancelled) {
        baseImgRef.current = base;
        logoImgRef.current = logo;
      }
    })();
    return () => { cancelled = true; };
  }, [activeImageUrl, logoDataUrl]);

  // ── Live preview animation ───────────────────────────────────────────────────
  useEffect(() => {
    const canvas = previewRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    startTimeRef.current = performance.now();

    const cfg: BannerConfig = {
      imageUrl: activeImageUrl, logoDataUrl, badgeText, ctaText,
      width: size.width, height: size.height,
      durationMs, fps,
    };

    function tick(now: number) {
      const elapsed = now - startTimeRef.current;
      const t = (elapsed % durationMs) / durationMs;
      if (baseImgRef.current) {
        drawFrame(ctx!, t, baseImgRef.current, logoImgRef.current, cfg);
      }
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [activeImageUrl, logoDataUrl, badgeText, ctaText, size, durationMs, fps]);

  // ── Export ──────────────────────────────────────────────────────────────────
  const handleExport = useCallback(async () => {
    setExporting(true);
    setProgress(0);
    setError(null);

    const cfg: BannerConfig = {
      imageUrl: activeImageUrl, logoDataUrl, badgeText, ctaText,
      width: size.width, height: size.height,
      durationMs, fps,
    };

    try {
      if (format === 'html5') {
        // Scale the composited imageUrl into the target ad size via canvas
        const canvas = document.createElement('canvas');
        canvas.width  = size.width;
        canvas.height = size.height;
        const ctx = canvas.getContext('2d')!;
        if (baseImgRef.current) {
          // Cover-fit the base image (which is already fully composited)
          const img = baseImgRef.current;
          const imgAR = img.naturalWidth / img.naturalHeight;
          const canAR = size.width / size.height;
          let dw: number, dh: number, dx: number, dy: number;
          if (imgAR > canAR) { dh = size.height; dw = dh * imgAR; dx = (size.width - dw) / 2; dy = 0; }
          else               { dw = size.width;  dh = dw / imgAR; dx = 0; dy = (size.height - dh) / 2; }
          ctx.drawImage(img, dx, dy, dw, dh);
        }
        const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
        const html = exportHtml5Banner(cfg, dataUrl, null);
        const blob = new Blob([html], { type: 'text/html' });
        triggerDownload(blob, `ad-banner-${size.width}x${size.height}.html`);
        setProgress(100);
      } else if (format === 'webm') {
        const blob = await exportWebM(cfg, setProgress);
        triggerDownload(blob, `ad-banner-${size.width}x${size.height}.webm`);
      } else {
        const blob = await exportGif(cfg, setProgress);
        triggerDownload(blob, `ad-banner-${size.width}x${size.height}.gif`);
      }
    } catch (e) {
      console.error('Export failed:', e);
      setError(`Export failed: ${(e as Error).message}`);
    } finally {
      setExporting(false);
    }
  }, [format, size, durationMs, fps, activeImageUrl, logoDataUrl, badgeText, ctaText]);

  // Scale preview to fit in modal — cap both width AND height so tall
  // portrait/Story formats (1080×1920) don't overflow the modal.
  const MAX_PREVIEW_W = 320;
  const MAX_PREVIEW_H = 380;
  const previewScale = Math.min(1, MAX_PREVIEW_W / size.width, MAX_PREVIEW_H / size.height);
  const previewW = Math.round(size.width  * previewScale);
  const previewH = Math.round(size.height * previewScale);

  // Whether the selected ad size has an exactly matching generated image
  const hasMatchingImage = allImages.length > 0 &&
    !!allImages.find(e => e.formatId === AD_SIZES[sizeIdx]?.genFormat);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="surface rounded-2xl w-full max-w-3xl max-h-[92vh] overflow-y-auto animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div>
            <h2 className="text-base font-bold text-slate-100">Export Animated Banner</h2>
            <p className="text-xs text-slate-500 mt-0.5">Configure size, format &amp; animation settings</p>
          </div>
          <button onClick={onClose} className="p-2 text-slate-500 hover:text-slate-200 rounded-lg hover:bg-white/5 transition-colors cursor-pointer">
            <XIcon />
          </button>
        </div>

        <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ── Left: Live Preview ── */}
          <div className="flex flex-col items-center gap-3">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider self-start">Live Preview</div>

            {/* Canvas preview — fixed container so portrait/landscape both fit */}
            <div
              className="rounded-lg overflow-hidden border border-white/10 bg-surface-2 flex items-center justify-center"
              style={{ width: MAX_PREVIEW_W, height: MAX_PREVIEW_H }}
            >
              <canvas
                ref={previewRef}
                width={size.width}
                height={size.height}
                style={{ width: previewW, height: previewH, display: 'block' }}
              />
            </div>

            <p className="text-[10px] text-slate-600 text-center">
              Live preview · {size.width}×{size.height}px
            </p>

            {/* Image match status */}
            {allImages.length > 0 && (
              hasMatchingImage
                ? <p className="text-[10px] text-green-400 font-medium text-center">✓ Exact {AD_SIZES[sizeIdx]?.genFormat} image used</p>
                : (
                  <div className="w-full rounded-lg bg-amber-500/10 border border-amber-500/25 px-3 py-2 space-y-1">
                    <p className="text-[11px] text-amber-300 font-semibold">
                      ⚠ No {AD_SIZES[sizeIdx]?.label.split(' (')[0]} image was generated
                    </p>
                    <p className="text-[10px] text-amber-400/70">
                      A fallback image is shown. For best quality, go back and select the <strong>{AD_SIZES[sizeIdx]?.genFormat}</strong> format chip before generating.
                    </p>
                  </div>
                )
            )}
          </div>

          {/* ── Right: Settings ── */}
          <div className="space-y-5">

            {/* Ad Size */}
            <div className="space-y-2">
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Ad Size</label>
              <div className="space-y-1.5">
                {AD_SIZES.map((s, i) => {
                  const hasImg = allImages.length > 0 && !!allImages.find(e => e.formatId === s.genFormat);
                  return (
                    <button
                      key={s.label}
                      onClick={() => setSizeIdx(i)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-all cursor-pointer flex items-center justify-between gap-2 ${
                        sizeIdx === i
                          ? 'bg-brand-600/20 text-brand-300 border border-brand-600/40'
                          : 'bg-surface-2 text-slate-400 border border-white/5 hover:border-white/15 hover:text-slate-200'
                      }`}
                    >
                      <span>{s.label}</span>
                      {allImages.length > 0 && (
                        hasImg
                          ? <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-600/20 text-green-400 font-semibold shrink-0">✓ Image ready</span>
                          : <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-700/60 text-slate-500 font-medium shrink-0">No image</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Export Format */}
            <div className="space-y-2">
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Export Format</label>
              <div className="space-y-1.5">
                {FORMAT_OPTIONS.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setFormat(f.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-all cursor-pointer ${
                      format === f.id
                        ? 'bg-brand-600/20 border border-brand-600/40'
                        : 'bg-surface-2 border border-white/5 hover:border-white/15'
                    }`}
                  >
                    <div className={`flex items-center gap-2 text-xs font-semibold ${format === f.id ? 'text-brand-300' : 'text-slate-300'}`}>
                      {f.label} <span className="font-mono font-normal text-slate-500">{f.ext}</span>
                      {f.badge && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-600/20 text-green-400 font-semibold">{f.badge}</span>}
                    </div>
                    <div className="text-[10px] text-slate-600 mt-0.5">{f.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Duration + FPS */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Duration</label>
                <div className="flex flex-wrap gap-1">
                  {DURATION_OPTIONS.map((d) => (
                    <button key={d} onClick={() => setDurationMs(d)}
                      className={`px-2 py-1 text-[10px] rounded font-semibold transition-all cursor-pointer ${
                        durationMs === d ? 'bg-brand-600 text-white' : 'bg-surface-3 text-slate-400 hover:text-slate-200'
                      }`}
                    >{d / 1000}s</button>
                  ))}
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">FPS</label>
                <div className="flex gap-1">
                  {FPS_OPTIONS.map((f) => (
                    <button key={f} onClick={() => setFps(f)}
                      className={`px-2.5 py-1 text-[10px] rounded font-semibold transition-all cursor-pointer ${
                        fps === f ? 'bg-brand-600 text-white' : 'bg-surface-3 text-slate-400 hover:text-slate-200'
                      }`}
                    >{f}</button>
                  ))}
                </div>
                <p className="text-[10px] text-slate-600">
                  ~{Math.round((durationMs / 1000) * fps)} frames total
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Export bar */}
        <div className="px-6 py-4 border-t border-white/5 flex items-center gap-4">
          {exporting && (
            <div className="flex-1 space-y-1">
              <div className="flex items-center justify-between text-[10px] text-slate-500">
                <span>{progress < 80 ? 'Rendering frames…' : 'Encoding…'}</span>
                <span>{progress}%</span>
              </div>
              <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-600 to-pink-500 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
          {error && <p className="flex-1 text-xs text-red-400">{error}</p>}
          {!exporting && !error && (
            <p className="flex-1 text-xs text-slate-600">
              {format === 'webm'
                ? 'WebM: HD quality video, renders in real-time. Best for social platforms.'
                : format === 'html5'
                ? 'HTML5: Crisp at any resolution, CSS Ken Burns animation, instant export.'
                : 'GIF: Lower colour quality for photos — use WebM for best results.'}
            </p>
          )}
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-brand-600 to-pink-600 text-white rounded-lg font-semibold text-sm transition-all hover:opacity-90 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {exporting ? (
              <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Exporting…</>
            ) : (
              <><DownloadIcon />Export {FORMAT_OPTIONS.find(f => f.id === format)?.label}</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
