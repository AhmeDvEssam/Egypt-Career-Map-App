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
    """Serve full Folium map as standalone HTML with optional filters"""
    from flask import request
    
    # Get filter parameters from URL
    cities = request.args.getlist('city')
    companies = request.args.getlist('company')
    categories = request.args.getlist('category')
    work_modes = request.args.getlist('work_mode')
    search = request.args.get('search', '')
    
    # Create cache key based on filters
    import hashlib
    filter_key = f"{cities}_{companies}_{categories}_{work_modes}_{search}"
    cache_key = hashlib.md5(filter_key.encode()).hexdigest()
    
    # Check cache
    cached_full_map = cache.get(f'full_map_{cache_key}')
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
    map_df = df[['Job Title', 'Company', 'City', 'Category', 'Work Mode', 'In_City', 'Latitude', 'Longitude', 'Link']].copy()
    map_df = map_df.dropna(subset=['Latitude', 'Longitude'])
    map_df = map_df[(map_df['Latitude'].between(22, 32)) & (map_df['Longitude'].between(25, 37))]
    
    # Apply filters
    if cities:
        map_df = map_df[map_df['City'].isin(cities)]
    if companies:
        map_df = map_df[map_df['Company'].isin(companies)]
    if categories:
        map_df = map_df[map_df['Category'].isin(categories)]
    if work_modes:
        map_df = map_df[map_df['Work Mode'].isin(work_modes)]
    if search:
        # Simple search in Job Title, Company, City
        search_lower = search.lower()
        map_df = map_df[
            map_df['Job Title'].str.lower().str.contains(search_lower, na=False) |
            map_df['Company'].str.lower().str.contains(search_lower, na=False) |
            map_df['City'].str.lower().str.contains(search_lower, na=False)
        ]
    
    # Add filter info to map
    if cities or companies or categories or work_modes or search:
        filter_text = f"<b>Filters Applied:</b><br>"
        if cities: filter_text += f"Cities: {', '.join(cities)}<br>"
        if companies: filter_text += f"Companies: {', '.join(companies[:3])}{'...' if len(companies) > 3 else ''}<br>"
        if categories: filter_text += f"Categories: {', '.join(categories[:3])}{'...' if len(categories) > 3 else ''}<br>"
        if work_modes: filter_text += f"Work Modes: {', '.join(work_modes)}<br>"
        if search: filter_text += f"Search: {search}<br>"
        filter_text += f"<b>Total Jobs: {len(map_df)}</b>"
        
        folium.Marker(
            location=[31.5, 34],  # Top right corner
            icon=folium.DivIcon(html=f"""
                <div style="background: white; padding: 10px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); font-size: 12px;">
                    {filter_text}
                </div>
            """)
        ).add_to(m)
    
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
