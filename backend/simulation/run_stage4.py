import argparse
import json
import os
import datetime
from part_a_simulation import run_ensemble_simulation
from part_b_overlay import run_overlay_and_prioritization
from visualize_stage4 import visualize_simulation

def generate_dummy_geojson_if_missing():
    """
    Helper for demo purposes: generates dummy files if the user hasn't provided them yet.
    """
    dummy_settlements = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Demo Village A"},
                "geometry": {"type": "Point", "coordinates": [78.5700, 30.1250]}
            }
        ]
    }
    dummy_infra = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "District Hospital", "type": "hospital"},
                "geometry": {"type": "Point", "coordinates": [78.5650, 30.1200]}
            }
        ]
    }
    dummy_protected = {
        "type": "FeatureCollection",
        "features": []
    }
    
    if not os.path.exists("settlements.geojson"):
        with open("settlements.geojson", "w") as f: json.dump(dummy_settlements, f)
    if not os.path.exists("infrastructure.geojson"):
        with open("infrastructure.geojson", "w") as f: json.dump(dummy_infra, f)
    if not os.path.exists("protected_areas.geojson"):
        with open("protected_areas.geojson", "w") as f: json.dump(dummy_protected, f)


def run_stage4_pipeline(fire_id, lat, lng, output_json, no_map=False):
    """
    Executes Stage 4: Confirmed Fire -> Simulation & Prioritization
    """
    print(f"Starting Stage 4 Simulation for Fire ID: {fire_id} at [{lat}, {lng}]")
    
    # Ensure config exists
    if not os.path.exists("config.json"):
        print("Error: config.json not found in the current directory.")
        return
        
    generate_dummy_geojson_if_missing()
    
    print("\n--- PART A: Short-Horizon Spread Simulation ---")
    print("Fetching weather and environmental layers, running ensemble cellular automaton...")
    
    part_a_result = run_ensemble_simulation(
        lat=lat, 
        lng=lng, 
        config_path="config.json", 
        seed=42 # reproducible for demo
    )
    
    core_geojson = part_a_result["core_polygon"]
    uncert_geojson = part_a_result["uncertainty_polygon"]
    wind_used = part_a_result["wind_used"]
    
    print(f"Simulation complete. Wind used: {wind_used['speed_kmh']:.1f} km/h from {wind_used['direction_deg']:.1f} deg.")
    
    print("\n--- PART B: Habitat & Settlement Overlay ---")
    print("Intersecting simulation output with settlements, infrastructure, and protected areas...")
    
    priority_list = run_overlay_and_prioritization(
        core_geojson=core_geojson,
        uncert_geojson=uncert_geojson,
        settlements_path="settlements.geojson",
        infra_path="infrastructure.geojson",
        protected_path="protected_areas.geojson"
    )
    
    print(f"Found {len(priority_list)} at-risk assets.")
    for item in priority_list:
        print(f"  - [{item['priority']}] {item['name']} ({item['type']})")
        
    # Combine outputs
    final_output = {
        "fire_id": fire_id,
        "core_polygon": core_geojson,
        "uncertainty_polygon": uncert_geojson,
        "wind_used": wind_used,
        "priority_list": priority_list,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    print(f"\nSaving combined output to {output_json}...")
    with open(output_json, "w") as f:
        json.dump(final_output, f, indent=4)
        
    if not no_map:
        map_path = output_json.replace(".json", "_map.html")
        print(f"Generating visualization map at {map_path}...")
        visualize_simulation(
            lat=lat, 
            lng=lng, 
            core_geojson=core_geojson, 
            uncert_geojson=uncert_geojson, 
            priority_list=priority_list,
            output_path=map_path
        )
        
    print("Stage 4 pipeline completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Stage 4: Simulation & Prioritization")
    parser.add_argument('--fire-id', type=str, default='FIRE_999', help='ID of the confirmed fire')
    parser.add_argument('--lat', type=float, default=30.1234, help='Confirmed Fire Latitude')
    parser.add_argument('--lng', type=float, default=78.5678, help='Confirmed Fire Longitude')
    parser.add_argument('--output', type=str, default='stage4_output.json', help='Path to output JSON')
    parser.add_argument('--no-map', action='store_true', help='Disable map generation')
    
    args = parser.parse_args()
    
    run_stage4_pipeline(
        fire_id=args.fire_id,
        lat=args.lat,
        lng=args.lng,
        output_json=args.output,
        no_map=args.no_map
    )
