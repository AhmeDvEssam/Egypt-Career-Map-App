# ============================================
# INTERACTIVE CHARTS - PYTHON IMPLEMENTATION
# Option C: Click-to-Filter, Better Tooltips, Zoom
# ============================================

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import plotly.express as px

# ============================================
# 1. ENHANCED TOOLTIP CONFIGURATION
# ============================================

def create_rich_tooltip(fig, data_column='count', label_column='Category'):
    """
    Create beautiful, informative tooltips with:
    - Bold labels
    - Values with formatting
    - Percentage of total
    - Click instruction
    """
    total = data_column.sum()

    fig.update_traces(
        hovertemplate='<b style="font-size:16px">%{label}</b><br>' +
                      '<span style="color:#00CCFF">Count:</span> <b>%{value:,}</b><br>' +
                      '<span style="color:#3399FF">Percentage:</span> <b>%{customdata:.1f}%</b><br>' +
                      '<i style="font-size:12px; color:#9CA3AF">Click to filter</i>' +
                      '<extra></extra>',
        customdata=[(val/total*100) for val in data_column],
        hoverlabel=dict(
            bgcolor='rgba(10, 25, 41, 0.98)',
            font_size=16,
            font_family='Inter',
            font_color='white',
            bordercolor='rgba(0, 102, 204, 0.6)',
            align='left'
        )
    )
    return fig


# ============================================
# 2. CLICK-TO-FILTER FUNCTIONALITY
# ============================================

# Add a dcc.Store to track clicked filters
# In your layout, add:
# dcc.Store(id='chart-filter-store', data={}),

@app.callback(
    Output('chart-filter-store', 'data'),
    [
        Input('employment-type-chart', 'clickData'),
        Input('work-mode-chart', 'clickData'),
        Input('career-level-chart', 'clickData'),
        Input('top-categories-chart', 'clickData'),
        Input('top-companies-chart', 'clickData')
    ],
    State('chart-filter-store', 'data'),
    prevent_initial_call=True
)
def update_chart_filters(emp_click, work_click, career_click, cat_click, comp_click, current_filters):
    """
    Capture clicks on ANY chart and store the filter
    """
    ctx = callback_context

    if not ctx.triggered:
        return current_filters or {}

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Initialize filters dict if empty
    if not current_filters:
        current_filters = {}

    # Map chart IDs to filter keys
    chart_filter_map = {
        'employment-type-chart': ('employment_type', emp_click),
        'work-mode-chart': ('work_mode', work_click),
        'career-level-chart': ('career_level', career_click),
        'top-categories-chart': ('category', cat_click),
        'top-companies-chart': ('company', comp_click)
    }

    if trigger_id in chart_filter_map:
        filter_key, click_data = chart_filter_map[trigger_id]

        if click_data:
            # Extract the clicked value (works for both x and y axis)
            clicked_value = click_data['points'][0].get('y') or click_data['points'][0].get('x')
            current_filters[filter_key] = clicked_value

    return current_filters


# ============================================
# 3. APPLY CHART FILTERS TO DATA
# ============================================

@app.callback(
    [Output('total-jobs-kpi', 'children'),
     Output('total-companies-kpi', 'children'),
     Output('employment-type-chart', 'figure'),
     Output('work-mode-chart', 'figure'),
     Output('career-level-chart', 'figure'),
     Output('top-categories-chart', 'figure'),
     Output('chart-active-filter-display', 'children')],  # Shows active filter banner
    [Input('chart-filter-store', 'data'),
     Input('sidebar-company-filter', 'value'),
     Input('sidebar-city-filter', 'value')],
    # ... add all your other sidebar filters
)
def update_with_chart_filters(chart_filters, companies, cities, *other_filters):
    """
    Apply both sidebar filters AND chart click filters
    """
    filtered_df = df.copy()

    # Apply sidebar filters first
    if companies:
        filtered_df = filtered_df[filtered_df['Company'].isin(companies)]
    if cities:
        filtered_df = filtered_df[filtered_df['City'].isin(cities)]

    # Apply chart click filters
    active_chart_filter = None
    if chart_filters:
        if 'employment_type' in chart_filters:
            filtered_df = filtered_df[filtered_df['Employment Type'] == chart_filters['employment_type']]
            active_chart_filter = f"📊 Filtered by: {chart_filters['employment_type']}"

        if 'work_mode' in chart_filters:
            filtered_df = filtered_df[filtered_df['Work Mode'] == chart_filters['work_mode']]
            active_chart_filter = f"📊 Filtered by: {chart_filters['work_mode']}"

        if 'career_level' in chart_filters:
            filtered_df = filtered_df[filtered_df['Career Level'] == chart_filters['career_level']]
            active_chart_filter = f"📊 Filtered by: {chart_filters['career_level']}"

        if 'category' in chart_filters:
            filtered_df = filtered_df[filtered_df['Category'] == chart_filters['category']]
            active_chart_filter = f"📊 Filtered by: {chart_filters['category']}"

        if 'company' in chart_filters:
            filtered_df = filtered_df[filtered_df['Company'] == chart_filters['company']]
            active_chart_filter = f"📊 Filtered by: {chart_filters['company']}"

    # Calculate KPIs
    total_jobs = len(filtered_df)
    total_companies = filtered_df['Company'].nunique()

    # Create charts with enhanced tooltips
    # Employment Type Chart
    emp_data = filtered_df['Employment Type'].value_counts().reset_index()
    emp_data.columns = ['Employment Type', 'count']
    emp_fig = px.bar(emp_data, x='count', y='Employment Type', orientation='h')
    emp_fig = create_rich_tooltip(emp_fig, emp_data['count'], emp_data['Employment Type'])
    emp_fig = apply_interactive_styling(emp_fig, 'Jobs by Employment Type')

    # Work Mode Chart
    work_data = filtered_df['Work Mode'].value_counts().reset_index()
    work_data.columns = ['Work Mode', 'count']
    work_fig = px.bar(work_data, x='count', y='Work Mode', orientation='h')
    work_fig = create_rich_tooltip(work_fig, work_data['count'], work_data['Work Mode'])
    work_fig = apply_interactive_styling(work_fig, 'Jobs by Work Mode')

    # Create active filter banner
    filter_banner = None
    if active_chart_filter:
        filter_banner = html.Div([
            html.Span(active_chart_filter, style={'marginRight': '10px'}),
            html.Button('✕', id='clear-chart-filter', className='close-btn', n_clicks=0)
        ], className='chart-active-filter')

    return (
        total_jobs, total_companies,
        emp_fig, work_fig, career_fig, cat_fig,
        filter_banner
    )


# ============================================
# 4. CLEAR CHART FILTER BUTTON
# ============================================

@app.callback(
    Output('chart-filter-store', 'data', allow_duplicate=True),
    Input('clear-chart-filter', 'n_clicks'),
    prevent_initial_call=True
)
def clear_chart_filter(n_clicks):
    """Clear the chart click filter"""
    if n_clicks:
        return {}
    return dash.no_update


# ============================================
# 5. INTERACTIVE CHART STYLING FUNCTION
# ============================================

def apply_interactive_styling(fig, title):
    """
    Apply styling that enhances interactivity:
    - Click feedback
    - Hover effects
    - Zoom/pan controls
    """
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, color='white', family='Inter', weight=700),
            x=0.5,
            xanchor='center'
        ),

        # Enable click events
        clickmode='event+select',

        # Show modebar (zoom, pan controls)
        modebar=dict(
            bgcolor='rgba(10, 25, 41, 0.9)',
            color='white',
            activecolor='#00CCFF'
        ),

        # Drag mode for better interaction
        dragmode='zoom',

        xaxis=dict(
            title='',
            tickfont=dict(size=16, color='white', family='Inter'),
            gridcolor='rgba(0, 102, 204, 0.1)',
            showgrid=True
        ),

        yaxis=dict(
            title='',
            tickfont=dict(size=16, color='white', family='Inter'),
            gridcolor='rgba(0, 102, 204, 0.1)',
            showgrid=True
        ),

        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', family='Inter'),
        margin=dict(l=20, r=20, t=60, b=20),

        # Hover settings
        hovermode='closest',
        hoverdistance=10
    )

    # Apply gradient colors and enable selection
    fig.update_traces(
        marker=dict(
            color=fig.data[0].x if hasattr(fig.data[0], 'x') else fig.data[0].y,
            colorscale=[
                [0, '#004C99'],
                [0.5, '#0066CC'],
                [1, '#00CCFF']
            ],
            line=dict(width=0),
            showscale=False
        ),
        # Enable selection
        selected=dict(marker=dict(opacity=1, line=dict(color='#00CCFF', width=3))),
        unselected=dict(marker=dict(opacity=0.5))
    )

    # Enable zoom, pan, reset tools
    config = {
        'displayModeBar': True,
        'modeBarButtonsToAdd': ['select2d', 'lasso2d'],
        'modeBarButtonsToRemove': ['toImage'],
        'displaylogo': False
    }

    return fig


# ============================================
# 6. ADD VISUAL FEEDBACK FOR CLICKS
# ============================================

# In your layout, wrap charts with interactive-chart class:

def create_interactive_chart(chart_id, title):
    """
    Wrapper for charts to add interactive features
    """
    return html.Div([
        # Active filter display (hidden by default)
        html.Div(id=f'{chart_id}-filter-display', className='chart-active-filter'),

        # The chart itself
        dcc.Loading(
            id=f'loading-{chart_id}',
            type='circle',
            color='#0066CC',
            children=[
                dcc.Graph(
                    id=chart_id,
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['toImage']
                    },
                    className='interactive-chart-graph'
                )
            ]
        ),

        # Zoom controls overlay
        html.Div([
            html.Button('+', className='zoom-btn', id=f'{chart_id}-zoom-in'),
            html.Button('−', className='zoom-btn', id=f'{chart_id}-zoom-out'),
            html.Button('⟲', className='zoom-btn', id=f'{chart_id}-reset', title='Reset zoom')
        ], className='chart-zoom-controls')

    ], className='interactive-chart', style={'position': 'relative', 'marginBottom': '20px'})


# ============================================
# 7. USAGE EXAMPLE IN LAYOUT
# ============================================

# In your overview_layout():
def overview_layout():
    return html.Div([
        html.H1('Overview', className='gradient-text'),

        # Store for chart filters
        dcc.Store(id='chart-filter-store', data={}),

        # Active filter banner container
        html.Div(id='chart-active-filter-display'),

        # KPIs
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6('Total Jobs'),
                html.H3(id='total-jobs-kpi')
            ]), className='glass-effect'), width=3),
            # ... other KPIs
        ]),

        # Interactive Charts
        dbc.Row([
            dbc.Col(create_interactive_chart('employment-type-chart', 'Employment Type'), width=6),
            dbc.Col(create_interactive_chart('work-mode-chart', 'Work Mode'), width=6),
        ]),

        dbc.Row([
            dbc.Col(create_interactive_chart('career-level-chart', 'Career Level'), width=6),
            dbc.Col(create_interactive_chart('top-categories-chart', 'Top Categories'), width=6),
        ])
    ])


# ============================================
# 8. DOUBLE-CLICK TO RESET FILTER
# ============================================

@app.callback(
    Output('chart-filter-store', 'data', allow_duplicate=True),
    [Input('employment-type-chart', 'relayoutData'),
     Input('work-mode-chart', 'relayoutData'),
     Input('career-level-chart', 'relayoutData'),
     Input('top-categories-chart', 'relayoutData')],
    State('chart-filter-store', 'data'),
    prevent_initial_call=True
)
def reset_on_double_click(emp_relay, work_relay, career_relay, cat_relay, current_filters):
    """
    Double-click on chart to clear its filter
    """
    ctx = callback_context

    if not ctx.triggered:
        return current_filters

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Check if double-click (autosize event)
    relay_data = ctx.triggered[0]['value']
    if relay_data and 'autosize' in str(relay_data):
        # Clear the filter for this chart
        chart_filter_map = {
            'employment-type-chart': 'employment_type',
            'work-mode-chart': 'work_mode',
            'career-level-chart': 'career_level',
            'top-categories-chart': 'category'
        }

        if trigger_id in chart_filter_map:
            filter_key = chart_filter_map[trigger_id]
            if current_filters and filter_key in current_filters:
                del current_filters[filter_key]
                return current_filters

    return dash.no_update


# ============================================
# IMPLEMENTATION SUMMARY
# ============================================

# What you get:
# 1. ✅ Click any bar → filters entire dashboard
# 2. ✅ Rich tooltips showing count + percentage + click instruction
# 3. ✅ Visual feedback (glow, border) on hover
# 4. ✅ Active filter banner showing what's filtered
# 5. ✅ Clear button to remove chart filter
# 6. ✅ Double-click chart to reset filter
# 7. ✅ Zoom/pan controls on hover
# 8. ✅ Loading states during updates
# 9. ✅ Selection highlighting
# 10. ✅ Beautiful modebar (zoom buttons)
