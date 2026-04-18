import React, { useRef, useState } from 'react';
import { Card } from '@shared/components';
import { Table, Column } from '@shared/components/Table';
import type { BottomUpView, TopDownView } from '../types/blMainTypes';

interface ActiveViewsProps {
  bottomUpViews: BottomUpView[];
  topDownViews: TopDownView[];
  onDeleteBottomUp: (id: string) => void;
  onDeleteTopDown: (id: string) => void;
  onUpdateBottomUp: (id: string, fields: { value?: number; confidence?: number }) => void;
  onUpdateTopDown: (id: string, fields: { shock?: number; confidence?: number }) => void;
}

// ── helpers ──────────────────────────────────────────────────────────────────

/**
 * Editable number stepper rendered as a colour-coded badge.
 * Values are stored/emitted in decimal (e.g. 0.08 for 8%).
 * Displays multiplied by `displayFactor` (100 for %).
 * Debounces backend sync by `debounceMs` ms on every change.
 */
function EditableNumber({
  value,
  onChange,
  step = 0.001,
  min = -1,
  max = 5,
  displayFactor = 100,
  suffix = '%',
  debounceMs = 300,
}: {
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
  displayFactor?: number;
  suffix?: string;
  debounceMs?: number;
}) {
  // Local display state so the badge re-colours instantly on step
  const [localVal, setLocalVal] = useState(value);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const localRef = useRef(value);

  const commit = (decimal: number) => {
    const clamped = Math.min(max, Math.max(min, decimal));
    localRef.current = clamped;
    setLocalVal(clamped);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => onChange(clamped), debounceMs);
  };

  const handleStep = (dir: 1 | -1) => commit(localRef.current + dir * step);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = parseFloat(e.target.value);
    if (!isNaN(raw)) {
      // preserve current sign — user edits magnitude only via the text field
      const signed = localRef.current >= 0 ? Math.abs(raw) : -Math.abs(raw);
      commit(signed / displayFactor);
    }
  };

  const isPos = localVal >= 0;
  const sign = isPos ? '+' : '−';
  const displayStr = (Math.abs(localVal) * displayFactor).toFixed(2);

  return (
    <span className={`val-badge val-badge--${isPos ? 'pos' : 'neg'} val-badge--editable`}>
      <span className="step-display">
        <span className="step-sign">{sign}</span>
        <input
          type="number"
          className="editable-num"
          value={displayStr}
          step={(step * displayFactor).toString()}
          min="0"
          max={(Math.max(Math.abs(min), Math.abs(max)) * displayFactor).toString()}
          onChange={handleInputChange}
          style={{ width: `${displayStr.length + 0.3}ch` }}
          aria-label="edit value"
        />
        {suffix}
      </span>
      <span className="step-arrows">
        <button className="step-btn step-btn--up" onClick={() => handleStep(1)} tabIndex={-1} aria-label="increase">
          <svg width="7" height="5" viewBox="0 0 7 5" fill="none"><path d="M3.5 0.5L6.5 4.5H0.5L3.5 0.5Z" fill="currentColor"/></svg>
        </button>
        <button className="step-btn step-btn--down" onClick={() => handleStep(-1)} tabIndex={-1} aria-label="decrease">
          <svg width="7" height="5" viewBox="0 0 7 5" fill="none"><path d="M3.5 4.5L0.5 0.5H6.5L3.5 4.5Z" fill="currentColor"/></svg>
        </button>
      </span>
    </span>
  );
}

function TypeBadge({ type }: { type: 'absolute' | 'relative' }) {
  return <span className={`type-badge type-badge--${type}`}>{type}</span>;
}

function RemoveBtn({ onClick }: { onClick: () => void }) {
  return (
    <button className="remove-btn" onClick={onClick}>×</button>
  );
}

// ── Bottom-up table ───────────────────────────────────────────────────────────

function BottomUpTable({
  views,
  onDelete,
  onUpdate,
}: {
  views: BottomUpView[];
  onDelete: (id: string) => void;
  onUpdate: (id: string, fields: { value?: number; confidence?: number }) => void;
}) {
  const columns: Column<BottomUpView>[] = [
    {
      key: 'type',
      header: 'Type',
      width: '90px',
      render: (v) => <TypeBadge type={v.type} />,
    },
    {
      key: 'asset',
      header: 'Asset',
      render: (v) =>
        v.type === 'relative'
          ? `${v.asset_long ?? '?'} vs ${v.asset_short ?? '?'}`
          : (v.asset ?? '—'),
    },
    {
      key: 'value',
      header: 'Expected Return',
      width: '150px',
      render: (v) => (
        <EditableNumber
          value={v.value}
          step={0.001}
          min={-1}
          max={5}
          onChange={(newVal) => onUpdate(v.id, { value: newVal })}
        />
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      width: '120px',
      render: (v) => (
        <EditableNumber
          value={v.confidence}
          step={0.05}
          min={0}
          max={1}
          onChange={(newVal) => onUpdate(v.id, { confidence: newVal })}
        />
      ),
    },
    {
      key: 'label',
      header: 'Label',
      render: (v) => <span style={{ color: '#6b7280', fontSize: 12 }}>{v.label ?? '—'}</span>,
    },
    {
      key: 'actions',
      header: '',
      width: '44px',
      render: (v) => <RemoveBtn onClick={() => onDelete(v.id)} />,
    },
  ];

  return views.length === 0 ? (
    <p className="empty-hint">No bottom-up views yet.</p>
  ) : (
    <Table data={views} columns={columns} />
  );
}

// ── Top-down table ────────────────────────────────────────────────────────────

function TopDownTable({
  views,
  onDelete,
  onUpdate,
}: {
  views: TopDownView[];
  onDelete: (id: string) => void;
  onUpdate: (id: string, fields: { shock?: number; confidence?: number }) => void;
}) {
  const columns: Column<TopDownView>[] = [
    {
      key: 'factor',
      header: 'Factor',
      render: (v) => <span className="factor-name">{v.factor}</span>,
    },
    {
      key: 'shock',
      header: 'Shock',
      width: '130px',
      render: (v) => (
        <EditableNumber
          value={v.shock}
          step={0.001}
          min={-1}
          max={5}
          onChange={(newVal) => onUpdate(v.id, { shock: newVal })}
        />
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      width: '120px',
      render: (v) => (
        <EditableNumber
          value={v.confidence}
          step={0.05}
          min={0}
          max={1}
          onChange={(newVal) => onUpdate(v.id, { confidence: newVal })}
        />
      ),
    },
    {
      key: 'label',
      header: 'Label',
      render: (v) => <span style={{ color: '#6b7280', fontSize: 12 }}>{v.label ?? '—'}</span>,
    },
    {
      key: 'actions',
      header: '',
      width: '44px',
      render: (v) => <RemoveBtn onClick={() => onDelete(v.id)} />,
    },
  ];

  return views.length === 0 ? (
    <p className="empty-hint">No top-down views yet.</p>
  ) : (
    <Table data={views} columns={columns} />
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export const ActiveViews: React.FC<ActiveViewsProps> = ({
  bottomUpViews,
  topDownViews,
  onDeleteBottomUp,
  onDeleteTopDown,
  onUpdateBottomUp,
  onUpdateTopDown,
}) => {
  return (
    <>
      <div className="active-views-columns">
        <Card title="Bottom-Up Views">
          <BottomUpTable views={bottomUpViews} onDelete={onDeleteBottomUp} onUpdate={onUpdateBottomUp} />
        </Card>

        <Card title="Top-Down Factor Views">
          <TopDownTable views={topDownViews} onDelete={onDeleteTopDown} onUpdate={onUpdateTopDown} />
        </Card>
      </div>

      <style>{`
        .active-views-columns {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          align-items: start;
        }
        @media (max-width: 900px) {
          .active-views-columns {
            grid-template-columns: 1fr;
          }
        }

        /* Uniform header and row heights across both tables */
        .active-views-columns .data-table th {
          height: 44px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          vertical-align: middle;
          box-sizing: border-box;
        }
        .active-views-columns .data-table td {
          height: 48px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          vertical-align: middle;
          box-sizing: border-box;
        }
        /* remove old editable block that was declared before .val-badge */
        /* arrow column: hidden by default, revealed on badge hover */
        .step-arrows {
          display: inline-flex;
          flex-direction: column;
          align-items: center;
          gap: 0px;
          opacity: 0;
          pointer-events: none;
          transition: opacity 0.15s;
          flex-shrink: 0;
        }
        .val-badge--editable:hover .step-arrows {
          opacity: 1;
          pointer-events: auto;
        }
        .step-btn {
          background: transparent;
          border: none;
          color: inherit;
          line-height: 1;
          padding: 0;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 14px;
          height: 9px;
          border-radius: 2px;
          transition: background 0.1s;
        }
        .step-btn:hover { background: rgba(255,255,255,0.15); }
        .step-display {
          display: inline-flex;
          align-items: baseline;
          gap: 0;
          font-weight: 600;
          font-variant-numeric: tabular-nums;
          font-size: 12px;
          line-height: 1;
        }
        .step-sign {
          font-size: 12px;
          font-weight: 600;
          line-height: 1;
          padding-right: 1px;
          flex-shrink: 0;
        }
        .editable-num {
          background: transparent;
          border: none;
          outline: none;
          color: inherit;
          font: inherit;
          font-weight: 600;
          font-variant-numeric: tabular-nums;
          /* width set inline from character count — no fixed width here */
          text-align: left;
          padding: 0;
          line-height: 1;
          -moz-appearance: textfield;
          appearance: textfield;
        }
        .editable-num::-webkit-inner-spin-button,
        .editable-num::-webkit-outer-spin-button {
          display: none;
        }

        .type-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.4px;
        }
        .type-badge--absolute { background: #1e3a8a; color: #93c5fd; }
        .type-badge--relative { background: #4c1d95; color: #c7d2fe; }

        .val-badge {
          display: inline-flex;
          align-items: center;
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
          font-variant-numeric: tabular-nums;
          line-height: 1;
        }
        .val-badge--pos { background: #14532d; color: #86efac; }
        .val-badge--neg { background: #7f1d1d; color: #fca5a5; }
        /* editable overrides — must come AFTER .val-badge to win the cascade */
        .val-badge--editable {
          display: inline-flex;
          align-items: center;
          gap: 3px;
          padding: 3px 5px 3px 7px;
          cursor: default;
          line-height: 1;
        }

        .factor-name {
          font-weight: 500;
          font-size: 13px;
          color: #cbd5e1;
        }

        .empty-hint {
          color: #64748b;
          font-style: italic;
          margin: 0;
          padding: 4px 0;
          font-size: 13px;
        }

        .remove-btn {
          background: none;
          border: none;
          color: #64748b;
          font-size: 22px;
          cursor: pointer;
          padding: 0;
          line-height: 1;
          transition: color 0.15s;
        }
        .remove-btn:hover { color: #ef4444; }
      `}</style>
    </>
  );
};

