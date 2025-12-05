from dash import Input, Output, State
import plotly.express as px
import pandas as pd
from app_instance import app
from data_loader import df
from utils import get_color_scale, apply_large_fonts_to_chart

@app.callback(
    [Output('time-jobs-kpi', 'children'),
     Output('time-growth-kpi', 'children'),
     Output('time-applicants-kpi', 'children'),
     Output('time-peak-day-kpi', 'children'),
     Output('month-day-line-chart', 'figure'),
     Output('month-bar-chart', 'figure'),
     Output('applicants-trend-chart', 'figure')],
    [Input('sidebar-company-filter', 'value'),
     Input('sidebar-city-filter', 'value'),
     Input('sidebar-category-filter', 'value'),
     Input('sidebar-work-mode-filter', 'value'),
     Input('sidebar-employment-type-filter', 'value'),
     Input('sidebar-career-level-filter', 'value'),
     Input('sidebar-education-filter', 'value'),
     Input('sidebar-date-filter', 'start_date'),
     Input('sidebar-date-filter', 'end_date'),
     Input('sidebar-in-city-filter', 'value'),
     Input('sidebar-avg-exp-filter', 'value'),
     Input('sidebar-month-filter', 'value'),
     Input('global-search-bar', 'value'),
     Input('theme-store', 'data')]
)
def update_time_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme):
    try:
        filtered_df = df.copy()
        
        if companies:
            filtered_df = filtered_df[filtered_df['Company'].isin(companies)]
        if cities:
            filtered_df = filtered_df[filtered_df['City'].isin(cities)]
        if categories:
            filtered_df = filtered_df[filtered_df['Category'].isin(categories)]
        if work_modes:
            filtered_df = filtered_df[filtered_df['Work Mode'].isin(work_modes)]
        if employment_types:
            filtered_df = filtered_df[filtered_df['Employment Type'].isin(employment_types)]
        if career_levels:
            filtered_df = filtered_df[filtered_df['Career Level'].isin(career_levels)]
        if education_levels:
            filtered_df = filtered_df[filtered_df['education_level'].isin(education_levels)]
        
        # In-City filter
        if in_cities and 'In_City' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
        
        # Avg Years of Experience filter
        if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
            min_exp, max_exp = avg_exp_range[0], avg_exp_range[1]
            filtered_df = filtered_df[(filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)]
        
        # Month filter (applied before date range to avoid conflicts)
        if months and 'posted' in filtered_df.columns:
            filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
            filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]
        
        # Apply search text filter
        if search_text and search_text.strip():
            from utils import filter_dataframe_by_search
            filtered_df = filter_dataframe_by_search(filtered_df, search_text)
        
        # Ensure posted is datetime before filtering by date range
        if 'posted' in filtered_df.columns:
            filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        
        if start_date and end_date:
            filtered_df = filtered_df[(filtered_df['posted'] >= start_date) & (filtered_df['posted'] <= end_date)]
            
        # Prepare time data
        if 'posted' in filtered_df.columns and not filtered_df['posted'].dropna().empty:
            filtered_df['Month'] = filtered_df['posted'].dt.to_period('M').astype(str)
            filtered_df['Day'] = filtered_df['posted'].dt.day_name()
        else:
            filtered_df['Month'] = pd.Series(dtype='object')
            filtered_df['Day'] = pd.Series(dtype='object')
    except Exception as e:
        print(f"Error in update_time_analysis: {e}")
        filtered_df = pd.DataFrame()
        filtered_df['Month'] = pd.Series(dtype='object')
        filtered_df['Day'] = pd.Series(dtype='object')
    
    # Month-Day line chart
    if not filtered_df['Month'].dropna().empty:
        month_day_df = filtered_df.groupby(['Month', 'Day']).size().reset_index(name='count')
        month_day_fig = px.line(month_day_df, x='Month', y='count', color='Day', title='Jobs by Month and Day')
    else:
        month_day_fig = px.line(pd.DataFrame({'Month': [], 'count': [], 'Day': []}), x='Month', y='count', color='Day', title='Jobs by Month and Day')
    
    # Month bar chart
    deep_blue_scale = get_color_scale(theme)

    if not filtered_df['Month'].dropna().empty:
        month_df = filtered_df['Month'].value_counts().reset_index(name='count').rename(columns={'index': 'Month'}).sort_values('Month')
        month_bar_fig = px.bar(month_df, x='Month', y='count', title='Jobs by Month', color='count', color_continuous_scale=deep_blue_scale, text='count')
    else:
        month_bar_fig = px.bar(pd.DataFrame({'Month': [], 'count': []}), x='Month', y='count', title='Jobs by Month')
    
    # Applicants trend
    if 'applicants' in filtered_df.columns and not filtered_df['Month'].dropna().empty:
        applicants_trend = filtered_df.groupby('Month')['applicants'].mean().reset_index()
        applicants_trend_fig = px.line(applicants_trend, x='Month', y='applicants', title='Average Applicants Trend')
    else:
        applicants_trend_fig = px.line(pd.DataFrame({'Month': [], 'applicants': []}), x='Month', y='applicants', title='Average Applicants Trend')
    
    # Style figures with dark theme
    for fig in [month_day_fig, month_bar_fig, applicants_trend_fig]:
        fig.update_layout(
            dragmode=False,
            template='plotly',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#001F3F', family='Inter'),
            title_font=dict(size=51, color='#001F3F'),
            xaxis_title=None,
            yaxis_title=None,
            coloraxis_showscale=False,
            xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
            hoverlabel=dict(
                bgcolor='#001F3F',
                font_size=13,
                font_family='Inter',
                font_color='white'
            )
        )
        if fig == month_bar_fig:
             fig.update_layout(
                 xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
                 yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False)
             )
             fig.update_traces(textposition='outside', textfont=dict(size=22, color='#001F3F'))
        
        if fig == month_day_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Day: %{fullData.name}<br>Count: %{y}</span><extra></extra>')
        elif fig == applicants_trend_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Applicants: %{y:.1f}</span><extra></extra>')
        else:
            # Month bar chart
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Count: %{y}</span><extra></extra>')
    
    # Calculate KPIs for Time Analysis
    total_jobs_period = len(filtered_df)
    
    # MoM Growth
    mom_growth = "0%"
    if not filtered_df.empty and 'posted' in filtered_df.columns:
        try:
            current_month = filtered_df['posted'].max().month
            prev_month = current_month - 1 if current_month > 1 else 12
            current_count = len(filtered_df[filtered_df['posted'].dt.month == current_month])
            prev_count = len(filtered_df[filtered_df['posted'].dt.month == prev_month])
            if prev_count > 0:
                growth = ((current_count - prev_count) / prev_count) * 100
                mom_growth = f"{growth:+.1f}%"
            else:
                mom_growth = "N/A"
        except:
            mom_growth = "N/A"
            
    # Avg Applicants Trend (Last 30 days)
    avg_applicants_trend = "0"
    if 'applicants' in filtered_df.columns:
        avg_applicants_trend = f"{filtered_df['applicants'].mean():.1f}"
        
    # Peak Posting Day
    peak_day = "N/A"
    if 'Day' in filtered_df.columns and not filtered_df['Day'].dropna().empty:
        peak_day = filtered_df['Day'].value_counts().index[0]

    # Apply large fonts to all charts
    month_day_fig = apply_large_fonts_to_chart(month_day_fig, theme=theme)
    month_bar_fig = apply_large_fonts_to_chart(month_bar_fig, theme=theme)
    applicants_trend_fig = apply_large_fonts_to_chart(applicants_trend_fig, theme=theme)
    
    return f"{total_jobs_period:,}", mom_growth, avg_applicants_trend, peak_day, month_day_fig, month_bar_fig, applicants_trend_fig
