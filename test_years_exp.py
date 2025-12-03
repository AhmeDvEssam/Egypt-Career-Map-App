import sys
from pathlib import Path
import pandas as pd

# Ensure project dir is on sys.path
proj_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(proj_dir))

import Data_cleaning as dc

# Sample rows from the user
rows = [
    '2 - 3 Yrs of Exp',
    '2 - 5 Yrs of Exp',
    '1 - 2 Yrs of Exp',
    '7 - 10 Yrs of Exp',
    '2 - 6 Yrs of Exp',
    '1+ Yrs of Exp',
    '0 - 3 Yrs of Exp',
    '1 - 2 Yrs of Exp',
    '1 - 3 Yrs of Exp',
    '3 - 5 Yrs of Exp',
    '1 - 3 Yrs of Exp',
    '2 - 4 Yrs of Exp'
]

df = pd.DataFrame({'Years Of Exp': rows})

print('Input:')
print(df)

# Run general_cleaning non-interactively, request avg conversion
cleaned = dc.general_cleaning(df.copy(), interactive=False, convert_avg_choice=True, howlong_choice='1')

print('\nResult:')
print(cleaned[['Years Of Exp', 'Years Of Exp_Clean', 'Avg Years Of Exp']])
