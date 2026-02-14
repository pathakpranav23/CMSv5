
import pandas as pd

excel_path = r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA Semester 4 Updated Data 2026 Feb.xlsx"
xl = pd.ExcelFile(excel_path)
print("Sheet names:", xl.sheet_names)

for sheet in xl.sheet_names:
    df = pd.read_excel(excel_path, sheet_name=sheet)
    print(f"\n--- Sheet: {sheet} ---")
    print("Columns:", df.columns.tolist())
    # Find RollNo 1
    if 'RollNo' in df.columns:
        res = df[df['RollNo'].astype(str).str.startswith('1')] # using startswith to handle potential 1.0 or '1'
        if not res.empty:
            student = res.iloc[0]
            print(f"Student in {sheet} (RollNo 1): {student.get('Student Name')} {student.get('Surname')}")
