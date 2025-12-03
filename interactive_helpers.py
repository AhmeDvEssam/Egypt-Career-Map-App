# ============================================
# INTERACTIVE CHARTS - HELPER FUNCTIONS
# ============================================

def create_rich_tooltip(fig, data_values, labels=None):
    """
    Create beautiful, informative tooltips with:
    - Bold labels
    - Values with formatting
    - Percentage of total
    - Click instruction
    """
    if len(data_values) == 0:
        return fig
        
    total = sum(data_values)
    if total == 0:
        return fig
        
    percentages = [(val/total*100) for val in data_values]
    
    fig.update_traces(
        customdata=percentages,
        hovertemplate='<b style="font-size:16px">%{label}</b><br>' +
                      '<span style="color:#00CCFF">Count:</span> <b>%{value:,}</b><br>' +
                      '<span style="color:#3399FF">Percentage:</span> <b>%{customdata:.1f}%</b><br>' +
                      '<i style="font-size:12px; color:#9CA3AF">🖱️ Click to filter</i>' +
                      '<extra></extra>',
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


def apply_interactive_styling(fig, title, is_dark_theme=False):
    """
    Apply styling that enhances interactivity:
    - Click feedback
    - Hover effects
    - Zoom/pan controls
    """
    text_color = 'white' if is_dark_theme else '#001F3F'
    bg_color = 'rgba(0,0,0,0)'
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=48, color=text_color, family='Inter', weight=700),
            x=0.5,
            xanchor='center'
        ),
        
        # Enable click events
        clickmode='event+select',
        
        # Drag mode for better interaction
        dragmode='zoom',
        
        template='plotly_dark' if is_dark_theme else 'plotly',
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font=dict(color=text_color, family='Inter'),
        margin=dict(l=20, r=20, t=60, b=20),
        
        # Hover settings
        hovermode='closest',
        hoverdistance=10,
        
        xaxis_title=None,
        yaxis_title=None,
        coloraxis_showscale=False,
        xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22, color=text_color)),
        yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22, color=text_color))
    )
    
    # Apply gradient colors and enable selection
    deep_blue_scale = [(0, '#00C9FF'), (1, '#001f3f')]
    
    fig.update_traces(
        marker=dict(
            colorscale=deep_blue_scale,
            line=dict(width=0),
            showscale=False
        ),
        textfont=dict(size=22, color=text_color),
        # Enable selection
        selected=dict(marker=dict(opacity=1, line=dict(color='#00CCFF', width=3))),
        unselected=dict(marker=dict(opacity=0.5))
    )
    
    return fig


def create_interactive_chart_wrapper(chart_id, title=''):
    """
    Wrapper for charts to add interactive features
    """
    return html.Div([
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
                        'modeBarButtonsToRemove': ['toImage', 'lasso2d']
                    },
                    className='interactive-chart-graph'
                )
            ]
        )
    ], className='interactive-chart', style={'position': 'relative', 'marginBottom': '20px'})
