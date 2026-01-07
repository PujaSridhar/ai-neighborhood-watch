import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';

// Fix for default marker icon
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const CATEGORIES = {
    'Theft': '#EF4444',
    'Vandalism': '#F97316',
    'Accident': '#3B82F6',
    'Fire': '#D946EF',
    'Suspicious Activity': '#EAB308',
    'Other': '#6B7280',
    'Uncategorized': '#9CA3AF'
};

const HeatmapLayer = ({ points }) => {
    const map = useMap();
    const heatLayerRef = useRef(null);

    useEffect(() => {
        if (heatLayerRef.current) {
            map.removeLayer(heatLayerRef.current);
        }

        if (points.length > 0) {
            heatLayerRef.current = L.heatLayer(points, {
                radius: 30,
                blur: 20,
                maxZoom: 16,
                gradient: { 0.4: 'blue', 0.65: 'lime', 1: 'red' }
            }).addTo(map);
        }

        return () => {
            if (heatLayerRef.current) {
                map.removeLayer(heatLayerRef.current);
            }
        };
    }, [points, map]);

    return null;
};

const MapEvents = ({ onMoveEnd, onMapClick, setMapCenter }) => {
    const map = useMap();

    useEffect(() => {
        const handleMoveEnd = () => {
            const center = map.getCenter();
            onMoveEnd(center.lat, center.lng);
            setMapCenter([center.lat, center.lng]);
        };

        const handleClick = (e) => {
            onMapClick(e.latlng);
        };

        map.on('moveend', handleMoveEnd);
        map.on('click', handleClick);

        return () => {
            map.off('moveend', handleMoveEnd);
            map.off('click', handleClick);
        };
    }, [map, onMoveEnd, onMapClick, setMapCenter]);

    return null;
};

const MapController = ({ center }) => {
    const map = useMap();
    useEffect(() => {
        if (center) {
            map.flyTo(center, 16, { animate: true, duration: 1.5 });
        }
    }, [center, map]);
    return null;
}

const MapMap = ({ reports, viewMode, onMoveEnd, setMapCenter, onMapClick, theme }) => {
    // Prepare heatmap points
    const heatPoints = reports.map(r => [r.latitude, r.longitude, 0.6]);

    const tileUrl = theme === 'dark'
        ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        : "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";

    return (
        <MapContainer
            center={[40.5008, -74.4478]}
            zoom={13}
            style={{ height: '100%', width: '100%', zIndex: 0 }}
            zoomControl={false}
        >
            <TileLayer
                url={tileUrl}
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                maxZoom={20}
            />

            <ZoomControl position="bottomright" />

            <MapEvents onMoveEnd={onMoveEnd} onMapClick={onMapClick} setMapCenter={setMapCenter} />

            {/* We don't strictly need MapController if we lift state up, but for "flyTo" from sidebar it's useful */}
            {/* Actually, App.jsx passes setMapCenter, but we need a way to trigger flyTo when that state changes externally. 
          Wait, if App.jsx updates mapCenter, we need to react to it. 
          So we should pass mapCenter as a prop to MapMap and use MapController to fly to it.
      */}

            {viewMode === 'heatmap' && <HeatmapLayer points={heatPoints} />}

            {viewMode === 'density' && reports.map(r => (
                <CircleMarker
                    key={r.id}
                    center={[r.latitude, r.longitude]}
                    radius={6}
                    pathOptions={{
                        fillColor: CATEGORIES[r.category] || CATEGORIES['Uncategorized'],
                        color: '#fff',
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.9
                    }}
                >
                    <Popup className="aura-popup">
                        <div className="font-sans min-w-[150px]">
                            <strong className="block text-xs uppercase tracking-wide mb-1" style={{ color: CATEGORIES[r.category] || CATEGORIES['Uncategorized'] }}>{r.category}</strong>
                            <p className="text-sm font-medium text-[var(--color-text-primary)] leading-tight">{r.description}</p>
                            <p className="text-[10px] text-[var(--color-text-secondary)] mt-2 font-mono opacity-80">{new Date(r.created_at).toLocaleString()}</p>
                        </div>
                    </Popup>
                </CircleMarker>
            ))}
        </MapContainer>
    );
};

export default MapMap;
