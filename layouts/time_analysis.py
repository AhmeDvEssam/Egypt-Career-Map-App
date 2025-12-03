from dash import html, dcc
import dash_bootstrap_components as dbc
from data_loader import df
import pandas as pd

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
