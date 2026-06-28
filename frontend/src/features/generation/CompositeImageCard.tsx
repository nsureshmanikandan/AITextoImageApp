import { useEffect, useRef, useState, useCallback } from 'react';
import { BannerExportModal } from './BannerExportModal';
import { exportGif } from './bannerAnimator';
import type { GeneratedImageEntry } from './BannerExportModal';

interface CompositeImageCardProps {
  imageUrl: string;
  logoDataUrl: string | null;
  logoFileName?: string | null;
  logoBgColor?: string;
  badgeText?: string;
  ctaText?: string;
  alt: string;
  seed?: number;
  formatLabel?: string;
  sourceFormatId?: string;
  allImages?: GeneratedImageEntry[]; // all generated images for this session
}

type Position = 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';

const LOGO_SIZE_RATIO    = 0.22;
const LOGO_PADDING_RATIO = 0.03;
const PANEL_INNER_PAD    = 0.015; // inner padding inside the bg panel

async function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

function drawRoundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

// Height of AI-generated CTA strip as fraction of image height (matches bannerAnimator ~11%)
const CTA_STRIP_RATIO = 0.13;

async function compositeImages(
  baseUrl: string,
  logoDataUrl: string,
  position: Position,
  bgColor: string,
  hasCta: boolean,
): Promise<string> {
  const [base, logo] = await Promise.all([loadImage(baseUrl), loadImage(logoDataUrl)]);

  const canvas = document.createElement('canvas');
  canvas.width  = base.naturalWidth;
  canvas.height = base.naturalHeight;
  const ctx = canvas.getContext('2d')!;

  // 1. Draw base image
  ctx.drawImage(base, 0, 0);

  // 2. Calculate sizes
  const logoW    = Math.round(canvas.width * LOGO_SIZE_RATIO);
  const logoH    = Math.round((logo.naturalHeight / logo.naturalWidth) * logoW);
  const outerPad = Math.round(canvas.width * LOGO_PADDING_RATIO);
  const innerPad = Math.round(canvas.width * PANEL_INNER_PAD);
  const panelW   = logoW + innerPad * 2;
  const panelH   = logoH + innerPad * 2;
  const radius   = Math.round(panelW * 0.06);

  // When the AI has rendered a CTA strip at the bottom, lift the logo panel above it
  const ctaOffset = hasCta ? Math.round(canvas.height * CTA_STRIP_RATIO) : 0;

  let panelX = 0;
  let panelY = 0;
  switch (position) {
    case 'bottom-left':  panelX = outerPad;                          panelY = canvas.height - panelH - outerPad - ctaOffset; break;
    case 'bottom-right': panelX = canvas.width - panelW - outerPad;  panelY = canvas.height - panelH - outerPad - ctaOffset; break;
    case 'top-left':     panelX = outerPad;                          panelY = outerPad; break;
    case 'top-right':    panelX = canvas.width - panelW - outerPad;  panelY = outerPad; break;
  }

  // 3. Draw coloured background panel with subtle drop shadow
  ctx.save();
  ctx.shadowColor   = 'rgba(0,0,0,0.30)';
  ctx.shadowBlur    = 14;
  ctx.shadowOffsetX = 0;
  ctx.shadowOffsetY = 4;
  ctx.fillStyle = bgColor;
  drawRoundRect(ctx, panelX, panelY, panelW, panelH, radius);
  ctx.fill();
  ctx.restore();

  // 4. Draw the actual logo centred inside the panel
  const logoX = panelX + innerPad;
  const logoY = panelY + innerPad;

  // Clip to rounded panel so logo never bleeds outside
  ctx.save();
  drawRoundRect(ctx, panelX, panelY, panelW, panelH, radius);
  ctx.clip();
  ctx.drawImage(logo, logoX, logoY, logoW, logoH);
  ctx.restore();

  return canvas.toDataURL('image/png');
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

function FilmIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="2" width="20" height="20" rx="2.18"/>
      <line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/>
      <line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/>
      <line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/>
      <line x1="17" y1="7" x2="22" y2="7"/>
    </svg>
  );
}

function LogoIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2"/>
      <path d="M3 9h18"/>
      <path d="M9 21V9"/>
    </svg>
  );
}

export function CompositeImageCard({ imageUrl, logoDataUrl, logoFileName, logoBgColor = '#ffffff', badgeText = '', ctaText = '', alt, seed, formatLabel, sourceFormatId, allImages = [] }: CompositeImageCardProps) {
  const [compositedUrl, setCompositedUrl] = useState<string | null>(null);
  const [compositing, setCompositing] = useState(false);
  const [position, setPosition] = useState<Position>('top-left');
  const [showControls, setShowControls] = useState(false);
  const [showBannerModal, setShowBannerModal] = useState(false);
  const [gifDownloading, setGifDownloading] = useState(false);
  const abortRef = useRef(false);

  // Format → export ad dimensions (matching AD_SIZES in bannerAnimator)
  const FORMAT_DIMS: Record<string, { width: number; height: number }> = {
    square:   { width: 1080, height: 1080 },
    facebook: { width: 1200, height: 628  },
    wide:     { width: 1280, height: 720  },
    portrait: { width: 1000, height: 1500 },
    story:    { width: 1080, height: 1920 },
  };

  const runComposite = useCallback(async (pos: Position) => {
    if (!logoDataUrl) return;
    abortRef.current = false;
    setCompositing(true);
    try {
      const result = await compositeImages(imageUrl, logoDataUrl, pos, logoBgColor, !!ctaText);
      if (!abortRef.current) setCompositedUrl(result);
    } catch {
      if (!abortRef.current) setCompositedUrl(null);
    } finally {
      if (!abortRef.current) setCompositing(false);
    }
  }, [imageUrl, logoDataUrl, logoBgColor, ctaText]);

  // Auto-composite when logo or image changes
  useEffect(() => {
    if (!logoDataUrl) {
      setCompositedUrl(null);
      return;
    }
    runComposite(position);
    return () => { abortRef.current = true; };
  }, [logoDataUrl, imageUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePositionChange = useCallback((pos: Position) => {
    setPosition(pos);
    runComposite(pos);
  }, [runComposite]);

  const handleDownload = useCallback(async () => {
    const size = (sourceFormatId ? FORMAT_DIMS[sourceFormatId] : undefined) ?? { width: 1080, height: 1080 };
    setGifDownloading(true);
    try {
      const blob = await exportGif({
        // Use original image as base so logo + text are drawn by the animator
        // with proper entrance animations (zoom, slide-in) instead of baked-static
        imageUrl,
        logoDataUrl,
        badgeText,
        ctaText,
        width: size.width,
        height: size.height,
        durationMs: 6000,
        fps: 12,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ai-banner${logoDataUrl ? '-with-logo' : ''}.gif`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('GIF export failed:', e);
    } finally {
      setGifDownloading(false);
    }
  }, [compositedUrl, imageUrl, logoDataUrl, sourceFormatId]); // eslint-disable-line react-hooks/exhaustive-deps

  const displaySrc = compositedUrl ?? imageUrl;

  const POSITIONS: { id: Position; label: string }[] = [
    { id: 'bottom-left',  label: 'BL' },
    { id: 'bottom-right', label: 'BR' },
    { id: 'top-left',     label: 'TL' },
    { id: 'top-right',    label: 'TR' },
  ];

  return (
    <div className="rounded-lg overflow-hidden border border-white/5 bg-surface-2 group relative">
      {/* Main image */}
      <div className="relative">
        <img
          src={displaySrc}
          alt={alt}
          className="w-full h-auto object-contain transition-transform duration-300 group-hover:scale-[1.02]"
          loading="lazy"
        />

        {/* Compositing spinner overlay */}
        {compositing && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-2">
              <svg className="animate-spin w-6 h-6 text-pink-400" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              <span className="text-xs text-pink-300 font-medium">Placing logo…</span>
            </div>
          </div>
        )}

        {/* Format label badge — always visible top-right */}
        {formatLabel && (
          <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-sm text-[10px] font-semibold text-slate-200 pointer-events-none">
            {formatLabel}
          </div>
        )}

        {/* Logo badge — shows when logo is composited */}
        {logoDataUrl && compositedUrl && !compositing && (
          <div
            className="absolute top-2 left-2 flex items-center gap-1 px-2 py-1 rounded-full bg-pink-600/80 backdrop-blur-sm text-white text-[10px] font-semibold cursor-pointer"
            onClick={() => setShowControls((v) => !v)}
            title="Logo composited — click to adjust position"
          >
            <LogoIcon />
            Logo applied
          </div>
        )}

        {/* Hover bar — format label + seed + export buttons */}
        <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-end justify-between gap-2">
          <div className="flex flex-col gap-0.5 shrink-0">
            {formatLabel && (
              <p className="text-[10px] font-semibold text-pink-300 uppercase tracking-wider">{formatLabel}</p>
            )}
            {seed !== undefined && (
              <p className="text-xs text-slate-300 font-mono">Seed: {seed}</p>
            )}
          </div>
          <div className="flex gap-1.5 ml-auto">
            <button
              onClick={() => setShowBannerModal(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-pink-600/80 hover:bg-pink-600 backdrop-blur-sm rounded-lg text-xs text-white font-medium transition-all cursor-pointer"
              aria-label="Export animated banner"
            >
              <FilmIcon />
              Animate
            </button>
            <button
              onClick={handleDownload}
              disabled={gifDownloading}
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg text-xs text-white font-medium transition-all cursor-pointer disabled:opacity-60 disabled:cursor-wait"
              aria-label="Download animated GIF"
            >
              {gifDownloading ? (
                <><svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>GIF…</>
              ) : (
                <><DownloadIcon />GIF</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Logo position controls — shown when badge clicked */}
      {logoDataUrl && showControls && (
        <div className="px-3 py-2.5 border-t border-white/5 bg-surface flex items-center gap-2 flex-wrap">
          <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Logo position:</span>
          <div className="flex gap-1">
            {POSITIONS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => handlePositionChange(id)}
                disabled={compositing}
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold transition-all cursor-pointer disabled:opacity-40 ${
                  position === id
                    ? 'bg-pink-600 text-white'
                    : 'bg-surface-3 text-slate-400 hover:text-slate-200'
                }`}
                aria-label={`Place logo ${id.replace('-', ' ')}`}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="ml-auto text-[10px] text-slate-600">
            {logoFileName ?? 'Logo'}
          </span>
        </div>
      )}

      {/* Animated banner export modal — use the already-composited image as base
          so logo, badge, and CTA are not drawn a second time by the animator */}
      {showBannerModal && (
        <BannerExportModal
          imageUrl={compositedUrl ?? imageUrl}
          logoDataUrl={null}
          logoFileName={null}
          badgeText=""
          ctaText=""
          sourceFormatId={sourceFormatId}
          allImages={allImages}
          onClose={() => setShowBannerModal(false)}
        />
      )}
    </div>
  );
}
