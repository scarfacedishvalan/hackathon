import React, { useState, useEffect, useRef } from 'react';
import './SaveThesisModal.css';

interface SaveThesisModalProps {
  onSave: (name: string) => Promise<string>;
  onClose: () => void;
  saving: boolean;
}

/** Mirrors the backend sanitisation: lowercase, runs of non-alnum → '_' */
function toFileName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '');
}

export const SaveThesisModal: React.FC<SaveThesisModalProps> = ({ onSave, onClose, saving }) => {
  const [name, setName] = useState('');
  const [savedAs, setSavedAs] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const filePreview = toFileName(name) || '…';

  const handleSave = async () => {
    if (!name.trim()) { setError('Please enter a thesis name.'); return; }
    setError(null);
    try {
      const saved = await onSave(name.trim());
      setSavedAs(saved);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed — please try again.');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
  };

  return (
    <div className="thesis-overlay" onClick={onClose}>
      <div className="thesis-modal" onClick={e => e.stopPropagation()}>

        {savedAs ? (
          /* ── Success state ── */
          <div className="thesis-success">
            <div className="thesis-success-icon">✓</div>
            <h2 className="thesis-title">Thesis Saved!</h2>
            <p className="thesis-saved-path">
              Saved as <code>{savedAs}.json</code>
            </p>
            <button className="thesis-btn thesis-btn-close" onClick={onClose}>
              Close
            </button>
          </div>
        ) : (
          /* ── Input state ── */
          <>
            <div className="thesis-header">
              <div className="thesis-header-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M4 3h8l4 4v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"
                    stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" fill="none"/>
                  <path d="M12 3v5h5M7 10h6M7 13h4"
                    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </div>
              <h2 className="thesis-title">Save Thesis</h2>
              <button className="thesis-close-x" onClick={onClose}>✕</button>
            </div>

            <p className="thesis-subtitle">
              A snapshot of the current views, universe, and model parameters will be saved permanently.
            </p>

            <label className="thesis-label" htmlFor="thesis-name-input">
              Thesis name
            </label>
            <input
              id="thesis-name-input"
              ref={inputRef}
              className={`thesis-input${error ? ' thesis-input-error' : ''}`}
              type="text"
              placeholder="e.g. Q2 Tech Alpha Tilt"
              value={name}
              onChange={e => { setName(e.target.value); setError(null); }}
              onKeyDown={handleKeyDown}
              maxLength={80}
              disabled={saving}
            />

            {error && <p className="thesis-error">{error}</p>}

            <div className="thesis-preview">
              <span className="thesis-preview-label">File name preview:</span>
              <code className="thesis-preview-value">{filePreview}.json</code>
            </div>

            <div className="thesis-actions">
              <button className="thesis-btn thesis-btn-cancel" onClick={onClose} disabled={saving}>
                Cancel
              </button>
              <button
                className="thesis-btn thesis-btn-save"
                onClick={handleSave}
                disabled={saving || !name.trim()}
              >
                {saving ? 'Saving…' : '+ Save Thesis'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
