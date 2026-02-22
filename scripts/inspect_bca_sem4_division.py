import os
import pandas as pd


def main():
    # The actual data file (not the temporary ~ file)
    path = r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA Semester 4 Updated Data 2026 Feb.xlsx"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    print(f"Loading: {path}")
    df = pd.read_excel(path)

    print("Columns:", list(df.columns))

    if "Division" not in df.columns:
        print("No 'Division' column found in this sheet.")
        return

    print("\nUnique values in Division column:")
    print(df["Division"].dropna().unique())

    print("\nValue counts in Division column:")
    print(df["Division"].value_counts(dropna=False))

    cols = [c for c in ["RollNo", "Roll No", "Student Name", "Division"] if c in df.columns]
    if cols:
        print("\nSample rows (first 10) with roll and division:")
        print(df[cols].head(10))


if __name__ == "__main__":
    main()

