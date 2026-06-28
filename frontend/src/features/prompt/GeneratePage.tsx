import { useState, useCallback, useEffect, useRef } from 'react';
import { PromptInput } from './PromptInput';
import { PromptEditor } from './PromptEditor';
import { PromptDiffView } from './PromptDiffView';
import { SamplePromptsPanel } from './SamplePromptsPanel';
import { BrandOverlayPanel, buildOverlayPromptSuffix, EMPTY_OVERLAY } from './BrandOverlayPanel';
import type { BrandOverlayConfig } from './BrandOverlayPanel';
import { GenerationStatus } from '@/features/generation/GenerationStatus';
import { CompositeImageCard } from '@/features/generation/CompositeImageCard';
import { useGenerateImage, useRegenerateImage } from '@/hooks/useGenerateImage';
import { refinePrompt } from '@/api/generateApi';
import { getImageUrl } from '@/api/imagesApi';
import type { ImageResult } from '@/types';

function BookIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <line x1="12" y1="6" x2="16" y2="6" />
      <line x1="12" y1="10" x2="16" y2="10" />
    </svg>
  );
}

function BrandIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18" />
      <path d="M9 21V9" />
    </svg>
  );
}

function ChevronUpIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export function GeneratePage() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [results, setResults] = useState<ImageResult[] | null>(null);
  const [generatedPrompt, setGeneratedPrompt] = useState<string>('');
  const [previousPrompt, setPreviousPrompt] = useState<string>('');
  const [currentVersionId, setCurrentVersionId] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [showLibrary, setShowLibrary] = useState(false);
  const [showBrandOverlay, setShowBrandOverlay] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<string>('');
  const [overlayConfig, setOverlayConfig] = useState<BrandOverlayConfig>(EMPTY_OVERLAY);
  const [usedFormats, setUsedFormats] = useState<string[]>([]);
  // track the raw prompt text for AI suggest context
  const [currentPromptText, setCurrentPromptText] = useState<string>('');

  const generateMutation = useGenerateImage();
  const regenerateMutation = useRegenerateImage();

  const handleSubmit = useCallback((prompt: string, numVariations: number, presetId?: string, imageFormats?: string[]) => {
    setJobId(null);
    setResults(null);
    setGeneratedPrompt('');
    setPreviousPrompt('');
    setUsedFormats(imageFormats ?? []);
    const suffix = buildOverlayPromptSuffix(overlayConfig);
    const finalPrompt = suffix ? `${prompt}\n\n${suffix}` : prompt;
    generateMutation.mutate(
      { prompt: finalPrompt, numVariations, presetId, imageFormats },
      { onSuccess: (data) => setJobId(data.jobId) }
    );
  }, [generateMutation, overlayConfig]);

  const handleComplete = useCallback((completedResults: ImageResult[], promptText: string) => {
    setResults(completedResults);
    setGeneratedPrompt(promptText || completedResults[0]?.generatedPrompt || '');
    if (completedResults.length > 0) {
      setCurrentVersionId(completedResults[0].promptVersionId);
    }
  }, []);

  const handleRetry = useCallback(() => {
    setJobId(null);
    setResults(null);
  }, []);

  const handleSave = useCallback(async (editedText: string, promptVersionId: string) => {
    setIsSaving(true);
    try {
      const newVersion = await refinePrompt({ promptVersionId, editedText });
      setPreviousPrompt(generatedPrompt);
      setGeneratedPrompt(editedText);
      setCurrentVersionId(newVersion.id);
    } finally {
      setIsSaving(false);
    }
  }, [generatedPrompt]);

  const handleRegenerate = useCallback((editedPrompt: string) => {
    if (!results || results.length === 0) return;
    setResults(null);
    setPreviousPrompt(generatedPrompt);
    regenerateMutation.mutate(
      { imageId: results[0].imageId, editedPrompt },
      { onSuccess: (data) => setJobId(data.jobId) }
    );
  }, [results, generatedPrompt, regenerateMutation]);

  const handleUsePrompt = useCallback((prompt: string) => {
    setJobId(null);
    setResults(null);
    setGeneratedPrompt('');
    setPreviousPrompt('');
    setCurrentVersionId('');
    setSelectedPrompt(prompt);
    setCurrentPromptText(prompt);
    // Sample prompt is an explicit user choice — treat as manual edit
    userEditedPromptRef.current = true;
    setShowLibrary(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleOverlayToggle = useCallback(() => {
    setShowBrandOverlay((v) => {
      const next = !v;
      // Reset auto-fill when panel opens; keep overlay.enabled=true always once set
      if (next) userEditedPromptRef.current = false;
      return next;
    });
  }, []);

  // Ref to know whether the user has manually edited the textarea since last auto-fill
  const userEditedPromptRef = useRef(false);

  const handleOverlayChange = useCallback((cfg: BrandOverlayConfig) => {
    // enabled stays true once the user has entered any content — closing the panel
    // should not strip the logo or clear the prompt suffix from generation
    setOverlayConfig({ ...cfg, enabled: true });
  }, []);

  // Auto-update prompt textarea when brand overlay fields change
  useEffect(() => {
    if (!showBrandOverlay) return;
    // Don't overwrite if user has manually typed their own prompt
    if (userEditedPromptRef.current) return;

    const { companyName, badgeText, ctaText, subjectDesc } = overlayConfig;
    if (!companyName && !badgeText && !ctaText && !subjectDesc) return;

    const parts: string[] = [];
    if (companyName) parts.push(`Professional ${companyName} brand marketing campaign`);
    if (subjectDesc) parts.push(`featuring a ${subjectDesc}`);
    if (badgeText) parts.push(`key message: "${badgeText}"`);
    if (ctaText) parts.push(`call-to-action: "${ctaText}"`);

    const suggestion = parts.join(', ') + '. Photorealistic, high-quality advertising visual, clean and compelling.';
    setSelectedPrompt(suggestion);
    setCurrentPromptText(suggestion);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overlayConfig.companyName, overlayConfig.badgeText, overlayConfig.ctaText, overlayConfig.subjectDesc, showBrandOverlay]);

  const FORMAT_LABELS: Record<string, string> = {
    square:    'Square 1:1 · Instagram/FB (1080×1080)',
    facebook:  'Facebook/LinkedIn 1.9:1 (1200×628)',
    wide:      'Wide 16:9 · YouTube (1280×720)',
    portrait:  'Portrait 2:3 · Pinterest (1000×1500)',
    story:     'Story 9:16 · Stories/TikTok (1080×1920)',
    landscape: 'Facebook/LinkedIn 1.9:1 (1200×628)',
  };

  const isGenerating = generateMutation.isPending || (!!jobId && !results);

  const overlayActive = showBrandOverlay && (
    overlayConfig.companyName || overlayConfig.badgeText || overlayConfig.ctaText || overlayConfig.logoDataUrl
  );

  return (
    <div className="max-w-4xl mx-auto space-y-5">

      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold gradient-brand text-glow">Generate Image</h2>
          <p className="text-sm text-slate-500 mt-1">
            Describe what you want to see and let AI create it for you
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Brand Overlay toggle */}
          <button
            onClick={handleOverlayToggle}
            aria-expanded={showBrandOverlay}
            aria-controls="brand-overlay-panel"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer ${
              showBrandOverlay
                ? 'bg-pink-600/90 text-white ring-1 ring-pink-500 glow-pink'
                : 'bg-surface border border-white/8 text-slate-300 hover:text-slate-100 hover:border-white/20 hover:bg-surface-2'
            }`}
          >
            <BrandIcon />
            Brand Overlay
            {showBrandOverlay ? <ChevronUpIcon /> : <ChevronDownIcon />}
            {overlayActive && (
              <span className="w-2 h-2 rounded-full bg-pink-400 animate-pulse" />
            )}
          </button>

          {/* Prompt Library toggle */}
          <button
            onClick={() => {
              setShowLibrary((v) => {
                const next = !v;
                if (next) window.scrollTo({ top: 0, behavior: 'smooth' });
                return next;
              });
            }}
            aria-expanded={showLibrary}
            aria-controls="prompt-library"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer ${
              showLibrary
                ? 'bg-brand-600 text-white ring-1 ring-brand-500 glow-violet'
                : 'bg-surface border border-white/8 text-slate-300 hover:text-slate-100 hover:border-white/20 hover:bg-surface-2'
            }`}
          >
            <BookIcon />
            Prompt Library
            {showLibrary ? <ChevronUpIcon /> : <ChevronDownIcon />}
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/15 font-semibold">60+</span>
          </button>
        </div>
      </div>

      {/* Brand Overlay Panel */}
      {showBrandOverlay && (
        <div
          id="brand-overlay-panel"
          className="surface rounded-xl p-5 border-pink-600/20 animate-fade-in"
          style={{ borderColor: 'rgba(236,72,153,0.2)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <BrandIcon />
            <h3 className="text-sm font-semibold text-slate-200">Brand Overlay Settings</h3>
            <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-pink-600/20 text-pink-300 font-medium">
              Injected into prompt
            </span>
          </div>
          <BrandOverlayPanel
            config={overlayConfig}
            onChange={handleOverlayChange}
            promptContext={currentPromptText}
          />
        </div>
      )}

      {/* Prompt Library Panel */}
      {showLibrary && (
        <div id="prompt-library" className="animate-fade-in">
          <SamplePromptsPanel
            onUsePrompt={handleUsePrompt}
            onClose={() => setShowLibrary(false)}
          />
        </div>
      )}

      {/* Tip bar */}
      {!showLibrary && !showBrandOverlay && (
        <div className="flex items-center gap-2 px-3 py-2 bg-brand-600/8 border border-brand-600/15 rounded-lg">
          <BookIcon />
          <p className="text-xs text-slate-400">
            Need inspiration? Open the{' '}
            <button
              onClick={() => { setShowLibrary(true); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              className="text-brand-400 hover:text-brand-300 font-medium cursor-pointer underline underline-offset-2"
            >
              Prompt Library
            </button>
            {' '}— 60+ enterprise brand prompts for Nike, Unilever, Shell, BP, Jaguar, J&amp;J, Estée Lauder, SoCo &amp; MRC Global. Use{' '}
            <button
              onClick={handleOverlayToggle}
              className="text-pink-400 hover:text-pink-300 font-medium cursor-pointer underline underline-offset-2"
            >
              Brand Overlay
            </button>
            {' '}to add your logo, badge &amp; CTA text.
          </p>
        </div>
      )}

      {/* Prompt input */}
      <div className="surface rounded-xl p-5">
        <PromptInput
          onSubmit={handleSubmit}
          isLoading={isGenerating}
          disabled={isGenerating}
          externalPrompt={selectedPrompt}
          onPromptChange={(text) => {
            setCurrentPromptText(text);
            // Mark as manually edited so auto-fill stops overwriting
            userEditedPromptRef.current = true;
          }}
        />
      </div>

      {/* Generation status */}
      {jobId && !results && (
        <GenerationStatus
          jobId={jobId}
          onComplete={handleComplete}
          onRetry={handleRetry}
        />
      )}

      {/* Results */}
      {results && results.length > 0 && (
        <div className="space-y-5">
          <div className="surface rounded-xl p-5">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">
              Generated Images
            </h3>
            <div className={`grid gap-4 ${
              results.length === 1
                ? 'grid-cols-1 max-w-lg mx-auto'
                : usedFormats.length > 0
                ? 'grid-cols-1 sm:grid-cols-2'   // multi-format: each card shows natural ratio
                : 'grid-cols-1 sm:grid-cols-2'
            }`}>
              {results.map((result, idx) => (
                <CompositeImageCard
                  key={result.imageId}
                  imageUrl={getImageUrl(result.imageId)}
                  logoDataUrl={overlayConfig.logoDataUrl || null}
                  logoFileName={overlayConfig.logoFileName}
                  logoBgColor={overlayConfig.logoBgColor}
                  badgeText={overlayConfig.badgeText}
                  ctaText={overlayConfig.ctaText}
                  alt={`Generated from: ${result.generatedPrompt.slice(0, 100)}`}
                  seed={result.seed}
                  formatLabel={usedFormats[idx] ? FORMAT_LABELS[usedFormats[idx]] : undefined}
                  sourceFormatId={usedFormats[idx] ?? undefined}
                  allImages={results.map((r, i) => ({
                    formatId: usedFormats[i] ?? 'square',
                    imageUrl: getImageUrl(r.imageId),
                  }))}
                />
              ))}
            </div>
          </div>

          {previousPrompt && previousPrompt !== generatedPrompt && (
            <div className="surface rounded-xl p-5">
              <PromptDiffView currentText={generatedPrompt} previousText={previousPrompt} />
            </div>
          )}

          <div className="surface rounded-xl p-5">
            <PromptEditor
              initialPrompt={generatedPrompt}
              promptVersionId={currentVersionId}
              onSave={handleSave}
              onRegenerate={handleRegenerate}
              isSaving={isSaving}
              isRegenerating={regenerateMutation.isPending}
            />
          </div>
        </div>
      )}
    </div>
  );
}
