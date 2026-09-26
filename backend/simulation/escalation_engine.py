import json
import os
from shapely.geometry import shape
import pyproj
from shapely.ops import transform

def calculate_area_hectares(polygon_geojson):
    """
    Calculates area of a GeoJSON polygon in hectares.
    Assumes input is EPSG:4326 (WGS84).
    """
    if not polygon_geojson:
        return 0.0
        
    poly = shape(polygon_geojson)
    if poly.is_empty:
        return 0.0
        
    # Project to a suitable equal-area or metric projection for area calculation
    # EPSG:3857 (Web Mercator) distorts area heavily, but since we just want a rough 
    # estimate in hectares, an equal-area projection like Mollweide or local UTM is better.
    # Using an azimuthal equal area projection centered on the polygon.
    centroid = poly.centroid
    proj_string = f"+proj=laea +lat_0={centroid.y} +lon_0={centroid.x} +units=m"
    
    project = pyproj.Transformer.from_crs("EPSG:4326", proj_string, always_xy=True).transform
    poly_m = transform(project, poly)
    
    area_sq_m = poly_m.area
    area_ha = area_sq_m / 10000.0
    return area_ha


def evaluate_escalation(config, stage4_data, stage5_data=None):
    """
    Escalation Rule Engine
    
    POLICY:
    - Level = "Range" by default 
    - Level = "Division" if core polygon area exceeds a configurable hectare threshold (default 5 ha) 
    - Level = "SDMA_NDMA" if ANY of:
        - any priority_list item has priority "Critical"
        - OR Stage 5 intensity = "High"
        - OR Stage 5 flagged "simulation_deviation" = true
        
    Returns the determined escalation level.
    """
    cfg = config.get("stage6_escalation", {})
    threshold_ha = cfg.get("core_area_threshold_ha", 5.0)
    
    level = "Range"
    
    # Check Division condition (Core Area)
    # Use stage5 corrected core polygon if available, else stage 4
    core_geojson = None
    if stage5_data and stage5_data.get("stage5_corrected_simulation"):
        core_geojson = stage5_data["stage5_corrected_simulation"].get("core_polygon")
    elif stage4_data:
        core_geojson = stage4_data.get("core_polygon")
        
    area_ha = calculate_area_hectares(core_geojson)
    
    if area_ha > threshold_ha:
        level = "Division"
        
    # Check SDMA_NDMA conditions
    # 1. Critical Priority Item
    if stage4_data and "priority_list" in stage4_data:
        has_critical = any(item.get("priority") == "Critical" for item in stage4_data["priority_list"])
        if has_critical:
            level = "SDMA_NDMA"
            
    # 2 & 3. Stage 5 Refinement Metrics
    if stage5_data and "stage5_refinement" in stage5_data:
        refinement = stage5_data["stage5_refinement"]
        
        if refinement.get("intensity") == "High":
            level = "SDMA_NDMA"
            
        flags = refinement.get("flags", {})
        if flags.get("simulation_deviation") is True:
            level = "SDMA_NDMA"
            
    return level
