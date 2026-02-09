import React, { useState, useRef, useEffect } from 'react';
import { X, ChevronDown } from 'lucide-react';

interface StockSelectorProps {
  selectedStocks: string[];
  onChange: (stocks: string[]) => void;
}

const availableStocks = [
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM',
  'V', 'WMT', 'JNJ', 'PG', 'MA', 'HD', 'DIS', 'BAC', 'NFLX', 'CRM'
];

export function StockSelector({ selectedStocks, onChange }: StockSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  const filteredStocks = availableStocks.filter(
    stock => stock.toLowerCase().includes(searchTerm.toLowerCase())
  );

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearchTerm('');
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleStock = (stock: string) => {
    if (selectedStocks.includes(stock)) {
      onChange(selectedStocks.filter(s => s !== stock));
    } else {
      onChange([...selectedStocks, stock]);
    }
  };

  const removeStock = (stock: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(selectedStocks.filter(s => s !== stock));
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="min-h-[40px] w-full px-3 py-2 border border-slate-300 rounded-md bg-white cursor-pointer hover:border-slate-400 transition-colors"
      >
        {selectedStocks.length === 0 ? (
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-400">AAPL, MSFT, GOOGL…</span>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </div>
        ) : (
          <div className="flex items-center justify-between gap-2">
            <div className="flex flex-wrap gap-1.5">
              {selectedStocks.map(stock => (
                <span
                  key={stock}
                  className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium"
                >
                  {stock}
                  <button
                    onClick={(e) => removeStock(stock, e)}
                    className="hover:bg-blue-200 rounded-full p-0.5"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
          </div>
        )}
      </div>

      {isOpen && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-slate-300 rounded-md shadow-lg max-h-64 overflow-hidden">
          <div className="p-2 border-b border-slate-200">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search stocks..."
              className="w-full px-3 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <div className="overflow-y-auto max-h-52">
            {filteredStocks.map(stock => (
              <div
                key={stock}
                onClick={() => toggleStock(stock)}
                className="px-3 py-2 hover:bg-slate-100 cursor-pointer flex items-center gap-2 text-sm"
              >
                <input
                  type="checkbox"
                  checked={selectedStocks.includes(stock)}
                  onChange={() => {}}
                  className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                />
                <span className="text-slate-900">{stock}</span>
              </div>
            ))}
            {filteredStocks.length === 0 && (
              <div className="px-3 py-4 text-sm text-slate-500 text-center">
                No stocks found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
