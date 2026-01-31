
import pandas as pd
import sys

file_path = r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA\BCA Sem 6 Bulk Student Data 2026.xlsx"

try:
    print(f"Reading file: {file_path}")
    df = pd.read_excel(file_path)
    print("\n--- Columns ---")
    print(df.columns.tolist())
    
    print("\n--- First 5 Rows ---")
    print(df.head().to_string())
    
    # Try to find Roll No 1
    # Check for likely column names for Roll No and Name
    roll_col = next((c for c in df.columns if 'roll' in c.lower()), None)
    name_col = next((c for c in df.columns if 'name' in c.lower() or 'student' in c.lower()), None)
    
    if roll_col:
        print(f"\n--- Checking for Roll No 1 in column '{roll_col}' ---")
        # Ensure roll column is treated as string for comparison or int
        try:
            roll_1 = df[df[roll_col].astype(str).str.strip() == '1']
            if not roll_1.empty:
                print("Found Roll No 1:")
                print(roll_1.to_string())
            else:
                print("Roll No 1 not found in file.")
        except Exception as e:
            print(f"Error filtering for Roll No 1: {e}")
            
except Exception as e:
    print(f"Error reading Excel file: {e}")
