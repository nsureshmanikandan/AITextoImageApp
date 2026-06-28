import { useState, useCallback } from 'react';
import { useHistory } from '@/hooks/useHistory';
import type { HistoryFilters, PromptHistoryItem } from '@/types';

interface PromptHistoryProps {
  onSelectPrompt?: (item: PromptHistoryItem) => void;
}

function SearchIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin h-6 w-6 text-brand-500" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export function PromptHistory({ onSelectPrompt }: PromptHistoryProps) {
  const [filters, setFilters] = useState<HistoryFilters>({ page: 1, pageSize: 20 });
  const [searchInput, setSearchInput] = useState('');
  const { data, isLoading, isError } = useHistory(filters);

  const handleSearch = useCallback(() => {
    setFilters((prev) => ({ ...prev, page: 1, search: searchInput || undefined }));
  }, [searchInput]);

  const totalPages = data ? Math.ceil(data.total / (filters.pageSize || 20)) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold gradient-brand text-glow">Prompt History</h2>
        <p className="text-sm text-slate-500 mt-1">Browse and reuse your past prompts</p>
      </div>

      {/* Filters */}
      <div className="surface rounded-xl p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label htmlFor="history-search" className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
            Search prompts
          </label>
          <div className="flex gap-2">
            <input
              id="history-search"
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search by prompt text…"
              className="flex-1 px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent hover:border-white/15 transition-colors"
            />
            <button
              onClick={handleSearch}
              aria-label="Search history"
              className="px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-slate-400 hover:text-slate-200 hover:border-white/20 transition-all duration-150 cursor-pointer"
            >
              <SearchIcon />
            </button>
          </div>
        </div>
        <div>
          <label htmlFor="history-date-from" className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">From</label>
          <input id="history-date-from" type="date"
            value={filters.dateFrom || ''}
            onChange={(e) => setFilters((p) => ({ ...p, page: 1, dateFrom: e.target.value || undefined }))}
            className="px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 hover:border-white/15 transition-colors [color-scheme:dark]"
          />
        </div>
        <div>
          <label htmlFor="history-date-to" className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">To</label>
          <input id="history-date-to" type="date"
            value={filters.dateTo || ''}
            onChange={(e) => setFilters((p) => ({ ...p, page: 1, dateTo: e.target.value || undefined }))}
            className="px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 hover:border-white/15 transition-colors [color-scheme:dark]"
          />
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-16" role="status" aria-label="Loading history">
          <SpinnerIcon />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-16 text-red-400" role="alert">
          <p className="font-medium">Failed to load history.</p>
          <p className="text-sm text-red-400/70 mt-1">Please try again.</p>
        </div>
      )}

      {/* Empty */}
      {data && data.items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand-600/10 border border-brand-600/20 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /><path d="M12 7v5l4 2" />
            </svg>
          </div>
          <p className="text-slate-300 font-medium">No history yet</p>
          <p className="text-slate-600 text-sm mt-1">Start generating images to build your history.</p>
        </div>
      )}

      {/* List */}
      {data && data.items.length > 0 && (
        <ul className="space-y-2" role="list">
          {data.items.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => onSelectPrompt?.(item)}
                className="w-full text-left p-4 surface rounded-xl hover:border-brand-600/40 hover:bg-brand-600/5 transition-all duration-150 cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <div className="flex justify-between items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200 line-clamp-2">{item.userInput}</p>
                    <p className="text-xs text-slate-600 mt-1.5 tabular-nums">
                      {new Date(item.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <span className="text-xs text-slate-600 whitespace-nowrap bg-surface-2 px-2 py-0.5 rounded-full">
                    {item.versionCount}v
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <nav className="flex justify-center items-center gap-2" aria-label="History pagination">
          <button
            onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page || 1) - 1 }))}
            disabled={!filters.page || filters.page <= 1}
            className="px-4 py-2 text-sm border border-white/10 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150 cursor-pointer"
          >
            ← Previous
          </button>
          <span className="text-sm text-slate-500 tabular-nums px-2">
            {filters.page || 1} / {totalPages}
          </span>
          <button
            onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page || 1) + 1 }))}
            disabled={(filters.page || 1) >= totalPages}
            className="px-4 py-2 text-sm border border-white/10 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150 cursor-pointer"
          >
            Next →
          </button>
        </nav>
      )}
    </div>
  );
}
