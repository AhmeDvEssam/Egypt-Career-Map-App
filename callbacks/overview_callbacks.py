from dash import Input, Output, State
import plotly.express as px
import pandas as pd
from app_instance import app
from data_loader import df
from utils import get_color_scale, apply_visual_highlighting, apply_chart_styling

@app.callback(
    [Output('total-jobs-kpi', 'children'),
     Output('total-companies-kpi', 'children'),
     Output('total-categories-kpi', 'children'),
     Output('avg-applicants-kpi', 'children'),
     Output('remote-hybrid-kpi', 'children'),
     Output('latest-date-kpi', 'children'),
     Output('employment-type-chart', 'figure'),
     Output('work-mode-chart', 'figure'),
     Output('career-level-chart', 'figure'),
     Output('top-categories-chart', 'figure')],
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
def update_overview(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme):
    filtered_df = df.copy()
    
    # Apply filters
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
    if start_date and end_date and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[(filtered_df['posted'] >= start_date) & (filtered_df['posted'] <= end_date)]
    
    # In-City filter
    if in_cities and 'In_City' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
    
    # Avg Years of Experience filter
    if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
        min_exp, max_exp = avg_exp_range[0], avg_exp_range[1]
        filtered_df = filtered_df[
            (filtered_df['Year Of Exp_Avg'].isna()) | 
            ((filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp))
        ]
    
    # Month filter
    if months and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]
    
    # Apply search text filter
    # Apply search text filter
    if search_text and search_text.strip():
        from utils import filter_dataframe_by_search
        filtered_df = filter_dataframe_by_search(filtered_df, search_text)
    
    # KPIs
    total_jobs = len(filtered_df)
    total_companies = int(filtered_df['Company'].nunique()) if 'Company' in filtered_df.columns else 0
    total_categories = int(filtered_df['Category'].nunique()) if 'Category' in filtered_df.columns else 0
    
    latest_date = "N/A"
    if 'posted' in filtered_df.columns:
        valid_dates = pd.to_datetime(filtered_df['posted'], errors='coerce').dropna()
        if not valid_dates.empty:
            latest_date = valid_dates.max().strftime('%Y-%m-%d')
            
    avg_applicants = round(filtered_df['applicants'].mean(), 1) if 'applicants' in filtered_df.columns and not filtered_df['applicants'].dropna().empty else 0
    
    # Calculate Remote/Hybrid percentage
    remote_hybrid_pct = "0%"
    if 'Work Mode' in filtered_df.columns and len(filtered_df) > 0:
        remote_hybrid_count = filtered_df[filtered_df['Work Mode'].isin(['Remote', 'Hybrid'])].shape[0]
        pct = (remote_hybrid_count / len(filtered_df)) * 100
        remote_hybrid_pct = f"{pct:.1f}%"
    
    # Charts
    deep_blue_scale = get_color_scale(theme)

    # Employment Type chart
    col = 'Employment Type'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    employment_type_fig = px.bar(vc, x='count', y=col, title='Jobs by Employment Type', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    employment_type_fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    apply_visual_highlighting(employment_type_fig, vc[col].tolist(), employment_types, is_pie=False)
    apply_chart_styling(employment_type_fig, is_horizontal_bar=True)
    
    # Work Mode - Donut Chart
    col = 'Work Mode'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    work_mode_fig = px.pie(vc, values='count', names=col, title='Jobs by Work Mode', hole=0.5, color_discrete_sequence=px.colors.sequential.Blues_r)
    work_mode_fig.update_traces(textposition='inside', textinfo='percent+label', rotation=-45)
    apply_visual_highlighting(work_mode_fig, vc[col].tolist(), work_modes, is_pie=True)
    apply_chart_styling(work_mode_fig, is_horizontal_bar=False)
    
    # Career Level
    col = 'Career Level'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().reset_index()
    vc.columns = [col, 'count']
    career_level_fig = px.bar(vc, x='count', y=col, title='Jobs by Career Level', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    career_level_fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    apply_visual_highlighting(career_level_fig, vc[col].tolist(), career_levels, is_pie=False)
    apply_chart_styling(career_level_fig, is_horizontal_bar=True)

    # Top Categories
    col = 'Category'
    s = filtered_df[col] if col in filtered_df.columns else pd.Series(dtype='object')
    vc = s.value_counts().head(10).reset_index()
    vc.columns = [col, 'count']
    top_categories_fig = px.bar(vc, x='count', y=col, title='Top 10 Categories', orientation='h', color='count', color_continuous_scale=deep_blue_scale, text='count')
    top_categories_fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    apply_visual_highlighting(top_categories_fig, vc[col].tolist(), categories, is_pie=False)
    apply_chart_styling(top_categories_fig, is_horizontal_bar=True)
    
    return f"{total_jobs:,}", f"{total_companies:,}", f"{total_categories:,}", f"{avg_applicants:.1f}", remote_hybrid_pct, latest_date, employment_type_fig, work_mode_fig, career_level_fig, top_categories_fig
