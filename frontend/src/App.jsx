import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import MapMap from './components/MapMap';
import ReportModal from './components/ReportModal';
import AnalyticsModal from './components/AnalyticsModal';
import PodcastModal from './components/PodcastModal';
import axios from 'axios';

import API_BASE_URL from './config';

function App() {
  const [reports, setReports] = useState([]);
  const [news, setNews] = useState([]);
  const [activeCategories, setActiveCategories] = useState(new Set(['Theft', 'Vandalism', 'Accident', 'Fire', 'Suspicious Activity', 'Other', 'Uncategorized']));
  const [viewMode, setViewMode] = useState('density'); // 'density' or 'heatmap'
  const [mapCenter, setMapCenter] = useState([40.5008, -74.4478]);
  const [modals, setModals] = useState({ report: false, analytics: false, podcast: false });
  const [loading, setLoading] = useState({ reports: true, news: false });

  // Theme State - Default to 'dark' for Aura theme
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem('theme') || 'dark';
    }
    return 'dark';
  });

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Fetch Reports
  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    setLoading(prev => ({ ...prev, reports: true }));
    try {
      const res = await axios.get(`${API_BASE_URL}/api/reports`);
      setReports(res.data);
    } catch (err) {
      console.error("Failed to fetch reports", err);
    } finally {
      setLoading(prev => ({ ...prev, reports: false }));
    }
  };

  // Fetch News when map moves (triggered by MapMap component)
  const fetchNews = async (lat, lng) => {
    setLoading(prev => ({ ...prev, news: true }));
    try {
      const res = await axios.get(`${API_BASE_URL}/api/news?lat=${lat}&lon=${lng}`);
      setNews(res.data);
    } catch (err) {
      console.error("Failed to fetch news", err);
    } finally {
      setLoading(prev => ({ ...prev, news: false }));
    }
  };

  const toggleCategory = (category) => {
    const newSet = new Set(activeCategories);
    if (newSet.has(category)) newSet.delete(category);
    else newSet.add(category);
    setActiveCategories(newSet);
  };

  const filteredReports = reports.filter(r => activeCategories.has(r.category));

  const openModal = (name) => setModals(prev => ({ ...prev, [name]: true }));
  const closeModal = (name) => setModals(prev => ({ ...prev, [name]: false }));

  const handleReportSubmit = async (data) => {
    try {
      const res = await axios.post(`${API_BASE_URL}/api/reports`, data);
      setReports(prev => [res.data, ...prev]);
      closeModal('report');
    } catch (err) {
      console.error("Failed to submit report", err);
      alert("Failed to submit report");
    }
  };

  return (
    <div className="h-screen w-screen overflow-hidden relative transition-colors duration-300">
      <MapMap
        reports={filteredReports}
        viewMode={viewMode}
        onMoveEnd={fetchNews}
        setMapCenter={setMapCenter}
        onMapClick={(latlng) => { /* handled in ReportModal context usually, but we can pass it down */ }}
        theme={theme}
      />

      <Navbar
        incidentCount={filteredReports.length}
        viewMode={viewMode}
        setViewMode={setViewMode}
        openModal={openModal}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <Sidebar
        reports={filteredReports}
        news={news}
        activeCategories={activeCategories}
        toggleCategory={toggleCategory}
        loading={loading}
        onFlyTo={(lat, lng) => setMapCenter([lat, lng])} // MapMap needs to listen to this change
      />

      {modals.report && <ReportModal onClose={() => closeModal('report')} onSubmit={handleReportSubmit} mapCenter={mapCenter} />}
      {modals.analytics && <AnalyticsModal onClose={() => closeModal('analytics')} />}
      {modals.podcast && <PodcastModal onClose={() => closeModal('podcast')} />}
    </div>
  );
}

export default App;
