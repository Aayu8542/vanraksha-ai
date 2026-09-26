import numpy as np
from sklearn.cluster import DBSCAN
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
import uuid

def determine_confidence(score, thresholds):
    """
    Determine confidence level based on score and thresholds.
    """
    if score >= thresholds.get("high_confidence", 0.85):
        return "High"
    elif score >= thresholds.get("medium_confidence", 0.65):
        return "Medium"
    elif score >= thresholds.get("low_confidence", 0.4):
        return "Low"
    else:
        return "None"


def select_target_nodes(score_data, transform, thresholds, max_nodes=3, radius_m=300):
    """
    Finds top high-scoring clusters and returns target nodes.
    
    score_data: 2D numpy array of risk scores.
    transform: rasterio affine transform to convert array indices to coordinates.
    thresholds: Dictionary of confidence thresholds.
    """
    if score_data is None or transform is None:
        return []
        
    # Flatten and find coordinates of all pixels above a minimal threshold
    # Let's consider only pixels with at least "Low" confidence or > 0.1 to cluster
    min_thresh = min(thresholds.get("low_confidence", 0.4) - 0.1, 0.3)
    
    # Get indices of cells above threshold
    y_indices, x_indices = np.where(score_data > min_thresh)
    
    if len(y_indices) == 0:
        return []
        
    # Get coordinates and scores
    points = []
    scores = []
    
    for y, x in zip(y_indices, x_indices):
        # transform * (x, y) gives coordinates of top-left corner. Add 0.5 for center.
        lon, lat = transform * (x + 0.5, y + 0.5)
        points.append([lat, lon]) # Note: lat, lon for DBSCAN (often distance in rads)
        scores.append(score_data[y, x])
        
    points = np.array(points)
    scores = np.array(scores)
    
    # Clustering using DBSCAN
    # Convert coordinates to radians for haversine metric
    coords_rad = np.radians(points)
    
    # eps in radians (e.g. 500m / Earth radius in meters)
    earth_radius_m = 6371000
    eps_rad = 500 / earth_radius_m
    
    # Perform DBSCAN
    db = DBSCAN(eps=eps_rad, min_samples=2, metric='haversine').fit(coords_rad)
    labels = db.labels_
    
    # Process clusters
    unique_labels = set(labels)
    clusters = []
    
    for label in unique_labels:
        if label == -1:
            continue # Noise
            
        # Get points in this cluster
        cluster_mask = (labels == label)
        cluster_points = points[cluster_mask]
        cluster_scores = scores[cluster_mask]
        
        # Calculate cluster center (weighted by score)
        center_lat = np.average(cluster_points[:, 0], weights=cluster_scores)
        center_lon = np.average(cluster_points[:, 1], weights=cluster_scores)
        
        # Max score in cluster
        max_score = np.max(cluster_scores)
        
        clusters.append({
            "lat": center_lat,
            "lon": center_lon,
            "score": max_score,
            "size": len(cluster_points)
        })
        
    # Sort clusters by score descending
    clusters.sort(key=lambda x: x["score"], reverse=True)
    
    # Select top N clusters
    top_clusters = clusters[:max_nodes]
    
    # If no clusters found (e.g., all were noise or no points above threshold), 
    # fallback to just top points
    if not top_clusters and len(points) > 0:
        # Sort points by score
        sorted_indices = np.argsort(scores)[::-1]
        for i in range(min(max_nodes, len(sorted_indices))):
            idx = sorted_indices[i]
            top_clusters.append({
                "lat": points[idx][0],
                "lon": points[idx][1],
                "score": scores[idx],
                "size": 1
            })
    
    # Format output
    target_nodes = []
    for i, cluster in enumerate(top_clusters):
        confidence = determine_confidence(cluster["score"], thresholds)
        
        target_nodes.append({
            "node_id": str(uuid.uuid4())[:8],
            "lat": float(cluster["lat"]),
            "lon": float(cluster["lon"]),
            "radius_m": radius_m,
            "score": float(cluster["score"]),
            "confidence": confidence
        })
        
    return target_nodes
