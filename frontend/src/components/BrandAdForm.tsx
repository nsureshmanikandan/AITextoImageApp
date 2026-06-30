import { useState } from 'react'
import type { BrandAdParams } from '../types'
import BrandTemplatePicker from './BrandTemplatePicker'
import type { BrandTemplate } from '../data/brandTemplates'

interface Props {
  onSubmit: (params: BrandAdParams & { brand_colors?: string[] }) => void
  loading: boolean
}

const TONES: { id: BrandAdParams['tone']; label: string; color: string }[] = [
  { id: 'energetic', label: 'Energetic', color: 'bg-orange-500' },
  { id: 'trustworthy', label: 'Trustworthy', color: 'bg-blue-500' },
  { id: 'emotional', label: 'Emotional', color: 'bg-pink-500' },
  { id: 'urgent', label: 'Urgent', color: 'bg-red-500' },
]

export default function BrandAdForm({ onSubmit, loading }: Props) {
  const [brandName, setBrandName] = useState('TREMFYA')
  const [product, setProduct] = useState('TREMFYA for IBD — Awareness Campaign')
  const [targetAudience, setTargetAudience] = useState('US patients experiencing persistent stomach pain, undiagnosed IBD')
  const [keyMessage, setKeyMessage] = useState('Persistent stomach pain could be a sign of IBD. You don\'t have to ignore it — options like TREMFYA exist.')
  const [cta, setCta] = useState('Learn more about IBD symptoms and TREMFYA')
  const [tone, setTone] = useState<BrandAdParams['tone']>('emotional')
  const [brandDescription, setBrandDescription] = useState('TREMFYA is a J&J Immunology biologic treatment for IBD. Early funnel awareness for patients who may not connect their symptoms to a diagnosable condition.')
  const [primaryColor, setPrimaryColor] = useState('#2563EB')
  const [secondaryColor, setSecondaryColor] = useState('#FFFFFF')
  const [adRef, setAdRef] = useState('')
  const [logoBase64, setLogoBase64] = useState<string>('')
  const [logoPreview, setLogoPreview] = useState<string>('')
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')

  const applyTemplate = (t: BrandTemplate) => {
    const p = t.params
    setBrandName(p.brand_name)
    setProduct(p.product)
    setTargetAudience(p.target_audience)
    setKeyMessage(p.key_message)
    setCta(p.cta)
    setTone(p.tone)
    setBrandDescription(p.brand_description ?? '')
    if (p.brand_colors && p.brand_colors.length >= 2) {
      setPrimaryColor(p.brand_colors[0])
      setSecondaryColor(p.brand_colors[1])
    }
    setSelectedTemplateId(t.id)
  }

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const result = ev.target?.result as string
      setLogoPreview(result)
      // Strip data URL prefix for storage (keep just base64)
      setLogoBase64(result.split(',')[1] ?? result)
    }
    reader.readAsDataURL(file)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      brand_name: brandName,
      product,
      target_audience: targetAudience,
      key_message: keyMessage,
      cta,
      tone,
      brand_description: brandDescription,
      ad_reference: adRef,
      brand_colors: [primaryColor, secondaryColor],
      logo_base64: logoBase64 || undefined,
    })
  }

  return (
    <div className="glass-card p-8">
      <h2 className="text-xl font-bold text-white mb-6">Brand Ad Configuration</h2>
      <BrandTemplatePicker onSelect={applyTemplate} selectedId={selectedTemplateId} />
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Brand Name *</label>
            <input className="input-field w-full" value={brandName} onChange={e => setBrandName(e.target.value)} required placeholder="e.g. Tanishq" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Product / Campaign *</label>
            <input className="input-field w-full" value={product} onChange={e => setProduct(e.target.value)} required placeholder="e.g. Diwali Collection 2025" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Target Audience *</label>
            <input className="input-field w-full" value={targetAudience} onChange={e => setTargetAudience(e.target.value)} required placeholder="e.g. Women 25-45, South India" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">CTA *</label>
            <input className="input-field w-full" value={cta} onChange={e => setCta(e.target.value)} required placeholder="e.g. Order now" />
          </div>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Key Message *</label>
          <input className="input-field w-full" value={keyMessage} onChange={e => setKeyMessage(e.target.value)} required placeholder="e.g. Celebrate every moment with timeless gold" />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-2">Tone</label>
          <div className="flex flex-wrap gap-2">
            {TONES.map(t => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTone(t.id)}
                className={`px-4 py-2 rounded-full text-sm font-medium border transition-all ${
                  tone === t.id ? `${t.color} text-white border-transparent` : 'border-slate-600 text-slate-400 hover:border-slate-400'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Primary Color</label>
            <input type="color" value={primaryColor} onChange={e => setPrimaryColor(e.target.value)} className="w-full h-10 rounded cursor-pointer border border-slate-600 bg-transparent" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Secondary Color</label>
            <input type="color" value={secondaryColor} onChange={e => setSecondaryColor(e.target.value)} className="w-full h-10 rounded cursor-pointer border border-slate-600 bg-transparent" />
          </div>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Brand Logo <span className="text-slate-500">(optional — PNG, SVG, JPG)</span></label>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-600 text-slate-400 hover:border-slate-400 hover:text-white cursor-pointer transition-colors text-sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
              Upload Logo
              <input type="file" accept="image/*" onChange={handleLogoUpload} className="hidden" />
            </label>
            {logoPreview && (
              <div className="flex items-center gap-2">
                <img src={logoPreview} alt="Logo preview" className="h-10 w-auto max-w-[120px] object-contain rounded border border-white/10 bg-white/5 p-1" />
                <button type="button" onClick={() => { setLogoBase64(''); setLogoPreview('') }} className="text-xs text-slate-500 hover:text-red-400 transition-colors">Remove</button>
              </div>
            )}
          </div>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Brand Description <span className="text-slate-500">(optional)</span></label>
          <textarea className="input-field w-full" rows={3} value={brandDescription} onChange={e => setBrandDescription(e.target.value)} placeholder="e.g. TREMFYA is a J&J Immunology biologic for IBD..." />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Existing Ad Reference <span className="text-slate-500">(optional)</span></label>
          <textarea className="input-field w-full" rows={2} value={adRef} onChange={e => setAdRef(e.target.value)} placeholder="Paste URL or describe an existing ad to inspire the style..." />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? 'Generating...' : 'Create Brand Ad'}
        </button>
      </form>
    </div>
  )
}
