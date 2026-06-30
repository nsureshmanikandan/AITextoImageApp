# Brand Template Picker — Design

**Date:** 2026-06-30
**Status:** Approved

## Goal

Add a row of clickable brand template cards above the Brand Ad Configuration
form. Clicking a card pre-fills every form field (brand, product, audience, key
message, CTA, tone, brand colors) from a curated preset, so the user can launch
a polished brand ad in one click — then edit if desired and run the existing
Sora + Flux→HTML generation path unchanged.

## Why this shape

The source project `AITextoImageApp` (`frontend/src/data/samplePrompts.ts`) has
51 brand templates, but they are **image-prompt-shaped** (key message and CTA
buried inside Flux prompt prose) and image-only (no Sora prompts). Rather than
parse incompatible blobs, we **curate ~10 VernacularCast-native presets** shaped
exactly as `BrandAdParams`, reusing the messaging, tone, and brand colors from
`AITextoImageApp`. This keeps the data clean and directly compatible with the
existing form + pipeline.

## Scope

- **Frontend only.** No backend, pipeline, schema, or credential changes.
- The generation path (Sora video + 3 Flux ad-variation images → animated HTML
  banner) is untouched. Templates only pre-fill the existing form.

## Brands (curated, ~10)

TREMFYA (J&J, Healthcare), Jaguar (Automotive/Luxury), Dove (Unilever, FMCG/
Beauty), Pepsi (Beverage), Coca-Cola (Beverage), BP (Energy), Shell (Energy),
Estée Lauder (Luxury Beauty), Nike (Sportswear), Lipton (Unilever, Beverage).

## Components

### 1. Data — `frontend/src/data/brandTemplates.ts` (new)

```ts
import type { BrandAdParams } from '../types'

export interface BrandTemplate {
  id: string          // 'tremfya'
  label: string       // 'TREMFYA'
  industry: string    // 'Healthcare'
  accent: string      // hex color for the card border/accent, e.g. '#c8102e'
  emoji?: string      // optional quick marker, e.g. '💊'
  params: BrandAdParams
}

export const BRAND_TEMPLATES: BrandTemplate[] = [ /* ~10 entries */ ]
```

Each `params` object fully satisfies the existing `BrandAdParams` interface:
`brand_name, product, target_audience, key_message, cta, tone,
brand_description?, brand_colors?`. `tone` must be one of the allowed values
(`'energetic' | 'trustworthy' | 'emotional' | 'urgent'`). `brand_colors` is a
two-entry `[primary, secondary]` hex array that already feeds the HTML banner.

Content is curated per brand (messaging/colors drawn from `AITextoImageApp`):
e.g. TREMFYA → emotional tone, key message about persistent stomach pain / IBD,
CTA "Learn about IBD", colors `['#0a4d8c', '#ffffff']`.

### 2. UI — `frontend/src/components/BrandTemplatePicker.tsx` (new)

```ts
interface Props {
  onSelect: (template: BrandTemplate) => void
  selectedId?: string
}
```

Renders a horizontally-scrollable / wrapping row of cards from
`BRAND_TEMPLATES`. Each card shows `emoji + label + industry`, uses `accent` for
its border, and highlights when `selectedId` matches. Clicking calls
`onSelect(template)`.

### 3. Wiring — `frontend/src/components/BrandAdForm.tsx` (modify)

- Render `<BrandTemplatePicker onSelect={applyTemplate} selectedId={selectedId} />`
  at the top of the form (above "Brand Name").
- `applyTemplate(t)` sets all controlled field states from `t.params`
  (brand name, product, target audience, key message, CTA, tone, and the brand
  color pickers) and records `selectedId = t.id`.
- The user can still edit any field afterward; editing does not need to clear
  the selection (cosmetic only).
- Submission is unchanged — the existing `onSubmit` fires with whatever is in the
  form.

## Data flow

Click card → `onSelect(template)` → `applyTemplate` populates form state →
(optional user edits) → existing **Create Brand Ad** submit → existing pipeline
(Sora + Flux variations + HTML banner). No new network calls for templates;
the data is static and bundled.

## Error handling

- Static data; no runtime fetch, so no failure modes for the picker itself.
- If a template omits an optional field (`brand_description`, `brand_colors`),
  the form falls back to its current defaults (same as a blank form today).

## Testing

- Typecheck (`npx tsc --noEmit`) and build (`npm run build`) must pass.
- Manual: open Brand Ad mode → the picker row shows ~10 cards → click TREMFYA →
  all fields populate (brand, product, audience, key message, CTA, tone, colors)
  → submit runs the normal pipeline and produces a banner using the template's
  brand colors.
- Manual: click a second card → fields update to the new template.
- Manual: blank/manual entry still works when no card is selected.

## Non-goals

- No backend template store or API (static frontend data is sufficient).
- No parsing/import of AITextoImageApp's 51 image prompts.
- No change to Sora/Flux/HTML generation logic.
- No per-platform sizing presets (single brand-ad format as today).
