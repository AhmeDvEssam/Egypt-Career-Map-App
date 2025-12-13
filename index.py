from dash import html, dcc
import dash_bootstrap_components as dbc
from app_instance import app, server
from layouts.sidebar import create_sidebar

# Import callbacks to register them
import callbacks.general_callbacks
import callbacks.overview_callbacks
# import callbacks.city_map_callbacks  # OLD: Folium version
# import callbacks.city_map_callbacks_leaflet as city_map_callbacks  # NEW: Dash Leaflet
import callbacks.city_map_callbacks as city_map_callbacks  # Folium default
import callbacks.deep_analysis_callbacks
import callbacks.time_analysis_callbacks
import callbacks.skills_analysis_callbacks
import callbacks.clientside_callbacks

# Import Flask routes
import full_map_route

# Define the app layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='theme-store', data='light', storage_type='local'),
    dcc.Store(id='click-filter-store', data=None),
    
    html.Div(id='theme-container', children=[
        # Simple PC Navbar
        dbc.Navbar(
            dbc.Container([
                # Sidebar Toggle Button
                html.Button(
                    html.I(className="fas fa-bars"),
                    id='sidebar-toggle-btn',
                    className='sidebar-toggle-btn me-3',
                    n_clicks=0
                ),
                
                # Brand
                dbc.NavbarBrand("Hire Q", href="/", className="me-3"),
                
                # Search bar
                html.Div([
                    html.I(className="fas fa-search search-icon"),
                    dcc.Input(
                        id='global-search-bar',
                        type='text',
                        placeholder='Search jobs, skills, companies...',
                        className='google-search-input',
                        debounce=True
                    )
                ], className='google-search-bar google-search-bar-compact'),
                
                # Page links on the right
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Overview", href="/", active="exact")),
                    dbc.NavItem(dbc.NavLink("Map", href="/city-map", active="exact")),
                    dbc.NavItem(dbc.NavLink("Deep Analysis", href="/deep-analysis", active="exact")),
                    dbc.NavItem(dbc.NavLink("Time Analysis", href="/time-analysis", active="exact")),
                    dbc.NavItem(dbc.NavLink("Skills", href="/skills", active="exact")),
                    dbc.NavItem(
                        html.Button(
                            [html.Span("🌙", className='icon'), " Dark Mode"],
                            id='theme-toggle-btn',
                            className='theme-toggle-btn'
                        )
                    ),
                ], className="ms-auto", style={'marginRight': '40px'}, navbar=True),
            ], fluid=True),
            color="primary",
            dark=True,
            className="custom-navbar",
        ),
        
        # Sidebar Tab (Mobile/Toggle)
        html.Div(id='sidebar-tab', children=[
            html.I(className="fas fa-filter")
        ]),
        
        # Backdrop (Mobile)
        html.Div(id='sidebar-backdrop', className='sidebar-backdrop'),
        
        # Left Filter Sidebar
        create_sidebar(),
        
        # Page Content
        html.Div(id='page-content', className='content-container')
    ])
])

if __name__ == '__main__':
    # new Dash versions use app.run()
    try:
        app.run(debug=True, host='127.0.0.1', port=8050)
    except TypeError:
        # fallback for older versions
        app.run_server(debug=True, host='127.0.0.1', port=8050)
