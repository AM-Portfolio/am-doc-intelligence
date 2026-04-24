import pdfplumber
import pandas as pd
import re
import json
from pdfminer.pdfdocument import PDFPasswordIncorrect
# PdfminerException moved in recent pdfplumber versions, catching general exception instead

def extract_holdings(file_path, password=None):
    """
    Extract portfolio holdings from Dhan broker document
    
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
            
            # Find the "Holding as on" section
            holding_match = re.search(r'Holding as on.*?\n(.*)', full_text, re.DOTALL)
            if not holding_match:
                return holdings
            
            # Get the text after "Holding as on"
            holdings_section = holding_match.group(1)
            
            # Split into lines
            lines = holdings_section.split('\n')
            
            # Track if we're in the holdings table
            in_holdings_table = False
            
            for line in lines:
                # Skip the header line
                if 'Sr.' in line and 'ISIN Code' in line and 'Company Name' in line:
                    in_holdings_table = True
                    continue
                
                # Stop if we hit the end of the document or a new section
                if in_holdings_table and (line.strip() == '' or 'Page' in line or '----' in line):
                    continue
                
                if not in_holdings_table:
                    continue
                
                # Parse holdings line - format: Sr. ISIN Code Company Name Free Bal Pldg Bal Demat Remat LockIn Rate Value
                # Example: 1 INE748C01038 3I INFOTECH-EQ10/- 500.00 21.55 10775.00
                # Example: 4 INE885A01032 AMARA RAJA EQ 1/- 30.00 989.25 29677.50
                
                # Match lines starting with number followed by ISIN code (INE...)
                match = re.match(r'^\s*(\d+)\s+(INE[A-Z0-9]+)\s+(.+?)\s+([\d,]+\.?\d*)\s+.*?([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$', line.strip())
                
                if match:
                    sr_no = match.group(1)
                    isin_code = match.group(2)
                    company_name = match.group(3).strip()
                    current_bal = match.group(4).replace(',', '')
                    rate = match.group(5).replace(',', '')
                    value = match.group(6).replace(',', '')
                    
                    holdings.append({
                        'isin_code': isin_code,
                        'company_name': company_name,
                        'current_bal': current_bal,
                        'rate': rate,
                        'value': value
                    })
        
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
