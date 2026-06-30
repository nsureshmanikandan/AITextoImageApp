# Brand Template Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add clickable brand template cards above the Brand Ad form that pre-fill every field from a curated preset, then run the existing Sora + Flux→HTML pipeline unchanged.

**Architecture:** Frontend-only. A static `brandTemplates.ts` data file (~10 `BrandAdParams`-shaped presets) + a `BrandTemplatePicker` card-row component, wired into `BrandAdForm` so selecting a card sets the form's controlled state. No backend, pipeline, or schema changes.

**Tech Stack:** React + TypeScript + Vite + Tailwind. No JS test runner in repo — verify with `npx tsc --noEmit` and `npm run build`.

---

## Background

`BrandAdForm.tsx` is a controlled form with these state setters (verbatim from the file):
`setBrandName, setProduct, setTargetAudience, setKeyMessage, setCta, setTone,
setBrandDescription, setPrimaryColor, setSecondaryColor`. `tone` is one of
`'energetic' | 'trustworthy' | 'emotional' | 'urgent'`. Colors are two hex strings
combined into `brand_colors: [primaryColor, secondaryColor]` on submit. The
`BrandAdParams` type (in `frontend/src/types/index.ts`) is:
`brand_name, product, target_audience, key_message, cta, tone, brand_description?,
ad_reference?, brand_colors?, logo_base64?`.

---

## Task 1: Brand template data

**Files:**
- Create: `frontend/src/data/brandTemplates.ts`

- [ ] **Step 1: Create the data file with the interface and 10 presets**

```ts
import type { BrandAdParams } from '../types'

export interface BrandTemplate {
  id: string
  label: string
  industry: string
  accent: string          // hex used for the card accent/border
  emoji: string
  params: BrandAdParams
}

export const BRAND_TEMPLATES: BrandTemplate[] = [
  {
    id: 'tremfya', label: 'TREMFYA', industry: 'Healthcare', accent: '#0a4d8c', emoji: '💊',
    params: {
      brand_name: 'TREMFYA',
      product: 'TREMFYA for IBD — Awareness Campaign',
      target_audience: 'US patients experiencing persistent stomach pain, undiagnosed IBD',
      key_message: "Persistent stomach pain could be a sign of IBD. You don't have to ignore it — options like TREMFYA exist.",
      cta: 'Learn about IBD symptoms',
      tone: 'emotional',
      brand_description: 'TREMFYA is a J&J Immunology biologic treatment for IBD. Early-funnel awareness for patients who may not connect their symptoms to a diagnosable condition.',
      brand_colors: ['#0a4d8c', '#ffffff'],
    },
  },
  {
    id: 'jaguar', label: 'Jaguar', industry: 'Automotive / Luxury', accent: '#d81b60', emoji: '🐆',
    params: {
      brand_name: 'Jaguar',
      product: 'Jaguar "Copy Nothing" — Electric Rebrand',
      target_audience: 'Affluent, design-forward buyers ready for a bold electric future',
      key_message: 'Exuberant. Fearless. Imaginative. Luxury reinvented for the electric age.',
      cta: 'Explore the new Jaguar',
      tone: 'energetic',
      brand_description: 'Jaguar\'s avant-garde 2024 rebrand — fashion-meets-automotive, matte magenta wordmark, geometric abstraction. Copy Nothing.',
      brand_colors: ['#d81b60', '#111111'],
    },
  },
  {
    id: 'dove', label: 'Dove', industry: 'FMCG / Beauty', accent: '#2e6cb6', emoji: '🕊️',
    params: {
      brand_name: 'Dove',
      product: 'Dove Real Beauty',
      target_audience: 'Women of all ages, ethnicities and body types seeking authentic beauty',
      key_message: 'Beauty has no standard. Real beauty is for everyone.',
      cta: 'Join the movement',
      tone: 'emotional',
      brand_description: 'Unilever Dove "Real Beauty" — warm, inclusive, authentic lifestyle photography. Zero heavy retouching, genuine human voice.',
      brand_colors: ['#2e6cb6', '#ffffff'],
    },
  },
  {
    id: 'pepsi', label: 'Pepsi', industry: 'Beverage', accent: '#004b93', emoji: '🥤',
    params: {
      brand_name: 'Pepsi',
      product: 'Pepsi — Summer Refresh',
      target_audience: 'Gen Z and millennials craving bold, fun, energetic refreshment',
      key_message: 'Thirsty for more? Crack open the bold taste of Pepsi.',
      cta: 'Grab a Pepsi',
      tone: 'energetic',
      brand_description: 'Pepsi summer campaign — vibrant, youthful, high-energy. Icy cans, splashes, bold blue and red brand identity.',
      brand_colors: ['#004b93', '#e32934'],
    },
  },
  {
    id: 'cocacola', label: 'Coca-Cola', industry: 'Beverage', accent: '#f40009', emoji: '🥤',
    params: {
      brand_name: 'Coca-Cola',
      product: 'Coca-Cola — Share a Coke',
      target_audience: 'Families and friends sharing everyday moments of happiness',
      key_message: 'Share happiness. Share a Coke.',
      cta: 'Share a Coke today',
      tone: 'emotional',
      brand_description: 'Coca-Cola feel-good campaign — iconic red, ice-cold bottle, warm shared moments, classic Spencerian script.',
      brand_colors: ['#f40009', '#ffffff'],
    },
  },
  {
    id: 'bp', label: 'BP', industry: 'Energy', accent: '#009e3a', emoji: '⚡',
    params: {
      brand_name: 'BP',
      product: 'BP Pulse — EV Charging Network',
      target_audience: 'EV drivers and businesses transitioning to clean energy',
      key_message: 'Powering the switch to electric — reliable charging, everywhere you go.',
      cta: 'Find a charge point',
      tone: 'trustworthy',
      brand_description: 'BP sustainability / EV charging — clean green-and-yellow identity, modern infrastructure, forward-looking energy transition.',
      brand_colors: ['#009e3a', '#ffe600'],
    },
  },
  {
    id: 'shell', label: 'Shell', industry: 'Energy', accent: '#ed1c24', emoji: '🐚',
    params: {
      brand_name: 'Shell',
      product: 'Shell Recharge — Cleaner Energy',
      target_audience: 'Drivers and fleets seeking cleaner, dependable energy solutions',
      key_message: 'Cleaner energy, powering progress for everyone.',
      cta: 'Discover Shell Recharge',
      tone: 'trustworthy',
      brand_description: 'Shell energy-transition campaign — iconic red and yellow pecten, dependable modern energy, renewables focus.',
      brand_colors: ['#ed1c24', '#fbce07'],
    },
  },
  {
    id: 'estee', label: 'Estée Lauder', industry: 'Luxury Beauty', accent: '#1f1f1f', emoji: '💄',
    params: {
      brand_name: 'Estée Lauder',
      product: 'Advanced Night Repair',
      target_audience: 'Discerning skincare consumers seeking premium anti-aging results',
      key_message: 'Wake up to radiant, repaired skin every morning.',
      cta: 'Shop the serum',
      tone: 'trustworthy',
      brand_description: 'Estée Lauder luxury skincare — elegant editorial, gold-and-navy palette, the iconic Advanced Night Repair serum hero shot.',
      brand_colors: ['#1f1f1f', '#c8a24b'],
    },
  },
  {
    id: 'nike', label: 'Nike', industry: 'Sportswear', accent: '#111111', emoji: '✔️',
    params: {
      brand_name: 'Nike',
      product: 'Nike — Just Do It',
      target_audience: 'Athletes and everyday movers chasing their personal best',
      key_message: 'Greatness isn\'t given. Just do it.',
      cta: 'Shop the collection',
      tone: 'energetic',
      brand_description: 'Nike brand-standard ad — dramatic cinematic athlete, pure black background, single Swoosh, bold "Just Do It" energy.',
      brand_colors: ['#111111', '#ffffff'],
    },
  },
  {
    id: 'lipton', label: 'Lipton', industry: 'Beverage', accent: '#f7b500', emoji: '🍋',
    params: {
      brand_name: 'Lipton',
      product: 'Lipton Ice Tea — Feel the Chill',
      target_audience: 'Young, active consumers seeking refreshing summer hydration',
      key_message: 'Feel the chill — refreshingly real iced tea.',
      cta: 'Taste the refresh',
      tone: 'energetic',
      brand_description: 'Unilever Lipton Ice Tea — vibrant summer energy, sweating glass with lemon and mint, bold yellow branding on cobalt sky.',
      brand_colors: ['#f7b500', '#0066b3'],
    },
  },
]
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exit 0 (the file is data-only; verifies every `params` satisfies `BrandAdParams`, especially the `tone` union).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/brandTemplates.ts
git commit -m "feat: curated brand ad templates data (10 presets)"
```

---

## Task 2: BrandTemplatePicker component

**Files:**
- Create: `frontend/src/components/BrandTemplatePicker.tsx`

- [ ] **Step 1: Create the component**

```tsx
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
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exit 0

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/BrandTemplatePicker.tsx
git commit -m "feat: BrandTemplatePicker card-row component"
```

---

## Task 3: Wire picker into BrandAdForm

**Files:**
- Modify: `frontend/src/components/BrandAdForm.tsx`

- [ ] **Step 1: Add imports and selection state**

At the top of `BrandAdForm.tsx`, change the import block:

```tsx
import { useState } from 'react'
import type { BrandAdParams } from '../types'
import BrandTemplatePicker from './BrandTemplatePicker'
import type { BrandTemplate } from '../data/brandTemplates'
```

After the existing `const [logoPreview, setLogoPreview] = useState<string>('')` line, add:

```tsx
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
```

- [ ] **Step 2: Add the applyTemplate handler**

Directly above `const handleLogoUpload`, add:

```tsx
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
```

- [ ] **Step 3: Render the picker at the top of the form**

In the JSX, change the opening of the form so the picker renders first. Replace:

```tsx
      <h2 className="text-xl font-bold text-white mb-6">Brand Ad Configuration</h2>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
```

with:

```tsx
      <h2 className="text-xl font-bold text-white mb-6">Brand Ad Configuration</h2>
      <BrandTemplatePicker onSelect={applyTemplate} selectedId={selectedTemplateId} />
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
```

- [ ] **Step 4: Typecheck and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: typecheck exit 0; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/BrandAdForm.tsx
git commit -m "feat: wire brand template picker into BrandAdForm"
```

---

## Task 4: Manual verification

**Files:** none

- [ ] **Step 1:** Open the app → Create Video → Brand Ad. Confirm a horizontal row of ~10 brand cards appears above "Brand Name".
- [ ] **Step 2:** Click **Jaguar** → confirm brand name, product, audience, key message, CTA, tone (Energetic), and both color pickers update to Jaguar's values; the card shows selected.
- [ ] **Step 3:** Click **Coca-Cola** → confirm all fields switch to Coca-Cola's values (red primary color).
- [ ] **Step 4:** Edit a field manually, then submit → confirm the existing Sora + Flux→HTML pipeline runs normally and the banner uses the selected brand colors.

---

## Self-Review Notes (author)

- **Spec coverage:** data file (T1), picker component (T2), form wiring (T3), manual verify (T4). All spec sections mapped.
- **Type consistency:** `BrandTemplate { id,label,industry,accent,emoji,params }` defined in T1, imported in T2 and T3. `applyTemplate` uses only setters that exist in `BrandAdForm` (verified against the file). Every preset's `tone` is within the allowed union.
- **No backend/pipeline changes** — matches the frontend-only scope.
