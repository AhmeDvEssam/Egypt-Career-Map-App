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
    """Return color scale based on theme"""
    if theme == 'dark':
        return [[0, '#003A70'], [0.5, '#0066CC'], [1, '#00CCFF']]
    else:
        return [[0, '#002040'], [0.5, '#004080'], [1, '#0060C0']]

def apply_visual_highlighting(fig, counts, selected_items, is_pie=False):
    """
    Apply visual highlighting to charts based on selection.
    
    Args:
        fig: Plotly figure object
        counts: List/Series of values used for coloring
        selected_items: List of currently selected items (names)
        is_pie: Boolean, true if chart is a pie/donut chart
    """
    if not selected_items:
        return

    # Default colors
    default_color = '#0066CC'
    highlight_color = '#00CCFF'  # Bright Cyan for selection
    dimmed_color = 'rgba(0, 102, 204, 0.3)'
    
    if is_pie:
        # For pie charts, we need to update marker colors
        colors = [highlight_color if label in selected_items else dimmed_color 
                 for label in fig.data[0].labels]
        fig.update_traces(marker=dict(colors=colors))
        
        # Add outline to selected slices
        line_width = [2 if label in selected_items else 0 for label in fig.data[0].labels]
        line_color = ['#FFFFFF' if label in selected_items else 'transparent' for label in fig.data[0].labels]
        fig.update_traces(marker=dict(line=dict(width=line_width, color=line_color)))
        
    else:
        # For bar charts
        # Note: This assumes the x/y axis matches the selection items
        # We need to check if the figure has customdata or text that matches
        
        # Simple implementation for bar charts where x or y axis is the category
        try:
            # Check if it's horizontal or vertical
            is_horizontal = fig.data[0].orientation == 'h'
            categories = fig.data[0].y if is_horizontal else fig.data[0].x
            
            colors = [highlight_color if cat in selected_items else dimmed_color 
                     for cat in categories]
            
            fig.update_traces(marker_color=colors)
            
            # Add border to selected bars
            line_width = [2 if cat in selected_items else 0 for cat in categories]
            line_color = ['#FFFFFF' if cat in selected_items else 'transparent' for cat in categories]
            fig.update_traces(marker=dict(line=dict(width=line_width, color=line_color)))
            
        except Exception as e:
            print(f"Error applying highlight: {e}")

def create_empty_chart(title="No Data Available"):
    """Create an empty chart with a message"""
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
                "font": {"size": 20, "color": "#001F3F"}
            }
        ],
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def apply_chart_styling(fig, is_horizontal_bar=True, add_margin=True):
    """
    Apply consistent styling to charts with proper data label visibility and white tooltips.
    
    Args:
        fig: Plotly figure object
        is_horizontal_bar: If True, adds margin to x-axis for horizontal bars
        add_margin: If True, adds 20% margin to prevent label truncation
    """
    # Add margin to prevent data label truncation
    if add_margin and is_horizontal_bar:
        try:
            max_val = max([trace.x.max() if hasattr(trace, 'x') and trace.x is not None and len(trace.x) > 0 else 0 for trace in fig.data])
            if max_val > 0:
                fig.update_layout(xaxis_range=[0, max_val * 1.2])  # 20% margin
        except:
            pass
    
    # Apply consistent styling
    fig.update_layout(
        dragmode=False,
        template='plotly',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#001F3F', family='Inter'),
        title_font=dict(size=48, color='#001F3F'),
        hoverlabel=dict(
            bgcolor='#001F3F',
            font_size=13,
            font_family='Inter',
            font_color='white'  # White tooltip text
        )
    )
    
    return fig
