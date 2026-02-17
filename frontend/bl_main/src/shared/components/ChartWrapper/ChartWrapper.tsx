import React, { ReactNode } from 'react';
import './ChartWrapper.css';

interface ChartWrapperProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export const ChartWrapper: React.FC<ChartWrapperProps> = ({
  title,
  children,
  className = '',
}) => {
  return (
    <div className={`chart-wrapper ${className}`}>
      <h3 className="chart-title">{title}</h3>
      <div className="chart-content">{children}</div>
    </div>
  );
};
