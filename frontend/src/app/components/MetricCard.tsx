import React from 'react';

interface MetricCardProps {
  label: string;
  value: string;
}

export function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="border border-slate-200 rounded-md p-4 bg-white">
      <div className="text-sm text-slate-600 mb-1">{label}</div>
      <div className="text-2xl text-slate-900 font-semibold">{value}</div>
    </div>
  );
}
