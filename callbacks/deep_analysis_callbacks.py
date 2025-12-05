from dash import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from app_instance import app
from data_loader import df
from utils import get_color_scale, create_empty_chart, apply_large_fonts_to_chart

@app.callback(
    [Output('top-companies-chart', 'figure'),
     Output('education-level-chart', 'figure'),
     Output('skills-cloud', 'figure'),
     Output('experience-chart', 'figure'),
     Output('applicants-chart', 'figure'),
     Output('deep-total-jobs-kpi', 'children'),
     Output('deep-total-applicants-kpi', 'children'),
     Output('deep-avg-exp-kpi', 'children'),
     Output('deep-avg-applicants-kpi', 'children'),
     Output('deep-top-career-kpi', 'children')],
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
     Input('theme-store', 'data')],
    prevent_initial_call=False
)
def update_deep_analysis(companies, cities, categories, work_modes, employment_types, career_levels, education_levels, start_date, end_date, in_cities, avg_exp_range, months, search_text, theme):
    filtered_df = df.copy()
    
    # Ensure Year Of Exp_Avg is numeric BEFORE filtering
    if 'Year Of Exp_Avg' in filtered_df.columns:
        filtered_df['Year Of Exp_Avg'] = pd.to_numeric(filtered_df['Year Of Exp_Avg'], errors='coerce')
        
    # Ensure posted is datetime
    if 'posted' in filtered_df.columns:
        filtered_df['posted'] = pd.to_datetime(filtered_df['posted'], errors='coerce')
        
    # Ensure applicants is numeric
    if 'applicants' in filtered_df.columns:
        filtered_df['applicants'] = pd.to_numeric(filtered_df['applicants'], errors='coerce')
    
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
        filtered_df = filtered_df[(filtered_df['posted'] >= start_date) & (filtered_df['posted'] <= end_date)]
    if in_cities and 'In_City' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['In_City'].isin(in_cities)]
    if avg_exp_range and 'Year Of Exp_Avg' in filtered_df.columns:
        min_exp, max_exp = avg_exp_range[0], avg_exp_range[1]
        if min_exp == 0:
             filtered_df = filtered_df[((filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)) | (filtered_df['Year Of Exp_Avg'].isna())]
        else:
             filtered_df = filtered_df[(filtered_df['Year Of Exp_Avg'] >= min_exp) & (filtered_df['Year Of Exp_Avg'] <= max_exp)]
    if months and 'posted' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['posted'].dt.month.isin(months)]
    
    # Apply search text filter
    if search_text and search_text.strip():
        from utils import filter_dataframe_by_search
        filtered_df = filter_dataframe_by_search(filtered_df, search_text)

    deep_blue_scale = get_color_scale(theme)
    has_applicants = 'applicants' in filtered_df.columns
    
    # Helper to get mode safely
    def get_mode(series):
        m = series.mode()
        return m[0] if not m.empty else 'N/A'

    # CHART 1: Company Performance
    if 'Company' in filtered_df.columns and not filtered_df.empty:
        # Columns to aggregate
        agg_dict = {'Job Title': 'count'}
        if has_applicants:
            agg_dict['applicants'] = 'sum'
        if 'Year Of Exp_Avg' in filtered_df.columns:
            agg_dict['Year Of Exp_Avg'] = 'mean'
        
        # Group by Company
        company_stats = filtered_df.groupby('Company').agg(agg_dict).reset_index()
        
        # Get categorical modes separately (groupby + apply is slow, but acceptable for filtered data)
        # Optimizing: Just take the top companies first, THEN get their detailed info to save time?
        # But we need to sort to find top companies first.
        
        if has_applicants:
            company_stats = company_stats.rename(columns={'applicants': 'primary_metric'})
            metric_name = 'Total Applicants'
            title = 'Top Companies by Total Applicants'
        else:
            company_stats['primary_metric'] = company_stats['Job Title']
            metric_name = 'Job Postings'
            title = 'Top Companies by Job Postings'
            
        top_companies = company_stats.nlargest(10, 'primary_metric').sort_values('primary_metric', ascending=True)
        
        # Enriched Data for Top 10 Only (Performance Optimization)
        enriched_data = []
        for company in top_companies['Company']:
            comp_df = filtered_df[filtered_df['Company'] == company]
            enriched_data.append({
                'Company': company,
                'Work Mode': get_mode(comp_df['Work Mode']) if 'Work Mode' in comp_df else 'N/A',
                'Employment Type': get_mode(comp_df['Employment Type']) if 'Employment Type' in comp_df else 'N/A',
                'Career Level': get_mode(comp_df['Career Level']) if 'Career Level' in comp_df else 'N/A',
                'Avg Exp': round(comp_df['Year Of Exp_Avg'].mean(), 1) if 'Year Of Exp_Avg' in comp_df else 0
            })
        
        enriched_df = pd.DataFrame(enriched_data)
        if not enriched_df.empty:
            top_companies = top_companies.merge(enriched_df, on='Company')

        if not top_companies.empty:
            company_performance_fig = px.bar(
                top_companies, x='primary_metric', y='Company', title=title, orientation='h', 
                color='primary_metric', color_continuous_scale=deep_blue_scale
            )
            company_performance_fig.update_layout(
                height=600, font=dict(color='#001F3F'), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=250, r=100, t=80, b=50), showlegend=False, coloraxis_showscale=False,
                xaxis=dict(fixedrange=True, showticklabels=False, showgrid=False, title=None),
                yaxis=dict(fixedrange=True, tickfont=dict(size=17), title=None),
                dragmode=False, title_font=dict(size=24)
            )
            
            # Prepare Custom Data
            # Stack columns: [Work Mode, Emp Type, Career Level, Avg Exp, Job Title (count)]
            custom_data = top_companies[['Work Mode', 'Employment Type', 'Career Level', 'Avg Exp', 'Job Title']].values
            
            company_performance_fig.update_traces(
                texttemplate='%{x:,.0f}', textposition='outside', textfont=dict(size=17, color='#001F3F'),
                hovertemplate=(
                    '<span style="font-size: 16px; font-weight: bold;">%{y}</span><br><br>' +
                    f'{metric_name}: <b>%{{x:,.0f}}</b><br>' +
                    'Jobs: <b>%{customdata[4]}</b><br>' +
                    'Avg Exp: <b>%{customdata[3]} yrs</b><br>' +
                    'Level: <b>%{customdata[2]}</b><br>' +
                    'Type: <b>%{customdata[1]}</b><br>' +
                    'Mode: <b>%{customdata[0]}</b><extra></extra>'
                ),
                customdata=custom_data,
                hoverlabel=dict(bgcolor='#001F3F', font_size=16, font_family='Inter', font_color='white', align='left')
            )
        else:
            company_performance_fig = create_empty_chart(title, theme=theme)
    else:
        company_performance_fig = create_empty_chart('Top Companies', theme=theme)
    
    # Apply large fonts to company performance chart
    if not isinstance(company_performance_fig.data, tuple) or len(company_performance_fig.data) > 0:
        company_performance_fig = apply_large_fonts_to_chart(company_performance_fig, theme=theme)
    
    # CHART 2: Experience Level Demand
    if 'Year Of Exp_Avg' in filtered_df.columns and not filtered_df.empty:
        def bucket_experience(years):
            if pd.isna(years): return 'Not Specified'
            if years < 1: return '0-1 years'
            elif years < 3: return '1-3 years'
            elif years < 5: return '3-5 years'
            elif years < 7: return '5-7 years'
            elif years < 10: return '7-10 years'
            else: return '10+ years'
        
        filtered_df['exp_bucket'] = filtered_df['Year Of Exp_Avg'].apply(bucket_experience)
        exp_counts = filtered_df['exp_bucket'].value_counts().reset_index()
        exp_counts.columns = ['Experience Level', 'count']
        bucket_order = ['0-1 years', '1-3 years', '3-5 years', '5-7 years', '7-10 years', '10+ years', 'Not Specified']
        exp_counts['order'] = exp_counts['Experience Level'].apply(lambda x: bucket_order.index(x) if x in bucket_order else 999)
        exp_counts = exp_counts.sort_values('order').drop('order', axis=1)
        exp_counts['percentage'] = (exp_counts['count'] / exp_counts['count'].sum() * 100).round(1)
        
        if not exp_counts.empty:
            experience_buckets_fig = px.bar(
                exp_counts, x='count', y='Experience Level', title='Experience Level Demand', orientation='h', color='count', color_continuous_scale=deep_blue_scale
            )
            experience_buckets_fig.update_layout(
                height=600, font=dict(color='#001F3F'), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=250, r=100, t=80, b=50), showlegend=False, coloraxis_showscale=False,
                xaxis=dict(fixedrange=True, showticklabels=False, showgrid=False, title=None),
                yaxis=dict(fixedrange=True, tickfont=dict(size=17), title=None),
                dragmode=False, title_font=dict(size=24)
            )
            experience_buckets_fig.update_traces(
                texttemplate='%{x}', textposition='outside', textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>Jobs: %{x}<br>Percentage: %{customdata}%<extra></extra>',
                customdata=exp_counts['percentage'].values,
                hoverlabel=dict(bgcolor='#001F3F', font_size=14, font_family='Inter', font_color='white')
            )
        else:
            experience_buckets_fig = create_empty_chart('Experience Level Demand', theme=theme)
    else:
        experience_buckets_fig = create_empty_chart('Experience Level Demand', theme=theme)
    
    # Apply large fonts to experience chart
    if not isinstance(experience_buckets_fig.data, tuple) or len(experience_buckets_fig.data) > 0:
        experience_buckets_fig = apply_large_fonts_to_chart(experience_buckets_fig, theme=theme)
    
    # CHART 3: Career Level by Average Years of Experience
    if 'Career Level' in filtered_df.columns and 'Year Of Exp_Avg' in filtered_df.columns and not filtered_df.empty:
        career_exp = filtered_df.groupby('Career Level')['Year Of Exp_Avg'].mean().reset_index()
        career_exp.columns = ['Career Level', 'avg_experience']
        career_exp['avg_experience'] = career_exp['avg_experience'].round(1)
        career_counts = filtered_df['Career Level'].value_counts().reset_index()
        career_counts.columns = ['Career Level', 'job_count']
        career_exp = career_exp.merge(career_counts, on='Career Level').sort_values('avg_experience', ascending=True)
        
        if not career_exp.empty:
            career_level_fig = px.bar(
                career_exp, x='avg_experience', y='Career Level', title='Career Level by Average Years of Experience', orientation='h', color='avg_experience', color_continuous_scale=deep_blue_scale
            )
            career_level_fig.update_layout(
                height=600, font=dict(color='#001F3F'), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=250, r=100, t=80, b=50), showlegend=False, coloraxis_showscale=False,
                xaxis=dict(fixedrange=True, showticklabels=False, showgrid=False, title=None),
                yaxis=dict(fixedrange=True, tickfont=dict(size=17), title=None),
                dragmode=False, title_font=dict(size=24)
            )
            career_level_fig.update_traces(
                texttemplate='%{x:.1f}', textposition='outside', textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>Avg Experience: %{x:.1f} years<br>Job Postings: %{customdata}<extra></extra>',
                customdata=career_exp['job_count'].values,
                hoverlabel=dict(bgcolor='#001F3F', font_size=14, font_family='Inter', font_color='white')
            )
        else:
            career_level_fig = create_empty_chart('Career Level by Average Years of Experience', theme=theme)
    else:
        career_level_fig = create_empty_chart('Career Level by Average Years of Experience', theme=theme)
    
    # Apply large fonts to career level chart
    if not isinstance(career_level_fig.data, tuple) or len(career_level_fig.data) > 0:
        career_level_fig = apply_large_fonts_to_chart(career_level_fig, theme=theme)
    
    # CHART 4: Education Requirements
    if 'education_level' in filtered_df.columns and not filtered_df.empty:
        edu_counts = filtered_df['education_level'].value_counts().reset_index()
        edu_counts.columns = ['Education Level', 'count']
        edu_counts = edu_counts.sort_values('count', ascending=True)
        edu_counts['percentage'] = (edu_counts['count'] / edu_counts['count'].sum() * 100).round(1)
        
        if not edu_counts.empty:
            education_distribution_fig = px.bar(
                edu_counts, x='count', y='Education Level', title='Education Requirements', orientation='h', color='count', color_continuous_scale=deep_blue_scale
            )
            education_distribution_fig.update_layout(
                height=600, font=dict(color='#001F3F'), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=250, r=100, t=80, b=50), showlegend=False, coloraxis_showscale=False,
                xaxis=dict(fixedrange=True, showticklabels=False, showgrid=False, title=None),
                yaxis=dict(fixedrange=True, tickfont=dict(size=17), title=None),
                dragmode=False, title_font=dict(size=24)
            )
            education_distribution_fig.update_traces(
                texttemplate='%{x}', textposition='outside', textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>Count: %{x}<br>Percentage: %{customdata}%<extra></extra>',
                customdata=edu_counts['percentage'].values,
                hoverlabel=dict(bgcolor='#001F3F', font_size=14, font_family='Inter', font_color='white')
            )
        else:
            education_distribution_fig = create_empty_chart('Education Requirements', theme=theme)
    else:
        education_distribution_fig = create_empty_chart('Education Requirements', theme=theme)
    
    # Apply large fonts to education chart
    if not isinstance(education_distribution_fig.data, tuple) or len(education_distribution_fig.data) > 0:
        education_distribution_fig = apply_large_fonts_to_chart(education_distribution_fig, theme=theme)
    
    # CHART 5: Company Hiring Intensity
    if 'Company' in filtered_df.columns and not filtered_df.empty and has_applicants:
        company_intensity = filtered_df.groupby('Company').agg({
            'applicants': 'mean',
            'Job Title': 'count'
        }).reset_index()
        company_intensity.columns = ['Company', 'avg_applicants', 'postings']
        company_intensity['avg_applicants'] = company_intensity['avg_applicants'].round(1)
        top_intensity = company_intensity.nlargest(10, 'avg_applicants').sort_values('avg_applicants', ascending=True)
        
        if not top_intensity.empty:
            hiring_intensity_fig = px.bar(
                top_intensity, x='avg_applicants', y='Company', title='Most Competitive Companies (Avg Applicants per Posting)', orientation='h', color='avg_applicants', color_continuous_scale=deep_blue_scale
            )
            hiring_intensity_fig.update_layout(
                height=600, font=dict(color='#001F3F'), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=250, r=100, t=80, b=50), showlegend=False, coloraxis_showscale=False,
                xaxis=dict(fixedrange=True, showticklabels=False, showgrid=False, title=None),
                yaxis=dict(fixedrange=True, tickfont=dict(size=17), title=None),
                dragmode=False, title_font=dict(size=24)
            )
            hiring_intensity_fig.update_traces(
                texttemplate='%{x:.1f}', textposition='outside', textfont=dict(size=17, color='#001F3F'),
                hovertemplate='<b>%{y}</b><br>Avg Applicants: %{x:.1f}<br>Total Postings: %{customdata}<extra></extra>',
                customdata=top_intensity['postings'].values,
                hoverlabel=dict(bgcolor='#001F3F', font_size=14, font_family='Inter', font_color='white')
            )
        else:
            hiring_intensity_fig = create_empty_chart('Most Competitive Companies (Avg Applicants per Posting)', theme=theme)
    else:
        hiring_intensity_fig = create_empty_chart('Most Competitive Companies (Avg Applicants per Posting)', theme=theme)
    
    # Apply large fonts to hiring intensity chart
    if not isinstance(hiring_intensity_fig.data, tuple) or len(hiring_intensity_fig.data) > 0:
        hiring_intensity_fig = apply_large_fonts_to_chart(hiring_intensity_fig, theme=theme)
    
    # KPIs
    total_jobs = len(filtered_df)
    total_applicants = int(filtered_df['applicants'].sum()) if 'applicants' in filtered_df.columns and filtered_df['applicants'].notna().any() else 0
    avg_exp = filtered_df['Year Of Exp_Avg'].mean() if 'Year Of Exp_Avg' in filtered_df.columns and filtered_df['Year Of Exp_Avg'].notna().any() else 0
    avg_applicants = filtered_df['applicants'].mean() if 'applicants' in filtered_df.columns and filtered_df['applicants'].notna().any() else 0
    top_career = filtered_df['Career Level'].value_counts().index[0] if 'Career Level' in filtered_df.columns and not filtered_df.empty else 'N/A'
    
    from utils import format_kpi_value

    return (company_performance_fig, education_distribution_fig, career_level_fig, experience_buckets_fig, hiring_intensity_fig,
            format_kpi_value(total_jobs, theme), 
            format_kpi_value(total_applicants, theme), 
            format_kpi_value(avg_exp, theme), 
            format_kpi_value(avg_applicants, theme), 
            format_kpi_value(top_career, theme))
