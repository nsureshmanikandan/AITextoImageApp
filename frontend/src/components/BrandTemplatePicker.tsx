import { BRAND_TEMPLATES, type BrandTemplate } from '../data/brandTemplates'

interface Props {
  onSelect: (template: BrandTemplate) => void
  selectedId?: string
}

export default function BrandTemplatePicker({ onSelect, selectedId }: Props) {
  return (
    <div className="mb-6">
      <label className="block text-sm text-slate-400 mb-2">
        Start from a brand template <span className="text-slate-500">(optional)</span>
      </label>
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
        {BRAND_TEMPLATES.map(t => {
          const active = t.id === selectedId
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onSelect(t)}
              title={`${t.label} — ${t.industry}`}
              style={{ borderColor: active ? t.accent : undefined }}
              className={`flex-shrink-0 w-32 text-left p-3 rounded-xl border-2 transition-all ${
                active
                  ? 'bg-white/10'
                  : 'border-slate-700 bg-white/5 hover:border-slate-500'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-lg leading-none">{t.emoji}</span>
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ background: t.accent }}
                />
              </div>
              <div className="text-sm font-semibold text-white truncate">{t.label}</div>
              <div className="text-[11px] text-slate-400 truncate">{t.industry}</div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
