import React from 'react';

interface ProvidersProps {
  children: React.ReactNode;
}

export const Providers: React.FC<ProvidersProps> = ({ children }) => {
  // Future: Add context providers here (theme, auth, etc.)
  return <>{children}</>;
};
