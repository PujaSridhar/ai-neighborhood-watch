import React, { useState, useEffect } from 'react';
import { X, MapPin, Info } from 'lucide-react';

const ReportModal = ({ onClose, onSubmit, mapCenter }) => {
    const [description, setDescription] = useState('');
    const [location, setLocation] = useState(null);

    useEffect(() => {
        if (mapCenter) setLocation({ lat: mapCenter[0], lng: mapCenter[1] });
    }, [mapCenter]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!location || !description) return;
        onSubmit({
            description,
            latitude: location.lat,
            longitude: location.lng
        });
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center animate-fade-in">
            <div className="panel-aura rounded-md w-full max-w-md m-4 overflow-hidden relative">
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                    <X size={20} />
                </button>

                <div className="p-6">
                    <h2 className="text-lg font-bold uppercase tracking-tight text-[var(--color-text-primary)] mb-6">Report Incident</h2>

                    <div className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] px-4 py-3 rounded-sm text-xs mb-4 flex items-start text-[var(--color-text-secondary)]">
                        <Info size={16} className="mr-2 mt-0.5 flex-shrink-0 text-[var(--color-accent)]" />
                        <p className="font-mono">LOC: {location ? `${location.lat.toFixed(6)}, ${location.lng.toFixed(6)}` : 'WAITING_FOR_GPS'}</p>
                    </div>

                    <form onSubmit={handleSubmit}>
                        <div className="mb-6">
                            <label className="block text-[var(--color-text-secondary)] text-xs font-bold uppercase tracking-wide mb-2">Description</label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                rows="3"
                                className="input-aura resize-none"
                                placeholder="Describe the event..."
                                required
                            ></textarea>
                        </div>
                        <div className="flex justify-end space-x-3">
                            <button type="button" onClick={onClose} className="btn-secondary text-xs uppercase tracking-wide">Cancel</button>
                            <button type="submit" className="btn-primary text-xs uppercase tracking-wide">Submit Report</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default ReportModal;
