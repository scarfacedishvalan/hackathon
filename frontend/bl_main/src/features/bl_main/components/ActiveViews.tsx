import React from 'react';
import { Card } from '@shared/components';
import { Table, Column } from '@shared/components/Table';
import type { ActiveView } from '../types/blMainTypes';

interface ActiveViewsProps {
  views: ActiveView[];
}

export const ActiveViews: React.FC<ActiveViewsProps> = ({ views }) => {
  const columns: Column<ActiveView>[] = [
    {
      key: 'type',
      header: 'Type',
      width: '100px',
      render: (view) => (
        <span className="view-type">{view.type}</span>
      ),
    },
    {
      key: 'asset',
      header: 'Asset/Factor',
    },
    {
      key: 'value',
      header: 'Value',
      width: '100px',
      render: (view) => view.value ? `${(view.value * 100).toFixed(2)}%` : '-',
    },
    {
      key: 'direction',
      header: 'Direction',
      width: '100px',
      render: (view) => (
        <span className={`direction direction-${view.direction}`}>
          {view.direction}
        </span>
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      width: '100px',
      render: (view) => `${(view.confidence * 100).toFixed(0)}%`,
    },
    {
      key: 'actions',
      header: '',
      width: '60px',
      render: () => (
        <button
          className="remove-btn"
          onClick={() => console.log('Remove view')}
        >
          ×
        </button>
      ),
    },
  ];

  return (
    <Card title="Active Views">
      {views.length === 0 ? (
        <div style={{ color: '#9ca3af', fontStyle: 'italic' }}>
          No active views. Create a view above.
        </div>
      ) : (
        <Table data={views} columns={columns} />
      )}
      <style>{`
        .view-type {
          text-transform: capitalize;
          font-size: 13px;
          color: #6b7280;
        }
        .direction {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          text-transform: capitalize;
        }
        .direction-positive {
          background: #d1fae5;
          color: #065f46;
        }
        .direction-negative {
          background: #fee2e2;
          color: #991b1b;
        }
        .direction-neutral {
          background: #e5e7eb;
          color: #374151;
        }
        .remove-btn {
          background: none;
          border: none;
          color: #9ca3af;
          font-size: 24px;
          cursor: pointer;
          padding: 0;
          line-height: 1;
          transition: color 0.2s;
        }
        .remove-btn:hover {
          color: #ef4444;
        }
      `}</style>
    </Card>
  );
};
