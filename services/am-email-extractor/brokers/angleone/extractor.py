import pandas as pd
import json
import os

def extract_holdings(file_path, password=None):
    """
    Extract portfolio holdings from AngleOne broker Excel document
    
    Args:
        file_path: Path to the Excel file
        password: Password for encrypted files (not typically used for Excel)
    
    Returns:
        List of dictionaries containing holdings information
    """
    holdings = []
    
    try:
        # Read Excel file - the header row is at row 9 (0-indexed)
        df = pd.read_excel(file_path, header=9)
        
        # The first row after header contains column names, skip it
        # Data starts from row 1 onwards
        df = df.iloc[1:].reset_index(drop=True)
        
        # Get column names
        # Column 0: Scrip/Contract
        # Column 1: Company Name
        # Column 2: ISIN
        # Column 5: Quantity
        # Column 7: Avg Trading Price (rate)
        # Column 10: Market Value as of last trading day
        
        for idx, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row.iloc[2]) or str(row.iloc[2]).strip() == '':
                continue
            
            isin_code = str(row.iloc[2]).strip()
            company_name = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else ''
            
            # Get quantity (current balance)
            current_bal = str(row.iloc[5]) if not pd.isna(row.iloc[5]) else '0'
            
            # Get average trading price (rate)
            rate = str(row.iloc[7]) if not pd.isna(row.iloc[7]) else '0'
            
            # Get market value
            value = str(row.iloc[10]) if not pd.isna(row.iloc[10]) else '0'
            
            # Only add if we have valid data
            if isin_code and isin_code.startswith('INE'):
                holding = {
                    'isin_code': isin_code,
                    'company_name': company_name,
                    'current_bal': current_bal,
                    'rate': rate,
                    'value': value
                }
                holdings.append(holding)
        
        return holdings
    
    except Exception as e:
        raise Exception(f"Error extracting holdings: {str(e)}")


def extract_holdings_to_json(file_path, password=None):
    """
    Extract holdings and return as JSON string
    """
    holdings = extract_holdings(file_path, password)
    return json.dumps(holdings, indent=2)
