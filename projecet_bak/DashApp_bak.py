import dash
from dash import dcc, html, Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import re
import requests
import time
import json
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Cache buster for forcing browser refresh
CACHE_VERSION = int(time.time())

# Create Dash app instance (allow callbacks for components added dynamically)
# Custom CSS will be automatically loaded from assets/custom.css
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Generate dummy data based on your actual columns
def load_real_data():
    """Load job data from Excel and normalize columns.

    This function:
    - reads the xlsx file at the configured path
    - parses the `posted` column with tolerant logic (absolute parse, coercion, and relative strings like '2 months')
    - extracts `City` from `Location` if needed
    - detects common latitude/longitude column name variants and, if missing, attempts a best-effort cached geocode
    """
    # path to your file; use relative path for portability
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, 'Jobs.xlsx')
    if not os.path.exists(path):
        # Fallback for development if file is not found
        print(f"Warning: File not found at {path}")
    
    df = pd.read_excel(path)
    
    # Rename columns to match expected names in the code
    # Actual columns: "Jobs Title", "Date_Posted", "How Long Ago"
    # Code expects: "Job Title", "posted"
    column_mapping = {
        'Jobs Title': 'Job Title',
        'Date_Posted': 'posted',
    }
    df.rename(columns=column_mapping, inplace=True)

    # posted parsing: try strict, then coerce, then relative parsing
    if 'posted' in df.columns:
        orig_posted = df['posted'].astype(str)
        try:
            df['posted'] = pd.to_datetime(orig_posted, errors='raise')
        except Exception:
            parsed = pd.to_datetime(orig_posted, errors='coerce')
            rel_mask = parsed.isna() & orig_posted.notna()

            def _parse_relative(s: str):
                if not isinstance(s, str) or not s.strip():
                    return pd.NaT
                m = re.search(r"(\d+)\s*(day|days|week|weeks|month|months|year|years)", s, flags=re.IGNORECASE)
                if not m:
                    return pd.NaT
                n = int(m.group(1))
                unit = m.group(2).lower()
                if 'day' in unit:
                    days = n
                elif 'week' in unit:
                    days = n * 7
                elif 'month' in unit:
                    days = n * 30
                else:
                    days = n * 365
                return datetime.now() - timedelta(days=days)

            if rel_mask.any():
                parsed_rel = orig_posted[rel_mask].apply(_parse_relative)
                parsed.loc[rel_mask] = parsed_rel

            df['posted'] = parsed

    # extract City from Location when possible
    if 'Location' in df.columns:
        # Location format: "Cairo, Egypt" or "Sheikh Zayed, Giza, Egypt"
        # Extract the first part (city name) as the city
        df['City'] = df['Location'].str.split(',').str[0].str.strip()
    elif 'City' not in df.columns and 'location2' in df.columns:
        # fallback to location2 column if present
        df['City'] = df['location2'].str.split(',').str[0].str.strip()

    # Helper: detect latitude/longitude column name variants
    def _detect_latlon(df_local: pd.DataFrame):
        lat_aliases = ['latitude', 'lat', 'Latitude', 'LAT', 'Lat']
        lon_aliases = ['longitude', 'lon', 'lng', 'Longitude', 'LON', 'Lng']
        lat_col = next((c for c in df_local.columns if c in lat_aliases or c.lower() in [a.lower() for a in lat_aliases]), None)
        lon_col = next((c for c in df_local.columns if c in lon_aliases or c.lower() in [a.lower() for a in lon_aliases]), None)
        return lat_col, lon_col

    # Simple JSON cache helpers for geocoding
    cache_path = os.path.join(os.path.dirname(__file__), 'geocode_cache.json')

    def _load_cache(path):
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    return json.load(fh)
            except Exception:
                return {}
        return {}

    def _save_cache(path, cache):
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(cache, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _geocode_city(name: str, cache: dict, cache_path_local: str, pause: float = 1.0):
        if not isinstance(name, str) or not name.strip():
            return None
        key = name.strip()
        if key in cache:
            return cache[key]
        try:
            params = {'q': name, 'format': 'json', 'limit': 1}
            headers = {'User-Agent': 'JobsDashboard/1.0 (contact@example.com)'}
            resp = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    lat = float(data[0].get('lat'))
                    lon = float(data[0].get('lon'))
                    cache[key] = {'lat': lat, 'lon': lon}
                    _save_cache(cache_path_local, cache)
                    time.sleep(pause)
                    return cache[key]
        except Exception:
            pass
        return None

    lat_col, lon_col = _detect_latlon(df)

    # If no lat/lon present, use cached geocoding results (no network calls by default)
    if (not lat_col or not lon_col) and 'City' in df.columns:
        cache = _load_cache(cache_path)
        # Only geocode missing cities if AUTO_GEOCODE=1 (network calls are slow/unreliable)
        do_geocode = os.environ.get('AUTO_GEOCODE', '').lower() in ('1', 'true', 'yes')
        if do_geocode:
            cities = df['City'].dropna().unique().tolist()
            for city in cities:
                if city in cache:
                    continue
                try:
                    _geocode_city(city, cache, cache_path)
                except Exception:
                    pass
            # reload cache after any geocoding attempts
            cache = _load_cache(cache_path)

        # if we have any coords in cache, map them back into df
        if cache:
            lat_vals = []
            lon_vals = []
            for city in df['City'].tolist():
                if city and city in cache:
                    lat_vals.append(cache[city]['lat'])
                    lon_vals.append(cache[city]['lon'])
                else:
                    lat_vals.append(None)
                    lon_vals.append(None)
            df['Latitude'] = lat_vals
            df['Longitude'] = lon_vals
            lat_col, lon_col = 'Latitude', 'Longitude'

    return df

# Load dataframe once so layout/callbacks can reference it
try:
    df = load_real_data()
except Exception as e:
    print(f"⚠ Could not load data in load_real_data(): {e}")
    df = pd.DataFrame()

# Page 3: Deep Analysis
def deep_analysis_layout():
    # safe option lists
    categories = df['Category'].dropna().unique().tolist() if 'Category' in df.columns else []
    companies = df['Company'].dropna().unique().tolist() if 'Company' in df.columns else []
    career_levels = df['Career Level'].dropna().unique().tolist() if 'Career Level' in df.columns else []
    education_levels = df['education_level'].dropna().unique().tolist() if 'education_level' in df.columns else []

    return html.Div([
        html.H1("Deep Analysis", className='gradient-text', style={'textAlign': 'center', 'marginBottom': 30}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='top-companies-chart'), width=6),
            dbc.Col(dcc.Graph(id='education-level-chart'), width=6),
        ], style={'marginBottom': 20}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='skills-cloud'), width=6),
            dbc.Col(dcc.Graph(id='experience-chart'), width=6),
        ], style={'marginBottom': 20}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='applicants-chart'), width=12),
        ])
    ])


# --- placeholder layouts (if full layouts live elsewhere) ---
def overview_layout():
    # Build safe option lists from df
    companies = df['Company'].dropna().unique().tolist() if 'Company' in df.columns else []
    cities = df['City'].dropna().unique().tolist() if 'City' in df.columns else []
    categories = df['Category'].dropna().unique().tolist() if 'Category' in df.columns else []
    work_modes = df['Work Mode'].dropna().unique().tolist() if 'Work Mode' in df.columns else []
    employment_types = df['Employment Type'].dropna().unique().tolist() if 'Employment Type' in df.columns else []
    education_levels = df['education_level'].dropna().unique().tolist() if 'education_level' in df.columns else []

    return html.Div([
        html.H1('Overview', className='gradient-text', style={'textAlign': 'center', 'marginBottom': 20}),

        # KPIs
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H6('Total Jobs'), html.H3(id='total-jobs-kpi', className='pulse')]), className='glass-effect'), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6('Total Companies'), html.H3(id='total-companies-kpi', className='pulse')]), className='glass-effect'), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6('Total Cities'), html.H3(id='total-cities-kpi', className='pulse')]), className='glass-effect'), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H6('Avg Applicants'), html.H3(id='avg-applicants-kpi', className='pulse')]), className='glass-effect'), width=3),
        ], style={'marginBottom': 30}),

        # Charts
        dbc.Row([
            dbc.Col(dcc.Graph(id='employment-type-chart'), width=6),
            dbc.Col(dcc.Graph(id='work-mode-chart'), width=6),
        ], style={'marginBottom': 20}),

        dbc.Row([
            dbc.Col(dcc.Graph(id='career-level-chart'), width=6),
            dbc.Col(dcc.Graph(id='top-categories-chart'), width=6),
        ])
    ], style={'margin': 20})


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
        
        html.Div(
            html.P('💡 Double-click on any circle to zoom in; double-click the map background to zoom out.', 
                   style={'fontSize': 14, 'color': '#666', 'fontStyle': 'italic', 'textAlign': 'center', 'marginBottom': 15}),
        ),

        dbc.Row([
            dbc.Col(dcc.Loading(dcc.Graph(id='city-bar-chart')), width=6),
            dbc.Col(dcc.Loading(dcc.Graph(id='city-map', config={
                'displayModeBar': True, 
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
                'responsive': True,
                'toImageButtonOptions': {'format': 'png'}
            })), width=6),
        ], style={'marginBottom': 20}),

        # Store for managing zoom state on double-click
        dcc.Store(id='map-zoom-store', data={'zoom': 5, 'center': {'lat': 26.8, 'lon': 30.8}}),

        html.H4('Jobs (sample)'),
        html.Div(id='job-table-container')
    ], style={'margin': 20})

# Page 4: Time Analysis
def time_analysis_layout():
    # safe option lists and posted range
    companies = df['Company'].dropna().unique().tolist() if 'Company' in df.columns else []
    categories = df['Category'].dropna().unique().tolist() if 'Category' in df.columns else []
    posted_series = pd.to_datetime(df['posted'], errors='coerce') if 'posted' in df.columns else pd.Series(dtype='datetime64[ns]')
    has_posted = posted_series.notna().any()

    return html.Div([
        html.H1("Time Analysis", className='gradient-text', style={'textAlign': 'center', 'marginBottom': 30}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='month-day-line-chart'), width=6),
            dbc.Col(dcc.Graph(id='month-bar-chart'), width=6),
        ], style={'marginBottom': 20}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='applicants-trend-chart'), width=12),
        ])
    ])


# --- set a top-level layout so Dash has something at startup ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    
    # Navbar with Logo
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Overview", href="/")),
            dbc.NavItem(dbc.NavLink("City Map", href="/city-map")),
            dbc.NavItem(dbc.NavLink("Deep Analysis", href="/deep-analysis")),
            dbc.NavItem(dbc.NavLink("Time Analysis", href="/time-analysis")),
        ],
        brand=html.Div([
            html.Img(src='/assets/logo.png', style={'height': '50px', 'marginRight': '15px'}),
            html.Span("Hire Q Services - Jobs Dashboard", style={'verticalAlign': 'middle', 'fontSize': '1.7rem', 'fontWeight': '700'})
        ]),
        color="primary",
        dark=True,
        sticky='top'
    ),
    
    # Sidebar Tab (visible on left edge)
    html.Div([
        html.Span("FILTERS", style={'writingMode': 'vertical-rl', 'color': 'white', 'fontWeight': '700', 'fontSize': '1.1rem', 'letterSpacing': '2px'})
    ], id='sidebar-tab'),
    
    # Backdrop
    html.Div(id='sidebar-backdrop', className=''),
    
    # Left Filter Sidebar (hover to reveal)
    html.Div([
        html.H4("🔍 Filters"),
        
        # Company Filter
        html.Div([
            html.Label("Company"),
            dcc.Dropdown(
                id='sidebar-company-filter',
                options=[{'label': c, 'value': c} for c in df['Company'].dropna().unique().tolist()] if 'Company' in df.columns else [],
                multi=True,
                placeholder='Select Companies'
            )
        ], className='filter-group'),
        
        # Date Posted Filter
        html.Div([
            html.Label("Date Posted"),
            dcc.DatePickerRange(
                id='sidebar-date-filter',
                start_date=df['posted'].min() if 'posted' in df.columns and df['posted'].notna().any() else None,
                end_date=df['posted'].max() if 'posted' in df.columns and df['posted'].notna().any() else None,
                display_format='YYYY-MM-DD'
            )
        ], className='filter-group'),
        
        # Years of Experience Filter
        html.Div([
            html.Label("Years of Experience"),
            dcc.RangeSlider(
                id='sidebar-exp-filter',
                min=0,
                max=20,
                step=1,
                marks={i: str(i) for i in range(0, 21, 5)},
                value=[0, 20],
                tooltip={"placement": "bottom", "always_visible": True}
            )
        ], className='filter-group'),
        
        # City Filter
        html.Div([
            html.Label("City"),
            dcc.Dropdown(
                id='sidebar-city-filter',
                options=[{'label': c, 'value': c} for c in df['City'].dropna().unique().tolist()] if 'City' in df.columns else [],
                multi=True,
                placeholder='Select Cities'
            )
        ], className='filter-group'),
        
        # Work Mode Filter
        html.Div([
            html.Label("Work Mode"),
            dcc.Dropdown(
                id='sidebar-work-mode-filter',
                options=[{'label': w, 'value': w} for w in df['Work Mode'].dropna().unique().tolist()] if 'Work Mode' in df.columns else [],
                multi=True,
                placeholder='Select Work Mode'
            )
        ], className='filter-group'),
        
        # Career Level Filter
        html.Div([
            html.Label("Career Level"),
            dcc.Dropdown(
                id='sidebar-career-level-filter',
                options=[{'label': c, 'value': c} for c in df['Career Level'].dropna().unique().tolist()] if 'Career Level' in df.columns else [],
                multi=True,
                placeholder='Select Career Level'
            )
        ], className='filter-group'),
        
        # Category Filter
        html.Div([
            html.Label("Category"),
            dcc.Dropdown(
                id='sidebar-category-filter',
                options=[{'label': c, 'value': c} for c in df['Category'].dropna().unique().tolist()] if 'Category' in df.columns else [],
                multi=True,
                placeholder='Select Categories'
            )
        ], className='filter-group'),

        # Education Filter
        html.Div([
            html.Label("Education"),
            dcc.Dropdown(
                id='sidebar-education-filter',
                options=[{'label': e, 'value': e} for e in df['education_level'].dropna().unique().tolist()] if 'education_level' in df.columns else [],
                multi=True,
                placeholder='Select Education'
            )
        ], className='filter-group'),

        # Employment Type Filter
        html.Div([
            html.Label("Employment Type"),
            dcc.Dropdown(
                id='sidebar-employment-type-filter',
                options=[{'label': e, 'value': e} for e in df['Employment Type'].dropna().unique().tolist()] if 'Employment Type' in df.columns else [],
                multi=True,
                placeholder='Select Employment Type'
            )
        ], className='filter-group'),
        
    ], id='filter-sidebar', className=''),
    
    
    # Global Search Bar - TEXT INPUT (not dropdown!)
    html.Div([
        dcc.Input(
            id='global-search-bar',
            type='text',
            placeholder='🔍 Search anything - Company, City, Category, Job Title, etc...',
            debounce=True,
            style={'width': '100%'}
        )
    ], id='global-search-container'),
    
    # Page Content
    html.Div(id='page-content', style={'margin': '20px'})
])

# Callbacks for routing
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    # normalize pathname: handle None and trailing slashes
    if not pathname:
        pathname = '/'
    path = pathname.rstrip('/') or '/'

    if path == "/":
        return overview_layout()
    elif path == "/city-map":
        return city_map_layout()
    elif path == "/deep-analysis":
        return deep_analysis_layout()
    elif path == "/time-analysis":
        return time_analysis_layout()
    return html.Div(["404 - Page not found"])

# Callbacks for Overview page
@app.callback(
    [Output('total-jobs-kpi', 'children'),
     Output('total-companies-kpi', 'children'),
     Output('total-cities-kpi', 'children'),
     Output('avg-applicants-kpi', 'children'),
     Output('employment-type-chart', 'figure'),
     Output('work-mode-chart', 'figure'),
     Output('career-level-chart', 'figure'),
     Output('top-categories-chart', 'figure')],
    [Input('sidebar-company-filter', 'value'),
     Input('sidebar-city-filter', 'value'),
     Input('sidebar-category-filter', 'value'),
     Input('sidebar-work-mode-filter', 'value'),
     Input('sidebar-employment-type-filter', 'value'),
     Input('sidebar-career-level-filter', 'value'),
     Input('sidebar-education-filter', 'value'),
     Input('sidebar-date-filter', 'start_date'),
     Input('sidebar-date-filter', 'end_date'),
     Input('global-search-bar', 'value')]
)
def update_overview(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, search_text):
    filtered_df = df.copy()
    
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
    
    # Apply search text filter
    if search_text and search_text.strip():
        search_term = search_text.strip().lower()
        search_cols = ['Company', 'City', 'Category', 'Job Title', 'Work Mode', 'Employment Type', 'Career Level']
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for col in search_cols:
            if col in filtered_df.columns:
                mask |= filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False)
        filtered_df = filtered_df[mask]
    
    # KPIs
    total_jobs = len(filtered_df)
    total_companies = int(filtered_df['Company'].nunique()) if 'Company' in filtered_df.columns else 0
    total_cities = int(filtered_df['City'].nunique()) if 'City' in filtered_df.columns else 0
    avg_applicants = round(filtered_df['applicants'].mean(), 1) if 'applicants' in filtered_df.columns and not filtered_df['applicants'].dropna().empty else 0
    
    # Charts
    # Employment Type chart (safe)
    col = 'Employment Type'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    employment_type_fig = px.bar(vc, x='count', y=col, title='Jobs by Employment Type', orientation='h')
    
    col = 'Work Mode'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    work_mode_fig = px.bar(vc, x='count', y=col, title='Jobs by Work Mode', orientation='h')
    
    col = 'Career Level'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    career_level_fig = px.bar(vc, x='count', y=col, title='Jobs by Career Level', orientation='h')
    
    col = 'Category'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().head(10).reset_index()
    vc.columns = [col, 'count']
    top_categories_fig = px.bar(vc, x='count', y=col, title='Top 10 Categories', orientation='h')
    
    # Style all figures with dark theme and custom colors
    for fig in [employment_type_fig, work_mode_fig, career_level_fig, top_categories_fig]:
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff', family='Inter'),
            title_font=dict(size=18, color='#0066CC'),
            hoverlabel=dict(
                bgcolor='rgba(26, 26, 62, 0.95)',
                font_size=13,
                font_family='Inter'
            )
        )
        fig.update_traces(
            marker=dict(
                line=dict(width=0),
                colorscale='Plasma'
            ),
            hovertemplate='<b>%{y}</b><br>Count: %{x}<extra></extra>'
        )
    
    return total_jobs, total_companies, total_cities, avg_applicants, employment_type_fig, work_mode_fig, career_level_fig, top_categories_fig

# Callbacks for City Map page
@app.callback(
    [Output('city-bar-chart', 'figure'),
     Output('city-map', 'figure'),
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
     Input('global-search-bar', 'value')],
    [dash.State('city-map', 'relayoutData')]
)
def update_city_map(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, search_text, relayout_data):
    filtered_df = df.copy()
    
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

    
    # Apply search text filter
    if search_text and search_text.strip():
        search_term = search_text.strip().lower()
        search_cols = ['Company', 'City', 'Category', 'Job Title', 'Work Mode', 'Employment Type', 'Career Level']
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for col in search_cols:
            if col in filtered_df.columns:
                mask |= filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False)
        filtered_df = filtered_df[mask]
    
    # City bar chart
    col = 'City'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    city_counts = s.value_counts().reset_index()
    city_counts.columns = [col, 'count']
    city_bar_fig = px.bar(city_counts, x='count', y=col, title='Jobs by City', orientation='h')
    city_bar_fig.update_layout(template='plotly_white')
    
    # Map
    # group city jobs safely, ensure Latitude/Longitude exist
    if 'City' in filtered_df.columns:
        agg_cols = {}
        if 'Latitude' in filtered_df.columns:
            agg_cols['Latitude'] = 'first'
        if 'Longitude' in filtered_df.columns:
            agg_cols['Longitude'] = 'first'
        agg_cols['Job Title'] = 'count' if 'Job Title' in filtered_df.columns else ('Company' if 'Company' in filtered_df.columns else lambda x: len(x))
        try:
            city_jobs = filtered_df.groupby('City').agg(agg_cols).reset_index()
        except Exception:
            city_jobs = pd.DataFrame(columns=['City', 'Latitude', 'Longitude', 'Job Title'])
    else:
        city_jobs = pd.DataFrame(columns=['City', 'Latitude', 'Longitude', 'Job Title'])
    
    # Check if we have lat/lon data
    has_geo = not city_jobs.empty and 'Latitude' in city_jobs.columns and 'Longitude' in city_jobs.columns
    if has_geo:
        try:
            geo_nonnull = city_jobs[['Latitude', 'Longitude']].dropna()
            has_geo = not geo_nonnull.empty
        except Exception:
            has_geo = False

    if has_geo:
        # Rename Job Title count column for clarity and sizing
        city_jobs_plot = city_jobs.copy()
        if 'Job Title' in city_jobs_plot.columns:
            city_jobs_plot.rename(columns={'Job Title': 'Total Jobs'}, inplace=True)
            size_col = 'Total Jobs'
        else:
            size_col = None
        
        # Create scatter mapbox with custom styling for better interactivity
        # Use a gradient color scale from Blue -> Red (No White)
        map_fig = px.scatter_mapbox(
            city_jobs_plot,
            lat="Latitude",
            lon="Longitude",
            size=size_col,
            color=size_col,
            hover_name="City",
            hover_data={k: True for k in city_jobs_plot.columns if k not in ['Latitude', 'Longitude']},
            title="🗺️ Job Distribution by City - Hover over circles for details",
            size_max=120,  # Larger circles for better visibility
            zoom=5,
            height=750,
            color_continuous_scale=px.colors.sequential.Plasma  # Vibrant scale: Blue/Purple -> Orange -> Yellow
        )
        
        # Add city name labels as annotations
        for idx, row in city_jobs_plot.iterrows():
            if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
                map_fig.add_annotation(
                    x=row['Longitude'],
                    y=row['Latitude'],
                    text=f"<b>{row['City']}</b><br>{int(row['Total Jobs']) if 'Total Jobs' in row else 0} jobs",
                    showarrow=False,
                    font=dict(size=12, color='black', family='Arial Black'),
                    bgcolor='rgba(255, 255, 255, 0.7)',
                    bordercolor='rgba(0, 0, 0, 0.5)',
                    borderwidth=1,
                    borderpad=4,
                    xanchor='center',
                    yanchor='middle'
                )
        
        # Update mapbox styling with enhanced interactivity
        map_fig.update_layout(
            mapbox_style="carto-positron", # Cleaner, lighter map style
            margin={"r":0,"t":50,"l":0,"b":0},
            clickmode='event+select',
            hovermode='closest',
            font=dict(size=14, family='Arial'),
            showlegend=True,
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(255, 255, 255, 0.9)', bordercolor='black', borderwidth=1)
        )
        
        # Update marker appearance
        map_fig.update_traces(
            marker=dict(
                opacity=0.8,
                sizemode='area',
                sizeref=0.1,
                allowoverlap=True,
                sizemin=8
            ),
            textposition='top center'
        )
        
        # Add colorbar with better styling and ensure full color range
        map_fig.update_coloraxes(
            colorbar_title=dict(
                text="Total<br>Jobs",
                font=dict(size=13)
            ),
            showscale=True
        )

        # PERSIST ZOOM AND CENTER
        if relayout_data:
            if 'mapbox.center' in relayout_data:
                map_fig.update_layout(mapbox_center=relayout_data['mapbox.center'])
            if 'mapbox.zoom' in relayout_data:
                map_fig.update_layout(mapbox_zoom=relayout_data['mapbox.zoom'])

    else:
        # Placeholder map when no coordinates available
        map_fig = go.Figure()
        map_fig.update_layout(
            title='Map unavailable — no Latitude/Longitude data',
            template='plotly_white',
            xaxis={'visible': False},
            yaxis={'visible': False},
            annotations=[{
                'text': 'No geolocation data (Latitude/Longitude) found. Geocoding is disabled by default. Set AUTO_GEOCODE=1 to enable.',
                'xref': 'paper', 'yref': 'paper', 'showarrow': False, 'x': 0.5, 'y': 0.5,
                'font': {'size': 12}
            }],
            height=550,
        )
    
    # Table with more columns from your data — only include columns that actually exist
    candidate_cols = ['Job Title', 'Company', 'City', 'Category', 'applicants', 'Work Mode']
    present_cols = [c for c in candidate_cols if c in filtered_df.columns]
    table_data = filtered_df[present_cols].head(20) if present_cols else pd.DataFrame()
    table = dash_table.DataTable(
        data=table_data.to_dict('records'),
        columns=[{'name': col, 'id': col} for col in table_data.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'minWidth': '100px', 'width': '150px', 'maxWidth': '200px'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
    )
    
    return city_bar_fig, map_fig, table


# Callbacks for Deep Analysis page
@app.callback(
    [Output('top-companies-chart', 'figure'),
     Output('education-level-chart', 'figure'),
     Output('skills-cloud', 'figure'),
     Output('experience-chart', 'figure'),
     Output('applicants-chart', 'figure')],
    [Input('sidebar-company-filter', 'value'),
     Input('sidebar-city-filter', 'value'),
     Input('sidebar-category-filter', 'value'),
     Input('sidebar-work-mode-filter', 'value'),
     Input('sidebar-employment-type-filter', 'value'),
     Input('sidebar-career-level-filter', 'value'),
     Input('sidebar-education-filter', 'value'),
     Input('sidebar-date-filter', 'start_date'),
     Input('sidebar-date-filter', 'end_date'),
     Input('global-search-bar', 'value')]
)
def update_deep_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, search_text):
    filtered_df = df.copy()
    
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

    
    # Apply search text filter
    if search_text and search_text.strip():
        search_term = search_text.strip().lower()
        search_cols = ['Company', 'City', 'Category', 'Job Title', 'Work Mode', 'Employment Type', 'Career Level']
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for col in search_cols:
            if col in filtered_df.columns:
                mask |= filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False)
        filtered_df = filtered_df[mask]
    
    # Top companies chart
    col = 'Company'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    top_companies = s.value_counts().head(5).reset_index(name='count').rename(columns={'index': col})
    top_companies_fig = px.bar(top_companies, x='count', y=col, title='Top 5 Companies', orientation='h')
    
    # Education level chart
    col = 'education_level'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    education_counts = s.value_counts().reset_index(name='count').rename(columns={'index': col})
    # pie expects names to match column
    education_fig = px.pie(education_counts, values='count', names=col, title='Education Level Distribution')
    
    # Skills cloud (using bar chart as proxy)
    all_skills = []
    for i in range(11):
        skill_col = f'Skill{i}'
        if skill_col in filtered_df.columns:
            all_skills.extend(filtered_df[skill_col].dropna().tolist())
    
    if all_skills:
        skill_counts = pd.Series(all_skills).value_counts().head(15).reset_index(name='count').rename(columns={'index': 'skill'})
        skills_fig = px.bar(skill_counts, x='count', y='skill', title='Top Skills Demand', orientation='h')
    else:
        skills_fig = px.bar(pd.DataFrame({'skill': [], 'count': []}), x='count', y='skill', title='Top Skills Demand', orientation='h')
    
    # Experience chart
    if 'Year Of Exp' in filtered_df.columns:
        experience_fig = px.histogram(filtered_df, x='Year Of Exp', title='Years of Experience Distribution')
    else:
        experience_fig = px.histogram(pd.DataFrame({'Year Of Exp': []}), x='Year Of Exp', title='Years of Experience Distribution')
    
    # Applicants by company
    if 'Company' in filtered_df.columns and 'applicants' in filtered_df.columns:
        applicants_by_company = filtered_df.groupby('Company')['applicants'].mean().reset_index().sort_values('applicants', ascending=False).head(10)
        applicants_fig = px.bar(applicants_by_company, x='applicants', y='Company', title='Average Applicants per Company', orientation='h')
    else:
        applicants_fig = px.bar(pd.DataFrame({'Company': [], 'applicants': []}), x='applicants', y='Company', title='Average Applicants per Company', orientation='h')
    
    # Style figures with dark theme
    for fig in [top_companies_fig, education_fig, skills_fig, experience_fig, applicants_fig]:
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff', family='Inter'),
            title_font=dict(size=18, color='#0066CC'),
            hoverlabel=dict(
                bgcolor='rgba(26, 26, 62, 0.95)',
                font_size=13,
                font_family='Inter'
            )
        )
    
    return top_companies_fig, education_fig, skills_fig, experience_fig, applicants_fig

# Callbacks for Time Analysis page
@app.callback(
    [Output('month-day-line-chart', 'figure'),
     Output('month-bar-chart', 'figure'),
     Output('applicants-trend-chart', 'figure')],
    [Input('sidebar-company-filter', 'value'),
     Input('sidebar-city-filter', 'value'),
     Input('sidebar-category-filter', 'value'),
     Input('sidebar-work-mode-filter', 'value'),
     Input('sidebar-employment-type-filter', 'value'),
     Input('sidebar-career-level-filter', 'value'),
     Input('sidebar-education-filter', 'value'),
     Input('sidebar-date-filter', 'start_date'),
     Input('sidebar-date-filter', 'end_date'),
     Input('global-search-bar', 'value')]
)
def update_time_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, search_text):
    try:
        filtered_df = df.copy()
        
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
        
        # Apply search text filter
        if search_text and search_text.strip():
            search_term = search_text.strip().lower()
            search_cols = ['Company', 'City', 'Category', 'Job Title', 'Work Mode', 'Employment Type', 'Career Level']
            mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
            for col in search_cols:
                if col in filtered_df.columns:
                    mask |= filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False)
            filtered_df = filtered_df[mask]
        
        # Ensure posted is datetime before filtering by date range
        if 'posted' in filtered_df.columns:
            filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        
        if start_date and end_date:
            filtered_df = filtered_df[(filtered_df['posted'] >= start_date) & (filtered_df['posted'] <= end_date)]
            
        # Prepare time data
        if 'posted' in filtered_df.columns and not filtered_df['posted'].dropna().empty:
            filtered_df['Month'] = filtered_df['posted'].dt.to_period('M').astype(str)
            filtered_df['Day'] = filtered_df['posted'].dt.day_name()
        else:
            filtered_df['Month'] = pd.Series(dtype='object')
            filtered_df['Day'] = pd.Series(dtype='object')
    except Exception as e:
        print(f"Error in update_time_analysis: {e}")
        filtered_df = pd.DataFrame()
        filtered_df['Month'] = pd.Series(dtype='object')
        filtered_df['Day'] = pd.Series(dtype='object')
    
    # Month-Day line chart
    if not filtered_df['Month'].dropna().empty:
        month_day_df = filtered_df.groupby(['Month', 'Day']).size().reset_index(name='count')
        month_day_fig = px.line(month_day_df, x='Month', y='count', color='Day', title='Jobs by Month and Day')
    else:
        month_day_fig = px.line(pd.DataFrame({'Month': [], 'count': [], 'Day': []}), x='Month', y='count', color='Day', title='Jobs by Month and Day')
    
    # Month bar chart
    if not filtered_df['Month'].dropna().empty:
        month_df = filtered_df['Month'].value_counts().reset_index(name='count').rename(columns={'index': 'Month'}).sort_values('Month')
        month_bar_fig = px.bar(month_df, x='Month', y='count', title='Jobs by Month')
    else:
        month_bar_fig = px.bar(pd.DataFrame({'Month': [], 'count': []}), x='Month', y='count', title='Jobs by Month')
    
    # Applicants trend
    if 'applicants' in filtered_df.columns and not filtered_df['Month'].dropna().empty:
        applicants_trend = filtered_df.groupby('Month')['applicants'].mean().reset_index()
        applicants_trend_fig = px.line(applicants_trend, x='Month', y='applicants', title='Average Applicants Trend')
    else:
        applicants_trend_fig = px.line(pd.DataFrame({'Month': [], 'applicants': []}), x='Month', y='applicants', title='Average Applicants Trend')
    
    # Style figures with dark theme
    for fig in [month_day_fig, month_bar_fig, applicants_trend_fig]:
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff', family='Inter'),
            title_font=dict(size=18, color='#0066CC'),
            hoverlabel=dict(
                bgcolor='rgba(10, 25, 41, 0.95)',
                font_size=13,
                font_family='Inter'
            )
        )
    
    return month_day_fig, month_bar_fig, applicants_trend_fig


if __name__ == '__main__':
    # new Dash versions use app.run()
    try:
        app.run(debug=True, host='127.0.0.1', port=8050)
    except TypeError:
        # fallback for older versions
        app.run_server(debug=True, host='127.0.0.1', port=8050)
