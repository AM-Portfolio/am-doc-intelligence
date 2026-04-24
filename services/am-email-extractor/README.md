# Gmail Extractor API

A microservice API for extracting portfolio holdings from broker statements via Gmail or file upload. Supports Groww, Zerodha, AngelOne, Dhan, and Mstock.

## 🚀 Quick Start

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth secret
- `JWT_SECRET` - **Must match your main backend** (api.munish.org)
- `ALLOWED_ORIGINS` - Flutter app URL (http://localhost:3000)

### 2. Run with Docker Compose
```bash
docker-compose up -d
```

### 3. Test Health Endpoint
```bash
curl http://localhost:8080/api/v1/health
```

---

## 📡 API Endpoints

Base URL: `http://localhost:8080/api/v1`

### Health & Info
- `GET /health` - Health check (no auth)
- `GET /brokers` - List supported brokers (no auth)

### Gmail OAuth (Requires JWT)
- `GET /gmail/connect` - Start OAuth flow
- `GET /gmail/callback` - OAuth callback
- `GET /gmail/status` - Check connection
- `DELETE /gmail/disconnect` - Revoke access

### Extract Holdings (Requires JWT)
- `GET /extract/gmail/{broker}?pan=XXXXX` - Fetch from Gmail
- `POST /extract/upload/{broker}` - Upload file

Brokers: `groww`, `zerodha`, `angleone`, `dhan`, `mstock`

---

## 🧪 Testing with Postman

### Import Collection
1. Import `Gmail_Extractor_API.postman_collection.json`
2. Set variable `jwt_token` to your JWT token
3. Test endpoints starting with Health Check

### Get JWT Token (Development)
Use [jwt.io](https://jwt.io) with this payload:
```json
{
  "user_id": "test-user-123",
  "iat": 1616239022,
  "exp": 9999999999
}
```
Secret: Your `JWT_SECRET` from `.env`

### Testing Flow
1. Health Check → Verify API running
2. Gmail Connect → Get OAuth URL
3. Open URL in browser → Authorize
4. Gmail Status → Verify connected
5. Extract Holdings → Fetch broker data

---

## 🔧 Configuration

### Docker Internal Networking
When accessing your main backend from Docker container, use:
- ✅ `host.docker.internal` (not localhost)
- Example: `http://host.docker.internal:3000`

### Google OAuth Redirect URIs
Add to Google Cloud Console:
- Dev: `http://localhost:8080/api/v1/gmail/callback`
- Prod: `https://api.munish.org/am/gmail/callback`

---

## 📚 Documentation

- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - Detailed Docker setup
- [FLUTTER_INTEGRATION.md](FLUTTER_INTEGRATION.md) - Frontend integration guide
- [GMAIL_OAUTH_SETUP.md](GMAIL_OAUTH_SETUP.md) - OAuth configuration

---

## 🛠️ Development

### Run without Docker
```bash
pip install -r requirements.txt
python app_api.py
```

### View Logs
```bash
docker-compose logs -f gmail-extractor
```

### Rebuild Container
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 🐳 Docker Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Check status
docker-compose ps
```

---

## ⚠️ Troubleshooting

**"JWT verification failed"**
- Ensure `JWT_SECRET` matches main backend
- Check token format: `Bearer <token>`

**"CORS error"**
- Verify `ALLOWED_ORIGINS` includes your Flutter app URL

**"Gmail not connected"**
- Run `/gmail/connect` first
- Complete OAuth in browser

**Container won't start**
```bash
docker-compose logs gmail-extractor
```

---

## 📦 Project Structure

```
├── app_api.py              # Main API application
├── gmail_integration.py    # Gmail API integration
├── brokers/                # Broker-specific extractors
├── Dockerfile              # Container definition
├── docker-compose.yml      # Docker services
└── Gmail_Extractor_API.postman_collection.json
```

---

## 🔐 Security Notes

- Never commit `.env` file
- Keep OAuth credentials confidential
- JWT_SECRET must be shared securely with main backend
- Use HTTPS in production

---

## 📞 Support

For detailed guides, see:
- Docker deployment: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- Flutter integration: [FLUTTER_INTEGRATION.md](FLUTTER_INTEGRATION.md)
- OAuth setup: [GMAIL_OAUTH_SETUP.md](GMAIL_OAUTH_SETUP.md)
