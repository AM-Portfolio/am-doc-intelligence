"""Zerodha holdings extraction from Holding Statement PDF or holdings Excel."""
from __future__ import annotations

import json
import os
import re

try:
    from pdfminer.pdfdocument import PDFPasswordIncorrect
except ImportError:  # local unit tests without pdfminer
    class PDFPasswordIncorrect(Exception):
        pass


_ISIN_RE = re.compile(r'\b(IN[A-Z0-9]{9,12})\b')
_NUM_TOKEN = re.compile(r'^[\d,]+\.?\d*$')
_HOLDINGS_HEADER = re.compile(
    r'Holdings\s+as\s+on|Equity\s+Holdings|Current\s+Holdings|Holding\s+Statement',
    re.IGNORECASE,
)


def _clean_num(token: str) -> str:
    return (token or '').replace(',', '').strip()


def _is_excel(path: str) -> bool:
    lower = (path or '').lower()
    return lower.endswith('.xlsx') or lower.endswith('.xls')


def _parse_numeric_tail(parts):
    """
    Split ISIN-line tokens into company name + numeric columns.
    Prefer Curr.Bal at first number, Rate/Value as last two numerics when enough cols.
    """
    numeric_values = []
    company_name_parts = []
    found_numbers = False
    for part in parts:
        if _NUM_TOKEN.match(part.replace(',', '')):
            found_numbers = True
            numeric_values.append(_clean_num(part))
        elif not found_numbers:
            company_name_parts.append(part)
        else:
            # Mixed token after numbers started — keep as numeric string if possible
            cleaned = _clean_num(part)
            if _NUM_TOKEN.match(cleaned):
                numeric_values.append(cleaned)
            else:
                numeric_values.append(cleaned)

    company_name = ' '.join(company_name_parts).strip()
    if not numeric_values:
        return company_name, None, None, None

    current_bal = numeric_values[0]
    rate = None
    value = None
    if len(numeric_values) >= 3:
        rate = numeric_values[-2]
        value = numeric_values[-1]
    elif len(numeric_values) >= 9:
        # Classic CDSL layout: Curr.Bal Free Pldg Earmark Demat Remat Lockin Rate Value
        rate = numeric_values[7]
        value = numeric_values[8]
    elif len(numeric_values) == 2:
        rate = numeric_values[1]

    return company_name, current_bal, rate, value


def _extract_from_pdf(pdf_path, password=None):
    import pdfplumber

    holdings = []
    with pdfplumber.open(pdf_path, password=password) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"

    holdings_match = _HOLDINGS_HEADER.search(full_text)
    holdings_text = full_text[holdings_match.end():] if holdings_match else full_text
    lines = holdings_text.split('\n')

    # Accept INE* equity and INF* (ETF/fund) ISINs that appear in Zerodha statements.
    isin_line = re.compile(r'^(IN[A-Z0-9]+)\b')
    current_holding = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Stop at common footers
        if re.match(r'^(Notes?|Disclaimer|Page\s+\d+|Total\s+Value)\b', line, re.IGNORECASE):
            if current_holding and current_holding.get('isin_code') and current_holding.get('current_bal'):
                holdings.append(current_holding)
                current_holding = None
            if re.match(r'^(Notes?|Disclaimer)\b', line, re.IGNORECASE):
                break
            continue

        isin_match = isin_line.match(line)
        if isin_match:
            if current_holding and current_holding.get('isin_code') and current_holding.get('current_bal'):
                holdings.append(current_holding)

            isin_code = isin_match.group(1)
            parts = line.split()
            company_name, current_bal, rate, value = _parse_numeric_tail(parts[1:])
            current_holding = {
                'isin_code': isin_code,
                'company_name': company_name or '',
                'current_bal': current_bal or '',
                'rate': rate or '',
                'value': value or '',
            }
            continue

        if current_holding and current_holding.get('isin_code'):
            parts = line.split()
            numeric_values = [_clean_num(p) for p in parts if _NUM_TOKEN.match(p.replace(',', ''))]
            if len(numeric_values) >= 2 and not current_holding.get('current_bal'):
                company_name, current_bal, rate, value = _parse_numeric_tail(parts)
                if company_name and not current_holding.get('company_name'):
                    current_holding['company_name'] = company_name
                if current_bal:
                    current_holding['current_bal'] = current_bal
                if rate:
                    current_holding['rate'] = rate
                if value:
                    current_holding['value'] = value
            elif not numeric_values and not current_holding.get('company_name'):
                current_holding['company_name'] = line

    if current_holding and current_holding.get('isin_code') and current_holding.get('current_bal'):
        holdings.append(current_holding)

    # Drop incomplete rows
    return [
        h for h in holdings
        if h.get('isin_code') and h.get('current_bal')
    ]


def _col_map(columns):
    """Map header names → logical fields for Zerodha holdings Excel."""
    mapping = {}
    for idx, raw in enumerate(columns):
        name = str(raw or '').strip().lower()
        if not name or name == 'nan':
            continue
        if name in ('isin', 'isin code', 'isin_code'):
            mapping['isin'] = idx
        elif name in ('symbol', 'trading symbol', 'tradingsymbol'):
            mapping['symbol'] = idx
        elif name in ('stock name', 'company name', 'name', 'instrument'):
            mapping['name'] = idx
        elif name in ('quantity', 'qty', 'qty.', 'available quantity', 'free qty'):
            mapping['qty'] = idx
        elif name in ('average price', 'avg price', 'avg. price', 'avg buy price', 'average buy price'):
            mapping['avg'] = idx
        elif name in ('ltp', 'last price', 'close price', 'closing price', 'price'):
            mapping['ltp'] = idx
        elif name in ('current value', 'cur. val', 'value', 'market value'):
            mapping['value'] = idx
        elif name in ('invested', 'investment', 'investment value'):
            mapping['invested'] = idx
    return mapping


def _extract_from_excel(file_path, password=None):
    import pandas as pd

    # password unused for typical Zerodha xlsx exports; kept for API symmetry
    _ = password
    holdings = []
    # Try first few sheets / header rows (Zerodha tax/holdings often deep headers)
    xl = pd.ExcelFile(file_path)
    for sheet in xl.sheet_names[:5]:
        for header_row in range(0, 30):
            try:
                df = pd.read_excel(file_path, sheet_name=sheet, header=header_row)
            except Exception:
                continue
            if df is None or df.empty:
                continue
            colmap = _col_map(list(df.columns))
            if 'isin' not in colmap and 'symbol' not in colmap:
                continue
            if 'qty' not in colmap:
                continue

            for _, row in df.iterrows():
                isin = ''
                if 'isin' in colmap:
                    raw_isin = row.iloc[colmap['isin']]
                    if pd.notna(raw_isin):
                        isin = str(raw_isin).strip().upper()
                if isin and not _ISIN_RE.search(isin):
                    # Sometimes ISIN cell has extra text
                    m = _ISIN_RE.search(isin)
                    isin = m.group(1) if m else ''
                name = ''
                if 'name' in colmap and pd.notna(row.iloc[colmap['name']]):
                    name = str(row.iloc[colmap['name']]).strip()
                symbol = ''
                if 'symbol' in colmap and pd.notna(row.iloc[colmap['symbol']]):
                    symbol = str(row.iloc[colmap['symbol']]).strip()
                qty_raw = row.iloc[colmap['qty']] if 'qty' in colmap else None
                if pd.isna(qty_raw):
                    continue
                try:
                    qty = float(str(qty_raw).replace(',', ''))
                except ValueError:
                    continue
                if qty <= 0:
                    continue
                if not isin and not symbol:
                    continue

                holding = {
                    'isin_code': isin or '',
                    'company_name': name or symbol,
                    'symbol': symbol or None,
                    'current_bal': str(qty),
                    'rate': '',
                    'value': '',
                }
                if 'avg' in colmap and pd.notna(row.iloc[colmap['avg']]):
                    holding['avg_price'] = _clean_num(str(row.iloc[colmap['avg']]))
                    holding['rate'] = holding['avg_price']
                if 'ltp' in colmap and pd.notna(row.iloc[colmap['ltp']]):
                    ltp = _clean_num(str(row.iloc[colmap['ltp']]))
                    if 'avg' in colmap:
                        # keep rate as avg; LTP goes via value if needed
                        holding['ltp'] = ltp
                    else:
                        holding['rate'] = ltp
                if 'value' in colmap and pd.notna(row.iloc[colmap['value']]):
                    holding['value'] = _clean_num(str(row.iloc[colmap['value']]))
                elif holding.get('ltp') and qty:
                    try:
                        holding['value'] = str(float(holding['ltp']) * qty)
                    except ValueError:
                        pass
                if 'invested' in colmap and pd.notna(row.iloc[colmap['invested']]):
                    holding['investment_value'] = _clean_num(str(row.iloc[colmap['invested']]))
                holdings.append(holding)

            if holdings:
                return holdings
    return holdings


def extract_holdings(file_path, password=None):
    """
    Extract portfolio holdings from Zerodha PDF or Excel.

    Returns list of dicts with isin_code, company_name, current_bal, rate, value
    (and avg_price when Excel provides Average Price).
    """
    try:
        if _is_excel(file_path):
            return _extract_from_excel(file_path, password)

        return _extract_from_pdf(file_path, password)

    except PDFPasswordIncorrect:
        raise Exception(
            "Incorrect password. Please enter the correct PAN/password to unlock the PDF."
        )
    except Exception as e:
        msg = str(e).lower()
        if "password" in msg:
            raise Exception(
                "Incorrect password. Please enter the correct PAN/password to unlock the PDF."
            )
        raise Exception(f"Error extracting Zerodha holdings: {str(e)}")


def extract_holdings_to_json(file_path, password=None):
    holdings = extract_holdings(file_path, password)
    return json.dumps(holdings, indent=2)
