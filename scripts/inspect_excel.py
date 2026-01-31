import pandas as pd
import os

file_path = r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA\BCA Sem 2 Bulk Student Data 2026.xlsx"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
else:
    try:
        df = pd.read_excel(file_path)
        print("Columns:", df.columns.tolist())
        print("First 5 rows:")
        print(df.head().to_string())
    except Exception as e:
        print(f"Error reading excel: {e}")
