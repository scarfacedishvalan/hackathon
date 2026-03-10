import React from 'react';
import { Card } from '@shared/components';
import { Table, Column } from '@shared/components/Table';
import type { BottomUpView, TopDownView } from '../types/blMainTypes';

interface ActiveViewsProps {
  bottomUpViews: BottomUpView[];
  topDownViews: TopDownView[];
  onDeleteBottomUp: (id: string) => void;
  onDeleteTopDown: (id: string) => void;
}

// ── helpers ──────────────────────────────────────────────────────────────────

function ValueBadge({ value }: { value: number }) {
  const pct = `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
  return (
    <span className={`val-badge val-badge--${value >= 0 ? 'pos' : 'neg'}`}>
      {pct}
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
}: {
  views: BottomUpView[];
  onDelete: (id: string) => void;
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
      width: '130px',
      render: (v) => <ValueBadge value={v.value} />,
    },
    {
      key: 'confidence',
      header: 'Confidence',
      width: '100px',
      render: (v) => `${(v.confidence * 100).toFixed(0)}%`,
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
}: {
  views: TopDownView[];
  onDelete: (id: string) => void;
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
      width: '110px',
      render: (v) => <ValueBadge value={v.shock} />,
    },
    {
      key: 'confidence',
      header: 'Confidence',
      width: '100px',
      render: (v) => `${(v.confidence * 100).toFixed(0)}%`,
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
}) => {
  return (
    <>
      <Card title="Bottom-Up Views">
        <BottomUpTable views={bottomUpViews} onDelete={onDeleteBottomUp} />
      </Card>

      <Card title="Top-Down Factor Views">
        <TopDownTable views={topDownViews} onDelete={onDeleteTopDown} />
      </Card>

      <style>{`
        .type-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.4px;
        }
        .type-badge--absolute { background: #dbeafe; color: #1e40af; }
        .type-badge--relative { background: #ede9fe; color: #5b21b6; }

        .val-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
          font-variant-numeric: tabular-nums;
        }
        .val-badge--pos { background: #d1fae5; color: #065f46; }
        .val-badge--neg { background: #fee2e2; color: #991b1b; }

        .factor-name {
          font-weight: 500;
          font-size: 13px;
        }

        .empty-hint {
          color: #9ca3af;
          font-style: italic;
          margin: 0;
          padding: 4px 0;
          font-size: 13px;
        }

        .remove-btn {
          background: none;
          border: none;
          color: #9ca3af;
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

