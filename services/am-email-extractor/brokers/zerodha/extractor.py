import pdfplumber
import re
import json
from pdfminer.pdfdocument import PDFPasswordIncorrect
# PdfminerException moved in recent pdfplumber versions, catching general exception instead

def extract_holdings(pdf_path, password=None):
    """
    Extract portfolio holdings from Zerodha broker PDF document
    
    Args:
        pdf_path: Path to the PDF file
        password: Password for encrypted PDFs
    
    Returns:
        List of dictionaries containing holdings information
    """
    holdings = []
    
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            full_text = ""
            
            # Extract text from all pages
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Find the Holdings section
            holdings_match = re.search(r'Holdings as on.*?:', full_text, re.IGNORECASE)
            
            if not holdings_match:
                return holdings
            
            # Extract text after "Holdings as on" section
            holdings_section_start = holdings_match.end()
            holdings_text = full_text[holdings_section_start:]
            
            # Split into lines
            lines = holdings_text.split('\n')
            
            # ISIN pattern: INE followed by alphanumerics
            isin_pattern = re.compile(r'^(INE[A-Z0-9]+)')
            
            current_holding = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line starts with ISIN code
                isin_match = isin_pattern.match(line)
                
                if isin_match:
                    # Save previous holding if exists
                    if current_holding and current_holding.get('isin_code'):
                        holdings.append(current_holding)
                    
                    # Start new holding
                    isin_code = isin_match.group(1)
                    
                    # Parse the line to extract details
                    # Format: ISIN Company Name Curr.Bal Free Pldg Earmark Demat Remat Lockin Rate Value
                    parts = line.split()
                    
                    if len(parts) >= 11:
                        # Find where the numeric values start (after company name)
                        # The company name can have multiple words
                        # Numbers typically start from the current balance
                        numeric_values = []
                        company_name_parts = []
                        found_numbers = False
                        
                        for i, part in enumerate(parts[1:], 1):
                            # Check if this looks like a number
                            if re.match(r'^\d+\.?\d*$', part):
                                found_numbers = True
                                numeric_values.append(part)
                            elif not found_numbers:
                                company_name_parts.append(part)
                            else:
                                numeric_values.append(part)
                        
                        company_name = ' '.join(company_name_parts)
                        
                        # Extract values: we need Curr.Bal (index 0), Rate (index 7), Value (index 8)
                        if len(numeric_values) >= 9:
                            current_bal = numeric_values[0]
                            rate = numeric_values[7]
                            value = numeric_values[8]
                            
                            current_holding = {
                                'isin_code': isin_code,
                                'company_name': company_name,
                                'current_bal': current_bal,
                                'rate': rate,
                                'value': value
                            }
                    else:
                        # If the line is short, company name might be on next line
                        current_holding = {
                            'isin_code': isin_code,
                            'company_name': '',
                            'current_bal': '',
                            'rate': '',
                            'value': ''
                        }
                        
                        # Try to extract company name from remaining parts
                        remaining = line[len(isin_code):].strip()
                        current_holding['company_name'] = remaining
                
                elif current_holding and current_holding.get('isin_code'):
                    # This might be a continuation line with numeric data
                    parts = line.split()
                    
                    # Check if this line has numeric values
                    numeric_values = [p for p in parts if re.match(r'^\d+\.?\d*$', p)]
                    
                    if len(numeric_values) >= 9:
                        # This line has the data
                        current_holding['current_bal'] = numeric_values[0]
                        current_holding['rate'] = numeric_values[7]
                        current_holding['value'] = numeric_values[8]
                    elif not numeric_values and not current_holding['company_name']:
                        # This might be the company name
                        current_holding['company_name'] = line
            
            # Add the last holding
            if current_holding and current_holding.get('isin_code'):
                holdings.append(current_holding)
        
        return holdings
    
    except (PDFPasswordIncorrect, Exception) as e:
        if "password" in str(e).lower():
            raise Exception("Incorrect password. Please enter the correct password to unlock the PDF.")
        raise Exception(f"Error extracting holdings: {str(e)}")


def extract_holdings_to_json(pdf_path, password=None):
    """
    Extract holdings and return as JSON string
    """
    holdings = extract_holdings(pdf_path, password)
    return json.dumps(holdings, indent=2)
