import React from 'react';
import { Shield, MapPin, Flame, BarChart2, Mic, Megaphone, Sun, Moon } from 'lucide-react';

const Navbar = ({ incidentCount, viewMode, setViewMode, openModal, theme, toggleTheme }) => {
    return (
        <nav className="absolute top-4 left-4 right-4 z-20 flex justify-between items-start pointer-events-none">
            {/* Brand & Stats */}
            <div className="panel-aura px-4 py-3 rounded-md flex items-center space-x-4 pointer-events-auto">
                <div className="bg-[var(--color-accent)] p-1.5 rounded-sm">
                    <Shield className="text-white" size={20} />
                </div>
                <div>
                    <h1 className="text-lg font-bold uppercase tracking-tight leading-none text-[var(--color-text-primary)]">Aura <span className="text-[var(--color-text-secondary)] font-normal text-xs normal-case">/ Watch</span></h1>
                    <div className="flex items-center space-x-2 mt-0.5">
                        <span className="flex h-1.5 w-1.5 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-500"></span>
                        </span>
                        <span className="text-[10px] font-bold text-[var(--color-text-secondary)] uppercase tracking-wider">System Online</span>
                    </div>
                </div>
                <div className="h-8 w-px bg-[var(--color-border)] mx-2"></div>
                <div className="flex flex-col">
                    <span className="text-xs font-bold text-[var(--color-text-secondary)] uppercase">Incidents</span>
                    <span className="text-sm font-mono font-bold text-[var(--color-text-primary)]">{incidentCount}</span>
                </div>
            </div>

            {/* Controls */}
            <div className="flex flex-col space-y-2 pointer-events-auto items-end">
                {/* View Mode Switcher */}
                <div className="panel-aura p-1 rounded-md flex space-x-0.5">
                    <button
                        onClick={() => setViewMode('density')}
                        className={`px-3 py-1.5 rounded-sm text-xs font-bold uppercase tracking-wide transition-all flex items-center ${viewMode === 'density' ? 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] shadow-sm' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}`}
                    >
                        <MapPin size={14} className="mr-1.5" /> Markers
                    </button>
                    <button
                        onClick={() => setViewMode('heatmap')}
                        className={`px-3 py-1.5 rounded-sm text-xs font-bold uppercase tracking-wide transition-all flex items-center ${viewMode === 'heatmap' ? 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] shadow-sm' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}`}
                    >
                        <Flame size={14} className="mr-1.5" /> Heatmap
                    </button>
                </div>

                <div className="flex space-x-2">
                    <button onClick={toggleTheme} className="panel-aura px-3 py-2 rounded-md hover:bg-[var(--color-surface-hover)] transition-colors text-[var(--color-text-primary)]">
                        {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
                    </button>
                    <button onClick={() => openModal('analytics')} className="btn-secondary flex items-center text-xs uppercase tracking-wide">
                        <BarChart2 size={16} className="mr-2" /> Analytics
                    </button>
                    <button onClick={() => openModal('podcast')} className="btn-secondary flex items-center text-xs uppercase tracking-wide">
                        <Mic size={16} className="mr-2" /> Briefing
                    </button>
                    <button onClick={() => openModal('report')} className="btn-primary flex items-center text-xs uppercase tracking-wide shadow-lg shadow-red-900/20">
                        <Megaphone size={16} className="mr-2" /> Report
                    </button>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
