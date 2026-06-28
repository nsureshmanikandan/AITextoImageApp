import { useState, useMemo } from 'react';

interface PromptDiffViewProps {
  currentText: string;
  previousText: string;
}

interface DiffSegment {
  type: 'same' | 'added' | 'removed';
  text: string;
}

function computeDiff(oldText: string, newText: string): DiffSegment[] {
  const oldWords = oldText.split(/(\s+)/);
  const newWords = newText.split(/(\s+)/);
  const segments: DiffSegment[] = [];

  // Simple LCS-based word diff
  const m = oldWords.length;
  const n = newWords.length;

  // Build LCS table
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (oldWords[i - 1] === newWords[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to find diff
  let i = m;
  let j = n;
  const result: DiffSegment[] = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldWords[i - 1] === newWords[j - 1]) {
      result.unshift({ type: 'same', text: oldWords[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift({ type: 'added', text: newWords[j - 1] });
      j--;
    } else {
      result.unshift({ type: 'removed', text: oldWords[i - 1] });
      i--;
    }
  }

  // Merge consecutive segments of the same type
  for (const seg of result) {
    const last = segments[segments.length - 1];
    if (last && last.type === seg.type) {
      last.text += seg.text;
    } else {
      segments.push({ ...seg });
    }
  }

  return segments;
}

export function PromptDiffView({ currentText, previousText }: PromptDiffViewProps) {
  const [showDiff, setShowDiff] = useState(true);

  const segments = useMemo(() => computeDiff(previousText, currentText), [previousText, currentText]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Prompt Changes</span>
        <button
          type="button"
          onClick={() => setShowDiff(!showDiff)}
          className="text-xs text-brand-400 hover:text-brand-300 font-medium transition-colors cursor-pointer"
          aria-pressed={showDiff}
        >
          {showDiff ? 'Show plain text' : 'Show diff'}
        </button>
      </div>

      <div className="p-4 border border-white/8 rounded-xl bg-surface-2 text-sm leading-relaxed text-slate-300">
        {showDiff ? (
          <div aria-label="Diff view showing changes between prompt versions">
            {segments.map((segment, idx) => {
              if (segment.type === 'added') {
                return (
                  <span
                    key={idx}
                    className="bg-emerald-500/20 text-emerald-300 rounded px-0.5"
                    aria-label={`Added: ${segment.text}`}
                  >
                    {segment.text}
                  </span>
                );
              }
              if (segment.type === 'removed') {
                return (
                  <span
                    key={idx}
                    className="bg-red-500/20 text-red-300 line-through rounded px-0.5"
                    aria-label={`Removed: ${segment.text}`}
                  >
                    {segment.text}
                  </span>
                );
              }
              return <span key={idx}>{segment.text}</span>;
            })}
          </div>
        ) : (
          <p className="whitespace-pre-wrap">{currentText}</p>
        )}
      </div>

      {showDiff && (
        <div className="flex gap-4 text-xs text-slate-600">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-emerald-500/20 rounded-sm" aria-hidden="true" />
            Added
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-red-500/20 rounded-sm" aria-hidden="true" />
            Removed
          </span>
        </div>
      )}
    </div>
  );
}
