import geopandas as gpd
from shapely.geometry import shape
import os

def load_geojson_layer(filepath):
    """
    Safely load a GeoJSON layer.
    Returns an empty GeoDataFrame if file is missing.
    """
    if os.path.exists(filepath):
        try:
            return gpd.read_file(filepath)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    # Return empty GDF
    return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def extract_point_coords(geom):
    if geom.geom_type == 'Point':
        return geom.y, geom.x
    elif geom.geom_type == 'Polygon' or geom.geom_type == 'MultiPolygon':
        # Use centroid for polygons (like protected areas)
        c = geom.centroid
        return c.y, c.x
    return None, None


def prioritize_intersections(core_geojson, uncert_geojson, settlements_gdf, infra_gdf, protected_gdf):
    """
    Spatially intersects the core and uncertainty polygons with habitats and settlements.
    Assigns priority based on exact rules:
    - Settlement or hospital within CORE = "Critical"
    - Settlement/hospital within UNCERTAINTY ONLY, or protected area overlap with CORE = "High"
    - Protected area overlap with UNCERTAINTY ONLY, or infrastructure (non-hospital) anywhere = "Standard"
    """
    priority_list = []
    
    # Convert GeoJSON to Shapely geometries
    core_poly = shape(core_geojson) if core_geojson else None
    uncert_poly = shape(uncert_geojson) if uncert_geojson else None
    
    # Helper to check intersection and return zone ("core", "uncertainty", or None)
    def get_zone(geom):
        if core_poly and geom.intersects(core_poly):
            return "core"
        if uncert_poly and geom.intersects(uncert_poly):
            return "uncertainty"
        return None

    # 1. Process Settlements (Points)
    for idx, row in settlements_gdf.iterrows():
        zone = get_zone(row.geometry)
        if zone:
            priority = "Critical" if zone == "core" else "High"
            lat, lng = extract_point_coords(row.geometry)
            name = row.get('name', f'Settlement_{idx}')
            priority_list.append({
                "name": name,
                "type": "Settlement",
                "priority": priority,
                "lat": lat,
                "lng": lng
            })
            
    # 2. Process Infrastructure (Points)
    for idx, row in infra_gdf.iterrows():
        zone = get_zone(row.geometry)
        if zone:
            # Check if it's a hospital
            infra_type = str(row.get('type', '')).lower()
            amenity = str(row.get('amenity', '')).lower()
            is_hospital = ('hospital' in infra_type or 'hospital' in amenity)
            
            if is_hospital:
                priority = "Critical" if zone == "core" else "High"
                type_label = "Hospital"
            else:
                priority = "Standard" # Infrastructure (non-hospital) anywhere in either polygon
                type_label = f"Infrastructure ({infra_type or amenity or 'Unknown'})"
                
            lat, lng = extract_point_coords(row.geometry)
            name = row.get('name', f'Infra_{idx}')
            priority_list.append({
                "name": name,
                "type": type_label,
                "priority": priority,
                "lat": lat,
                "lng": lng
            })
            
    # 3. Process Protected Areas (Polygons)
    for idx, row in protected_gdf.iterrows():
        zone = get_zone(row.geometry)
        if zone:
            priority = "High" if zone == "core" else "Standard"
            lat, lng = extract_point_coords(row.geometry) # using centroid
            name = row.get('name', f'Protected_Area_{idx}')
            priority_list.append({
                "name": name,
                "type": "Protected Area",
                "priority": priority,
                "lat": lat,
                "lng": lng
            })
            
    # Sort list: Critical > High > Standard
    sort_order = {"Critical": 0, "High": 1, "Standard": 2}
    priority_list.sort(key=lambda x: sort_order.get(x["priority"], 99))
    
    return priority_list


def run_overlay_and_prioritization(core_geojson, uncert_geojson, 
                                   settlements_path="settlements.geojson", 
                                   infra_path="infrastructure.geojson", 
                                   protected_path="protected_areas.geojson"):
    """
    Main entry point for Part B.
    """
    settlements_gdf = load_geojson_layer(settlements_path)
    infra_gdf = load_geojson_layer(infra_path)
    protected_gdf = load_geojson_layer(protected_path)
    
    priority_list = prioritize_intersections(
        core_geojson, uncert_geojson, 
        settlements_gdf, infra_gdf, protected_gdf
    )
    
    return priority_list
