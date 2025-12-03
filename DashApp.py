import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
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
import folium
from folium.plugins import MarkerCluster, FastMarkerCluster
from folium.features import DivIcon
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Cache buster for forcing browser refresh
CACHE_VERSION = int(time.time())

# Create Dash app instance (allow callbacks for components added dynamically)
# Custom CSS will be automatically loaded from assets/custom.css
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css'
    ], 
    suppress_callback_exceptions=True
)
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

    # extract City from Location ONLY if City column is missing or empty
    if 'City' not in df.columns:
        if 'location_2' in df.columns:
            # Prefer location_2 (e.g. "Cairo, Egypt") -> "Cairo"
            df['City'] = df['location_2'].str.split(',').str[0].str.strip()
        elif 'Location' in df.columns:
            # Fallback to Location
            df['City'] = df['Location'].str.split(',').str[0].str.strip()
    else:
        # City column exists, but fill NaNs if any
        if 'location_2' in df.columns:
             df['City'] = df['City'].fillna(df['location_2'].str.split(',').str[0].str.strip())

    # Create job_status if missing
    if 'job_status' not in df.columns:
        # Logic: If open_positions > 0 -> Open, else Closed. 
        # Fallback: If no open_positions, assume Open for recent posts (last 30 days), else Closed
        if 'open_positions' in df.columns:
            df['job_status'] = df['open_positions'].apply(lambda x: 'Open' if x > 0 else 'Closed')
        else:
            # Fallback logic
            df['job_status'] = 'Open' # Default to Open if no data
            
    # Clean Link column
    if 'Link' in df.columns:
        df['Link'] = df['Link'].fillna('#').astype(str)
    else:
        df['Link'] = '#'
    
    # Normalize City column to fix filter issues
    if 'City' in df.columns:
        df['City'] = df['City'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
            
    # Ensure In_City exists (District level)
    if 'In_City' not in df.columns and 'Location' in df.columns:
        # If Location is "Sheraton, Cairo, Egypt", In_City = "Sheraton"
        df['In_City'] = df['Location'].str.split(',').str[0].str.strip()

    # Filter for Egypt only - STRICT FILTER
    # Prefer Location_2 as it's more reliable, fallback to Location
    if 'Location_2' in df.columns:
        # Use Location_2 which should have format "City, Egypt"
        df = df[df['Location_2'].astype(str).str.contains('Egypt', case=False, na=False)]
        print(f"✓ Filtered to {len(df)} jobs in Egypt using Location_2")
    elif 'Location' in df.columns:
        # Fallback to Location column
        df = df[df['Location'].astype(str).str.contains('Egypt', case=False, na=False)]
        print(f"✓ Filtered to {len(df)} jobs in Egypt using Location")
    
    # Additional validation: Remove any rows with coordinates clearly outside Egypt
    # Egypt bounds: roughly 22°N to 32°N latitude, 25°E to 37°E longitude
    # Additional validation: Remove any rows with coordinates clearly outside Egypt
    # Egypt bounds: roughly 22°N to 32°N latitude, 25°E to 37°E longitude
    # COMMENTED OUT TO FIX JOB COUNT DISCREPANCY (User wants all 7315 jobs)
    # if 'Latitude' in df.columns and 'Longitude' in df.columns:
    #     before_count = len(df)
    #     df = df[
    #         ((df['Latitude'] >= 22) & (df['Latitude'] <= 32) & 
    #          (df['Longitude'] >= 25) & (df['Longitude'] <= 37)) |
    #         (df['Latitude'].isna()) | (df['Longitude'].isna())
    #     ]
    #     removed = before_count - len(df)
    #     if removed > 0:
    #         print(f"✓ Removed {removed} jobs with coordinates outside Egypt")

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

    # Hardcoded coordinates for major Egyptian cities to ensure data visibility
    # This solves the "map is not making sense" issue by guaranteeing coordinates for top cities
    egypt_cities_coords = {
        'Cairo': {'lat': 30.0444, 'lon': 31.2357},
        'Giza': {'lat': 30.0131, 'lon': 31.2089},
        'Alexandria': {'lat': 31.2001, 'lon': 29.9187},
        'New Cairo': {'lat': 30.0074, 'lon': 31.4913},
        'Nasr City': {'lat': 30.0561, 'lon': 31.3301},
        '6th of October': {'lat': 29.9742, 'lon': 30.9582},
        'Maadi': {'lat': 29.9602, 'lon': 31.2569},
        'Sheikh Zayed': {'lat': 30.0444, 'lon': 30.9833},
        'Sharm El Sheikh': {'lat': 27.9158, 'lon': 34.3299},
        'Hurghada': {'lat': 27.2579, 'lon': 33.8116},
        'Luxor': {'lat': 25.6872, 'lon': 32.6396},
        'Aswan': {'lat': 24.0889, 'lon': 32.8998},
        'Mansoura': {'lat': 31.0409, 'lon': 31.3785},
        'Tanta': {'lat': 30.7865, 'lon': 31.0004},
        'Port Said': {'lat': 31.2653, 'lon': 32.3019},
        'Suez': {'lat': 29.9668, 'lon': 32.5498},
        'Ismailia': {'lat': 30.5965, 'lon': 32.2715},
        'Damietta': {'lat': 31.4175, 'lon': 31.8144},
        'Zagazig': {'lat': 30.5765, 'lon': 31.5041},
        'Fayoum': {'lat': 29.3084, 'lon': 30.8428},
        'Minya': {'lat': 28.1099, 'lon': 30.7503},
        'Assiut': {'lat': 27.1783, 'lon': 31.1859},
        'Sohag': {'lat': 26.5590, 'lon': 31.6957},
        'Qena': {'lat': 26.1551, 'lon': 32.7160},
        'Beni Suef': {'lat': 29.0661, 'lon': 31.0994},
        'Matruh': {'lat': 31.3543, 'lon': 27.2373},
        'Kafr El Sheikh': {'lat': 31.1107, 'lon': 30.9388},
        'Banha': {'lat': 30.4660, 'lon': 31.1858},
        'Damanhur': {'lat': 31.0424, 'lon': 30.4635},
        'Obour City': {'lat': 30.2233, 'lon': 31.4756},
        'Helwan': {'lat': 29.8414, 'lon': 31.3008},
        'Mokattam': {'lat': 30.0220, 'lon': 31.3060},
        'Heliopolis': {'lat': 30.0890, 'lon': 31.3284},
        'Sheraton': {'lat': 30.1066, 'lon': 31.3688},
        'Dokki': {'lat': 30.0385, 'lon': 31.2123},
        'Mohandessin': {'lat': 30.0511, 'lon': 31.2045},
        'Agouza': {'lat': 30.0538, 'lon': 31.2148},
        'Zamalek': {'lat': 30.0609, 'lon': 31.2197},
        'Downtown': {'lat': 30.0444, 'lon': 31.2357},
        'Garden City': {'lat': 30.0362, 'lon': 31.2316},
        'Katameya': {'lat': 29.9926, 'lon': 31.4055},
        'Rehab City': {'lat': 30.0630, 'lon': 31.4950},
        'Madinaty': {'lat': 30.0850, 'lon': 31.6300},
        'Shorouk City': {'lat': 30.1290, 'lon': 31.6090},
        'Badr City': {'lat': 30.1420, 'lon': 31.7400},
        '10th of Ramadan': {'lat': 30.3000, 'lon': 31.7333},
        'Sadat City': {'lat': 30.3833, 'lon': 30.5167},
        'Borg El Arab': {'lat': 30.9167, 'lon': 29.5333},
        'Ain Sokhna': {'lat': 29.6000, 'lon': 32.3167},
        'North Coast': {'lat': 30.9500, 'lon': 28.8500},
        'Siwa Oasis': {'lat': 29.2032, 'lon': 25.5195},
        'Marsa Alam': {'lat': 25.0676, 'lon': 34.8790},
        'Dahab': {'lat': 28.5096, 'lon': 34.5136},
        'Nuweiba': {'lat': 29.0333, 'lon': 34.6667},
        'Taba': {'lat': 29.4925, 'lon': 34.8957},
        'Saint Catherine': {'lat': 28.5559, 'lon': 33.9760},
        'El Tor': {'lat': 28.2333, 'lon': 33.6167},
        'Ras Sudr': {'lat': 29.5833, 'lon': 32.7000},
        'Qalyub': {'lat': 30.1785, 'lon': 31.2067},
        'Khanka': {'lat': 30.2111, 'lon': 31.3686},
        'Shubra El Kheima': {'lat': 30.1286, 'lon': 31.2422}
    }

    lat_col, lon_col = _detect_latlon(df)

    # 1. First try to map from hardcoded dictionary (fastest and most reliable)
    # 1. First try to map from hardcoded dictionary (fastest and most reliable)
    # PRIORITIZE In_City for better granularity (e.g. show Maadi location instead of generic Cairo)
    df['temp_lat'] = np.nan
    df['temp_lon'] = np.nan

    if 'In_City' in df.columns:
         df['temp_lat'] = df['In_City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lat'))
         df['temp_lon'] = df['In_City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lon'))

    if 'City' in df.columns:
        # Fill missing with City mapping
        mask_missing = df['temp_lat'].isna()
        df.loc[mask_missing, 'temp_lat'] = df.loc[mask_missing, 'City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lat'))
        df.loc[mask_missing, 'temp_lon'] = df.loc[mask_missing, 'City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lon'))

        # If Latitude/Longitude columns don't exist, create them
        if 'Latitude' not in df.columns: df['Latitude'] = np.nan
        if 'Longitude' not in df.columns: df['Longitude'] = np.nan

        # Fill missing values in main columns with our hardcoded values
        df['Latitude'] = df['Latitude'].fillna(df['temp_lat'])
        df['Longitude'] = df['Longitude'].fillna(df['temp_lon'])
        
        # Cleanup
        df.drop(columns=['temp_lat', 'temp_lon'], inplace=True)
        lat_col, lon_col = 'Latitude', 'Longitude'

    # Add small jitter to prevent perfect overlap (spiderfy hell)
    # 0.005 degrees is roughly 500m
    if 'Latitude' in df.columns and 'Longitude' in df.columns:
        df['Latitude'] = df['Latitude'] + np.random.uniform(-0.005, 0.005, size=len(df))
        df['Longitude'] = df['Longitude'] + np.random.uniform(-0.005, 0.005, size=len(df))

    # 2. If still missing, use cached geocoding results
    if 'City' in df.columns:
        cache = _load_cache(cache_path)
        # Only geocode missing cities if AUTO_GEOCODE=1
        do_geocode = os.environ.get('AUTO_GEOCODE', '').lower() in ('1', 'true', 'yes')
        
        # Identify cities that still have no coordinates
        missing_coords_mask = df['Latitude'].isna() | df['Longitude'].isna()
        missing_cities = df.loc[missing_coords_mask, 'City'].dropna().unique().tolist()
        
        if do_geocode and missing_cities:
            for city in missing_cities:
                if city in cache: continue
                try:
                    _geocode_city(city, cache, cache_path)
                except Exception: pass
            cache = _load_cache(cache_path)

        # Map from cache
        if cache:
            # We iterate only over rows that still need coords
            def get_lat_from_cache(city):
                return cache.get(city, {}).get('lat')
            def get_lon_from_cache(city):
                return cache.get(city, {}).get('lon')
                
            df.loc[missing_coords_mask, 'Latitude'] = df.loc[missing_coords_mask, 'City'].apply(get_lat_from_cache)
            df.loc[missing_coords_mask, 'Longitude'] = df.loc[missing_coords_mask, 'City'].apply(get_lon_from_cache)

    return df

# Load dataframe once so layout/callbacks can reference it
try:
    df = load_real_data()
    print(f"📊 DEBUG: After load_real_data(), df has {len(df)} jobs")
    print(f"📊 DEBUG: Columns: {list(df.columns)}")
    print(f"📊 DEBUG: Any duplicates? {df.duplicated().sum()}")
except Exception as e:
    print(f"⚠ Could not load data in load_real_data(): {e}")
    df = pd.DataFrame()

# Load Skills data from unpivoted file
try:
    skills_df = pd.read_excel(os.path.join(os.path.dirname(__file__), 'Skills_Cleaned_UnPivot.xlsx'))
    # Rename columns for consistency
    skills_df.rename(columns={'Jobs Title': 'Job Title'}, inplace=True)
    print(f"✓ Loaded {len(skills_df)} skills records")
except Exception as e:
    print(f"⚠ Could not load skills data: {e}")
    skills_df = pd.DataFrame()


# ============================================
# HELPER FUNCTION: Theme-Aware Color Scales
# ============================================

def get_color_scale(theme='light'):
    """
    Return appropriate color scale based on theme.
    
    Light Mode: Cyan to Dark Blue (existing gradient)
    Dark Mode: Light Blue to White (smaller bars = lighter, larger bars = white)
    """
    if theme == 'dark':
        # Light Blue → White gradient
        # Smaller values = Light Blue, Larger values = White
        return [(0, '#66B3FF'), (0.5, '#B3D9FF'), (1, '#FFFFFF')]
    else:
        # Light Mode: Cyan to Dark Blue (existing)
        return [(0, '#00C9FF'), (1, '#001f3f')]


def apply_chart_styling(fig, is_horizontal_bar=True, add_margin=True):
    """
    Apply consistent styling to charts with proper data label visibility and white tooltips.
    
    Args:
        fig: Plotly figure object
        is_horizontal_bar: If True, adds margin to x-axis for horizontal bars
        add_margin: If True, adds 20% margin to prevent label truncation
    """
    # Add margin to prevent data label truncation
    if add_margin and is_horizontal_bar:
        try:
            max_val = max([trace.x.max() if hasattr(trace, 'x') and trace.x is not None and len(trace.x) > 0 else 0 for trace in fig.data])
            if max_val > 0:
                fig.update_layout(xaxis_range=[0, max_val * 1.2])  # 20% margin
        except:
            pass
    
    # Apply consistent styling
    fig.update_layout(
        dragmode=False,
        template='plotly',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#001F3F', family='Inter'),
        title_font=dict(size=48, color='#001F3F'),
        hoverlabel=dict(
            bgcolor='#001F3F',
            font_size=13,
            font_family='Inter',
            font_color='white'  # White tooltip text
        )
    )
    
    return fig


def apply_visual_highlighting(fig, all_values, selected_values, is_pie=False):
    """
    Apply Power BI-style visual highlighting to charts.
    Selected bars/slices remain opaque, non-selected become semi-transparent.
    
    Args:
        fig: Plotly figure object
        all_values: List of all category values in the chart
        selected_values: List of currently selected/filtered values
        is_pie: True if this is a pie/donut chart
    """
    if not selected_values or len(selected_values) == 0:
        # No filter active - all bars fully opaque
        return fig
    
    # Create opacity list: 1.0 for selected, 0.3 for non-selected
    opacities = [1.0 if val in selected_values else 0.3 for val in all_values]
    
    if is_pie:
        # For pie charts, we need to modify each slice individually
        # Plotly pie charts don't support marker opacity, so we use trace opacity
        # We'll need to update the colors with alpha channel instead
        import plotly.graph_objects as go
        
        # Get current colors
        if fig.data[0].marker.colors is not None:
            colors = list(fig.data[0].marker.colors)
        else:
            # Use default plotly colors
            default_colors = px.colors.qualitative.Plotly
            colors = [default_colors[i % len(default_colors)] for i in range(len(all_values))]
        
        # Convert colors to RGBA with opacity
        rgba_colors = []
        for i, (color, opacity) in enumerate(zip(colors, opacities)):
            if opacity < 1.0:
                # Convert to RGBA with transparency
                if color.startswith('#'):
                    # Convert hex to RGB
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                    rgba_colors.append(f'rgba({r},{g},{b},{opacity})')
                else:
                    rgba_colors.append(color)  # Keep as is if already rgba or named color
            else:
                rgba_colors.append(color)
        
        fig.update_traces(marker=dict(colors=rgba_colors))
    else:
        # For bar charts, update marker opacity
        fig.update_traces(marker=dict(opacity=opacities, line=dict(width=0)))
    
    return fig


# ============================================
# LAYOUT FUNCTIONS
# ============================================

# Page 3: Deep Analysis
def deep_analysis_layout():
    # safe option lists
    categories = df['Category'].dropna().unique().tolist() if 'Category' in df.columns else []
    companies = df['Company'].dropna().unique().tolist() if 'Company' in df.columns else []
    career_levels = df['Career Level'].dropna().unique().tolist() if 'Career Level' in df.columns else []
    education_levels = df['education_level'].dropna().unique().tolist() if 'education_level' in df.columns else []

    return html.Div([
        html.H1("Deep Analysis", className='gradient-text', style={'textAlign': 'center', 'marginBottom': 30}),
        
        # KPIs Row - Professional Design with Icons
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-clipboard-list')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Total Jobs", className='kpi-label-v2'),
                    html.Div(id='deep-total-jobs-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=12//5),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-users')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Total Applicants", className='kpi-label-v2'),
                    html.Div(id='deep-total-applicants-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=12//5),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-clock')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Avg Years of Exp", className='kpi-label-v2'),
                    html.Div(id='deep-avg-exp-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=12//5),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-user-plus')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Avg Applicants", className='kpi-label-v2'),
                    html.Div(id='deep-avg-applicants-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=12//5),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-bullseye')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Top Career Level", className='kpi-label-v2'),
                    html.Div(id='deep-top-career-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=12//5),
        ], style={'marginBottom': 30}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='top-companies-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
            dbc.Col(dcc.Graph(id='education-level-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
        ], style={'marginBottom': 20}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='skills-cloud', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
            dbc.Col(dcc.Graph(id='experience-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
        ], style={'marginBottom': 20}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='applicants-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=12),
        ], style={'marginBottom': 20}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='decomposition-tree', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=12),
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

        # KPIs - Row 1
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-briefcase')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Total Jobs", className='kpi-label-v2'),
                    html.Div(id='total-jobs-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-building')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Total Companies", className='kpi-label-v2'),
                    html.Div(id='total-companies-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-layer-group')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Total Categories", className='kpi-label-v2'),
                    html.Div(id='total-categories-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
        ], style={'marginBottom': 20}),

        # KPIs - Row 2
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-chart-line')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Avg Applicants", className='kpi-label-v2'),
                    html.Div(id='avg-applicants-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-globe-americas')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("% Remote / Hybrid", className='kpi-label-v2'),
                    html.Div(id='remote-hybrid-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-calendar-alt')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Latest Posting", className='kpi-label-v2'),
                    html.Div(id='latest-date-kpi', className='kpi-value-v2', style={'fontSize': '1.2rem'})
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=4),
        ], style={'marginBottom': 30}),

        # Charts
        dbc.Row([
            dbc.Col(dcc.Graph(id='employment-type-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
            dbc.Col(dcc.Graph(id='work-mode-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
        ], style={'marginBottom': 20}),

        dbc.Row([
            dbc.Col(dcc.Graph(id='career-level-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
            dbc.Col(dcc.Graph(id='top-categories-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
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
        
        # Map Style Switcher
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
                value='satellite',  # Default to Satellite as discussed
                clearable=False,
                style={'width': '250px', 'color': 'black'}
            )
        ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'marginBottom': '20px'}),

        dbc.Row([
            dbc.Col(html.Div(dcc.Loading(dcc.Graph(id='city-bar-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]})), style={'height': '600px', 'overflowY': 'auto'}), width=6),
            dbc.Col(dcc.Loading(html.Iframe(id='city-map', style={'width': '100%', 'height': '600px', 'border': 'none'})), width=6),
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
        
        # KPIs Row - Professional Design
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-calendar-days')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Jobs in Period", className='kpi-label-v2'),
                    html.Div(id='time-jobs-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=3),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-arrow-trend-up')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("MoM Growth", className='kpi-label-v2'),
                    html.Div(id='time-growth-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=3),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-chart-area')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Avg Applicants Trend", className='kpi-label-v2'),
                    html.Div(id='time-applicants-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=3),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-calendar-week')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Peak Posting Day", className='kpi-label-v2'),
                    html.Div(id='time-peak-day-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=3),
        ], style={'marginBottom': 30}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='month-day-line-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
            dbc.Col(dcc.Graph(id='month-bar-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=6),
        ], style={'marginBottom': 20}),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id='applicants-trend-chart', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]}), width=12),
        ])
    ])


# Page 5: Skills Analysis
def skills_page_layout():
    return html.Div([
        html.H1("Skills Analysis", className='gradient-text', style={'textAlign': 'center', 'marginBottom': 30}),
        
        # KPIs Row - Professional Design
        dbc.Row([
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-hashtag')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Total Unique Skills", className='kpi-label-v2'),
                    html.Div(id='total-skills-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=3),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-star')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Most Demanded Skill", className='kpi-label-v2'),
                    html.Div(id='top-skill-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=3),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-list-check')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Avg Skills per Job", className='kpi-label-v2'),
                    html.Div(id='avg-skills-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=3),
            
            dbc.Col(html.Div([
                html.Div([
                    html.I(className='fa-solid fa-chart-pie')
                ], className='kpi-icon-box'),
                html.Div([
                    html.Div("Top Skill Category", className='kpi-label-v2'),
                    html.Div(id='top-skill-cat-kpi', className='kpi-value-v2')
                ], className='kpi-content-box')
            ], className='kpi-card-v2 kpi-float'), width=3),
        ], style={'marginBottom': 30}),
        
        # Main visualizations
        dbc.Row([
            dbc.Col(dcc.Loading(dcc.Graph(id='skills-wordcloud', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]})), width=8),
            dbc.Col(dcc.Loading(dcc.Graph(id='skills-category-breakdown', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]})), width=4),
        ], style={'marginBottom': 20}),
        
        dbc.Row([
            dbc.Col(dcc.Loading(dcc.Graph(id='top-skills-bar', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]})), width=6),
            dbc.Col(dcc.Loading(dcc.Graph(id='skills-trend', config={'displayModeBar': True, 'modeBarButtons': [['toImage']]})), width=6),
        ], style={'marginBottom': 20}),
    ])


# --- set a top-level layout so Dash has something at startup ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    
    # Store for theme preference (light/dark)
    dcc.Store(id='theme-store', data='light', storage_type='local'),
    
    # Store for click-to-filter data
    dcc.Store(id='click-filter-store', data=None),
    
    # Theme Container - Wraps everything to apply CSS classes
    html.Div(id='theme-container', children=[
        # Navbar with Logo
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Overview", href="/")),
            dbc.NavItem(dbc.NavLink("City Map", href="/city-map")),
            dbc.NavItem(dbc.NavLink("Deep Analysis", href="/deep-analysis")),
            dbc.NavItem(dbc.NavLink("Time Analysis", href="/time-analysis")),
            dbc.NavItem(dbc.NavLink("Skills", href="/skills")),
            dbc.NavItem(
                html.Button(
                    [html.Span("🌙", className='icon', id='theme-icon'), " Dark Mode"],
                    id='theme-toggle-btn',
                    n_clicks=0,
                    style={'marginLeft': '20px'}
                )
            ),
        ],
        brand=html.Div([
            # Logo and Title Container (Static, won't shrink or move)
            html.Div([
                html.Img(src='/assets/logo.png', style={'height': '60px', 'marginRight': '15px'}),
                html.Span("Hire Q Services - Jobs Dashboard", style={'verticalAlign': 'middle', 'fontSize': '24px', 'fontWeight': '800', 'whiteSpace': 'nowrap'}),
            ], style={'display': 'flex', 'alignItems': 'center', 'flexShrink': 0, 'marginRight': '20px'}),
            
            
            # ========== SINGLE SEARCH BAR - VERSION 2.0 ==========
            # Global Search Bar Container - Minimal Rounded Design
            html.Div([
                # SEARCH ICON - يمكنك تغيير الأيقونة هنا
                html.Span("🔍", style={
                    'fontSize': '24px',
                    'marginRight': '15px',
                    'color': '#888',
                    'flexShrink': 0
                }), 
                
                dcc.Input(
                    id='global-search-bar',
                    type='text',
                    placeholder='Search Anything',
                    debounce=True,
                    className='search-input-field',
                    style={
                        'width': '100%',
                        'border': 'none',
                        'backgroundColor': 'transparent',
                        'color': '#333',
                        'fontSize': '18px',
                        'outline': 'none',
                        'height': '100%',
                        'fontWeight': '400',
                        'boxShadow': 'none',
                        'caretColor': 'transparent'  # Hides the blinking cursor line
                    }
                )
            ], className='navbar-search-container', style={
                'display': 'flex',
                'alignItems': 'center',
                'height': '60px',
                'borderRadius': '30px',
                'border': '1px solid #e0e0e0',
                'padding': '0 25px',
                'backgroundColor': 'white',
                'marginLeft': '20px',
                'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'
            })
        ], style={'display': 'flex', 'alignItems': 'center'}),  # End of Brand Div
        color="primary",
        dark=True,
        sticky='top',
        fluid=True,
        style={'padding': '10px 30px'}
    ),
    
    # Sidebar Tab (visible on left edge)
    html.Div([
        html.Span("FILTERS", style={'writingMode': 'vertical-rl', 'color': 'white', 'fontWeight': '700', 'fontSize': '1.1rem', 'letterSpacing': '2px'})
    ], id='sidebar-tab'),
    
    # Backdrop
    html.Div(id='sidebar-backdrop', className=''),
    
    # Left Filter Sidebar (hover to reveal) with Pagination
    html.Div([
        html.H4("🔍 Filters"),
        
        # Clear Filters Button
        html.Button([html.Span("🗑️", className='icon'), " Clear Filters"], id='clear-filters-btn', n_clicks=0),
        
        # Page 1 Filters (Main Filters)
        html.Div([
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
            
            # City Filter - USES CITY COLUMN ONLY
            html.Div([
                html.Label("City"),
                dcc.Dropdown(
                    id='sidebar-city-filter',
                    options=[{'label': c, 'value': c} for c in sorted(df['City'].dropna().unique().tolist())] if 'City' in df.columns else [],
                    multi=True,
                    placeholder='Select Cities'
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
            
            # Arrow to Page 2
            html.Div([
                html.Button([html.Span("➡️", className='icon'), " More Filters"], id='more-filters-btn', n_clicks=0)
            ]),
            
        ], id='filter-page-1', style={'display': 'block'}),
        
        # Page 2 Filters (Additional Filters)
        html.Div([
            # Back Arrow
            html.Div([
                html.Button('⬅️ Back', id='goto-page-1', n_clicks=0,
                           style={'width': '100%', 'marginBottom': '15px', 'backgroundColor': '#666', 'color': 'white', 'border': 'none', 'padding': '10px', 'borderRadius': '5px', 'cursor': 'pointer'})
            ]),
            
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
            
            # In-City Filter
            html.Div([
                html.Label("Location within City"),
                dcc.Dropdown(
                    id='sidebar-in-city-filter',
                    options=[{'label': loc, 'value': loc} for loc in sorted(df['In_City'].dropna().unique().tolist())] if 'In_City' in df.columns and not df.empty else [],
                    multi=True,
                    placeholder='Select Locations'
                )
            ], className='filter-group'),
            
            # Avg Years of Experience Filter (NEW)
            html.Div([
                html.Label("Avg Years of Experience"),
                dcc.RangeSlider(
                    id='sidebar-avg-exp-filter',
                    min=0,
                    max=int(df['Year Of Exp_Avg'].max()) if 'Year Of Exp_Avg' in df.columns and df['Year Of Exp_Avg'].notna().any() else 20,
                    step=1,
                    marks={i: str(i) for i in range(0, 21, 5)},
                    value=[0, int(df['Year Of Exp_Avg'].max()) if 'Year Of Exp_Avg' in df.columns and df['Year Of Exp_Avg'].notna().any() else 20]
                )
            ], className='filter-group'),
            
            # Month Filter (NEW - extracted from Date_Posted)
            html.Div([
                html.Label("Month"),
                dcc.Dropdown(
                    id='sidebar-month-filter',
                    options=[
                        {'label': 'January', 'value': 1},
                        {'label': 'February', 'value': 2},
                        {'label': 'March', 'value': 3},
                        {'label': 'April', 'value': 4},
                        {'label': 'May', 'value': 5},
                        {'label': 'June', 'value': 6},
                        {'label': 'July', 'value': 7},
                        {'label': 'August', 'value': 8},
                        {'label': 'September', 'value': 9},
                        {'label': 'October', 'value': 10},
                        {'label': 'November', 'value': 11},
                        {'label': 'December', 'value': 12}
                    ],
                    multi=True,
                    placeholder='Select Months'
                )
            ], className='filter-group'),
            
        ], id='filter-page-2', style={'display': 'none'}),
        
    ], id='filter-sidebar', className=''),
    
    
    # Page Content
    html.Div(id='page-content', style={'margin': '20px'})
    ])  # Close theme-container
])

# Callbacks for routing
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    # normalize pathname: handle None and trailing slashes
    if not pathname or pathname == '/':
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
    elif path == "/skills":
        return skills_page_layout()
    return html.Div(["404 - Page not found"])

# Callback for Sidebar Pagination
@app.callback(
    [Output('filter-page-1', 'style'),
     Output('filter-page-2', 'style'),
     Output('more-filters-btn', 'className')],
    [Input('more-filters-btn', 'n_clicks'),
     Input('goto-page-1', 'n_clicks')]
)
def toggle_filter_pages(more_filters_clicks, goto_page_1_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return {'display': 'block'}, {'display': 'none'}, ''
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'more-filters-btn':
        return {'display': 'none'}, {'display': 'block'}, 'expanded'
    elif button_id == 'goto-page-1':
        return {'display': 'block'}, {'display': 'none'}, ''
    
    return {'display': 'block'}, {'display': 'none'}, ''

# Callback to Clear All Filters
@app.callback(
    [Output('sidebar-company-filter', 'value'),
     Output('sidebar-city-filter', 'value'),
     Output('sidebar-category-filter', 'value'),
     Output('sidebar-work-mode-filter', 'value'),
     Output('sidebar-employment-type-filter', 'value'),
     Output('sidebar-career-level-filter', 'value'),
     Output('sidebar-education-filter', 'value'),
     Output('sidebar-date-filter', 'start_date'),
     Output('sidebar-date-filter', 'end_date'),
     Output('sidebar-in-city-filter', 'value'),
     Output('sidebar-avg-exp-filter', 'value'),
     Output('sidebar-month-filter', 'value'),
     Output('global-search-bar', 'value')],
    [Input('clear-filters-btn', 'n_clicks')]
)
def clear_all_filters(n_clicks):
    if n_clicks:
        # Reset all values
        max_exp = int(df['Year Of Exp_Avg'].max()) if 'Year Of Exp_Avg' in df.columns and df['Year Of Exp_Avg'].notna().any() else 20
        return [], [], [], [], [], [], [], None, None, [], [0, max_exp], [], ""
    return dash.no_update

# Callbacks for Overview page
@app.callback(
    [Output('total-jobs-kpi', 'children'),
     Output('total-companies-kpi', 'children'),
     Output('total-categories-kpi', 'children'),
     Output('avg-applicants-kpi', 'children'),
     Output('remote-hybrid-kpi', 'children'),
     Output('latest-date-kpi', 'children'),
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
     Input('sidebar-in-city-filter', 'value'),
     Input('sidebar-avg-exp-filter', 'value'),
     Input('sidebar-month-filter', 'value'),
     Input('global-search-bar', 'value'),
     Input('theme-store', 'data')]
)
def update_overview(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme):
    filtered_df = df.copy()
    
    print(f"📊 DEBUG update_overview: Starting with {len(filtered_df)} jobs")
    
    # Apply filters
    if companies:
        before = len(filtered_df)
        filtered_df = filtered_df[filtered_df['Company'].isin(companies)]
        print(f"  Company filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    if cities:
        before = len(filtered_df)
        filtered_df = filtered_df[filtered_df['City'].isin(cities)]
        print(f"  City filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    if categories:
        before = len(filtered_df)
        filtered_df = filtered_df[filtered_df['Category'].isin(categories)]
        print(f"  Category filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    if work_modes:
        before = len(filtered_df)
        filtered_df = filtered_df[filtered_df['Work Mode'].isin(work_modes)]
        print(f"  Work Mode filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    if employment_types:
        before = len(filtered_df)
        filtered_df = filtered_df[filtered_df['Employment Type'].isin(employment_types)]
        print(f"  Employment Type filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    if career_levels:
        before = len(filtered_df)
        filtered_df = filtered_df[filtered_df['Career Level'].isin(career_levels)]
        print(f"  Career Level filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    if education_levels:
        before = len(filtered_df)
        filtered_df = filtered_df[filtered_df['education_level'].isin(education_levels)]
        print(f"  Education Level filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    if start_date and end_date and 'posted' in filtered_df.columns:
        before = len(filtered_df)
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[(filtered_df['posted'] >= start_date) & (filtered_df['posted'] <= end_date)]
        print(f"  Date filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    
    # In-City filter
    if in_cities and 'In_City' in filtered_df.columns:
        before = len(filtered_df)
        filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
        print(f"  In-City filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    
    # Avg Years of Experience filter
    if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
        before = len(filtered_df)
        min_exp, max_exp = avg_exp_range[0], avg_exp_range[1]
        # Include rows with NaN values OR values within range
        filtered_df = filtered_df[
            (filtered_df['Year Of Exp_Avg'].isna()) | 
            ((filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp))
        ]
        print(f"  Experience filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    
    # Month filter
    if months and 'posted' in filtered_df.columns:
        before = len(filtered_df)
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]
        print(f"  Month filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    
    # Apply search text filter - ENHANCED to search ALL relevant columns
    if search_text and search_text.strip():
        before = len(filtered_df)
        search_term = search_text.strip().lower()
        
        # Search across ALL relevant columns from Jobs file
        search_cols = [
            'Job Title', 'Company', 'Location', 'City', 'In_City', 'location_2',
            'Employment Type', 'Work Mode', 'Career Level', 'Category', 
            'Category 2', 'Category 3', 'Skills', 'Skill_List', 'education_level',
            'Year Of Exp', 'How Long Ago'
        ]
        
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for col in search_cols:
            if col in filtered_df.columns:
                mask |= filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False, regex=False)
        
        filtered_df = filtered_df[mask]
        print(f"  Search filter: {before} → {len(filtered_df)} (dropped {before - len(filtered_df)})")
    
    print(f"📊 DEBUG update_overview: After all filters, {len(filtered_df)} jobs remain")
    
    # KPIs
    total_jobs = len(filtered_df)
    total_companies = int(filtered_df['Company'].nunique()) if 'Company' in filtered_df.columns else 0
    total_categories = int(filtered_df['Category'].nunique()) if 'Category' in filtered_df.columns else 0
    
    latest_date = "N/A"
    if 'posted' in filtered_df.columns:
        valid_dates = pd.to_datetime(filtered_df['posted'], errors='coerce').dropna()
        if not valid_dates.empty:
            latest_date = valid_dates.max().strftime('%Y-%m-%d')
            
    avg_applicants = round(filtered_df['applicants'].mean(), 1) if 'applicants' in filtered_df.columns and not filtered_df['applicants'].dropna().empty else 0
    
    # Calculate Remote/Hybrid percentage
    remote_hybrid_pct = "0%"
    if 'Work Mode' in filtered_df.columns and len(filtered_df) > 0:
        remote_hybrid_count = filtered_df[filtered_df['Work Mode'].isin(['Remote', 'Hybrid'])].shape[0]
        pct = (remote_hybrid_count / len(filtered_df)) * 100
        remote_hybrid_pct = f"{pct:.1f}%"
    
    # Charts
    # Employment Type chart (safe)
    col = 'Employment Type'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    # Get theme-aware gradient
    deep_blue_scale = get_color_scale(theme)

    employment_type_fig = px.bar(vc, x='count', y=col, title='Jobs by Employment Type', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    employment_type_fig.update_layout(yaxis={'categoryorder': 'total ascending'}) # Descending order for h-bar
    # Apply visual highlighting
    apply_visual_highlighting(employment_type_fig, vc[col].tolist(), employment_types, is_pie=False)
    
    col = 'Work Mode'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    # Work Mode - Donut Chart
    work_mode_fig = px.pie(vc, values='count', names=col, title='Jobs by Work Mode', hole=0.5, color_discrete_sequence=px.colors.sequential.Blues_r)
    work_mode_fig.update_traces(textposition='inside', textinfo='percent+label', rotation=-45)
    # Apply visual highlighting
    apply_visual_highlighting(work_mode_fig, vc[col].tolist(), work_modes, is_pie=True)
    
    col = 'Career Level'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    career_level_fig = px.bar(vc, x='count', y=col, title='Jobs by Career Level', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    career_level_fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    # Apply visual highlighting
    apply_visual_highlighting(career_level_fig, vc[col].tolist(), career_levels, is_pie=False)

    col = 'Category'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().head(10).reset_index()
    vc.columns = [col, 'count']
    top_categories_fig = px.bar(vc, x='count', y=col, title='Top 10 Categories', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    top_categories_fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    # Apply visual highlighting
    apply_visual_highlighting(top_categories_fig, vc[col].tolist(), categories, is_pie=False)
    
    # Style all figures with dark theme and custom colors
    for fig in [employment_type_fig, work_mode_fig, career_level_fig, top_categories_fig]:
        # Calculate max value for x-axis range (add 20% margin to prevent label truncation)
        if fig == work_mode_fig:
            # Skip for donut chart
            pass
        else:
            # For bar charts, get max value and add margin
            max_val = max([trace.x.max() if hasattr(trace, 'x') and trace.x is not None and len(trace.x) > 0 else 0 for trace in fig.data])
            fig.update_layout(xaxis_range=[0, max_val * 1.2])  # 20% margin
        
        fig.update_layout(
            dragmode=False,
            template='plotly',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#001F3F', family='Inter'),
            title_font=dict(size=48, color='#001F3F'),
            xaxis_title=None,
            yaxis_title=None,
            coloraxis_showscale=False,
            xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False, tickfont=dict(size=22)),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
            hoverlabel=dict(
                bgcolor='#001F3F',
                font_size=13,
                font_family='Inter',
                font_color='white'  # Changed to white for better visibility
            )
        )
        fig.update_traces(
            marker=dict(
                line=dict(width=0)
            ),
            textposition='outside',
            textfont=dict(size=22, color='#001F3F'),
            hovertemplate='<span style="color:white; font-family:Inter;"><b>%{y}</b><br>Count: %{x}</span><extra></extra>'
        )
    
    return f"{total_jobs:,}", f"{total_companies:,}", f"{total_categories:,}", f"{avg_applicants:.1f}", remote_hybrid_pct, latest_date, employment_type_fig, work_mode_fig, career_level_fig, top_categories_fig

# Callbacks for City Map page
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
        search_term = search_text.strip().lower()
        search_cols = ['Company', 'City', 'Category', 'Job Title', 'Work Mode', 'Employment Type', 'Career Level', 'In_City']
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
    
    # Sort by count ascending so largest is at the top in the chart
    city_counts = city_counts.sort_values('count', ascending=True)

    # Custom Deep Blue Gradient
    # Get theme-aware gradient
    deep_blue_scale = get_color_scale(theme)

    city_bar_fig = px.bar(city_counts, x='count', y=col, title='Jobs by City', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    # Apply visual highlighting
    apply_visual_highlighting(city_bar_fig, city_counts[col].tolist(), cities, is_pie=False)
    
    # Dynamic height: min 400px, add 60px per city to make bars bigger (2x size)
    dynamic_height = max(500, len(city_counts) * 60)
    
    # Calculate max value for x-axis range (add 20% margin)
    max_count = city_counts['count'].max() if not city_counts.empty else 100
    
    city_bar_fig.update_layout(
        dragmode=False,
        height=dynamic_height,
        template='plotly',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#001F3F', family='Inter'),
        title_font=dict(size=48, color='#001F3F'),
        xaxis_title=None,
        yaxis_title=None,
        coloraxis_showscale=False,
        xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False, tickfont=dict(size=22), range=[0, max_count * 1.2]),
        yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
        hoverlabel=dict(
            bgcolor='#001F3F',
            font_size=13,
            font_family='Inter',
            font_color='white'
        )
    )
    city_bar_fig.update_traces(
        marker=dict(line=dict(width=0)),
        texttemplate='%{x}',
        textposition='outside',
        textfont=dict(color='#001F3F', size=18),
        hovertemplate='<span style="color:white; font-family:Inter;"><b>%{y}</b><br>Count: %{x}</span><extra></extra>'
    )
    
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
    
    # Determine map tiles based on dropdown
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
    else: # voyager or default
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
        
        # OPTIMIZATION: Use FastMarkerCluster for high performance with 7000+ points
        # This renders all individual points (preserving accuracy) but uses efficient JS clustering
        if not map_df.empty:
            # Prepare data for FastMarkerCluster with custom callback
            # We pass [lat, lon, popup_html, tooltip_text]
            map_data = []
            
            for _, row in map_df.iterrows():
                job_title = str(row['Job Title']).replace("'", "")
                company = str(row['Company']).replace("'", "")
                city = str(row['City'])
                in_city = str(row['In_City']) if pd.notna(row['In_City']) else ""
                
                job_link = str(row['Link']) if pd.notna(row['Link']) else "#"
                
                # Tooltip content (Rich HTML)
                # User requested: Bigger font, Job Title (Bold Black) -> Company -> City/In_City
                tooltip_html = f"""
                <div style="font-family: 'Inter', Arial, sans-serif; min-width: 200px; padding: 10px; border-radius: 12px;">
                    <div style="font-size: 16px; font-weight: 900; color: black; margin-bottom: 4px; line-height: 1.2;">{job_title}</div>
                    <div style="font-size: 15px; color: #333; font-weight: bold; margin-bottom: 2px;">{company}</div>
                    <div style="font-size: 14px; color: #0066CC; margin-bottom: 8px;">{city} {f'- {in_city}' if in_city else ''}</div>
                    <div style="font-size: 12px; color: #0066CC; font-weight: 800; border-top: 1px solid #eee; padding-top: 5px;">Click To Visit Wuzzuf.com ↗</div>
                </div>
                """
                
                # Pass Link instead of Popup HTML
                map_data.append([row['Latitude'], row['Longitude'], job_link, tooltip_html])
            
            # Custom JavaScript callback to create markers with tooltips and CLICK event
            callback = """
            function (row) {
                var marker = L.marker(new L.LatLng(row[0], row[1]));
                
                // Bind Tooltip (Rounded Rectangle on Hover)
                marker.bindTooltip(row[3], {
                    direction: 'top',
                    className: 'custom-map-tooltip',
                    opacity: 1,
                    offset: [0, -10]
                });
                
                // Click Event: Open Link
                marker.on('click', function() {
                    window.open(row[2], '_blank');
                });
                
                return marker;
            }
            """
            
            # Add FastMarkerCluster with callback
            FastMarkerCluster(
                data=map_data,
                callback=callback,
                name='Jobs'
            ).add_to(m)
            
    map_html = m.get_root().render()
    
    # Table with more columns from your data — only include columns that actually exist
    candidate_cols = ['Job Title', 'Company', 'City', 'Category', 'applicants', 'Work Mode', 'Link']
    present_cols = [c for c in candidate_cols if c in filtered_df.columns]
    
    table_data_df = filtered_df[present_cols].copy()
    
    # Create Markdown Link for Job Title
    if 'Link' in table_data_df.columns and 'Job Title' in table_data_df.columns:
        table_data_df['Job Title'] = table_data_df.apply(
            lambda x: f"[{x['Job Title']}]({x['Link']})" if x['Link'] and x['Link'] != '#' else x['Job Title'], 
            axis=1
        )
    
    # Tooltip Data
    tooltip_data = []
    for row in table_data_df.to_dict('records'):
        # Create a tooltip for each cell in the row
        row_tooltip = {}
        tooltip_content = f"""### {row.get('Job Title', 'N/A')}

**{row.get('Company', 'N/A')}**  
{row.get('City', 'N/A')} • {row.get('Category', 'N/A')}

_Click to visit Wuzzuf.com_"""
        for col in table_data_df.columns:
            row_tooltip[col] = {'value': tooltip_content, 'type': 'markdown'}
        tooltip_data.append(row_tooltip)

    table = dash_table.DataTable(
        id='jobs-table', # Added ID for callbacks
        data=table_data_df.to_dict('records'),
        columns=[
            {'name': i, 'id': i, 'presentation': 'markdown'} if i == 'Job Title' else {'name': i, 'id': i} 
            for i in table_data_df.columns if i != 'Link' # Hide raw Link column
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
            {
                'if': {'state': 'active'},
                'backgroundColor': 'rgba(0, 102, 204, 0.1)',
                'border': '1px solid #0066CC'
            },
            {
                'if': {'state': 'selected'},
                'backgroundColor': 'rgba(0, 102, 204, 0.1)',
                'border': '1px solid #0066CC'
            }
        ],
        css=[
            {
                'selector': '.dash-spreadsheet td:hover',
                'rule': 'color: #0066CC !important; font-weight: bold; cursor: pointer;'
            }
        ],
        tooltip_data=tooltip_data,
        tooltip_duration=None,
        page_action='native',
        page_size=10,
        sort_action='native',
        filter_action='native'
    )
    
    return f"{total_jobs_city:,}", top_city, f"{avg_jobs_per_city:.1f}", city_bar_fig, map_html, table


# Callbacks for Deep Analysis page
@app.callback(
    [Output('top-companies-chart', 'figure'),
     Output('education-level-chart', 'figure'),
     Output('skills-cloud', 'figure'),
     Output('experience-chart', 'figure'),
     Output('applicants-chart', 'figure'),
     Output('decomposition-tree', 'figure'),
     Output('deep-total-jobs-kpi', 'children'),
     Output('deep-total-applicants-kpi', 'children'),
     Output('deep-avg-exp-kpi', 'children'),
     Output('deep-avg-applicants-kpi', 'children'),
     Output('deep-top-career-kpi', 'children')],
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
     Input('global-search-bar', 'value'),
     Input('theme-store', 'data')],
    prevent_initial_call=False  # Allow initial call to populate charts
)
def update_deep_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme):
    """
    Deep Analysis callback - provides meaningful business insights:
    1. Company Performance (by total applicants)
    2. Experience Level Demand (bucketed)
    3. Top Skills in Demand
    4. Education Requirements (grouped)
    5. Company Hiring Intensity (avg applicants per posting)
    """
    filtered_df = df.copy()
    
    # Ensure Year Of Exp_Avg is numeric BEFORE filtering
    if 'Year Of Exp_Avg' in filtered_df.columns:
        filtered_df['Year Of Exp_Avg'] = pd.to_numeric(filtered_df['Year Of Exp_Avg'], errors='coerce')
        
    # Ensure posted is datetime
    if 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        
    # Ensure applicants is numeric
    if 'applicants' in filtered_df.columns:
        filtered_df['applicants'] = pd.to_numeric(filtered_df['applicants'], errors='coerce')
    
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
        # Handle NaNs: include them if range covers 0 (assuming NaN ~ 0 or unknown) OR exclude them?
        # For now, let's see if this is the culprit.
        # We'll include NaNs if min_exp is 0, otherwise exclude them.
        if min_exp == 0:
             filtered_df = filtered_df[((filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)) | (filtered_df['Year Of Exp_Avg'].isna())]
        else:
             filtered_df = filtered_df[(filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)]

    
    # Month filter
    if months and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]


    # Apply search text filter
    if search_text and search_text.strip():
        search_term = search_text.strip().lower()
        search_cols = ['Company', 'City', 'Category', 'Job Title', 'Work Mode', 'Employment Type', 'Career Level', 'In_City']
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for col in search_cols:
            if col in filtered_df.columns:
                mask |= filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False)
        filtered_df = filtered_df[mask]

    
    # Get color scale for theme
    deep_blue_scale = get_color_scale(theme)
        
    # Ensure Year Of Exp_Avg is numeric
    if 'Year Of Exp_Avg' in filtered_df.columns:
        filtered_df['Year Of Exp_Avg'] = pd.to_numeric(filtered_df['Year Of Exp_Avg'], errors='coerce')
    
    # Check if 'applicants' column exists, if not create a proxy or use count
    has_applicants = 'applicants' in filtered_df.columns
    if not has_applicants:
        # If applicants missing, we can't show "Total Applicants", but we can show "Job Postings"
        # We'll use a flag to adjust titles/metrics
        print("DEBUG: 'applicants' column missing. Using job counts.")
    
    # Helper function for empty state
    def create_empty_chart(title):
        fig = go.Figure()
        fig.add_annotation(
            text="No data for current filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color='#999', family='Inter')
        )
        fig.update_layout(
            dragmode=False,
            template='plotly',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#001F3F', family='Inter'),
            title=dict(text=title, font=dict(size=48, color='#001F3F')),
            xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False)
        )
        return fig
    
    # ========================================
    # CHART 1: Company Performance
    # ========================================
    if 'Company' in filtered_df.columns and not filtered_df.empty:
        if has_applicants:
            # Aggregate by company: total applicants, number of postings
            company_stats = filtered_df.groupby('Company').agg({
                'applicants': 'sum',
                'Job Title': 'count'
            }).reset_index()
            company_stats.columns = ['Company', 'primary_metric', 'postings']
            metric_name = 'Total Applicants'
            title = 'Top Companies by Total Applicants'
            company_stats['avg_metric'] = (company_stats['primary_metric'] / company_stats['postings']).round(1)
        else:
            # Fallback to postings count
            company_stats = filtered_df['Company'].value_counts().reset_index()
            company_stats.columns = ['Company', 'primary_metric']
            company_stats['postings'] = company_stats['primary_metric']
            metric_name = 'Job Postings'
            title = 'Top Companies by Job Postings'
            company_stats['avg_metric'] = 0 # Not applicable
            
        # Top 10 by primary metric, sorted descending
        top_companies = company_stats.nlargest(10, 'primary_metric').sort_values('primary_metric', ascending=True)  # Ascending for horizontal (highest at top)
        
        if not top_companies.empty:
            company_performance_fig = px.bar(
                top_companies, 
                x='primary_metric', 
                y='Company', 
                title=title,
                orientation='h',
                color='primary_metric',
                color_continuous_scale=deep_blue_scale
            )

            # Enhanced layout
            company_performance_fig.update_layout(
                height=600,  # Uniform height
                font=dict(color='#001F3F'),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=250, r=100, t=80, b=50),  # More space for labels
                showlegend=False,
                coloraxis_showscale=False,
                xaxis=dict(
                    fixedrange=True,
                    showticklabels=False,  # Hide axis numbers
                    showgrid=False,
                    title=None  # Remove axis title
                ),
                yaxis=dict(
                    fixedrange=True,
                    tickfont=dict(size=17),  # Y-axis label size
                    title=None  # Remove axis title
                ),
                dragmode=False,
                title_font=dict(size=24)
            )
            
            # Add data labels
            company_performance_fig.update_traces(
                texttemplate='%{x:,.0f}',
                textposition='outside',
                textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>' + 
                             ('Total Applicants: %{x:,.0f}<br>' if has_applicants else 'Job Postings: %{x:,.0f}<br>') +
                             '<extra></extra>',
                hoverlabel=dict(
                    bgcolor='#001F3F',
                    font_size=14,
                    font_family='Inter',
                    font_color='white'
                )
            )
        else:
            company_performance_fig = create_empty_chart(title)
    else:
        company_performance_fig = create_empty_chart('Top Companies')
    
    # ========================================
    # CHART 2: Experience Level Demand (Bucketed)
    # ========================================
    if 'Year Of Exp_Avg' in filtered_df.columns and not filtered_df.empty:
        # Define experience buckets
        def bucket_experience(years):
            if pd.isna(years):
                return 'Not Specified'
            if years < 1:
                return '0-1 years'
            elif years < 3:
                return '1-3 years'
            elif years < 5:
                return '3-5 years'
            elif years < 7:
                return '5-7 years'
            elif years < 10:
                return '7-10 years'
            else:
                return '10+ years'
        
        filtered_df['exp_bucket'] = filtered_df['Year Of Exp_Avg'].apply(bucket_experience)
        
        # Count by bucket
        exp_counts = filtered_df['exp_bucket'].value_counts().reset_index()
        exp_counts.columns = ['Experience Level', 'count']
        
        # Define order for buckets
        bucket_order = ['0-1 years', '1-3 years', '3-5 years', '5-7 years', '7-10 years', '10+ years', 'Not Specified']
        exp_counts['order'] = exp_counts['Experience Level'].apply(lambda x: bucket_order.index(x) if x in bucket_order else 999)
        exp_counts = exp_counts.sort_values('order').drop('order', axis=1)
        
        # Calculate percentage
        exp_counts['percentage'] = (exp_counts['count'] / exp_counts['count'].sum() * 100).round(1)
        
        if not exp_counts.empty:
            experience_buckets_fig = px.bar(
                exp_counts,
                x='count',
                y='Experience Level',
                title='Experience Level Demand',
                orientation='h',
                color='count',
                color_continuous_scale=deep_blue_scale
            )
            experience_buckets_fig.update_layout(
                height=600,
                font=dict(color='#001F3F'),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=250, r=100, t=80, b=50),
                showlegend=False,
                coloraxis_showscale=False,
                xaxis=dict(
                    fixedrange=True,
                    showticklabels=False,
                    showgrid=False,
                    title=None
                ),
                yaxis=dict(
                    fixedrange=True,
                    tickfont=dict(size=17),
                    title=None
                ),
                dragmode=False,
                title_font=dict(size=24)
            )
            
            # Add data labels and tooltips
            experience_buckets_fig.update_traces(
                texttemplate='%{x}',
                textposition='outside',
                textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>Jobs: %{x}<br>Percentage: %{customdata}%<extra></extra>',
                customdata=exp_counts['percentage'].values,
                hoverlabel=dict(
                    bgcolor='#001F3F',
                    font_size=14,
                    font_family='Inter',
                    font_color='white'
                )
            )
        else:
            experience_buckets_fig = create_empty_chart('Experience Level Demand')
    else:
        experience_buckets_fig = create_empty_chart('Experience Level Demand')
    
    # ========================================
    # CHART 3: Career Level by Average Years of Experience
    # ========================================
    if 'Career Level' in filtered_df.columns and 'Year Of Exp_Avg' in filtered_df.columns and not filtered_df.empty:
        # Calculate average years of experience for each career level
        career_exp = filtered_df.groupby('Career Level')['Year Of Exp_Avg'].mean().reset_index()
        career_exp.columns = ['Career Level', 'avg_experience']
        career_exp['avg_experience'] = career_exp['avg_experience'].round(1)
        
        # Count jobs per career level for additional context
        career_counts = filtered_df['Career Level'].value_counts().reset_index()
        career_counts.columns = ['Career Level', 'job_count']
        
        # Merge
        career_exp = career_exp.merge(career_counts, on='Career Level')
        
        # Sort by average experience ascending for horizontal (highest at top)
        career_exp = career_exp.sort_values('avg_experience', ascending=True)
        
        if not career_exp.empty:
            career_level_fig = px.bar(
                career_exp,
                x='avg_experience',
                y='Career Level',
                title='Career Level by Average Years of Experience',
                orientation='h',
                color='avg_experience',
                color_continuous_scale=deep_blue_scale
            )
            career_level_fig.update_layout(
                height=600,
                font=dict(color='#001F3F'),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=250, r=100, t=80, b=50),
                showlegend=False,
                coloraxis_showscale=False,
                xaxis=dict(
                    fixedrange=True,
                    showticklabels=False,
                    showgrid=False,
                    title=None
                ),
                yaxis=dict(
                    fixedrange=True,
                    tickfont=dict(size=17),
                    title=None
                ),
                dragmode=False,
                title_font=dict(size=24)
            )
            
            # Add data labels and tooltips
            career_level_fig.update_traces(
                texttemplate='%{x:.1f}',
                textposition='outside',
                textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>Avg Experience: %{x:.1f} years<br>Job Postings: %{customdata}<extra></extra>',
                customdata=career_exp['job_count'].values,
                hoverlabel=dict(
                    bgcolor='#001F3F',
                    font_size=14,
                    font_family='Inter',
                    font_color='white'
                )
            )
        else:
            career_level_fig = create_empty_chart('Career Level by Average Years of Experience')
    else:
        career_level_fig = create_empty_chart('Career Level by Average Years of Experience')
    
    # ========================================
    # CHART 4: Education Requirements (All Levels)
    # ========================================
    if 'education_level' in filtered_df.columns and not filtered_df.empty:
        edu_counts = filtered_df['education_level'].value_counts().reset_index()
        edu_counts.columns = ['Education Level', 'count']
        
        # Sort by count ascending for horizontal (highest at top)
        edu_counts = edu_counts.sort_values('count', ascending=True)
        
        # Calculate percentage
        edu_counts['percentage'] = (edu_counts['count'] / edu_counts['count'].sum() * 100).round(1)
        
        if not edu_counts.empty:
            # Use horizontal bar for better readability
            education_distribution_fig = px.bar(
                edu_counts,
                x='count',
                y='Education Level',
                title='Education Requirements',
                orientation='h',
                color='count',
                color_continuous_scale=deep_blue_scale
            )
            education_distribution_fig.update_layout(
                height=600,
                font=dict(color='#001F3F'),
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=250, r=100, t=80, b=50),
                showlegend=False,
                coloraxis_showscale=False,
                xaxis=dict(
                    fixedrange=True,
                    showticklabels=False,
                    showgrid=False,
                    title=None
                ),
                yaxis=dict(
                    fixedrange=True,
                    tickfont=dict(size=17),
                    title=None
                ),
                dragmode=False,
                title_font=dict(size=24)
            )
            
            # Add data labels and tooltips
            education_distribution_fig.update_traces(
                texttemplate='%{x}',
                textposition='outside',
                textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>Count: %{x}<br>Percentage: %{customdata}%<extra></extra>',
                customdata=edu_counts['percentage'].values,
                hoverlabel=dict(
                    bgcolor='#001F3F',
                    font_size=14,
                    font_family='Inter',
                    font_color='white'
                )
            )
        else:
            education_distribution_fig = create_empty_chart('Education Requirements')
    else:
        education_distribution_fig = create_empty_chart('Education Requirements')
    
    # ========================================
    # CHART 5: Company Hiring Intensity (Avg Applicants per Posting)
    # ========================================
    # ========================================
    # CHART 5: Company Hiring Intensity (Avg Applicants per Posting)
    # ========================================
    if 'Company' in filtered_df.columns and not filtered_df.empty and has_applicants:
        # Calculate average applicants per posting for each company
        company_intensity = filtered_df.groupby('Company').agg({
            'applicants': 'mean',
            'Job Title': 'count'
        }).reset_index()
        company_intensity.columns = ['Company', 'avg_applicants', 'postings']
        company_intensity['avg_applicants'] = company_intensity['avg_applicants'].round(1)
        
        # Top 10 by average applicants, sorted ascending for horizontal (highest at top)
        top_intensity = company_intensity.nlargest(10, 'avg_applicants').sort_values('avg_applicants', ascending=True)
        
        if not top_intensity.empty:
            hiring_intensity_fig = px.bar(
                top_intensity,
                x='avg_applicants',
                y='Company',
                title='Most Competitive Companies (Avg Applicants per Posting)',
                orientation='h',
                color='avg_applicants',
                color_continuous_scale=deep_blue_scale
            )
            hiring_intensity_fig.update_layout(
                height=600,
                font=dict(color='#001F3F'),
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=250, r=100, t=80, b=50),
                showlegend=False,
                coloraxis_showscale=False,
                xaxis=dict(
                    fixedrange=True,
                    showticklabels=False,
                    showgrid=False,
                    title=None
                ),
                yaxis=dict(
                    fixedrange=True,
                    tickfont=dict(size=17),
                    title=None
                ),
                dragmode=False,
                title_font=dict(size=24)
            )
            
            # Add data labels and tooltips
            hiring_intensity_fig.update_traces(
                texttemplate='%{x:.1f}',
                textposition='outside',
                textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>Avg Applicants: %{x:.1f}<br>Total Postings: %{customdata}<extra></extra>',
                customdata=top_intensity['postings'].values,
                hoverlabel=dict(
                    bgcolor='#001F3F',
                    font_size=14,
                    font_family='Inter',
                    font_color='white'
                )
            )
        else:
            hiring_intensity_fig = create_empty_chart('Most Competitive Companies (Avg Applicants per Posting)')
    else:
        if not has_applicants:
             hiring_intensity_fig = create_empty_chart('Applicants Data Not Available')
        else:
             hiring_intensity_fig = create_empty_chart('Most Competitive Companies (Avg Applicants per Posting)')
    
    # ========================================
    # DECOMPOSITION TREE (Sunburst Chart)
    # ========================================
    # TEMPORARILY DISABLED DUE TO PERFORMANCE ISSUES
    decomposition_tree_fig = create_empty_chart('Job Market Decomposition Tree (Temporarily Disabled)')
    
    # # Create hierarchical decomposition: Category → Company → City → In_City → Employment Type → Work Mode → Career Level
    # # Note: We'll limit depth to avoid overcrowding
    # if not filtered_df.empty:
    #     # Prepare data for sunburst - we need to create a path for each row
    #     # Hierarchy: Category → Company → City → In_City → Employment Type → Work Mode → Career Level
    #     
    #     # Select relevant columns and handle missing values
    #     hierarchy_cols = ['Category', 'Company', 'City', 'In_City', 'Employment Type', 'Work Mode', 'Career Level']
    #     available_cols = [col for col in hierarchy_cols if col in filtered_df.columns]
    #     
    #     if len(available_cols) >= 2:  # Need at least 2 levels for sunburst
    #         # Create a copy with only hierarchy columns
    #         sunburst_df = filtered_df[available_cols].copy()
    #         
    #         # Fill NaN values with 'Not Specified'
    #         for col in available_cols:
    #             sunburst_df[col] = sunburst_df[col].fillna('Not Specified')
    #         
    #         # Add a count column
    #         sunburst_df['count'] = 1
    #         
    #         # Group by all hierarchy levels and sum counts
    #         grouped = sunburst_df.groupby(available_cols, dropna=False)['count'].sum().reset_index()
    #         
    #         # Limit to top categories to avoid overcrowding (top 5 per level)
    #         # Get top 5 categories
    #         top_categories = filtered_df['Category'].value_counts().head(5).index.tolist() if 'Category' in filtered_df.columns else []
    #         if top_categories:
    #             grouped = grouped[grouped['Category'].isin(top_categories)]
    #         
    #         if not grouped.empty and len(grouped) > 1:
    #             decomposition_tree_fig = px.sunburst(
    #                 grouped,
    #                 path=available_cols,
    #                 values='count',
    #                 title='Job Market Decomposition Tree',
    #                 color='count',
    #                 color_continuous_scale=deep_blue_scale
    #             )
    #             
    #             decomposition_tree_fig.update_layout(
    #                 dragmode=False,
    #                 template='plotly',
    #                 paper_bgcolor='rgba(0,0,0,0)',
    #                 plot_bgcolor='rgba(0,0,0,0)',
    #                 font=dict(color='#001F3F', family='Inter'),
    #                 title_font=dict(size=48, color='#001F3F'),
    #                 hoverlabel=dict(
    #                     bgcolor='#001F3F',
    #                     font_size=13,
    #                     font_family='Inter',
    #                     font_color='white'
    #                 )
    #             )
    #             
    #             # Custom tooltip
    #             decomposition_tree_fig.update_traces(
    #                 hovertemplate='<span style="color:white; font-family:Inter;"><b>%{label}</b><br>Jobs: %{value}<br>%{percentParent} of parent<br>%{percentRoot} of total</span><extra></extra>'
    #             )
    #         else:
    #             decomposition_tree_fig = create_empty_chart('Job Market Decomposition Tree')
    #     else:
    #         decomposition_tree_fig = create_empty_chart('Job Market Decomposition Tree')
    # else:
    #     decomposition_tree_fig = create_empty_chart('Job Market Decomposition Tree')

    # ========================================
    # Apply consistent styling to all charts
    # ========================================
    # DISABLED FOR DEBUGGING
    # for fig in [company_performance_fig, education_distribution_fig, career_level_fig, experience_buckets_fig, hiring_intensity_fig, decomposition_tree_fig]:
    #     # Skip styling for empty charts (they are already styled by create_empty_chart)
    #     if not fig.data:
    #         continue
    #         
    #     fig.update_layout(
    #         dragmode=False,
    #         template='plotly',
    #         paper_bgcolor='rgba(0,0,0,0)',
    #         plot_bgcolor='rgba(0,0,0,0)',
    #         font=dict(color='#001F3F', family='Inter'),
    #         title_font=dict(size=48, color='#001F3F'),
    #         xaxis_title=None,
    #         yaxis_title=None,
    #         coloraxis_showscale=False,
    #         xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False, tickfont=dict(size=22)),
    #         yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
    #         hoverlabel=dict(
    #             bgcolor='#001F3F',
    #             font_size=13,
    #             font_family='Inter',
    #             font_color='white'
    #         )
    #     )
    #     
    #     # Add text labels for bar charts (if they have data)
    #     if fig.data and hasattr(fig.data[0], 'x') and fig.data[0].x is not None:
    #         fig.update_traces(textposition='outside', textfont=dict(size=22, color='#001F3F'))
    
    # ========================================
    # Calculate KPIs
    # ========================================
    total_jobs = len(filtered_df)
    total_applicants = int(filtered_df['applicants'].sum()) if 'applicants' in filtered_df.columns and filtered_df['applicants'].notna().any() else 0
    avg_exp = filtered_df['Year Of Exp_Avg'].mean() if 'Year Of Exp_Avg' in filtered_df.columns and filtered_df['Year Of Exp_Avg'].notna().any() else 0
    avg_applicants = filtered_df['applicants'].mean() if 'applicants' in filtered_df.columns and filtered_df['applicants'].notna().any() else 0
    top_career = filtered_df['Career Level'].value_counts().index[0] if 'Career Level' in filtered_df.columns and not filtered_df.empty else 'N/A'
    
    # Format KPIs
    total_jobs_kpi = f"{total_jobs:,}"
    total_applicants_kpi = f"{total_applicants:,}"
    avg_exp_kpi = f"{avg_exp:.1f} yrs"
    avg_applicants_kpi = f"{avg_applicants:.0f}"
    top_career_kpi = top_career
    
    # CRITICAL: Return order MUST match callback outputs exactly:
    # 1. top-companies-chart → company_performance_fig
    # 2. education-level-chart → education_distribution_fig  
    # 3. skills-cloud → career_level_fig (using this as placeholder)
    # 4. experience-chart → experience_buckets_fig
    # 5. applicants-chart → hiring_intensity_fig
    # 6. decomposition-tree → decomposition_tree_fig
    # 7-11. KPIs
    return (company_performance_fig, education_distribution_fig, career_level_fig, experience_buckets_fig, hiring_intensity_fig, decomposition_tree_fig,
            total_jobs_kpi, total_applicants_kpi, avg_exp_kpi, avg_applicants_kpi, top_career_kpi)

# Callbacks for Time Analysis page
@app.callback(
    [Output('time-jobs-kpi', 'children'),
     Output('time-growth-kpi', 'children'),
     Output('time-applicants-kpi', 'children'),
     Output('time-peak-day-kpi', 'children'),
     Output('month-day-line-chart', 'figure'),
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
     Input('sidebar-in-city-filter', 'value'),
     Input('sidebar-avg-exp-filter', 'value'),
     Input('sidebar-month-filter', 'value'),
     Input('global-search-bar', 'value'),
     Input('theme-store', 'data')]
)
def update_time_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme):
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
        
        # In-City filter
        if in_cities and 'In_City' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
        
        # Avg Years of Experience filter
        if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
            min_exp, max_exp = avg_exp_range[0], avg_exp_range[1]
            filtered_df = filtered_df[(filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)]
        
        # Month filter (applied before date range to avoid conflicts)
        if months and 'posted' in filtered_df.columns:
            filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
            filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]
        
        # Apply search text filter
        if search_text and search_text.strip():
            search_term = search_text.strip().lower()
            search_cols = ['Company', 'City', 'Category', 'Job Title', 'Work Mode', 'Employment Type', 'Career Level', 'In_City']
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
    # Custom Deep Blue Gradient
    deep_blue_scale = get_color_scale(theme)

    if not filtered_df['Month'].dropna().empty:
        month_df = filtered_df['Month'].value_counts().reset_index(name='count').rename(columns={'index': 'Month'}).sort_values('Month')
        month_bar_fig = px.bar(month_df, x='Month', y='count', title='Jobs by Month', color='count', color_continuous_scale=deep_blue_scale, text='count')
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
            dragmode=False,
            template='plotly',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#001F3F', family='Inter'),
            title_font=dict(size=51, color='#001F3F'),
            xaxis_title=None,
            yaxis_title=None,
            coloraxis_showscale=False,
            xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
            hoverlabel=dict(
                bgcolor='#001F3F',
                font_size=13,
                font_family='Inter',
                font_color='white'
            )
        )
        if fig == month_bar_fig:
             fig.update_layout(
                 xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
                 yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False)
             )
             fig.update_traces(textposition='outside', textfont=dict(size=22, color='#001F3F'))
        
        if fig == month_day_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Day: %{fullData.name}<br>Count: %{y}</span><extra></extra>')
        elif fig == applicants_trend_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Applicants: %{y:.1f}</span><extra></extra>')
        else:
            # Month bar chart
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Count: %{y}</span><extra></extra>')
    
    # Calculate KPIs for Time Analysis
    total_jobs_period = len(filtered_df)
    
    # MoM Growth
    mom_growth = "0%"
    if not filtered_df.empty and 'posted' in filtered_df.columns:
        try:
            current_month = filtered_df['posted'].max().month
            prev_month = current_month - 1 if current_month > 1 else 12
            current_count = len(filtered_df[filtered_df['posted'].dt.month == current_month])
            prev_count = len(filtered_df[filtered_df['posted'].dt.month == prev_month])
            if prev_count > 0:
                growth = ((current_count - prev_count) / prev_count) * 100
                mom_growth = f"{growth:+.1f}%"
            else:
                mom_growth = "N/A"
        except:
            mom_growth = "N/A"
            
    # Avg Applicants Trend (Last 30 days)
    avg_applicants_trend = "0"
    if 'applicants' in filtered_df.columns:
        avg_applicants_trend = f"{filtered_df['applicants'].mean():.1f}"
        
    # Peak Posting Day
    peak_day = "N/A"
    if 'Day' in filtered_df.columns and not filtered_df['Day'].dropna().empty:
        peak_day = filtered_df['Day'].value_counts().index[0]

    return f"{total_jobs_period:,}", mom_growth, avg_applicants_trend, peak_day, month_day_fig, month_bar_fig, applicants_trend_fig


# Callback for Skills Analysis page
@app.callback(
    [Output('total-skills-kpi', 'children'),
     Output('top-skill-kpi', 'children'),
     Output('avg-skills-kpi', 'children'),
     Output('skills-wordcloud', 'figure'),
     Output('skills-category-breakdown', 'figure'),
     Output('top-skills-bar', 'figure'),
     Output('skills-trend', 'figure'),
     Output('top-skill-cat-kpi', 'children')],
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
     Input('global-search-bar', 'value')]
)
def update_skills_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text):
    filtered_df = df.copy()
    
    # Apply all filters
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
    if in_cities and 'In_City' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
    if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
        min_exp, max_exp = avg_exp_range[0], avg_exp_range[1]
        filtered_df = filtered_df[(filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)]
    if months and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]
    if search_text and search_text.strip():
        search_term = search_text.strip().lower()
        search_cols = ['Company', 'City', 'Category', 'Job Title', 'Work Mode', 'Employment Type', 'Career Level', 'In_City']
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for col in search_cols:
            if col in filtered_df.columns:
                mask |= filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False, regex=False)
        filtered_df = filtered_df[mask]
    
    # Merge with skills data
    if not skills_df.empty and 'Job Title' in filtered_df.columns:
        # Get job titles from filtered dataset
        filtered_job_titles = filtered_df['Job Title'].unique().tolist()
        # Filter skills_df to only include skills for jobs in filtered dataset
        filtered_skills = skills_df[skills_df['Job Title'].isin(filtered_job_titles)].copy()
        
        # Collect all skills
        all_skills = filtered_skills['Skills'].dropna().tolist() if 'Skills' in filtered_skills.columns else []
    else:
        all_skills = []
    
    # Calculate KPIs
    unique_skills = len(set(all_skills)) if all_skills else 0
    top_skill = pd.Series(all_skills).value_counts().index[0] if all_skills else "N/A"
    avg_skills_per_job = round(len(all_skills) / len(filtered_df), 1) if len(filtered_df) > 0 else 0
    
    # Calculate Top Skill Category (Proxy using Job Category for now as Skill Category isn't in skills_df)
    # If skills_df had a category column, we would use that.
    top_skill_cat = filtered_df['Category'].value_counts().index[0] if 'Category' in filtered_df.columns and not filtered_df.empty else "N/A"
    
    # Skills Word Cloud (using Treemap for interactive word cloud effect)
    if all_skills:
        skill_counts = pd.Series(all_skills).value_counts().head(30).reset_index()
        skill_counts.columns = ['skill', 'count']
        wordcloud_fig = px.treemap(
            skill_counts,
            path=['skill'],
            values='count',
            title='Top 30 Skills (Word Cloud)',
            color='count',
            color_continuous_scale='Blues'
        )
    else:
        wordcloud_fig = px.treemap(pd.DataFrame({'skill': [], 'count': []}), path=['skill'], values='count', title='Top 30 Skills (Word Cloud)')
    
    # Skills by Category Breakdown
    if not skills_df.empty and 'Category' in skills_df.columns and all_skills:
        # Filter skills_df for the filtered job titles
        filtered_job_titles = filtered_df['Job Title'].unique().tolist() if 'Job Title' in filtered_df.columns else []
        filtered_skills_cat = skills_df[skills_df['Job Title'].isin(filtered_job_titles)].copy()
        
        if not filtered_skills_cat.empty and 'Category' in filtered_skills_cat.columns:
            category_counts = filtered_skills_cat.groupby('Category').size().reset_index(name='count')
            category_breakdown_fig = px.pie(
                category_counts,
                values='count',
                names='Category',
                title='Skills Distribution by Category'
            )
        else:
            category_breakdown_fig = px.pie(pd.DataFrame({'Category': [], 'count': []}), values='count', names='Category', title='Skills Distribution by Category')
    else:
        category_breakdown_fig = px.pie(pd.DataFrame({'Category': [], 'count': []}), values='count', names='Category', title='Skills Distribution by Category')
    
    # Top 15 Skills Bar Chart
    if all_skills:
        top_skills = pd.Series(all_skills).value_counts().head(15).reset_index()
        top_skills.columns = ['skill', 'count']
        top_skills_fig = px.bar(
            top_skills,
            x='count',
            y='skill',
            orientation='h',
            title='Top 15 Most Demanded Skills',
            color='count',
            color_continuous_scale=[(0, '#00C9FF'), (1, '#001f3f')],
            text='count'
        )
    else:
        top_skills_fig = px.bar(pd.DataFrame({'skill': [], 'count': []}), x='count', y='skill', orientation='h', title='Top 15 Most Demanded Skills')
    
    # Skills Trend Over Time
    if 'posted' in filtered_df.columns and all_skills:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df['Month'] = filtered_df['posted'].dt.to_period('M').astype(str)
        
        # Count skills per month
        skill_trend_data = []
        for idx, row in filtered_df.iterrows():
            month = row.get('Month')
            if pd.notna(month):
                for i in range(11):
                    skill_col = f'Skill{i}'
                    if skill_col in row and pd.notna(row[skill_col]):
                        skill_trend_data.append({'Month': month, 'Skill': row[skill_col]})
        
        if skill_trend_data:
            trend_df = pd.DataFrame(skill_trend_data)
            monthly_counts = trend_df.groupby('Month').size().reset_index(name='count')
            skills_trend_fig = px.line(
                monthly_counts,
                x='Month',
                y='count',
                title='Skills Demand Trend Over Time'
            )
        else:
            skills_trend_fig = px.line(pd.DataFrame({'Month': [], 'count': []}), x='Month', y='count', title='Skills Demand Trend Over Time')
    else:
        skills_trend_fig = px.line(pd.DataFrame({'Month': [], 'count': []}), x='Month', y='count', title='Skills Demand Trend Over Time')
    
    # Apply dark theme to all figures
    for fig in [wordcloud_fig, category_breakdown_fig, top_skills_fig, skills_trend_fig]:
        fig.update_layout(
            dragmode=False,
            template='plotly',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#001F3F', family='Inter'),
            title_font=dict(size=51, color='#001F3F'),
            xaxis_title=None,
            yaxis_title=None,
            coloraxis_showscale=False,
            xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False, tickfont=dict(size=22)),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
            hoverlabel=dict(
                bgcolor='#001F3F',
                font_size=13,
                font_family='Inter',
                font_color='white'
            )
        )
        
        # Force white text in tooltip using inline styles
        if fig == top_skills_fig:
            fig.update_traces(textposition='outside', textfont=dict(size=22, color='#001F3F'))
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{y}</b><br>Count: %{x}</span><extra></extra>')
        elif fig == category_breakdown_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}</span><extra></extra>')
        elif fig == skills_trend_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Count: %{y}</span><extra></extra>')
        elif fig == wordcloud_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{label}</b><br>Count: %{value}</span><extra></extra>')
    
    return f"{unique_skills:,}", top_skill, f"{avg_skills_per_job}", wordcloud_fig, category_breakdown_fig, top_skills_fig, skills_trend_fig, top_skill_cat


# THEME SWITCHER CALLBACK
# ============================================

@app.callback(
    [Output('theme-store', 'data'),
     Output('theme-toggle-btn', 'children')],
    Input('theme-toggle-btn', 'n_clicks'),
    State('theme-store', 'data'),
    prevent_initial_call=True
)
def toggle_theme(n_clicks, current_theme):
    """Toggle between light and dark themes"""
    # Initialize theme if not set
    if not current_theme:
        current_theme = 'light'
    
    if n_clicks and n_clicks > 0:
        # Toggle theme
        new_theme = 'dark' if current_theme == 'light' else 'light'
        
        # Update button text and icon
        if new_theme == 'dark':
            button_content = [html.Span("☀️", className='icon'), " Light Mode"]
        else:
            button_content = [html.Span("🌙", className='icon'), " Dark Mode"]
        
        return new_theme, button_content
    
    # Initial state
    button_content = [html.Span("🌙", className='icon'), " Dark Mode"]
    return current_theme or 'light', button_content


# Server-side callback to apply theme CSS classes
@app.callback(
    Output('theme-container', 'className'),
    Input('theme-store', 'data')
)
def apply_theme_class(theme):
    """Apply theme class to container"""
    if theme == 'dark':
        return 'dark-theme'
    return 'light-theme'





# ============================================
# CLICK-TO-FILTER CLIENTSIDE CALLBACKS
# ============================================

# Overview Page Charts
app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior: if already filtered by this value, clear it
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];  // Clear filter
        }
        return [clickedValue];  // Set filter
    }
    """,
    Output('sidebar-employment-type-filter', 'value', allow_duplicate=True),
    Input('employment-type-chart', 'clickData'),
    State('sidebar-employment-type-filter', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].label;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-work-mode-filter', 'value', allow_duplicate=True),
    Input('work-mode-chart', 'clickData'),
    State('sidebar-work-mode-filter', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-career-level-filter', 'value', allow_duplicate=True),
    Input('career-level-chart', 'clickData'),
    State('sidebar-career-level-filter', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-category-filter', 'value', allow_duplicate=True),
    Input('top-categories-chart', 'clickData'),
    State('sidebar-category-filter', 'value'),
    prevent_initial_call=True
)

# City Map Page Charts
app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-city-filter', 'value', allow_duplicate=True),
    Input('city-bar-chart', 'clickData'),
    State('sidebar-city-filter', 'value'),
    prevent_initial_call=True
)

# Deep Analysis Page Charts
app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-company-filter', 'value', allow_duplicate=True),
    Input('top-companies-chart', 'clickData'),
    State('sidebar-company-filter', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].label;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-education-filter', 'value', allow_duplicate=True),
    Input('education-level-chart', 'clickData'),
    State('sidebar-education-filter', 'value'),
    prevent_initial_call=True
)


if __name__ == '__main__':
    # new Dash versions use app.run()
    try:
        app.run(debug=True, host='127.0.0.1', port=8050)
    except TypeError:
        # fallback for older versions
        app.run_server(debug=True, host='127.0.0.1', port=8050)

