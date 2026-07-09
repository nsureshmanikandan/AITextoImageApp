import { motion } from 'framer-motion'
import { CheckCircle2, Link, X } from 'lucide-react'
import { useState } from 'react'
import { cn } from '../lib/utils'
import { LANGUAGE_OPTIONS } from '../types'

export interface FeedFormData {
  feed_url: string
  display_name: string
  polling_interval_seconds: number
  language: string
  priority_keywords: string
  trust_level: 'trusted' | 'standard' | 'untrusted'
  auto_approve: boolean
  enabled: boolean
}

interface FeedFormProps {
  mode: 'create' | 'edit'
  initialData?: Partial<FeedFormData>
  onSubmit: (data: FeedFormData) => void
  onCancel: () => void
  onValidateUrl?: () => void
  validating?: boolean
}

const DEFAULT_FORM: FeedFormData = {
  feed_url: '',
  display_name: '',
  polling_interval_seconds: 300,
  language: 'en-IN',
  priority_keywords: '',
  trust_level: 'standard',
  auto_approve: false,
  enabled: true,
}

export default function FeedForm({ mode, initialData, onSubmit, onCancel, onValidateUrl, validating }: FeedFormProps) {
  const [form, setForm] = useState<FeedFormData>({ ...DEFAULT_FORM, ...initialData })
  const [errors, setErrors] = useState<Partial<Record<keyof FeedFormData, string>>>({})

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof FeedFormData, string>> = {}

    if (!form.feed_url) {
      newErrors.feed_url = 'Feed URL is required'
    } else {
      try {
        const url = new URL(form.feed_url)
        if (!['http:', 'https:'].includes(url.protocol)) {
          newErrors.feed_url = 'URL must use HTTP or HTTPS'
        }
      } catch {
        newErrors.feed_url = 'Invalid URL format'
      }
    }

    if (!form.display_name.trim()) {
      newErrors.display_name = 'Display name is required'
    }

    if (form.polling_interval_seconds < 60) {
      newErrors.polling_interval_seconds = 'Minimum polling interval is 60 seconds'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validate()) {
      onSubmit(form)
    }
  }

  const updateField = <K extends keyof FeedFormData>(key: K, value: FeedFormData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    if (errors[key]) {
      setErrors((prev) => ({ ...prev, [key]: undefined }))
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="glass-card p-6 max-w-lg w-full"
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">
          {mode === 'create' ? 'Add Feed' : 'Edit Feed'}
        </h3>
        <button onClick={onCancel} className="text-slate-400 hover:text-white transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Feed URL */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Feed URL</label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Link className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={form.feed_url}
                onChange={(e) => updateField('feed_url', e.target.value)}
                placeholder="https://example.com/rss.xml"
                className={cn(
                  'w-full pl-9 pr-3 py-2.5 rounded-lg bg-navy-900/60 border text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-azure-500',
                  errors.feed_url ? 'border-red-500/50' : 'border-white/10'
                )}
              />
            </div>
            {onValidateUrl && mode === 'edit' && (
              <button
                type="button"
                onClick={onValidateUrl}
                disabled={validating}
                className="btn-secondary text-xs px-3"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          {errors.feed_url && <p className="text-xs text-red-400 mt-1">{errors.feed_url}</p>}
        </div>

        {/* Display Name */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Display Name</label>
          <input
            type="text"
            value={form.display_name}
            onChange={(e) => updateField('display_name', e.target.value)}
            placeholder="My News Feed"
            className={cn(
              'w-full px-3 py-2.5 rounded-lg bg-navy-900/60 border text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-azure-500',
              errors.display_name ? 'border-red-500/50' : 'border-white/10'
            )}
          />
          {errors.display_name && <p className="text-xs text-red-400 mt-1">{errors.display_name}</p>}
        </div>

        {/* Polling Interval & Language */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Polling Interval (sec)</label>
            <input
              type="number"
              min={60}
              value={form.polling_interval_seconds}
              onChange={(e) => updateField('polling_interval_seconds', parseInt(e.target.value) || 60)}
              className={cn(
                'w-full px-3 py-2.5 rounded-lg bg-navy-900/60 border text-sm text-white focus:outline-none focus:ring-1 focus:ring-azure-500',
                errors.polling_interval_seconds ? 'border-red-500/50' : 'border-white/10'
              )}
            />
            {errors.polling_interval_seconds && <p className="text-xs text-red-400 mt-1">{errors.polling_interval_seconds}</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Language</label>
            <select
              value={form.language}
              onChange={(e) => updateField('language', e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-navy-900/60 border border-white/10 text-sm text-white focus:outline-none focus:ring-1 focus:ring-azure-500"
            >
              {LANGUAGE_OPTIONS.map((lang) => (
                <option key={lang.value} value={lang.value}>{lang.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Priority Keywords */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Priority Keywords (comma-separated)</label>
          <input
            type="text"
            value={form.priority_keywords}
            onChange={(e) => updateField('priority_keywords', e.target.value)}
            placeholder="breaking, urgent, exclusive"
            className="w-full px-3 py-2.5 rounded-lg bg-navy-900/60 border border-white/10 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-azure-500"
          />
        </div>

        {/* Trust Level */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Trust Level</label>
          <select
            value={form.trust_level}
            onChange={(e) => updateField('trust_level', e.target.value as FeedFormData['trust_level'])}
            className="w-full px-3 py-2.5 rounded-lg bg-navy-900/60 border border-white/10 text-sm text-white focus:outline-none focus:ring-1 focus:ring-azure-500"
          >
            <option value="trusted">Trusted</option>
            <option value="standard">Standard</option>
            <option value="untrusted">Untrusted</option>
          </select>
        </div>

        {/* Auto-approve toggle */}
        <div className="flex items-center justify-between py-2">
          <div>
            <label className="text-sm font-medium text-white">Auto-Approve</label>
            <p className="text-xs text-slate-400">Automatically approve videos from this feed</p>
          </div>
          <button
            type="button"
            onClick={() => updateField('auto_approve', !form.auto_approve)}
            className={cn(
              'relative w-11 h-6 rounded-full transition-colors',
              form.auto_approve ? 'bg-azure-500' : 'bg-slate-600'
            )}
          >
            <span
              className={cn(
                'absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform',
                form.auto_approve && 'translate-x-5'
              )}
            />
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button type="button" onClick={onCancel} className="btn-secondary text-sm px-4 py-2">
            Cancel
          </button>
          <button type="submit" className="btn-primary text-sm px-4 py-2">
            {mode === 'create' ? 'Add Feed' : 'Save Changes'}
          </button>
        </div>
      </form>
    </motion.div>
  )
}
