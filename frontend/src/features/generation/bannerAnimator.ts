/**
 * bannerAnimator.ts
 *
 * Renders an animated ad banner onto a series of canvas frames.
 * Animation: Ken Burns zoom on the image + logo fade-in + badge bounce + CTA slide-up.
 *
 * Returns frames as ImageData arrays for GIF encoding, or drives a canvas
 * live for preview / MediaRecorder export.
 */

export interface BannerConfig {
  imageUrl: string;
  logoDataUrl: string | null;
  badgeText: string;
  ctaText: string;
  width: number;
  height: number;
  durationMs: number;   // total animation duration (loops)
  fps: number;          // frames per second
}

// Industry-standard ad export sizes.
// These match the same aspect ratios used at generation time so no content is lost.
export const AD_SIZES: { label: string; width: number; height: number; genFormat: string }[] = [
  { label: 'Instagram Square (1080×1080)',    width: 1080, height: 1080, genFormat: 'square'    },  // 1:1
  { label: 'Facebook Feed (1200×628)',        width: 1200, height: 628,  genFormat: 'facebook'  },  // ~1.9:1
  { label: 'LinkedIn Post (1200×627)',        width: 1200, height: 627,  genFormat: 'facebook'  },  // ~1.9:1
  { label: 'YouTube / Display (1280×720)',    width: 1280, height: 720,  genFormat: 'wide'      },  // 16:9
  { label: 'Pinterest Portrait (1000×1500)',  width: 1000, height: 1500, genFormat: 'portrait'  },  // 2:3
  { label: 'Instagram Stories (1080×1920)',   width: 1080, height: 1920, genFormat: 'story'     },  // 9:16
  { label: 'Google Display (300×250)',        width: 300,  height: 250,  genFormat: 'square'    },  // ~1.2:1
];

async function loadImg(src: string): Promise<HTMLImageElement> {
  return new Promise((res, rej) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => res(img);
    img.onerror = rej;
    img.src = src;
  });
}

function easeOut(t: number) { return 1 - Math.pow(1 - t, 3); }
function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }
function clamp(v: number, lo: number, hi: number) { return Math.min(Math.max(v, lo), hi); }

/** Draw one animation frame at time t (0..1) onto the given canvas context. */
export function drawFrame(
  ctx: CanvasRenderingContext2D,
  t: number,                        // 0 = start, 1 = end
  baseImg: HTMLImageElement,
  logoImg: HTMLImageElement | null,
  cfg: BannerConfig,
) {
  const { width: W, height: H, badgeText, ctaText } = cfg;
  ctx.clearRect(0, 0, W, H);

  // High-quality image scaling for crisp output
  ctx.imageSmoothingEnabled = true;
  (ctx as CanvasRenderingContext2D & { imageSmoothingQuality: string }).imageSmoothingQuality = 'high';

  // ── 1. Image — fade in + very subtle drift (image stays mostly still so text
  //    animations read clearly; heavy zoom would fight the text entrance effects)
  const fadeAlpha = clamp(t / 0.10, 0, 1);

  // Very gentle zoom 1.0 → 1.04 (just enough to feel alive, not distracting)
  const zoom   = lerp(1.0, 1.04, easeOut(t));
  // Subtle rightward drift so scene feels live
  const driftX = lerp(0, W * 0.012, easeOut(t));
  const driftY = lerp(0, H * 0.006, easeOut(t));

  const imgAR  = baseImg.naturalWidth / baseImg.naturalHeight;
  const canAR  = W / H;

  // ── Blurred background fill (letterbox/pillarbox) ──────────────────────────
  ctx.save();
  ctx.globalAlpha = fadeAlpha;
  ctx.filter = 'blur(28px) brightness(0.45) saturate(1.3)';
  let bgW: number, bgH: number;
  if (imgAR > canAR) { bgW = W * zoom * 1.2; bgH = bgW / imgAR; }
  else               { bgH = H * zoom * 1.2; bgW = bgH * imgAR; }
  ctx.drawImage(baseImg, (W - bgW) / 2 - driftX * 0.5, (H - bgH) / 2 - driftY * 0.5, bgW, bgH);
  ctx.filter = 'none';
  ctx.restore();

  // ── Contain-fit the real image ──────────────────────────────────────────────
  let drawW: number, drawH: number;
  if (imgAR > canAR) { drawW = W * zoom; drawH = drawW / imgAR; }
  else               { drawH = H * zoom; drawW = drawH * imgAR; }
  const dx = (W - drawW) / 2 - driftX;
  const dy = (H - drawH) / 2 - driftY;
  ctx.save();
  ctx.globalAlpha = fadeAlpha;
  ctx.drawImage(baseImg, dx, dy, drawW, drawH);
  ctx.restore();

  // ── 2. Badge — ZOOM IN from tiny with elastic overshoot (t=0.15..0.42) ──────
  if (badgeText) {
    const bt = clamp((t - 0.15) / 0.27, 0, 1);
    // Elastic spring: 0 → 1.25 → 0.95 → 1.0
    const spring = bt < 0.55 ? lerp(0, 1.25, easeOut(bt / 0.55))
                 : bt < 0.78 ? lerp(1.25, 0.95, easeOut((bt - 0.55) / 0.23))
                 :              lerp(0.95, 1.0,  easeOut((bt - 0.78) / 0.22));
    const badgeAlpha = clamp(bt / 0.25, 0, 1);
    // Gentle breathing pulse after settled
    const scale = bt >= 1 ? 1 + Math.sin(t * Math.PI * 4) * 0.012 : spring;

    if (badgeAlpha > 0) {
      const bR = Math.min(W, H) * 0.13;
      const bX = W * 0.76;
      const bY = H * 0.30;
      ctx.save();
      ctx.globalAlpha = badgeAlpha;
      ctx.translate(bX, bY);
      ctx.scale(scale, scale);

      // Outer glow ring
      ctx.beginPath();
      ctx.arc(0, 0, bR + 6, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(220,38,38,0.22)';
      ctx.fill();

      // Main circle
      ctx.beginPath();
      ctx.arc(0, 0, bR, 0, Math.PI * 2);
      ctx.fillStyle = '#DC2626';
      ctx.shadowColor = 'rgba(220,38,38,0.7)';
      ctx.shadowBlur = 22;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Wrap text into lines
      const words = badgeText.split(' ');
      const lineCount = words.length <= 4 ? 2 : 3;
      const perLine = Math.ceil(words.length / lineCount);
      const lines: string[] = [];
      for (let i = 0; i < lineCount; i++) {
        const chunk = words.slice(i * perLine, (i + 1) * perLine).join(' ');
        if (chunk) lines.push(chunk);
      }
      const fontSize = Math.max(10, Math.round(bR * 0.29));
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${fontSize}px Inter, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const lineH = fontSize * 1.28;
      lines.forEach((line, i) => ctx.fillText(line, 0, (i - (lines.length - 1) / 2) * lineH));
      ctx.restore();
    }
  }

  // ── 3. Logo — DROPS IN from above top-left, elastic settle (t=0.05..0.30) ───
  if (logoImg) {
    const lt = clamp((t - 0.05) / 0.25, 0, 1);
    const logoAlpha = clamp(lt / 0.35, 0, 1);
    // Drop from -logoH above final position, overshoot slightly, settle
    const dropT = lt < 0.65 ? easeOut(lt / 0.65) : lerp(1, 0.96, easeOut((lt - 0.65) / 0.35));
    if (logoAlpha > 0) {
      const pad   = Math.round(W * 0.03);
      const logoW = Math.round(W * 0.22);
      const logoH = Math.round((logoImg.naturalHeight / logoImg.naturalWidth) * logoW);
      const finalY = pad;
      const startY = -(logoH + pad);
      const lx = pad;
      const ly = lerp(startY, finalY, dropT);
      ctx.save();
      ctx.globalAlpha = logoAlpha;
      ctx.shadowColor = 'rgba(0,0,0,0.40)';
      ctx.shadowBlur  = 14;
      ctx.drawImage(logoImg, lx, ly, logoW, logoH);
      ctx.restore();
    }
  }

  // ── 4. CTA strip — SLIDES IN FROM LEFT (t=0.42..0.65) then holds ───────────
  if (ctaText) {
    const ct = clamp((t - 0.42) / 0.23, 0, 1);
    // Strip slides from fully off-left to final position with overshoot
    const slideProgress = ct < 0.72
      ? easeOut(ct / 0.72)
      : lerp(1, 0.97, easeOut((ct - 0.72) / 0.28));  // tiny retract to settle
    const ctaAlpha = clamp(ct / 0.20, 0, 1);
    const stripH   = Math.round(H * 0.11);
    const stripY   = H - stripH;
    const stripX   = lerp(-W, 0, slideProgress);  // ← slides in from left

    if (ctaAlpha > 0) {
      ctx.save();
      ctx.globalAlpha = ctaAlpha;

      // Clip so strip never bleeds outside canvas
      ctx.beginPath();
      ctx.rect(0, stripY, W, stripH + 4);
      ctx.clip();

      // Gradient background (slides with text)
      const grad = ctx.createLinearGradient(stripX, 0, stripX + W, 0);
      grad.addColorStop(0,    'rgba(109,40,217,0.95)');  // violet-700
      grad.addColorStop(0.55, 'rgba(20,10,40,0.95)');
      grad.addColorStop(1,    'rgba(10,5,20,0.95)');
      ctx.fillStyle = grad;
      ctx.fillRect(stripX, stripY, W + Math.abs(stripX), stripH + 4);

      // Accent line at leading (left) edge of the sliding strip
      ctx.fillStyle = 'rgba(216,180,254,0.9)';  // purple-300
      ctx.fillRect(stripX + W - 3, stripY, 3, stripH);

      // Arrow/chevron indicator → showing motion direction
      const arrowX = stripX + 14;
      const arrowY = stripY + stripH / 2;
      ctx.strokeStyle = 'rgba(216,180,254,0.85)';
      ctx.lineWidth = Math.max(2, Math.round(stripH * 0.12));
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      const aw = Math.round(stripH * 0.22);
      ctx.beginPath();
      ctx.moveTo(arrowX, arrowY - aw * 0.6);
      ctx.lineTo(arrowX + aw, arrowY);
      ctx.lineTo(arrowX, arrowY + aw * 0.6);
      ctx.stroke();

      // CTA text — also slides with strip
      const fontSize = Math.max(10, Math.round(stripH * 0.40));
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${fontSize}px Inter, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.shadowColor = 'rgba(167,139,250,0.6)';
      ctx.shadowBlur = 10;
      ctx.fillText(ctaText, stripX + W / 2, stripY + stripH / 2, W * 0.80);
      ctx.shadowBlur = 0;
      ctx.restore();
    }
  }
}

/** Render all frames and return as an array of canvas ImageData (for GIF encoding). */
export async function renderFrames(
  cfg: BannerConfig,
  onProgress?: (pct: number) => void,
): Promise<{ frames: ImageData[]; canvas: HTMLCanvasElement }> {
  const canvas = document.createElement('canvas');
  canvas.width  = cfg.width;
  canvas.height = cfg.height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true })!;

  const [baseImg, logoImg] = await Promise.all([
    loadImg(cfg.imageUrl),
    cfg.logoDataUrl ? loadImg(cfg.logoDataUrl) : Promise.resolve(null),
  ]);

  const totalFrames = Math.round((cfg.durationMs / 1000) * cfg.fps);
  const frames: ImageData[] = [];

  for (let i = 0; i < totalFrames; i++) {
    const t = i / (totalFrames - 1);
    drawFrame(ctx, t, baseImg, logoImg, cfg);
    frames.push(ctx.getImageData(0, 0, cfg.width, cfg.height));
    onProgress?.(Math.round((i / totalFrames) * 100));
    // Yield to browser every 5 frames so UI stays responsive
    if (i % 5 === 0) await new Promise((r) => setTimeout(r, 0));
  }

  onProgress?.(100);
  return { frames, canvas };
}

/** Export as WebM video using MediaRecorder. Returns a Blob. */
export async function exportWebM(
  cfg: BannerConfig,
  onProgress?: (pct: number) => void,
): Promise<Blob> {
  const canvas = document.createElement('canvas');
  canvas.width  = cfg.width;
  canvas.height = cfg.height;
  const ctx = canvas.getContext('2d')!;

  const [baseImg, logoImg] = await Promise.all([
    loadImg(cfg.imageUrl),
    cfg.logoDataUrl ? loadImg(cfg.logoDataUrl) : Promise.resolve(null),
  ]);

  return new Promise((resolve, reject) => {
    const stream   = (canvas as any).captureStream(cfg.fps) as MediaStream;
    // Try VP9 first (best quality), fall back to VP8 or default
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : MediaRecorder.isTypeSupported('video/webm;codecs=vp8')
      ? 'video/webm;codecs=vp8'
      : 'video/webm';
    const recorder = new MediaRecorder(stream, {
      mimeType,
      videoBitsPerSecond: 8_000_000, // 8 Mbps for HD quality
    });
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
    recorder.onstop = () => resolve(new Blob(chunks, { type: 'video/webm' }));
    recorder.onerror = (e) => reject(e);
    recorder.start();

    const totalFrames = Math.round((cfg.durationMs / 1000) * cfg.fps);
    let frame = 0;
    const interval = setInterval(() => {
      if (frame >= totalFrames) {
        clearInterval(interval);
        recorder.stop();
        return;
      }
      const t = frame / (totalFrames - 1);
      drawFrame(ctx, t, baseImg, logoImg, cfg);
      onProgress?.(Math.round((frame / totalFrames) * 100));
      frame++;
    }, 1000 / cfg.fps);
  });
}

// ── Pure-JS GIF encoder (no web worker, works in Vite ESM) ──────────────────
// Adaptive palette via median-cut quantization — photorealistic quality.
function buildAdaptivePalette(frames: ImageData[], maxColors = 256): Uint8Array {
  // Sample pixels from all frames (skip every N pixels for speed)
  const totalPx = frames.reduce((s, f) => s + f.width * f.height, 0);
  const step = Math.max(1, Math.floor(totalPx / 12000)); // sample ~12k pixels
  const samples: number[][] = [];
  for (const frame of frames) {
    const d = frame.data;
    for (let i = 0; i < d.length; i += 4 * step) {
      samples.push([d[i], d[i + 1], d[i + 2]]);
    }
  }

  // Median-cut: split the largest-range axis recursively until we have maxColors buckets
  type Bucket = number[][];
  let buckets: Bucket[] = [samples];

  while (buckets.length < maxColors) {
    // Find the bucket with the largest color range across any axis
    let bestBucketIdx = 0;
    let bestRange = -1;
    for (let bi = 0; bi < buckets.length; bi++) {
      const bk = buckets[bi];
      if (bk.length < 2) continue;
      for (let axis = 0; axis < 3; axis++) {
        let mn = 255, mx = 0;
        for (const px of bk) { if (px[axis] < mn) mn = px[axis]; if (px[axis] > mx) mx = px[axis]; }
        if (mx - mn > bestRange) { bestRange = mx - mn; bestBucketIdx = bi; }
      }
    }
    if (bestRange < 1) break;

    const bk = buckets[bestBucketIdx];
    // Find which axis has the largest range in this bucket
    let splitAxis = 0, splitRange = -1;
    for (let axis = 0; axis < 3; axis++) {
      let mn = 255, mx = 0;
      for (const px of bk) { if (px[axis] < mn) mn = px[axis]; if (px[axis] > mx) mx = px[axis]; }
      if (mx - mn > splitRange) { splitRange = mx - mn; splitAxis = axis; }
    }
    // Sort by that axis and split at median
    bk.sort((a, b) => a[splitAxis] - b[splitAxis]);
    const mid = Math.floor(bk.length / 2);
    buckets.splice(bestBucketIdx, 1, bk.slice(0, mid), bk.slice(mid));
  }

  // Average each bucket → one palette color
  const palette = new Uint8Array(maxColors * 3);
  for (let bi = 0; bi < maxColors; bi++) {
    const bk = buckets[bi] ?? [];
    if (bk.length === 0) continue;
    let r = 0, g = 0, b = 0;
    for (const px of bk) { r += px[0]; g += px[1]; b += px[2]; }
    palette[bi * 3]     = Math.round(r / bk.length);
    palette[bi * 3 + 1] = Math.round(g / bk.length);
    palette[bi * 3 + 2] = Math.round(b / bk.length);
  }
  return palette;
}

function encodeGif(frames: ImageData[], delayCs: number, W: number, H: number): Uint8Array {
  const paletteSize = 256;

  // Build adaptive palette from all frames for best photo quality
  const palette = buildAdaptivePalette(frames, paletteSize);

  // Fast nearest-color lookup with a small cache
  const colorCache = new Map<number, number>();
  function nearestIdx(r: number, g: number, b: number): number {
    const key = (r >> 2) << 16 | (g >> 2) << 8 | (b >> 2); // quantize key for cache hits
    const cached = colorCache.get(key);
    if (cached !== undefined) return cached;
    let best = 0, bestDist = Infinity;
    for (let i = 0; i < paletteSize; i++) {
      const dr = r - palette[i * 3];
      const dg = g - palette[i * 3 + 1];
      const db = b - palette[i * 3 + 2];
      // Weight green more (human eye is more sensitive)
      const dist = dr * dr * 0.299 + dg * dg * 0.587 + db * db * 0.114;
      if (dist < bestDist) { bestDist = dist; best = i; }
    }
    colorCache.set(key, best);
    return best;
  }

  // LZW encoder
  function lzwEncode(indices: Uint8Array, minCode: number): Uint8Array {
    const out: number[] = [];
    const clearCode = 1 << minCode;
    const eofCode   = clearCode + 1;
    let codeSize = minCode + 1;
    let nextCode = eofCode + 1;
    type Table = Map<string, number>;
    let table: Table = new Map();
    const resetTable = () => { table = new Map(); codeSize = minCode + 1; nextCode = eofCode + 1; };

    let buf = 0, bufBits = 0;
    const writeBits = (code: number, bits: number) => {
      buf |= code << bufBits; bufBits += bits;
      while (bufBits >= 8) { out.push(buf & 0xff); buf >>= 8; bufBits -= 8; }
    };

    resetTable();
    writeBits(clearCode, codeSize);
    let str = '' + indices[0];
    for (let i = 1; i < indices.length; i++) {
      const c = '' + indices[i];
      const sc = str + ',' + c;
      if (table.has(sc)) { str = sc; }
      else {
        writeBits(table.get(str) ?? parseInt(str), codeSize);
        table.set(sc, nextCode++);
        if (nextCode > (1 << codeSize) && codeSize < 12) codeSize++;
        if (nextCode > 4095) { writeBits(clearCode, codeSize); resetTable(); }
        str = c;
      }
    }
    writeBits(table.get(str) ?? parseInt(str), codeSize);
    writeBits(eofCode, codeSize);
    if (bufBits > 0) out.push(buf & 0xff);
    return new Uint8Array(out);
  }

  // Write GIF bytes
  const parts: Uint8Array[] = [];
  const put = (a: number[]) => parts.push(new Uint8Array(a));
  const putStr = (s: string) => put([...s].map(c => c.charCodeAt(0)));
  const u16 = (n: number) => [n & 0xff, (n >> 8) & 0xff];

  // Header + Logical Screen Descriptor
  putStr('GIF89a');
  put([...u16(W), ...u16(H), 0xf7, 0, 0]); // 0xf7 = global CT, 256 colours
  parts.push(palette);
  put([0]); // background colour index
  put([0]); // pixel aspect ratio

  // Netscape loop extension (loop forever)
  put([0x21, 0xff, 0x0b]);
  putStr('NETSCAPE2.0');
  put([3, 1, 0, 0, 0]);

  const minCodeSize = 8;
  for (let fi = 0; fi < frames.length; fi++) {
    const frame = frames[fi];
    const pixels = frame.data;
    const indices = new Uint8Array(W * H);
    for (let i = 0; i < W * H; i++) {
      indices[i] = nearestIdx(pixels[i * 4], pixels[i * 4 + 1], pixels[i * 4 + 2]);
    }

    // Graphic Control Extension
    put([0x21, 0xf9, 4, 0, ...u16(delayCs), 0, 0]);
    // Image Descriptor
    put([0x2c, ...u16(0), ...u16(0), ...u16(W), ...u16(H), 0]);
    // Image Data
    put([minCodeSize]);
    const lzw = lzwEncode(indices, minCodeSize);
    for (let i = 0; i < lzw.length; i += 255) {
      const chunk = lzw.slice(i, i + 255);
      put([chunk.length]);
      parts.push(chunk);
    }
    put([0]); // block terminator
  }
  put([0x3b]); // GIF trailer

  const total = parts.reduce((s, p) => s + p.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const p of parts) { out.set(p, offset); offset += p.length; }
  return out;
}

/** Export animated GIF using pure-JS encoder (no web worker required).
 *  GIF is capped at 540px on the longest side — 256-color limit means smaller
 *  dimensions look better (less banding) and encode/download much faster. */
export async function exportGif(
  cfg: BannerConfig,
  onProgress?: (pct: number) => void,
): Promise<Blob> {
  // Scale down for GIF — large dimensions + 256 colors = visible banding
  const GIF_MAX_PX = 540;
  const scale = Math.min(1, GIF_MAX_PX / Math.max(cfg.width, cfg.height));
  const gifW = Math.round(cfg.width  * scale);
  const gifH = Math.round(cfg.height * scale);

  const gifCfg: BannerConfig = { ...cfg, width: gifW, height: gifH, fps: Math.min(cfg.fps, 12) };
  const { frames } = await renderFrames(gifCfg, (p) => onProgress?.(Math.round(p * 0.70)));

  onProgress?.(72);
  // Build adaptive palette — most expensive step, yield first
  await new Promise((r) => setTimeout(r, 0));

  // GIF delay is in centiseconds
  const delayCs = Math.round(100 / gifCfg.fps);
  onProgress?.(80);
  await new Promise((r) => setTimeout(r, 0));
  const gifData = encodeGif(frames, delayCs, gifW, gifH);
  onProgress?.(100);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return new Blob([gifData.buffer as any], { type: 'image/gif' });
}

/** Export self-contained HTML5 animated banner (CSS keyframe Ken Burns zoom).
 *  The imageDataUrl is the fully composited image (logo + AI content already baked in),
 *  so no overlay elements are re-drawn here — clean single-pass animation. */
export function exportHtml5Banner(
  cfg: BannerConfig,
  imageDataUrl: string,
  _logoDataUrl: string | null,
): string {
  const { width: W, height: H } = cfg;
  const aspect = `${W}/${H}`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ad Banner ${W}x${H}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:100%;height:100%;background:#000;display:flex;align-items:center;justify-content:center;}
.outer{
  aspect-ratio:${aspect};
  width:min(100vw, calc(100vh * ${W} / ${H}));
  max-width:${W}px;
  position:relative;
  overflow:hidden;
}
.bg{
  position:absolute;inset:-10%;
  background:url("${imageDataUrl}") center/cover no-repeat;
  filter:blur(20px) brightness(0.5) saturate(1.3);
  transform-origin:center center;
}
.base{
  position:absolute;inset:0;
  background:url("${imageDataUrl}") center/contain no-repeat;
  animation:kenburns ${cfg.durationMs}ms ease-in-out infinite alternate;
  transform-origin:center center;
}
@keyframes kenburns{
  0%  {transform:scale(1)   translate(0,0);}
  50% {transform:scale(1.06) translate(-1%,0.5%);}
  100%{transform:scale(1.08) translate(0.5%,-0.5%);}
}
</style>
</head>
<body>
<div class="outer">
  <div class="bg"></div>
  <div class="base"></div>
</div>
</body>
</html>`;
}
