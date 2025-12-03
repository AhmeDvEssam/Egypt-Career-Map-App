from dash import Input, Output, State, html, dcc
import dash
from app_instance import app
from data_loader import df
from layouts.overview import overview_layout
from layouts.city_map import city_map_layout
from layouts.deep_analysis import deep_analysis_layout
from layouts.time_analysis import time_analysis_layout
from layouts.skills_analysis import skills_page_layout

# Callbacks for routing
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    # normalize pathname: handle None and trailing slashes
    if not pathname or pathname == '/':
        pathname = '/'
    path = pathname.rstrip('/') or '/'

    if path == "/":
        return overview_layout()
    elif path == "/city-map":
        return city_map_layout()
    elif path == "/deep-analysis":
        return deep_analysis_layout()
    elif path == "/time-analysis":
        return time_analysis_layout()
    elif path == "/skills":
        return skills_page_layout()
    return html.Div(["404 - Page not found"])

# Callback for Sidebar Pagination
@app.callback(
    [Output('filter-page-1', 'style'),
     Output('filter-page-2', 'style'),
     Output('more-filters-btn', 'className')],
    [Input('more-filters-btn', 'n_clicks'),
     Input('goto-page-1', 'n_clicks')]
)
def toggle_filter_pages(more_filters_clicks, goto_page_1_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return {'display': 'block'}, {'display': 'none'}, ''
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'more-filters-btn':
        return {'display': 'none'}, {'display': 'block'}, 'expanded'
    elif button_id == 'goto-page-1':
        return {'display': 'block'}, {'display': 'none'}, ''
    
    return {'display': 'block'}, {'display': 'none'}, ''

# Callback to Clear All Filters
@app.callback(
    [Output('sidebar-company-filter', 'value'),
     Output('sidebar-city-filter', 'value'),
     Output('sidebar-category-filter', 'value'),
     Output('sidebar-work-mode-filter', 'value'),
     Output('sidebar-employment-type-filter', 'value'),
     Output('sidebar-career-level-filter', 'value'),
     Output('sidebar-education-filter', 'value'),
     Output('sidebar-date-filter', 'start_date'),
     Output('sidebar-date-filter', 'end_date'),
     Output('sidebar-in-city-filter', 'value'),
     Output('sidebar-avg-exp-filter', 'value'),
     Output('sidebar-month-filter', 'value'),
     Output('global-search-bar', 'value')],
    [Input('clear-filters-btn', 'n_clicks')]
)
def clear_all_filters(n_clicks):
    if n_clicks:
        # Reset all values
        max_exp = int(df['Year Of Exp_Avg'].max()) if 'Year Of Exp_Avg' in df.columns and df['Year Of Exp_Avg'].notna().any() else 20
        return [], [], [], [], [], [], [], None, None, [], [0, max_exp], [], ""
    return dash.no_update

# THEME SWITCHER CALLBACK
@app.callback(
    [Output('theme-store', 'data'),
     Output('theme-toggle-btn', 'children')],
    Input('theme-toggle-btn', 'n_clicks'),
    State('theme-store', 'data'),
    prevent_initial_call=True
)
def toggle_theme(n_clicks, current_theme):
    """Toggle between light and dark themes"""
    # Initialize theme if not set
    if not current_theme:
        current_theme = 'light'
    
    if n_clicks and n_clicks > 0:
        # Toggle theme
        new_theme = 'dark' if current_theme == 'light' else 'light'
        
        # Update button text and icon
        if new_theme == 'dark':
            button_content = [html.Span("☀️", className='icon'), " Light Mode"]
        else:
            button_content = [html.Span("🌙", className='icon'), " Dark Mode"]
        
        return new_theme, button_content
    
    # Initial state
    button_content = [html.Span("🌙", className='icon'), " Dark Mode"]
    return current_theme or 'light', button_content

# Server-side callback to apply theme CSS classes
@app.callback(
    Output('theme-container', 'className'),
    Input('theme-store', 'data')
)
def apply_theme_class(theme):
    """Apply theme class to container"""
    if theme == 'dark':
        return 'dark-theme'
    return 'light-theme'
