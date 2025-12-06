from dash import Input, Output, State, dash_table, callback_context, no_update
import plotly.express as px
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from app_instance import app, cache
from data_loader import df
from utils import get_color_scale, apply_visual_highlighting, apply_chart_styling, apply_large_fonts_to_chart
import hashlib
import json

# Helper function to generate map HTML (cached)
@cache.memoize(timeout=300)  # Cache for 5 minutes
def generate_map_html(filter_hash, map_style, theme, highlight_lat=None, highlight_lon=None, highlight_title=None):
    """Generate Folium map HTML - cached based on filters"""
    # Reconstruct filtered_df from global df based on filter_hash
    # For now, we'll cache the entire map generation
    # This is a simplified version - in production you'd pass actual filter params
    
    filtered_df_for_map = df.copy()  # This should be filtered based on filter_hash
    
    # Map generation logic (extracted from main callback)
    center_location = [26.8, 30.8]
    zoom_level = 6
    
    if highlight_lat and highlight_lon:
        center_location = [highlight_lat, highlight_lon]
        zoom_level = 15
    
    # Map Tiles Logic
    if map_style == 'dark':
        tiles = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
        attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    elif map_style == 'satellite':
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        attr = 'Tiles &copy; Esri'
    elif map_style == 'positron':
        tiles = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
        attr = '&copy; OpenStreetMap &copy; CARTO'
    elif map_style == 'osm':
        tiles = 'OpenStreetMap'
        attr = '&copy; OpenStreetMap'
    else:
        tiles = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
        attr = '&copy; OpenStreetMap'

    m = folium.Map(
        location=center_location, 
        zoom_start=zoom_level,
        tiles=tiles,
        attr=attr,
        zoom_control=True,
        scrollWheelZoom=True,
        prefer_canvas=True  # Performance boost
    )
    
    return m  # Return map object, not HTML yet


@app.callback(
    [Output('city-total-jobs-kpi', 'children'),
     Output('city-top-city-kpi', 'children'),
     Output('city-avg-jobs-kpi', 'children'),
     Output('city-bar-chart', 'figure'),
     Output('city-map', 'srcDoc'),
     Output('job-table-container', 'children')],
    [Input('sidebar-company-filter', 'value'),
     Input('sidebar-city-filter', 'value'),
     Input('sidebar-category-filter', 'value'),
     Input('sidebar-work-mode-filter', 'value'),
     Input('sidebar-employment-type-filter', 'value'),
     Input('sidebar-career-level-filter', 'value'),
     Input('sidebar-education-filter', 'value'),
     Input('sidebar-date-filter', 'start_date'),
     Input('sidebar-date-filter', 'end_date'),
     Input('sidebar-in-city-filter', 'value'),
     Input('sidebar-avg-exp-filter', 'value'),
     Input('sidebar-month-filter', 'value'),
     Input('map-style-dropdown', 'value'),
     Input('global-search-bar', 'value'),
     Input('theme-store', 'data'),
     Input('jobs-table', 'active_cell')]  # For Linking Table -> Map
)
def update_city_map(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, map_style, search_text, theme, active_cell):
    
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'initial'

    # 1. Base Filtering
    filtered_df = df.copy()
    
    if companies: filtered_df = filtered_df[filtered_df['Company'].isin(companies)]
    if cities: filtered_df = filtered_df[filtered_df['City'].isin(cities)]
    if categories: filtered_df = filtered_df[filtered_df['Category'].isin(categories)]
    if work_modes: filtered_df = filtered_df[filtered_df['Work Mode'].isin(work_modes)]
    if employment_types: filtered_df = filtered_df[filtered_df['Employment Type'].isin(employment_types)]
    if career_levels: filtered_df = filtered_df[filtered_df['Career Level'].isin(career_levels)]
    if education_levels: filtered_df = filtered_df[filtered_df['education_level'].isin(education_levels)]
    
    if start_date and end_date and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[(filtered_df['posted'] >= start_date) & (filtered_df['posted'] <= end_date)]
        
    if in_cities and 'In_City' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
        
    if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
        filtered_df = filtered_df[(filtered_df['Year Of Exp_Avg'] >= avg_exp_range[0]) & (filtered_df['Year Of Exp_Avg'] <= avg_exp_range[1])]
        
    if months and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]
        
    if search_text and search_text.strip():
        from utils import filter_dataframe_by_search
        filtered_df = filter_dataframe_by_search(filtered_df, search_text)

    # --- KPI Calculations ---
    total_jobs_city = len(filtered_df)
    top_city = filtered_df['City'].value_counts().index[0] if 'City' in filtered_df.columns and not filtered_df.empty else "N/A"
    avg_jobs_per_city = round(filtered_df.groupby('City').size().mean(), 1) if 'City' in filtered_df.columns and not filtered_df.empty else 0

    # --- City Bar Chart ---
    col = 'City'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    city_counts = s.value_counts().reset_index()
    city_counts.columns = [col, 'count']
    city_counts = city_counts.sort_values('count', ascending=True).tail(20)
    
    deep_blue_scale = get_color_scale(theme)
    city_bar_fig = px.bar(city_counts, x='count', y=col, title='Jobs by City', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    dynamic_height = max(500, len(city_counts) * 40)
    city_bar_fig.update_layout(height=dynamic_height)
    apply_chart_styling(city_bar_fig, is_horizontal_bar=True, theme=theme)

    # --- Interactivity: Check for Table Selection ---
    center_location = [26.8, 30.8]
    zoom_level = 6
    highlight_row = None
    
    # If Triggered by Table Click (Link Table -> Map)
    if triggered_id == 'jobs-table' and active_cell:
        row_idx = active_cell['row']
        if row_idx < len(filtered_df):
            target_row = filtered_df.iloc[row_idx]
            if pd.notna(target_row['Latitude']) and pd.notna(target_row['Longitude']):
                center_location = [target_row['Latitude'], target_row['Longitude']]
                zoom_level = 15 # Zoom in on the job
                highlight_row = target_row
    elif cities and len(cities) > 0:
         # Fallback to City Center if no row selected but city filter exists
         city_data = filtered_df[filtered_df['City'] == cities[0]]
         if not city_data.empty and 'Latitude' in city_data.columns and 'Longitude' in city_data.columns:
             city_coords_df = city_data[['Latitude', 'Longitude']].dropna()
             if not city_coords_df.empty:
                 city_coords = city_coords_df.iloc[0]
                 center_location = [city_coords['Latitude'], city_coords['Longitude']]
                 zoom_level = 11

    # --- Generate Folium Map ---
    # Map Tiles Logic
    if map_style == 'dark':
        tiles = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
        attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    elif map_style == 'satellite':
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        attr = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    elif map_style == 'positron':
        tiles = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
        attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    elif map_style == 'osm':
        tiles = 'OpenStreetMap'
        attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    else:
        tiles = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
        attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

    m = folium.Map(
        location=center_location, 
        zoom_start=zoom_level,
        tiles=tiles,
        attr=attr,
        zoom_control=True,
        scrollWheelZoom=True
    )
    
    # Only fit bounds if we are NOT zoomed in on a specific job
    if highlight_row is None and not (cities and len(cities) > 0):
        m.fit_bounds([[22, 25], [32, 37]])

    map_df = filtered_df.copy()
    if 'Latitude' in map_df.columns and 'Longitude' in map_df.columns:
        map_df = map_df.dropna(subset=['Latitude', 'Longitude'])
        # Filter bounds
        map_df = map_df[(map_df['Latitude'].between(22, 32)) & (map_df['Longitude'].between(25, 37))]

        if not map_df.empty:
            map_data = []
            for _, row in map_df.iterrows():
                job_title = str(row['Job Title']).replace("'", "")[:50]  # Limit length
                company = str(row['Company']).replace("'", "")[:30]
                city = str(row['City'])[:20]
                job_link = str(row['Link']) if pd.notna(row['Link']) else "#"
                
                # SIMPLIFIED tooltip - much smaller HTML
                tooltip_html = f"<b>{job_title}</b><br>{company}<br>{city}"
                
                map_data.append([row['Latitude'], row['Longitude'], job_link, tooltip_html])
            
            # JS Callback for Clusters - Optimized
            callback = """
            function (row) {
                var marker = L.marker(new L.LatLng(row[0], row[1]));
                marker.bindTooltip(row[3], {
                    direction: 'top',
                    className: 'custom-map-tooltip',
                    opacity: 1,
                    offset: [0, -10]
                });
                marker.on('click', function() {
                    window.open(row[2], '_blank');
                });
                return marker;
            }
            """
            # Use optimized clustering settings - ALWAYS cluster for performance
            FastMarkerCluster(
                data=map_data, 
                callback=callback, 
                name='Jobs',
                options={
                    'spiderfyOnMaxZoom': True,
                    'showCoverageOnHover': False,
                    'maxClusterRadius': 120,  # Larger radius = more aggressive clustering
                    'animate': True,
                    'animateAddingMarkers': False  # Faster initial load
                }
            ).add_to(m)
            
            # If a row is highlighted, add a special marker in Red
            if highlight_row is not None:
                # Add a functional popup + click behavior (via popup for simplicity in Python)
                target_link = str(highlight_row['Link']) if pd.notna(highlight_row['Link']) else "#"
                popup_html = f'<a href="{target_link}" target="_blank" style="font-weight:bold; font-size:14px; color:#0066CC;">👉 Click to Visit Job Page</a>'
                
                folium.Marker(
                    location=[highlight_row['Latitude'], highlight_row['Longitude']],
                    tooltip="Selected Job: " + str(highlight_row['Job Title']),
                    popup=folium.Popup(popup_html, max_width=300),
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(m)

    map_html = m.get_root().render()

    # --- Job Table (Updated with requested columns and rich tooltip) ---
    display_cols = ['Job Title', 'Company', 'City', 'Category', 'Year Of Exp_Avg', 
                   'Work Mode', 'Employment Type', 'Career Level', 'Skills', 'applicants', 'posted']
    final_cols = [c for c in display_cols if c in filtered_df.columns]
    rename_map = {'Year Of Exp_Avg': 'Exp (Yrs)', 'posted': 'Date Posted'}
    table_df = filtered_df[final_cols].rename(columns=rename_map).copy()

    # Ensure Title is a Link (Markdown) for "Click to Visit" behavior
    if 'Link' in filtered_df.columns and 'Job Title' in table_df.columns:
         # Need original Link column to construct markdown
         # We already filtered table_df, so map by index or merge?
         # filtered_df matches table_df indexwise if we didn't drop rows. We copied.
         # Safer to rely on the fact we haven't reordered table_df relative to filtered_df yet.
         links = filtered_df['Link'].fillna('#')
         titles = table_df['Job Title']
         table_df['Job Title'] = [f"[{t}]({l})" for t, l in zip(titles, links)]

    if 'Date Posted' in table_df.columns:
        table_df['Date Posted'] = pd.to_datetime(table_df['Date Posted'], errors='coerce').dt.strftime('%b %d')

    tooltip_data = []
    for i, row in table_df.iterrows():
        # Rich Tooltip Content with all details
        tt = f"""
**{row.get('Job Title', 'N/A').split(']')[0][1:] if '[' in str(row.get('Job Title', '')) else row.get('Job Title', 'N/A')}**  
*{row.get('Company', 'N/A')}*  
📍 {row.get('City', 'N/A')} | 💼 {row.get('Work Mode', 'N/A')}  
🎓 {row.get('Career Level', 'N/A')} | 🕒 {row.get('Employment Type', 'N/A')}  

**Skills:**  
{str(row.get('Skills', 'No skills listed'))[:200]}{'...' if len(str(row.get('Skills', ''))) > 200 else ''}

👉 **Click Title to Visit Link on Wuzzuf**
        """
        tooltip_data.append({c: {'value': tt, 'type': 'markdown'} for c in table_df.columns})

    style_header = {
        'backgroundColor': '#0f172a', 
        'color': '#f8fafc', 
        'fontWeight': 'bold', 
        'border': '1px solid #334155'
    }
    style_cell = {
        'backgroundColor': '#1e293b' if theme == 'dark' else '#ffffff',
        'color': '#e2e8f0' if theme == 'dark' else '#1e293b',
        'border': '1px solid #334155' if theme == 'dark' else '1px solid #e2e8f0',
        'padding': '12px',
        'textAlign': 'left',
        'fontFamily': 'Inter',
        'maxWidth': '200px',
        'overflow': 'hidden',
        'textOverflow': 'ellipsis',
    }
    style_data_conditional = [
        {'if': {'state': 'active'}, 'backgroundColor': 'rgba(56, 189, 248, 0.2)', 'border': '1px solid #38bdf8'},
        {'if': {'state': 'selected'}, 'backgroundColor': 'rgba(56, 189, 248, 0.3)', 'border': '1px solid #38bdf8'},
        {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgba(255, 255, 255, 0.03)' if theme == 'dark' else '#f8fafc'}
    ]

    # Tooltip Styling (Large width, visible text)
    css = [
        {'selector': '.dash-spreadsheet td:hover', 'rule': 'color: #0066CC !important; font-weight: bold; cursor: pointer;'},
        {'selector': '.dash-table-tooltip', 'rule': 'background-color: #1e293b !important; color: white !important; font-size: 14px; border: 1px solid #334155; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5); width: 400px !important; max-width: 400px !important; min-width: 400px !important; white-space: pre-wrap !important;'},
        {'selector': '.dash-tooltip', 'rule': 'border: none !important;'}
    ]

    table_component = dash_table.DataTable(
        id='jobs-table',
        data=table_df.to_dict('records'),
        columns=[
            {'name': i, 'id': i, 'presentation': 'markdown'} if i == 'Job Title' else {'name': i, 'id': i}
            for i in table_df.columns
        ],
        style_table={'overflowX': 'auto', 'minWidth': '100%'}, # Ensure scrollbar appears
        style_header=style_header,
        style_cell=style_cell,
        style_data_conditional=style_data_conditional,
        tooltip_data=tooltip_data,
        tooltip_duration=None,
        css=css,
        page_size=15,
        page_action='native',
        sort_action='native',
        filter_action='native',
        row_selectable='single'
    )

    return f"{total_jobs_city:,}", top_city, f"{avg_jobs_per_city:.1f}", city_bar_fig, map_html, table_component
