"""
Flask route to serve full interactive map
Access via: /full-map
"""
from flask import Response
from app_instance import server, cache
from data_loader import df
import folium
from folium.plugins import FastMarkerCluster
import pandas as pd

@server.route('/full-map')
def full_map():
    """Serve full Folium map as standalone HTML"""
    
    # Check cache first
    cached_full_map = cache.get('full_map_html')
    if cached_full_map:
        return Response(cached_full_map, mimetype='text/html')
    
    # Generate full map with all jobs
    m = folium.Map(
        location=[26.8, 30.8],
        zoom_start=6,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles © Esri',
        prefer_canvas=True
    )
    
    # Get all jobs with coordinates
    map_df = df[['Job Title', 'Company', 'City', 'In_City', 'Latitude', 'Longitude', 'Link']].copy()
    map_df = map_df.dropna(subset=['Latitude', 'Longitude'])
    map_df = map_df[(map_df['Latitude'].between(22, 32)) & (map_df['Longitude'].between(25, 37))]
    
    # Prepare markers
    map_data = []
    for _, row in map_df.iterrows():
        job_title = str(row['Job Title']).replace("'", "")
        company = str(row['Company']).replace("'", "")
        city = str(row['City'])
        in_city = str(row['In_City']) if pd.notna(row.get('In_City')) else ""
        job_link = str(row['Link']) if pd.notna(row['Link']) else "#"
        
        tooltip_html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 200px; padding: 8px;">
            <div style="font-size: 15px; font-weight: bold; color: #000; margin-bottom: 4px;">{job_title[:70]}</div>
            <div style="font-size: 14px; color: #333; margin-bottom: 3px;">{company[:50]}</div>
            <div style="font-size: 13px; color: #0066CC; margin-bottom: 8px;">{city}{f' - {in_city}' if in_city else ''}</div>
            <div style="font-size: 12px; color: #0066CC; font-weight: bold; border-top: 1px solid #ddd; padding-top: 5px;">👉 Click to Visit Wuzzuf</div>
        </div>
        """
        map_data.append([row['Latitude'], row['Longitude'], job_link, tooltip_html])
    
    # Add markers with clustering
    callback = """
    function (row) {
        var marker = L.marker(new L.LatLng(row[0], row[1]));
        marker.bindTooltip(row[3], {direction: 'top', opacity: 1, offset: [0, -10]});
        marker.on('click', function() { window.open(row[2], '_blank'); });
        return marker;
    }
    """
    
    FastMarkerCluster(
        data=map_data,
        callback=callback,
        options={
            'spiderfyOnMaxZoom': True,
            'showCoverageOnHover': False,
            'maxClusterRadius': 100,
            'animate': True
        }
    ).add_to(m)
    
    # Generate HTML
    html = m.get_root().render()
    
    # Cache for 10 minutes
    cache.set('full_map_html', html, timeout=600)
    
    return Response(html, mimetype='text/html')
