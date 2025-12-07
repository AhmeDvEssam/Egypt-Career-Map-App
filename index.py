from dash import html, dcc
import dash_bootstrap_components as dbc
from app_instance import app, server
from layouts.sidebar import create_sidebar

# Import callbacks to register them
import callbacks.general_callbacks
import callbacks.overview_callbacks
import callbacks.city_map_callbacks
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
        # Mobile-Responsive Navbar
        dbc.Navbar(
            dbc.Container([
                # Left side: Sidebar toggle + Brand
                html.Div([
                    html.Button(
                        html.I(className="fas fa-bars"),
                        id='sidebar-toggle-btn',
                        className='sidebar-toggle-btn me-2',
                        n_clicks=0
                    ),
                    dbc.NavbarBrand("Hire Q", href="/", className="d-none d-sm-block ms-2"),
                    dbc.NavbarBrand("HQ", href="/", className="d-sm-none ms-2"),
                ], className='d-flex align-items-center'),
                
                # Mobile hamburger toggle for nav links
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                
                # Collapsible navigation
                dbc.Collapse(
                    dbc.Nav([
                        # Search bar (full width on mobile)
                        dbc.NavItem(
                            html.Div([
                                html.I(className="fas fa-search search-icon"),
                                dcc.Input(
                                    id='global-search-bar',
                                    type='text',
                                    placeholder='Search...',
                                    className='google-search-input',
                                    debounce=True
                                )
                            ], className='google-search-bar google-search-bar-compact my-2 my-lg-0'),
                            className='w-100 w-lg-auto'
                        ),
                        
                        # Navigation links
                        dbc.NavItem(dbc.NavLink("Overview", href="/", active="exact", className="nav-link-mobile")),
                        dbc.NavItem(dbc.NavLink("City Map", href="/city-map", active="exact", className="nav-link-mobile")),
                        dbc.NavItem(dbc.NavLink("Deep Analysis", href="/deep-analysis", active="exact", className="nav-link-mobile")),
                        dbc.NavItem(dbc.NavLink("Time Analysis", href="/time-analysis", active="exact", className="nav-link-mobile")),
                        dbc.NavItem(dbc.NavLink("Skills", href="/skills", active="exact", className="nav-link-mobile")),
                        
                        # Dark mode toggle
                        dbc.NavItem(
                            html.Button(
                                [html.Span("🌙", className='icon'), html.Span(" Dark Mode", className='d-lg-inline d-none')],
                                id='theme-toggle-btn',
                                className='theme-toggle-btn mt-2 mt-lg-0'
                            ),
                            className='ms-lg-2'
                        ),
                    ], className="ms-auto", navbar=True),
                    id="navbar-collapse",
                    is_open=False,
                    navbar=True,
                ),
            ], fluid=True),
            color="primary",
            dark=True,
            className="custom-navbar",
            sticky="top",
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
