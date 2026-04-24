# Multi-Broker Portfolio Holdings Extractor

## Overview

A Flask-based web application that extracts portfolio holdings data from password-protected PDF documents from multiple brokers. The application uses pdfplumber to parse PDF files, extract structured holdings information (ISIN codes, company names, current balances, rates, and values), and present the data in a user-friendly web interface with both table and JSON views.

**Last Updated**: October 20, 2025
**Status**: Multi-broker architecture fully implemented with Groww, Zerodha, AngleOne, Dhan, and MSTOCK support. Gmail auto-import with multi-user support added.

## Supported Brokers

### Groww
- **Status**: ✅ Fully functional and tested
- **Test Data**: September and August 2025 portfolio statements (password: JYQPK9320A)
- **Extraction Logic**: Parses "HOLDINGS BALANCE" sections from Groww PDF statements
- **Sample Files**: `attached_assets/groww/`

### Zerodha
- **Status**: ✅ Fully functional and tested
- **Test Data**: September 2025 transaction with holding statements (password: JYQPK9320A)
- **Extraction Logic**: Parses "Holdings as on" sections from Zerodha PDF statements
- **Sample Files**: `attached_assets/zerodha/`
- **Extraction Count**: Successfully extracts 59 holdings from test documents

### AngleOne
- **Status**: ✅ Fully functional and tested
- **Test Data**: Excel holdings statements
- **Extraction Logic**: Parses Excel (.xlsx) holdings files with pandas
- **Sample Files**: `attached_assets/angleone/`
- **Extraction Count**: Successfully extracts 7 holdings from test documents
- **Special Note**: Supports Excel format (.xlsx) in addition to PDFs

### Dhan
- **Status**: ✅ Fully functional and tested
- **Test Data**: September and August 2025 CDSL statements (password: BWKPM5493A)
- **Extraction Logic**: Parses "Holding as on" sections from Dhan CDSL PDF statements
- **Sample Files**: `attached_assets/dhan/`
- **Extraction Count**: Successfully extracts 40 holdings (Sep) and 36 holdings (Aug) from test documents

### MSTOCK
- **Status**: ✅ Fully functional and tested
- **Test Data**: September and August 2025 transaction statements (password: JYQPK9320A)
- **Extraction Logic**: Parses "STATEMENT OF HOLDINGS" sections from MSTOCK CDSL transaction statements
- **Sample Files**: `attached_assets/mstock/`
- **Extraction Count**: Successfully extracts 14 holdings (Sep) and 14 holdings (Aug) from test documents
- **Special Note**: Rate and Value fields show "N/A" as MSTOCK statements don't include pricing data

## Gmail Auto-Import Feature

### Overview
Automatically fetch portfolio statements from Gmail inbox without manual file uploads. The system connects to your Gmail account using Google OAuth, displays your name in the interface, and extracts holdings directly from email attachments.

### Setup
- **OAuth Credentials**: Google Client ID and Client Secret stored as environment secrets
- **Scopes**: Read-only Gmail access (`gmail.readonly`), user profile info (`userinfo.profile`, `userinfo.email`)
- **Authentication**: OAuth 2.0 flow with per-user token persistence
- **Multi-User Support**: Each user gets a unique session ID and separate token file in `user_tokens/` directory
- **User Display**: User's name and email from Google account displayed in UI after OAuth authentication
- **Session Management**: Flask sessions track each user independently with UUID-based session IDs

### Supported Brokers Email Patterns
| Broker | Sender Email | Subject Pattern |
|--------|--------------|-----------------|
| Zerodha | no-reply-transaction-with-holding-statement@reportsmailer.zerodha.net | Monthly Demat Transaction with Holding Statement |
| Groww | noreply@groww.in | Transaction and Holding Statement |
| Dhan | statements@dhan.co | Demat Transaction and Holding Statement for the Month ending |
| MSTOCK | no-reply@mstock.com | TRANSACTION STATEMENT |
| AngleOne | noreply@angelone.in | Holdings |

### Features
- **User PAN Input**: Users enter their PAN number in the UI to unlock PDFs
- **Latest Statement Detection**: Fetches most recent email (within 180 days / 6 months)
- **Direct Extraction**: Downloads attachment and extracts holdings automatically
- **Same Output Format**: Returns identical JSON structure as manual upload
- **PAN Validation**: Frontend validation ensures correct PAN format (5 letters + 4 digits + 1 letter)
- **Multi-User Support**: Multiple users can connect their Gmail accounts simultaneously without interfering with each other
- **Debug Logging**: Detailed Gmail search query logging for troubleshooting
- **Fallback Search**: If no emails found with subject filter, retries without subject filter

### Routes
- `/gmail` - Gmail integration interface
- `/gmail/authorize` - Start OAuth flow
- `/gmail/callback` - OAuth callback handler
- `/gmail/status` - Check authentication status
- `/gmail/fetch/<broker>` - Fetch and extract holdings for specific broker

## User Preferences

Preferred communication style: Simple, everyday language.

## Project Structure

```
.
├── app.py                          # Main Flask application with broker routing and Gmail integration
├── gmail_integration.py            # Gmail API integration module for auto-fetching statements
├── brokers/
│   ├── groww/
│   │   └── extractor.py            # Groww-specific PDF extraction logic
│   ├── zerodha/
│   │   └── extractor.py            # Zerodha-specific PDF extraction logic
│   ├── angleone/
│   │   └── extractor.py            # AngleOne-specific Excel extraction logic
│   ├── dhan/
│   │   └── extractor.py            # Dhan-specific CDSL PDF extraction logic
│   └── mstock/
│       └── extractor.py            # MSTOCK-specific CDSL transaction statement extraction logic
├── templates/
│   ├── index.html                  # Broker selection homepage
│   ├── groww/
│   │   └── index.html              # Groww extraction interface
│   ├── zerodha/
│   │   └── index.html              # Zerodha extraction interface
│   ├── angleone/
│   │   └── index.html              # AngleOne extraction interface
│   ├── dhan/
│   │   └── index.html              # Dhan extraction interface
│   ├── mstock/
│   │   └── index.html              # MSTOCK extraction interface
│   └── gmail/
│       └── index.html              # Gmail auto-import interface
└── attached_assets/
    ├── groww/                      # Groww test PDFs
    ├── zerodha/                    # Zerodha test PDFs
    ├── angleone/                   # AngleOne test Excel files
    ├── dhan/                       # Dhan test PDFs
    └── mstock/                     # MSTOCK test PDFs
```

## System Architecture

### Frontend Architecture
- **Technology**: Server-side rendered HTML templates with vanilla JavaScript
- **Rationale**: Simple multi-page application that doesn't require a complex frontend framework
- **UI Pattern**: 
  - Broker selection landing page
  - Broker-specific upload pages with progressive enhancement
  - Form-based file upload and dynamic result display
- **Styling**: Embedded CSS with gradient backgrounds and card-based layout for modern UI appearance
- **Navigation**: Easy switching between brokers with back-to-home links

### Backend Architecture
- **Framework**: Flask (Python micro-framework)
- **Routing Strategy**: 
  - `/` - Broker selection homepage
  - `/groww` - Groww extraction interface
  - `/zerodha` - Zerodha extraction interface
  - `/angleone` - AngleOne extraction interface
  - `/dhan` - Dhan extraction interface
  - `/mstock` - MSTOCK extraction interface
  - `/gmail` - Gmail auto-import interface
  - `/gmail/authorize` - Start Gmail OAuth flow
  - `/gmail/callback` - OAuth callback handler
  - `/gmail/fetch/<broker>` - Fetch latest statement from Gmail
  - `/extract/<broker>` - Broker-specific extraction endpoint
  - `/download` - JSON file download endpoint
- **Broker System**: Modular architecture with broker-specific extractors in `brokers/` folder
- **File Handling**: Temporary file storage using Python's `tempfile` module
  - **Problem Addressed**: Secure handling of uploaded files without persisting sensitive financial documents
  - **Solution**: Create temporary files that are automatically cleaned up after processing
  - **Security Benefit**: Files are removed immediately after extraction, reducing data exposure risk
- **File Size Limits**: 16MB maximum upload size to prevent resource exhaustion
- **Allowed File Types**: PDF and Excel (.xlsx) files (validated by file extension)

### Data Processing Engine
- **PDF Processing**: pdfplumber library for robust text extraction with password support
- **Excel Processing**: pandas library for structured Excel data extraction
- **Extraction Strategy**:
  - **Groww**: Parses "HOLDINGS BALANCE" sections using ISIN-based pattern matching from PDFs
  - **Zerodha**: Parses "Holdings as on" sections with tabular data extraction from PDFs
  - **AngleOne**: Extracts holdings from Excel files (.xlsx) using pandas DataFrame parsing
  - **Dhan**: Parses "Holding as on" sections from CDSL Bill-Cum-Transaction statements
  - Multi-page/multi-sheet text aggregation across all brokers
  - ISIN code detection (pattern: INE + alphanumerics) as primary identifier for holdings entries
  - Line-by-line parsing to build structured holding objects
- **Data Structure**: Returns list of dictionaries with fields: `isin_code`, `company_name`, `current_bal`, `rate`, `value`
- **Extensibility**: Each broker has its own extractor module for custom parsing logic
- **Error Handling**: User-friendly password error messages when incorrect password is provided

### Security Mechanisms
- **Password Protection**: Supports password-protected PDFs (password passed from frontend form)
- **File Validation**: Extension-based whitelist (PDF only)
- **Session Security**: Flask secret key configuration via environment variable with fallback
- **Temporary Storage**: No persistent file storage; all uploads processed in-memory or via temp files
- **Broker Isolation**: Each broker's extraction logic is isolated in separate modules

### Error Handling
- **Validation**: Client-side file type checking and server-side validation
- **HTTP Error Codes**: Appropriate 400 responses for invalid requests
- **File Cleanup**: Guaranteed cleanup with try-finally pattern to remove temporary files even on errors
- **Broker-Specific Errors**: Detailed error messages with broker context

## External Dependencies

### Python Libraries
- **Flask**: Web framework for HTTP routing and request handling
- **pdfplumber**: PDF text extraction with password support
- **pandas**: Excel file processing and data manipulation
- **openpyxl**: Excel file reading library (dependency for pandas)
- **Werkzeug**: Secure filename handling (included with Flask)
- **tempfile**: Python standard library for temporary file management
- **requests**: HTTP library for testing and integration

### File Storage
- **Temporary Storage**: OS-level temporary directory (no persistent storage)
- **Sample Assets**: Development/test PDFs stored in `attached_assets/<broker>/` directories

### Environment Variables
- **SESSION_SECRET**: Flask session encryption key (defaults to 'dev-secret-key' for development)
- **GOOGLE_CLIENT_ID**: Google OAuth Client ID for Gmail integration
- **GOOGLE_CLIENT_SECRET**: Google OAuth Client Secret for Gmail integration

## Adding a New Broker

To add support for a new broker:

1. **Create Broker Folder**: `mkdir brokers/<broker_name>`
2. **Create Extractor**: Create `brokers/<broker_name>/extractor.py` with `extract_holdings()` function
3. **Create Template**: Create `templates/<broker_name>/index.html` (copy from existing broker and modify)
4. **Add Route**: Add route in `app.py` for `/<broker_name>`
5. **Update Home Page**: Add broker card to `templates/index.html`
6. **Test Data**: Add sample PDFs to `attached_assets/<broker_name>/`

## API Endpoints

### GET /
Broker selection homepage

### GET /groww
Groww extraction interface

### GET /zerodha
Zerodha extraction interface

### POST /extract/<broker>
Extract holdings from uploaded PDF
- **Parameters**: 
  - `file`: PDF file (multipart/form-data)
  - `password`: Optional PDF password (form field)
- **Returns**: JSON with holdings array, count, and broker name

### POST /download
Download extracted holdings as JSON file
- **Parameters**: 
  - `holdings`: Array of holding objects (JSON body)
  - `broker`: Broker name for filename (JSON body)
- **Returns**: JSON file download

## Development Notes

- Each broker's extraction logic is completely independent
- The main app.py dynamically imports the correct extractor based on the URL route
- All templates share similar structure for consistency but can be customized per broker
- Test PDFs should be stored in broker-specific folders under `attached_assets/`
