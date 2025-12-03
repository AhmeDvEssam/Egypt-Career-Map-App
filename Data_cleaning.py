import pandas as pd
import re
from typing import Optional
import argparse
import logging
import unicodedata
from collections import Counter
from difflib import get_close_matches
from difflib import SequenceMatcher
import difflib
from datetime import datetime, timedelta
import numpy as np
try:
    from rapidfuzz import process as _rf_process, fuzz as _rf_fuzz  # optional, faster fuzzy matching
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    RAPIDFUZZ_AVAILABLE = False

# Skills that should keep numbers
SKILLS_WITH_NUMBERS = [
    '3D Animation', '3D Design', '3D Imaging', '3D Modeling', '3D Printing', 
    '3D Rendering', '3D Scanning', '3D Visualization', '4D BIM', '4G Network Management',
    '5G Technology', '5S Methodology', '6 Sigma Certification', '8D Problem Solving',
    'IPv6 Management', 'PostgreSQL 10+', 'Python 2/3', 'Wi-Fi 6 Configuration'
]

# Skills with dots, pluses, or special characters to preserve
PRESERVE_SPECIAL_CHARS = [
    'C#', '.Net', '.NET', '.NET Framework', 'ASP.NET', 'C++', 'C++11', 'C++14', 
    'C++17', 'C++20', 'F#', 'J#', 'Objective-C', 'Node.js', 'Express.js', 'React.js',
    'Vue.js', 'AngularJS', 'HTML/CSS', 'HTML5', 'CSS3', 'Sass/SCSS', 'PHP 7', 'PHP 8',
    'Python 3', 'SwiftUI', 'T-SQL', 'PL/SQL', 'CI/CD', 'REST API', 'Linux/Unix',
    'VB.NET', 'ASP.NET MVC', 'ASP.NET Core', 'Three.js', 'D3.js', 'Power BI',
    'Primavera P6', 'MS Project', 'Socket.io', 'Web3.js', 'SSL/TLS', 'OAuth2',
    '1C', '1C:Enterprise', 'Dynamics 365', 'UI/UX', 'Material-UI', 'GPT-3', 'GPT-4'
]

CATEGORY_LIST = [
    "IT/Software Development", "Marketing/PR/Advertising", "Business Development",
    "Accounting/Finance", "Analyst/Research", "Customer Service/Support", "R&D/Science",
    "Administration", "Operations/Management", "Logistics/Supply Chain",
    "Manufacturing/Production", "Human Resources", "Engineering - Telecom/Technology",
    "Other", "Sales/Retail", "Creative/Design/Art", "Installation/Maintenance/Repair",
    "Writing/Editorial", "Medical/Healthcare", "Engineering - Other", "Quality",
    "Engineering - Construction/Civil/Architecture", "Engineering - Mechanical/Electrical",
    "Purchasing/Procurement", "Engineering - Oil & Gas/Energy", "Legal",
    "Project/Program Management", "Hospitality/Hotels/Food Services", "Banking",
    "Pharmaceutical", "Tourism/Travel", "Media/Journalism/Publishing", "Strategy/Consulting",
    "Education/Teaching", "Fashion", "C-Level Executive/GM/Director", "Training/Instructor",
    "Sports and Leisure"
]

def browse_file():
    """Open file dialog to select file"""
    # Lazy import tkinter so the module can be imported in headless environments
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        print("GUI file dialog is not available in this environment.")
        return None

    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a file",
        filetypes=[("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
    )
    return file_path


def _safe_save_dataframe(df, output_path):
    """Save dataframe, retrying with timestamp on PermissionError."""
    try:
        if output_path.endswith('.csv'):
            df.to_csv(output_path, index=False)
        else:
            df.to_excel(output_path, index=False)
        print(f"✓ Main table saved: {output_path}")
        return output_path
    except PermissionError:
        print(f"⚠ Warning: Cannot save {output_path} (file may be open)")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = output_path.rsplit('.', 1)
        if len(parts) == 2:
            output_path_ts = f"{parts[0]}_{timestamp}.{parts[1]}"
        else:
            output_path_ts = f"{output_path}_{timestamp}"
        if output_path_ts.endswith('.csv'):
            df.to_csv(output_path_ts, index=False)
        else:
            df.to_excel(output_path_ts, index=False)
        print(f"✓ Main table saved with timestamp: {output_path_ts}")
        return output_path_ts

# Create lowercase sets for faster membership checks
PRESERVE_SPECIAL_SET = {s.lower() for s in PRESERVE_SPECIAL_CHARS}
SKILLS_WITH_NUMBERS_SET = {s.lower() for s in SKILLS_WITH_NUMBERS}

# Precompile regexes used heavily for performance
RE_RANGE = re.compile(r'^\s*(\d+)\s*-\s*(\d+)')
RE_PLUS = re.compile(r'^\s*(\d+)\s*\+')
RE_NUM = re.compile(r'(\d+)')


def is_preserved_skill(text):
    """Check if skill should preserve special characters"""
    if pd.isna(text):
        return False
    text_str = str(text).strip().lower()
    return text_str in PRESERVE_SPECIAL_SET

def remove_numbers_from_text(text):
    """Remove numbers from beginning/end unless it's a preserved skill"""
    if pd.isna(text) or text == '':
        return text
    
    text_str = str(text).strip()
    
    # Check if it's a preserved skill with numbers (substring match)
    low = text_str.lower()
    for skill in SKILLS_WITH_NUMBERS_SET:
        if skill in low:
            return text_str
    
    # Remove numbers from beginning and end
    text_str = re.sub(r'^\d+', '', text_str)
    text_str = re.sub(r'\d+$', '', text_str)
    return text_str.strip()

def remove_unwanted_words(text):
    """Remove unwanted words from beginning/end"""
    if pd.isna(text) or text == '':
        return text
    
    text_str = str(text).strip()
    unwanted = ['or', 'and', 'with', 'of', 'on', 'by', 'to']

    for word in unwanted:
        if text_str.lower().startswith(word + ' '):
            text_str = text_str[len(word)+1:].strip()
        if text_str.lower().endswith(' ' + word):
            text_str = text_str[:-len(word)-1].strip()
    
    return text_str

def clean_special_characters(text):
    """Remove special characters unless skill is preserved"""
    if pd.isna(text) or text == '':
        return text
    
    text_str = str(text).strip()
    
    if is_preserved_skill(text_str):
        return text_str
    # Compile regexes at module-level alternatives would be possible; keep simple here
    text_str = re.sub(r'^[,\-\\/\*#\$%•●▪·\.;"\)\(]+', '', text_str)
    text_str = re.sub(r'[,\-\\/\*#\$%•●▪·\.;"\)\(]+$', '', text_str)

    return text_str.strip()

def split_skills_by_delimiters(text):
    """Split skills by : or ; and return list"""
    if pd.isna(text) or text == '':
        return [text]
    
    text_str = str(text).strip()
    
    # Split by : or ;
    if ':' in text_str or ';' in text_str:
        parts = re.split(r'[:;]', text_str)
        return [p.strip() for p in parts if p.strip()]
    
    return [text_str]

def clean_parentheses(text):
    """Clean parentheses from text"""
    if pd.isna(text) or text == '':
        return text
    
    text_str = str(text).strip()
    
    # If entire text is in parentheses, remove them
    if text_str.startswith('(') and text_str.endswith(')'):
        return text_str[1:-1].strip()
    
    # Complete incomplete parentheses
    if '(' in text_str and ')' not in text_str:
        text_str += ')'
    
    return text_str

def proper_case(text):
    """Apply proper case: capitalize first letter, lowercase rest"""
    if pd.isna(text) or text == '':
        return text
    
    text_str = str(text).strip()
    
    if is_preserved_skill(text_str):
        return text_str
    
    return text_str.capitalize()

def skill_cleaning(df, interactive=True, unpivot_choice=None, pivot_choice=None):
    """Main skill cleaning function"""
    print("\n=== SKILL CLEANING STARTED ===\n")
    
    # Get skill columns
    skill_cols = [col for col in df.columns if col.startswith('Skill')]
    
    issues_found = []
    
    # Check for issues
    for col in skill_cols:
        for idx, val in df[col].items():
            if pd.notna(val):
                val_str = str(val).strip()

                # Check for unwanted words (case-insensitive)
                if any(val_str.lower().startswith(word.lower()) or val_str.lower().endswith(word.lower())
                       for word in ['Or', 'And', 'With', 'Of', 'On', 'By', 'To']):
                    issues_found.append(f"Unwanted words found in {col}")

                # Check for special characters at start
                if re.search(r'^[,\-\\/\*#\$%•●▪·\.;\"\)\(]', val_str):
                    issues_found.append(f"Special characters at start in {col}")
    
    if issues_found:
        print("Issues found:")
        for issue in set(issues_found[:10]):  # Show first 10 unique issues
            print(f"  - {issue}")
        if interactive:
            fix = input("\nDo you want to fix these issues? (yes/no): ").lower()
        else:
            fix = 'no' if unpivot_choice is None else unpivot_choice
        if fix != 'yes':
            print("Skipping fixes...")
            return df
    
    print("\nCleaning skills...")
    
    # Process each skill column
    for col in skill_cols:
        # Apply cleaning functions (vectorized where possible)
        df[col] = df[col].apply(remove_numbers_from_text)
        df[col] = df[col].apply(remove_unwanted_words)
        df[col] = df[col].apply(clean_special_characters)
        df[col] = df[col].apply(clean_parentheses)
        df[col] = df[col].apply(proper_case)
        df[col] = df[col].str.strip()
    
    print("Skills cleaned successfully!")
    
    # Ask about unpivoting
    if interactive:
        unpivot = input("\nDo you want to unpivot the skills? (yes/no): ").lower()
    else:
        unpivot = 'yes' if unpivot_choice else 'no'

    if unpivot == 'yes':
        if interactive:
            print("\nChoose column to pivot by:")
            print("1. Job Title")
            print("2. Category")
            choice = input("Enter choice (1 or 2): ")
        else:
            choice = '1' if (pivot_choice is None) or pivot_choice == 'job' else '2'

        pivot_col = 'Job Title' if choice == '1' else 'Category'

        # Get non-skill columns
        id_cols = [col for col in df.columns if not col.startswith('Skill')]

        # Unpivot
        df_melted = pd.melt(
            df,
            id_vars=id_cols,
            value_vars=skill_cols,
            var_name='Skill_Column',
            value_name='Skills'
        )

        # Remove empty skills
        df_melted = df_melted[df_melted['Skills'].notna()]
        df_melted = df_melted[df_melted['Skills'] != '']
        df_melted = df_melted.drop('Skill_Column', axis=1)

        print(f"\nSkills unpivoted by {pivot_col}!")
        return df_melted
    
    return df


def _normalize_skill_text(s: str) -> str:
    """Normalize a single skill string: unicode normalize, lowercase, remove punctuation
    normalize separators, remove excessive whitespace and common noise.
    """
    if s is None:
        return ""
    s = str(s)
    # remove control chars and normalize unicode
    s = unicodedata.normalize('NFKC', s)
    # lower
    s = s.lower()
    # replace common connectors
    s = s.replace('&', ' and ')
    s = s.replace('/', ' ')
    s = s.replace('\\', ' ')
    # remove punctuation except + (for c++, c# etc) and keep dots inside tokens
    s = re.sub(r"[\"'(),:;\[\]|<>?@#!$%^&*_~=]+", ' ', s)
    # collapse multiple spaces
    s = re.sub(r"\s+", ' ', s).strip()
    return s


def _cluster_and_map_skills(unique_skills, counts, cutoff=0.86):
    """Cluster skill variants into canonical representatives by frequency.

    Algorithm:
    - Sort unique skills by decreasing frequency.
    - Iterate top->down: for each skill not yet assigned, mark it as canonical
      and assign all close matches (difflib) above cutoff to it.

    Returns mapping dict: variant -> canonical
    """
    uniques = list(unique_skills)
    # build an index list used by get_close_matches
    remaining = set(uniques)
    mapping = {}
    # order by counts desc
    ordered = sorted(uniques, key=lambda x: -counts.get(x, 0))
    for rep in ordered:
        if rep not in remaining:
            continue
        # representative becomes the canonical form
        canonical = rep
        mapping[canonical] = canonical
        remaining.remove(canonical)
        # find close matches among remaining
        # get_close_matches returns sorted by closeness
        # check against list(remaining)
        if remaining:
            candidates = list(remaining)
            # use rapidfuzz if available for better scoring
            if RAPIDFUZZ_AVAILABLE:
                # rapidfuzz returns (match, score, idx)
                # score is 0-100, convert cutoff accordingly
                rf_matches = _rf_process.extract(canonical, candidates, scorer=_rf_fuzz.ratio, score_cutoff=int(cutoff * 100))
                for m, score, _ in rf_matches:
                    mapping[m] = canonical
                    if m in remaining:
                        remaining.remove(m)
            else:
                matches = get_close_matches(canonical, candidates, n=len(candidates), cutoff=cutoff)
                for m in matches:
                    mapping[m] = canonical
                    if m in remaining:
                        remaining.remove(m)
    # any leftover (not matched) map to themselves
    for left in list(remaining):
        mapping[left] = left
    return mapping


def skills_standardize(
    df,
    skills_column: str = 'Skill',
    output_clean_col: str = 'Skill_Clean',
    output_mapped_col: str = 'Skill_Mapped',
    output_source_col: str = 'Skill_Mapped_Source',
    cutoff: float = 0.86,
    export_report: str = None,
    overrides: dict = None,
    interactive: bool = False,
):
    """Standardize a skills column in-place and produce mapping columns.

    Strategy:
    - Normalize all skill strings to a cleaned text (`Skill_Clean`).
    - Build frequency counts over cleaned values.
    - Cluster variants using frequency-first fuzzy matching and map variants to canonical.
    - Apply optional overrides mapping (exact cleaned match -> canonical).
    - Write mapping report if export_report path provided.

    This function is vectorized at the level of unique values (efficient for large df
    with many repeated skills).
    """
    col = skills_column
    if col not in df.columns:
        raise KeyError(f"Column '{col}' not found in DataFrame")

    # Normalize
    df[output_clean_col] = df[col].fillna('').astype(str).map(_normalize_skill_text)

    # frequency counts over cleaned values
    counts = Counter(df[output_clean_col].values)
    unique_vals = list(counts.keys())

    # apply overrides first (if provided) — expects cleaned keys
    overrides = overrides or {}
    mapping = {}

    # build clusters and mapping for the remaining
    cluster_map = _cluster_and_map_skills(unique_vals, counts, cutoff=cutoff)

    # merge overrides
    for k, v in cluster_map.items():
        if k in overrides:
            mapping[k] = overrides[k]
        else:
            mapping[k] = cluster_map[k]

    # create mapped and source columns
    mapped = []
    source = []
    for orig_clean in df[output_clean_col]:
        if orig_clean == '':
            mapped.append('')
            source.append('empty')
            continue
        if orig_clean in overrides:
            mapped.append(overrides[orig_clean])
            source.append('override')
            continue
        mapped_val = mapping.get(orig_clean, orig_clean)
        if mapped_val == orig_clean:
            source.append('direct')
        else:
            source.append('clustered')
        mapped.append(mapped_val)

    df[output_mapped_col] = mapped
    df[output_source_col] = source

    # export report if requested (include raw examples and similarity score)
    if export_report:
        report_rows = []
        # build a map cleaned->examples (original raw variants)
        examples = df.groupby(output_clean_col)[skills_column].apply(lambda s: ', '.join(list(pd.unique(s.dropna()))[:3])).to_dict()

        def _sim(a, b):
            if RAPIDFUZZ_AVAILABLE:
                try:
                    return _rf_fuzz.ratio(a, b) / 100.0
                except Exception:
                    return SequenceMatcher(None, a, b).ratio()
            else:
                return SequenceMatcher(None, a, b).ratio()

        for variant, canon in mapping.items():
            cnt = counts.get(variant, 0)
            sample_raw = examples.get(variant, '')
            score = _sim(variant, canon) if variant and canon else 0.0
            report_rows.append((variant, sample_raw, canon, cnt, round(float(score), 3)))

        import csv
        with open(export_report, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['variant_clean', 'sample_raw_examples', 'canonical', 'count', 'similarity'])
            for row in sorted(report_rows, key=lambda r: -r[3]):
                w.writerow(row)

    return df

    return df


def load_skill_overrides(path: str):
    """Load mapping overrides from JSON or CSV. Returns dict of cleaned_variant -> canonical."""
    if not path:
        return {}
    path = str(path)
    try:
        if path.lower().endswith('.json'):
            import json
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # expect dict-like
            if isinstance(data, dict):
                return { _normalize_skill_text(k): v for k, v in data.items() }
            else:
                # try list of pairs
                out = {}
                for entry in data:
                    if isinstance(entry, dict) and 'variant' in entry and 'canonical' in entry:
                        out[_normalize_skill_text(entry['variant'])] = entry['canonical']
                return out
        else:
            import csv
            out = {}
            with open(path, newline='', encoding='utf-8') as f:
                r = csv.reader(f)
                headers = next(r, None)
                # If two columns assume variant,canonical
                for row in r:
                    if not row:
                        continue
                    if len(row) >= 2:
                        var = _normalize_skill_text(row[0])
                        can = row[1]
                        out[var] = can
            return out
    except Exception as e:
        print(f"⚠ Warning: failed to load overrides from {path}: {e}")
        return {}

def general_cleaning(df, interactive=True, howlong_choice=None, convert_avg_choice=None, map_category=False, map_column=None):
    """General cleaning function"""
    print("\n=== GENERAL CLEANING STARTED ===\n")
    
    # Trim all columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
    # Clean Company column
    if 'Company' in df.columns:
        df['Company'] = df['Company'].str.replace('-', '', regex=False).str.strip()
    
    # Transform "How Long Ago" to date
    if 'How Long Ago' in df.columns:
        if interactive:
            date_choice = input("Convert 'How Long Ago' to:\n1. Date only\n2. Date and time\nChoice: ")
        else:
            date_choice = str(howlong_choice) if howlong_choice in ('1', '2') else '1'

        def convert_time_ago(text):
            if pd.isna(text):
                return None

            now = datetime.now()
            text = str(text).lower()

            if 'minute' in text or 'min' in text:
                mins = int(re.search(r'\d+', text).group())
                return now - timedelta(minutes=mins)
            elif 'hour' in text:
                hours = int(re.search(r'\d+', text).group())
                return now - timedelta(hours=hours)
            elif 'day' in text:
                days = int(re.search(r'\d+', text).group())
                return now - timedelta(days=days)
            elif 'month' in text:
                months = int(re.search(r'\d+', text).group())
                return now - timedelta(days=months*30)

            return None

        df['Date Posted'] = df['How Long Ago'].apply(convert_time_ago)

        if date_choice == '1':
            df['Date Posted'] = pd.to_datetime(df['Date Posted']).dt.date

        print("Date conversion completed!")
    
    # Clean Years Of Exp: create a cleaned text column and optionally an average numeric column
    if 'Years Of Exp' in df.columns:
        # keep original column, produce a cleaned string column without ' of Exp'
        df['Years Of Exp_Clean'] = df['Years Of Exp'].astype(str).str.replace(' of Exp', '', regex=False)
        df['Years Of Exp_Clean'] = df['Years Of Exp_Clean'].str.replace('of Exp', '', regex=False)

        # Standardize format on the cleaned column
        df['Years Of Exp_Clean'] = df['Years Of Exp_Clean'].str.strip()
        df['Years Of Exp_Clean'] = df['Years Of Exp_Clean'].str.replace(r'\s+', ' ', regex=True)
        df['Years Of Exp_Clean'] = df['Years Of Exp_Clean'].str.replace(r'-\s*', '- ', regex=True)
        df['Years Of Exp_Clean'] = df['Years Of Exp_Clean'].str.replace(r'\+\s*', '+ ', regex=True)

        # Ask about converting to average (numeric) and store numeric in 'Avg Years Of Exp'
        if interactive:
            convert_avg = input("\nConvert Years Of Exp to average number? (yes/no): ").lower()
        else:
            convert_avg = 'yes' if convert_avg_choice else 'no'
        if convert_avg == 'yes':
            # Vectorized parsing using pandas string methods and precompiled regexes for performance
            s = df['Years Of Exp_Clean'].fillna('').astype(str)

            # Extract ranges
            range_df = s.str.extract(r'^\s*(\d+)\s*-\s*(\d+)', expand=True)
            # Convert to numeric and compute average where range present
            range_avg = None
            if not range_df.empty:
                range0 = pd.to_numeric(range_df[0], errors='coerce')
                range1 = pd.to_numeric(range_df[1], errors='coerce')
                range_avg = (range0 + range1) / 2
            else:
                range_avg = pd.Series([np.nan] * len(s), index=s.index)

            # Extract plus patterns like '1+'
            plus_df = s.str.extract(r'^\s*(\d+)\s*\+', expand=True)
            plus_num = pd.to_numeric(plus_df[0], errors='coerce')

            # Extract any single number as fallback
            single_num = pd.to_numeric(s.str.extract(r'(\d+)', expand=True)[0], errors='coerce')

            # Compose final avg: prefer range_avg, then plus_num, then single_num
            avg_series = range_avg.combine_first(plus_num).combine_first(single_num)

            df['Avg Years Of Exp'] = avg_series
            print("Average years calculated!")
    
    # Extract City from Location
    if 'Location' in df.columns:
        def extract_city(location):
            if pd.isna(location):
                return None
            
            parts = str(location).split(',')
            if len(parts) >= 2:
                return parts[-2].strip()  # Get second to last part (city)
            return parts[0].strip()
        
        df['City'] = df['Location'].apply(extract_city)
        print("City extracted from Location!")
    
    # Category mapping option
    cat_cols = [c for c in ['Category', 'Category 2', 'Category 3'] if c in df.columns]
    if cat_cols:
        if interactive:
            do_map = input("\nDo you want to run category mapping to canonical categories? (yes/no): ").lower()
            chosen_col = None
            if do_map == 'yes':
                print("Choose source column to map from:")
                for i, col in enumerate(cat_cols, 1):
                    print(f"{i}. {col}")
                sel = input("Enter choice number: ")
                try:
                    chosen_col = cat_cols[int(sel)-1]
                except Exception:
                    chosen_col = cat_cols[0]
                df = map_categories(df, chosen_col)
        else:
            if map_category:
                chosen_col = map_column if map_column in cat_cols else cat_cols[0]
                df = map_categories(df, chosen_col)

    return df


def map_categories(df, source_col: str, job_title_col: str = 'Job Title'):
    """Map free-text category values to the canonical CATEGORY_LIST.

    Returns df with columns 'Category_Mapped' and 'Category_Mapped_Source'.
    """
    print(f"\nMapping categories from column: {source_col}")

    # Build category options and lowercase versions
    cat_options = [c for c in CATEGORY_LIST]
    cat_options_lower = [c.lower() for c in cat_options]

    # Tokenize helper
    def tokenize(text: str):
        return set(re.findall(r"\w+", text.lower()))

    cat_token_sets = [tokenize(c) for c in cat_options]

    series = df.get(source_col, pd.Series([''] * len(df))).fillna('').astype(str)

    OTHERS = {'other', 'others', 'misc', 'n/a', ''}

    def find_mapping_for_string(v: str) -> tuple:
        """Return (matched_category or None, source_str) for a single string value."""
        if not v:
            return (None, None)
        s = str(v).strip()
        s_lower = s.lower()
        if s_lower in OTHERS:
            return (None, None)

        # fuzzy match on lowercase strings
        matches = difflib.get_close_matches(s_lower, cat_options_lower, n=1, cutoff=0.6)
        if matches:
            return (cat_options[cat_options_lower.index(matches[0])], 'direct_match')

        # token overlap
        v_tokens = tokenize(s)
        best_idx = -1
        best_score = 0
        for idx, toks in enumerate(cat_token_sets):
            score = len(v_tokens & toks)
            if score > best_score:
                best_score = score
                best_idx = idx
        if best_score > 0:
            return (cat_options[best_idx], 'token_overlap')

        return (None, None)

    # Map unique values first
    unique_vals = series.unique()
    val_map = {val: find_mapping_for_string(str(val)) for val in unique_vals}

    mapped = series.map(lambda x: val_map.get(x, (None, None))[0])
    src = series.map(lambda x: val_map.get(x, (None, None))[1])

    # For rows where source was 'Other' (or similar), try to use Category 2 / Category 3 per-row
    other_mask = series.str.lower().isin(OTHERS)
    if other_mask.any():
        for i in df[other_mask].index:
            replaced = False
            for alt_col in ['Category 2', 'Category 3']:
                if alt_col in df.columns:
                    alt_val = str(df.at[i, alt_col]).strip()
                    if not alt_val or alt_val.lower() in OTHERS:
                        continue
                    m, s_val = find_mapping_for_string(alt_val)
                    if m:
                        mapped.iat[i] = m
                        src.iat[i] = f'from_{alt_col}'
                        replaced = True
                        break
            if not replaced and job_title_col in df.columns:
                title_val = str(df.at[i, job_title_col]).strip()
                m, s_val = find_mapping_for_string(title_val)
                if m:
                    mapped.iat[i] = m
                    src.iat[i] = 'from_job_title'

    # Try alternate category columns for any remaining unmapped rows
    unmapped_mask = mapped.isna()
    if unmapped_mask.any():
        for alt_col in ['Category 2', 'Category 3']:
            if alt_col in df.columns:
                alt_series = df[alt_col].fillna('').astype(str)
                for i in df[unmapped_mask].index:
                    alt_val = alt_series.iat[i]
                    if not alt_val:
                        continue
                    m, s_val = find_mapping_for_string(alt_val)
                    if m:
                        mapped.iat[i] = m
                        src.iat[i] = f'from_{alt_col}'
                unmapped_mask = mapped.isna()
                if not unmapped_mask.any():
                    break

    # Last fallback: try Job Title for any still unmapped
    unmapped_mask = mapped.isna()
    if unmapped_mask.any() and job_title_col in df.columns:
        titles = df[job_title_col].fillna('').astype(str)
        for i in df[unmapped_mask].index:
            title = titles.iat[i]
            m, s_val = find_mapping_for_string(title)
            if m:
                mapped.iat[i] = m
                src.iat[i] = 'from_job_title'

    mapped = mapped.fillna('Other')
    src = src.fillna('inferred')

    df['Category_Mapped'] = mapped
    df['Category_Mapped_Source'] = src

    counts = df['Category_Mapped'].value_counts().head(10)
    print("Category mapping summary (top 10):")
    for k, v in counts.items():
        print(f"  - {k}: {v}")

    return df


def create_dimension_table(df):
    """Create dimension tables for data modeling"""
    print("\n=== DATA MODELING ===\n")
    
    dim_tables = {}
    dim_counter = 1
    
    while True:
        print(f"\nAvailable columns:")
        for idx, col in enumerate(df.columns, 1):
            print(f"{idx}. {col}")

        choice = input("\nEnter column number to create dimension table (or 'done' to finish): ")
        
        if choice.lower() == 'done':
            break
        
        try:
            col_idx = int(choice) - 1
            dim_column = df.columns[col_idx]

            # If the user selected 'Years Of Exp' and we have an Avg column, offer to use it
            if dim_column == 'Years Of Exp' and 'Avg Years Of Exp' in df.columns:
                use_avg = input(f"Use numeric 'Avg Years Of Exp' for dimension instead of '{dim_column}'? (yes/no): ").lower()
                if use_avg == 'yes':
                    dim_column = 'Avg Years Of Exp'
            
            # Ask for additional columns first
            additional_cols = []
            add_more = input(f"\nAdd more columns to {dim_column} dimension? (yes/no): ").lower()
            if add_more == 'yes':
                print("\nAvailable columns:")
                remaining_cols = [col for col in df.columns if col != dim_column]
                for idx, col in enumerate(remaining_cols, 1):
                    print(f"{idx}. {col}")
                
                add_choices = input("Enter column numbers (comma-separated): ").split(',')
                for add_choice in add_choices:
                    try:
                        add_col_idx = int(add_choice.strip()) - 1
                        add_col = remaining_cols[add_col_idx]
                        additional_cols.append(add_col)
                    except:
                        print(f"Invalid choice: {add_choice}")
            
            # Create dimension table with all columns at once
            cols_for_dim = [dim_column] + additional_cols
            dim_df = df[cols_for_dim].drop_duplicates().reset_index(drop=True)
            dim_df.insert(0, f'{dim_column}_ID', range(1, len(dim_df) + 1))
            
            print(f"\nDimension table shape: {dim_df.shape}")
            print(f"Original dataframe shape before merge: {df.shape}")
            
            # Replace in main table with ID using a proper merge
            # Create a mapping dataframe
            merge_cols = [dim_column] + additional_cols
            mapping_df = dim_df[merge_cols + [f'{dim_column}_ID']]
            
            # Merge to add the ID
            df = df.merge(mapping_df, on=merge_cols, how='left')
            
            print(f"Dataframe shape after merge: {df.shape}")
            
            # Drop the original columns
            df = df.drop(columns=merge_cols)
            
            dim_tables[f'Dim_{dim_column}'] = dim_df
            print(f"\nDimension table 'Dim_{dim_column}' created!")
            print(f"Final dataframe shape: {df.shape}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    return df, dim_tables

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Data cleaning utility')
    parser.add_argument('--file', '-f', help='Input file path (CSV or Excel)')
    parser.add_argument('--mode', choices=['skill', 'general'], help='Cleaning mode')
    parser.add_argument('--non-interactive', action='store_true', help='Run without interactive prompts')
    parser.add_argument('--unpivot', action='store_true', help='Unpivot skills (when using skill mode)')
    parser.add_argument('--pivot-col', choices=['job', 'category'], help='Pivot by job or category')
    parser.add_argument('--skills-column', help="Column name to standardize skills (default: 'Skills' or 'Skill')")
    parser.add_argument('--export-skill-report', help='Path to export skill mapping report CSV')
    parser.add_argument('--skills-cutoff', type=float, default=0.86, help='Fuzzy matching cutoff for skills clustering (0-1)')
    parser.add_argument('--skills-overrides', help='Path to JSON/CSV file with overrides mapping (variant -> canonical)')
    parser.add_argument('--use-rapidfuzz', action='store_true', help='Use rapidfuzz for fuzzy matching if available')
    parser.add_argument('--interactive-review', action='store_true', help='If interactive, open a quick review of mapping report and allow small overrides')
    parser.add_argument('--howlong-choice', choices=['1', '2'], help="How Long Ago conversion: 1=date only,2=date+time")
    parser.add_argument('--convert-years-avg', action='store_true', help='Convert Years Of Exp to average')
    parser.add_argument('--create-dims', action='store_true', help='Create dimension tables (non-interactive will skip)')
    parser.add_argument('--map-category', action='store_true', help='Map Category values to canonical categories')
    parser.add_argument('--map-column', choices=['Category', 'Category 2', 'Category 3'], help='Column to use for category mapping')
    parser.add_argument('--output', '-o', help='Output filename (optional)')
    args = parser.parse_args()

    interactive = not args.non_interactive

    print("=== DATA CLEANING SYSTEM ===\n")

    # Determine mode
    if args.mode:
        choice = '1' if args.mode == 'skill' else '2'
    elif interactive:
        print("Choose cleaning type:")
        print("1. Skill-Cleaning")
        print("2. General-Cleaning")
        choice = input("\nEnter choice (1 or 2): ")
    else:
        print("No mode provided in non-interactive mode. Defaulting to 'general'.")
        choice = '2'

    # Browse for file or use provided
    if args.file:
        file_path = args.file
    elif interactive:
        print("\nPlease select the file to clean...")
        file_path = browse_file()
    else:
        print("No input file provided. Use --file to specify a file in non-interactive mode.")
        return
    
    if not file_path:
        print("No file selected. Exiting...")
        return
    
    # Load file
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    print(f"\nFile loaded: {file_path}")
    print(f"Shape: {df.shape}")
    
    # Process based on choice
    if choice == '1':
        df = skill_cleaning(df, interactive=interactive, unpivot_choice=args.unpivot, pivot_choice=args.pivot_col)
        # After cleaning/unpivot, optionally run skills standardization
        if interactive:
            do_skills_std = input("\nDo you want to standardize/cluster skills into canonical values? (yes/no): ").lower()
        else:
            # if user passed any skills-specific args, run standardization
            do_skills_std = 'yes' if any([args.export_skill_report, args.skills_overrides, args.skills_column]) else 'no'

    if do_skills_std == 'yes':
            # determine skills column
            skills_col = args.skills_column if args.skills_column else ('Skills' if 'Skills' in df.columns else ('Skill' if 'Skill' in df.columns else None))
            if not skills_col:
                print("No skills column found to standardize. Skipping skills_standardize.")
            else:
                overrides = load_skill_overrides(args.skills_overrides) if args.skills_overrides else {}
                # determine whether to use rapidfuzz (if requested and available)
                use_rf = args.use_rapidfuzz and RAPIDFUZZ_AVAILABLE
                df = skills_standardize(
                    df,
                    skills_column=skills_col,
                    cutoff=args.skills_cutoff,
                    export_report=args.export_skill_report,
                    overrides=overrides,
                    interactive=interactive,
                )

                # If interactive review requested, allow small override edits and re-run mapping
                if interactive and args.interactive_review and args.export_skill_report:
                    # load report and ask user to provide simple overrides
                    try:
                        import pandas as _pd
                        report = _pd.read_csv(args.export_skill_report)
                        print('\nTop mapping suggestions (from report):')
                        display_count = min(20, len(report))
                        print(report[['variant_clean','sample_raw_examples','canonical','count','similarity']].head(display_count).to_string(index=False))
                        review = input('\nDo you want to add manual overrides before finalizing mappings? (yes/no): ').lower()
                        if review == 'yes':
                            print("Enter overrides one per line in the form: variant_clean -> canonical. Empty line to finish.")
                            manual = {}
                            while True:
                                line = input().strip()
                                if not line:
                                    break
                                if '->' in line:
                                    a, b = line.split('->', 1)
                                    manual[_normalize_skill_text(a.strip())] = b.strip()
                                    print(f"Recorded override: {a.strip()} -> {b.strip()}")
                                else:
                                    print("Invalid format, use 'variant -> canonical'")
                            if manual:
                                # re-run standardize with overrides
                                df = skills_standardize(
                                    df,
                                    skills_column=skills_col,
                                    cutoff=args.skills_cutoff,
                                    export_report=args.export_skill_report.replace('.csv', '_reviewed.csv') if args.export_skill_report else None,
                                    overrides=manual,
                                    interactive=interactive,
                                )
                                print('Applied manual overrides and re-exported reviewed report.')
                    except Exception as e:
                        print(f"⚠ Could not run interactive review: {e}")
    elif choice == '2':
        df = general_cleaning(
            df,
            interactive=interactive,
            howlong_choice=args.howlong_choice,
            convert_avg_choice=args.convert_years_avg,
            map_category=args.map_category,
            map_column=args.map_column,
        )
    else:
        print("Invalid choice!")
        return
    
    # Ask about data modeling
    if interactive:
        model = input("\nDo you want to create dimension tables? (yes/no): ").lower()
    else:
        model = 'yes' if args.create_dims else 'no'

    if model == 'yes':
        if interactive:
            df, dim_tables = create_dimension_table(df)
        else:
            print("Skipping interactive dimension creation in non-interactive mode.")
            dim_tables = {}
        
        # Save dimension tables
        print("\n=== SAVING DIMENSION TABLES ===")
        for dim_name, dim_df in dim_tables.items():
            try:
                output_path = file_path.replace('.', f'_{dim_name}.')
                
                # Try to save, handle permission errors
                try:
                    if output_path.endswith('.csv'):
                        dim_df.to_csv(output_path, index=False)
                    else:
                        dim_df.to_excel(output_path, index=False)
                    print(f"✓ Saved: {output_path}")
                except PermissionError:
                    print(f"⚠ Warning: Cannot save {output_path} (file may be open)")
                    # Try with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = output_path.replace('.', f'_{timestamp}.')
                    if output_path.endswith('.csv'):
                        dim_df.to_csv(output_path, index=False)
                    else:
                        dim_df.to_excel(output_path, index=False)
                    print(f"✓ Saved with timestamp: {output_path}")
            except Exception as e:
                print(f"✗ Error saving {dim_name}: {e}")
    
    # Save cleaned main file
    print("\n=== SAVING MAIN TABLE ===")
    print(f"Final dataframe shape: {df.shape}")
    
    # Generate output filename
    if args.output:
        output_path = args.output
    else:
        base_name = file_path.rsplit('.', 1)[0]
        extension = file_path.rsplit('.', 1)[1] if '.' in file_path else 'xlsx'
        output_path = f"{base_name}_cleaned.{extension}"
    
    # Check if file is too large for Excel
    if df.shape[0] > 1048576 or df.shape[1] > 16384:
        print(f"⚠ Warning: File too large for Excel format ({df.shape[0]} rows, {df.shape[1]} cols)")
        print("Saving as CSV instead...")
        output_path = f"{base_name}_cleaned.csv"
        try:
            _safe_save_dataframe(df, output_path)
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{base_name}_cleaned_{timestamp}.csv"
            _safe_save_dataframe(df, output_path)
    else:
        try:
            _safe_save_dataframe(df, output_path)
        except PermissionError:
            # _safe_save_dataframe will handle PermissionError and retry
            output_path = _safe_save_dataframe(df, output_path)
    
    print("\n=== CLEANING COMPLETED ===")
    print(f"\nFiles saved:")
    print(f"  - Main table: {output_path}")
    if model == 'yes' and dim_tables:
        print(f"  - Dimension tables: {len(dim_tables)} table(s)")

if __name__ == "__main__":
    main()


