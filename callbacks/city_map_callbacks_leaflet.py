from dash import Input, Output, State, dash_table, callback_context, no_update, html, ALL, ClientsideFunction
import dash_leaflet as dl
import pandas as pd
from app_instance import app
from data_loader import df
from utils import get_color_scale, apply_visual_highlighting, apply_chart_styling
import json
import uuid
import folium
from folium.plugins import FastMarkerCluster
import uuid
import gc
import sys
import time
from dash_extensions.javascript import Namespace

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

# Client-side callback to SHOW the popup when TRIGGER updates
app.clientside_callback(
    """
    function(trigger_data) {
        if (trigger_data) {
            // DIRECT DOM FORCE - Bypass React Reconciliation
            var el = document.getElementById('click-popup');
            if (el) {
                el.style.display = 'block';
                el.style.visibility = 'visible'; // Ensure visibility
            }
            
            return {
                'display': 'block', 
                'position': 'fixed', 
                'bottom': '30px', 
                'right': '30px', 
                'width': '600px', 
                'zIndex': 999999, 
                'boxShadow': '0 10px 40px rgba(0,0,0,0.3)', 
                'fontFamily': 'Segoe UI, sans-serif',
                '--force-render': trigger_data 
            };
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('click-popup', 'style', allow_duplicate=True),
    Input('popup-show-trigger', 'data'),
    prevent_initial_call=True
)

# Client-side callback to CLOSE the persistent popup
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            return {'display': 'none'};
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('click-popup', 'style', allow_duplicate=True),
    Input('close-popup-btn', 'n_clicks'),
    prevent_initial_call=True
)

@app.callback(
    [Output('city-total-jobs-kpi', 'children'),
     Output('city-top-city-kpi', 'children'),
     Output('city-avg-jobs-kpi', 'children'),
     Output('city-bar-chart', 'figure'),
     Output('city-map-leaflet', 'children'),
     Output('jobs-table', 'data'),
     Output('jobs-table', 'tooltip_data'),
     Output('jobs-table', 'page_count'),
     Output('selected-job-link-store', 'data'),
     Output('full-map-btn-link', 'href'),
     Output('click-popup', 'children'),
     Output('popup-show-trigger', 'data'),
     Output('total-jobs-count-store', 'data')], 
    [Input('sidebar-company-filter', 'value'),
     Input('sidebar-city-filter', 'value'),
     Input('sidebar-category-filter', 'value'),
     Input('sidebar-work-mode-filter', 'value'),
     Input('sidebar-job-status-filter', 'value'),
     Input('sidebar-employment-type-filter', 'value'),
     Input('sidebar-career-level-filter', 'value'),
     Input('sidebar-education-filter', 'value'),
     Input('sidebar-avg-exp-filter', 'value'),
     Input('global-search-bar', 'value'),
     Input('map-style-dropdown', 'value'),
     Input('theme-store', 'data'),
     Input('jobs-table', 'active_cell'),
     Input('map-mode-store', 'data'),
     Input('jobs-table', 'page_current'),
     Input('jobs-table', 'page_size'),
     Input('nav-action-store', 'data')],
    [State('jobs-table', 'data')]
)
def update_city_map(companies, cities, categories, work_modes, job_statuses, employment_types, 
                    career_levels, education_levels, avg_exp_range, search_term, map_style, theme, 
                    active_cell, map_mode, page_current, page_size, nav_action_data, current_table_data):
    
    try:
        print("DEBUG: update_city_map triggered")
        # Explicit GC
        gc.collect()
        
        # Helper for cleaning values (Critical for Tooltips)
        def clean_val(val):
            if pd.isna(val) or str(val).lower() == 'nan' or val == 'None' or val == '':
                return ""
            return str(val)
        
        # Initialize Popup Output
        popup_children = no_update
        popup_trigger = no_update
        popup_style = {'display': 'none'}

        # ... (Rest of existing logic setup)
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
        if job_statuses:
            filtered_df = filtered_df[filtered_df['job_status'].isin(job_statuses)]
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
        # Added 'How Long Ago' to ensure it survives for the Table Data
        # RESTORED COLUMNS (User Request Step 11552: Popup needs these!)
        final_display_cols = ['Job Title', 'Company', 'City', 'In_City', 'Work Mode', 'Employment Type', 'Career Level', 'Year Of Exp_Avg', 'Date Posted', 'job_status', 'Skills', 'Link', 'Latitude', 'Longitude', 'Image_link']

        # 2. Determine trigger (MOVED TO TOP TO SUPPORT SLICING LOGIC)
        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Check for Nav Button Trigger to SUPPRESS POPUP
        triggered_props = [t['prop_id'] for t in ctx.triggered] if ctx.triggered else []
        is_nav_trigger = any('nav-action-store' in p for p in triggered_props)
        
        # If nav trigger, we ensure we don't accidentally consider it 'active_cell' manual click for popup purposes
        # But 'is_active_cell' below logic handles Map skipping. We want Map Zoom, so 'active_cell' logic is fine.
        # We just need to suppress the 'click-popup' generation later.

        # ------------------------------------------------------------------
        # MOVED LOGIC TO TOP: PRE-CALCULATE TABLE SLICE FOR MAP SYNC
        # ------------------------------------------------------------------
        req_cols = ['Job Title', 'Company', 'City', 'In_City', 'Work Mode', 'Employment Type', 
                   'Career Level', 'Year Of Exp_Avg', 'posted', 'job_status', 'Skills', 'Link', 'Latitude', 'Longitude', 'How Long Ago', 'Date Posted', 'Image_link']
        
        for c in req_cols:
            if c not in filtered_df.columns:
                filtered_df[c] = None

        table_cols = req_cols 
        target_df = filtered_df
        
        import math
        current_page = 0
        if triggered_id == 'jobs-table' and page_current is not None:
             current_page = page_current
        
        if page_size is None: page_size = 15
        
        # Reset page to 0 if filters changed (triggered_id is NOT jobs-table)
        if triggered_id != 'jobs-table':
            current_page = 0
            
        # SERVER-SIDE PAGINATION: Slice only the visible rows
        start_idx = current_page * page_size
        end_idx = start_idx + page_size
        table_df = target_df[table_cols].iloc[start_idx:end_idx].copy()
        
        # Calculate Total Pages for the Paginator
        total_pages = math.ceil(len(target_df) / page_size)
        
        if 'posted' in table_df.columns:
            table_df['Date Posted'] = pd.to_datetime(table_df['posted'], errors='coerce').dt.strftime('%Y-%m-%d')
        else:
            table_df['Date Posted'] = ""

        # Job Title as Link Logic
        def make_job_link_inner(row):
            title = str(row['Job Title'])
            link = row['Link']
            if pd.notna(link) and len(str(link)) > 5:
                return f"[{title}]({link})"
            return title

        if 'Link' in table_df.columns and 'Job Title' in table_df.columns:
            table_df['Job Title'] = table_df.apply(make_job_link_inner, axis=1)

        # Convert to records for Map Logic usage
        current_table_records = table_df.to_dict('records')
        # ------------------------------------------------------------------

        # ------------------------------------------------------------------

        map_output = None
        
        # ---------------------------------------------------------
        # OPTIMIZATION: EARLY RETURN FOR PAGINATION
        # If trigger is ONLY table pagination, we do NOT need to regenerate the Map (saves 2s+ latency).
        # We must assume 'filtered_df' is consistent because filters didn't change (only table page changed).
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        if triggered_id == 'jobs-table':
             is_pagination = 'page_current' in ctx.triggered[0]['prop_id'] if ctx.triggered else False
             is_active_cell = 'active_cell' in ctx.triggered[0]['prop_id'] if ctx.triggered else False
             
             if is_pagination and not is_active_cell:
                 pass # Skip Logic
        # ---------------------------------------------------------
             
        map_output = no_update # Default if skipped
        link_data = None 
        
        # 3. Calculate Map Data GLOBALLY (for Consistency)
        # We must align KPI and Map to show the SAME numbers as requested.
        map_df_all = filtered_df.dropna(subset=['Latitude', 'Longitude'])
        map_df_all = map_df_all[(map_df_all['Latitude'].between(22, 32)) & (map_df_all['Longitude'].between(25, 37))]
        
        # Determine if we need to run Map Logic
        run_map_logic = True
        
        # OPTIMIZATION: Only skip if PAGE changed but ACTIVE CELL did NOT change.
        triggered_props = [t['prop_id'] for t in ctx.triggered] if ctx.triggered else []
        is_pagination = any('page_current' in p for p in triggered_props)
        is_active_cell = any('active_cell' in p for p in triggered_props)
        
        if triggered_id == 'jobs-table' and is_pagination and not is_active_cell:
             run_map_logic = False
             
        # --- BRANCH A: INTERACTIVE (FOLIUM) MODE ---
        if map_mode == 'interactive' and run_map_logic:
            center_location = [26.8, 30.8]
            # ... (Rest of Branch A variables) ...
            zoom_level = 6
            selected_lat = None
            selected_lon = None
            selected_popup = None
            
            # Check Table Trigger (Branch A specific logic)
            if triggered_id == 'jobs-table' and active_cell and current_table_records:
                try:
                    row_idx = active_cell['row']
                    if row_idx < len(current_table_records):
                        sel_row = current_table_records[row_idx]
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

            map_df = map_df_all # Use Globally filtered map_df
            # map_df = filtered_df.dropna(subset=['Latitude', 'Longitude'])
            # map_df = map_df[(map_df['Latitude'].between(22, 32)) & (map_df['Longitude'].between(25, 37))]
            
            # PERFORMANCE CAP REMOVED: User requested all data.
            # if len(map_df) > 150: ...
            
            # OPTIMIZATION: If a single job is selected (Table Click), skip heavy cluster generation to prevent timeout.
            # Only show the cluster if we are in "Explore Mode" (no single selection focused).
            if not selected_lat and not map_df.empty:
                map_data = []
                # Optimized Loop using zip (10x faster than iterrows)
                # Pre-calc columns to avoid overhead
                cols = ['Latitude', 'Longitude', 'Job Title', 'Company', 'City', 'Link', 'In_City', 'Image_link']
                # Ensure columns exist
                for c in cols: 
                    if c not in map_df.columns: map_df[c] = ""
                
                # CLIENT-SIDE RENDERING OPTIMIZATION
                # Instead of building Heavy XML locally, we send Raw Data arrays.
                # Data Schema: [Lat, Lon, Title, Company, City, Link, Img_Link]
                
                # Pre-process columns to avoid overhead - RENAMED TO AVOID SHADOWING
                titles_series = map_df['Job Title'].astype(str).str.replace("'", "", regex=False).fillna("Job")
                companies_series = map_df['Company'].astype(str).str.replace("'", "", regex=False).fillna("")
                cities_series = map_df['City'].astype(str).fillna("")
                in_cities_series = map_df['In_City'].astype(str).fillna("")
                links_series = map_df['Link'].astype(str).fillna("#")
                imgs_series = map_df['Image_link'].astype(str).fillna("")
                
                # Fast List Construction
                map_data = []
                # Use simple iteration for speed
                for lat, lon, t, c, city, incity, l, i in zip(
                    map_df['Latitude'], map_df['Longitude'], titles_series, companies_series, cities_series, in_cities_series, links_series, imgs_series
                ):
                     # Handle City Logic
                     c_str = city
                     if incity and incity.lower() not in ['nan', 'none', '']:
                         c_str = f"{city} - {incity}"
                     
                     # Append Raw Props
                     map_data.append([lat, lon, t, c, c_str, l, i])
                     
                # JS Callback to Render HTML on Client
                callback = """
                function (row) {
                    var marker = L.marker(new L.LatLng(row[0], row[1]));
                    
                    // Client-Side Template Construction
                    var title = row[2];
                    var company = row[3];
                    var city = row[4];
                    var link = row[5];
                    var img = row[6];
                    
                    var logo_html = "";
                    if (img && img.length > 10) {
                        logo_html = '<img src="' + img + '" style="height: 35px; width: auto; max-width: 80px; margin-right: 10px; object-fit: contain;">';
                    }
                    
                    var html = '<div style="font-family: \\'Segoe UI\\', sans-serif; min-width: 250px; font-size: 14px;">' +
                        '<div style="font-weight: bold; font-size: 16px; color: #111; margin-bottom: 5px;">' + title + '</div>' +
                        '<div style="display: flex; align-items: center; margin-bottom: 5px;">' +
                             logo_html +
                            '<div style="font-size: 14px; color: #555;">' + company + '</div>' +
                        '</div>' +
                        '<div style="font-size: 13px; color: #777; margin-bottom: 8px;">' + city + '</div>' +
                        '<a href="' + link + '" target="_blank" style="display: inline-block; text-decoration: none; color: white; background-color: #0066CC; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 13px;">' +
                           'Visit Job Link' +
                        '</a>' +
                    '</div>';
                    
                    marker.bindPopup(html); 
                    return marker;
                }
                """
                print(f"DEBUG: Folium map_data count = {len(map_data)}")
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
        elif run_map_logic:
            # Logic variables with defaults
            highlight_lat = None
            highlight_lon = None
            zoom_level = 6
            center_location = [26.8, 30.8]
            selected_row = None
            is_single_view = False
            row_idx_str = "0"

            # Table click handler using NEW RECORDS
            # Table click handler using NEW RECORDS (or Nav Button)
            is_nav_trigger = triggered_id == 'nav-action-store'
            is_table_trigger = triggered_id == 'jobs-table'
            
            # Use 'table_df' (calculated above) instead of 'current_table_records' (stale state)
            # This ensures we get the correct row even if page changed in this very callback
            if (is_table_trigger or is_nav_trigger) and active_cell:
                try:
                    row_idx = active_cell['row']
                    # We use table_df logic (it is already the slice for the NEW page)
                    if row_idx < len(table_df):
                        selected_row = table_df.iloc[row_idx]
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
                except Exception as e: print(f"Error in Selection Logic: {e}")



            # Map Markers Generation
            map_df = map_df_all.copy() # Use Globally filtered map_df
            markers = []

            if is_single_view and selected_row is not None:
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
                # ---------------------------------------------------------
                # RESTORED LOGIC: Full Data + Clustering (Plain Text Tooltips)
                # ---------------------------------------------------------
                
                geojson_data = None
                
                # 1. KPIs Calculation
                total_jobs = len(filtered_df)
                total_jobs_kpi = f"{total_jobs:,}"
                
                if not filtered_df.empty:
                    top_city = filtered_df['City'].mode()[0] if not filtered_df['City'].mode().empty else "N/A"
                    avg_jobs = int(len(filtered_df) / filtered_df['City'].nunique()) if filtered_df['City'].nunique() > 0 else 0
                    top_city_kpi = top_city
                    avg_jobs_kpi = f"{avg_jobs:,}"
                    
                    # Bar Chart Logic
                    city_counts = filtered_df['City'].value_counts().nlargest(10).reset_index()
                    city_counts.columns = ['City', 'Count']
                    # Sort Ascendingly so Largest is at the Top of the Chart (Plotly standard for hbar)
                    city_counts = city_counts.sort_values(by="Count", ascending=True)
                    
                    import plotly.express as px
                    fig = px.bar(city_counts, x='Count', y='City', orientation='h', title="Top Cities", template='plotly_white', text='Count')
                    fig.update_layout(
                        margin=dict(l=20, r=20, t=40, b=20), 
                        height=750,
                        yaxis={'categoryorder':'total ascending', 'title': None}, # Remove Y Axis Title
                        xaxis={'title': None} # Remove X Axis Title
                    )
                    fig.update_traces(textposition='outside') # Labels outside
                    apply_chart_styling(fig)
                else:
                    top_city_kpi = "N/A"
                    avg_jobs_kpi = "0"
                    fig = {}

                # 2. Map Data Generation
                if 'Latitude' in map_df.columns and 'Longitude' in map_df.columns:
                    features = []
                    
                    # Convert columns to lists for speed
                    # ... (keep existing setup) ...
                    titles = map_df['Job Title'].astype(str).str.replace("'", "", regex=False).fillna("Job").tolist()
                    companies = map_df['Company'].astype(str).str.replace("'","", regex=False).fillna("").tolist()
                    cities = map_df['City'].astype(str).fillna("").tolist()
                    in_cities = map_df['In_City'].astype(str).fillna("").tolist()
                    links = map_df['Link'].astype(str).fillna("#").tolist()
                    lats = map_df['Latitude'].tolist()
                    lons = map_df['Longitude'].tolist()

                    # Define row for single view if needed (Safe Check)
                    if is_single_view and selected_row is not None:
                        row = selected_row
                        # ... Logic will follow in next chunk or rely on existing loop if I don't change it ..
                        # Wait, I need to check where I am editing.
                        # The block below 'if is_single_view and selected_row:' is further down.
                        # I will edit that separately or include it here if contiguous.
                        # It is separated by the loop. I'll stick to Bar Chart here and do the Series fix in a separate chunk.
                        pass

                    
                    for lat, lon, title, comp, city, in_city, link in zip(lats, lons, titles, companies, cities, in_cities, links):
                        try:
                            lat_flt = float(lat)
                            lon_flt = float(lon)
                            if pd.isna(lat_flt) or pd.isna(lon_flt): continue
                            
                            # Format Location String
                            loc_str = str(city)
                            inc = str(in_city).lower()
                            if inc and inc not in ['nan', 'none', '']:
                                loc_str = f"{loc_str} | {str(in_city)}"
                            
                            # BEAAUTIFUL HTML TOOLTIP (Restored)
                            # Using CSS classes from assets/map_cluster.css for styling
                            tooltip_html = (
                                f'<div>'
                                f'<div class="job-tooltip-title">{title}</div>'
                                f'<div class="job-tooltip-comp">{comp}</div>'
                                f'<div class="job-tooltip-loc">{loc_str}</div>'
                                f'<div class="job-tooltip-link">Click to Visit</div>'
                                f'</div>'
                            )
                            
                            features.append({
                                "type": "Feature",
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": [lon_flt, lat_flt]
                                },
                                "properties": {
                                    "tooltip": tooltip_html, # Dash Leaflet renders HTML string automatically
                                    "link": link
                                }
                            })
                        except: continue

                    if features:
                        geojson_data = {
                            "type": "FeatureCollection",
                            "features": features
                        }

                # TILE LAYER SELECTION (Fixed URLs)
                # Ensure we use {z}/{x}/{y} format which is standard for Leaflet
                map_styles = {
                    'voyager': 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
                    'positron': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                    'dark': 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                    'satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    'osm': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
                }
                
                # If map_style is empty or invalid, default to Voyager (Clean)
                selected_url = map_styles.get(map_style, map_styles['voyager'])
                # Attribution
                if map_style == 'satellite': attr = 'Tiles &copy; Esri'
                elif map_style == 'osm': attr = '&copy; OpenStreetMap'
                else: attr = '&copy; CARTO'

                children = [
                    dl.TileLayer(url=selected_url, attribution=attr),
                    dl.GeoJSON(
                        data=geojson_data,
                        cluster=True,
                        zoomToBoundsOnClick=True,
                        id="city-geojson-layer"
                    )
                ]
                
                map_output = dl.Map(
                    center=center_location,
                    zoom=zoom_level,
                    children=children,
                    style={'width': '100%', 'height': '750px', 'borderRadius': '12px', 'boxShadow': '0 4px 12px rgba(0,0,0,0.1)'},
                    id='city-map-leaflet-component'
                )
                
                # Define other return variables
                tooltip_data = []
                page_count = 1 
                link_data = no_update
                full_map_href = "/full-map"
                popup_children = no_update
                popup_trigger = no_update
                total_jobs_count_for_store = len(filtered_df)
                
                return total_jobs_kpi, top_city_kpi, avg_jobs_kpi, fig, map_output, current_table_data, no_update, page_count, no_update, no_update, no_update, no_update, total_jobs_count_for_store

        # KPIs - FIXED: User wants KPI to show TOTAL jobs (7315) regardless of map count.
        total_jobs = len(filtered_df)
        total_jobs_count_for_store = total_jobs # Duplicate for store output
        
        
        # ... (Keep existing KPI logic) ...
        # Use filtered_df for City Stats? Or Map DF?
        # User said "number in map must equal KPI". 
        # So we should use map_df_all for consistency.
        
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

        city_counts = map_df_all['City'].value_counts()
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
        # TABLE LOGIC MOVED TO TOP. 
        # Here we just use the pre-calculated 'table_df' and 'total_pages'
        # ---------------------------------------------------------

        # Tooltip data generation - OPTIMIZED: DISABLED AS PER USER REQUEST
        tooltip_data = []
        
        # def clean_val(val): ... (Logic Disabled)
        '''
        def clean_val(val):
            s = str(val).strip()
            if not s or s.lower() in ['nan', 'n/a', 'none', 'nat', '']: return None
            return s
        '''
        
        def clean_val(val):
            s = str(val).strip()
            if not s or s.lower() in ['nan', 'n/a', 'none', 'nat', '']: return None
            return s

        # CRITICAL OPTIMIZATION: Tooltips only for visible slice (already sliced above)
        for idx, row in table_df.iterrows(): # table_df is already small (15 rows)

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
                'ago': clean_val(row.get('How Long Ago')),
                'link': row.get('Link', '#')
            }
            
            # Clean Skills for display
            skills_txt = vals['skills'].replace('\n', ', ') if vals['skills'] else "N/A"
            if len(skills_txt) > 200: skills_txt = skills_txt[:200] + "..."
            
            # Rich Markdown Layout
            md = f"""
## {vals['job'].split('](')[0].replace('[', '') if '[' in vals['job'] else vals['job']}
**{vals['comp']}**  
📍 {vals['city']} {f"- {vals['incity']}" if vals['incity'] else ""}

---
🔥 **Status:** {vals['status']}  
🕒 **Posted:** {vals['ago']}

💼 **Type:** {vals['emp']}  
🏠 **Mode:** {vals['wmode']}  
🎓 **Level:** {vals['level']}  
⏳ **Exp:** {vals['exp']} Yrs

**🛠 Skills:**  
{skills_txt}

[🔗 Visit Job Link on Wuzzuf]({vals['link']})
            """

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
            tooltip_delay=0,
            tooltip_duration=None,

            page_action='custom',
            page_current=current_page,
            page_size=page_size,
            page_count=total_pages,
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
                # FORCE RELOAD TRIGGERED
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
                    background-color: white !important; 
                    color: #333 !important; 
                    border: 1px solid #ccc !important; 
                    border-radius: 8px !important; 
                    padding: 20px !important; 
                    font-family: 'Segoe UI', sans-serif !important;
                    box-shadow: 0 12px 40px rgba(0,0,0,0.3) !important;
                    min-width: 450px !important;
                    max-width: 650px !important;
                    width: auto !important;
                    font-size: 15px !important;
                    line-height: 1.6 !important;
                    z-index: 2147483647 !important; /* Max Z-Index */
                    position: absolute !important; /* Force positioning */
                 '''},
                 # H2 Header Styling - Card Style (Blue Background, White Text)
                 {'selector': '.dash-table-tooltip h2', 'rule': '''
                    background-color: #0066CC !important; 
                    color: white !important; 
                    padding: 15px 20px !important; 
                    margin: -20px -20px 15px -20px !important; /* Negative margin to fill top */
                    border-radius: 8px 8px 0 0 !important;
                    font-size: 20px !important; 
                    font-weight: 700 !important;
                 '''},
                 # Link Button Styling (Blue button with white text)
                 {'selector': '.dash-table-tooltip a', 'rule': '''
                    color: white !important; 
                    background-color: #0066CC !important; 
                    padding: 10px 15px !important; 
                    text-decoration: none !important; 
                    border-radius: 6px !important; 
                    display: block !important; 
                    text-align: center !important; 
                    font-weight: 600 !important; 
                    margin-top: 15px !important; 
                    font-size: 14px !important;
                    width: 100% !important;
                    box-sizing: border-box !important;
                 '''},
                 {'selector': '.dash-table-tooltip a:hover', 'rule': 'background-color: #004C99 !important;'},
                 {'selector': 'td.cell--selected, td.focused', 'rule': 'background-color: transparent !important;'}
            ]
        )

        # [LOGIC INSERTION FOR POPUP]
        if triggered_id == 'jobs-table' and active_cell and active_cell['row'] < len(current_table_data):
            try:
                row = current_table_data[active_cell['row']]
                # Clean Job Title (Remove Markdown Link)
                raw_job = clean_val(row.get('Job Title'))
                if '[' in raw_job and '](' in raw_job:
                    try: raw_job = raw_job.split('](')[0].replace('[', '')
                    except: pass

                p_vals = {
                    'job': raw_job,
                    'comp': clean_val(row.get('Company')),
                    'city': clean_val(row.get('City')),
                    'incity': clean_val(row.get('In_City')),
                    'ago': clean_val(row.get('How Long Ago')),
                    'status': clean_val(row.get('job_status')),
                    'emp': clean_val(row.get('Employment Type')),
                    'wmode': clean_val(row.get('Work Mode')),
                    'level': clean_val(row.get('Career Level')),
                    'exp': clean_val(row.get('Year Of Exp_Avg')),
                    'skills': clean_val(row.get('Skills')),
                    'link': row.get('Link', '#'),
                    'logo': row.get('Image_link', '')
                }
                
                # Logo Logic - LARGER and RIGHT
                logo_html = html.Div()
                if p_vals['logo'] and len(str(p_vals['logo'])) > 10:
                    logo_html = html.Img(src=p_vals['logo'], style={'height': '80px', 'width': 'auto', 'maxWidth': '140px', 'objectFit': 'contain'})
                
                skills_clean = p_vals['skills'].replace('\n', ', ')
                if len(skills_clean) > 200: skills_clean = skills_clean[:200] + "..."
                
                # Construct Popup Content (White Card Style)
                popup_children = html.Div([
                    
                    # Close Button (Top Right Absolute)
                    html.Button('×', id='close-popup-btn', n_clicks=0, style={'position': 'absolute', 'top': '15px', 'right': '15px', 'background': 'transparent', 'border': 'none', 'color': '#999', 'fontSize': '28px', 'fontWeight': 'bold', 'cursor': 'pointer', 'zIndex': 10}),

                    html.Div([
                        
                        # Top Row: Title/Company (Left) vs Logo (Right)
                        html.Div([
                            # Left Column
                            html.Div([
                                html.H2(p_vals['job'], className='popup-job-title', style={'margin': '0 0 8px 0', 'fontSize': '20px', 'fontWeight': 'bold', 'color': '#000000', 'paddingRight': '10px'}),
                                html.Div(p_vals['comp'], style={'fontWeight': 'bold', 'color': '#333', 'fontSize': '16px', 'marginBottom': '4px'}),
                                html.Div(f"📍 {p_vals['city']}" + (f" - {p_vals['incity']}" if p_vals['incity'] else ""), style={'color': '#666', 'fontSize': '14px'}),
                            ], style={'flex': '1'}),
                            
                            # Right Column (Logo)
                            html.Div(logo_html, style={'marginLeft': '20px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
                        ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'start', 'justifyContent': 'space-between', 'marginBottom': '20px'}),

                        # Metadata Bar
                        html.Div([
                            html.Span(f"🔥 {p_vals['status']}", style={'marginRight': '20px', 'color': '#d32f2f', 'fontWeight': 'bold'}),
                            html.Span(f"🕒 Posted: {p_vals['ago']}", style={'color': '#444', 'fontWeight': '500'}) 
                        ], style={'marginBottom': '20px', 'fontSize': '13px', 'background': '#f5f5f5', 'padding': '10px 15px', 'borderRadius': '6px', 'display': 'flex', 'alignItems': 'center'}),
                        
                        # Details Grid
                        html.Div([
                            html.Div(f"💼 {p_vals['emp']}", style={'fontSize': '14px', 'fontWeight': '500', 'color': '#555'}),
                            html.Div(f"🏠 {p_vals['wmode']}", style={'fontSize': '14px', 'fontWeight': '500', 'color': '#555'}),
                            html.Div(f"🎓 {p_vals['level']}", style={'fontSize': '14px', 'fontWeight': '500', 'color': '#555'}),
                            html.Div(f"⏳ {p_vals['exp']} Yrs", style={'fontSize': '14px', 'fontWeight': '500', 'color': '#555'}),
                        ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '10px', 'background': '#fafafa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px', 'border': '1px solid #eee'}),
                        
                        # Skills
                        html.Div([
                            html.Div("🛠 Skills:", style={'fontWeight': 'bold', 'fontSize': '14px', 'marginBottom': '6px', 'color': '#222'}), 
                            html.Div(skills_clean, style={'fontSize': '14px', 'color': '#333', 'lineHeight': '1.5', 'fontWeight': '500'}) 
                        ], style={'marginBottom': '25px'}),
                        
                        # CTA Button
                        html.A("Visit Job Link on Wuzzuf", href=p_vals['link'], target="_blank", style={
                            'display': 'block', 'backgroundColor': '#0066CC', 'color': 'white', 'textAlign': 'center', 
                            'padding': '14px', 'borderRadius': '8px', 'textDecoration': 'none', 'fontWeight': 'bold', 'fontSize': '16px',
                            'boxShadow': '0 4px 10px rgba(0,102,204,0.2)', 'transition': 'transform 0.1s'
                        })
                    ], style={'padding': '30px', 'backgroundColor': 'white', 'borderRadius': '12px', 'boxShadow': '0 10px 30px rgba(0,0,0,0.1)', 'border': '1px solid #eee'})
                ], style={'padding': '0'})
                
                popup_style = {
                    'display': 'block', 'position': 'fixed', 'bottom': '30px', 'right': '30px', 
                    'width': '600px', 'zIndex': 999999, 'boxShadow': '0 10px 40px rgba(0,0,0,0.3)', 
                    'fontFamily': 'Segoe UI, sans-serif',
                    # FORCE REACT RE-RENDER to undo JS hide
                    '--force-update': str(uuid.uuid4())
                }
            except: pass
            
            # TRIGGER SHOW (ONLY If NOT Nav Trigger)
            if not is_nav_trigger:
                popup_trigger = str(time.time())
            else:
                popup_trigger = no_update

        # BRANCH C: Table Interaction (Row Click vs Pagination)
        # If trigger is Table but NOT Pagination, we return no_update for table data to avoid reset.
        # But if trigger IS Pagination (page_current), we MUST fall through to generate new data slice.
        if triggered_id == 'jobs-table' and (not ctx.triggered or 'page_current' not in ctx.triggered[0]['prop_id']):
            return (
                no_update, # Total Jobs
                no_update, # Top City
                no_update, # Avg Jobs
                no_update, # Bar Chart (Prevent reload!)
                map_output, # Map (Update zoom/markers or Iframe)
                no_update, # Table Data
                no_update, # Table Tooltips
                no_update, # Table Page Count
                link_data,  # Store: Update with link if single view
                no_update, # Full Map Link
                popup_children, # Click Popup
                popup_trigger, # Trigger Show
                no_update # Total Jobs Store
            )

        return (
            f"{total_jobs:,}",
            top_city,
            f"{avg_jobs:,}",
            city_bar_fig,
            map_output, # Use unified map_output
            table_df.to_dict('records'),
            tooltip_data,
            total_pages,
            link_data,
            full_map_href,
            popup_children, # Defaults
            popup_trigger,
            total_jobs_count_for_store # Return Total Count for Nav Logic
        )
    except Exception as e:
        import traceback
        print(f"Callback Error: {traceback.format_exc()}")
        return (
            "Error",
            f"Sys Error: {str(e)[:50]}",
            "Error",
            {},
            html.Div(f"System Error: {str(e)}", style={'color': 'red', 'padding': '20px', 'fontWeight': 'bold'}),
            [], # Data
            [], # Tooltips
            0, # Page Count
            None,
            "#",
            no_update,
            no_update,
            0 # Store
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


# NAV BUTTON LOGIC
@app.callback(
    [Output('jobs-table', 'page_current', allow_duplicate=True),
     Output('jobs-table', 'active_cell', allow_duplicate=True),
     Output('nav-action-store', 'data')],
    [Input('btn-next-job', 'n_clicks'), Input('btn-prev-job', 'n_clicks')],
    [State('jobs-table', 'page_current'), 
     State('jobs-table', 'page_size'),
     State('jobs-table', 'active_cell'), 
     State('total-jobs-count-store', 'data')],
    prevent_initial_call=True
)
def navigate_table(n_next, n_prev, current_page, page_size, active_cell, total_jobs):
    ctx = callback_context
    if not ctx.triggered: return no_update, no_update, no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Defaults
    if current_page is None: current_page = 0
    if page_size is None or page_size == 0: page_size = 15
    if total_jobs is None: total_jobs = 0
    
    # Calculate Current Global Index
    current_row_idx = 0
    if active_cell and 'row' in active_cell:
        current_row_idx = active_cell['row']
        
    global_index = (current_page * page_size) + current_row_idx
    
    # Determine Navigation Direction
    if button_id == 'btn-next-job':
        global_index += 1
    elif button_id == 'btn-prev-job':
        global_index -= 1
        
    # Bounds Check
    if global_index < 0: global_index = 0
    if global_index >= total_jobs: global_index = total_jobs - 1
    
    # Calculate New Page and Row
    new_page = global_index // page_size
    new_row_idx = global_index % page_size
    
    # Construct new active_cell
    new_active_cell = {
        'row': new_row_idx,
        'column': 0, 
        'column_id': 'Job Title'
    }
    
    # Signal Nav Action
    nav_data = {'ts': time.time(), 'action': 'nav'}
    
    return new_page, new_active_cell, nav_data

# ------------------------------------------------------------------
# NEW: Handle Next/Prev Button Logic
# ------------------------------------------------------------------
@app.callback(
    [Output('jobs-table', 'active_cell'),
     Output('jobs-table', 'page_current'),
     Output('nav-action-store', 'data', allow_duplicate=True)],
    [Input('btn-prev-job', 'n_clicks'),
     Input('btn-next-job', 'n_clicks')],
    [State('jobs-table', 'active_cell'),
     State('jobs-table', 'page_current'),
     State('jobs-table', 'page_size'),
     State('total-jobs-count-store', 'data')],
    prevent_initial_call=True
)
def handle_job_navigation(prev_clicks, next_clicks, active_cell, page_current, page_size, total_jobs):
    ctx = callback_context
    if not ctx.triggered: return no_update, no_update, no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Defaults
    if page_current is None: page_current = 0
    if page_size is None or page_size == 0: page_size = 15
    if total_jobs is None: total_jobs = 0
    
    current_row = active_cell['row'] if active_cell else 0
    # Global Index = (page * size) + row
    global_idx = (page_current * page_size) + current_row
    
    new_global_idx = global_idx
    
    if button_id == 'btn-next-job':
        new_global_idx += 1
        if new_global_idx >= total_jobs: new_global_idx = 0 # Loop to start
    elif button_id == 'btn-prev-job':
        new_global_idx -= 1
        if new_global_idx < 0: new_global_idx = max(0, total_jobs - 1)
        
    # Convert back to Page/Row
    new_page = new_global_idx // page_size
    new_row = new_global_idx % page_size
    
    new_active_cell = {'row': new_row, 'column': 0, 'column_id': 'Job Title'}
    timestamp = int(time.time() * 1000)
    
    return new_active_cell, new_page, {'ts': timestamp, 'action': 'nav'}
