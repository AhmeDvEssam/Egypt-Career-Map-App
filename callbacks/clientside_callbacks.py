from dash import Input, Output, State
from app_instance import app

# Overview Page Charts
app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior: if already filtered by this value, clear it
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];  // Clear filter
        }
        return [clickedValue];  // Set filter
    }
    """,
    Output('sidebar-employment-type-filter', 'value', allow_duplicate=True),
    Input('employment-type-chart', 'clickData'),
    State('sidebar-employment-type-filter', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].label;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-work-mode-filter', 'value', allow_duplicate=True),
    Input('work-mode-chart', 'clickData'),
    State('sidebar-work-mode-filter', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-career-level-filter', 'value', allow_duplicate=True),
    Input('career-level-chart', 'clickData'),
    State('sidebar-career-level-filter', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-category-filter', 'value', allow_duplicate=True),
    Input('top-categories-chart', 'clickData'),
    State('sidebar-category-filter', 'value'),
    prevent_initial_call=True
)

# City Map Page Charts
app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-city-filter', 'value', allow_duplicate=True),
    Input('city-bar-chart', 'clickData'),
    State('sidebar-city-filter', 'value'),
    prevent_initial_call=True
)

# Deep Analysis Page Charts
app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].y;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-company-filter', 'value', allow_duplicate=True),
    Input('top-companies-chart', 'clickData'),
    State('sidebar-company-filter', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(clickData, currentFilter) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return window.dash_clientside.no_update;
        }
        const clickedValue = clickData.points[0].label;
        
        // Toggle behavior
        if (currentFilter && currentFilter.length === 1 && currentFilter[0] === clickedValue) {
            return [];
        }
        return [clickedValue];
    }
    """,
    Output('sidebar-education-filter', 'value', allow_duplicate=True),
    Input('education-level-chart', 'clickData'),
    State('sidebar-education-filter', 'value'),
    prevent_initial_call=True
)
