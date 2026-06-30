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
      key_message: "Greatness isn't given. Just do it.",
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
