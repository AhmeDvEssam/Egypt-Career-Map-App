import pandas as pd
from Data_cleaning import skills_standardize, RAPIDFUZZ_AVAILABLE

# sample data (a subset of the long list) to demonstrate behavior
rows = [
    'Data Analysis', 'data analysis', 'Data Analysis ', 'data-Analysis',
    'Machine Learning', 'Machine learning', 'ml', 'Machine-Learning',
    'Python', 'python programming', 'Programming Python',
    'Ms Office', 'Microsoft Office', 'ms office', 'Ms. Office', 'MS OFFICE',
    'Excel', 'Microsoft Excel', 'excel advanced', 'Excel Advanced',
    'Power Bi', 'Power BI', 'Power bi', 'Power-BI',
    'Ficial Accounting', 'Fical Accounting', 'Financial Accounting',
    'Ai', 'Artificial Intelligence', 'AI', 'artificial intelligence',
    '', None
]

df = pd.DataFrame({'Skill': rows})

print('Input sample:')
print(df)

# run standardizer
out = skills_standardize(df, skills_column='Skill', export_report='demo_skill_report.csv', cutoff=0.86)
print('\nRAPIDFUZZ_AVAILABLE =', RAPIDFUZZ_AVAILABLE)

print('\nResult sample:')
print(out[['Skill', 'Skill_Clean', 'Skill_Mapped', 'Skill_Mapped_Source']])

# optional: write report
out.to_csv('demo_skills_mapped.csv', index=False, encoding='utf-8')
print('\nWrote demo_skills_mapped.csv')
