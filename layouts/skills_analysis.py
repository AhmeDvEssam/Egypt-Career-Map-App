from dash import html, dcc
import dash_bootstrap_components as dbc

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
