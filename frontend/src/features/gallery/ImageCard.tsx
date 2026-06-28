import { useState, useCallback } from 'react';
import { useDeleteImage } from '@/hooks/useGallery';
import { useRegenerateImage } from '@/hooks/useGenerateImage';
import type { GalleryImage } from '@/types';

interface ImageCardProps {
  image: GalleryImage;
}

function ZoomIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function SpinnerIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export function ImageCard({ image }: ImageCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showFullSize, setShowFullSize] = useState(false);

  const deleteMutation = useDeleteImage();
  const regenerateMutation = useRegenerateImage();

  const handleDelete = useCallback(() => {
    deleteMutation.mutate(image.id, {
      onSuccess: () => setShowDeleteConfirm(false),
    });
  }, [image.id, deleteMutation]);

  const handleRegenerate = useCallback(() => {
    regenerateMutation.mutate({ imageId: image.id });
  }, [image.id, regenerateMutation]);

  const formattedDate = new Date(image.createdAt).toLocaleDateString();

  return (
    <>
      <article className="rounded-xl overflow-hidden border border-white/5 bg-surface group">
        {/* Image */}
        <div className="aspect-square bg-surface-2 relative overflow-hidden">
          <img
            src={image.url}
            alt={image.prompt || 'Generated image'}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
            width={512}
            height={512}
          />

          {/* Hover overlay — metadata */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-200 p-3 flex flex-col justify-end">
            <dl className="text-xs text-slate-300 space-y-0.5 font-mono">
              <div className="flex gap-1"><dt className="text-slate-500">Seed</dt><dd>{image.seed}</dd></div>
              <div className="flex gap-1"><dt className="text-slate-500">Model</dt><dd className="truncate">{image.modelName}</dd></div>
              <div className="flex gap-1"><dt className="text-slate-500">Size</dt><dd>{image.width}×{image.height}</dd></div>
            </dl>
          </div>
        </div>

        {/* Footer */}
        <div className="px-3 py-2.5 flex items-center justify-between gap-2">
          <p className="text-xs text-slate-500 truncate flex-1 min-w-0" title={image.prompt || formattedDate}>
            {image.prompt ? image.prompt.slice(0, 40) + (image.prompt.length > 40 ? '…' : '') : formattedDate}
          </p>

          <div className="flex gap-0.5 shrink-0">
            <button
              onClick={() => setShowFullSize(true)}
              className="p-1.5 text-slate-600 hover:text-brand-400 rounded-lg hover:bg-brand-600/10 transition-all duration-150 cursor-pointer min-w-[32px] min-h-[32px] flex items-center justify-center"
              aria-label="View full size"
              title="View full size"
            >
              <ZoomIcon />
            </button>
            <button
              onClick={handleRegenerate}
              disabled={regenerateMutation.isPending}
              className="p-1.5 text-slate-600 hover:text-emerald-400 rounded-lg hover:bg-emerald-600/10 transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed min-w-[32px] min-h-[32px] flex items-center justify-center"
              aria-label="Regenerate image"
              title="Regenerate"
            >
              {regenerateMutation.isPending ? <SpinnerIcon className="w-4 h-4" /> : <RefreshIcon />}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="p-1.5 text-slate-600 hover:text-red-400 rounded-lg hover:bg-red-600/10 transition-all duration-150 cursor-pointer min-w-[32px] min-h-[32px] flex items-center justify-center"
              aria-label="Delete image"
              title="Delete"
            >
              <TrashIcon />
            </button>
          </div>
        </div>
      </article>

      {/* Delete confirmation dialog */}
      {showDeleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-dialog-title"
          onClick={(e) => { if (e.target === e.currentTarget) setShowDeleteConfirm(false); }}
        >
          <div className="surface rounded-2xl p-6 max-w-sm w-full shadow-2xl glow-violet">
            <h3 id="delete-dialog-title" className="text-base font-semibold text-slate-100">Delete Image</h3>
            <p className="mt-2 text-sm text-slate-400">
              Are you sure you want to delete this image? This action cannot be undone.
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm border border-white/10 rounded-lg text-slate-300 hover:bg-white/5 transition-all duration-150 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-all duration-150 cursor-pointer disabled:opacity-50 font-medium flex items-center gap-2"
              >
                {deleteMutation.isPending && <SpinnerIcon />}
                {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Full size modal */}
      {showFullSize && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Full size image"
          onClick={() => setShowFullSize(false)}
          onKeyDown={(e) => e.key === 'Escape' && setShowFullSize(false)}
          tabIndex={-1}
        >
          <div className="relative max-w-[90vw] max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
            <img
              src={image.url}
              alt={image.prompt || 'Generated image full size'}
              className="max-w-full max-h-[90vh] object-contain rounded-xl"
            />
            <button
              onClick={() => setShowFullSize(false)}
              className="absolute top-3 right-3 p-2 bg-black/60 text-white rounded-full hover:bg-black/80 transition-colors cursor-pointer backdrop-blur-sm"
              aria-label="Close full size view"
            >
              <XIcon />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
