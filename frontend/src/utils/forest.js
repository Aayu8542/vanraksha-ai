export function threatColor(threat) {
  if (threat >= 60) return '#ef4444';
  if (threat >= 45) return '#f59e0b';
  return '#38bdf8';
}

export function ndviLabel(val) {
  const n = Number(val);
  if (n < 0.2) return 'Bare soil';
  if (n < 0.35) return 'Sparse veg.';
  if (n < 0.5) return 'Grassland';
  if (n < 0.65) return 'Mixed forest';
  if (n < 0.8) return 'Dense forest';
  return 'Very dense';
}

export function ndviColor(ndvi) {
  const n = Math.max(0, Math.min(1, ndvi));
  if (n < 0.2) return '#7a3605';
  if (n < 0.4) return '#c8a000';
  if (n < 0.6) return '#3dcc73';
  if (n < 0.8) return '#168746';
  return '#004d18';
}

export function createCircleCoords(lng, lat, radius, steps = 32) {
  const coords = [];
  for (let i = 0; i <= steps; i += 1) {
    const angle = (i / steps) * Math.PI * 2;
    coords.push([lng + Math.cos(angle) * radius, lat + Math.sin(angle) * radius]);
  }
  return coords;
}

export function getNDVIForCell(lat, lng, year) {
  const seed = Math.sin(lat * 127.1 + lng * 311.7) * 0.5 + 0.5;
  let base;
  if ((lat > 22 && lng > 88) || (lat > 25 && lng > 90)) base = 0.75;
  else if (lat < 14 && lng < 78) base = 0.72;
  else if (lat > 28 && lng < 80) base = 0.62;
  else if (lat < 25 && lng < 76) base = 0.4;
  else if (lat > 20 && lng < 78) base = 0.55;
  else base = 0.58;
  const yearFactor = (year - 2000) * -0.002;
  const improvement = year > 2019 ? 0.01 : 0;
  return Math.max(0.05, Math.min(0.95, base + seed * 0.2 + yearFactor + improvement));
}

export function generateNDVIGrid(year) {
  const features = [];
  const step = 0.8;
  for (let lat = 8; lat < 37; lat += step) {
    for (let lng = 68; lng < 97; lng += step) {
      const cLat = lat + step / 2;
      const cLng = lng + step / 2;
      if (cLat < 8 || cLat > 37 || cLng < 68 || cLng > 97) continue;
      if (cLat < 10 && cLng > 80) continue;
      if (cLat > 35 && cLng < 74) continue;
      if (cLat < 12 && cLng < 76) continue;
      if (cLng < 70 && cLat > 30) continue;
      const ndvi = getNDVIForCell(lat, lng, year);
      features.push({
        type: 'Feature',
        properties: { ndvi: ndvi.toFixed(2), color: ndviColor(ndvi) },
        geometry: { type: 'Polygon', coordinates: [[[lng, lat], [lng + step, lat], [lng + step, lat + step], [lng, lat + step], [lng, lat]]] }
      });
    }
  }
  return { type: 'FeatureCollection', features };
}

export function scanZone(lat, lng) {
  const seed = Math.abs(Math.sin(lat * 12.9898 + lng * 78.233));
  const score = Math.round(seed * 55 + 35);
  const ndvi = (Math.sin(lat * 7.1 + lng * 3.3) * 0.3 + 0.45).toFixed(2);
  const rainfall = Math.round(seed * 1200 + 400);
  const soilQuality = ['Poor', 'Fair', 'Good', 'Excellent'][Math.floor(seed * 4)];
  const carbonPotential = Math.round(seed * 120 + 40);
  const connectivity = (seed * 0.7 + 0.2).toFixed(2);
  const speciesBenefit = Math.round(seed * 15 + 5);
  const quality = score >= 75 ? 'excellent' : score >= 55 ? 'good' : 'moderate';
  const qualityLabel = quality === 'excellent' ? 'High Reforestation Potential' : quality === 'good' ? 'Moderate Potential' : 'Needs Intervention First';
  return { score, ndvi, rainfall, soilQuality, carbonPotential, connectivity, speciesBenefit, quality, qualityLabel };
}

export function calcCarbonSequestration(areaHa, vegetationType, years) {
  const rates = { 'Dense Forest': 8.5, 'Mixed Forest': 5.2, Grassland: 2.1, Mangrove: 12.3, 'Degraded Land': 1.4 };
  const rate = rates[vegetationType] || 4;
  const tonnesPerYear = areaHa * rate;
  const total = tonnesPerYear * years;
  return { tonnesPerYear, total, credits: total * 15 };
}
