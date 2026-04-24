import pdfplumber
import pandas as pd
import re
import json
from pdfminer.pdfdocument import PDFPasswordIncorrect
# PdfminerException moved in recent pdfplumber versions, catching general exception instead

def extract_holdings(file_path, password=None):
    """
    Extract portfolio holdings from MSTOCK broker document
    
    Args:
        file_path: Path to the PDF or Excel file
        password: Password for encrypted PDFs
    
    Returns:
        List of dictionaries containing holdings information
    """
    holdings = []
    
    try:
        # PDF file processing
        with pdfplumber.open(file_path, password=password) as pdf:
            full_text = ""
            
            # Extract text from all pages
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Find the "STATEMENT OF HOLDINGS" section
            holding_match = re.search(r'STATEMENT OF HOLDINGS.*?FROM.*?TO.*?\n(.*)', full_text, re.DOTALL | re.IGNORECASE)
            if not holding_match:
                return holdings
            
            # Get the text after "STATEMENT OF HOLDINGS"
            holdings_section = holding_match.group(1)
            
            # Split into lines
            lines = holdings_section.split('\n')
            
            # Track if we're in the holdings table
            in_holdings_table = False
            current_isin = None
            current_company = None
            line_count = 0
            
            for line in lines:
                # Skip the header line
                if 'ISIN CD' in line and 'ISIN NAME' in line:
                    in_holdings_table = True
                    continue
                
                # Stop if we hit the end marker
                if '---' in line and len(line) > 50:
                    continue
                
                # Stop at "Important Information" section
                if 'Important Information' in line:
                    break
                
                if not in_holdings_table:
                    continue
                
                # Parse holdings - MSTOCK format has holdings spread across 3 lines:
                # Line 1: ISIN CODE COMPANY NAME CURRENT_BAL FROZEN_BAL PLEDGED_BAL
                # Line 2: FREE_BAL LOCKED_IN_BAL EARMARKED_BAL
                # Line 3: LENT_BAL AVL_BAL BORROWED_BAL
                
                # Match first line with ISIN code (INE...)
                match = re.match(r'^\s*(INE[A-Z0-9]+)\s+(.+?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$', line.strip())
                
                if match:
                    current_isin = match.group(1)
                    current_company = match.group(2).strip()
                    current_bal = match.group(3).replace(',', '')
                    line_count = 1
                    
                    # Add the holding (we'll use current balance as the quantity)
                    holdings.append({
                        'isin_code': current_isin,
                        'company_name': current_company,
                        'current_bal': current_bal,
                        'rate': 'N/A',  # Not available in MSTOCK statement
                        'value': 'N/A'  # Not available in MSTOCK statement
                    })
                    current_isin = None
                    current_company = None
                    line_count = 0
        
        return holdings
    
    except (PDFPasswordIncorrect, Exception) as e:
        if "password" in str(e).lower():
            raise Exception("Incorrect password. Please enter the correct password to unlock the PDF.")
        raise Exception(f"Error extracting holdings: {str(e)}")


def extract_holdings_to_json(file_path, password=None):
    """
    Extract holdings and return as JSON string
    """
    holdings = extract_holdings(file_path, password)
    return json.dumps(holdings, indent=2)
