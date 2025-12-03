import pandas as pd
import os

# Path to the data file
base_dir = os.getcwd()
path = os.path.join(base_dir, 'Jobs.xlsx')

print(f"Checking file at: {path}")

if os.path.exists(path):
    try:
        df = pd.read_excel(path)
        print("\nColumns found:")
        print(df.columns.tolist())
        
        print("\nChecking for specific columns:")
        required_columns = ['Company', 'applicants', 'Year Of Exp_Avg', 'Career Level', 'education_level']
        for col in required_columns:
            if col in df.columns:
                print(f"✅ {col} found")
            else:
                print(f"❌ {col} NOT found")
                
        # Check if 'applicants' might be named differently
        print("\nPotential 'applicants' columns:")
        for col in df.columns:
            if 'app' in col.lower():
                print(f"- {col}")
                
    except Exception as e:
        print(f"Error reading file: {e}")
else:
    print("File not found!")
