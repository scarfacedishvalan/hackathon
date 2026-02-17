import React, { useState, useEffect } from 'react';
import { Card } from '@shared/components';
import { Table, Column } from '@shared/components/Table';
import type { AnalystNews } from '../types/blMainTypes';
import mockData from '../mock/mockBlMainData.json';
import './AnalystSuggestions.css';

interface AnalystSuggestionsProps {
  suggestions: any[]; // Keep for backward compatibility but not used
}

export const AnalystSuggestions: React.FC<AnalystSuggestionsProps> = () => {
  const allNews: AnalystNews[] = mockData.analystNews || [];
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredNews, setFilteredNews] = useState<AnalystNews[]>(allNews);

  useEffect(() => {
    setFilteredNews(allNews);
  }, []);

  const handleSearch = () => {
    if (!searchTerm.trim()) {
      setFilteredNews(allNews);
      return;
    }

    const term = searchTerm.toLowerCase();
    const filtered = allNews.filter(
      (news) =>
        news.heading.toLowerCase().includes(term) ||
        news.translatedView.toLowerCase().includes(term)
    );
    setFilteredNews(filtered);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleAddToActiveViews = (news: AnalystNews) => {
    console.log('Adding to active views:', news);
    // In production, this would trigger a callback to add the view
  };

  const columns: Column<AnalystNews>[] = [
    {
      key: 'heading',
      header: 'Heading',
      render: (news) => <span className="news-heading">{news.heading}</span>,
    },
    {
      key: 'translatedView',
      header: 'Translated View',
      render: (news) => (
        <span className="translated-view">{news.translatedView}</span>
      ),
    },
    {
      key: 'link',
      header: 'Link',
      width: '80px',
      render: (news) => (
        <a
          href={news.link}
          target="_blank"
          rel="noopener noreferrer"
          className="news-link"
        >
          Open
        </a>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '140px',
      render: (news) => (
        <button
          className="add-view-btn"
          onClick={() => handleAddToActiveViews(news)}
        >
          + Active Views
        </button>
      ),
    },
  ];

  return (
    <Card title="Analyst Suggestions">
      <div className="analyst-suggestions-container">
        <div className="search-section">
          <input
            type="text"
            className="search-input"
            placeholder="Filter news by keyword..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyPress={handleKeyPress}
          />
          <button className="search-btn" onClick={handleSearch}>
            Search
          </button>
        </div>

        <div className="news-table-container">
          {filteredNews.length === 0 ? (
            <div className="no-results">
              No news items found matching "{searchTerm}"
            </div>
          ) : (
            <Table data={filteredNews} columns={columns} />
          )}
        </div>
      </div>
    </Card>
  );
};
