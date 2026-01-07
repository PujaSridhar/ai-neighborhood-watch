import React, { useState, useEffect } from 'react';
import { X, BarChart2 } from 'lucide-react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title } from 'chart.js';
import { Doughnut, Line } from 'react-chartjs-2';
import axios from 'axios';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title);

import API_BASE_URL from '../config';
const CATEGORIES = {
    'Theft': '#EF4444',
    'Vandalism': '#F97316',
    'Accident': '#3B82F6',
    'Fire': '#D946EF',
    'Suspicious Activity': '#EAB308',
    'Other': '#6B7280',
    'Uncategorized': '#9CA3AF'
};

const AnalyticsModal = ({ onClose }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchAnalytics = async () => {
            try {
                const res = await axios.get(`${API_BASE_URL}/api/trends`);
                setData(res.data);
            } catch (err) {
                setError("Failed to load analytics");
            } finally {
                setLoading(false);
            }
        };
        fetchAnalytics();
    }, []);

    const doughnutData = data ? {
        labels: Object.keys(data.category_counts || {}),
        datasets: [{
            data: Object.values(data.category_counts || {}),
            backgroundColor: Object.keys(data.category_counts || {}).map(c => CATEGORIES[c] || CATEGORIES['Other']),
            borderWidth: 1,
            borderColor: '#0f172a'
        }]
    } : null;

    const lineData = data ? {
        labels: (data.daily_trends || []).map(d => new Date(d.date).toLocaleDateString([], { weekday: 'short' })),
        datasets: [{
            label: 'Incidents',
            data: (data.daily_trends || []).map(d => d.count),
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0,
            pointRadius: 3,
            pointBackgroundColor: '#ef4444',
            pointBorderColor: '#ef4444',
            pointBorderWidth: 1
        }]
    } : null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center animate-fade-in">
            <div className="panel-aura rounded-md w-full max-w-4xl m-4 overflow-hidden flex flex-col max-h-[90vh] relative">
                <div className="p-6 border-b border-[var(--color-border)] flex justify-between items-center bg-[var(--color-bg-secondary)]">
                    <h2 className="text-lg font-bold uppercase tracking-tight text-[var(--color-text-primary)] flex items-center">
                        <BarChart2 className="mr-2 text-[var(--color-accent)]" size={20} /> Community Analytics
                    </h2>
                    <button onClick={onClose} className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-6 overflow-y-auto bg-[var(--color-bg-primary)]">
                    {loading ? (
                        <div className="flex justify-center items-center h-64">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-accent)]"></div>
                        </div>
                    ) : error ? (
                        <p className="text-[var(--color-accent)] text-center text-sm font-bold">{error}</p>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="panel-aura p-5 rounded-sm">
                                <h3 className="text-label mb-2">Peak Incident Time</h3>
                                <p className="text-3xl font-bold font-mono text-[var(--color-text-primary)]">
                                    {data.busiest_hour !== null
                                        ? new Date(0, 0, 0, data.busiest_hour).toLocaleTimeString([], { hour: 'numeric', hour12: true })
                                        : 'N/A'}
                                </p>
                                <p className="text-xs text-[var(--color-text-secondary)] mt-1">Most reports occur around this time</p>
                            </div>

                            <div className="panel-aura p-5 rounded-sm relative" style={{ minHeight: '250px' }}>
                                <h3 className="text-label mb-4 absolute top-5 left-5 z-10">Distribution</h3>
                                <div className="h-full w-full flex justify-center pt-6">
                                    <Doughnut data={doughnutData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: '#94a3b8', font: { family: 'Inter', size: 10 } } } } }} />
                                </div>
                            </div>

                            <div className="md:col-span-2 panel-aura p-5 rounded-sm relative" style={{ minHeight: '300px' }}>
                                <h3 className="text-label mb-4 absolute top-5 left-5 z-10">Weekly Trend</h3>
                                <div className="h-full w-full pt-8">
                                    <Line data={lineData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { borderDash: [2, 4], color: '#334155' }, ticks: { color: '#94a3b8', font: { family: 'Inter', size: 10 } } }, x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { family: 'Inter', size: 10 } } } } }} />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default AnalyticsModal;
