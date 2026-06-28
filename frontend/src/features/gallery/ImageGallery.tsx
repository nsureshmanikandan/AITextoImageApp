import { useState, useCallback } from 'react';
import { useGallery } from '@/hooks/useGallery';
import { ImageGrid } from './ImageGrid';
import type { GalleryFilters } from '@/types';

function SearchIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

export function ImageGallery() {
  const [filters, setFilters] = useState<GalleryFilters>({ page: 1, pageSize: 12 });
  const [searchInput, setSearchInput] = useState('');

  const { data, isLoading, isError } = useGallery(filters);

  const handleSearch = useCallback(() => {
    setFilters((prev) => ({ ...prev, page: 1, search: searchInput || undefined }));
  }, [searchInput]);

  const handleDateFromChange = useCallback((value: string) => {
    setFilters((prev) => ({ ...prev, page: 1, dateFrom: value || undefined }));
  }, []);

  const handleDateToChange = useCallback((value: string) => {
    setFilters((prev) => ({ ...prev, page: 1, dateTo: value || undefined }));
  }, []);

  const totalPages = data ? Math.ceil(data.total / (filters.pageSize || 12)) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold gradient-brand text-glow">Gallery</h2>
        <p className="text-sm text-slate-500 mt-1">Browse your generated images</p>
      </div>

      {/* Filters */}
      <div className="surface rounded-xl p-4 flex flex-wrap gap-3 items-end">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <label htmlFor="gallery-search" className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
            Search
          </label>
          <div className="flex gap-2">
            <input
              id="gallery-search"
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search by prompt…"
              className="flex-1 px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent hover:border-white/15 transition-colors"
            />
            <button
              onClick={handleSearch}
              aria-label="Search gallery"
              className="px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-slate-400 hover:text-slate-200 hover:border-white/20 focus:outline-none focus:ring-2 focus:ring-brand-500 transition-all duration-150 cursor-pointer"
            >
              <SearchIcon />
            </button>
          </div>
        </div>

        {/* Date From */}
        <div>
          <label htmlFor="gallery-date-from" className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
            From
          </label>
          <input
            id="gallery-date-from"
            type="date"
            value={filters.dateFrom || ''}
            onChange={(e) => handleDateFromChange(e.target.value)}
            className="px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent hover:border-white/15 transition-colors [color-scheme:dark]"
          />
        </div>

        {/* Date To */}
        <div>
          <label htmlFor="gallery-date-to" className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
            To
          </label>
          <input
            id="gallery-date-to"
            type="date"
            value={filters.dateTo || ''}
            onChange={(e) => handleDateToChange(e.target.value)}
            className="px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent hover:border-white/15 transition-colors [color-scheme:dark]"
          />
        </div>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4" role="status" aria-label="Loading gallery">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="aspect-square rounded-xl skeleton" />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-16 text-red-400" role="alert">
          <p className="font-medium">Failed to load gallery.</p>
          <p className="text-sm text-red-400/70 mt-1">Please try refreshing the page.</p>
        </div>
      )}

      {/* Empty state */}
      {data && data.items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand-600/10 border border-brand-600/20 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="9" cy="9" r="2" />
              <path d="M21 15l-5-5L5 21" />
            </svg>
          </div>
          <p className="text-slate-300 font-medium">No images yet</p>
          <p className="text-slate-600 text-sm mt-1">Generate some images to see them here.</p>
        </div>
      )}

      {/* Grid */}
      {data && data.items.length > 0 && <ImageGrid images={data.items} />}

      {/* Pagination */}
      {totalPages > 1 && (
        <nav className="flex justify-center items-center gap-2" aria-label="Gallery pagination">
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
