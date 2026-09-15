import React from 'react';
import { ALERTS } from '../data/data.js';

export default function Sidebar({ year, setYear, layers, setLayers, onFlyTo, onScanCoords, trees, fires }) {
  const toggle = key => setLayers(v => ({...v, [key]: !v[key]}));
  const rows = [
    ['ndvi','NDVI Heatmap','NASA MODIS'],['deforestation','Deforestation Zones','Hansen GFW'],['protected','Protected Areas','MoEFCC'],['fires','Fire Hotspots','NASA FIRMS'],['species','Species Corridors','GBIF + WII'],['aqi','Air Quality (AQI)','OpenAQ']
  ];
  return <aside className="sidebar" id="left-sidebar">
    <div className="sidebar-card"><div className="card-header"><span className="card-title">National Forest Health</span><span className="card-badge badge-warning">⚠ Declining</span></div>
      <div className="score-ring-wrap"><div className="score-ring"><svg viewBox="0 0 120 120"><defs><linearGradient id="ring-gradient" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stopColor="#1a7a3e"/><stop offset="100%" stopColor="#3dcc73"/></linearGradient></defs><circle className="ring-bg" cx="60" cy="60" r="50"/><circle className="ring-fill" cx="60" cy="60" r="50" stroke="url(#ring-gradient)" strokeDasharray={`${Math.round((year===2024 ? 0.7 : 0.65)*314)} 314`} strokeDashoffset="-47"/></svg><div className="score-center"><span className="score-value">{year===2024?'70':'65'}%</span><span className="score-label">NDVI Index</span></div></div></div>
      <div className="score-stats"><div className="stat-item"><span className="stat-num green">713,789</span><span className="stat-label">km² Forest Cover</span></div><div className="stat-item"><span className="stat-num red">-1.3%</span><span className="stat-label">Loss This Year</span></div></div>
    </div>
    <div className="sidebar-card"><div className="card-header"><span className="card-title">🚨 Active Alerts</span><span className="card-badge badge-danger">{ALERTS.length} Active</span></div><div className="alerts-list">{ALERTS.map(a=><div className={`alert-item ${a.type}`} key={a.id} onClick={()=>onFlyTo(a.lat,a.lng)}><div className="alert-icon">{a.icon}</div><div className="alert-text"><div className="alert-title">{a.title}</div><div className="alert-sub">{a.sub}</div></div><div className="alert-time">{a.time}</div></div>)}</div></div>
    <div className="sidebar-card"><div className="card-header"><span className="card-title">🗂️ Map Layers</span></div><div className="layer-controls">{rows.map(([id,label,source])=><label className="layer-toggle" key={id}><input type="checkbox" checked={!!layers[id]} onChange={()=>toggle(id)}/><span className="toggle-slider"></span><span className="layer-name">{label}</span><span className="layer-source">{source}</span></label>)}<label className="layer-toggle"><input type="checkbox" checked={!!layers.gbif} onChange={()=>toggle('gbif')}/><span className="toggle-slider"></span><span className="layer-name">Species Sightings</span><span className="layer-source">GBIF Live</span></label></div></div>
    <div className="sidebar-card"><div className="card-header"><span className="card-title">⏳ Historical View</span><span className="card-badge badge-info">{year}</span></div><input type="range" className="year-slider" min="2000" max="2024" value={year} onChange={e=>setYear(Number(e.target.value))}/><div className="slider-labels"><span>2000</span><span>2010</span><span>2024</span></div><p className="slider-hint">Drag to see NDVI & forest loss changes over time</p></div>
    <button className="scan-cta sidebar-scan" onClick={() => onScanCoords({lat:20.59,lng:78.96})}>🔍 Open Zone Scanner</button>
    <div className="sidebar-card quick-stats-card"><div className="quick-stat"><span className="qs-icon">🌳</span><div><div className="qs-num">{trees}</div><div className="qs-label">Trees Lost Today</div></div></div><div className="quick-stat"><span className="qs-icon">🔥</span><div><div className="qs-num">{fires}</div><div className="qs-label">Active Fire Alerts</div></div></div></div>
  </aside>;
}
