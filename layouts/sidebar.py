from dash import html, dcc
import dash_bootstrap_components as dbc
from data_loader import df

def create_sidebar():
    return html.Div([
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
            
            # Job Status Filter
            html.Div([
                html.Label("Job Status"),
                dcc.Dropdown(
                    id='sidebar-job-status-filter',
                    options=[{'label': s, 'value': s} for s in df['job_status'].dropna().unique().tolist()] if 'job_status' in df.columns else [],
                    multi=True,
                    value=['Open'], # Default to 'Open' per user request
                    placeholder='Select Job Status'
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
        
    ], id='filter-sidebar', className='sidebar')
