# Gmail Extractor API - Backend Integration

## Overview
Microservice API for extracting broker portfolio holdings from Gmail and persisting to MongoDB with Kafka notifications.

**Base URL**: `http://your-domain:8080/api/v1`

## Authentication
All endpoints (except `/health` and `/brokers`) require JWT authentication.

**Header**: `Authorization: Bearer <JWT_TOKEN>`

The JWT must contain one of: `user_id`, `sub`, or `id` claim.

---

## API Endpoints

### Health & Info

#### `GET /health`
Health check endpoint (no auth required).

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "gmail-extractor-api"
}
```

#### `GET /brokers`
List supported brokers (no auth required).

**Response**:
```json
{
  "brokers": [
    {"id": "groww", "name": "Groww", "format": "PDF"},
    {"id": "zerodha", "name": "Zerodha", "format": "PDF"},
    {"id": "angleone", "name": "AngelOne", "format": "Excel"},
    {"id": "dhan", "name": "Dhan", "format": "PDF"},
    {"id": "mstock", "name": "Mstock", "format": "PDF"}
  ]
}
```

---

### Gmail OAuth

#### `GET /gmail/connect`
Start Gmail OAuth flow.

**Response**:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "random-state-token"
}
```

#### `GET /gmail/callback`
OAuth callback (handled automatically by Google redirect).

#### `GET /gmail/status`
Check Gmail connection status.

**Response**:
```json
{
  "connected": true,
  "email": "user@gmail.com",
  "name": "John Doe"
}
```

#### `DELETE /gmail/disconnect`
Disconnect Gmail account.

**Response**:
```json
{
  "message": "Gmail disconnected successfully"
}
```

---

### Portfolio Extraction

#### `GET /extract/gmail/<broker>`
Extract holdings from Gmail for specified broker.

**Path Params**:
- `broker`: One of `zerodha`, `groww`, `angleone`, `dhan`, `mstock`

**Query Params**:
- `pan`: PAN number (required for all except AngelOne)

**Response (Success)**:
```json
{
  "success": true,
  "broker": "zerodha",
  "count": 50,
  "holdings": [...],
  "metadata": {
    "email_subject": "Monthly Statement...",
    "email_date": "Wed, 20 Dec 2023...",
    "filename": "statement.pdf",
    "source": "gmail"
  },
  "db_id": "65b2f0a2..."
}
```

**Errors**:
- `400`: Invalid broker or missing PAN
- `401`: Gmail not connected
- `404`: No recent emails found

#### `POST /extract/upload/<broker>`
Upload and extract holdings from file.

**Path Params**:
- `broker`: One of `zerodha`, `groww`, `angleone`, `dhan`, `mstock`

**Body** (multipart/form-data):
- `file`: PDF or Excel file
- `password`: (optional) File password

**Response**: Same as `/extract/gmail/<broker>`

---

## Data Flow

1. **User Extraction Request** → API validates auth
2. **Gmail Search** → Fetch latest statement
3. **PDF/Excel Parsing** → Extract holdings
4. **MongoDB Persistence** → Save to `portfolio_holdings` collection
5. **Kafka Event** → Publish to `portfolio_updates` topic
6. **API Response** → Return holdings + `db_id`

---

## Kafka Event Schema

**Topic**: `portfolio_updates`

**Message**:
```json
{
  "event": "PORTFOLIO_UPDATED",
  "user_id": "user_123",
  "broker": "zerodha",
  "status": "SUCCESS",
  "db_id": "65b2f0a2...",
  "timestamp": "2023-12-23T10:00:00Z",
  "error": null
}
```

---

## MongoDB Schema

**Collection**: `portfolio_holdings`

**Document**:
```json
{
  "_id": "65b2f0a2...",
  "user_id": "user_123",
  "broker": "zerodha",
  "holdings": [
    {
      "symbol": "RELIANCE",
      "quantity": 10,
      "avg_price": 2450.50,
      ...
    }
  ],
  "extracted_at": "2023-12-23T10:00:00Z",
  "source": "gmail_extraction",
  "metadata": {
    "email_subject": "...",
    "email_date": "...",
    "filename": "..."
  }
}
```
