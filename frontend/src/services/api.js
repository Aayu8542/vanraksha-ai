import { GBIF_SPECIES_SEED, AQI_SEED } from '../data/phase2Seed.js';

const BACKEND_URL = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');

async function requestBackend(path, options = {}) {
  if (!BACKEND_URL) {
    throw new Error('Set VITE_API_BASE_URL in the frontend deployment to connect to the backend.');
  }

  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers: { ...(options.body == null ? {} : { 'Content-Type': 'application/json' }), ...options.headers }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Backend request failed (${response.status})`);
  return data;
}

export function createBackendSimulation(payload) {
  return requestBackend('/api/simulation/start', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function runBackendSimulation(simulationId) {
  return requestBackend(`/api/simulation/${encodeURIComponent(simulationId)}/run`, { method: 'POST' });
}

export function getBackendSimulation(simulationId) {
  return requestBackend(`/api/simulation/${encodeURIComponent(simulationId)}`);
}

export function getBackendSimulationOutput(simulationId, output) {
  const supportedOutputs = new Set(['timeline', 'fire-spread', 'risk-map', 'biodiversity-impact', 'response-plan']);
  if (!supportedOutputs.has(output)) throw new Error(`Unsupported simulation output: ${output}`);
  return requestBackend(`/api/simulation/${encodeURIComponent(simulationId)}/${output}`);
}

export async function getBackendSimulationEvents(simulationId) {
  if (!BACKEND_URL) {
    throw new Error('Set VITE_API_BASE_URL in the frontend deployment to connect to the backend.');
  }

  const response = await fetch(`${BACKEND_URL}/api/simulation/${encodeURIComponent(simulationId)}/events`, {
    headers: { Accept: 'text/event-stream' }
  });
  const text = await response.text();
  if (!response.ok) {
    let message = `Backend request failed (${response.status})`;
    try {
      message = JSON.parse(text).error || message;
    } catch {
      message = text || message;
    }
    throw new Error(message);
  }

  return text.trim().split(/\r?\n\r?\n/).filter(Boolean).map(block => {
    const eventName = block.match(/^event:\s*(.+)$/m)?.[1];
    const data = block.match(/^data:\s*(.+)$/m)?.[1];
    if (!data) return null;
    const parsed = JSON.parse(data);
    return { ...parsed, event: parsed.event || eventName };
  }).filter(Boolean);
}

export async function getBackendSimulationOutputs(simulationId) {
  const [timeline, fireSpread, riskMap, biodiversity, response, events] = await Promise.all([
    getBackendSimulationOutput(simulationId, 'timeline'),
    getBackendSimulationOutput(simulationId, 'fire-spread'),
    getBackendSimulationOutput(simulationId, 'risk-map'),
    getBackendSimulationOutput(simulationId, 'biodiversity-impact'),
    getBackendSimulationOutput(simulationId, 'response-plan'),
    getBackendSimulationEvents(simulationId)
  ]);
  return { timeline, fireSpread, riskMap, biodiversity, response, events };
}

export function advanceBackendFireCycle(fireId, demoMode = true) {
  return requestBackend('/api/advance_cycle', {
    method: 'POST',
    body: JSON.stringify({ fire_id: fireId, demo_mode: demoMode })
  });
}

export function updateBackendFireStatus(fireId, status) {
  return requestBackend('/api/update_status', {
    method: 'POST',
    body: JSON.stringify({ fire_id: fireId, status })
  });
}

export async function fetchGBIFOccurrences() {
  const result = [];
  for (const sp of GBIF_SPECIES_SEED) {
    try {
      const url = `https://api.gbif.org/v1/occurrence/search?country=IN&taxonKey=${sp.taxonKey}&hasCoordinate=true&limit=40&fields=decimalLatitude,decimalLongitude,species,taxonKey`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const points = (data.results || []).filter(r => r.decimalLatitude && r.decimalLongitude).map(r => ({ lat: r.decimalLatitude, lng: r.decimalLongitude, species: sp.name, color: sp.color, dot: sp.dot, emoji: sp.emoji }));
      result.push(...points);
    } catch {
      result.push(...sp.fallback.map(([lat, lng]) => ({ lat, lng, species: sp.name, color: sp.color, dot: sp.dot, emoji: sp.emoji })));
    }
  }
  return result;
}

export async function fetchAirQuality() {
  try {
    const res = await fetch('https://api.openaq.org/v2/locations?country=IN&limit=8&has_geo=true&order_by=lastUpdated&sort=desc');
    if (!res.ok) throw new Error('OpenAQ request failed');
    const data = await res.json();
    const rows = (data.results || []).slice(0, 8).map(r => ({ city: r.city || r.name || 'Unknown', lat: r.coordinates?.latitude, lng: r.coordinates?.longitude, aqi: null, pm25: null, pm10: null }));
    return rows.length ? rows : AQI_SEED;
  } catch {
    return AQI_SEED;
  }
}
