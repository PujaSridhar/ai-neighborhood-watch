import React from 'react';

const IncidentCard = ({ report, categoryConfig, onClick }) => {
    const timeString = new Date(report.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const dateString = new Date(report.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' });

    return (
        <div
            onClick={onClick}
            className="group p-4 border-b border-[var(--color-border)] hover:bg-white/5 transition-colors cursor-pointer animate-fade-in flex flex-col gap-1"
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full shadow-[0_0_8px_currentColor]" style={{ color: categoryConfig.color, backgroundColor: 'currentColor' }}></span>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-secondary)] group-hover:text-[var(--color-accent)] transition-colors">
                        {report.category}
                    </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono text-[var(--color-text-secondary)] opacity-70">
                    <span>{dateString}</span>
                    <span>{timeString}</span>
                </div>
            </div>

            <p className="text-sm text-[var(--color-text-primary)] leading-relaxed line-clamp-2 font-medium">
                {report.description}
            </p>
        </div>
    );
};

export default IncidentCard;
