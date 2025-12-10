from dash import Input, Output, State, dash_table, callback_context, no_update, html, ALL
import dash_leaflet as dl
import pandas as pd
from app_instance import app
from data_loader import df
from utils import get_color_scale, apply_visual_highlighting, apply_chart_styling
import json
import uuid
import folium
from folium.plugins import FastMarkerCluster

# Callback to Toggle Map Mode
@app.callback(
    [Output('map-mode-store', 'data'),
     Output('switch-map-btn', 'children')],
    Input('switch-map-btn', 'n_clicks'),
    State('map-mode-store', 'data'),
    prevent_initial_call=True
)
def toggle_map_mode(n_clicks, current_mode):
    if not current_mode: current_mode = 'leaflet'
    new_mode = 'interactive' if current_mode == 'leaflet' else 'leaflet'
    
    icon_cls = "fa-solid fa-layer-group" if new_mode == 'leaflet' else "fa-solid fa-bolt"
    label = "Switch to Interactive Map" if new_mode == 'leaflet' else "Switch to Fast Map"
    
    content = [html.I(className=icon_cls, style={'marginRight':'8px'}), label]
    return new_mode, content

# Client-side validation to open link on marker click
app.clientside_callback(
    """
    function(n_clicks, data) {
        try {
            if (!n_clicks) return window.dash_clientside.no_update;
            
            // Normalize input to array if single value
            const clicks = Array.isArray(n_clicks) ? n_clicks : [n_clicks];
            
            // Check if ANY click is valid (truthy and > 0)
            const clicked = clicks.some(n => n && n > 0);
            
            if (clicked && data && data.url) {
                window.open(data.url, '_blank');
            }
        } catch (e) {
            console.error("Link Open Error:", e);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('selected-job-link-store', 'data', allow_duplicate=True),
    Input({'type': 'marker-selected', 'index': ALL}, 'n_clicks'),
    State('selected-job-link-store', 'data'),
    prevent_initial_call=True
)

@app.callback(
    [Output('city-total-jobs-kpi', 'children'),
     Output('city-top-city-kpi', 'children'),
     Output('city-avg-jobs-kpi', 'children'),
     Output('city-bar-chart', 'figure'),
     Output('city-map-leaflet', 'children'),
     Output('job-table-container', 'children'),
     Output('selected-job-link-store', 'data'),
     Output('full-map-btn-link', 'href')], 
    [Input('sidebar-company-filter', 'value'),
     Input('sidebar-city-filter', 'value'),
     Input('sidebar-category-filter', 'value'),
     Input('sidebar-work-mode-filter', 'value'),
     Input('sidebar-employment-type-filter', 'value'),
     Input('sidebar-career-level-filter', 'value'),
     Input('sidebar-education-filter', 'value'),
     Input('sidebar-avg-exp-filter', 'value'),
     Input('global-search-bar', 'value'),
     Input('map-style-dropdown', 'value'),
     Input('theme-store', 'data'),
     Input('jobs-table', 'active_cell'),
     Input('map-mode-store', 'data')],
    [State('jobs-table', 'data')]
)
def update_city_map(companies, cities, categories, work_modes, employment_types, 
                    career_levels, education_levels, avg_exp_range, search_term, map_style, theme, 
                    active_cell, map_mode, current_table_data):
    
    # Default Mode
    if not map_mode: map_mode = 'leaflet'
    
    # 1. Filter data FIRST
    filtered_df = df.copy()
    
    if companies:
        filtered_df = filtered_df[filtered_df['Company'].isin(companies)]
    if cities:
        filtered_df = filtered_df[filtered_df['City'].isin(cities)]
    if categories:
        filtered_df = filtered_df[filtered_df['Category'].isin(categories)]
    
    # CORRECT COLUMN NAMES HERE
    if work_modes:
        filtered_df = filtered_df[filtered_df['Work Mode'].isin(work_modes)]
    if employment_types:
        filtered_df = filtered_df[filtered_df['Employment Type'].isin(employment_types)]
    if career_levels:
        filtered_df = filtered_df[filtered_df['Career Level'].isin(career_levels)]
        
    if education_levels:
        # Fixed Column Name
        filtered_df = filtered_df[filtered_df['education_level'].isin(education_levels)]
    if avg_exp_range:
        # Added Avg Exp Filter
        min_exp, max_exp = avg_exp_range
        # Include NaNs if min_exp is 0 (default range start)
        mask = (filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)
        if min_exp == 0:
            mask = mask | filtered_df['Year Of Exp_Avg'].isna()
        filtered_df = filtered_df[mask]
        
    if search_term:
        mask = filtered_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)
        filtered_df = filtered_df[mask]

    # DEFINITION MOVED TO TOP SCOPE TO PREVENT NameError
    final_display_cols = ['Job Title', 'Company', 'City', 'In_City', 'Work Mode', 'Employment Type', 'Career Level', 'Year Of Exp_Avg', 'Date Posted']

    # 2. Determine trigger
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    map_output = None
    link_data = None 

    # --- BRANCH A: INTERACTIVE (FOLIUM) MODE ---
    # --- BRANCH A: INTERACTIVE (FOLIUM) MODE ---
    if map_mode == 'interactive':
        center_location = [26.8, 30.8]
        zoom_level = 6
        selected_lat = None
        selected_lon = None
        selected_popup = None
        
        # Check Table Trigger (Branch A specific logic)
        if triggered_id == 'jobs-table' and active_cell and current_table_data:
            try:
                row_idx = active_cell['row']
                if row_idx < len(current_table_data):
                    sel_row = current_table_data[row_idx]
                    if sel_row.get('Latitude') and sel_row.get('Longitude'):
                        slat = float(sel_row['Latitude'])
                        slon = float(sel_row['Longitude'])
                        if -90 <= slat <= 90 and -180 <= slon <= 180:
                            center_location = [slat, slon]
                            zoom_level = 18 # MAX ZOOM
                            selected_lat = slat
                            selected_lon = slon
                            
                            # Construct Popup for selected item
                            p_title = str(sel_row.get('Job Title', '')).replace("'", "")
                            # Clean Markdown: [Title](Link) -> Title
                            if "[" in p_title and "](" in p_title:
                                try: p_title = p_title.split('](')[0].replace('[', '')
                                except: pass
                                
                            p_comp = str(sel_row.get('Company', '')).replace("'", "")
                            p_city = str(sel_row.get('City', ''))
                            p_incity = str(sel_row.get('In_City', ''))
                            if p_incity and p_incity.lower() != 'nan': p_city += f" - {p_incity}"
                            p_link = str(sel_row.get('Link', '#'))
                            
                            p_link = str(sel_row.get('Link', '#'))
                            
                            # Enhanced Popup Content
                            p_status = str(sel_row.get('job_status', 'Open'))
                            p_work = str(sel_row.get('Work Mode', '-'))
                            p_emp = str(sel_row.get('Employment Type', '-'))
                            p_level = str(sel_row.get('Career Level', '-'))
                            p_exp = str(sel_row.get('Year Of Exp_Avg', '-'))
                            
                            selected_popup = f"""
                            <div style="font-family: 'Segoe UI', sans-serif; min-width: 350px; padding: 5px;">
                                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                                    <div style="font-weight: 900; font-size: 18px; color: #b71c1c; line-height: 1.2;">{p_title}</div>
                                    <div style="background: {'#e8f5e9' if p_status=='Open' else '#ffebee'}; color: {'#2e7d32' if p_status=='Open' else '#c62828'}; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; white-space: nowrap; margin-left: 10px;">{p_status}</div>
                                </div>
                                <div style="font-size: 15px; color: #333; font-weight: 600; margin-bottom: 4px;">{p_comp}</div>
                                <div style="font-size: 14px; color: #555; margin-bottom: 12px;">📍 {p_city}</div>
                                
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; color: #444; margin-bottom: 15px; background: #fafafa; padding: 10px; border-radius: 6px; border: 1px solid #eee;">
                                    <div>💼 <b>Type:</b> {p_emp}</div>
                                    <div>🏠 <b>Mode:</b> {p_work}</div>
                                    <div>📊 <b>Level:</b> {p_level}</div>
                                    <div>⏳ <b>Exp:</b> {p_exp} Yrs</div>
                                </div>

                                <a href="{p_link}" target="_blank" style="display: block; text-align: center; text-decoration: none; color: white; background-color: #d32f2f; padding: 10px; border-radius: 6px; font-weight: bold; font-size: 15px; box-shadow: 0 3px 6px rgba(183, 28, 28, 0.3); transition: background-color 0.2s;">
                                   Visit Job Link on Wuzzuf <span style="margin-left:5px;">&#8594;</span>
                                </a>
                            </div>
                            """
            except: pass
            
        # Tiles Logic
        if map_style == 'dark': tiles = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'; attr = '&copy; OpenStreetMap &copy; CARTO'
        elif map_style == 'satellite': tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'; attr = 'Tiles &copy; Esri'
        elif map_style == 'positron': tiles = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'; attr = '&copy; OpenStreetMap &copy; CARTO'
        elif map_style == 'osm': tiles = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'; attr = '&copy; OpenStreetMap contributors'
        else: tiles = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'; attr = '&copy; OpenStreetMap'

        m = folium.Map(location=center_location, zoom_start=zoom_level, tiles=tiles, attr=attr, zoom_control=True, scrollWheelZoom=True, prefer_canvas=True)

        map_df = filtered_df.dropna(subset=['Latitude', 'Longitude'])
        map_df = map_df[(map_df['Latitude'].between(22, 32)) & (map_df['Longitude'].between(25, 37))]
        
        # OPTIMIZATION: If a single job is selected (Table Click), skip heavy cluster generation to prevent timeout.
        # Only show the cluster if we are in "Explore Mode" (no single selection focused).
        if not selected_lat and not map_df.empty:
            map_data = []
            for _, row in map_df.iterrows():
                try:
                    job_title = str(row['Job Title']).replace("'", "")
                    company = str(row['Company']).replace("'", "")
                    city = str(row['City'])
                    in_city = str(row.get('In_City', ''))
                    if in_city and in_city.lower() != 'nan':
                         city = f"{city} - {in_city}"
                    
                    link = str(row['Link']) if pd.notna(row['Link']) else "#"
                    
                    # Popup Content
                    popup_html = f"""
                    <div style="font-family: 'Segoe UI', sans-serif; min-width: 250px; font-size: 14px;">
                        <div style="font-weight: bold; font-size: 16px; color: #111; margin-bottom: 5px;">{job_title}</div>
                        <div style="font-size: 14px; color: #555; margin-bottom: 2px;">{company}</div>
                        <div style="font-size: 13px; color: #777; margin-bottom: 8px;">{city}</div>
                        <a href="{link}" target="_blank" style="display: inline-block; text-decoration: none; color: white; background-color: #0066CC; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 13px;">
                           Visit Job Link In Wuzzuf <span style="margin-left:5px;">&#8594;</span>
                        </a>
                    </div>
                    """
                    map_data.append([row['Latitude'], row['Longitude'], link, popup_html])
                except: continue
                
            callback = """
            function (row) {
                var marker = L.marker(new L.LatLng(row[0], row[1]));
                marker.bindPopup(row[3]); 
                return marker;
            }
            """
            FastMarkerCluster(data=map_data, callback=callback).add_to(m)

        # Add Selected Job Marker (RED)
        if selected_lat and selected_lon and selected_popup:
            folium.Marker(
                location=[selected_lat, selected_lon],
                popup=folium.Popup(selected_popup, max_width=400, show=True),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        map_html = m.get_root().render()
        # Return Iframe as children
        map_output = html.Iframe(
            srcDoc=map_html, 
            style={'width': '100%', 'height': '750px', 'border': 'none', 'borderRadius': '12px', 'boxShadow': '0 4px 12px rgba(0,0,0,0.1)'}
        )

    # --- BRANCH B: FAST (LEAFLET) MODE ---
    else:
        # Logic variables with defaults
        highlight_lat = None
        highlight_lon = None
        zoom_level = 6
        center_location = [26.8, 30.8]
        selected_row = None
        is_single_view = False
        row_idx_str = "0"

        # Table click handler
        if triggered_id == 'jobs-table' and active_cell and current_table_data:
            try:
                row_idx = active_cell['row']
                if row_idx < len(current_table_data):
                    selected_row = current_table_data[row_idx]
                    row_idx_str = f"{row_idx}_{uuid.uuid4()}" # Unique ID
                    
                    if selected_row.get('Latitude') and selected_row.get('Longitude'):
                        lat = float(selected_row['Latitude'])
                        lon = float(selected_row['Longitude'])
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            highlight_lat = lat
                            highlight_lon = lon
                            center_location = [lat, lon]
                            zoom_level = 18
                            is_single_view = True
                            if selected_row.get('Link'): link_data = {'url': selected_row['Link']}
            except Exception as e: print(f"Error: {e}")

        # Map Markers Generation
        map_df = filtered_df.copy()
        markers = []

        if is_single_view and selected_row:
            row = selected_row
            raw_title = str(row['Job Title'])
            # Clean Title
            job_title_clean = raw_title
            if "[" in raw_title: 
                try: job_title_clean = raw_title.split('](')[0].replace('[', '')
                except: job_title_clean = raw_title
            
            tooltip_html = html.Div([
                html.Div(job_title_clean, style={'fontWeight': 'bold', 'fontSize': '16px', 'color': '#c62828', 'marginBottom': '4px'}),
                html.Div(str(row['Company']), style={'fontSize': '14px', 'fontWeight': '600', 'marginBottom': '4px'}),
                html.Div(str(row['City']), style={'fontSize': '13px', 'color': '#555', 'marginBottom': '4px'}),
                html.A("Visit Job Link In Wuzzuf", href=row.get('Link', '#'), target='_blank', style={'color': '#0066CC', 'fontWeight': 'bold', 'fontSize': '13px', 'textDecoration': 'underline', 'display': 'block', 'marginTop': '8px'})
            ], style={'fontFamily': 'sans-serif', 'padding': '12px', 'minWidth': '200px', 'pointerEvents': 'auto'})

            # Single RED Marker
            markers.append(dl.CircleMarker(
                center=[highlight_lat, highlight_lon], radius=15, color='#b71c1c', fillColor='#f44336', fillOpacity=1.0,
                children=[dl.Tooltip(tooltip_html, direction='top', sticky=False, permanent=True, interactive=True, className='custom-leaflet-tooltip')],
                id={'type': 'marker-selected', 'index': row_idx_str}
            ))

        else:
            # Cluster Logic
            if 'Latitude' in map_df.columns and 'Longitude' in map_df.columns:
                valid_map_df = map_df.dropna(subset=['Latitude', 'Longitude'])
                valid_map_df = valid_map_df[(valid_map_df['Latitude'].between(22, 32)) & (valid_map_df['Longitude'].between(24, 38))]
                city_groups = valid_map_df.groupby('City')
                max_val = city_groups.size().max() if not city_groups.size().empty else 1
                
                def get_color(count, max_c):
                    ratio = count / max_c
                    if ratio < 0.1: return 'rgba(144, 202, 249, 0.9)'
                    if ratio < 0.3: return 'rgba(66, 165, 245, 0.9)'
                    if ratio < 0.6: return 'rgba(30, 136, 229, 0.9)'
                    if ratio < 0.8: return 'rgba(21, 101, 192, 0.9)'
                    return 'rgba(13, 71, 161, 0.95)'

                for city_name, group in city_groups:
                    count = len(group)
                    lat = group['Latitude'].mean()
                    lon = group['Longitude'].mean()
                    
                    # Size Logic
                    radius = 15
                    if count > 50: radius = 22
                    if count > 200: radius = 30
                    if count > 1000: radius = 38
                    size = radius * 2
                    
                    fill_color = get_color(count, max_val)
                    
                    markers.append(dl.CircleMarker(
                        center=[lat, lon],
                        radius=radius,
                        color='white',
                        weight=1,
                        fillColor=fill_color,
                        fillOpacity=0.8,
                        children=[
                            dl.Tooltip(
                                html.Div([
                                    html.Span(str(count), className='marker-count'),
                                    html.Span(city_name, className='marker-name')
                                ], className='marker-content'),
                                permanent=True, 
                                direction='center', 
                                className='custom-marker-tooltip',
                                opacity=1
                            )
                        ],
                        id=f"city-marker-{city_name}"
                    ))

        # Leaflet Output
        map_styles = {
            'voyager': 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
            'positron': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            'dark': 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            'satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'osm': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        }
        tile_url = map_styles.get(map_style, map_styles['voyager'])
        if map_style == 'satellite': attribution = 'Tiles &copy; Esri'
        elif map_style == 'osm': attribution = '&copy; OpenStreetMap contributors'
        else: attribution = '&copy; OpenStreetMap &copy; CARTO'
        
        map_output = dl.Map(
            center=center_location,
            zoom=zoom_level,
            children=[
                dl.TileLayer(url=tile_url, attribution=attribution),
                dl.LayerGroup(children=markers)
            ],
            style={'width': '100%', 'height': '750px', 'borderRadius': '12px', 'boxShadow': '0 4px 12px rgba(0,0,0,0.1)'},
            id='city-map-leaflet-internal' 
        )

    # KPIs
    total_jobs = len(filtered_df)
    # ... (Keep existing KPI logic) ...
    
    # Construct Full Map Link with Filters
    import urllib.parse
    query_params = {}
    if companies: query_params['company'] = companies
    if cities: query_params['city'] = cities
    if categories: query_params['category'] = categories
    if work_modes: query_params['work_mode'] = work_modes
    if search_term: query_params['search'] = search_term
    
    full_map_href = "/full-map"
    if query_params:
        full_map_href += "?" + urllib.parse.urlencode(query_params, doseq=True)


    city_counts = filtered_df['City'].value_counts()
    top_city = city_counts.index[0] if len(city_counts) > 0 else "N/A"
    avg_jobs = round(city_counts.mean(), 1) if len(city_counts) > 0 else 0
    
    # Bar Chart 
    import plotly.express as px
    top_n_cities = 50
    chart_data = city_counts.head(top_n_cities)
    chart_df_local = pd.DataFrame({'City': chart_data.index, 'Count': chart_data.values})
    
    city_bar_fig = px.bar(
        chart_df_local,
        x='Count',
        y='City',
        orientation='h',
        title=f'Top {top_n_cities} Cities by Job Count',
        text_auto=True
    )
    city_bar_fig.update_yaxes(autorange="reversed", tickfont=dict(size=14)) 
    chart_height = max(600, len(city_counts[:top_n_cities]) * 45)
    city_bar_fig.update_layout(height=chart_height) 
    city_bar_fig.update_traces(marker_color='#0066CC', textfont_size=14, textposition='outside')
    apply_chart_styling(city_bar_fig, is_horizontal_bar=True, theme=theme)
    
    # ---------------------------------------------------------
    # RESTORED LOGIC FOR TABLE DATAFRAME AND TOOLTIPS
    # ---------------------------------------------------------
    
    # Job Table - USING CORRECT COLUMN NAMES
    req_cols = ['Job Title', 'Company', 'City', 'In_City', 'Work Mode', 'Employment Type', 
               'Career Level', 'Year Of Exp_Avg', 'posted', 'job_status', 'Skills', 'Link', 'Latitude', 'Longitude']
    
    for c in req_cols:
        if c not in filtered_df.columns:
            filtered_df[c] = None

    table_cols = req_cols 
    table_df = filtered_df[table_cols].head(10000) 
    
    if 'posted' in table_df.columns:
        table_df['Date Posted'] = pd.to_datetime(table_df['posted'], errors='coerce').dt.strftime('%Y-%m-%d')
    else:
        table_df['Date Posted'] = ""

    # Job Title as Link Logic
    def make_job_link(row):
        title = str(row['Job Title'])
        link = row['Link']
        if pd.notna(link) and len(str(link)) > 5:
            return f"[{title}]({link})"
        return title

    if 'Link' in table_df.columns and 'Job Title' in table_df.columns:
        table_df['Job Title'] = table_df.apply(make_job_link, axis=1)

    # Tooltip data generation
    tooltip_data = []
    
    def clean_val(val):
        s = str(val).strip()
        if not s or s.lower() in ['nan', 'n/a', 'none', 'nat', '']: return None
        return s

    for idx, row in table_df.iterrows():
        row_tooltip = {}
        vals = {
            'job': clean_val(row.get('Job Title')),
            'comp': clean_val(row.get('Company')),
            'wmode': clean_val(row.get('Work Mode')),
            'city': clean_val(row.get('City')),
            'incity': clean_val(row.get('In_City')),
            'emp': clean_val(row.get('Employment Type')),
            'level': clean_val(row.get('Career Level')),
            'exp': clean_val(row.get('Year Of Exp_Avg')),
            'skills': clean_val(row.get('Skills')),
            'date': clean_val(row.get('Date Posted')),
            'status': clean_val(row.get('job_status')),
            'link': row.get('Link', '#')
        }
        
        # Reconstruct MD (clean title for header)
        md = ""
        raw_title = vals['job']
        # Strip markdown from title if present for the header part
        if raw_title and '[' in raw_title:
             try:
                raw_title = raw_title.split('](')[0].replace('[', '')
             except: pass
        
        if raw_title: md += f"**{raw_title}**\n\n"
        if vals['comp']: md += f"_{vals['comp']}_\n\n"
        
        loc_parts = []
        if vals['wmode']: loc_parts.append(f"📍 {vals['wmode']}")
        if vals['city']: 
            c = vals['city']
            if vals['incity']: c += f" - {vals['incity']}"
            loc_parts.append(c)
        if loc_parts: md += " | ".join(loc_parts) + "\n\n"
        
        meta_parts = []
        if vals['emp']: meta_parts.append(f"💼 {vals['emp']}")
        if vals['level']: meta_parts.append(f"🎓 {vals['level']}")
        if vals['exp']: meta_parts.append(f"⏳ {vals['exp']} Yrs")
        if meta_parts: md += " | ".join(meta_parts) + "\n\n"
        
        if vals['status']: md += f"**Status:** {vals['status']}  "
        if vals['date']: md += f"**Posted:** {vals['date']}\n\n"
        
        if vals['skills']: md += f"**Skills:**\n{vals['skills']}\n\n"
        
        md += f"🔗 [Visit Job Link]({vals['link']})"

        # Safer loop using defined columns from top scope
        cols_to_tooltip = ['Job Title', 'Company', 'City', 'In_City', 'Work Mode', 'Employment Type', 'Career Level', 'Year Of Exp_Avg', 'Date Posted']
        for col in cols_to_tooltip: 
            row_tooltip[col] = {'value': md, 'type': 'markdown'}
        tooltip_data.append(row_tooltip)

    is_dark = theme == 'dark'
    table_bg = '#1e1e1e' if is_dark else 'white'
    table_text = '#e0e0e0' if is_dark else '#333'
    header_bg = '#0d47a1' if is_dark else '#0066CC'
    header_text = 'white'
    row_odd = '#2d2d2d' if is_dark else '#f9f9f9'
    row_even = '#1e1e1e' if is_dark else 'white'
    row_hover = '#303f9f' if is_dark else '#E3F2FD'
    
    job_table = dash_table.DataTable(
        id='jobs-table',
        columns=[
            {"name": i.replace('_', ' '), "id": i, "presentation": "markdown"} if i in ["Job Title", "Visit"] else {"name": i.replace('_', ' '), "id": i} 
            for i in final_display_cols
        ],
        data=table_df.to_dict('records'),
        tooltip_data=tooltip_data,
        tooltip_duration=None,
        page_action='native',
        page_size=15,
        style_table={'overflowX': 'auto', 'borderRadius': '8px', 'border': '1px solid #444' if is_dark else '1px solid #ddd'},
        style_cell={
            'textAlign': 'left',
            'padding': '12px',
            'fontFamily': 'Segoe UI, sans-serif',
            'fontSize': '13px',
            'backgroundColor': table_bg,
            'color': table_text,
            'borderBottom': '1px solid #444' if is_dark else '1px solid #eee',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'minWidth': '150px',
            'maxWidth': '300px'
        },
        style_header={
            'backgroundColor': header_bg,
            'color': header_text,
            'fontWeight': 'bold',
            'fontSize': '14px',
            'border': 'none',
            'padding': '12px'
        },
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': row_odd},
            {'if': {'row_index': 'even'}, 'backgroundColor': row_even},
            {'if': {'state': 'active'}, 'backgroundColor': row_hover, 'border': '1px solid #0066CC', 'color': 'white' if is_dark else 'inherit'}
        ],
        css=[
            {'selector': '.dash-table-tooltip', 
             'rule': '''
                background-color: #fcfcfc !important; 
                color: #333 !important; 
                border: 1px solid #ccc !important; 
                border-radius: 8px !important; 
                padding: 15px !important; 
                font-family: 'Segoe UI', sans-serif !important;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
                min-width: 400px !important;
                max-width: 600px !important;
                width: auto !important;
                font-size: 14px !important;
                z-index: 9999 !important;
             '''},
             {'selector': 'td.cell--selected, td.focused', 'rule': 'background-color: transparent !important;'}
        ]
    )

    if triggered_id == 'jobs-table':
        return (
            no_update, # Total Jobs
            no_update, # Top City
            no_update, # Avg Jobs
            no_update, # Bar Chart (Prevent reload!)
            map_output, # Map (Update zoom/markers or Iframe)
            no_update, # Job Table (Keep persistence!)
            link_data,  # Store: Update with link if single view
            no_update # Full Map Link
        )

    return (
        f"{total_jobs:,}",
        top_city,
        f"{avg_jobs:,}",
        city_bar_fig,
        map_output, # Use unified map_output
        job_table,
        link_data,
        full_map_href
    )



# Callback to sync Map Zoom/Center to Store
@app.callback(
    Output('map-zoom-store', 'data'),
    [Input('city-map-leaflet-internal', 'zoom'),
     Input('city-map-leaflet-internal', 'center')],
    prevent_initial_call=True
)
def update_map_store(zoom, center):
    if zoom is None: return no_update
    return {'zoom': zoom, 'center': center}


# CLIENT-SIDE CALLBACK FOR MAP CLASS ZOOM
app.clientside_callback(
    """
    function(zoom_data) {
        if (!zoom_data) return 'map-low-zoom';
        if (zoom_data.zoom > 7) return 'map-high-zoom';
        return 'map-low-zoom';
    }
    """,
    Output('map-wrapper', 'className'),
    Input('map-zoom-store', 'data')
)
