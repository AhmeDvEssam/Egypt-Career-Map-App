import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from data_loader import skills_df

def filter_dataframe_by_search(df, search_text):
    """
    Filter the dataframe based on a global search text across ALL columns
    in both the main Jobs dataframe and the Skills dataframe.
    """
    if not search_text or not search_text.strip():
        return df
        
    search_term = search_text.strip().lower()
    
    # 1. Search in main Jobs dataframe (df)
    # Create a mask for all columns
    # Optimization: Select only object/string columns for string search to avoid errors
    string_cols = df.select_dtypes(include=['object', 'string']).columns
    mask_df = pd.Series([False] * len(df), index=df.index)
    
    for col in string_cols:
        mask_df |= df[col].astype(str).str.lower().str.contains(search_term, na=False, regex=False)
        
    # 2. Search in Skills dataframe (skills_df)
    matching_titles = set()
    if not skills_df.empty:
        skills_string_cols = skills_df.select_dtypes(include=['object', 'string']).columns
        skills_mask = pd.Series([False] * len(skills_df), index=skills_df.index)
        
        for col in skills_string_cols:
            skills_mask |= skills_df[col].astype(str).str.lower().str.contains(search_term, na=False, regex=False)
            
        matching_titles = set(skills_df.loc[skills_mask, 'Job Title'].unique())
        
    # 3. Combine results
    # Include rows where the search term was found in df OR the Job Title matches a skill search result
    final_mask = mask_df | df['Job Title'].isin(matching_titles)
    
    return df[final_mask]


def get_color_scale(theme):
    """
    Return PERFECT color scale based on theme.
    
    Light Mode: Professional Blue Gradient (Dark Blue → Bright Blue)
    Dark Mode: Vibrant Gradient (Deep Blue → Cyan → White for highest values)
    """
    if theme == 'dark':
        # Dark Mode: Deep Blue → Electric Cyan → Bright White
        # Creates beautiful contrast on dark backgrounds
        return [
            [0.0, '#1A4D7A'],    # Deep Blue (lowest values)
            [0.4, '#0080FF'],    # Electric Blue
            [0.7, '#00CCFF'],    # Bright Cyan
            [1.0, '#66E0FF']     # Light Cyan (highest values)
        ]
    else:
        # Light Mode: Professional Dark Blue → Sky Blue
        # Perfect for white backgrounds
        return [
            [0.0, '#002D5C'],    # Navy Blue (lowest values)
            [0.5, '#0066CC'],    # Professional Blue
            [1.0, '#3399FF']     # Sky Blue (highest values)
        ]

def apply_visual_highlighting(fig, counts, selected_items, is_pie=False):
    """
    Apply visual highlighting to charts based on selection.
    Selected items glow, non-selected dim out.
    
    Args:
        fig: Plotly figure object
        counts: List/Series of values used for coloring
        selected_items: List of currently selected items (names)
        is_pie: Boolean, true if chart is a pie/donut chart
    """
    if not selected_items:
        return

    # Enhanced colors for better visibility
    highlight_color = '#00E5FF'  # Electric Cyan for selection (pops on any background)
    dimmed_color = 'rgba(100, 100, 100, 0.25)'  # Very dim gray
    
    if is_pie:
        # For pie charts, update marker colors
        colors = [highlight_color if label in selected_items else dimmed_color 
                 for label in fig.data[0].labels]
        fig.update_traces(marker=dict(colors=colors))
        
        # Add glowing outline to selected slices
        line_width = [3 if label in selected_items else 0 for label in fig.data[0].labels]
        line_color = ['#FFFFFF' if label in selected_items else 'transparent' for label in fig.data[0].labels]
        fig.update_traces(marker=dict(line=dict(width=line_width, color=line_color)))
        
    else:
        # For bar charts
        try:
            is_horizontal = fig.data[0].orientation == 'h'
            categories = fig.data[0].y if is_horizontal else fig.data[0].x
            
            colors = [highlight_color if cat in selected_items else dimmed_color 
                     for cat in categories]
            
            fig.update_traces(marker_color=colors)
            
            # Add glowing border to selected bars
            line_width = [3 if cat in selected_items else 0 for cat in categories]
            line_color = ['#FFFFFF' if cat in selected_items else 'transparent' for cat in categories]
            fig.update_traces(marker=dict(line=dict(width=line_width, color=line_color)))
            
        except Exception as e:
            print(f"Error applying highlight: {e}")

def create_empty_chart(title="No Data Available", theme='light'):
    """Create an empty chart with a message"""
    text_color = '#e8eaed' if theme == 'dark' else '#001F3F'
    
    fig = go.Figure()
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": title,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 24, "color": text_color, "family": "Inter"}
            }
        ],
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def apply_chart_styling(fig, is_horizontal_bar=True, add_margin=True, theme='light'):
    """
    🎨 ULTIMATE CHART STYLING - Perfect Colors, Transparent Backgrounds, Smooth Animations
    
    Features:
    - Transparent backgrounds (page + chart)
    - Perfect text colors for Dark/Light modes
    - Large, readable fonts
    - Smooth transitions
    - Data labels ONLY (no X-axis numbers)
    
    Args:
        fig: Plotly figure object
        is_horizontal_bar: If True, adds margin to x-axis for horizontal bars
        add_margin: If True, adds 25% margin to prevent label truncation
        theme: 'light' or 'dark' for color scheme
    """
    # Theme-aware text color
    text_color = '#ffffff' if theme == 'dark' else '#001F3F'
    grid_color = 'rgba(255, 255, 255, 0.1)' if theme == 'dark' else 'rgba(0, 0, 0, 0.1)'
    
    # Add generous margin to prevent data label truncation
    if add_margin and is_horizontal_bar:
        try:
            max_val = max([trace.x.max() if hasattr(trace, 'x') and trace.x is not None and len(trace.x) > 0 else 0 for trace in fig.data])
            if max_val > 0:
                fig.update_layout(xaxis_range=[0, max_val * 1.25])  # 25% margin for large labels
        except:
            pass
    
    # 🎨 CORE STYLING - Transparent, Clean, Professional
    fig.update_layout(
        # Backgrounds - FULLY TRANSPARENT
        paper_bgcolor='rgba(0,0,0,0)',  # Outer background
        plot_bgcolor='rgba(0,0,0,0)',   # Chart area background
        
        # Fonts - Large & Clear
        font=dict(
            color=text_color,
            family='Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
            size=18  # Base font size
        ),
        
        # Title - Bold & Prominent
        title=dict(
            font=dict(size=24, color=text_color, family='Inter'),
            x=0.02,  # Left align
            xanchor='left'
        ),
        
        # Interaction
        dragmode=False,
        hovermode='closest',
        
        # Tooltip - Dark background with white text (works on both themes)
        hoverlabel=dict(
            bgcolor='rgba(10, 25, 41, 0.95)',
            font_size=16,
            font_family='Inter',
            font_color='white',
            bordercolor='rgba(0, 204, 255, 0.6)',
            align='left'
        ),
        
        # Margins - Generous for large fonts
        margin=dict(l=20, r=80, t=60, b=20),
        
        # Animations - Smooth transitions
        transition=dict(
            duration=500,
            easing='cubic-in-out'
        ),
        
        # Legend - Clean
        showlegend=False,  # Hide standard legend if not needed
        coloraxis_showscale=False,  # ❌ HIDE COLOR BAR (LEGEND)
    )
    
    # 📊 AXIS STYLING
    fig.update_xaxes(
        showgrid=True,
        gridcolor=grid_color,
        gridwidth=1,
        zeroline=False,
        showline=False,
        # ❌ HIDE X-AXIS TICK LABELS (numbers) - User Request
        showticklabels=False,  # This hides the numbers on X-axis
        title=dict(font=dict(size=20, color=text_color)),
        color=text_color
    )
    
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        # ✅ SHOW Y-AXIS LABELS (category names)
        showticklabels=True,
        tickfont=dict(size=18, color=text_color),  # LARGE Y-axis labels
        title=dict(font=dict(size=20, color=text_color)),
        color=text_color
    )
    
    # 🔢 DATA LABELS - Large, Bold, Always Visible
    # Apply common font settings first
    fig.update_traces(
        textfont=dict(
            size=14,
            color=text_color,
            family='Inter',
            weight=600
        )
    )
    
    # Apply type-specific settings
    for trace in fig.data:
        if trace.type == 'bar':
            trace.update(textposition='outside', cliponaxis=False)
        elif trace.type == 'scatter':
            trace.update(textposition='top center', cliponaxis=False)
        elif trace.type in ['pie', 'donut']:
            trace.update(textposition='inside')
        elif trace.type in ['treemap', 'sunburst']:
            trace.update(textposition='middle center')
    
    return fig

def apply_large_fonts_to_chart(fig, theme='light'):
    """
    🔤 APPLY OPTIMIZED FONTS - Professional Readability
    
    Optimized text sizes for better visibility without breaking layout:
    - Data labels: 14px (Readable but fits)
    - Y-axis labels: 13px (Clear category names)
    - X-axis: HIDDEN (per user request)
    - Titles: 16px (Prominent but not huge)
    
    Args:
        fig: Plotly figure object
        theme: 'light' or 'dark' for color scheme
    """
    text_color = '#ffffff' if theme == 'dark' else '#001F3F'
    grid_color = 'rgba(255, 255, 255, 0.08)' if theme == 'dark' else 'rgba(0, 0, 0, 0.08)'
    
    fig.update_layout(
        # Base font - Optimized
        font=dict(
            size=13,
            color=text_color,
            family='Inter'
        ),
        
        # Title - Professional Size
        title=dict(
            font=dict(size=16, color=text_color, family='Inter', weight=700)
        ),
        
        # X-axis - HIDDEN per user request
        xaxis=dict(
            showticklabels=False,  # ❌ Hide X-axis numbers
            title=dict(text=''),  # Hide X-axis title
            showgrid=True,
            gridcolor=grid_color,
            gridwidth=1
        ),
        
        # Y-axis - Clear & Visible
        yaxis=dict(
            title=dict(font=dict(size=14, color=text_color)),  # Y-axis title
            tickfont=dict(size=13, color=text_color, family='Inter'),  # ✅ Readable Y-axis labels
            showgrid=False
        ),
        
        # Legend - Balanced
        legend=dict(
            font=dict(size=13, color=text_color)
        )
    )
    
    # Data labels - OPTIMIZED SIZE & POSITION
    fig.update_traces(
        textfont=dict(
            size=14,
            color=text_color,
            family='Inter',
            weight=600
        )
    )
    
    # Apply type-specific settings safely
    for trace in fig.data:
        if trace.type == 'bar':
            trace.update(textposition='outside', cliponaxis=False)
        elif trace.type == 'scatter':
            trace.update(textposition='top center', cliponaxis=False)
        elif trace.type in ['pie', 'donut']:
            trace.update(textposition='inside')
        elif trace.type in ['treemap', 'sunburst']:
            trace.update(textposition='middle center')
    
    return fig
