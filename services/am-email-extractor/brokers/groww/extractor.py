import pdfplumber
import re
import json
from pdfminer.pdfdocument import PDFPasswordIncorrect
# PdfminerException moved in recent pdfplumber versions, catching general exception instead

def extract_holdings(pdf_path, password=None):
    """
    Extract portfolio holdings from Groww broker PDF document
    
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
            
            # Find the HOLDINGS BALANCE section
            holdings_match = re.search(r'HOLDINGS BALANCE\s+As on.*?\n(.*?)(?:Total|$)', 
                                      full_text, re.DOTALL)
            
            if holdings_match:
                holdings_text = holdings_match.group(1)
                
                # Split into lines and process
                lines = holdings_text.strip().split('\n')
                
                # Pattern to match holding entries
                # ISIN Code is like INE192R01011, followed by company name, then numbers
                current_holding = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if line starts with ISIN code (INE followed by alphanumeric)
                    isin_match = re.match(r'^(INE[A-Z0-9]+)\s+(.+)', line)
                    
                    if isin_match:
                        # If we have a previous holding being built, save it
                        if current_holding and 'value' in current_holding:
                            holdings.append(current_holding)
                        
                        isin_code = isin_match.group(1)
                        rest_of_line = isin_match.group(2)
                        
                        # Extract company name and numbers
                        # Pattern: Company Name followed by numbers
                        parts = rest_of_line.split()
                        
                        # Find where the numbers start (after company name)
                        company_name_parts = []
                        numbers = []
                        found_number = False
                        
                        for part in parts:
                            # Check if it's a number (including decimals)
                            if re.match(r'^\d+\.?\d*$', part):
                                found_number = True
                                numbers.append(part)
                            else:
                                if not found_number:
                                    company_name_parts.append(part)
                                else:
                                    # After numbers started, non-number means continuation
                                    numbers.append(part)
                        
                        company_name = ' '.join(company_name_parts)
                        
                        # Extract the specific fields we need:
                        # Current Bal (index 0), Rate (index -2), Value (index -1)
                        if len(numbers) >= 3:
                            current_holding = {
                                'isin_code': isin_code,
                                'company_name': company_name,
                                'current_bal': numbers[0],
                                'rate': numbers[-2],
                                'value': numbers[-1]
                            }
                        else:
                            # Store partial data, might continue on next line
                            current_holding = {
                                'isin_code': isin_code,
                                'company_name': company_name,
                                'numbers': numbers
                            }
                    elif current_holding and 'value' not in current_holding:
                        # This line might be a continuation of the previous entry
                        # Extract numbers from this line
                        numbers = re.findall(r'\d+\.?\d*', line)
                        if 'numbers' in current_holding:
                            current_holding['numbers'].extend(numbers)
                        else:
                            current_holding['numbers'] = numbers
                        
                        # Try to extract the fields
                        all_numbers = current_holding.get('numbers', [])
                        if len(all_numbers) >= 3:
                            current_holding['current_bal'] = all_numbers[0]
                            current_holding['rate'] = all_numbers[-2]
                            current_holding['value'] = all_numbers[-1]
                            del current_holding['numbers']
                
                # Don't forget the last holding
                if current_holding and 'value' in current_holding:
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
