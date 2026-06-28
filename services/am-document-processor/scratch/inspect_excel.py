import pandas as pd
import sys

def read_excel(file_path):
    print(f"Reading {file_path}")
    try:
        xls = pd.ExcelFile(file_path)
        print("Sheets:", xls.sheet_names)
        for sheet in xls.sheet_names:
            print(f"\n--- Sheet: {sheet} ---")
            df = pd.read_excel(xls, sheet_name=sheet, nrows=20, header=None)
            for i, row in df.iterrows():
                print(f"Row {i}: {row.tolist()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    read_excel(sys.argv[1])
