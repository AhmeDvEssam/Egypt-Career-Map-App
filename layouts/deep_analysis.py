from dash import html, dcc
import dash_bootstrap_components as dbc
from data_loader import df

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
