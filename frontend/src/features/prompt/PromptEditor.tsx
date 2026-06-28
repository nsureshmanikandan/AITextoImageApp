import { useState, useCallback } from 'react';

const MAX_PROMPT_LENGTH = 5000;

interface PromptEditorProps {
  initialPrompt: string;
  promptVersionId: string;
  onSave: (editedText: string, promptVersionId: string) => void;
  onRegenerate: (editedPrompt: string) => void;
  isSaving?: boolean;
  isRegenerating?: boolean;
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export function PromptEditor({
  initialPrompt,
  promptVersionId,
  onSave,
  onRegenerate,
  isSaving = false,
  isRegenerating = false,
}: PromptEditorProps) {
  const [text, setText] = useState(initialPrompt);
  const [hasChanges, setHasChanges] = useState(false);

  const handleChange = useCallback((value: string) => {
    setText(value);
    setHasChanges(value !== initialPrompt);
  }, [initialPrompt]);

  const handleSave = useCallback(() => {
    if (!text.trim() || text.length > MAX_PROMPT_LENGTH) return;
    onSave(text.trim(), promptVersionId);
    setHasChanges(false);
  }, [text, promptVersionId, onSave]);

  const handleRegenerate = useCallback(() => {
    if (!text.trim() || text.length > MAX_PROMPT_LENGTH) return;
    onRegenerate(text.trim());
  }, [text, onRegenerate]);

  const charCount = text.length;
  const isOverLimit = charCount > MAX_PROMPT_LENGTH;
  const isDisabled = isSaving || isRegenerating;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label htmlFor="prompt-editor" className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
          Generated Prompt
        </label>
        {hasChanges && (
          <span className="text-xs text-amber-400 font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
            Unsaved changes
          </span>
        )}
      </div>

      <textarea
        id="prompt-editor"
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        rows={6}
        disabled={isDisabled}
        aria-describedby="editor-char-count"
        aria-invalid={isOverLimit}
        className={`w-full px-4 py-3 bg-surface-2 border rounded-lg resize-none text-slate-200 text-sm leading-relaxed transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent ${
          isOverLimit ? 'border-red-500/60' : 'border-white/8 hover:border-white/15'
        }`}
      />

      <div className="flex items-center justify-between">
        <span
          id="editor-char-count"
          className={`text-xs tabular-nums ${isOverLimit ? 'text-red-400 font-semibold' : 'text-slate-600'}`}
        >
          {charCount.toLocaleString()} / {MAX_PROMPT_LENGTH.toLocaleString()}
        </span>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={isDisabled || !hasChanges || !text.trim() || isOverLimit}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm border border-white/10 rounded-lg text-slate-300 hover:bg-white/5 hover:text-slate-100 transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {isSaving && <SpinnerIcon />}
            {isSaving ? 'Saving…' : 'Save Version'}
          </button>
          <button
            type="button"
            onClick={handleRegenerate}
            disabled={isDisabled || !text.trim() || isOverLimit}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer font-medium"
          >
            {isRegenerating && <SpinnerIcon />}
            {isRegenerating ? 'Regenerating…' : 'Regenerate'}
          </button>
        </div>
      </div>
    </div>
  );
}
