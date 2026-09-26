import ee
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, box

# Initialize Earth Engine if not already initialized
try:
    ee.Initialize(project='vanraksha-ai-27380')
except Exception as e:
    # If not authenticated, we might need to authenticate first, but assume auth is done
    ee.Authenticate()
    ee.Initialize(project='vanraksha-ai-27380')


def get_vegetation_mask(roi_ee: ee.Geometry):
    """
    Get ESA WorldCover mask for burnable vegetation in the given ROI.
    Keep only classes 10: Trees, 20: Shrubland, 30: Grassland.
    """
    # Load ESA WorldCover 2021 (10m resolution)
    dataset = ee.ImageCollection("ESA/WorldCover/v200").first()
    
    # Select the map band
    landcover = dataset.select('Map')
    
    # Create mask for burnable vegetation
    # Classes: 10 (Trees), 20 (Shrubland), 30 (Grassland)
    trees = landcover.eq(10)
    shrubland = landcover.eq(20)
    grassland = landcover.eq(30)
    
    # Combine masks
    burnable_mask = trees.Or(shrubland).Or(grassland)
    
    # Clip to ROI
    return burnable_mask.clip(roi_ee)


def get_roads_mask_gdf(roi_polygon: Polygon, buffer_m: float = 40.0):
    """
    Fetch road network data using OSMnx for the bounding box of the ROI.
    Buffer roads by a configurable distance and return as a GeoDataFrame.
    """
    # Ensure ROI is in WGS84 (EPSG:4326)
    # Get bounding box of the ROI
    bounds = roi_polygon.bounds  # (minx, miny, maxx, maxy)
    
    # Fetch road network
    # Use standard OSMnx API
    try:
        # Create graph from bounding box (north, south, east, west)
        north, south, east, west = bounds[3], bounds[1], bounds[2], bounds[0]
        G = ox.graph_from_bbox(north, south, east, west, network_type='drive')
        
        # Convert to GeoDataFrames
        nodes, edges = ox.graph_to_gdfs(G)
        
        if edges.empty:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            
        # Project edges to a suitable CRS for buffering in meters (e.g., local UTM or World Mercator)
        # Using ox.project_gdf to project to UTM automatically
        edges_proj = ox.project_gdf(edges)
        
        # Buffer roads
        edges_buffered_proj = edges_proj.copy()
        edges_buffered_proj['geometry'] = edges_proj.geometry.buffer(buffer_m)
        
        # Project back to WGS84
        edges_buffered = edges_buffered_proj.to_crs("EPSG:4326")
        
        return edges_buffered
        
    except ox._errors.EmptyOverpassResponse:
        # No roads found
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    except Exception as e:
        print(f"Error fetching roads: {e}")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def get_ee_roads_mask(roads_gdf, roi_ee: ee.Geometry):
    """
    Convert roads GeoDataFrame to Earth Engine feature collection to mask out of GEE image.
    """
    if roads_gdf.empty:
        # Return an image of 0s (no roads to mask)
        return ee.Image(0).clip(roi_ee)
        
    # Combine all buffered roads into a single geometry
    combined_roads = roads_gdf.unary_union
    
    # Handle multi-part geometries
    if combined_roads.geom_type == 'MultiPolygon':
        features = []
        for poly in combined_roads.geoms:
            coords = list(poly.exterior.coords)
            features.append(ee.Feature(ee.Geometry.Polygon(coords)))
        fc = ee.FeatureCollection(features)
    elif combined_roads.geom_type == 'Polygon':
        coords = list(combined_roads.exterior.coords)
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Polygon(coords))])
    else:
        return ee.Image(0).clip(roi_ee)
        
    # Rasterize road mask (1 for roads, 0 for non-roads)
    # Using reduceToImage on the feature collection
    empty = ee.Image(0).byte()
    roads_raster = empty.paint(fc, 1).clip(roi_ee)
    
    return roads_raster


def get_eligible_forest_mask(roi_polygon: Polygon, buffer_m: float = 40.0):
    """
    Returns an Earth Engine Image representing eligible forest terrain (1 = eligible, 0 = non-eligible).
    Combines ESA WorldCover vegetation mask and OSMnx roads mask.
    """
    # Create GEE Geometry from Shapely Polygon
    coords = list(roi_polygon.exterior.coords)
    roi_ee = ee.Geometry.Polygon(coords)
    
    # 1. Get Vegetation Mask (1 for burnable, 0 for non-burnable)
    veg_mask = get_vegetation_mask(roi_ee)
    
    # 2. Get Roads Mask
    roads_gdf = get_roads_mask_gdf(roi_polygon, buffer_m)
    roads_mask_ee = get_ee_roads_mask(roads_gdf, roi_ee)
    
    # 3. Final Eligible Mask: Vegetation is 1 AND Roads is NOT 1
    # Eligible if veg_mask == 1 and roads_mask_ee == 0
    eligible_mask = veg_mask.And(roads_mask_ee.Not())
    
    return eligible_mask, roads_gdf
