import pandas as pd
import json
import os
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

file_path = r'c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA Semester 4 Updated Data 2026 Feb.xlsx'

def inspect_excel(path):
    if not os.path.exists(path):
        print(f"Error: File not found at {path}")
        return

    try:
        # Load the Excel file
        xl = pd.ExcelFile(path)
        sheet_names = xl.sheet_names
        print(f"Sheets: {sheet_names}")

        summary = {}
        for sheet in sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            summary[sheet] = {
                "columns": df.columns.tolist(),
                "row_count": len(df),
                "sample": df.head(3).to_dict(orient='records')
            }
        
        print(json.dumps(summary, indent=2, cls=DateTimeEncoder))
    except Exception as e:
        print(f"Error reading excel: {str(e)}")

if __name__ == "__main__":
    inspect_excel(file_path)
