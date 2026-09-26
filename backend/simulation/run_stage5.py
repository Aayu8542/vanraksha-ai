import argparse
import folium
import os
import json
from stage5_refinement import run_stage5_refinement

def visualize_stage5_comparison(archive_data, lat, lng, output_path):
    """
    Overlays:
    - Original Stage 4 Core/Uncertainty (Red/Orange outlines)
    - FIRMS-corrected perimeter (Solid Purple)
    - Corrected Core/Uncertainty (Blue outlines)
    """
    m = folium.Map(location=[lat, lng], zoom_start=13, tiles='CartoDB dark_matter')
    
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    # 1. Original Stage 4
    stg4 = archive_data.get("stage4_original", {})
    if stg4.get("uncertainty_polygon"):
        folium.GeoJson(
            stg4["uncertainty_polygon"],
            name="Original Stage 4 Uncertainty",
            style_function=lambda x: {'fillOpacity': 0, 'color': '#d97706', 'weight': 1, 'dashArray': '4'}
        ).add_to(m)
        
    if stg4.get("core_polygon"):
        folium.GeoJson(
            stg4["core_polygon"],
            name="Original Stage 4 Core",
            style_function=lambda x: {'fillOpacity': 0.1, 'fillColor': '#ef4444', 'color': '#ef4444', 'weight': 2}
        ).add_to(m)

    # 2. FIRMS Corrected Perimeter (Reality)
    refinement = archive_data.get("stage5_refinement", {})
    if refinement.get("firms_perimeter"):
        folium.GeoJson(
            refinement["firms_perimeter"],
            name="FIRMS Corrected Perimeter (Reality)",
            style_function=lambda x: {'fillOpacity': 0.6, 'fillColor': '#9333ea', 'color': '#a855f7', 'weight': 3}
        ).add_to(m)

    # 3. Corrected Simulation (Stage 5)
    stg5_corr = archive_data.get("stage5_corrected_simulation")
    if stg5_corr:
        if stg5_corr.get("uncertainty_polygon"):
            folium.GeoJson(
                stg5_corr["uncertainty_polygon"],
                name="Corrected Uncertainty",
                style_function=lambda x: {'fillOpacity': 0, 'color': '#3b82f6', 'weight': 1, 'dashArray': '4'}
            ).add_to(m)
            
        if stg5_corr.get("core_polygon"):
            folium.GeoJson(
                stg5_corr["core_polygon"],
                name="Corrected Core",
                style_function=lambda x: {'fillOpacity': 0.2, 'fillColor': '#3b82f6', 'color': '#2563eb', 'weight': 2}
            ).add_to(m)

    # Original Point
    folium.Marker(
        location=[lat, lng],
        icon=folium.Icon(color='black', icon='fire', prefix='fa'),
        popup="Original Ignition Point"
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(output_path)
    print(f"Comparison map saved to {output_path}")
    return m

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Stage 5: High-Resolution Refinement")
    parser.add_argument('--stage4-json', type=str, default='stage4_output.json', help='Path to Stage 4 JSON output')
    parser.add_argument('--lat', type=float, default=30.1472, help='Original Fire Latitude')
    parser.add_argument('--lng', type=float, default=78.5925, help='Original Fire Longitude')
    parser.add_argument('--live', action='store_true', help='Use live FIRMS API instead of demo cache')
    parser.add_argument('--no-map', action='store_true', help='Disable map generation')
    
    args = parser.parse_args()
    
    # Check if we need to simulate stage 4 first for the demo
    if not os.path.exists(args.stage4_json):
        print(f"File {args.stage4_json} not found. Running a quick Stage 4 to generate it...")
        from run_stage4 import run_stage4_pipeline
        run_stage4_pipeline("demo_fire_01", args.lat, args.lng, args.stage4_json, no_map=True)
    
    demo_mode = not args.live
    
    # Use "sample_fire_01" for cache lookup if we are in demo mode testing
    # We patch the fire_id in stage4_json to match the user's sample data file just for demo purposes.
    if demo_mode:
        with open(args.stage4_json, 'r') as f:
            data = json.load(f)
        data['fire_id'] = "sample_fire_01"
        with open(args.stage4_json, 'w') as f:
            json.dump(data, f)
            
    archive_path, archive_record = run_stage5_refinement(
        stage4_json_path=args.stage4_json,
        lat=args.lat,
        lng=args.lng,
        demo_mode=demo_mode
    )
    
    if not args.no_map:
        map_path = archive_path.replace(".json", "_comparison_map.html")
        visualize_stage5_comparison(archive_record, args.lat, args.lng, map_path)
