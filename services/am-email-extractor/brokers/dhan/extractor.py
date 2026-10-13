import re
import json

try:
    from pdfminer.pdfdocument import PDFPasswordIncorrect
except ImportError:  # local unit tests without pdfminer
    class PDFPasswordIncorrect(Exception):
        pass

# Indian / western thousand separators, optional trailing %


_NUM = r'[\d,]+\.?\d*%?'
# Current Dhan Demat Holding Summary rows, e.g.:
# 1 listed INE931S01010 Adani Energy Solutions 18.00 0.00 ... 18.00 1,436.10 25,849.80 1.01%
_NEW_ROW = re.compile(
    rf'^\s*(\d+)\s+\S+\s+(IN[A-Z0-9]+)\s+(.+?)\s+'
    rf'({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})\s+'
    rf'({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})\s*$'
)
# Legacy CDSL-style rows used by older Dhan statements
_LEGACY_ROW = re.compile(
    r'^\s*(\d+)\s+(INE[A-Z0-9]+)\s+(.+?)\s+([\d,]+\.?\d*)\s+.*?([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$'
)


def _num(value: str) -> str:
    """Normalize numeric string (strip commas / %); keep as string for API compatibility."""
    return (value or '').replace(',', '').replace('%', '').strip()


def _parse_new_row(line: str):
    match = _NEW_ROW.match(line.strip())
    if not match:
        return None
    isin_code = match.group(2)
    company_name = match.group(3).strip()
    # groups 4..9 = free/locked/.../cusa, 10=total, 11=close, 12=valuation, 13=%
    current_bal = _num(match.group(10))
    rate = _num(match.group(11))
    value = _num(match.group(12))
    try:
        if float(current_bal) <= 0:
            return None
    except ValueError:
        return None
    return {
        'isin_code': isin_code,
        'company_name': company_name,
        'current_bal': current_bal,
        'rate': rate,
        'value': value,
    }


def _parse_legacy_row(line: str):
    match = _LEGACY_ROW.match(line.strip())
    if not match:
        return None
    return {
        'isin_code': match.group(2),
        'company_name': match.group(3).strip(),
        'current_bal': _num(match.group(4)),
        'rate': _num(match.group(5)),
        'value': _num(match.group(6)),
    }


def extract_holdings(file_path, password=None):
    """
    Extract portfolio holdings from Dhan broker PDF (current Holding Summary + legacy).
    """
    holdings = []

    try:
        import pdfplumber

        with pdfplumber.open(file_path, password=password) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            # Prefer current Dhan layout ("Holding Summary as on")
            if re.search(r'Holding Summary as on', full_text, re.IGNORECASE):
                for line in full_text.split('\n'):
                    row = _parse_new_row(line)
                    if row:
                        holdings.append(row)
                if holdings:
                    return holdings

            # Legacy: "Holding as on" + ISIN Code header table
            holding_match = re.search(r'Holding as on.*?\n(.*)', full_text, re.DOTALL | re.IGNORECASE)
            if not holding_match:
                # Last resort: scan every line with both parsers
                for line in full_text.split('\n'):
                    row = _parse_new_row(line) or _parse_legacy_row(line)
                    if row:
                        holdings.append(row)
                return holdings

            holdings_section = holding_match.group(1)
            in_holdings_table = False
            for line in holdings_section.split('\n'):
                if 'Sr.' in line and 'ISIN' in line and ('Company Name' in line or 'Security Name' in line):
                    in_holdings_table = True
                    continue
                if not in_holdings_table:
                    # New-format rows can appear without the old header gate
                    row = _parse_new_row(line)
                    if row:
                        holdings.append(row)
                    continue
                if line.strip() == '' or line.strip().startswith('Total') or 'Client code:' in line:
                    continue
                row = _parse_new_row(line) or _parse_legacy_row(line)
                if row:
                    holdings.append(row)

        return holdings

    except (PDFPasswordIncorrect, Exception) as e:
        if "password" in str(e).lower():
            raise Exception("Incorrect password. Please enter the correct password to unlock the PDF.")
        raise Exception(f"Error extracting holdings: {str(e)}")


def extract_holdings_to_json(file_path, password=None):
    """Extract holdings and return as JSON string."""
    holdings = extract_holdings(file_path, password)
    return json.dumps(holdings, indent=2)
