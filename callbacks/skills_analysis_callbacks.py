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
     Output('top-skill-cat-kpi', 'children')],
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
def update_skills_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme):
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
    
    # Skills Word Cloud (using Treemap for interactive word cloud effect)
    if all_skills:
        skill_counts = pd.Series(all_skills).value_counts().head(30).reset_index()
        skill_counts.columns = ['skill', 'count']
        wordcloud_fig = px.treemap(
            skill_counts,
            path=['skill'],
            values='count',
            title='Top 30 Skills (Word Cloud)',
            color='count',
            color_continuous_scale='Blues'
        )
    else:
        wordcloud_fig = px.treemap(pd.DataFrame({'skill': [], 'count': []}), path=['skill'], values='count', title='Top 30 Skills (Word Cloud)')
    
    # Skills by Category Breakdown
    if not skills_df.empty and 'Category' in skills_df.columns and all_skills:
        filtered_job_titles = filtered_df['Job Title'].unique().tolist() if 'Job Title' in filtered_df.columns else []
        filtered_skills_cat = skills_df[skills_df['Job Title'].isin(filtered_job_titles)].copy()
        
        if not filtered_skills_cat.empty and 'Category' in filtered_skills_cat.columns:
            category_counts = filtered_skills_cat.groupby('Category').size().reset_index(name='count')
            category_breakdown_fig = px.pie(
                category_counts,
                values='count',
                names='Category',
                title='Skills Distribution by Category'
            )
        else:
            category_breakdown_fig = px.pie(pd.DataFrame({'Category': [], 'count': []}), values='count', names='Category', title='Skills Distribution by Category')
    else:
        category_breakdown_fig = px.pie(pd.DataFrame({'Category': [], 'count': []}), values='count', names='Category', title='Skills Distribution by Category')
    
    # Top 15 Skills Bar Chart
    if all_skills:
        top_skills = pd.Series(all_skills).value_counts().head(15).reset_index()
        top_skills.columns = ['skill', 'count']
        top_skills_fig = px.bar(
            top_skills,
            x='count',
            y='skill',
            orientation='h',
            title='Top 15 Most Demanded Skills',
            color='count',
            color_continuous_scale=[(0, '#00C9FF'), (1, '#001f3f')],
            text='count'
        )
    else:
        top_skills_fig = px.bar(pd.DataFrame({'skill': [], 'count': []}), x='count', y='skill', orientation='h', title='Top 15 Most Demanded Skills')
    
    # Skills Trend Over Time
    if 'posted' in filtered_df.columns and all_skills:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df['Month'] = filtered_df['posted'].dt.to_period('M').astype(str)
        
        # Count skills per month
        skill_trend_data = []
        for idx, row in filtered_df.iterrows():
            month = row.get('Month')
            if pd.notna(month):
                for i in range(11):
                    skill_col = f'Skill{i}'
                    if skill_col in row and pd.notna(row[skill_col]):
                        skill_trend_data.append({'Month': month, 'Skill': row[skill_col]})
        
        if skill_trend_data:
            trend_df = pd.DataFrame(skill_trend_data)
            monthly_counts = trend_df.groupby('Month').size().reset_index(name='count')
            skills_trend_fig = px.line(
                monthly_counts,
                x='Month',
                y='count',
                title='Skills Demand Trend Over Time'
            )
        else:
            skills_trend_fig = px.line(pd.DataFrame({'Month': [], 'count': []}), x='Month', y='count', title='Skills Demand Trend Over Time')
    else:
        skills_trend_fig = px.line(pd.DataFrame({'Month': [], 'count': []}), x='Month', y='count', title='Skills Demand Trend Over Time')
    
    # Apply dark theme to all figures
    for fig in [wordcloud_fig, category_breakdown_fig, top_skills_fig, skills_trend_fig]:
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
            xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False, tickfont=dict(size=22)),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
            hoverlabel=dict(
                bgcolor='#001F3F',
                font_size=13,
                font_family='Inter',
                font_color='white'
            )
        )
        
        # Force white text in tooltip using inline styles
        if fig == top_skills_fig:
            fig.update_traces(textposition='outside', textfont=dict(size=22, color='#001F3F'))
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{y}</b><br>Count: %{x}</span><extra></extra>')
        elif fig == category_breakdown_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}</span><extra></extra>')
        elif fig == skills_trend_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Count: %{y}</span><extra></extra>')
        elif fig == wordcloud_fig:
from dash import Input, Output, State
import plotly.express as px
import pandas as pd
from app_instance import app
from data_loader import df, skills_df
from utils import apply_large_fonts_to_chart, format_kpi_value

@app.callback(
    [Output('total-skills-kpi', 'children'),
     Output('top-skill-kpi', 'children'),
     Output('avg-skills-kpi', 'children'),
     Output('skills-wordcloud', 'figure'),
     Output('skills-category-breakdown', 'figure'),
     Output('top-skills-bar', 'figure'),
     Output('skills-trend', 'figure'),
     Output('top-skill-cat-kpi', 'children')],
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
def update_skills_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme):
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
    
    # Skills Word Cloud (using Treemap for interactive word cloud effect)
    if all_skills:
        skill_counts = pd.Series(all_skills).value_counts().head(30).reset_index()
        skill_counts.columns = ['skill', 'count']
        wordcloud_fig = px.treemap(
            skill_counts,
            path=['skill'],
            values='count',
            title='Top 30 Skills (Word Cloud)',
            color='count',
            color_continuous_scale='Blues'
        )
    else:
        wordcloud_fig = px.treemap(pd.DataFrame({'skill': [], 'count': []}), path=['skill'], values='count', title='Top 30 Skills (Word Cloud)')
    
    # Skills by Category Breakdown
    if not skills_df.empty and 'Category' in skills_df.columns and all_skills:
        filtered_job_titles = filtered_df['Job Title'].unique().tolist() if 'Job Title' in filtered_df.columns else []
        filtered_skills_cat = skills_df[skills_df['Job Title'].isin(filtered_job_titles)].copy()
        
        if not filtered_skills_cat.empty and 'Category' in filtered_skills_cat.columns:
            category_counts = filtered_skills_cat.groupby('Category').size().reset_index(name='count')
            category_breakdown_fig = px.pie(
                category_counts,
                values='count',
                names='Category',
                title='Skills Distribution by Category'
            )
        else:
            category_breakdown_fig = px.pie(pd.DataFrame({'Category': [], 'count': []}), values='count', names='Category', title='Skills Distribution by Category')
    else:
        category_breakdown_fig = px.pie(pd.DataFrame({'Category': [], 'count': []}), values='count', names='Category', title='Skills Distribution by Category')
    
    # Top 15 Skills Bar Chart
    if all_skills:
        top_skills = pd.Series(all_skills).value_counts().head(15).reset_index()
        top_skills.columns = ['skill', 'count']
        top_skills_fig = px.bar(
            top_skills,
            x='count',
            y='skill',
            orientation='h',
            title='Top 15 Most Demanded Skills',
            color='count',
            color_continuous_scale=[(0, '#00C9FF'), (1, '#001f3f')],
            text='count'
        )
    else:
        top_skills_fig = px.bar(pd.DataFrame({'skill': [], 'count': []}), x='count', y='skill', orientation='h', title='Top 15 Most Demanded Skills')
    
    # Skills Trend Over Time
    if 'posted' in filtered_df.columns and all_skills:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        filtered_df['Month'] = filtered_df['posted'].dt.to_period('M').astype(str)
        
        # Count skills per month
        skill_trend_data = []
        for idx, row in filtered_df.iterrows():
            month = row.get('Month')
            if pd.notna(month):
                for i in range(11):
                    skill_col = f'Skill{i}'
                    if skill_col in row and pd.notna(row[skill_col]):
                        skill_trend_data.append({'Month': month, 'Skill': row[skill_col]})
        
        if skill_trend_data:
            trend_df = pd.DataFrame(skill_trend_data)
            monthly_counts = trend_df.groupby('Month').size().reset_index(name='count')
            skills_trend_fig = px.line(
                monthly_counts,
                x='Month',
                y='count',
                title='Skills Demand Trend Over Time'
            )
        else:
            skills_trend_fig = px.line(pd.DataFrame({'Month': [], 'count': []}), x='Month', y='count', title='Skills Demand Trend Over Time')
    else:
        skills_trend_fig = px.line(pd.DataFrame({'Month': [], 'count': []}), x='Month', y='count', title='Skills Demand Trend Over Time')
    
    # Apply dark theme to all figures
    for fig in [wordcloud_fig, category_breakdown_fig, top_skills_fig, skills_trend_fig]:
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
            xaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=False, tickfont=dict(size=22)),
            yaxis=dict(showgrid=False, showline=False, zeroline=False, showticklabels=True, tickfont=dict(size=22)),
            hoverlabel=dict(
                bgcolor='#001F3F',
                font_size=13,
                font_family='Inter',
                font_color='white'
            )
        )
        
        # Force white text in tooltip using inline styles
        if fig == top_skills_fig:
            fig.update_traces(textposition='outside', textfont=dict(size=22, color='#001F3F'))
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{y}</b><br>Count: %{x}</span><extra></extra>')
        elif fig == category_breakdown_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}</span><extra></extra>')
        elif fig == skills_trend_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{x}</b><br>Count: %{y}</span><extra></extra>')
        elif fig == wordcloud_fig:
            fig.update_traces(hovertemplate='<span style="color:white; font-family:Inter;"><b>%{label}</b><br>Count: %{value}</span><extra></extra>')
    
    # Apply large fonts to all charts
    wordcloud_fig = apply_large_fonts_to_chart(wordcloud_fig, theme=theme)
    category_breakdown_fig = apply_large_fonts_to_chart(category_breakdown_fig, theme=theme)
    top_skills_fig = apply_large_fonts_to_chart(top_skills_fig, theme=theme)
    skills_trend_fig = apply_large_fonts_to_chart(skills_trend_fig, theme=theme)
    
    return format_kpi_value(unique_skills, theme), format_kpi_value(top_skill, theme), format_kpi_value(avg_skills_per_job, theme), wordcloud_fig, category_breakdown_fig, top_skills_fig, skills_trend_fig, format_kpi_value(top_skill_cat, theme)
