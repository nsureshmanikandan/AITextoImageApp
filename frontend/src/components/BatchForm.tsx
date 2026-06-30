import { useState, useEffect, useCallback } from 'react'
import { getTrendingSuggestions, suggestTopics } from '../lib/api'
import type { TrendingTopic } from '../types'

interface Props {
  onBatchSubmit: (topics: string[], language: string, format: string, soraIntro: boolean) => void
  loading: boolean
}

const CATEGORIES = ['Tech', 'Finance', 'Health', 'Business', 'Science']

const LANGUAGES = [
  { value: 'en-IN', label: 'English (India)' },
  { value: 'hi-IN', label: 'Hindi' },
  { value: 'ta-IN', label: 'Tamil' },
  { value: 'te-IN', label: 'Telugu' },
  { value: 'kn-IN', label: 'Kannada' },
]

const FORMATS = [
  { value: 'landscape_16_9', label: 'Landscape' },
  { value: 'vertical_9_16',  label: 'Vertical' },
]

type AISuggestion = { label: string; hot: boolean }

export default function BatchForm({ onBatchSubmit, loading }: Props) {
  const [category, setCategory]           = useState('Tech')
  const [trending, setTrending]           = useState<TrendingTopic[]>([])
  const [trendingLoading, setTrendingLoading] = useState(false)
  const [selected, setSelected]           = useState<string[]>([])
  const [manualInput, setManualInput]     = useState('')
  const [language, setLanguage]           = useState('en-IN')
  const [format, setFormat]               = useState('landscape_16_9')
  const [soraIntro, setSoraIntro]         = useState(false)

  // AI suggestions state
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([])
  const [aiLoading, setAiLoading]         = useState(false)
  const [aiError, setAiError]             = useState('')
  const [showAI, setShowAI]               = useState(false)

  useEffect(() => {
    setTrendingLoading(true)
    getTrendingSuggestions(category.toLowerCase())
      .then(data => setTrending(data.slice(0, 10)))
      .catch(() => setTrending([]))
      .finally(() => setTrendingLoading(false))
  }, [category])

  const handleAISuggest = useCallback(async () => {
    setAiLoading(true)
    setAiError('')
    setShowAI(true)
    try {
      const topics = await suggestTopics('batch', category)
      setAiSuggestions(topics)
    } catch {
      setAiError('Could not fetch AI suggestions — try again')
    } finally {
      setAiLoading(false)
    }
  }, [category])

  const addTopic = (topic: string) => {
    if (!selected.includes(topic)) setSelected(prev => [...prev, topic])
  }

  const removeTopic = (topic: string) => setSelected(prev => prev.filter(t => t !== topic))

  const handleManualAdd = () => {
    const topics = manualInput.split(',').map(t => t.trim()).filter(Boolean)
    topics.forEach(t => { if (!selected.includes(t)) setSelected(prev => [...prev, t]) })
    setManualInput('')
  }

  return (
    <div className="glass-card p-8">
      <h2 className="text-xl font-bold text-white mb-1">Batch / Trending Topics</h2>
      <p className="text-sm text-slate-400 mb-6">
        Generate multiple educational videos — LinkedIn-skill quality, one per topic
      </p>

      <div className="space-y-6">

        {/* ── Category + AI Suggest header row ── */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm text-slate-400">Category</label>
            <button
              onClick={handleAISuggest}
              disabled={aiLoading}
              className="flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold
                         bg-gradient-to-r from-violet-600 to-azure-500 text-white
                         hover:opacity-90 disabled:opacity-50 transition-all"
            >
              {aiLoading
                ? <><span className="animate-spin inline-block">⟳</span> Generating…</>
                : <>✨ AI Suggest Topics</>}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                onClick={() => { setCategory(cat); setAiSuggestions([]); setShowAI(false) }}
                className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-all ${
                  category === cat
                    ? 'bg-amber-500 border-amber-500 text-white'
                    : 'border-slate-600 text-slate-400 hover:border-slate-400'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* ── AI-generated suggestions ── */}
        {showAI && (
          <div className="rounded-xl border border-violet-500/40 bg-violet-500/5 p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-semibold text-violet-300 uppercase tracking-wider">
                ✨ AI-Generated — Fresh Every Time
              </span>
            </div>
            {aiError && <p className="text-red-400 text-xs mb-2">{aiError}</p>}
            {aiLoading ? (
              <div className="flex flex-wrap gap-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="h-7 w-28 rounded-full bg-violet-800/40 animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {aiSuggestions.map(s => (
                  <button
                    key={s.label}
                    onClick={() => addTopic(s.label)}
                    disabled={selected.includes(s.label)}
                    className={`text-xs px-3 py-1.5 rounded-full border cursor-pointer transition-all
                      ${s.hot
                        ? 'border-amber-500 text-amber-300 hover:bg-amber-500/20'
                        : 'border-violet-500/60 text-violet-300 hover:bg-violet-500/20'}
                      ${selected.includes(s.label) ? 'opacity-40 cursor-default' : ''}`}
                  >
                    {s.hot ? '🔥 ' : '✦ '}{s.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Trending Now (existing) ── */}
        <div>
          <label className="block text-sm text-slate-400 mb-3">Trending Now</label>
          {trendingLoading ? (
            <div className="flex flex-wrap gap-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-7 w-24 rounded-full bg-slate-700 animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {trending.map(t => (
                <button
                  key={t.slug}
                  onClick={() => addTopic(t.label)}
                  disabled={selected.includes(t.label)}
                  className={`text-xs px-3 py-1.5 rounded-full border cursor-pointer transition-all ${
                    t.hot
                      ? 'border-amber-500 text-amber-300 hover:bg-amber-500/20'
                      : 'border-slate-600 text-slate-400 hover:border-slate-400'
                  } ${selected.includes(t.label) ? 'opacity-40 cursor-default' : ''}`}
                >
                  {t.hot ? '🔥 ' : ''}{t.label}
                </button>
              ))}
              {trending.length === 0 && (
                <span className="text-slate-500 text-sm">No trending topics — use AI Suggest above</span>
              )}
            </div>
          )}
        </div>

        {/* ── Manual input ── */}
        <div>
          <label className="block text-sm text-slate-400 mb-2">Add Topics Manually</label>
          <div className="flex gap-2">
            <input
              className="input-field flex-1"
              value={manualInput}
              onChange={e => setManualInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleManualAdd())}
              placeholder="Type topic or paste comma-separated list…"
            />
            <button onClick={handleManualAdd} className="btn-secondary px-4">Add</button>
          </div>
        </div>

        {/* ── Selected topics ── */}
        {selected.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-slate-400">
                {selected.length} topic{selected.length !== 1 ? 's' : ''} queued
              </label>
              <button
                onClick={() => setSelected([])}
                className="text-xs text-slate-500 hover:text-red-400 transition-colors"
              >
                Clear all
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {selected.map(t => (
                <span
                  key={t}
                  className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-full
                             bg-azure-500/20 border border-azure-500 text-azure-300"
                >
                  {t}
                  <button onClick={() => removeTopic(t)} className="ml-1 hover:text-white">×</button>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── Language + Format ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">Language</label>
            <select
              value={language}
              onChange={e => setLanguage(e.target.value)}
              className="input-field w-full"
            >
              {LANGUAGES.map(l => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-2">Format</label>
            <div className="flex gap-2">
              {FORMATS.map(f => (
                <button
                  key={f.value}
                  onClick={() => setFormat(f.value)}
                  className={`px-3 py-2 rounded-full text-sm border-2 capitalize transition-all ${
                    format === f.value
                      ? 'border-azure-500 bg-azure-500/20 text-azure-300'
                      : 'border-slate-700 text-slate-400 hover:border-slate-500'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Cinematic Sora intro toggle ── */}
        <label className="flex items-start gap-3 p-3 rounded-lg border-2 border-slate-700 hover:border-slate-500 cursor-pointer transition-all">
          <input
            type="checkbox"
            checked={soraIntro}
            onChange={e => setSoraIntro(e.target.checked)}
            className="mt-1 accent-amber-500 w-4 h-4"
          />
          <span>
            <span className="block text-sm font-semibold text-white">Add cinematic Sora intro to each video</span>
            <span className="block text-xs text-slate-400">
              A 12s cinematic opener per topic. Adds ~3–5 min <strong>per video</strong>.
            </span>
          </span>
        </label>

        <button
          onClick={() => onBatchSubmit(selected, language, format, soraIntro)}
          disabled={loading || selected.length === 0}
          className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading
            ? 'Queuing…'
            : `Generate ${selected.length} Video${selected.length !== 1 ? 's' : ''}${selected.length > 0 ? ` — ${language}` : ''}`}
        </button>
      </div>
    </div>
  )
}
