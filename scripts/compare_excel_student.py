
import pandas as pd

excel_path = r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA Semester 4 Updated Data 2026 Feb.xlsx"
df = pd.read_excel(excel_path)

# Look for Roll Number 1 in Division A
# Based on previous imports, the columns are likely 'Roll No', 'Division', 'Student Name', 'Surname'
print("Columns found in Excel:", df.columns.tolist())

# Filter for Roll No 1 and Division A
# Note: Excel might have 'Roll No' as float or int, and 'Division' as 'A'
res = df[(df['Roll No'].astype(str) == '1') & (df['Division'].astype(str).str.upper() == 'A')]

if not res.empty:
    student = res.iloc[0]
    print(f"Excel Student: {student.get('Student Name')} {student.get('Surname')}")
else:
    print("Roll Number 1 in Division A not found in Excel.")
