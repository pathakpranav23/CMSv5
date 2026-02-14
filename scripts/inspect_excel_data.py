
import pandas as pd

excel_path = r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA Semester 4 Updated Data 2026 Feb.xlsx"
df = pd.read_excel(excel_path)

# Show first 5 students
print("--- Excel First 5 Students ---")
print(df[['RollNo', 'Student Name', 'Surname', 'Enrollment Number']].head(5))

# Check for SIDDHARTHBHAI in Excel
res = df[df['Student Name'].str.contains('SIDDHARTH', case=False, na=False)]
if not res.empty:
    print("\n--- Found SIDDHARTH in Excel ---")
    print(res[['RollNo', 'Student Name', 'Surname', 'Enrollment Number']])
else:
    print("\nSIDDHARTH not found in Excel.")
