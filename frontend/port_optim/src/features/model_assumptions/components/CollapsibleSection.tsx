import React, { useState } from 'react';
import './CollapsibleSection.css';

interface CollapsibleSectionProps {
  title: string;
  defaultExpanded?: boolean;
  headerExtra?: React.ReactNode;
  children: React.ReactNode;
}

export const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  defaultExpanded = false,
  headerExtra,
  children,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="collapsible-section">
      <div className="collapsible-section-header" onClick={() => setExpanded((p) => !p)}>
        <h3 className="collapsible-section-title">
          {title}
          {headerExtra}
          <span className={`chevron ${expanded ? 'expanded' : ''}`}>▼</span>
        </h3>
      </div>
      {expanded && <div className="collapsible-section-body">{children}</div>}
    </div>
  );
};
