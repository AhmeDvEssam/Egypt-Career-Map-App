from dash import Input, Output, State
import plotly.express as px
import pandas as pd
from app_instance import app
from data_loader import df, skills_df
from utils import apply_large_fonts_to_chart

@app.callback(
    [Output('total-skills-kpi', 'children'),
     Output('top-skill-kpi', 'children'),
     Output('avg-skills-kpi', 'children'),
     Output('skills-wordcloud', 'figure'),
     Output('skills-category-breakdown', 'figure'),
     Output('top-skills-bar', 'figure'),
     Output('skills-trend', 'figure'),
     Output('top-skill-cat-kpi', 'children'),
     Output('skill-trend-selector', 'options')],
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
     Input('theme-store', 'data'),
     Input('skill-trend-selector', 'value')]
)
def update_skills_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme, selected_trend_skills):
    filtered_df = df.copy()
    
    # Apply all filters
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
    if in_cities and 'In_City' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
    if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
        min_exp, max_exp = avg_exp_range[0], avg_exp_range[1]
        filtered_df = filtered_df[(filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)]
    if months and 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]
    if search_text and search_text.strip():
        from utils import filter_dataframe_by_search
        filtered_df = filter_dataframe_by_search(filtered_df, search_text)
    
    # Merge with skills data
    if not skills_df.empty and 'Job Title' in filtered_df.columns:
        # Get job titles from filtered dataset
        filtered_job_titles = filtered_df['Job Title'].unique().tolist()
        # Filter skills_df to only include skills for jobs in filtered dataset
        filtered_skills = skills_df[skills_df['Job Title'].isin(filtered_job_titles)].copy()
        
        # Collect all skills
        all_skills = filtered_skills['Skills'].dropna().tolist() if 'Skills' in filtered_skills.columns else []
    else:
        all_skills = []
    
    # Calculate KPIs
    unique_skills = len(set(all_skills)) if all_skills else 0
    top_skill = pd.Series(all_skills).value_counts().index[0] if all_skills else "N/A"
    avg_skills_per_job = round(len(all_skills) / len(filtered_df), 1) if len(filtered_df) > 0 else 0
    
    # Calculate Top Skill Category (Proxy using Job Category for now as Skill Category isn't in skills_df)
    top_skill_cat = filtered_df['Category'].value_counts().index[0] if 'Category' in filtered_df.columns and not filtered_df.empty else "N/A"
    
    # Skills Word Cloud (Treemap - Dark Mode Optimized)
    if all_skills:
        skill_counts = pd.Series(all_skills).value_counts().head(30).reset_index()
        skill_counts.columns = ['skill', 'count']
        
        # Use a custom scale that starts DARK enough for white text
        # (0, Medium Blue) -> (1, Dark Navy)
        dark_contrast_scale = [(0, '#3a7bd5'), (1, '#001f3f')] 
        
        wordcloud_fig = px.treemap(
            skill_counts,
            path=['skill'],
            values='count',
            title='Top 30 Skills (Click to Filter)',
            color='count',
            color_continuous_scale=dark_contrast_scale, 
            hover_data=['count'],
            height=600 # Ensure it fills the container
        )
        wordcloud_fig.update_layout(transition={'duration': 0}, margin=dict(t=50, l=10, r=10, b=10)) 
        wordcloud_fig.update_traces(
            textinfo="label+value",
            root_color="rgba(0,0,0,0)",
            hovertemplate='<b>%{label}</b><br>Count: %{value}<extra></extra>'
        )
    else:
        wordcloud_fig = px.treemap(pd.DataFrame({'skill': [], 'count': []}), path=['skill'], values='count', title='Top 30 Skills (Treemap)')
    
    # Skills by Category Breakdown (Horizontal Bar Chart)
    # USER REQUEST: Use Category from Jobs.xlsx ONLY.
    if not skills_df.empty and all_skills:
        # 1. Filter skills_df to only relevant job titles
        curr_titles = filtered_df['Job Title'].dropna().unique()
        # Drop 'Category' from skills_df slice because we ONLY want Category from Jobs Data
        rel_skills = skills_df[skills_df['Job Title'].isin(curr_titles)].copy().drop(columns=['Category'], errors='ignore')
        
        # 2. Merge to associate Skill -> Job Category
        # Ensure join keys are strings to avoid type mismatch
        rel_skills['Job Title'] = rel_skills['Job Title'].astype(str)
        
        # Prepare Jobs Data for merge (Drop duplicates to avoid Cartesian explosion if multiple job entries exist? 
        # Actually we WANT multiple job entries if they represent distinct jobs. But Category is per job.
        # Ideally: We want to count how many TIMES a skill appears in a category.
        # So we behave as if we are counting (Job, Skill) pairs -> Category.
        
        jobs_for_merge = filtered_df[['Job Title', 'Category']].dropna(subset=['Category']).copy()
        jobs_for_merge['Job Title'] = jobs_for_merge['Job Title'].astype(str)
        
        merged_cat = rel_skills.merge(jobs_for_merge, on='Job Title', how='inner')
        
        if not merged_cat.empty:
            category_counts = merged_cat.groupby('Category').size().reset_index(name='count')
            category_counts = category_counts.sort_values('count', ascending=True) 
            
            # Dynamic Height for Scrollbar
            dynamic_height = max(600, len(category_counts) * 50)

            category_breakdown_fig = px.bar(
                category_counts,
                x='count',
                y='Category',
                orientation='h',
                title='Skills Demand by Category (Jobs Data)',
                text='count',
                color='count',
                color_continuous_scale=px.colors.sequential.Blues,
                height=dynamic_height
            )
            
            category_breakdown_fig.update_traces(textposition='outside', textfont=dict(size=14, color='#ffffff' if theme == 'dark' else '#001f3f'))
            category_breakdown_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
            
        else:
            category_breakdown_fig = px.bar(pd.DataFrame({'Category': [], 'count': []}), x='count', y='Category', orientation='h', title='No Data Available for Selection')
    else:
        category_breakdown_fig = px.bar(pd.DataFrame({'Category': [], 'count': []}), x='count', y='Category', orientation='h', title='Skills Demand by Category (Empty)')
    
    # Top 15 Skills Bar Chart (Existing - keep style consistent)
    if all_skills:
        top_skills = pd.Series(all_skills).value_counts().head(15).reset_index()
        top_skills.columns = ['skill', 'count']
        top_skills = top_skills.sort_values('count', ascending=True) # Sort for Bar h
        top_skills_fig = px.bar(
            top_skills,
            x='count',
            y='skill',
            orientation='h',
            title='Top 15 Most Demanded Skills',
            color='count',
            color_continuous_scale=px.colors.sequential.Blues,
            text='count'
        )
    else:
        top_skills_fig = px.bar(pd.DataFrame({'skill': [], 'count': []}), x='count', y='skill', orientation='h', title='Top 15 Most Demanded Skills')
    
    # Skills Trend Over Time (Interactive)
    trend_options = []
    if all_skills:
        # Populate options from Top 50 skills to avoid overload
        top_50_skills = pd.Series(all_skills).value_counts().head(50).index.tolist()
        trend_options = [{'label': s, 'value': s} for s in top_50_skills]
    
    if not filtered_df.empty and 'posted' in filtered_df.columns and not skills_df.empty:
        # 1. Merge filtered jobs with skills to get (Date, Skill) tuples
        # Optimization: Filter skills_df first
        filtered_titles = filtered_df['Job Title'].unique()
        rel_skills = skills_df[skills_df['Job Title'].isin(filtered_titles)]
        
        # Merge
        merged = rel_skills.merge(filtered_df[['Job Title', 'posted']], on='Job Title', how='inner')
        merged['Month'] = pd.to_datetime(merged['posted']).dt.to_period('M').astype(str)
        
        # Filter by selected skills (or Top 5 default)
        if not selected_trend_skills:
             selected_trend_skills = pd.Series(all_skills).value_counts().head(5).index.tolist()
        
        trend_data = merged[merged['Skills'].isin(selected_trend_skills)]
        
        if not trend_data.empty:
            monthly_counts = trend_data.groupby(['Month', 'Skills']).size().reset_index(name='count')
            monthly_counts = monthly_counts.sort_values('Month')
            
            skills_trend_fig = px.line(
                monthly_counts,
                x='Month',
                y='count',
                color='Skills',
                title='Skills Trend Over Time',
                markers=True
            )
        else:
            skills_trend_fig = px.line(pd.DataFrame({'Month': [], 'count': [], 'Skills': []}), x='Month', y='count', title='Skills Trend Over Time')
    else:
        skills_trend_fig = px.line(pd.DataFrame({'Month': [], 'count': [], 'Skills': []}), x='Month', y='count', title='Skills Trend Over Time')
    
    # Apply dark theme to all figures
    font_color = '#ffffff' if theme == 'dark' else '#001F3F'
    
    for fig in [wordcloud_fig, category_breakdown_fig, top_skills_fig, skills_trend_fig]:
        fig.update_layout(
            dragmode=False,
            template='plotly',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=font_color, family='Inter'),
            title_font=dict(size=40, color=font_color), # Adjusted size
            xaxis_title=None,
            yaxis_title=None,
            coloraxis_showscale=False,
            xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=18, color=font_color)),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=18, color=font_color)),
            hoverlabel=dict(
                bgcolor='#001F3F',
                font_size=13,
                font_family='Inter',
                font_color='white'
            )
        )
        
        # Specific Adjustments
        if fig == top_skills_fig or fig == category_breakdown_fig:
            fig.update_traces(textposition='outside', textfont=dict(size=18, color=font_color))
            fig.update_layout(margin=dict(l=150)) # Add left margin for labels
            
        if fig == wordcloud_fig:
             fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{label}</b><br>Count: %{value}</span><extra></extra>')

    # Apply large fonts
    wordcloud_fig = apply_large_fonts_to_chart(wordcloud_fig, theme=theme)
    category_breakdown_fig = apply_large_fonts_to_chart(category_breakdown_fig, theme=theme)
    top_skills_fig = apply_large_fonts_to_chart(top_skills_fig, theme=theme)
    skills_trend_fig = apply_large_fonts_to_chart(skills_trend_fig, theme=theme)
    
    from utils import format_kpi_value
    return format_kpi_value(unique_skills, theme), format_kpi_value(top_skill, theme), format_kpi_value(avg_skills_per_job, theme), wordcloud_fig, category_breakdown_fig, top_skills_fig, skills_trend_fig, format_kpi_value(top_skill_cat, theme), trend_options

@app.callback(
    Output('global-search-bar', 'value', allow_duplicate=True),
    [Input('skills-wordcloud', 'clickData')],
    [State('global-search-bar', 'value')],
    prevent_initial_call=True
)
def filter_by_clicked_skill(clickData, current_search):
    """
    Update global search bar when a skill in the word cloud is clicked.
    """
    if not clickData:
        return current_search
    
    try:
        # Treemap clickData: {'points': [{'label': 'SkillName', 'value': 123...}]}
        point = clickData['points'][0]
        skill = point.get('label')
        
        # Don't overwrite if clicking the same thing, but usually we just set it.
        # This acts as a 'filter by this skill' action.
        if skill:
            return skill
            
    except Exception:
        pass
        
    return current_search
