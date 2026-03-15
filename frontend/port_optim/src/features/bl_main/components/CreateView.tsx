import React from 'react';
import { Card, Button } from '@shared/components';
import './CreateView.css';

interface CreateViewProps {
  parseView: (text: string) => Promise<void>;
  parseViewLoading: boolean;
  value: string;
  onChange: (v: string) => void;
}

export const CreateView: React.FC<CreateViewProps> = ({ parseView, parseViewLoading, value, onChange }) => {

  const handleCreate = async () => {
    if (!value.trim()) return;
    await parseView(value);
    onChange('');
  };

  return (
    <Card title="Create New View">
      <div className="create-view-form">
        <div className="form-row">
          <label className="form-label">View Input</label>
          <textarea
            className="form-textarea"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="AAPL will beat MSFT by 2%. Growth prospects are strong."
            rows={7}
          />
        </div>

        <Button variant="secondary" onClick={handleCreate} className="create-btn" disabled={parseViewLoading}>
          {parseViewLoading ? 'Parsing...' : 'Add View'}
        </Button>
      </div>
    </Card>
  );
};
