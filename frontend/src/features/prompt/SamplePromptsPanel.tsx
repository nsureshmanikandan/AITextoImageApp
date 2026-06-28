import { useState, useMemo, useCallback } from 'react';
import { CATEGORIES, SAMPLE_PROMPTS } from '@/data/samplePrompts';
import type { SamplePrompt } from '@/data/samplePrompts';

interface SamplePromptsPanelProps {
  onUsePrompt: (prompt: string) => void;
  onClose: () => void;
}

// ── Icon helpers ──────────────────────────────────────────────────────────────
function SearchIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}
function XIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}
function CopyIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}
function CheckIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}
function UseIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

// ── Category icon map ─────────────────────────────────────────────────────────
function CategoryIcon({ id, className }: { id: string; className?: string }) {
  const cls = className || 'w-4 h-4';
  // Brand-specific icons using recognizable shapes/metaphors
  switch (id) {
    case 'all':      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>;
    // Nike — swoosh-like diagonal check
    case 'nike':     return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 17 Q8 6 14 8 Q20 10 21 7"/></svg>;
    // Unilever — U shape
    case 'unilever': return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M5 4v9a7 7 0 0 0 14 0V4"/></svg>;
    // Estée Lauder — diamond / star (beauty luxury)
    case 'estee':    return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>;
    // J&J — medical cross
    case 'jnj':      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M12 4v16M4 12h16"/></svg>;
    // Jaguar — leaping cat silhouette approximated as diamond shape
    case 'jaguar':   return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3 L20 8 L20 16 L12 21 L4 16 L4 8 Z"/><circle cx="12" cy="12" r="3"/></svg>;
    // Shell — scallop shell / fan
    case 'shell':    return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M12 21 C6 18 3 14 3 9 A9 9 0 0 1 21 9 C21 14 18 18 12 21Z"/><line x1="12" y1="21" x2="12" y2="9"/><line x1="3" y1="9" x2="21" y2="9"/></svg>;
    // BP — sun/helios rays
    case 'bp':       return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="4.22" y1="4.22" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.78" y2="19.78"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="4.22" y1="19.78" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.78" y2="4.22"/></svg>;
    // SoCo — glass/goblet for spirits
    case 'soco':     return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M8 3h8l-2 9H10L8 3z"/><line x1="12" y1="12" x2="12" y2="19"/><line x1="8" y1="19" x2="16" y2="19"/></svg>;
    // MRC Global — industrial pipe/valve shape
    case 'mrc':      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="8" width="20" height="8" rx="4"/><circle cx="8" cy="12" r="2"/><circle cx="16" cy="12" r="2"/></svg>;
    default:         return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/></svg>;
  }
}

// ── Platform badge colors — keyed on prompt.platform string ──────────────────
const PLATFORM_COLORS: Record<string, string> = {
  Facebook:       'bg-blue-600/15 text-blue-300',
  Instagram:      'bg-pink-600/15 text-pink-300',
  'Google Ads':   'bg-amber-500/15 text-amber-300',
  Amazon:         'bg-orange-500/15 text-orange-300',
  LinkedIn:       'bg-sky-600/15 text-sky-300',
  TikTok:         'bg-rose-600/15 text-rose-300',
  Pinterest:      'bg-red-600/15 text-red-300',
  YouTube:        'bg-red-700/15 text-red-400',
  Snapchat:       'bg-yellow-400/15 text-yellow-300',
  'Digital Banner': 'bg-cyan-600/15 text-cyan-300',
  Email:          'bg-emerald-600/15 text-emerald-300',
};

function platformBadgeCls(platform: string) {
  return PLATFORM_COLORS[platform] || 'bg-slate-700/50 text-slate-400';
}

// ── Single prompt card ────────────────────────────────────────────────────────
function PromptCard({ prompt, onUse }: { prompt: SamplePrompt; onUse: (p: string) => void }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(prompt.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [prompt.prompt]);

  return (
    <article className="surface rounded-xl p-4 flex flex-col gap-3 hover:border-brand-600/30 transition-all duration-150 group">
      {/* Top action bar — badge + buttons on one line, full width */}
      <div className="flex items-center gap-1.5">
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${platformBadgeCls(prompt.platform)}`}>
          {prompt.platform}
        </span>
        <div className="flex items-center gap-1.5 ml-auto">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 text-[10px] border border-white/8 rounded-md text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all duration-150 cursor-pointer whitespace-nowrap"
            aria-label="Copy prompt to clipboard"
          >
            {copied ? <><CheckIcon /> Copied</> : <><CopyIcon /> Copy</>}
          </button>
          <button
            onClick={() => onUse(prompt.prompt)}
            className="flex items-center gap-1 px-2.5 py-1 text-[10px] bg-brand-600 text-white rounded-md hover:bg-brand-700 transition-all duration-150 cursor-pointer font-medium whitespace-nowrap"
            aria-label={`Use prompt: ${prompt.title}`}
          >
            <UseIcon /> Use
          </button>
        </div>
      </div>

      {/* Title + description — full width, no squeezing */}
      <div>
        <h3 className="text-sm font-semibold text-slate-200 leading-snug">{prompt.title}</h3>
        <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{prompt.description}</p>
      </div>

      {/* Prompt preview */}
      <div
        className="relative bg-surface-2 rounded-lg p-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setExpanded(!expanded)}
      >
        <p className={`text-xs text-slate-400 leading-relaxed font-mono ${expanded ? '' : 'line-clamp-3'}`}>
          {prompt.prompt}
        </p>
        {!expanded && (
          <div className="absolute bottom-0 inset-x-0 h-6 bg-gradient-to-t from-surface-2 to-transparent rounded-b-lg" />
        )}
        <p className="text-[10px] text-brand-500 mt-1">{expanded ? 'Show less ↑' : 'Read more ↓'}</p>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1">
        {prompt.tags.slice(0, 4).map((tag) => (
          <span key={tag} className="text-[10px] px-1.5 py-0.5 bg-surface-3 text-slate-600 rounded">
            {tag}
          </span>
        ))}
      </div>
    </article>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────
export function SamplePromptsPanel({ onUsePrompt, onClose }: SamplePromptsPanelProps) {
  const [activeCategory, setActiveCategory] = useState('all');
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    return SAMPLE_PROMPTS.filter((p) => {
      const matchCat = activeCategory === 'all' || p.category === activeCategory;
      if (!matchCat) return false;
      if (!q) return true;
      return (
        p.title.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.platform.toLowerCase().includes(q) ||
        p.tags.some((t) => t.toLowerCase().includes(q)) ||
        p.prompt.toLowerCase().includes(q)
      );
    });
  }, [activeCategory, search]);

  const handleUse = useCallback((prompt: string) => {
    onUsePrompt(prompt);
    onClose();
  }, [onUsePrompt, onClose]);

  return (
    <section
      className="surface rounded-xl flex flex-col overflow-hidden"
      style={{ maxHeight: '92vh' }}
      aria-label="Sample prompt library"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 shrink-0">
        <div>
          <h2 className="text-base font-bold gradient-brand text-glow">Prompt Library</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {filtered.length} prompt{filtered.length !== 1 ? 's' : ''} — click <strong className="text-brand-400">Use Prompt</strong> to load into editor
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-2 text-slate-500 hover:text-slate-200 rounded-lg hover:bg-white/5 transition-all duration-150 cursor-pointer"
          aria-label="Close prompt library"
        >
          <XIcon />
        </button>
      </div>

      {/* Search */}
      <div className="px-5 py-3 border-b border-white/5 shrink-0">
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600">
            <SearchIcon />
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by brand, platform, or keyword — e.g. Nike, LinkedIn, sustainability…"
            className="w-full pl-9 pr-4 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-colors"
            aria-label="Search prompts"
          />
        </div>
      </div>

      {/* Category tabs — horizontal scroll with fade hints */}
      <div className="relative border-b border-white/5 shrink-0">
        {/* Right fade gradient — hints there are more tabs */}
        <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-surface to-transparent z-10" />
        {/* Left fade gradient — shows when scrolled right */}
        <div className="pointer-events-none absolute left-0 top-0 bottom-0 w-6 bg-gradient-to-r from-surface to-transparent z-10" />
        <div className="px-5 py-3 overflow-x-auto scrollbar-hide">
        <div className="flex gap-2 min-w-max pr-10">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              aria-pressed={activeCategory === cat.id}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-150 cursor-pointer ${
                activeCategory === cat.id
                  ? 'bg-brand-600 text-white ring-1 ring-brand-500'
                  : 'bg-surface-2 text-slate-400 hover:text-slate-200 hover:bg-surface-3 border border-white/5'
              }`}
            >
              <CategoryIcon id={cat.id} className="w-3.5 h-3.5" />
              {cat.label}
              {cat.id !== 'all' && (
                <span className={`text-[10px] px-1 py-0.5 rounded ml-0.5 ${
                  activeCategory === cat.id ? 'bg-white/20 text-white' : 'bg-surface-3 text-slate-600'
                }`}>
                  {SAMPLE_PROMPTS.filter((p) => p.category === cat.id).length}
                </span>
              )}
            </button>
          ))}
        </div>
        </div>
      </div>

      {/* Prompt grid — scrollable */}
      <div className="flex-1 overflow-y-auto p-5">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-12 h-12 rounded-xl bg-brand-600/10 border border-brand-600/20 flex items-center justify-center mb-3">
              <SearchIcon />
            </div>
            <p className="text-slate-400 font-medium">No prompts found</p>
            <p className="text-slate-600 text-xs mt-1">Try a different search or category</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((p) => (
              <PromptCard key={p.id} prompt={p} onUse={handleUse} />
            ))}
          </div>
        )}
      </div>

      {/* Stats footer */}
      <div className="px-5 py-3 border-t border-white/5 shrink-0 flex items-center justify-between">
        <p className="text-xs text-slate-600">
          {SAMPLE_PROMPTS.length} brand marketing prompts · {CATEGORIES.length - 1} enterprise brands · Facebook, Instagram, LinkedIn, TikTok &amp; more
        </p>
        <div className="flex gap-1">
          {['Facebook', 'Instagram', 'LinkedIn', 'TikTok', 'Pinterest'].map((p) => (
            <span key={p} className={`w-2 h-2 rounded-full ${platformBadgeCls(p).split(' ')[0]}`} />
          ))}
        </div>
      </div>
    </section>
  );
}
