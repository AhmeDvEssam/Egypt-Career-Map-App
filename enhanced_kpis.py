"""
Enhanced KPI Components with Sparklines
========================================
This module adds professional sparkline charts to KPIs showing trends over time.

Features:
- Mini trend charts beside KPI values
- Color-coded indicators (green for up, red for down)
- Percentage change from previous period
- Smooth animations

Author: Ahmed Essam
Date: December 2025
"""

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from dash import dcc, html
import dash_bootstrap_components as dbc


def create_sparkline(data_series, color='#0066CC', height=40):
    """
    Create a mini sparkline chart for KPI trends.
    
    Parameters:
    -----------
    data_series : list or pd.Series
        Time series data for the sparkline
    color : str
        Color of the line (default: blue)
    height : int
        Height of sparkline in pixels
    
    Returns:
    --------
    dcc.Graph : Plotly graph object with sparkline
    """
    
    if len(data_series) < 2:
        # Not enough data for sparkline
        return html.Div()
    
    # Create figure
    fig = go.Figure()
    
    # Add line
    fig.add_trace(go.Scatter(
        y=data_series,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba{tuple(list(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + [0.1])}',
        hovertemplate='<b>Value: %{y:.0f}</b><extra></extra>'
    ))
    
    # Minimal layout
    fig.update_layout(
        showlegend=False,
        xaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        dragmode=False
    )
    
    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': False},
        style={'width': '80px', 'height': f'{height}px', 'display': 'inline-block'}
    )


def calculate_trend_indicator(current_value, previous_value):
    """
    Calculate percentage change and direction indicator.
    
    Returns:
    --------
    dict : {
        'change': float (percentage change),
        'direction': str ('up' or 'down'),
        'icon': str (emoji icon),
        'color': str (CSS color)
    }
    """
    
    if previous_value == 0 or pd.isna(previous_value):
        return {
            'change': 0,
            'direction': 'neutral',
            'icon': '➖',
            'color': '#666'
        }
    
    change = ((current_value - previous_value) / previous_value) * 100
    
    if change > 0:
        return {
            'change': change,
            'direction': 'up',
            'icon': '📈',
            'color': '#00C896'
        }
    elif change < 0:
        return {
            'change': abs(change),
            'direction': 'down',
            'icon': '📉',
            'color': '#FF6B35'
        }
    else:
        return {
            'change': 0,
            'direction': 'neutral',
            'icon': '➖',
            'color': '#666'
        }


def create_enhanced_kpi_card(
    title, 
    value, 
    icon_class, 
    sparkline_data=None, 
    previous_value=None,
    subtitle=None
):
    """
    Create an enhanced KPI card with sparkline and trend indicator.
    
    Parameters:
    -----------
    title : str
        KPI title (e.g., "Total Jobs")
    value : str or int
        Current KPI value
    icon_class : str
        Font Awesome icon class (e.g., "fa-solid fa-briefcase")
    sparkline_data : list, optional
        Historical data for sparkline
    previous_value : float, optional
        Previous period value for comparison
    subtitle : str, optional
        Additional context text
    
    Returns:
    --------
    dbc.Col : Bootstrap column with enhanced KPI card
    """
    
    # Create trend indicator if previous value provided
    trend = None
    if previous_value is not None:
        current = float(str(value).replace(',', ''))
        trend = calculate_trend_indicator(current, previous_value)
    
    # Build card content
    card_content = [
        html.Div([
            html.I(className=icon_class)
        ], className='kpi-icon-box'),
        
        html.Div([
            html.Div(title, className='kpi-label-v2'),
            
            # Value with sparkline
            html.Div([
                html.Span(value, className='kpi-value-v2', style={'display': 'inline-block', 'marginRight': '10px'}),
                
                # Sparkline (if data provided)
                create_sparkline(sparkline_data) if sparkline_data and len(sparkline_data) > 1 else html.Div()
                
            ], style={'display': 'flex', 'alignItems': 'center'}),
            
            # Trend indicator (if previous value provided)
            html.Div([
                html.Span(trend['icon'], style={'marginRight': '5px', 'fontSize': '14px'}),
                html.Span(
                    f"{trend['change']:.1f}% vs last period",
                    style={
                        'fontSize': '12px',
                        'color': trend['color'],
                        'fontWeight': '600'
                    }
                )
            ], style={'marginTop': '5px'}) if trend else html.Div(),
            
            # Subtitle (if provided)
            html.Div(
                subtitle,
                style={
                    'fontSize': '11px',
                    'color': '#999',
                    'marginTop': '3px'
                }
            ) if subtitle else html.Div()
            
        ], className='kpi-content-box')
    ]
    
    return html.Div(card_content, className='kpi-card-v2 kpi-float enhanced-kpi')


def get_historical_kpi_data(df, kpi_type, groupby_column='posted', periods=7):
    """
    Extract historical KPI data for sparklines.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Main dataframe
    kpi_type : str
        Type of KPI ('count', 'sum', 'mean', 'unique')
    groupby_column : str
        Column to group by (usually date/time)
    periods : int
        Number of historical periods to include
    
    Returns:
    --------
    list : Historical values for sparkline
    """
    
    if groupby_column not in df.columns or df.empty:
        return []
    
    try:
        # Ensure datetime
        df = df.copy()
        df[groupby_column] = pd.to_datetime(df[groupby_column], errors='coerce')
        df = df.dropna(subset=[groupby_column])
        
        if df.empty:
            return []
        
        # Group by date and calculate metric
        if kpi_type == 'count':
            grouped = df.groupby(df[groupby_column].dt.date).size()
        elif kpi_type == 'mean':
            grouped = df.groupby(df[groupby_column].dt.date)['applicants'].mean()
        elif kpi_type == 'unique_companies':
            grouped = df.groupby(df[groupby_column].dt.date)['Company'].nunique()
        else:
            return []
        
        # Get last N periods
        if len(grouped) > periods:
            grouped = grouped.tail(periods)
        
        return grouped.tolist()
    
    except Exception as e:
        print(f"Error calculating historical KPI data: {e}")
        return []


# Example usage function
def create_overview_kpis_with_sparklines(df):
    """
    Create all Overview page KPIs with sparklines.
    
    Example implementation showing how to integrate sparklines.
    """
    
    # Calculate current values
    total_jobs = len(df)
    total_companies = df['Company'].nunique() if 'Company' in df.columns else 0
    
    # Get historical data for sparklines
    jobs_sparkline = get_historical_kpi_data(df, 'count', 'posted', periods=7)
    companies_sparkline = get_historical_kpi_data(df, 'unique_companies', 'posted', periods=7)
    
    # Calculate previous period values (7 days ago)
    if 'posted' in df.columns:
        df_copy = df.copy()
        df_copy['posted'] = pd.to_datetime(df_copy['posted'], errors='coerce')
        latest_date = df_copy['posted'].max()
        
        if pd.notna(latest_date):
            week_ago = latest_date - pd.Timedelta(days=7)
            df_previous = df_copy[df_copy['posted'] < week_ago]
            previous_jobs = len(df_previous) / 7  # Average per day
        else:
            previous_jobs = None
    else:
        previous_jobs = None
    
    # Create KPI cards
    kpis_row = dbc.Row([
        dbc.Col(
            create_enhanced_kpi_card(
                title="Total Jobs",
                value=f"{total_jobs:,}",
                icon_class="fa-solid fa-briefcase",
                sparkline_data=jobs_sparkline,
                previous_value=previous_jobs,
                subtitle="Last 7 days"
            ),
            width=4
        ),
        
        dbc.Col(
            create_enhanced_kpi_card(
                title="Total Companies",
                value=f"{total_companies:,}",
                icon_class="fa-solid fa-building",
                sparkline_data=companies_sparkline,
                subtitle="Unique employers"
            ),
            width=4
        ),
        
        # Add more KPIs...
        
    ], style={'marginBottom': '30px'})
    
    return kpis_row


# CSS Enhancement for sparkline KPIs
SPARKLINE_KPI_CSS = """
.enhanced-kpi {
    position: relative;
    overflow: visible;
}

.enhanced-kpi .kpi-value-v2 {
    transition: transform 0.3s ease;
}

.enhanced-kpi:hover .kpi-value-v2 {
    transform: scale(1.05);
}

.enhanced-kpi .plotly {
    opacity: 0.7;
    transition: opacity 0.3s ease;
}

.enhanced-kpi:hover .plotly {
    opacity: 1;
}

/* Trend indicator animation */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

.enhanced-kpi .trend-up,
.enhanced-kpi .trend-down {
    animation: pulse 2s infinite;
}
"""
