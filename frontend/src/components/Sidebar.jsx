import React, { useState } from 'react';
import IncidentCard from './IncidentCard';
import { Search, Newspaper } from 'lucide-react';

const CATEGORIES = {
    'Theft': { color: '#EF4444', label: 'Theft' },
    'Vandalism': { color: '#F97316', label: 'Vandalism' },
    'Accident': { color: '#3B82F6', label: 'Accident' },
    'Fire': { color: '#D946EF', label: 'Fire' },
    'Suspicious Activity': { color: '#EAB308', label: 'Suspicious' },
    'Other': { color: '#6B7280', label: 'Other' },
    'Uncategorized': { color: '#9CA3AF', label: 'Uncategorized' }
};

const Sidebar = ({ reports, news, activeCategories, toggleCategory, loading, onFlyTo }) => {
    const [activeTab, setActiveTab] = useState('incidents'); // 'incidents' or 'news'

    return (
        <aside className="absolute top-28 left-4 bottom-8 w-96 z-10 flex flex-col pointer-events-none">
            <div className="panel-aura rounded-md flex flex-col h-full overflow-hidden pointer-events-auto">

                {/* Filters */}
                <div className="p-4 border-b border-[var(--color-border)] bg-[var(--color-bg-tertiary)]">
                    <p className="text-label mb-3">Filter by Category</p>
                    <div className="flex flex-wrap gap-2">
                        {Object.entries(CATEGORIES).map(([name, config]) => {
                            const isActive = activeCategories.has(name);
                            return (
                                <button
                                    key={name}
                                    onClick={() => toggleCategory(name)}
                                    className={`flex items-center justify-center px-2 py-1 rounded-sm text-[10px] uppercase font-bold tracking-wider border transition-all duration-200`}
                                    style={{
                                        backgroundColor: isActive ? config.color : 'transparent',
                                        borderColor: isActive ? config.color : 'var(--color-border)',
                                        color: isActive ? '#fff' : 'var(--color-text-secondary)'
                                    }}
                                >
                                    {name}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
                    <button
                        onClick={() => setActiveTab('incidents')}
                        className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${activeTab === 'incidents' ? 'text-[var(--color-accent)] border-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] border-transparent hover:text-[var(--color-text-primary)]'}`}
                    >
                        Live Feed
                    </button>
                    <button
                        onClick={() => setActiveTab('news')}
                        className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${activeTab === 'news' ? 'text-[var(--color-accent)] border-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] border-transparent hover:text-[var(--color-text-primary)]'}`}
                    >
                        Local News
                    </button>
                </div>

                {/* Content Feed */}
                <div className="flex-grow overflow-y-auto custom-scrollbar bg-[var(--color-bg-secondary)] relative">

                    {/* Incident Feed */}
                    {activeTab === 'incidents' && (
                        <div className="absolute inset-0">
                            {loading.reports ? (
                                <div className="flex justify-center items-center h-full">
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--color-accent)]"></div>
                                </div>
                            ) : reports.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-48 text-[var(--color-text-secondary)]">
                                    <Search size={32} className="mb-2 opacity-50" />
                                    <p className="text-xs uppercase tracking-wide">No incidents found</p>
                                </div>
                            ) : (
                                <div>
                                    <div className="px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-tertiary)] flex justify-between items-center">
                                        <span className="text-[10px] uppercase font-bold text-[var(--color-text-secondary)]">Latest Reports</span>
                                        <span className="text-[10px] font-mono text-[var(--color-text-secondary)]">{reports.length} Items</span>
                                    </div>
                                    {reports.map(report => (
                                        <IncidentCard
                                            key={report.id}
                                            report={report}
                                            categoryConfig={CATEGORIES[report.category] || CATEGORIES['Uncategorized']}
                                            onClick={() => onFlyTo(report.latitude, report.longitude)}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* News Feed */}
                    {activeTab === 'news' && (
                        <div className="absolute inset-0">
                            {loading.news ? (
                                <div className="flex justify-center items-center h-full">
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--color-accent)]"></div>
                                </div>
                            ) : news.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-48 text-[var(--color-text-secondary)]">
                                    <Newspaper size={32} className="mb-2 opacity-50" />
                                    <p className="text-xs uppercase tracking-wide">No recent news</p>
                                </div>
                            ) : (
                                news.map((item, idx) => (
                                    <a
                                        key={idx}
                                        href={item.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block p-4 border-b border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] transition-colors group"
                                    >
                                        <h4 className="text-sm font-bold text-[var(--color-text-primary)] mb-1 group-hover:text-[var(--color-accent)] transition-colors line-clamp-2 leading-tight">{item.title}</h4>
                                        <p className="text-xs text-[var(--color-text-secondary)] line-clamp-2 mt-1">{item.summary}</p>
                                        <div className="mt-2 text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider opacity-70">Source: Local News</div>
                                    </a>
                                ))
                            )}
                        </div>
                    )}

                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
