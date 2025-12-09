from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from data_loader import df
from datetime import datetime
import pandas as pd

def city_map_layout():
    # safe option lists
    companies = df['Company'].dropna().unique().tolist() if 'Company' in df.columns else []
    categories = df['Category'].dropna().unique().tolist() if 'Category' in df.columns else []
    # compute posted range if present (coerce to datetime to avoid mixed-type issues)
    posted_series = pd.to_datetime(df['posted'], errors='coerce') if 'posted' in df.columns else pd.Series(dtype='datetime64[ns]')
    has_posted = posted_series.notna().any()
    if has_posted:
        min_dt = posted_series.min()
        max_dt = posted_series.max()
        # ensure we have Timestamp objects
        try:
            min_ts = int(pd.Timestamp(min_dt).timestamp())
            max_ts = int(pd.Timestamp(max_dt).timestamp())
        except Exception:
            # fallback to now if weird values
            min_ts = int(datetime.now().timestamp()) - 7 * 24 * 3600
            max_ts = int(datetime.now().timestamp())
        val = [min_ts, max_ts]
        marks = {min_ts: pd.Timestamp(min_dt).strftime('%Y-%m-%d'), max_ts: pd.Timestamp(max_dt).strftime('%Y-%m-%d')}
    else:
        # fallback to relative simple slider until posted becomes available
        now_ts = int(datetime.now().timestamp())
        min_ts = now_ts - 7 * 24 * 3600
        max_ts = now_ts
        val = [min_ts, max_ts]
        marks = {min_ts: 'Start', max_ts: 'End'}

    return html.Div([
        html.H1('City Map', className='gradient-text', style={'textAlign': 'center', 'marginBottom': 20}),
        
        # KPIs Row - Professional Design
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-map-location-dot')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Total Jobs", className='kpi-label-v2'),
                    html.Div(id='city-total-jobs-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-city')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Top City", className='kpi-label-v2'),
                    html.Div(id='city-top-city-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-calculator')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Avg Jobs/City", className='kpi-label-v2'),
                    html.Div(id='city-avg-jobs-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
        ], style={'marginBottom': 30}),
        
        # Map Controls Row
        html.Div([
            # Map Style Dropdown
            html.Div([
                html.Label("Select Map Style:", style={'color': '#001F3F', 'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='map-style-dropdown',
                    options=[
                        {'label': 'Light Theme (Voyager)', 'value': 'voyager'},
                        {'label': 'Dark Theme (Dark Matter)', 'value': 'dark'},
                        {'label': 'Satellite (Esri)', 'value': 'satellite'},
                        {'label': 'Light Grey (Positron)', 'value': 'positron'},
                        {'label': 'OpenStreetMap', 'value': 'osm'}
                    ],
                    value='satellite',
                    clearable=False,
                    style={'width': '220px', 'color': 'black'}
                )
            ], style={'marginRight': '10px'}),

            # Switch Map Mode Button
            dbc.Button(
                [html.I(className="fa-solid fa-layer-group", style={'marginRight':'8px'}), "Switch to Interactive Map"],
                id="switch-map-btn",
                color="secondary",
                style={'fontWeight':'bold', 'boxShadow':'0 2px 5px rgba(0,0,0,0.2)', 'marginRight': '10px'}
            ),

            # Full Map Button (Styled to Match)
            dbc.Button(
                [html.I(className="fa-solid fa-expand", style={'marginRight':'8px'}), "Open Full Screen Map"],
                id="full-map-btn-link", # different ID to avoid callback issues if any, or wrap in A tag?
                href="/full-map",
                target="_blank",
                external_link=True, # Important for DBC Button as Link
                color="primary",
                style={'fontWeight':'bold', 'boxShadow':'0 2px 5px rgba(0,0,0,0.2)'}
            ),
            
        ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'marginBottom': '15px', 'flexWrap': 'wrap', 'gap': '10px'}),


        dbc.Row([
            dbc.Col(html.Div(dcc.Loading(dcc.Graph(id='city-bar-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]})), style={'height': '750px', 'overflowY': 'auto'}), width=5),
            dbc.Col(html.Div(id='city-map-leaflet'), width=7), 
        ], style={'marginBottom': 20}),

        # STORES
        dcc.Store(id='map-zoom-store', data={'zoom': 5, 'center': {'lat': 26.8, 'lon': 30.8}}),
        dcc.Store(id='selected-job-link-store', data=None),
        dcc.Store(id='map-mode-store', data='leaflet'), # Default to Fast mode

        html.H4('Jobs (sample)'),
        html.Div(id='job-table-container', children=[
            # Initial Empty Table to prevent "Nonexistent object" callback error
            dash_table.DataTable(id='jobs-table', data=[], columns=[], page_action='native', page_size=15)
        ])
    ], style={'margin': 20})
