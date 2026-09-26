import json
import ee
import os
import numpy as np

# Initialize Earth Engine if not already initialized
try:
    ee.Initialize(project='vanraksha-ai-27380')
except Exception:
    ee.Authenticate()
    ee.Initialize(project='vanraksha-ai-27380')


def load_config(config_path: str = "config.json"):
    """
    Load weights and thresholds from Phase 1 configuration.
    """
    if not os.path.exists(config_path):
        # Create dummy config for fallback, normally should fail or be provided
        print(f"Warning: {config_path} not found. Using default weights.")
        return {
            "weights": {
                "w_thermal": 0.4,
                "w_ndvi": 0.3,
                "w_slope": 0.15,
                "w_dryness": 0.15
            },
            "thresholds": {
                "low_confidence": 0.4,
                "medium_confidence": 0.65,
                "high_confidence": 0.85
            }
        }
    
    with open(config_path, 'r') as f:
        return json.load(f)


def get_environmental_layers(roi_ee: ee.Geometry):
    """
    Fetch and return Phase 1 environmental layers clipped to ROI.
    """
    # 1. NDVI (Sentinel-2 or Landsat or MODIS)
    # Using Sentinel-2 (latest available cloud-free image)
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
        .filterBounds(roi_ee) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) \
        .sort('system:time_start', False) \
        .first()
    
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    # 2. SRTM Slope
    srtm = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(srtm).rename('Slope')
    
    # 3. CHIRPS Dryness (proxy for precipitation deficit / drought)
    # Get last 30 days of precipitation
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
        .filterBounds(roi_ee) \
        .filterDate(ee.Date(s2.get('system:time_start')).advance(-30, 'day'), 
                    s2.get('system:time_start')) \
        .sum().rename('Precipitation')
    
    # Simple dryness index: invert precipitation and normalize (rough proxy)
    # Assuming max precip in 30 days is around 300mm for scaling
    dryness = ee.Image(300).subtract(chirps).divide(300).clamp(0, 1).rename('Dryness')
    
    # Thermal anomaly proxy (using MODIS active fire or LST as a stand-in for Phase 1 flags, 
    # but here we can just use MODIS LST normalized)
    modis_lst = ee.ImageCollection("MODIS/061/MOD11A1") \
        .filterBounds(roi_ee) \
        .sort('system:time_start', False) \
        .first()
    
    # Scale LST to Kelvin, then rough normalization to 0-1 (e.g. 290K to 330K)
    lst = modis_lst.select('LST_Day_1km').multiply(0.02).rename('Thermal')
    thermal_norm = lst.subtract(290).divide(40).clamp(0, 1).rename('ThermalNorm')
    
    # Normalize NDVI (lower NDVI = higher fire risk)
    # Invert NDVI (-1 to 1) to (0 to 1) where low NDVI is 1
    ndvi_risk = ee.Image(1).subtract(ndvi.add(1).divide(2)).clamp(0, 1).rename('NdviRisk')
    
    # Normalize Slope (0 to 90 degrees)
    slope_norm = slope.divide(90).clamp(0, 1).rename('SlopeNorm')
    
    return ee.Image([thermal_norm, ndvi_risk, slope_norm, dryness])


def compute_risk_score(roi_ee: ee.Geometry, eligible_mask: ee.Image, config_path: str = "config.json"):
    """
    Computes high-resolution risk probability score for each 200m sub-cell.
    Returns Earth Engine Image of scores.
    """
    config = load_config(config_path)
    weights = config.get("weights", {})
    w_thermal = weights.get("w_thermal", 0.4)
    w_ndvi = weights.get("w_ndvi", 0.3)
    w_slope = weights.get("w_slope", 0.15)
    w_dryness = weights.get("w_dryness", 0.15)
    
    layers = get_environmental_layers(roi_ee)
    
    thermal_risk = layers.select('ThermalNorm').multiply(w_thermal)
    ndvi_risk = layers.select('NdviRisk').multiply(w_ndvi)
    slope_risk = layers.select('SlopeNorm').multiply(w_slope)
    dryness_risk = layers.select('Dryness').multiply(w_dryness)
    
    # Sum up the weighted risks
    total_risk = thermal_risk.add(ndvi_risk).add(slope_risk).add(dryness_risk).rename('RiskScore')
    
    # Apply eligibility mask (non-eligible areas get score 0)
    final_score = total_risk.updateMask(eligible_mask).unmask(0)
    
    return final_score


def export_score_to_numpy(roi_ee: ee.Geometry, score_image: ee.Image, scale: int = 200):
    """
    Exports the score image to a NumPy array for local processing.
    Resamples to the specified scale (default 200m).
    """
    # Sample the image at the given scale
    # Since we need a grid, we can use ee.Image.sampleRectangle or getDownloadURL and read with rasterio.
    # For small ROIs (4km x 4km), getRegion or sampleRectangle is fine.
    
    # Get bounding box coordinates
    coords = roi_ee.bounds().getInfo()['coordinates'][0]
    
    try:
        # Request a GeoTIFF download URL and use rasterio or requests
        url = score_image.getDownloadURL({
            'scale': scale,
            'crs': 'EPSG:4326',
            'region': roi_ee,
            'format': 'GEO_TIFF'
        })
        
        import requests
        import rasterio
        from rasterio.io import MemoryFile
        
        response = requests.get(url)
        with MemoryFile(response.content) as memfile:
            with memfile.open() as dataset:
                data = dataset.read(1)
                transform = dataset.transform
                
        return data, transform
        
    except Exception as e:
        print(f"Error downloading score image: {e}")
        return None, None
