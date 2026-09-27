import React, { useEffect, useState } from 'react';
import Header from './components/Header.jsx';
import Sidebar, { MapLayersPanel } from './components/Sidebar.jsx';
import MapDashboard from './components/MapDashboard.jsx';
import Timeline from './pages/Timeline.jsx';
import Zones from './pages/Zones.jsx';
import Species from './pages/Species.jsx';
import Forecast from './pages/Forecast.jsx';
import Landing from './pages/Landing.jsx';
import FireSimulation from './pages/FireSimulation.jsx';
import { fetchGBIFOccurrences, fetchAirQuality } from './services/api.js';
import { renderGBIFLayer, renderAQILayer, flyTo } from './services/mapService.js';
import { ALERTS } from './data/data.js';

export default function App() {
  const isFireDetailRoute = window.location.pathname.endsWith('/fire-detail.html');
  const [activeView, setActiveView] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return isFireDetailRoute || params.has('fire_id') ? 'fire-simulation' : params.get('view') || 'landing';
  }); const [year, setYear] = useState(2024);
  const [layers, setLayers] = useState({ ndvi: false, deforestation: true, protected: true, fires: true, species: false, aqi: false, gbif: false });
  const [gbif, setGbif] = useState([]); const [aqi, setAqi] = useState([]); const [trees, setTrees] = useState('2.40M'); const [fires, setFires] = useState(124);
  const mapGetter = window.__vanarakshaMap;
  useEffect(() => { fetchGBIFOccurrences().then(setGbif); fetchAirQuality().then(setAqi); const t = setInterval(() => { setTrees(v => (parseFloat(v) + 0.0001).toFixed(2) + 'M'); setFires(v => Math.max(90, v + (Math.random() > .5 ? 1 : -1))) }, 3000); return () => clearInterval(t) }, []);
  useEffect(() => { if (window.__vanarakshaMap) { renderGBIFLayer(window.__vanarakshaMap, gbif, layers.gbif); renderAQILayer(window.__vanarakshaMap, aqi, layers.aqi) } }, [gbif, aqi, layers.gbif, layers.aqi]);
  const navigate = v => {
    if (isFireDetailRoute && v !== 'fire-simulation') {
      window.location.assign(`/?view=${encodeURIComponent(v)}`);
      return;
    }
    setActiveView(v);
  };
  if (activeView === 'landing' && !isFireDetailRoute) return <Landing onLaunch={() => setActiveView('map')} />;
  if (isFireDetailRoute) return <div className="app-root fire-app-root"><Header activeView="fire-simulation" onNavigate={navigate} /><main className="react-fullscreen fire-detail-shell"><FireSimulation /></main></div>;
  const main = activeView === 'map' ? <MapDashboard year={year} layers={layers} onLayersChange={setLayers} /> :
    <main className={`react-fullscreen ${activeView === 'fire-simulation' ? 'fire-detail-shell' : ''}`}>{activeView === 'timeline' && <Timeline />}{activeView === 'zones' && <Zones onFlyTo={(lat, lng) => { setActiveView('map'); setTimeout(() => window.__vanarakshaMap && flyTo(window.__vanarakshaMap, lat, lng), 200) }} />}{activeView === 'species' && <Species />} {activeView === 'forecast' && <Forecast />}{activeView === 'fire-simulation' && <FireSimulation />}</main>;
  return <div className={`app-root ${activeView === 'fire-simulation' ? 'fire-app-root' : ''}`}><Header activeView={activeView} onNavigate={navigate} />{main}</div>;
}
