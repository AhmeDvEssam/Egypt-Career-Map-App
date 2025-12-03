from dash import html, dcc
import dash_bootstrap_components as dbc
from data_loader import df
from datetime import datetime
import pandas as pd

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
