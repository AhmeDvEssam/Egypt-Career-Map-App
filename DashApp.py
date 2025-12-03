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

# ============================================
# SPARKLINE HELPER FUNCTIONS (NEW!)
# ============================================

def create_sparkline_figure(data_series, color='#0066CC'):
    """
    Create a mini sparkline chart (80x40px) for KPI trends.
    
    Args:
        data_series: list or pd.Series - last 7 days of data
        color: hex color for the line
    
    Returns:
        dcc.Graph with sparkline
    """
    if not data_series or len(data_series) < 2:
        return html.Div()  # Empty if insufficient data
    
    fig = go.Figure()
    
    # Add line trace with fill
    fig.add_trace(go.Scatter(
        y=data_series,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba(0,102,204,0.1)',
        hovertemplate='<b>Value: %{y:,.0f}</b><extra></extra>'
    ))
    
    # Minimal layout for tiny sparkline
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False, showgrid=False),
        yaxis=dict(visible=False, showgrid=False),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=40,
        dragmode=False
    )
    
    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': False, 'staticPlot': True},
        style={'width': '80px', 'height': '40px', 'display': 'inline-block', 'marginLeft': '10px'}
    )


def calculate_percentage_change(current, previous):
    """
    Calculate percentage change with icon and color.
    
    Returns:
        dict: {'icon': str, 'change': float, 'color': str}
    """
    if previous == 0 or pd.isna(previous):
        return {'icon': '➖', 'change': 0, 'color': '#999'}
    
    pct = ((current - previous) / previous) * 100
    
    if pct > 0:
        return {'icon': '📈', 'change': pct, 'color': '#00C896'}
    elif pct < 0:
        return {'icon': '📉', 'change': abs(pct), 'color': '#FF6B35'}
    else:
        return {'icon': '➖', 'change': 0, 'color': '#999'}


# [REST OF THE CODE REMAINS THE SAME UNTIL overview_layout() function]

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

# === REST OF CODE CONTINUES AS BEFORE UNTIL overview_layout() ===