import json
import argparse
import geopandas as gpd
from shapely.geometry import Polygon
import os
import ee

# Import phase 2 modules
from masking import get_eligible_forest_mask
from fine_scoring import compute_risk_score, export_score_to_numpy, load_config
from node_selection import select_target_nodes
from visualize_nodes import create_map

def run_phase2_pipeline(input_geojson, output_json, config_path="config.json", make_map=True):
    """
    Run the Phase 2 pipeline.
    """
    print(f"Loading input cell from {input_geojson}...")
    
    # 1. Load Input (4km cell)
    try:
        gdf = gpd.read_file(input_geojson)
        if gdf.empty:
            print("Error: Input GeoJSON is empty.")
            return
            
        # Assuming the first feature is the 4km cell
        roi_polygon = gdf.geometry.iloc[0]
        
    except Exception as e:
        # If file doesn't exist for testing, create a dummy 4km cell
        print(f"Could not read {input_geojson}: {e}")
        print("Creating a dummy 4km cell for demonstration in California...")
        # A bounding box roughly 4x4 km
        lon, lat = -121.0, 39.0
        deg_4km = 0.036 # approx 4km
        roi_polygon = Polygon([
            (lon, lat),
            (lon + deg_4km, lat),
            (lon + deg_4km, lat + deg_4km),
            (lon, lat + deg_4km),
            (lon, lat)
        ])
    
    # Get GEE Geometry
    coords = list(roi_polygon.exterior.coords)
    roi_ee = ee.Geometry.Polygon(coords)
    
    print("1. Masking out unburnable areas and roads...")
    eligible_mask, roads_gdf = get_eligible_forest_mask(roi_polygon, buffer_m=40.0)
    
    print("2. Computing high-resolution (200m) risk scores...")
    score_image = compute_risk_score(roi_ee, eligible_mask, config_path)
    
    print("Exporting score image to local array...")
    score_data, transform = export_score_to_numpy(roi_ee, score_image, scale=200)
    
    if score_data is None:
        print("Failed to compute or download score data. Exiting.")
        return
        
    print("3. Selecting target nodes...")
    config = load_config(config_path)
    thresholds = config.get("thresholds", {
        "low_confidence": 0.4,
        "medium_confidence": 0.65,
        "high_confidence": 0.85
    })
    
    target_nodes = select_target_nodes(
        score_data=score_data, 
        transform=transform, 
        thresholds=thresholds,
        max_nodes=3,
        radius_m=300
    )
    
    print(f"Found {len(target_nodes)} target nodes.")
    for node in target_nodes:
        print(f"  - Node {node['node_id']}: Score={node['score']:.2f}, Confidence={node['confidence']}")
        
    print(f"4. Saving output to {output_json}...")
    with open(output_json, 'w') as f:
        json.dump(target_nodes, f, indent=4)
        
    if make_map:
        map_path = output_json.replace('.json', '_map.html')
        print(f"5. Generating visualization: {map_path}...")
        create_map(roi_polygon, roads_gdf, score_data, transform, target_nodes, output_path=map_path)
        
    print("Phase 2 pipeline completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Phase 2: Spatial Filtering & Probability Scoring")
    parser.add_argument('--input', type=str, default='phase1_flagged_cell.geojson', help='Path to input flagged cell GeoJSON')
    parser.add_argument('--output', type=str, default='phase2_output_nodes.json', help='Path to output nodes JSON')
    parser.add_argument('--config', type=str, default='config.json', help='Path to Phase 1 config file')
    parser.add_argument('--no-map', action='store_true', help='Disable map generation')
    
    args = parser.parse_args()
    
    # Initialize GEE once at startup
    try:
        ee.Initialize(project='vanraksha-ai-27380')
    except Exception:
        print("Authenticating Earth Engine...")
        ee.Authenticate()
        ee.Initialize(project='vanraksha-ai-27380')
        
    run_phase2_pipeline(
        input_geojson=args.input,
        output_json=args.output,
        config_path=args.config,
        make_map=not args.no_map
    )
