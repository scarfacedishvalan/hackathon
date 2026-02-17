import React, { useState } from 'react';
import { Card, Button } from '@shared/components';
import './CreateView.css';

export const CreateView: React.FC = () => {
  const [assetInput, setAssetInput] = useState('');

  const handleCreate = () => {
    console.log('Creating view:', { assetInput });
    // In production, this would call a callback to add the view
    setAssetInput('');
  };

  const copyToInput = (text: string) => {
    setAssetInput(text);
  };

  const assetViewExamples = [
    "AAPL will outperform MSFT by 3% over the next quarter. Strong iPhone sales expected.",
    "TSLA expected to underperform SP500 by 5%. Delivery concerns and competition increasing."
  ];

  const factorViewExamples = [
    "Technology sector will outperform by 4%. AI adoption driving growth across the sector.",
    "Energy sector expected to decline by 2%. Renewable transition pressuring traditional energy."
  ];

  return (
    <Card title="Create New View">
      <div className="create-view-form">
        <div className="form-row">
          <label className="form-label">View Input</label>
          <textarea
            className="form-textarea"
            value={assetInput}
            onChange={(e) => setAssetInput(e.target.value)}
            placeholder="AAPL will beat MSFT by 2%. Growth prospects are strong."
            rows={4}
          />
        </div>

        <Button variant="secondary" onClick={handleCreate} className="create-btn">
          Add View
        </Button>

        <div className="examples-section">
          <div className="examples-category">
            <h4 className="examples-title">Asset Views</h4>
            {assetViewExamples.map((example, idx) => (
              <div key={idx} className="example-item">
                <p className="example-text">{example}</p>
                <button 
                  className="copy-btn" 
                  onClick={() => copyToInput(example)}
                  title="Copy to input"
                >
                  📋
                </button>
              </div>
            ))}
          </div>

          <div className="examples-category">
            <h4 className="examples-title">Factor Views</h4>
            {factorViewExamples.map((example, idx) => (
              <div key={idx} className="example-item">
                <p className="example-text">{example}</p>
                <button 
                  className="copy-btn" 
                  onClick={() => copyToInput(example)}
                  title="Copy to input"
                >
                  📋
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
};
