import { useState, useRef, useCallback } from 'react';
import { suggestOverlayText } from '@/api/overlayApi';

export interface BrandOverlayConfig {
  enabled: boolean;
  companyName: string;
  logoDataUrl: string | null;
  logoFileName: string | null;
  logoBgColor: string;
  badgeText: string;
  ctaText: string;
  subjectDesc: string; // e.g. "adult woman", "elderly man"
}

export const EMPTY_OVERLAY: BrandOverlayConfig = {
  enabled: false,
  companyName: '',
  logoDataUrl: null,
  logoFileName: null,
  logoBgColor: '#ffffff',
  badgeText: '',
  ctaText: '',
  subjectDesc: '',
};

const SUBJECT_CHIPS = [
  { id: 'adult-woman',   label: 'Adult Woman',   icon: '👩', desc: 'clearly defined adult woman, South Asian appearance' },
  { id: 'adult-man',     label: 'Adult Man',     icon: '👨', desc: 'clearly defined adult man' },
  { id: 'elderly-woman', label: 'Elderly Woman', icon: '👵', desc: 'clearly defined elderly woman, 60s-70s' },
  { id: 'elderly-man',   label: 'Elderly Man',   icon: '👴', desc: 'clearly defined elderly man, 60s-70s' },
  { id: 'couple',        label: 'Couple',        icon: '👫', desc: 'clearly defined man and woman couple' },
  { id: 'doctor',        label: 'Doctor',        icon: '🩺', desc: 'clearly defined doctor in white coat' },
] as const;

interface BrandOverlayPanelProps {
  config: BrandOverlayConfig;
  onChange: (config: BrandOverlayConfig) => void;
  promptContext?: string;
}

// ── icons ──────────────────────────────────────────────────────────────────────
function UploadIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  );
}

function SparkleIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v1m0 16v1M4.22 4.22l.7.7m12.16 12.16.7.7M3 12h1m16 0h1M4.22 19.78l.7-.7M18.36 5.64l.7-.7"/>
      <circle cx="12" cy="12" r="4"/>
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
      <path d="M10 11v6M14 11v6"/>
    </svg>
  );
}

// ── field row with AI suggest ──────────────────────────────────────────────────
function OverlayField({
  label,
  value,
  onChange,
  placeholder,
  field,
  company,
  promptContext,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  field: 'badge' | 'cta';
  company: string;
  promptContext?: string;
  hint?: string;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSuggest = useCallback(async () => {
    if (!company.trim()) {
      setError('Enter a company name first');
      setTimeout(() => setError(null), 3000);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const suggestion = await suggestOverlayText({ company, field, promptContext });
      onChange(suggestion);
    } catch (e) {
      setError('Suggestion failed — try again');
      setTimeout(() => setError(null), 3000);
    } finally {
      setLoading(false);
    }
  }, [company, field, promptContext, onChange]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{label}</label>
        <button
          type="button"
          onClick={handleSuggest}
          disabled={loading}
          className="flex items-center gap-1 text-[10px] text-brand-400 hover:text-brand-300 disabled:opacity-50 cursor-pointer transition-colors duration-150 font-medium"
          aria-label={`AI suggest ${label}`}
        >
          {loading ? <SpinnerIcon /> : <SparkleIcon />}
          {loading ? 'Suggesting…' : 'AI Suggest'}
        </button>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 bg-surface-3 border border-white/8 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all duration-150"
      />
      {hint && !error && <p className="text-[10px] text-slate-600">{hint}</p>}
      {error && <p className="text-[10px] text-red-400">{error}</p>}
    </div>
  );
}

// ── main panel ─────────────────────────────────────────────────────────────────
export function BrandOverlayPanel({ config, onChange, promptContext }: BrandOverlayPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const update = useCallback(
    (partial: Partial<BrandOverlayConfig>) => onChange({ ...config, ...partial }),
    [config, onChange]
  );

  const handleLogoUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      update({ logoDataUrl: reader.result as string, logoFileName: file.name });
    };
    reader.readAsDataURL(file);
    // reset input so same file can be re-selected
    e.target.value = '';
  }, [update]);

  const clearLogo = useCallback(() => {
    update({ logoDataUrl: null, logoFileName: null });
  }, [update]);

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Row 1 — Company name + Logo upload */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

        {/* Company name */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Company / Brand Name
          </label>
          <input
            type="text"
            value={config.companyName}
            onChange={(e) => update({ companyName: e.target.value })}
            placeholder="e.g. MRC Global, Nike, BP…"
            className="w-full px-3 py-2 bg-surface-3 border border-white/8 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all duration-150"
          />
          <p className="text-[10px] text-slate-600">Used by AI Suggest to tailor the copy</p>
        </div>

        {/* Logo upload */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Logo Upload <span className="text-slate-600 normal-case font-normal">(PNG / SVG / JPG)</span>
          </label>

          {config.logoDataUrl ? (
            /* Logo preview */
            <div className="flex items-center gap-3 px-3 py-2 bg-surface-3 border border-white/8 rounded-lg">
              <img
                src={config.logoDataUrl}
                alt="Brand logo preview"
                className="h-8 w-auto max-w-[80px] object-contain rounded"
              />
              <div className="min-w-0 flex-1">
                <p className="text-xs text-slate-300 truncate">{config.logoFileName}</p>
                <p className="text-[10px] text-slate-600">Logo uploaded</p>
              </div>
              <button
                type="button"
                onClick={clearLogo}
                className="shrink-0 p-1 text-slate-500 hover:text-red-400 rounded transition-colors cursor-pointer"
                aria-label="Remove logo"
              >
                <TrashIcon />
              </button>
            </div>
          ) : (
            /* Upload trigger */
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-surface-3 border border-dashed border-white/15 hover:border-brand-500/40 hover:bg-surface-3/80 rounded-lg text-sm text-slate-500 hover:text-slate-300 transition-all duration-150 cursor-pointer group"
            >
              <UploadIcon />
              <span className="text-xs">Click to upload logo</span>
            </button>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/svg+xml,image/jpeg,image/webp"
            onChange={handleLogoUpload}
            className="hidden"
            aria-label="Upload brand logo"
          />
          <p className="text-[10px] text-slate-600">
            Logo is composited directly onto the generated image via canvas — pixel-perfect, no blank boxes, no AI hallucination
          </p>
        </div>
      </div>

      {/* Subject / Person selector */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Subject / Person in Image
          </label>
          {config.subjectDesc && (
            <button
              type="button"
              onClick={() => update({ subjectDesc: '' })}
              className="text-[10px] text-slate-500 hover:text-slate-300 cursor-pointer transition-colors"
            >
              Clear
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {SUBJECT_CHIPS.map((chip) => {
            const active = config.subjectDesc === chip.desc;
            return (
              <button
                key={chip.id}
                type="button"
                onClick={() => update({ subjectDesc: active ? '' : chip.desc })}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                  active
                    ? 'bg-pink-600/20 border-pink-500/50 text-pink-200'
                    : 'bg-surface-3 border-white/8 text-slate-400 hover:border-white/20 hover:text-slate-200'
                }`}
              >
                <span>{chip.icon}</span>
                {chip.label}
              </button>
            );
          })}
        </div>
        <p className="text-[10px] text-slate-600">
          Injected into prompt to ensure a clearly defined, realistic person is generated
        </p>
      </div>

      {/* Logo background color — only shown when a logo is uploaded */}
      {config.logoDataUrl && (
        <div className="space-y-1.5">
          <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Logo Background Color
          </label>
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={config.logoBgColor}
              onChange={(e) => update({ logoBgColor: e.target.value })}
              className="h-9 w-14 rounded-lg border border-white/10 cursor-pointer bg-transparent p-0.5"
              aria-label="Logo background panel color"
            />
            <div className="flex gap-1.5 flex-wrap">
              {['#ffffff', '#000000', '#1a1a2e', '#0057B8', '#C8102E', '#004225', '#F7941D'].map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => update({ logoBgColor: c })}
                  title={c}
                  className={`w-6 h-6 rounded-full border-2 cursor-pointer transition-transform hover:scale-110 ${config.logoBgColor === c ? 'border-brand-400 scale-110' : 'border-white/10'}`}
                  style={{ background: c }}
                  aria-label={`Set background to ${c}`}
                />
              ))}
            </div>
            <span className="text-[10px] font-mono text-slate-500">{config.logoBgColor}</span>
          </div>
          <p className="text-[10px] text-slate-600">Coloured panel drawn behind your logo on the composited image</p>
        </div>
      )}

      {/* Divider */}
      <div className="border-t border-white/5" />

      {/* Row 2 — Badge text + CTA text */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <OverlayField
          label="Badge / Urgency Text"
          value={config.badgeText}
          onChange={(v) => update({ badgeText: v })}
          placeholder="e.g. 24/7 Emergency Supply"
          field="badge"
          company={config.companyName}
          promptContext={promptContext}
          hint="Short punchy text shown on a bold badge overlay"
        />
        <OverlayField
          label="Call-to-Action Text"
          value={config.ctaText}
          onChange={(v) => update({ ctaText: v })}
          placeholder="e.g. Contact Your MRC Branch"
          field="cta"
          company={config.companyName}
          promptContext={promptContext}
          hint="Action text shown as a CTA strip on the image"
        />
      </div>

      {/* Prompt injection preview */}
      {(config.companyName || config.badgeText || config.ctaText || config.logoDataUrl) && (
        <div className="space-y-2">
          {config.logoDataUrl && (
            <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-pink-600/8 border border-pink-600/20">
              <svg className="w-3.5 h-3.5 text-pink-400 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              <p className="text-[11px] text-pink-300 leading-relaxed">
                <strong>Logo:</strong> Your uploaded file will be pixel-composited directly onto each generated image — exact colors, exact format, no AI approximation. Click the pink "Logo applied" badge on any result to reposition it.
              </p>
            </div>
          )}
          {buildOverlayPromptSuffix(config) && (
            <div className="rounded-lg bg-brand-600/8 border border-brand-600/20 px-4 py-3">
              <p className="text-[10px] font-semibold text-brand-400 uppercase tracking-wider mb-1.5">
                Appended to prompt (badge &amp; CTA)
              </p>
              <p className="text-[11px] text-slate-400 font-mono leading-relaxed">
                {buildOverlayPromptSuffix(config)}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── exported helper — builds the prompt suffix to inject ───────────────────────
// NOTE: Logo placement is NOT included here — the real uploaded logo is composited
// directly onto the generated image client-side via Canvas, so pixel-perfect fidelity
// is guaranteed regardless of what the AI model would hallucinate.
export function buildOverlayPromptSuffix(config: BrandOverlayConfig): string {
  if (!config.enabled) return '';

  const parts: string[] = [];

  // Subject description — ensures a clearly defined person is rendered
  if (config.subjectDesc) {
    parts.push(
      `The main subject must be a ${config.subjectDesc}, clearly visible, photorealistic, anatomically accurate, unambiguous gender presentation.`
    );
  }

  if (!config.logoDataUrl && config.companyName) {
    parts.push(`Place the ${config.companyName} company logo in the top-left corner of the image.`);
  }

  if (config.badgeText) {
    parts.push(
      `Include a bold red circular urgency badge in the upper-right area of the image with the text: "${config.badgeText}".`
    );
  }

  if (config.ctaText) {
    parts.push(
      `Add a call-to-action strip at the very bottom of the image with white bold text: "${config.ctaText}".`
    );
  }

  if (parts.length === 0) return '';
  return `[Brand overlay instructions: ${parts.join(' ')}]`;
}
