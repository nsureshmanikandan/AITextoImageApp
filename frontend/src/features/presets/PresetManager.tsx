import { useState, useCallback } from 'react';
import { usePresets, useCreatePreset, useUpdatePreset, useDeletePreset } from '@/hooks/usePresets';
import type { Preset, CreatePresetParams } from '@/types';

const MAX_PRESETS = 20;
const EMPTY_FORM: CreatePresetParams = { name: '', style: '', lighting: '', composition: '', quality: '', negativePrompt: '' };

function inputCls(extra = '') {
  return `w-full px-3 py-2 bg-surface-2 border border-white/8 rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent hover:border-white/15 transition-colors ${extra}`;
}

function PlusIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
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

const TAG_COLORS: Record<string, string> = {
  style:       'bg-brand-600/15 text-brand-300 ring-1 ring-brand-600/20',
  lighting:    'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/20',
  composition: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/20',
  quality:     'bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/20',
};

export function PresetManager() {
  const { data: presets, isLoading, isError } = usePresets();
  const createMutation = useCreatePreset();
  const updateMutation = useUpdatePreset();
  const deleteMutation = useDeletePreset();

  const [showForm, setShowForm] = useState(false);
  const [editingPreset, setEditingPreset] = useState<Preset | null>(null);
  const [form, setForm] = useState<CreatePresetParams>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);

  const presetCount = presets?.length || 0;
  const isAtLimit = presetCount >= MAX_PRESETS;

  const resetForm = useCallback(() => {
    setForm(EMPTY_FORM); setEditingPreset(null); setShowForm(false); setFormError(null);
  }, []);

  const handleEdit = useCallback((preset: Preset) => {
    setEditingPreset(preset);
    setForm({ name: preset.name, style: preset.style || '', lighting: preset.lighting || '', composition: preset.composition || '', quality: preset.quality || '', negativePrompt: preset.negativePrompt || '' });
    setShowForm(true); setFormError(null);
  }, []);

  const handleSubmit = useCallback(() => {
    if (!form.name.trim()) { setFormError('Preset name is required.'); return; }
    if (form.name.length > 100) { setFormError('Preset name must be at most 100 characters.'); return; }
    const params: CreatePresetParams = {
      name: form.name.trim(),
      style: form.style?.trim() || undefined,
      lighting: form.lighting?.trim() || undefined,
      composition: form.composition?.trim() || undefined,
      quality: form.quality?.trim() || undefined,
      negativePrompt: form.negativePrompt?.trim() || undefined,
    };
    if (editingPreset) { updateMutation.mutate({ id: editingPreset.id, params }, { onSuccess: resetForm }); }
    else { createMutation.mutate(params, { onSuccess: resetForm }); }
  }, [form, editingPreset, createMutation, updateMutation, resetForm]);

  const handleDelete = useCallback((id: string) => {
    if (window.confirm('Are you sure you want to delete this preset?')) deleteMutation.mutate(id);
  }, [deleteMutation]);

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold gradient-brand text-glow">Presets</h2>
          <p className="text-sm text-slate-500 mt-1">Manage your generation presets</p>
        </div>
        <span className="text-xs text-slate-600 tabular-nums">{presetCount}/{MAX_PRESETS}</span>
      </div>

      {/* Create button */}
      {!showForm && (
        <button
          onClick={() => { setShowForm(true); setEditingPreset(null); setForm(EMPTY_FORM); }}
          disabled={isAtLimit}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-brand text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          <PlusIcon />
          {isAtLimit ? 'Preset limit reached' : 'Create Preset'}
        </button>
      )}

      {/* Form */}
      {showForm && (
        <div className="surface rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-widest">
            {editingPreset ? 'Edit Preset' : 'New Preset'}
          </h3>

          {formError && (
            <p className="text-sm text-red-400" role="alert">{formError}</p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label htmlFor="preset-name" className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
                Name <span className="text-brand-500">*</span>
              </label>
              <input id="preset-name" type="text" value={form.name}
                onChange={(e) => { setForm({ ...form, name: e.target.value }); setFormError(null); }}
                maxLength={100} placeholder="e.g., Cinematic Portrait"
                className={inputCls()} />
            </div>

            {([['style', 'Style', 'e.g., photorealistic, oil painting'], ['lighting', 'Lighting', 'e.g., golden hour, studio'], ['composition', 'Composition', 'e.g., rule of thirds'], ['quality', 'Quality', 'e.g., 8K, ultra detailed']] as const).map(([field, label, placeholder]) => (
              <div key={field}>
                <label htmlFor={`preset-${field}`} className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">{label}</label>
                <input id={`preset-${field}`} type="text" value={(form[field as keyof typeof form] as string) || ''}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  placeholder={placeholder} className={inputCls()} />
              </div>
            ))}

            <div className="md:col-span-2">
              <label htmlFor="preset-negative" className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Negative Prompt</label>
              <textarea id="preset-negative" value={form.negativePrompt || ''}
                onChange={(e) => setForm({ ...form, negativePrompt: e.target.value })}
                placeholder="e.g., blurry, low quality, distorted" rows={2}
                className={inputCls('resize-none')} />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-1">
            <button onClick={resetForm} className="px-4 py-2 text-sm border border-white/10 rounded-lg text-slate-300 hover:bg-white/5 transition-all duration-150 cursor-pointer">
              Cancel
            </button>
            <button onClick={handleSubmit} disabled={isSaving}
              className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-all duration-150 cursor-pointer disabled:opacity-50 font-medium flex items-center gap-2">
              {isSaving ? <><svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Saving…</> : editingPreset ? 'Update Preset' : 'Create Preset'}
            </button>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-16" role="status" aria-label="Loading presets"><SpinnerIcon /></div>
      )}

      {isError && (
        <div className="text-center py-16 text-red-400" role="alert">Failed to load presets.</div>
      )}

      {/* Empty */}
      {presets && presets.length === 0 && !showForm && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand-600/10 border border-brand-600/20 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/>
              <circle cx="9" cy="6" r="2" fill="currentColor" stroke="none"/>
              <circle cx="15" cy="12" r="2" fill="currentColor" stroke="none"/>
              <circle cx="9" cy="18" r="2" fill="currentColor" stroke="none"/>
            </svg>
          </div>
          <p className="text-slate-300 font-medium">No presets yet</p>
          <p className="text-slate-600 text-sm mt-1">Create one to save your favorite settings.</p>
        </div>
      )}

      {/* List */}
      {presets && presets.length > 0 && (
        <ul className="space-y-2" role="list">
          {presets.map((preset) => (
            <li key={preset.id} className="surface rounded-xl p-4 flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200">{preset.name}</p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {preset.style && <span className={`text-xs px-2 py-0.5 rounded-full ${TAG_COLORS.style}`}>{preset.style}</span>}
                  {preset.lighting && <span className={`text-xs px-2 py-0.5 rounded-full ${TAG_COLORS.lighting}`}>{preset.lighting}</span>}
                  {preset.composition && <span className={`text-xs px-2 py-0.5 rounded-full ${TAG_COLORS.composition}`}>{preset.composition}</span>}
                  {preset.quality && <span className={`text-xs px-2 py-0.5 rounded-full ${TAG_COLORS.quality}`}>{preset.quality}</span>}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => handleEdit(preset)}
                  className="px-3 py-1.5 text-xs border border-white/10 rounded-lg text-slate-300 hover:bg-white/5 transition-all duration-150 cursor-pointer">
                  Edit
                </button>
                <button onClick={() => handleDelete(preset.id)} disabled={deleteMutation.isPending}
                  className="px-3 py-1.5 text-xs text-red-400 border border-red-500/20 rounded-lg hover:bg-red-600/10 transition-all duration-150 cursor-pointer disabled:opacity-50">
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
