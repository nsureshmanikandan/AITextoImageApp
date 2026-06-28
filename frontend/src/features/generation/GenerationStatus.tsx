import { useState, useEffect } from 'react';
import { useJobStatus } from '@/hooks/useJobStatus';
import type { JobStatus, ImageResult } from '@/types';

interface GenerationStatusProps {
  jobId: string | null;
  onComplete?: (results: ImageResult[], promptText: string) => void;
  onRetry?: () => void;
}

function WarningIcon() {
  return (
    <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function XCircleIcon() {
  return (
    <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

export function GenerationStatus({ jobId, onComplete, onRetry }: GenerationStatusProps) {
  const { data: jobStatus, isError, error } = useJobStatus(jobId);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [startTime] = useState(() => Date.now());

  useEffect(() => {
    if (!jobId) return;
    const terminal = jobStatus?.status === 'completed' || jobStatus?.status === 'failed' || jobStatus?.status === 'timed_out';
    if (terminal) return;
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [jobId, jobStatus?.status, startTime]);

  useEffect(() => {
    if (jobStatus?.status === 'completed' && jobStatus.results && onComplete) {
      const promptText = jobStatus.results[0]?.generatedPrompt || '';
      onComplete(jobStatus.results, promptText);
    }
  }, [jobStatus?.status, jobStatus?.results, onComplete]);

  if (!jobId) return null;

  if (isError) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/8 p-4" role="alert">
        <div className="flex items-start gap-3">
          <span className="text-red-400 mt-0.5"><WarningIcon /></span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-red-300">Failed to check job status</p>
            <p className="text-xs text-red-400/80 mt-0.5">
              {(error as { message?: string })?.message || 'Please try again.'}
            </p>
          </div>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 px-4 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors duration-150 cursor-pointer font-medium"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  return <StatusDisplay status={jobStatus} elapsedSeconds={elapsedSeconds} onRetry={onRetry} />;
}

function StatusDisplay({
  status,
  elapsedSeconds,
  onRetry,
}: {
  status: JobStatus | undefined;
  elapsedSeconds: number;
  onRetry?: () => void;
}) {
  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return m > 0 ? `${m}m ${rem}s` : `${rem}s`;
  };

  if (!status || status.status === 'queued' || status.status === 'processing') {
    const isProcessing = status?.status === 'processing';
    return (
      <div className="rounded-xl border border-brand-600/20 bg-brand-600/8 p-4" role="status" aria-live="polite">
        <div className="flex items-center gap-3">
          {/* Animated ring */}
          <div className="relative w-8 h-8 shrink-0">
            <svg className="w-8 h-8 animate-spin-slow" viewBox="0 0 36 36" aria-hidden="true">
              <circle cx="18" cy="18" r="14" fill="none" stroke="#7C3AED22" strokeWidth="3" />
              <circle cx="18" cy="18" r="14" fill="none"
                stroke="url(#ring-grad)" strokeWidth="3"
                strokeDasharray="88" strokeDashoffset="66"
                strokeLinecap="round"
              />
              <defs>
                <linearGradient id="ring-grad" x1="0" y1="0" x2="1" y2="0">
                  <stop stopColor="#7C3AED" />
                  <stop offset="1" stopColor="#EC4899" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-brand-300">
              {isProcessing ? 'Generating your image…' : 'Queued — waiting for worker…'}
            </p>
            <p className="text-xs text-slate-500 mt-0.5 tabular-nums">
              Elapsed: {formatTime(elapsedSeconds)}
            </p>
          </div>
        </div>

        {/* Animated gradient progress bar */}
        <div className="mt-3 h-0.5 rounded-full bg-surface-3 overflow-hidden">
          <div
            className="h-full bg-gradient-brand rounded-full"
            style={{
              width: isProcessing ? '70%' : '30%',
              transition: 'width 0.8s ease',
              animation: 'shimmer 2s ease-in-out infinite',
            }}
          />
        </div>
      </div>
    );
  }

  if (status.status === 'failed' || status.status === 'timed_out') {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/8 p-4" role="alert">
        <div className="flex items-start gap-3">
          <span className="text-red-400 mt-0.5"><XCircleIcon /></span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-red-300">
              {status.status === 'timed_out' ? 'Generation timed out' : 'Generation failed'}
            </p>
            {status.error && (
              <p className="text-xs text-red-400/80 mt-0.5 truncate">{status.error.message}</p>
            )}
          </div>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 px-4 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors duration-150 cursor-pointer font-medium"
          >
            Try Again
          </button>
        )}
      </div>
    );
  }

  return null;
}
