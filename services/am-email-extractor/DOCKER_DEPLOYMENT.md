# Docker Deployment Guide

## 🐳 Quick Start

### 1. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required Variables:**
- `GOOGLE_CLIENT_ID` - From Google Cloud Console
- `GOOGLE_CLIENT_SECRET` - From Google Cloud Console  
- `JWT_SECRET` - **MUST match your main backend** (api.munish.org)
- `ALLOWED_ORIGINS` - Your Flutter app URL (http://localhost:3000)

### 2. Build the Docker Image

```bash
docker-compose build
```

### 3. Run the Container

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f gmail-extractor

# Stop the service
docker-compose down
```

## 🌐 Internal Network Configuration

### Option A: Standalone Deployment

Use the current `docker-compose.yml` as-is. The service will be available at:
- **Internal:** `http://gmail-extractor:8080`
- **External:** `http://localhost:8080` (if ports are exposed)

### Option B: Join Existing Network (Recommended)

If your main backend (api.munish.org) is also containerized:

1. **Update `docker-compose.yml`:**
   ```yaml
   networks:
     app-network:
       external: true
       name: munish-network  # Your existing network name
   ```

2. **Remove port exposure:**
   ```yaml
   # Comment out this line for internal-only access
   # ports:
   #   - "8080:8080"
   ```

3. **Access from other containers:**
   ```
   http://gmail-extractor-api:8080/api/v1/
   ```

## 📡 API Endpoints

Base URL: `http://localhost:8080/api/v1`

### Health Check
```bash
GET /api/v1/health
Response: {"status": "healthy", "version": "1.0.0"}
```

### Gmail Authentication
```bash
# Get Gmail OAuth URL
GET /api/v1/gmail/connect
Headers: Authorization: Bearer <jwt-token>
Response: {"auth_url": "https://accounts.google.com/..."}

# Check Gmail connection status
GET /api/v1/gmail/status
Headers: Authorization: Bearer <jwt-token>
Response: {"connected": true, "email": "user@gmail.com"}

# Disconnect Gmail
DELETE /api/v1/gmail/disconnect
Headers: Authorization: Bearer <jwt-token>
Response: {"message": "Disconnected successfully"}
```

### Extract Holdings
```bash
# Fetch from Gmail
GET /api/v1/extract/gmail/{broker}?pan=ABCDE1234F
Headers: Authorization: Bearer <jwt-token>
Brokers: groww | zerodha | angleone | dhan | mstock
Response: {
  "broker": "groww",
  "count": 15,
  "holdings": [...],
  "email_subject": "Portfolio Statement",
  "email_date": "2024-12-13",
  "filename": "portfolio.pdf"
}
```

## 🔧 Nginx Reverse Proxy (Optional)

If deploying alongside main backend:

```nginx
# Add to your existing nginx config
location /am/gmail/ {
    proxy_pass http://gmail-extractor-api:8080/api/v1/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Authorization $http_authorization;
}
```

Access via: `https://api.munish.org/am/gmail/connect`

## 🔐 Google OAuth Setup

**Add redirect URI to Google Cloud Console:**
```
http://localhost:8080/api/v1/gmail/callback
https://api.munish.org/am/gmail/callback  (production)
```

See [GMAIL_OAUTH_SETUP.md](GMAIL_OAUTH_SETUP.md) for detailed OAuth setup.

## 📊 Monitoring

### View Logs
```bash
# Real-time logs
docker-compose logs -f gmail-extractor

# Last 100 lines
docker-compose logs --tail=100 gmail-extractor
```

### Health Check
```bash
curl http://localhost:8080/api/v1/health
```

### Container Status
```bash
docker ps | grep gmail-extractor
```

## 🛠️ Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs gmail-extractor

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### "JWT verification failed"
- Ensure `JWT_SECRET` matches your main backend
- Check token is being sent in `Authorization: Bearer <token>` header

### "CORS error" from Flutter app
-Check `ALLOWED_ORIGINS` includes your Flutter app URL
- Verify URL format matches exactly (no trailing slash)

### Gmail OAuth errors
- Verify redirect URIs in Google Cloud Console
- Check `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct

## 🚀 Production Deployment

1. **Set environment to production:**
   ```bash
   FLASK_ENV=production
   ```

2. **Use Docker secrets for sensitive data:** (Docker Swarm)
   ```yaml
   secrets:
     - jwt_secret
     - google_client_secret
   ```

3. **Enable HTTPS only:**
   - Configure SSL certificates
   - Update redirect URIs to HTTPS

4. **Scale if needed:**
   ```bash
   docker-compose up -d --scale gmail-extractor=3
   ```

## 📝 Next Steps

1. Configure environment variables in `.env`
2. Build and run with `docker-compose up -d`
3. Test health endpoint: `curl http://localhost:8080/api/v1/health`
4. Integrate with Flutter app (see API endpoints above)
5. Update Google OAuth redirect URIs
