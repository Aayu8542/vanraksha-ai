import folium
from folium import plugins
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import array_bounds

def create_map(roi_polygon, roads_gdf, score_data, transform, target_nodes, output_path="phase2_map.html"):
    """
    Creates an interactive Folium map showing the Phase 2 outputs.
    """
    # 1. Initialize map centered on ROI
    bounds = roi_polygon.bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles='OpenStreetMap')
    
    # Add Satellite basemap
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    # 2. Add ROI Boundary (4km cell)
    roi_coords = list(roi_polygon.exterior.coords)
    roi_folium_coords = [(lat, lon) for lon, lat in roi_coords]
    folium.Polygon(
        locations=roi_folium_coords,
        color='blue',
        fill=False,
        weight=2,
        name='4km Cell Boundary'
    ).add_to(m)

    # 3. Add Roads (Masked areas)
    if roads_gdf is not None and not roads_gdf.empty:
        folium.GeoJson(
            roads_gdf,
            name='Masked Roads',
            style_function=lambda x: {'color': 'black', 'weight': 1, 'fillColor': 'black', 'fillOpacity': 0.5}
        ).add_to(m)

    # 4. Add Heatmap for Scores
    if score_data is not None and transform is not None:
        # Generate heat data
        heat_data = []
        y_indices, x_indices = np.where(score_data > 0) # Only positive scores
        
        for y, x in zip(y_indices, x_indices):
            lon, lat = transform * (x + 0.5, y + 0.5)
            score = score_data[y, x]
            # Folium HeatMap expects [lat, lon, weight]
            heat_data.append([lat, lon, float(score)])
            
        plugins.HeatMap(
            heat_data,
            name='Risk Score Heatmap',
            radius=15,
            blur=10,
            max_zoom=13
        ).add_to(m)
        
        # Optionally add image overlay of the scores
        try:
            from folium import raster_layers
            
            # Calculate bounds of the array for ImageOverlay
            minx, miny, maxx, maxy = array_bounds(score_data.shape[0], score_data.shape[1], transform)
            
            # Create RGBA image from scores (using a colormap)
            import matplotlib.pyplot as plt
            cmap = plt.get_cmap('YlOrRd')
            
            # Normalize scores for colormap
            score_norm = score_data.copy()
            max_val = np.max(score_norm)
            if max_val > 0:
                score_norm = score_norm / max_val
                
            # Apply colormap (returns RGBA)
            rgba_img = cmap(score_norm)
            
            # Make transparent where score is 0
            rgba_img[score_data == 0, 3] = 0.0
            
            raster_layers.ImageOverlay(
                image=rgba_img,
                bounds=[[miny, minx], [maxy, maxx]],
                opacity=0.6,
                name='Score Image Overlay',
                interactive=True,
                cross_origin=False,
                zindex=1
            ).add_to(m)
        except Exception as e:
            print(f"Could not add ImageOverlay: {e}")

    # 5. Add Target Nodes
    target_nodes_group = folium.FeatureGroup(name='Target Nodes (300m)')
    for node in target_nodes:
        lat, lon = node['lat'], node['lon']
        radius = node['radius_m']
        score = node['score']
        confidence = node['confidence']
        
        # Color based on confidence
        color = 'red' if confidence == 'High' else 'orange' if confidence == 'Medium' else 'yellow'
        
        folium.Circle(
            location=[lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.3,
            tooltip=f"Score: {score:.2f} ({confidence})"
        ).add_to(target_nodes_group)
        
        # Add marker at center
        folium.Marker(
            location=[lat, lon],
            icon=folium.Icon(color=color, icon='fire'),
            popup=f"<b>Node ID:</b> {node['node_id']}<br><b>Score:</b> {score:.2f}<br><b>Confidence:</b> {confidence}"
        ).add_to(target_nodes_group)
        
    target_nodes_group.add_to(m)

    # Add Layer Control
    folium.LayerControl().add_to(m)

    # Save to file
    m.save(output_path)
    print(f"Map saved to {output_path}")
    return m
