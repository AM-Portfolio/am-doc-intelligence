import xlrd
import sys

def read_excel(file_path):
    print(f"Reading {file_path}")
    try:
        wb = xlrd.open_workbook(file_path)
        print("Sheets:", wb.sheet_names())
        for sheet_name in wb.sheet_names():
            sheet = wb.sheet_by_name(sheet_name)
            print(f"\n--- Sheet: {sheet_name} ---")
            for i in range(min(20, sheet.nrows)):
                print(f"Row {i}: {sheet.row_values(i)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    read_excel(sys.argv[1])
