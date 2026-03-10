import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '@shared/components';
import { Table, Column } from '@shared/components/Table';
import type { AnalystNews } from '../types/blMainTypes';
import { newsService } from '../services/blMainService';
import './AnalystSuggestions.css';

interface AnalystSuggestionsProps {
  suggestions?: any[];        // kept for backward compatibility, unused
  onViewAdded?: () => void;   // callback to refresh ActiveViews after adding
}

export const AnalystSuggestions: React.FC<AnalystSuggestionsProps> = ({ onViewAdded }) => {
  const [allNews, setAllNews] = useState<AnalystNews[]>([]);
  const [filteredNews, setFilteredNews] = useState<AnalystNews[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loadingFetch, setLoadingFetch] = useState(false);
  const [addingId, setAddingId] = useState<string | null>(null);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // ── Load cached news on mount ─────────────────────────────────────────────
  const loadNews = useCallback(async () => {
    const items = await newsService.getNews();
    setAllNews(items);
    setFilteredNews(items);
  }, []);

  useEffect(() => { loadNews(); }, [loadNews]);

  // ── Refresh from NewsAPI + view_parser ───────────────────────────────────
  const handleRefresh = async () => {
    setLoadingFetch(true);
    setError(null);
    try {
      const items = await newsService.fetchNews();
      setAllNews(items);
      setFilteredNews(items);
      setSearchTerm('');
    } catch (e) {
      setError('Failed to fetch news. Check the backend is running.');
    } finally {
      setLoadingFetch(false);
    }
  };

  // ── Search / filter ──────────────────────────────────────────────────────
  const handleSearch = () => {
    if (!searchTerm.trim()) {
      setFilteredNews(allNews);
      return;
    }
    const term = searchTerm.toLowerCase();
    setFilteredNews(
      allNews.filter(
        (n) =>
          n.heading.toLowerCase().includes(term) ||
          n.translatedView.toLowerCase().includes(term) ||
          (n.ticker ?? '').toLowerCase().includes(term),
      ),
    );
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch();
  };

  // ── Add to Active Views (bl_llm_parser round-trip) ───────────────────────
  const handleAddToActiveViews = async (news: AnalystNews) => {
    setAddingId(news.id);
    setError(null);
    try {
      await newsService.addNewsView(news.id);
      setAddedIds((prev) => new Set(prev).add(news.id));
      onViewAdded?.();
    } catch {
      setError(`Failed to add view for "${news.heading}".`);
    } finally {
      setAddingId(null);
    }
  };

  // ── Columns ──────────────────────────────────────────────────────────────
  const columns: Column<AnalystNews>[] = [
    {
      key: 'heading',
      header: 'Heading',
      render: (n) => (
        <span className="news-heading">
          {n.ticker && <span className="news-ticker">{n.ticker}</span>}
          {n.heading}
        </span>
      ),
    },
    {
      key: 'translatedView',
      header: 'Translated View',
      render: (n) => <span className="translated-view">{n.translatedView}</span>,
    },
    {
      key: 'link',
      header: 'Link',
      width: '60px',
      render: (n) => (
        <a href={n.link} target="_blank" rel="noopener noreferrer" className="news-link">
          Open
        </a>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '150px',
      render: (n) => (
        <button
          className={`add-view-btn${addedIds.has(n.id) ? ' added' : ''}`}
          onClick={() => handleAddToActiveViews(n)}
          disabled={addingId === n.id || addedIds.has(n.id)}
        >
          {addingId === n.id ? 'Adding…' : addedIds.has(n.id) ? '✓ Added' : '+ Active Views'}
        </button>
      ),
    },
  ];

  return (
    <Card title="Analyst Suggestions">
      <div className="analyst-suggestions-container">
        {/* Controls */}
        <div className="search-section">
          <input
            type="text"
            className="search-input"
            placeholder="Filter by keyword or ticker…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyPress={handleKeyPress}
          />
          <button className="search-btn" onClick={handleSearch}>
            Search
          </button>
          <button
            className="refresh-btn"
            onClick={handleRefresh}
            disabled={loadingFetch}
          >
            {loadingFetch ? 'Fetching…' : 'Refresh News'}
          </button>
        </div>

        {error && <div className="news-error">{error}</div>}

        {/* Table */}
        <div className="news-table-container">
          {filteredNews.length === 0 ? (
            <div className="no-results">
              {allNews.length === 0
                ? 'No news loaded. Click "Refresh News" to fetch the latest articles.'
                : `No news items found matching "${searchTerm}"`}
            </div>
          ) : (
            <Table data={filteredNews} columns={columns} />
          )}
        </div>
      </div>
    </Card>
  );
};

