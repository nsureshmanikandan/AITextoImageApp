import React, { useState, useCallback } from 'react'
import { suggestTopics } from '../lib/api'
import type { EducationalParams } from '../types'

interface Props {
  onSubmit: (params: EducationalParams) => void
  loading: boolean
}

const LEVELS: { id: EducationalParams['level']; label: string; sub: string }[] = [
  { id: 'school',       label: 'School',       sub: 'Age 10–15' },
  { id: 'college',      label: 'College',      sub: 'Undergrad' },
  { id: 'professional', label: 'Professional', sub: 'Industry'  },
]

const DURATIONS = [3, 5, 10]

const CATEGORIES = ['AI', 'Tech', 'Finance', 'Health', 'Science']

type Suggestion = { label: string; hot: boolean }

export default function EducationalForm({ onSubmit, loading }: Props) {
  const [topic, setTopic]       = useState('')
  const [level, setLevel]       = useState<EducationalParams['level']>('professional')
  const [duration, setDuration] = useState(5)
  const [category, setCategory] = useState('AI')

  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [suggesting, setSuggesting]   = useState(false)
  const [suggestErr, setSuggestErr]   = useState('')

  const handleSuggest = useCallback(async () => {
    setSuggesting(true)
    setSuggestErr('')
    try {
      const topics = await suggestTopics('educational', category)
      setSuggestions(topics)
    } catch {
      setSuggestErr('Could not fetch suggestions — try again')
    } finally {
      setSuggesting(false)
    }
  }, [category])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!topic.trim()) return
    onSubmit({ topic: topic.trim(), level, duration_mins: duration })
  }

  return (
    <div className="glass-card p-8">
      <h2 className="text-xl font-bold text-white mb-1">Educational Video</h2>
      <p className="text-sm text-slate-400 mb-6">
        LinkedIn-quality structured learning video — same design as GenAI 30-min skill
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* ── Topic input ── */}
        <div>
          <label className="block text-sm text-slate-400 mb-1">Topic *</label>
          <input
            className="input-field w-full text-lg"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            required
            placeholder="e.g. LangChain, Agentic RAG, MCP Protocol…"
          />
        </div>

        {/* ── AI Suggest section ── */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm text-slate-400">Category</label>
            <button
              type="button"
              onClick={handleSuggest}
              disabled={suggesting}
              className="flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold
                         bg-gradient-to-r from-violet-600 to-azure-500 text-white
                         hover:opacity-90 disabled:opacity-50 transition-all"
            >
              {suggesting
                ? <><span className="animate-spin">⟳</span> Generating…</>
                : <>✨ Suggest Topics</>}
            </button>
          </div>

          {/* Category chips */}
          <div className="flex gap-2 mb-3">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                type="button"
                onClick={() => { setCategory(cat); setSuggestions([]) }}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                  category === cat
                    ? 'bg-azure-500 border-azure-500 text-white'
                    : 'border-slate-600 text-slate-400 hover:border-slate-400'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Suggestion chips */}
          {suggestErr && <p className="text-red-400 text-xs mb-2">{suggestErr}</p>}

          {suggestions.length > 0 && (
            <div className="flex flex-wrap gap-2 max-h-44 overflow-y-auto pr-1">
              {suggestions.map(s => (
                <button
                  key={s.label}
                  type="button"
                  onClick={() => setTopic(s.label)}
                  className={`text-xs px-3 py-1.5 rounded-full border cursor-pointer transition-all
                    hover:border-azure-400 hover:text-azure-300
                    ${s.hot ? 'border-amber-500 text-amber-300' : 'border-slate-600 text-slate-400'}
                    ${topic === s.label ? 'bg-azure-500/20 border-azure-400 text-azure-300' : ''}`}
                >
                  {s.hot ? '🔥 ' : ''}{s.label}
                </button>
              ))}
            </div>
          )}

          {suggestions.length === 0 && !suggesting && (
            <p className="text-xs text-slate-500 italic">
              Click "✨ Suggest Topics" to get fresh AI-generated topic ideas — new suggestions every time.
            </p>
          )}
        </div>

        {/* ── Level ── */}
        <div>
          <label className="block text-sm text-slate-400 mb-3">Audience Level</label>
          <div className="grid grid-cols-3 gap-3">
            {LEVELS.map(l => (
              <button
                key={l.id}
                type="button"
                onClick={() => setLevel(l.id)}
                className={`p-3 rounded-lg border-2 text-center transition-all ${
                  level === l.id
                    ? 'border-emerald-500 bg-emerald-500/10 text-white'
                    : 'border-slate-700 text-slate-400 hover:border-slate-500'
                }`}
              >
                <div className="font-semibold">{l.label}</div>
                <div className="text-xs opacity-70">{l.sub}</div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Duration ── */}
        <div>
          <label className="block text-sm text-slate-400 mb-3">Duration</label>
          <div className="flex gap-3">
            {DURATIONS.map(d => (
              <button
                key={d}
                type="button"
                onClick={() => setDuration(d)}
                className={`px-5 py-2 rounded-full border-2 text-sm font-medium transition-all ${
                  duration === d
                    ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300'
                    : 'border-slate-700 text-slate-400 hover:border-slate-500'
                }`}
              >
                {d} min
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !topic.trim()}
          className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Generating…' : (
            <span className="flex items-center justify-center gap-1 min-w-0">
              <span className="shrink-0">Create Educational Video —</span>
              <span className="truncate">{topic.trim() || 'enter topic'}</span>
            </span>
          )}
        </button>
      </form>
    </div>
  )
}
