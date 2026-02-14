import pandas as pd
import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

file_path = r'c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA\BCA Staff info.xlsx'

def inspect_excel():
    try:
        xl = pd.ExcelFile(file_path)
        sheets = xl.sheet_names
        result = {}
        for sheet in sheets:
            df = pd.read_excel(file_path, sheet_name=sheet)
            result[sheet] = {
                "columns": df.columns.tolist(),
                "row_count": len(df),
                "sample": df.head(3).to_dict(orient='records')
            }
        print(json.dumps(result, indent=2, cls=DateTimeEncoder))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_excel()
