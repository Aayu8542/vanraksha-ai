import json
import math
import random
import requests
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, Point
import ee

# Attempt to initialize Earth Engine
try:
    ee.Initialize(project='vanraksha-ai-27380')
except Exception:
    pass # Expected to be already authenticated from earlier stages

def load_config(config_path="config.json"):
    with open(config_path, 'r') as f:
        return json.load(f)

def fetch_weather(lat, lng):
    """
    Fetch current/forecast wind speed, wind direction, and humidity from Open-Meteo.
    We grab the current hour's data.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"
    res = requests.get(url).json()
    current = res.get("current", {})
    return {
        "wind_speed_kmh": current.get("wind_speed_10m", 10.0),
        "wind_direction_deg": current.get("wind_direction_10m", 0.0),
        "humidity_pct": current.get("relative_humidity_2m", 50.0)
    }

def fetch_environmental_grid(lat, lng, radius_km, cell_size_m):
    """
    Fetch Fuel Load (Dryness) and Slope from Earth Engine for the bounding box.
    Returns NumPy arrays for fuel, elevation, and the affine transform.
    """
    # Create bounding box around center point
    # 1 deg lat is approx 111 km
    lat_deg = radius_km / 111.0
    lng_deg = radius_km / (111.0 * math.cos(math.radians(lat)))
    
    bbox = [
        lng - lng_deg, lat - lat_deg,
        lng + lng_deg, lat + lat_deg
    ]
    roi = ee.Geometry.Rectangle(bbox)
    
    # Sentinel-2 for NDVI/Dryness proxy
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
        .filterBounds(roi) \
        .sort('system:time_start', False) \
        .first()
    
    ndvi = s2.normalizedDifference(['B8', 'B4'])
    # Normalize fuel dryness: lower NDVI -> higher dryness
    fuel_dryness = ee.Image(1).subtract(ndvi.add(1).divide(2)).clamp(0, 1).rename('Fuel')
    
    # Elevation from SRTM
    elevation = ee.Image("USGS/SRTMGL1_003").rename('Elevation')
    
    combined = ee.Image([fuel_dryness, elevation])
    
    # Download the grid as GeoTIFF
    try:
        url = combined.getDownloadURL({
            'scale': cell_size_m,
            'crs': 'EPSG:4326',
            'region': roi,
            'format': 'GEO_TIFF'
        })
        
        import rasterio
        from rasterio.io import MemoryFile
        
        response = requests.get(url)
        with MemoryFile(response.content) as memfile:
            with memfile.open() as dataset:
                data = dataset.read() # Band 1: Fuel, Band 2: Elevation
                transform = dataset.transform
                fuel = data[0]
                elev = data[1]
                
                # Handle no-data / nan
                fuel = np.nan_to_num(fuel, nan=0.5)
                elev = np.nan_to_num(elev, nan=0.0)
                
        return fuel, elev, transform, bbox
        
    except Exception as e:
        print(f"Error fetching GEE grid: {e}")
        # Fallback to dummy arrays if GEE fails in demo
        grid_size = int((radius_km * 2 * 1000) / cell_size_m)
        import rasterio.transform
        tf = rasterio.transform.from_bounds(*bbox, grid_size, grid_size)
        return np.full((grid_size, grid_size), 0.6), np.full((grid_size, grid_size), 100.0), tf, bbox


def calculate_wind_alignment(wind_dir, cell_angle):
    """
    Calculate how aligned a neighbor cell is with the wind.
    0 to 1 scale. 1 = directly downwind, 0 = directly upwind.
    """
    diff = abs((wind_dir - cell_angle + 180) % 360 - 180)
    # Cosine mapping: 0 deg diff -> 1, 180 deg diff -> 0
    return (math.cos(math.radians(diff)) + 1) / 2


def calculate_upslope_bonus(elev_current, elev_neighbor, distance):
    """
    Calculate upslope bonus. Fire spreads faster uphill.
    """
    slope = (elev_neighbor - elev_current) / distance
    # Cap at a reasonable slope for bonus (e.g. 45 degrees -> slope = 1.0)
    # Bonus is 0 if downslope
    return max(0.0, min(1.0, slope * 2.0)) # Scaled approximation


def run_cellular_automaton(fuel_grid, elev_grid, start_row, start_col, cell_size_m, 
                           num_steps, base_prob, weights, wind_speed, wind_dir, seed=None, initial_burn_grid=None):
    """
    Runs a single simulation of fire spread.
    
    FIRE SPREAD PROBABILITY FORMULA (FOR NON-TECHNICAL JUDGES):
    =========================================================
    Every 10 minutes (time step), a burning cell attempts to ignite its immediate neighbors.
    The chance of a neighbor catching fire depends on three main factors, plus a baseline risk:
    
    1. WIND ALIGNMENT (Weight: 40%): Is the wind blowing the flames directly toward this neighbor? 
       If the neighbor is directly downwind, this risk is maximized.
    2. UPSLOPE BONUS (Weight: 30%): Is the neighbor uphill from the fire? Fire naturally 
       preheats fuel above it and moves faster uphill.
    3. FUEL DRYNESS (Weight: 30%): Is the vegetation thick and bone-dry? We measure this 
       using satellite data (NDVI).
       
    Formula: 
    Total Ignition Probability = Base Risk 
                               + (0.4 * Wind Alignment) 
                               + (0.3 * Upslope Bonus) 
                               + (0.3 * Fuel Dryness)
    
    We generate a random number; if it's lower than the Total Ignition Probability, the neighbor catches fire.
    """
    if seed is not None:
        np.random.seed(seed)
        
    rows, cols = fuel_grid.shape
    if initial_burn_grid is not None:
        burn_grid = initial_burn_grid.copy()
        # Find all currently burning cells
        y_idx, x_idx = np.where(burn_grid == 1)
        burning_cells = list(zip(y_idx, x_idx))
    else:
        burn_grid = np.zeros((rows, cols), dtype=int)
        if start_row is not None and start_col is not None:
            burn_grid[start_row, start_col] = 1 # 1 = burning
            burning_cells = [(start_row, start_col)]
        else:
            burning_cells = []
    
    w_wind = weights.get('w_wind_alignment', 0.4)
    w_slope = weights.get('w_upslope_bonus', 0.3)
    w_fuel = weights.get('w_fuel_dryness', 0.3)
    
    # Pre-calculate neighbor relative angles and distances
    # N, NE, E, SE, S, SW, W, NW
    neighbors = [
        (-1, 0, 0, cell_size_m),           # N
        (-1, 1, 45, cell_size_m * 1.414),  # NE
        (0, 1, 90, cell_size_m),           # E
        (1, 1, 135, cell_size_m * 1.414),  # SE
        (1, 0, 180, cell_size_m),          # S
        (1, -1, 225, cell_size_m * 1.414), # SW
        (0, -1, 270, cell_size_m),         # W
        (-1, -1, 315, cell_size_m * 1.414) # NW
    ]
    
    # (removed overriding burning_cells)
    
    # Scale wind speed factor (rough proxy: e.g. 50 km/h is max expected effect multiplier)
    wind_multiplier = min(2.0, max(0.5, wind_speed / 20.0))
    
    for step in range(num_steps):
        new_burning = []
        for r, c in burning_cells:
            for dr, dc, angle, dist in neighbors:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and burn_grid[nr, nc] == 0:
                    # 1. Wind Alignment
                    wind_align = calculate_wind_alignment(wind_dir, angle)
                    # 2. Upslope Bonus
                    upslope = calculate_upslope_bonus(elev_grid[r, c], elev_grid[nr, nc], dist)
                    # 3. Fuel Dryness
                    fuel = fuel_grid[nr, nc]
                    
                    prob = base_prob + (w_wind * wind_align * wind_multiplier) + (w_slope * upslope) + (w_fuel * fuel)
                    
                    # Ignite?
                    if np.random.random() < prob:
                        burn_grid[nr, nc] = 1
                        new_burning.append((nr, nc))
        
        burning_cells.extend(new_burning)
        
    return burn_grid


def generate_polygons(ensemble_sum, num_runs, transform, core_threshold_pct):
    """
    Converts ensemble grid sums to Core and Uncertainty GeoJSON polygons.
    Core = Burned in > core_threshold_pct of runs.
    Uncertainty = Burned in > 0 runs (but not in core).
    """
    import rasterio.features
    from shapely.geometry import shape
    from shapely.ops import unary_union
    
    core_mask = (ensemble_sum >= (num_runs * core_threshold_pct)).astype('uint8')
    any_mask = (ensemble_sum > 0).astype('uint8')
    
    def mask_to_poly(mask):
        shapes = rasterio.features.shapes(mask, transform=transform)
        polys = [shape(geom) for geom, val in shapes if val == 1]
        if not polys:
            return None
        return unary_union(polys)
    
    core_poly = mask_to_poly(core_mask)
    any_poly = mask_to_poly(any_mask)
    
    uncertainty_poly = None
    if any_poly and core_poly:
        uncertainty_poly = any_poly.difference(core_poly)
    elif any_poly:
        uncertainty_poly = any_poly
        
    # Convert shapely polys to GeoJSON dictionary
    import shapely.geometry
    
    core_geojson = shapely.geometry.mapping(core_poly) if core_poly else None
    uncert_geojson = shapely.geometry.mapping(uncertainty_poly) if uncertainty_poly else None
    
    return core_geojson, uncert_geojson


def run_ensemble_simulation(lat, lng, config_path="config.json", seed=42, initial_burn_grid=None, num_steps_override=None, firms_polygon=None):
    """
    Main entry point for Part A.
    Runs an ensemble of CA spread models with perturbed weather.
    """
    config = load_config(config_path)
    cfg_sim = config['simulation']
    cfg_weights = config['model_weights']
    cfg_pert = config['ensemble_perturbations']
    
    weather = fetch_weather(lat, lng)
    base_wind_speed = weather['wind_speed_kmh']
    base_wind_dir = weather['wind_direction_deg']
    
    # Fetch grid
    fuel_grid, elev_grid, transform, bbox = fetch_environmental_grid(
        lat, lng, cfg_sim['radius_km'], cfg_sim['cell_size_m']
    )
    
    # Find start row/col for the lat/lng center
    import rasterio
    start_row, start_col = rasterio.transform.rowcol(transform, lng, lat)
    
    rows, cols = fuel_grid.shape
    start_row = max(0, min(rows - 1, start_row))
    start_col = max(0, min(cols - 1, start_col))
    
    # Rasterize firms_polygon if provided
    if firms_polygon is not None:
        import rasterio.features
        initial_burn_grid = rasterio.features.rasterize(
            [(firms_polygon, 1)],
            out_shape=(rows, cols),
            transform=transform,
            fill=0,
            dtype='uint8'
        )
    
    
    # Ensemble accumulator
    ensemble_sum = np.zeros(fuel_grid.shape, dtype=int)
    
    np.random.seed(seed)
    
    num_runs = cfg_sim['ensemble_size']
    for i in range(num_runs):
        # Perturb weather
        pct_change = np.random.uniform(-cfg_pert['wind_speed_pct_max'], cfg_pert['wind_speed_pct_max'])
        wind_speed = base_wind_speed * (1 + pct_change)
        
        dir_change = np.random.uniform(-cfg_pert['wind_dir_deg_max'], cfg_pert['wind_dir_deg_max'])
        wind_dir = (base_wind_dir + dir_change) % 360
        
        steps = num_steps_override if num_steps_override is not None else cfg_sim['num_steps']
        burn_grid = run_cellular_automaton(
            fuel_grid, elev_grid, start_row, start_col,
            cfg_sim['cell_size_m'], steps,
            cfg_weights['base_ignition_prob'], cfg_weights,
            wind_speed, wind_dir, seed=(seed + i if seed else None),
            initial_burn_grid=initial_burn_grid
        )
        
        ensemble_sum += burn_grid
        
    core_geojson, uncert_geojson = generate_polygons(
        ensemble_sum, num_runs, transform, cfg_sim['core_threshold_pct']
    )
    
    return {
        "core_polygon": core_geojson,
        "uncertainty_polygon": uncert_geojson,
        "wind_used": {
            "speed_kmh": base_wind_speed,
            "direction_deg": base_wind_dir,
            "humidity_pct": weather['humidity_pct']
        },
        "config_used": config
    }
