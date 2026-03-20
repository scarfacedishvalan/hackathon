import React, { ReactNode } from 'react';
import './AboutSection.css';

interface AboutSectionProps {
  title: string;
  image?: string;
  children: ReactNode;
}

export const AboutSection: React.FC<AboutSectionProps> = ({ title, image, children }) => {
  return (
    <div className="about-section">
      <h2 className="about-section__title">{title}</h2>
      {image ? (
        <img src={image} alt={title} className="about-section__image" />
      ) : (
        <div className="about-section__image-placeholder">Image Placeholder</div>
      )}
      <div className="about-section__body">{children}</div>
    </div>
  );
};
