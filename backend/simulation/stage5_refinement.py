import json
import os
import requests
import datetime
from shapely.geometry import Point, shape, mapping
from shapely.ops import unary_union
import pyproj
from functools import partial
from shapely.ops import transform
from part_a_simulation import run_ensemble_simulation

def load_config(config_path="config.json"):
    with open(config_path, 'r') as f:
        return json.load(f)

def fetch_firms_data(lat, lng, fire_id, demo_mode=False, buffer_km=5, time_window_hours=3):
    """
    Fetch FIRMS active fire points for the area.
    In demo_mode, loads from local cache.
    """
    if demo_mode:
        cache_path = os.path.join("..", "calibration", "firms_cache", f"{fire_id}.json")
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        else:
            print(f"Demo cache {cache_path} not found. Returning empty list.")
            return []
            
    # Live API call
    map_key = os.environ.get("FIRMS_MAP_KEY")
    if not map_key:
        print("Error: FIRMS_MAP_KEY environment variable not set.")
        return []
        
    deg_buffer = buffer_km / 111.0
    w, s, e, n = lng - deg_buffer, lat - deg_buffer, lng + deg_buffer, lat + deg_buffer
    coords = f"{w:.3f},{s:.3f},{e:.3f},{n:.3f}"
    
    # We fetch VIIRS SNPP and MODIS
    # Actually, FIRMS area API only accepts one source at a time.
    # We will fetch VIIRS_SNPP_NRT first
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_SNPP_NRT/{coords}/1"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        lines = response.text.strip().splitlines()
        if len(lines) <= 1:
            return [] # Only header or empty
            
        header = lines[0].split(',')
        points = []
        for line in lines[1:]:
            parts = line.split(',')
            row = dict(zip(header, parts))
            points.append({
                "latitude": float(row.get("latitude", 0)),
                "longitude": float(row.get("longitude", 0)),
                "frp": float(row.get("frp", 0)),
                "confidence": row.get("confidence", "nominal"),
                "satellite": "VIIRS_SNPP",
                "acq_time": row.get("acq_time", "")
            })
        return points
    except Exception as ex:
        print(f"Error fetching FIRMS data: {ex}")
        return []


def create_firms_perimeter(firms_points, viirs_pixel_m=187.5, modis_pixel_m=500.0):
    """
    Takes FIRMS point list, prefers VIIRS, buffers each point by half its footprint,
    and computes the union of all buffers as a single polygon.
    """
    if not firms_points:
        return None
        
    # Prefer VIIRS if mixed (though our fetch only gets VIIRS for simplicity/speed in demo)
    viirs_points = [p for p in firms_points if "VIIRS" in p.get("satellite", "")]
    target_points = viirs_points if viirs_points else firms_points
    
    # We buffer in a metric projection to ensure accurate sizing in meters
    # WGS84 -> Web Mercator or local UTM
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    project_back = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
    
    buffered_geoms = []
    for pt in target_points:
        radius_m = viirs_pixel_m / 2.0 if "VIIRS" in pt.get("satellite", "") else modis_pixel_m / 2.0
        
        geom = Point(pt["longitude"], pt["latitude"])
        geom_m = transform(project, geom)
        buffered_m = geom_m.buffer(radius_m)
        buffered = transform(project_back, buffered_m)
        
        buffered_geoms.append(buffered)
        
    perimeter = unary_union(buffered_geoms)
    return perimeter


def score_intensity(firms_points, thresholds):
    """
    Sums FRP and maps to Low/Medium/High.
    """
    total_frp = sum(p.get("frp", 0) for p in firms_points)
    
    if total_frp >= thresholds.get("high", 200):
        return "High", total_frp
    elif total_frp >= thresholds.get("medium", 50):
        return "Medium", total_frp
    else:
        return "Low", total_frp


def calculate_overlap_confidence(firms_poly, core_poly, overlap_thresholds):
    """
    Computes overlap (as % area of FIRMS perimeter) and applies adjustment rule.
    
    OVERLAP CONFIDENCE RULE:
    - If the predicted core polygon covers >= 60% of the actual FIRMS perimeter -> "High" confidence.
    - If overlap is 20-60% -> "partial_deviation" (fire spread somewhat unexpectedly).
    - If overlap < 20% -> "simulation_deviation" (simulation likely mispredicted direction/speed).
    """
    if not firms_poly or not core_poly or firms_poly.area == 0:
        return 0, False, False
        
    intersection = firms_poly.intersection(core_poly)
    overlap_pct = intersection.area / firms_poly.area
    
    high_thresh = overlap_thresholds.get("high_confidence_pct", 0.6)
    partial_thresh = overlap_thresholds.get("partial_deviation_pct", 0.2)
    
    partial_deviation = False
    simulation_deviation = False
    
    if overlap_pct >= high_thresh:
        pass # Good alignment
    elif overlap_pct >= partial_thresh:
        partial_deviation = True
    else:
        simulation_deviation = True
        
    return overlap_pct, partial_deviation, simulation_deviation


def run_stage5_refinement(stage4_json_path, lat, lng, demo_mode=True):
    """
    Main entry point for Stage 5.
    """
    print("--- STAGE 5: High-Resolution Refinement (Accuracy Anchor) ---")
    
    # 1. Load config and input
    config = load_config("config.json")
    stage5_cfg = config.get("stage5_refinement", {})
    
    with open(stage4_json_path, 'r') as f:
        stage4_data = json.load(f)
        
    fire_id = stage4_data.get("fire_id")
    core_geojson = stage4_data.get("core_polygon")
    core_poly = shape(core_geojson) if core_geojson else None
    
    # 2. Fetch FIRMS
    print(f"Fetching FIRMS data for {fire_id} (Demo Mode: {demo_mode})...")
    firms_points = fetch_firms_data(
        lat, lng, fire_id, demo_mode, 
        buffer_km=stage5_cfg.get("firms_buffer_km", 5)
    )
    
    # 3. Perimeter & Intensity
    if not firms_points:
        print("No FIRMS points found in window. Flagging 'no_satellite_confirmation'.")
        refinement_data = {
            "firms_perimeter": None,
            "intensity": "Unknown",
            "total_frp": 0,
            "overlap_pct": 0,
            "flags": {"no_satellite_confirmation": True}
        }
        corrected_sim = None
    else:
        print(f"Found {len(firms_points)} active fire points. Building perimeter...")
        firms_poly = create_firms_perimeter(
            firms_points,
            stage5_cfg.get("viirs_pixel_m", 187.5),
            stage5_cfg.get("modis_pixel_m", 500.0)
        )
        
        intensity_label, total_frp = score_intensity(firms_points, stage5_cfg.get("intensity_thresholds", {}))
        print(f"Intensity scored as: {intensity_label} (FRP: {total_frp:.1f} MW)")
        
        # 4. Compare Overlap
        overlap_pct, partial_dev, sim_dev = calculate_overlap_confidence(
            firms_poly, core_poly, stage5_cfg.get("overlap_thresholds", {})
        )
        print(f"Overlap with Stage 4 Prediction: {overlap_pct*100:.1f}%")
        if sim_dev: print("-> FLAG: simulation_deviation (Simulation likely mispredicted direction/speed)")
        elif partial_dev: print("-> FLAG: partial_deviation")
        
        refinement_data = {
            "firms_perimeter": mapping(firms_poly),
            "intensity": intensity_label,
            "total_frp": total_frp,
            "overlap_pct": overlap_pct,
            "flags": {
                "partial_deviation": partial_dev,
                "simulation_deviation": sim_dev,
                "no_satellite_confirmation": False
            }
        }
        
        # 5. Course-Correction Re-Simulation
        print("Running Course-Correction Re-Simulation re-seeded from FIRMS perimeter...")
        corrected_sim = run_ensemble_simulation(
            lat, lng, 
            config_path="config.json", 
            seed=101, 
            num_steps_override=stage5_cfg.get("resimulate_steps", 6),
            firms_polygon=firms_poly
        )
        print("Course-Correction complete.")
        
    # 6. Archive
    archive_record = {
        "fire_id": fire_id,
        "original_lat": lat,
        "original_lng": lng,
        "stage4_original": stage4_data,
        "stage5_refinement": refinement_data,
        "stage5_corrected_simulation": corrected_sim,
        "final_status": "pending_review",
        "archived_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    os.makedirs("fire_archive", exist_ok=True)
    archive_path = os.path.join("fire_archive", f"{fire_id}.json")
    with open(archive_path, 'w') as f:
        json.dump(archive_record, f, indent=4)
    print(f"Consolidated record archived to {archive_path}")
    
    return archive_path, archive_record
