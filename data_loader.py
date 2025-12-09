import pandas as pd
import numpy as np
import os
import re
import json
import time
import requests
from datetime import datetime, timedelta

import sys

def load_real_data():
    """Load job data from Excel and normalize columns."""
    # path to your file; use relative path for portability
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, 'Jobs.xlsx')
    if not os.path.exists(path):
        print(f"Warning: File not found at {path}")
        return pd.DataFrame()
    
    df = pd.read_excel(path)
    
    # Rename columns to match expected names in the code
    column_mapping = {
        'Jobs Title': 'Job Title',
        'Date_Posted': 'posted',
    }
    df.rename(columns=column_mapping, inplace=True)

    # posted parsing
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

    # extract City from Location
    if 'City' not in df.columns:
        if 'location_2' in df.columns:
            df['City'] = df['location_2'].str.split(',').str[0].str.strip()
        elif 'Location' in df.columns:
            df['City'] = df['Location'].str.split(',').str[0].str.strip()
    else:
        if 'location_2' in df.columns:
             df['City'] = df['City'].fillna(df['location_2'].str.split(',').str[0].str.strip())

    # Create job_status
    if 'job_status' not in df.columns:
        if 'open_positions' in df.columns:
            df['job_status'] = df['open_positions'].apply(lambda x: 'Open' if x > 0 else 'Closed')
        else:
            df['job_status'] = 'Open'
            
    # Clean Link column
    if 'Link' in df.columns:
        df['Link'] = df['Link'].fillna('#').astype(str)
    else:
        df['Link'] = '#'
    
    # Normalize City column
    if 'City' in df.columns:
        df['City'] = df['City'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
            
    # Ensure In_City exists
    if 'In_City' not in df.columns and 'Location' in df.columns:
        df['In_City'] = df['Location'].str.split(',').str[0].str.strip()

    # Filter for Egypt only
    if 'Location_2' in df.columns:
        df = df[df['Location_2'].astype(str).str.contains('Egypt', case=False, na=False)]
    elif 'Location' in df.columns:
        df = df[df['Location'].astype(str).str.contains('Egypt', case=False, na=False)]
    
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

    # Hardcoded coordinates for major Egyptian cities
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

    # 1. First try to map from hardcoded dictionary
    df['temp_lat'] = np.nan
    df['temp_lon'] = np.nan

    if 'In_City' in df.columns:
         df['temp_lat'] = df['In_City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lat'))
         df['temp_lon'] = df['In_City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lon'))

    if 'City' in df.columns:
        mask_missing = df['temp_lat'].isna()
        df.loc[mask_missing, 'temp_lat'] = df.loc[mask_missing, 'City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lat'))
        df.loc[mask_missing, 'temp_lon'] = df.loc[mask_missing, 'City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lon'))

        if 'Latitude' not in df.columns: df['Latitude'] = np.nan
        if 'Longitude' not in df.columns: df['Longitude'] = np.nan

        df['Latitude'] = df['Latitude'].fillna(df['temp_lat'])
        df['Longitude'] = df['Longitude'].fillna(df['temp_lon'])
        
        df.drop(columns=['temp_lat', 'temp_lon'], inplace=True)

    # Add small jitter
    if 'Latitude' in df.columns and 'Longitude' in df.columns:
        df['Latitude'] = df['Latitude'] + np.random.uniform(-0.005, 0.005, size=len(df))
        df['Longitude'] = df['Longitude'] + np.random.uniform(-0.005, 0.005, size=len(df))

    # 2. If still missing, use cached geocoding results
    if 'City' in df.columns:
        cache = _load_cache(cache_path)
        do_geocode = os.environ.get('AUTO_GEOCODE', '').lower() in ('1', 'true', 'yes')
        
        missing_coords_mask = df['Latitude'].isna() | df['Longitude'].isna()
        missing_cities = df.loc[missing_coords_mask, 'City'].dropna().unique().tolist()
        
        if do_geocode and missing_cities:
            for city in missing_cities:
                if city in cache: continue
                try:
                    _geocode_city(city, cache, cache_path)
                except Exception: pass
            cache = _load_cache(cache_path)

    if 'City' not in df.columns:
        if 'location_2' in df.columns:
            df['City'] = df['location_2'].str.split(',').str[0].str.strip()
        elif 'Location' in df.columns:
            df['City'] = df['Location'].str.split(',').str[0].str.strip()
    else:
        if 'location_2' in df.columns:
             df['City'] = df['City'].fillna(df['location_2'].str.split(',').str[0].str.strip())

    # Create job_status
    if 'job_status' not in df.columns:
        if 'open_positions' in df.columns:
            df['job_status'] = df['open_positions'].apply(lambda x: 'Open' if x > 0 else 'Closed')
        else:
            df['job_status'] = 'Open'
            
    # Clean Link column
    if 'Link' in df.columns:
        df['Link'] = df['Link'].fillna('#').astype(str)
    else:
        df['Link'] = '#'
    
    # Normalize City column
    if 'City' in df.columns:
        df['City'] = df['City'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
            
    # Ensure In_City exists
    if 'In_City' not in df.columns and 'Location' in df.columns:
        df['In_City'] = df['Location'].str.split(',').str[0].str.strip()

    # Filter for Egypt only
    if 'Location_2' in df.columns:
        df = df[df['Location_2'].astype(str).str.contains('Egypt', case=False, na=False)]
    elif 'Location' in df.columns:
        df = df[df['Location'].astype(str).str.contains('Egypt', case=False, na=False)]
    
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

    # Hardcoded coordinates for major Egyptian cities
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

    # 1. First try to map from hardcoded dictionary
    df['temp_lat'] = np.nan
    df['temp_lon'] = np.nan

    if 'In_City' in df.columns:
         df['temp_lat'] = df['In_City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lat'))
         df['temp_lon'] = df['In_City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lon'))

    if 'City' in df.columns:
        mask_missing = df['temp_lat'].isna()
        df.loc[mask_missing, 'temp_lat'] = df.loc[mask_missing, 'City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lat'))
        df.loc[mask_missing, 'temp_lon'] = df.loc[mask_missing, 'City'].map(lambda x: egypt_cities_coords.get(str(x).strip(), {}).get('lon'))

        if 'Latitude' not in df.columns: df['Latitude'] = np.nan
        if 'Longitude' not in df.columns: df['Longitude'] = np.nan

        df['Latitude'] = df['Latitude'].fillna(df['temp_lat'])
        df['Longitude'] = df['Longitude'].fillna(df['temp_lon'])
        
        df.drop(columns=['temp_lat', 'temp_lon'], inplace=True)

    # Add small jitter
    if 'Latitude' in df.columns and 'Longitude' in df.columns:
        df['Latitude'] = df['Latitude'] + np.random.uniform(-0.005, 0.005, size=len(df))
        df['Longitude'] = df['Longitude'] + np.random.uniform(-0.005, 0.005, size=len(df))

    # 2. If still missing, use cached geocoding results
    if 'City' in df.columns:
        cache = _load_cache(cache_path)
        do_geocode = os.environ.get('AUTO_GEOCODE', '').lower() in ('1', 'true', 'yes')
        
        missing_coords_mask = df['Latitude'].isna() | df['Longitude'].isna()
        missing_cities = df.loc[missing_coords_mask, 'City'].dropna().unique().tolist()
        
        if do_geocode and missing_cities:
            for city in missing_cities:
                if city in cache: continue
                try:
                    _geocode_city(city, cache, cache_path)
                except Exception: pass
            cache = _load_cache(cache_path)

        if cache:
            def get_lat_from_cache(city):
                return cache.get(city, {}).get('lat')
            def get_lon_from_cache(city):
                return cache.get(city, {}).get('lon')
                
            df.loc[missing_coords_mask, 'Latitude'] = df.loc[missing_coords_mask, 'City'].apply(get_lat_from_cache)
            df.loc[missing_coords_mask, 'Longitude'] = df.loc[missing_coords_mask, 'City'].apply(get_lon_from_cache)

    return df

# Load dataframe once
try:
    df = load_real_data()
    print(f"[+] Loaded {len(df)} jobs")
except Exception as e:
    print(f"[!] Could not load data: {e}")
    # Create empty DataFrame with expected columns to prevent app crash
    df = pd.DataFrame(columns=[
        'Job Title', 'Company', 'Location', 'City', 'In_City', 'location_2',
        'Employment Type', 'Work Mode', 'Career Level', 'Category', 
        'Category 2', 'Category 3', 'Skills', 'Skill_List', 'education_level',
        'Year Of Exp', 'How Long Ago', 'posted', 'applicants', 'open_positions',
        'job_status', 'Link', 'Latitude', 'Longitude', 'Year Of Exp_Avg'
    ])
    
# Load Skills Data
try:
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(__file__)
        
    skills_path = os.path.join(base_dir, 'Skills_Cleaned_UnPivot.xlsx')
    if os.path.exists(skills_path):
        skills_df = pd.read_excel(skills_path)
        skills_df.rename(columns={'Jobs Title': 'Job Title'}, inplace=True) # Keep this line from original
        print(f"[+] Loaded {len(skills_df)} skills rows")
    else:
        print(f"[!] Skills file not found at {skills_path}")
        skills_df = pd.DataFrame(columns=['Job Title', 'Skills', 'Category'])
except Exception as e:
    print(f"[!] Error loading skills data: {e}")
    skills_df = pd.DataFrame(columns=['Job Title', 'Skills', 'Category'])
