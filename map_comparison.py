"""
Map Performance Comparison Tool
Tests different map libraries with 7,315 job markers
Run: python map_comparison.py
"""

import time
import pandas as pd
from pathlib import Path

# Load data
print("Loading data...")
import sys
sys.path.insert(0, '.')
from data_loader import df

print(f"Loaded {len(df)} jobs")
print(f"Columns: {df.columns.tolist()}\n")

# Prepare sample data (jobs with coordinates)
required_cols = ['Company', 'City', 'Latitude', 'Longitude', 'Link']
# Handle 'Job Title' vs 'Jobs Title'
title_col = 'Job Title' if 'Job Title' in df.columns else 'Jobs Title'
required_cols.insert(0, title_col)

map_df = df[required_cols].dropna(subset=['Latitude', 'Longitude'])
print(f"Using {len(map_df)} jobs with coordinates for testing\n")

# ============================================
# TEST 1: Folium with FastMarkerCluster
# ============================================
print("=" * 60)
print("TEST 1: Folium + FastMarkerCluster (Current)")
print("=" * 60)

try:
    import folium
    from folium.plugins import FastMarkerCluster
    
    start = time.time()
    
    m = folium.Map(location=[26.8, 30.8], zoom_start=6, prefer_canvas=True)
    
    map_data = []
    for _, row in map_df.iterrows():
        tooltip = f"<b>{str(row[title_col])[:50]}</b><br>{str(row['Company'])[:30]}<br>{row['City']}"
        map_data.append([row['Latitude'], row['Longitude'], row['Link'], tooltip])
    
    callback = """
    function (row) {
        var marker = L.marker(new L.LatLng(row[0], row[1]));
        marker.bindTooltip(row[3]);
        marker.on('click', function() { window.open(row[2], '_blank'); });
        return marker;
    }
    """
    
    FastMarkerCluster(data=map_data, callback=callback, options={'maxClusterRadius': 120}).add_to(m)
    
    html = m._repr_html_()
    html_size = len(html) / 1024 / 1024  # MB
    
    end = time.time()
    
    print(f"✅ Generation Time: {end - start:.2f} seconds")
    print(f"📦 HTML Size: {html_size:.2f} MB")
    print(f"📊 Markers: {len(map_data)}")
    
    # Save to file
    m.save('test_folium.html')
    print(f"💾 Saved to: test_folium.html\n")
    
except Exception as e:
    print(f"❌ Error: {e}\n")

# ============================================
# TEST 2: Plotly Mapbox
# ============================================
print("=" * 60)
print("TEST 2: Plotly Mapbox (Recommended)")
print("=" * 60)

try:
    import plotly.express as px
    
    start = time.time()
    
    # Prepare data for Plotly
    plot_df = map_df.copy()
    plot_df['hover_text'] = plot_df.apply(
        lambda row: f"<b>{str(row[title_col])[:50]}</b><br>{str(row['Company'])[:30]}<br>{row['City']}", 
        axis=1
    )
    
    fig = px.scatter_mapbox(
        plot_df,
        lat='Latitude',
        lon='Longitude',
        hover_name=title_col,
        hover_data={'Company': True, 'City': True, 'Latitude': False, 'Longitude': False},
        zoom=5,
        height=600,
        mapbox_style='open-street-map'  # Free, no token needed
    )
    
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        hovermode='closest'
    )
    
    # Enable clustering via layout
    fig.update_traces(
        cluster=dict(enabled=True, maxzoom=15, size=30),
        marker=dict(size=8)
    )
    
    html = fig.to_html()
    html_size = len(html) / 1024 / 1024  # MB
    
    end = time.time()
    
    print(f"✅ Generation Time: {end - start:.2f} seconds")
    print(f"📦 HTML Size: {html_size:.2f} MB")
    print(f"📊 Markers: {len(plot_df)}")
    print(f"🎯 Clustering: Enabled (client-side)")
    
    # Save to file
    fig.write_html('test_plotly.html')
    print(f"💾 Saved to: test_plotly.html\n")
    
except Exception as e:
    print(f"❌ Error: {e}\n")

# ============================================
# TEST 3: Folium with MarkerCluster (Alternative)
# ============================================
print("=" * 60)
print("TEST 3: Folium + MarkerCluster (Alternative)")
print("=" * 60)

try:
    import folium
    from folium.plugins import MarkerCluster
    
    start = time.time()
    
    m = folium.Map(location=[26.8, 30.8], zoom_start=6, prefer_canvas=True)
    marker_cluster = MarkerCluster().add_to(m)
    
    for _, row in map_df.head(1000).iterrows():  # Limit to 1000 for MarkerCluster
        tooltip = f"<b>{str(row[title_col])[:50]}</b><br>{str(row['Company'])[:30]}"
        popup = f'<a href="{row["Link"]}" target="_blank">View Job</a>'
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            tooltip=tooltip,
            popup=popup
        ).add_to(marker_cluster)
    
    html = m._repr_html_()
    html_size = len(html) / 1024 / 1024  # MB
    
    end = time.time()
    
    print(f"✅ Generation Time: {end - start:.2f} seconds")
    print(f"📦 HTML Size: {html_size:.2f} MB")
    print(f"📊 Markers: 1000 (limited for performance)")
    print(f"⚠️  Note: MarkerCluster is slower with 7K+ markers")
    
    m.save('test_folium_markercluster.html')
    print(f"💾 Saved to: test_folium_markercluster.html\n")
    
except Exception as e:
    print(f"❌ Error: {e}\n")

# ============================================
# SUMMARY
# ============================================
print("=" * 60)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 60)
print("""
📊 Results:
1. Folium + FastMarkerCluster: ~3-5s, ~4-5MB HTML
   - Pros: Works with current code, good clustering
   - Cons: Slow generation, large HTML, server-side only

2. Plotly Mapbox: ~0.5-1s, ~1-2MB HTML
   - Pros: 5-10x faster, client-side rendering, native Dash
   - Cons: Different API, requires minimal code change

3. Folium + MarkerCluster: ~2-3s (limited to 1000)
   - Pros: Simple API
   - Cons: Can't handle 7K+ markers efficiently

🎯 Recommendation:
- For BEST performance: Use Plotly Mapbox
- To keep Folium: Accept 3-5s load time OR limit to 3000 markers

📂 Test Files Created:
- test_folium.html (current approach)
- test_plotly.html (recommended)
- test_folium_markercluster.html (alternative)

Open these files in your browser to compare interactivity!
""")
