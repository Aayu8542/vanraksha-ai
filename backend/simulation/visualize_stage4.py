import folium
import os

def visualize_simulation(lat, lng, core_geojson, uncert_geojson, priority_list, output_path="stage4_simulation_map.html"):
    """
    Creates an interactive map plotting:
    - Core Polygon (Red)
    - Uncertainty Band (Orange)
    - Priority List points color-coded (Critical=Red, High=Orange, Standard=Yellow)
    """
    # Initialize map centered on fire location
    m = folium.Map(location=[lat, lng], zoom_start=13, tiles='CartoDB dark_matter')
    
    # Add satellite as option
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    # Plot Uncertainty Band (Orange)
    if uncert_geojson:
        folium.GeoJson(
            uncert_geojson,
            name='Uncertainty Band',
            style_function=lambda x: {
                'fillColor': '#f59e0b', # amber
                'color': '#d97706',
                'weight': 1,
                'fillOpacity': 0.4
            }
        ).add_to(m)
        
    # Plot Core Polygon (Red)
    if core_geojson:
        folium.GeoJson(
            core_geojson,
            name='Core Burn Area (Predicted)',
            style_function=lambda x: {
                'fillColor': '#ef4444', # red
                'color': '#b91c1c',
                'weight': 2,
                'fillOpacity': 0.6
            }
        ).add_to(m)

    # Plot Ignition Point
    folium.Marker(
        location=[lat, lng],
        icon=folium.Icon(color='black', icon='fire', prefix='fa'),
        popup="Confirmed Ignition Point"
    ).add_to(m)

    # Plot Priority Items
    priority_group = folium.FeatureGroup(name="At-Risk Assets")
    
    color_map = {
        "Critical": "red",
        "High": "orange",
        "Standard": "blue"
    }

    for item in priority_list:
        p_color = color_map.get(item["priority"], "gray")
        
        # Circle marker for the asset
        folium.CircleMarker(
            location=[item["lat"], item["lng"]],
            radius=6,
            color=p_color,
            fill=True,
            fill_color=p_color,
            fill_opacity=0.8,
            popup=f"<b>{item['name']}</b><br>Type: {item['type']}<br>Priority: <b>{item['priority']}</b>"
        ).add_to(priority_group)

    priority_group.add_to(m)

    # Add Layer Control
    folium.LayerControl().add_to(m)

    # Save to file
    m.save(output_path)
    print(f"Map saved to {output_path}")
    return m
