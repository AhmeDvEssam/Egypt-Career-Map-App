from dash import Input, Output, State, dash_table
import plotly.express as px
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from app_instance import app
from data_loader import df
from utils import get_color_scale, apply_visual_highlighting, apply_chart_styling

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
     Input('theme-store', 'data')]
)
def update_city_map(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, map_style, search_text, theme):
    filtered_df = df.copy()
    
    # Calculate KPIs first
    total_jobs_city = len(filtered_df)
    top_city = filtered_df['City'].value_counts().index[0] if 'City' in filtered_df.columns and not filtered_df.empty else "N/A"
    avg_jobs_per_city = round(filtered_df.groupby('City').size().mean(), 1) if 'City' in filtered_df.columns and not filtered_df.empty else 0
    
    # Apply filters
    if companies:
        filtered_df = filtered_df[filtered_df['Company'].isin(companies)]
    if cities:
        filtered_df = filtered_df[filtered_df['City'].isin(cities)]
    if categories:
        filtered_df = filtered_df[filtered_df['Category'].isin(categories)]
    if work_modes:
        filtered_df = filtered_df[filtered_df['Work Mode'].isin(work_modes)]
    if employment_types:
        filtered_df = filtered_df[filtered_df['Employment Type'].isin(employment_types)]
    if career_levels:
        filtered_df = filtered_df[filtered_df['Career Level'].isin(career_levels)]
    if education_levels:
        filtered_df = filtered_df[filtered_df['education_level'].isin(education_levels)]
    if start_date and end_date and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[(filtered_df['posted'] >= start_date) & (filtered_df['posted'] <= end_date)]

    # In-City filter
    if in_cities and 'In_City' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
    
    # Avg Years of Experience filter
    if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
        min_exp, max_exp = avg_exp_range[0], avg_exp_range[1]
        filtered_df = filtered_df[(filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)]
    
    # Month filter
    if months and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]

    # Apply search text filter
    if search_text and search_text.strip():
        from utils import filter_dataframe_by_search
        filtered_df = filter_dataframe_by_search(filtered_df, search_text)
    
    # City bar chart
    col = 'City'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    city_counts = s.value_counts().reset_index()
    city_counts.columns = [col, 'count']
    city_counts = city_counts.sort_values('count', ascending=True)

    deep_blue_scale = get_color_scale(theme)

    city_bar_fig = px.bar(city_counts, x='count', y=col, title='Jobs by City', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    apply_visual_highlighting(city_bar_fig, city_counts[col].tolist(), cities, is_pie=False)
    
    # Dynamic height
    dynamic_height = max(500, len(city_counts) * 60)
    city_bar_fig.update_layout(height=dynamic_height)
    apply_chart_styling(city_bar_fig, is_horizontal_bar=True)
    
    # --- Generate Folium Map ---
    center_location = [26.8, 30.8]
    zoom_level = 6
    
    if cities and len(cities) > 0:
        city_data = filtered_df[filtered_df['City'] == cities[0]]
        if not city_data.empty and 'Latitude' in city_data.columns and 'Longitude' in city_data.columns:
            city_coords_df = city_data[['Latitude', 'Longitude']].dropna()
            if not city_coords_df.empty:
                city_coords = city_coords_df.iloc[0]
                center_location = [city_coords['Latitude'], city_coords['Longitude']]
                zoom_level = 11
    
    # Determine map tiles
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
        scrollWheelZoom=True,
        max_bounds=True,
        min_zoom=5,
        max_zoom=15
    )
    
    m.fit_bounds([[22, 25], [32, 37]])
    
    map_df = filtered_df.copy()
    if 'Latitude' in map_df.columns and 'Longitude' in map_df.columns and 'City' in map_df.columns:
        map_df = map_df[
            map_df['Latitude'].notna() & 
            map_df['Longitude'].notna() &
            (map_df['Latitude'] >= 22) & 
            (map_df['Latitude'] <= 32) &
            (map_df['Longitude'] >= 25) & 
            (map_df['Longitude'] <= 37)
        ]
        
        if not map_df.empty:
            map_data = []
            for _, row in map_df.iterrows():
                job_title = str(row['Job Title']).replace("'", "")
                company = str(row['Company']).replace("'", "")
                city = str(row['City'])
                in_city = str(row['In_City']) if pd.notna(row['In_City']) else ""
                job_link = str(row['Link']) if pd.notna(row['Link']) else "#"
                
                tooltip_html = f"""
                <div style="font-family: 'Inter', Arial, sans-serif; min-width: 200px; padding: 10px; border-radius: 12px;">
                    <div style="font-size: 16px; font-weight: 900; color: black; margin-bottom: 4px; line-height: 1.2;">{job_title}</div>
                    <div style="font-size: 15px; color: #333; font-weight: bold; margin-bottom: 2px;">{company}</div>
                    <div style="font-size: 14px; color: #0066CC; margin-bottom: 8px;">{city} {f'- {in_city}' if in_city else ''}</div>
                    <div style="font-size: 12px; color: #0066CC; font-weight: 800; border-top: 1px solid #eee; padding-top: 5px;">Click To Visit Wuzzuf.com ↗</div>
                </div>
                """
                map_data.append([row['Latitude'], row['Longitude'], job_link, tooltip_html])
            
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
            FastMarkerCluster(data=map_data, callback=callback, name='Jobs').add_to(m)
            
    map_html = m.get_root().render()
    
    # Table
    candidate_cols = ['Job Title', 'Company', 'City', 'Category', 'applicants', 'Work Mode', 'Link']
    present_cols = [c for c in candidate_cols if c in filtered_df.columns]
    table_data_df = filtered_df[present_cols].copy()
    
    if 'Link' in table_data_df.columns and 'Job Title' in table_data_df.columns:
        table_data_df['Job Title'] = table_data_df.apply(
            lambda x: f"[{x['Job Title']}]({x['Link']})" if x['Link'] and x['Link'] != '#' else x['Job Title'], 
            axis=1
        )
    
    tooltip_data = []
    for row in table_data_df.to_dict('records'):
        row_tooltip = {}
        tooltip_content = f"""### {row.get('Job Title', 'N/A')}

**{row.get('Company', 'N/A')}**  
{row.get('City', 'N/A')} • {row.get('Category', 'N/A')}

_Click to visit Wuzzuf.com_"""
        for col in table_data_df.columns:
            row_tooltip[col] = {'value': tooltip_content, 'type': 'markdown'}
        tooltip_data.append(row_tooltip)

    table = dash_table.DataTable(
        id='jobs-table',
        data=table_data_df.to_dict('records'),
        columns=[
            {'name': i, 'id': i, 'presentation': 'markdown'} if i == 'Job Title' else {'name': i, 'id': i} 
            for i in table_data_df.columns if i != 'Link'
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'fontFamily': 'Inter',
            'backgroundColor': 'rgba(255, 255, 255, 0.05)' if theme == 'dark' else 'white',
            'color': 'white' if theme == 'dark' else '#001F3F',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        style_header={
            'backgroundColor': '#001F3F',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {'if': {'state': 'active'}, 'backgroundColor': 'rgba(0, 102, 204, 0.1)', 'border': '1px solid #0066CC'},
            {'if': {'state': 'selected'}, 'backgroundColor': 'rgba(0, 102, 204, 0.1)', 'border': '1px solid #0066CC'}
        ],
        css=[{'selector': '.dash-spreadsheet td:hover', 'rule': 'color: #0066CC !important; font-weight: bold; cursor: pointer;'}],
        tooltip_data=tooltip_data,
        tooltip_duration=None,
        page_action='native',
        page_size=10,
        sort_action='native',
        filter_action='native'
    )
    
    return f"{total_jobs_city:,}", top_city, f"{avg_jobs_per_city:.1f}", city_bar_fig, map_html, table
