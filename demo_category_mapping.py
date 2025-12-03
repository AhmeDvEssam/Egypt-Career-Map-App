import pandas as pd
from pathlib import Path
import sys
proj_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(proj_dir))

import Data_cleaning as dc

# Sample data to exercise category mapping
data = {
    'Category': [
        'IT & Software',            # close to IT/Software Development
        'Marketing',               # close to Marketing/PR/Advertising
        'Business Dev',            # close to Business Development
        'Acct / Finance',          # Accounting/Finance
        'Customer Support',        # Customer Service/Support
        'R and D',                 # R&D/Science
        'Ops and Management',      # Operations/Management
        'Logistics',               # Logistics/Supply Chain
        'Manufacturing',           # Manufacturing/Production
        'Human Resources',         # exact
        'Unknown Category',        # should fallback
        'Other',                   # fallback to alt cols or job title
        ''                         # empty
    ],
    'Category 2': [
        '', '', '', '', '', '', '', '', '', '', '', 'Sales/Retail', ''
    ],
    'Category 3': [
        '', '', '', '', '', '', '', '', '', '', '', '', 'Engineering - Other'
    ],
    'Job Title': [
        'Software Engineer', 'Marketing Manager', 'Business Development Rep', 'Accountant',
        'Customer Service Rep', 'Research Scientist', 'Operations Manager', 'Logistics Coordinator',
        'Plant Operator', 'HR Specialist', 'Founder', 'Retail Salesperson', 'Field Technician'
    ]
}

df = pd.DataFrame(data)
print('Input:')
print(df)

# Run general_cleaning in non-interactive mode with category mapping enabled
cleaned = dc.general_cleaning(df.copy(), interactive=False, map_category=True, map_column='Category')

print('\nMapped results:')
print(cleaned[[ 'Category', 'Category 2', 'Category 3', 'Job Title', 'Category_Mapped', 'Category_Mapped_Source']])
