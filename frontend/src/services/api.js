import { GBIF_SPECIES_SEED, AQI_SEED } from '../data/phase2Seed.js';

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
