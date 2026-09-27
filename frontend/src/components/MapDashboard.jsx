import React, { useEffect, useRef, useState } from 'react';
import Chart from 'chart.js/auto';
import { createForestMap, flyTo, setLayerVisibility, updateNDVI } from '../services/mapService.js';
import { YEARLY_DATA, PROTECTED_ZONES } from '../data/data.js';

function MiniChart({ type = 'line', data, labels }) {
  const ref = useRef(null); const chartRef = useRef(null);
  useEffect(() => { if (!ref.current) return; chartRef.current?.destroy(); chartRef.current = new Chart(ref.current, { type, data: { labels, datasets: [{ data, borderColor: '#3dcc73', backgroundColor: 'rgba(61,204,115,0.08)', fill: true, tension: .4, pointRadius: 0, borderRadius: 3 }] }, options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { color: 'rgba(200,240,218,.35)', font: { size: 9 }, maxTicksLimit: 5 } }, y: { grid: { color: 'rgba(61,204,115,.05)' }, ticks: { color: 'rgba(200,240,218,.35)', font: { size: 9 } } } } } }); return () => chartRef.current?.destroy(); }, [data, labels]);
  return <canvas ref={ref} height="130" />;
}

export default function MapDashboard({ year, layers, onLayersChange }) {
  const mapRef = useRef(null), map = useRef(null); const [coords, setCoords] = useState({ lat: 20.5937, lng: 78.9629, zoom: 5 });
  useEffect(() => { if (!mapRef.current) return; map.current = createForestMap(mapRef.current, { year, onCoords: setCoords }); window.__vanarakshaMap = map.current; return () => { if (window.__vanarakshaMap === map.current) delete window.__vanarakshaMap; map.current?.remove(); }; }, []);
  useEffect(() => { updateNDVI(map.current, year); }, [year]);
  useEffect(() => { Object.entries(layers).forEach(([k, v]) => setLayerVisibility(map.current, k, v)); }, [layers]);
  const doFly = (lat, lng) => flyTo(map.current, lat, lng);
  const searchZone = event => { event.preventDefault(); const query = event.currentTarget.elements.zoneSearch.value.trim().toLowerCase(); if (!query) return; const hit = PROTECTED_ZONES.find(z => z.name.toLowerCase().includes(query) || z.state.toLowerCase().includes(query)); if (hit) doFly(hit.lat, hit.lng); };
  return <div className="map-container" id="map-view">
    <div id="map" ref={mapRef}></div>
  </div>;
}
