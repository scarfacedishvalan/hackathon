import React, { useState, useEffect } from 'react';
import { CalculationStep } from '../types/blMainTypes';
import './BLCalculationSteps.css';

// Extend Window interface for MathJax
declare global {
  interface Window {
    MathJax?: {
      typesetPromise?: () => Promise<void>;
    };
  }
}

interface BLCalculationStepsProps {
  steps: CalculationStep[];
}

const BLCalculationSteps: React.FC<BLCalculationStepsProps> = ({ steps }) => {
  const [mainExpanded, setMainExpanded] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set());

  useEffect(() => {
    // Typeset math when component mounts or when steps/expansion changes
    if (mainExpanded && window.MathJax) {
      window.MathJax.typesetPromise?.().catch((err: any) => {
        console.error('MathJax typesetting failed:', err);
      });
    }
  }, [mainExpanded, expandedSections, steps]);

  const toggleMain = () => {
    setMainExpanded(!mainExpanded);
    if (!mainExpanded) {
      // When expanding main, collapse all sections
      setExpandedSections(new Set());
    }
  };

  const toggleSection = (index: number) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSections(newExpanded);
  };

  if (!steps || steps.length === 0) {
    return null;
  }

  return (
    <div className="bl-calculation-steps">
      <button 
        className="bl-calc-main-toggle"
        onClick={toggleMain}
        aria-expanded={mainExpanded}
      >
        <span className="bl-calc-toggle-icon">
          {mainExpanded ? '▼' : '▶'}
        </span>
        <span className="bl-calc-main-title">
          Black–Litterman Computation Steps
        </span>
      </button>

      {mainExpanded && (
        <div className="bl-calc-content">
          {steps.map((step, index) => (
            <div key={index} className="bl-calc-section">
              <button
                className="bl-calc-section-toggle"
                onClick={() => toggleSection(index)}
                aria-expanded={expandedSections.has(index)}
              >
                <span className="bl-calc-toggle-icon">
                  {expandedSections.has(index) ? '▼' : '▶'}
                </span>
                <span className="bl-calc-section-title">
                  {step.title}
                </span>
              </button>

              {expandedSections.has(index) && (
                <div className="bl-calc-latex-content">
                  {step.latex}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BLCalculationSteps;
