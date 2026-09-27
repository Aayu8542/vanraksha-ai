import React, { useCallback, useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import {
  advanceBackendFireCycle,
  createBackendSimulation,
  getBackendSimulation,
  getBackendSimulationOutputs,
  runBackendSimulation,
  updateBackendFireStatus
} from '../services/api.js';

const RISK_TOKEN = {
  Low: '--risk-low',
  Moderate: '--risk-moderate',
  High: '--risk-high',
  'Very High': '--risk-very-high',
  Extreme: '--risk-extreme'
};
const PRIORITY_TOKEN = { Critical: '--risk-extreme', High: '--risk-high', Standard: '--risk-moderate' };
const PRIORITIES = ['Critical', 'High', 'Standard'];
const BACKEND_RISK_LABEL = { LOW: 'Low', MODERATE: 'Moderate', HIGH: 'High', VERY_HIGH: 'Very High', CRITICAL: 'Extreme' };
const OUTPUT_TABS = [
  { id: 'risk', label: 'Risk map' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'biodiversity', label: 'Biodiversity' },
  { id: 'response', label: 'Response' },
  { id: 'events', label: 'Events' }
];

function toFireRecord(simulation) {
  return {
    fire_id: simulation.simulation_id,
    core_polygon: simulation.risk_map || simulation.fire_perimeter,
    uncertainty_polygon: simulation.fire_spread,
    wind_used: {},
    priority_list: [],
    confidence: BACKEND_RISK_LABEL[simulation.risk?.class] || 'Moderate',
    intensity: `${simulation.risk?.score ?? '—'} / 100`,
    generated_at: simulation.created_at,
    backend_status: simulation.status,
    risk: simulation.risk,
    timeline: simulation.timeline || [],
    affected_assets: simulation.affected_assets || {},
    data_sources: simulation.data_sources || []
  };
}

function displayName(value) {
  return String(value).replaceAll('_', ' ');
}

function formatTimestamp(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function tokenColor(token) {
  return getComputedStyle(document.documentElement).getPropertyValue(token).trim();
}

function asFeatureCollection(geojson) {
  if (!geojson) return { type: 'FeatureCollection', features: [] };
  if (geojson.type === 'FeatureCollection') return geojson;
  if (geojson.type === 'Feature') return { type: 'FeatureCollection', features: [geojson] };
  return { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: geojson }] };
}

function polygonBounds(geojson) {
  const bounds = new maplibregl.LngLatBounds();
  const visit = value => {
    if (Array.isArray(value) && typeof value[0] === 'number' && typeof value[1] === 'number') bounds.extend([value[0], value[1]]);
    else if (Array.isArray(value)) value.forEach(visit);
  };
  asFeatureCollection(geojson).features.forEach(feature => visit(feature.geometry?.coordinates));
  return bounds.isEmpty() ? null : bounds;
}

function normalizedPriority(priority) {
  return PRIORITIES.find(value => value.toLowerCase() === String(priority).toLowerCase()) || 'Standard';
}

function markerShape(type) {
  const normalized = String(type).toLowerCase();
  if (normalized.includes('settlement')) return 'circle';
  if (normalized.includes('infrastructure')) return 'square';
  if (normalized.includes('protected')) return 'triangle';
  return 'circle';
}

function FireMap({ fire }) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const markers = useRef([]);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    if (!mapContainer.current) return undefined;
    const instance = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [82.8, 21.5],
      zoom: 5,
      minZoom: 3,
      maxZoom: 15
    });
    map.current = instance;
    window.__fireDetailMap = instance;
    instance.addControl(new maplibregl.NavigationControl(), 'bottom-right');
    instance.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');
    instance.once('load', () => setMapReady(true));
    return () => {
      markers.current.forEach(marker => marker.remove());
      instance.remove();
      map.current = null;
      window.__fireDetailMap = null;
    };
  }, []);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !mapReady || !fire) return;
    const riskColor = tokenColor(RISK_TOKEN[fire.confidence] || '--risk-moderate');
    const sources = [
      ['fire-uncertainty', asFeatureCollection(fire.uncertainty_polygon)],
      ['fire-core', asFeatureCollection(fire.core_polygon)]
    ];
    sources.forEach(([sourceId, data]) => {
      if (instance.getSource(sourceId)) instance.getSource(sourceId).setData(data);
      else instance.addSource(sourceId, { type: 'geojson', data });
    });

    if (!instance.getLayer('fire-uncertainty-fill')) {
      instance.addLayer({ id: 'fire-uncertainty-fill', type: 'fill', source: 'fire-uncertainty', paint: { 'fill-color': riskColor, 'fill-opacity': 0.2 } });
      instance.addLayer({ id: 'fire-uncertainty-line', type: 'line', source: 'fire-uncertainty', paint: { 'line-color': riskColor, 'line-width': 2, 'line-dasharray': [2, 2] } });
      instance.addLayer({ id: 'fire-core-fill', type: 'fill', source: 'fire-core', paint: { 'fill-color': riskColor, 'fill-opacity': 0.6 } });
      instance.addLayer({ id: 'fire-core-line', type: 'line', source: 'fire-core', paint: { 'line-color': riskColor, 'line-width': 2.5 } });
    } else {
      ['fire-uncertainty-fill', 'fire-uncertainty-line', 'fire-core-fill', 'fire-core-line'].forEach(layerId => {
        instance.setPaintProperty(layerId, layerId.endsWith('fill') ? 'fill-color' : 'line-color', riskColor);
      });
    }

    markers.current.forEach(marker => marker.remove());
    markers.current = (fire.priority_list || []).filter(item => Number.isFinite(Number(item.lat)) && Number.isFinite(Number(item.lng))).map(item => {
      const shape = markerShape(item.type);
      const element = document.createElement('div');
      element.className = `fire-map-marker fire-map-marker-${shape}`;
      element.setAttribute('aria-label', `${item.name}, ${item.priority} priority`);
      element.style.setProperty('--marker-color', tokenColor(PRIORITY_TOKEN[normalizedPriority(item.priority)]));
      return new maplibregl.Marker({ element, anchor: 'center' }).setLngLat([Number(item.lng), Number(item.lat)]).addTo(instance);
    });

    const bounds = polygonBounds(fire.uncertainty_polygon);
    if (bounds) instance.fitBounds(bounds, { padding: 56, maxZoom: 10, duration: 850 });
  }, [fire, mapReady]);

  return <div className="fire-map-wrap">
    <div ref={mapContainer} className="fire-map" aria-label="Map showing predicted fire spread and priority locations" />
    <div className="fire-map-legend" aria-label="Map legend">
      <div className="fire-legend-section"><span className="fire-legend-polygon fire-legend-core" /> Core spread</div>
      <div className="fire-legend-section"><span className="fire-legend-polygon fire-legend-uncertainty" /> Uncertainty extent</div>
      <div className="fire-legend-section"><span className="fire-legend-marker circle" style={{ '--marker-color': tokenColor('--risk-extreme') }} /> Critical</div>
      <div className="fire-legend-section"><span className="fire-legend-marker square" style={{ '--marker-color': tokenColor('--risk-high') }} /> High</div>
      <div className="fire-legend-section"><span className="fire-legend-marker triangle" style={{ '--marker-color': tokenColor('--risk-moderate') }} /> Standard</div>
      <div className="fire-legend-types">Circle settlement · square infrastructure · triangle protected area</div>
    </div>
  </div>;
}

function WindArrow({ direction }) {
  const compass = { N: 0, NE: 45, E: 90, SE: 135, S: 180, SW: 225, W: 270, NW: 315 };
  const normalized = String(direction ?? '').trim().toUpperCase();
  const rotation = Number.isFinite(Number(direction)) ? Number(direction) : compass[normalized] ?? 0;
  return <svg className="fire-wind-arrow" viewBox="0 0 24 24" aria-label={`Wind direction ${direction}`} style={{ transform: `rotate(${rotation}deg)` }}>
    <path d="M12 2.5 18 14h-4v7.5h-4V14H6z" />
  </svg>;
}

function FireSkeleton() {
  return <div className="fire-detail-layout fire-skeleton-layout" aria-label="Loading fire event">
    <div className="fire-map-skeleton"><span className="fire-loading-mark" /></div>
    <aside className="fire-panel fire-panel-skeleton">
      <div className="fire-skeleton-line wide" /><div className="fire-skeleton-line" /><div className="fire-skeleton-block" />
      <div className="fire-skeleton-line wide" /><div className="fire-skeleton-line" /><div className="fire-skeleton-block list" />
    </aside>
  </div>;
}

function SimulationOutputView({ tab, fire, outputs, loading, onRetry }) {
  if (loading) return <p className="fire-output-empty">Loading simulation outputs…</p>;
  if (!outputs) return <div className="fire-output-empty"><p>Simulation output details are unavailable.</p><button type="button" onClick={onRetry}>Retry</button></div>;

  if (tab === 'risk') {
    const features = outputs.riskMap?.features || [];
    const contributors = Object.entries(fire.risk?.contributors || {});
    const weights = fire.risk?.weights || {};
    return <div className="fire-output-view">
      <div className="fire-output-heading"><h2>Risk map</h2><span>{features.length} zone{features.length === 1 ? '' : 's'}</span></div>
      <p className="fire-output-description">Estimated risk zones are drawn on the map. Contributor values are normalized from 0 to 1.</p>
      {features.map((feature, index) => <div className="fire-risk-zone" key={`risk-zone-${index}`}>
        <strong>{feature.properties?.risk_class || fire.risk?.class || 'Unclassified'}</strong>
        <span>{feature.properties?.risk_score ?? fire.risk?.score ?? '—'} / 100</span>
      </div>)}
      <div className="fire-risk-list">
        {contributors.map(([name, value]) => <div className="fire-risk-row" key={name}>
          <div className="fire-risk-label"><span>{displayName(name)}</span><strong>{Math.round(Number(value) * 100)}%</strong></div>
          <div className="fire-risk-bar"><span style={{ width: `${Math.max(0, Math.min(100, Number(value) * 100))}%` }} /></div>
          <small>Model weight {Math.round(Number(weights[name] || 0) * 100)}%</small>
        </div>)}
      </div>
      {!!fire.data_sources?.length && <div className="fire-data-sources">
        <h3>Data provenance</h3>
        {fire.data_sources.map((source, index) => <article key={`${source.name}-${index}`}>
          <strong>{source.name}</strong><span>{source.kind}</span><small>{source.details}</small>
        </article>)}
      </div>}
    </div>;
  }

  if (tab === 'timeline') {
    const timeline = outputs.timeline || [];
    const maxArea = Math.max(1, ...timeline.map(point => Number(point.burned_area_ha) || 0));
    return <div className="fire-output-view">
      <div className="fire-output-heading"><h2>Spread timeline</h2><span>{timeline.length} steps</span></div>
      <div className="fire-timeline-list">
        {timeline.map((point, index) => <article className="fire-timeline-row" key={`${point.time_minutes}-${index}`}>
          <strong>{point.time_minutes} min</strong>
          <div className="fire-timeline-track"><span style={{ width: `${Math.max(3, (Number(point.burned_area_ha) / maxArea) * 100)}%` }} /></div>
          <span>{point.burned_area_ha} ha</span>
          <small>Risk {point.risk_score} · {point.active_cells} active cells</small>
        </article>)}
        {!timeline.length && <p className="fire-output-empty">No timeline points were returned.</p>}
      </div>
    </div>;
  }

  if (tab === 'biodiversity') {
    const biodiversity = outputs.biodiversity || {};
    return <div className="fire-output-view">
      <div className="fire-output-heading"><h2>Biodiversity impact</h2><span>{biodiversity.estimated ? 'Estimated' : 'Observed'}</span></div>
      <dl className="fire-output-dl">
        <dt>Affected area</dt><dd>{biodiversity.affected_area_ha ?? '—'} ha</dd>
        <dt>Protected areas affected</dt><dd>{biodiversity.protected_areas_affected ?? 0}</dd>
        <dt>Threatened species affected</dt><dd>{biodiversity.threatened_species_affected ?? 0}</dd>
        <dt>Priority score</dt><dd>{biodiversity.priority_score ?? '—'} / 100</dd>
      </dl>
      <p className="fire-output-description">Species counts are estimates; the current backend does not include a local species-habitat dataset.</p>
    </div>;
  }

  if (tab === 'response') {
    const response = outputs.response || {};
    const units = response.units || [];
    return <div className="fire-output-view">
      <div className="fire-output-heading"><h2>Response plan</h2><span>{response.estimated ? 'Estimated' : 'Operational'}</span></div>
      <dl className="fire-output-dl">
        <dt>Available units</dt><dd>{units.length}</dd>
        <dt>Nearest unit</dt><dd>{response.nearest_unit_km == null ? 'Unavailable' : `${response.nearest_unit_km} km`}</dd>
        <dt>Response estimate</dt><dd>{response.estimated_response_minutes == null ? 'Unavailable' : `${response.estimated_response_minutes} min`}</dd>
      </dl>
      {units.length ? <div className="fire-response-units">{units.map((unit, index) => <article key={unit.unit_id || unit.id || index}>
        <strong>{unit.name || unit.unit_id || unit.id || `Response unit ${index + 1}`}</strong>
        <span>{[unit.status, unit.distance_km == null ? null : `${unit.distance_km} km away`].filter(Boolean).join(' · ') || 'Details unavailable'}</span>
      </article>)}</div> : <p className="fire-output-description">{response.note || 'No response units are available in the backend dataset.'}</p>}
    </div>;
  }

  const events = outputs.events || [];
  return <div className="fire-output-view">
    <div className="fire-output-heading"><h2>Event history</h2><span>{events.length} events</span></div>
    <div className="fire-event-list">
      {events.map((event, index) => {
        const details = Object.entries(event.data || {}).map(([key, value]) => `${displayName(key)}: ${value}`).join(' · ');
        return <article key={`${event.event}-${index}`}>
          <div><strong>{displayName(event.event?.replace('simulation.', '') || 'event')}</strong><span>{event.status}</span></div>
          <time>{formatTimestamp(event.timestamp)}</time>
          {details && <small>{details}</small>}
        </article>;
      })}
      {!events.length && <p className="fire-output-empty">No lifecycle events were returned.</p>}
    </div>
  </div>;
}

export default function FireSimulation() {
  const [fireId, setFireId] = useState(() => new URLSearchParams(window.location.search).get('fire_id') || '');
  const [inputValue, setInputValue] = useState(fireId);
  const [fire, setFire] = useState(null);
  const [isBackendFire, setIsBackendFire] = useState(false);
  const [loading, setLoading] = useState(Boolean(fireId));
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState('');
  const [backendError, setBackendError] = useState('');
  const [backendLoading, setBackendLoading] = useState(false);
  const [backendOutputs, setBackendOutputs] = useState(null);
  const [outputsLoading, setOutputsLoading] = useState(false);
  const [activeOutputTab, setActiveOutputTab] = useState('risk');
  const [legacyStatus, setLegacyStatus] = useState('Contained');
  const [legacyActionLoading, setLegacyActionLoading] = useState(false);
  const [legacyActionMessage, setLegacyActionMessage] = useState('');

  const loadFire = useCallback(async id => {
    if (!id) return;
    setLoading(true);
    setError('');
    setNotFound(false);
    try {
      const clientUrl = new URL('/supabaseClient.js', window.location.origin).href;
      const { supabase } = await import(/* @vite-ignore */ clientUrl);
      const { data, error: queryError } = await supabase.from('fire_simulations').select('fire_id, core_polygon, uncertainty_polygon, wind_used, priority_list, confidence, intensity, simulation_deviation, generated_at').eq('fire_id', id).maybeSingle();
      if (queryError) throw queryError;
      setFire(data);
      setIsBackendFire(false);
      setNotFound(!data);
    } catch (caught) {
      setError(caught?.message || 'The fire event could not be loaded. Check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (fireId) loadFire(fireId);
  }, [fireId, loadFire]);

  const submitFireId = event => {
    event.preventDefault();
    const nextId = inputValue.trim();
    if (!nextId) return;
    const url = new URL(window.location.href);
    url.searchParams.set('fire_id', nextId);
    window.history.replaceState({}, '', url);
    setFireId(nextId);
  };

  const loadBackendOutputs = async simulationId => {
    setOutputsLoading(true);
    try {
      const outputs = await getBackendSimulationOutputs(simulationId);
      setBackendOutputs(outputs);
      setFire(current => current?.fire_id === simulationId ? {
        ...current,
        core_polygon: outputs.riskMap,
        uncertainty_polygon: outputs.fireSpread,
        timeline: outputs.timeline
      } : current);
    } catch (caught) {
      setBackendOutputs(null);
      setBackendError(caught?.message || 'Simulation outputs could not be loaded.');
    } finally {
      setOutputsLoading(false);
    }
  };

  const submitBackendSimulation = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBackendLoading(true);
    setBackendError('');
    setBackendOutputs(null);
    try {
      const created = await createBackendSimulation({
        latitude: Number(form.get('latitude')),
        longitude: Number(form.get('longitude')),
        radius: Number(form.get('radius')),
        duration_minutes: Number(form.get('duration_minutes')),
        time_step_minutes: Number(form.get('time_step_minutes')),
        scenario: form.get('scenario'),
        fire_id: form.get('fire_id') || 'sample_fire_01'
      });
      const completed = await runBackendSimulation(created.simulation_id);
      setFire(toFireRecord(completed));
      setIsBackendFire(true);
      setActiveOutputTab('risk');
      setNotFound(false);
      await loadBackendOutputs(created.simulation_id);
    } catch (caught) {
      setBackendError(caught?.message || 'The backend simulation could not be started.');
    } finally {
      setBackendLoading(false);
    }
  };

  const refresh = async () => {
    if (!isBackendFire) return loadFire(fireId);
    setLoading(true);
    setBackendError('');
    try {
      const simulation = await getBackendSimulation(fire.fire_id);
      setFire(toFireRecord(simulation));
      await loadBackendOutputs(fire.fire_id);
    } catch (caught) {
      setBackendError(caught?.message || 'The backend simulation could not be refreshed.');
    } finally {
      setLoading(false);
    }
  };

  const advanceLegacyCycle = async () => {
    setLegacyActionLoading(true);
    setLegacyActionMessage('');
    try {
      const result = await advanceBackendFireCycle(fire.fire_id, true);
      if (result.error) throw new Error(result.error);
      setLegacyActionMessage(`Cycle ${result.cycle_count} completed. ${result.changes?.join(' ') || ''}`.trim());
    } catch (caught) {
      setLegacyActionMessage(caught?.message || 'Could not advance this fire cycle.');
    } finally {
      setLegacyActionLoading(false);
    }
  };

  const updateLegacyStatus = async () => {
    setLegacyActionLoading(true);
    setLegacyActionMessage('');
    try {
      const result = await updateBackendFireStatus(fire.fire_id, legacyStatus);
      if (result.error) throw new Error(result.error);
      setFire(current => ({ ...current, final_status: legacyStatus }));
      setLegacyActionMessage(result.message || `Fire marked as ${legacyStatus}.`);
    } catch (caught) {
      setLegacyActionMessage(caught?.message || 'Could not update this fire status.');
    } finally {
      setLegacyActionLoading(false);
    }
  };
  const items = fire?.priority_list || [];
  const confidence = fire?.confidence || 'Moderate';
  const wind = fire?.wind_used || {};

  if (loading && !fire) return <FireSkeleton />;

  return <div className="fire-detail-layout">
    {fire ? <FireMap fire={fire} /> : <div className="fire-map-empty"><div className="fire-map-empty-mark">VR</div><span>Fire event map</span></div>}
    <aside className="fire-panel">
      <div className="fire-panel-heading">
        <div><span className="fire-eyebrow">{isBackendFire ? 'Live backend simulation' : 'Stage 4 + 5 output'}</span><h1>Fire event</h1></div>
        {fire && isBackendFire && <button className="fire-new-button" type="button" onClick={() => { setFire(null); setIsBackendFire(false); setBackendOutputs(null); setBackendError(''); }} title="Start another simulation">New run</button>}
        {fire && <button className="fire-refresh-button" type="button" onClick={refresh} disabled={loading} aria-label="Refresh fire event" title="Refresh fire event">
          <svg viewBox="0 0 24 24" aria-hidden="true" className={loading ? 'is-spinning' : ''}><path d="M20 7v5h-5M4 17v-5h5" /><path d="M5.5 9a7 7 0 0 1 11.9-2L20 12M4 12l2.6 5a7 7 0 0 0 11.9-2" /></svg>
        </button>}
      </div>

      {!fireId && !isBackendFire && <section className="fire-state-block fire-backend-form-block">
        <h2>Run a new simulation</h2>
        <p>Send a location and scenario to the deployed wildfire simulation API.</p>
        <form className="fire-id-form" onSubmit={submitBackendSimulation}>
          <div className="fire-backend-grid">
            <label>Latitude<input name="latitude" type="number" min="-90" max="90" step="any" defaultValue="30.1472" required /></label>
            <label>Longitude<input name="longitude" type="number" min="-180" max="180" step="any" defaultValue="78.5925" required /></label>
            <label>Radius (km)<input name="radius" type="number" min="0.1" max="50" step="any" defaultValue="3" required /></label>
            <label>Duration (minutes)<input name="duration_minutes" type="number" min="1" max="1440" step="1" defaultValue="120" required /></label>
            <label>Time step (minutes)<input name="time_step_minutes" type="number" min="1" max="240" step="1" defaultValue="15" required /></label>
          </div>
          <label>FIRMS cache ID<input name="fire_id" placeholder="sample_fire_01" /></label>
          <label>Scenario<select name="scenario" defaultValue="normal">
            <option value="normal">Normal</option>
            <option value="high_wind">High wind</option>
            <option value="extreme_heat">Extreme heat</option>
            <option value="low_humidity">Low humidity</option>
            <option value="high_fuel_load">High fuel load</option>
            <option value="high_biodiversity_sensitivity">High biodiversity sensitivity</option>
          </select></label>
          <button type="submit" disabled={backendLoading}>{backendLoading ? 'Running…' : 'Run simulation'}</button>
        </form>
      </section>}

      {backendError && <div className="fire-message fire-message-error" role="alert"><strong>Backend request failed</strong><span>{backendError}</span></div>}

      {!fire && !fireId && <section className="fire-state-block">
        <h2>Load a fire simulation</h2>
        <p>Enter a confirmed fire event ID to view its latest spread simulation and refinement.</p>
        <form className="fire-id-form" onSubmit={submitFireId}>
          <label htmlFor="fire-id-input">Fire ID</label>
          <input id="fire-id-input" value={inputValue} onChange={event => setInputValue(event.target.value)} placeholder="e.g. fire-event-001" />
          <button type="submit">Load event</button>
        </form>
      </section>}

      {error && <div className="fire-message fire-message-error" role="alert"><strong>Unable to load fire event</strong><span>{error}</span>{fireId && <button type="button" onClick={refresh}>Try again</button>}</div>}
      {notFound && <section className="fire-state-block fire-not-found" role="status"><span className="fire-state-code">404</span><h2>Fire event not found</h2><p>No simulation was found for <code>{fireId}</code>. Check the ID and try again.</p><form className="fire-id-form" onSubmit={submitFireId}><label htmlFor="fire-id-input">Fire ID</label><input id="fire-id-input" value={inputValue} onChange={event => setInputValue(event.target.value)} /><button type="submit">Search</button></form></section>}

      {fire && <>
        <div className="fire-event-meta"><span>{isBackendFire ? 'SIMULATION ID' : 'EVENT ID'}</span><code>{fire.fire_id}</code><span>GENERATED</span><code>{fire.generated_at ? new Date(fire.generated_at).toISOString() : '—'}</code></div>
        <div className="fire-metric-grid">
          <div className="fire-metric"><span>{isBackendFire ? 'Risk class' : 'Confidence'}</span><strong className="fire-confidence" style={{ '--confidence-color': tokenColor(RISK_TOKEN[confidence] || '--risk-moderate') }}>{confidence}</strong></div>
          <div className="fire-metric"><span>{isBackendFire ? 'Risk score' : 'Intensity'}</span><strong>{fire.intensity || '—'}</strong></div>
        </div>
        {isBackendFire ? <>
          <div className="fire-backend-facts"><span>Status</span><strong>{fire.backend_status}</strong><span>Forecast steps</span><strong>{backendOutputs?.timeline.length ?? fire.timeline.length}</strong><span>Settlements / infrastructure</span><strong>{fire.affected_assets.settlements || 0} / {fire.affected_assets.infrastructure || 0}</strong></div>
          <div className="fire-output-tabs" role="tablist" aria-label="Simulation outputs">
            {OUTPUT_TABS.map(tab => <button key={tab.id} type="button" role="tab" aria-selected={activeOutputTab === tab.id} className={activeOutputTab === tab.id ? 'active' : ''} onClick={() => setActiveOutputTab(tab.id)}>{tab.label}</button>)}
          </div>
          <section className="fire-output-panel" role="tabpanel">
            <SimulationOutputView tab={activeOutputTab} fire={fire} outputs={backendOutputs} loading={outputsLoading} onRetry={() => loadBackendOutputs(fire.fire_id)} />
          </section>
        </> : <>
          <div className="fire-wind-row"><div><span>Wind used</span><strong>{wind.speed ?? '—'} · {wind.direction ?? '—'}</strong></div><WindArrow direction={wind.direction} /></div>
          {fire.simulation_deviation && <div className="fire-deviation-notice"><span className="fire-notice-icon">i</span><p>Observed spread differed from the original prediction. The simulation has been corrected to reflect the updated fire perimeter.</p></div>}
          <section className="fire-priority-section">
            <div className="fire-section-heading"><h2>Priority locations</h2><span>{items.length}</span></div>
            <div className="fire-priority-list">
              {PRIORITIES.map(priority => {
                const group = items.filter(item => normalizedPriority(item.priority) === priority);
                if (!group.length) return null;
                return <div className="fire-priority-group" key={priority}>
                  <h3><span style={{ backgroundColor: tokenColor(PRIORITY_TOKEN[priority]) }} />{priority}<small>{group.length}</small></h3>
                  {group.map((item, index) => <article className="fire-priority-item" key={`${item.name}-${index}`}>
                    <span className={`fire-item-shape ${markerShape(item.type)}`} style={{ '--marker-color': tokenColor(PRIORITY_TOKEN[normalizedPriority(item.priority)]) }} />
                    <div className="fire-item-copy"><strong>{item.name}</strong><span>{item.type}</span></div>
                    <button type="button" className="fire-view-marker" onClick={() => window.__fireDetailMap?.flyTo({ center: [Number(item.lng), Number(item.lat)], zoom: 10, duration: 850 })}>View on map</button>
                  </article>)}
                </div>;
              })}
              {!items.length && <p className="fire-empty-list">No priority locations recorded.</p>}
            </div>
          </section>
          <section className="fire-legacy-actions">
            <div className="fire-section-heading"><h2>Archived fire controls</h2></div>
            <p>These actions require a matching Stage 4 archive on the backend.</p>
            <button type="button" onClick={advanceLegacyCycle} disabled={legacyActionLoading}>{legacyActionLoading ? 'Working…' : 'Advance fire cycle'}</button>
            <div className="fire-legacy-status">
              <select aria-label="Final fire status" value={legacyStatus} onChange={event => setLegacyStatus(event.target.value)}>
                <option>Contained</option><option>False Alarm</option><option>No Fire</option>
              </select>
              <button type="button" onClick={updateLegacyStatus} disabled={legacyActionLoading}>Set final status</button>
            </div>
            {fire.final_status && <span className="fire-legacy-current">Current status: {fire.final_status}</span>}
            {legacyActionMessage && <p className="fire-legacy-message" role="status">{legacyActionMessage}</p>}
          </section>
        </>}
      </>}
    </aside>
  </div>;
}
