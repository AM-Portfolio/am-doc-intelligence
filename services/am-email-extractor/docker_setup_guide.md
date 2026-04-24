# Docker Deployment Guide - Gmail Extractor API

## Quick Start (Development)

### Using Docker Compose
The easiest way to run the entire stack:

```bash
# Start all services (API + MongoDB + Kafka + Zookeeper)
docker-compose up -d

# View logs
docker-compose logs -f gmail-extractor

# Stop services
docker-compose down
```

---

## Production Deployment

### Option 1: Docker Run (API Only)

If you have MongoDB and Kafka already running:

```bash
docker build -t gmail-extractor-api .

docker run -d \
  -p 8080:8080 \
  -e FLASK_ENV=production \
  -e PORT=8080 \
  -e JWT_SECRET="your-shared-jwt-secret" \
  -e JWT_ALGORITHM=HS256 \
  -e GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com" \
  -e GOOGLE_CLIENT_SECRET="your-client-secret" \
  -e ALLOWED_ORIGINS="https://your-frontend.com" \
  -e MONGO_URI="mongodb://mongo:27017/" \
  -e MONGO_DB_NAME="portfolio_db" \
  -e KAFKA_BOOTSTRAP_SERVERS="kafka:9092" \
  -e KAFKA_TOPIC="portfolio_updates" \
  -v gmail-tokens:/app/user_tokens \
  -v gmail-logs:/app/logs \
  --name gmail-extractor \
  gmail-extractor-api
```

### Option 2: Docker Compose (Full Stack)

Edit `docker-compose.yml` to customize, then:

```bash
docker-compose up -d
```

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET` | Shared secret with main backend | `your-secret-key` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `xxx.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Secret | `GOCSPX-xxx` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | API port |
| `FLASK_ENV` | `production` | Environment |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection |
| `MONGO_DB_NAME` | `portfolio_db` | Database name |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka servers |
| `KAFKA_TOPIC` | `portfolio_updates` | Kafka topic name |

---

## Health Check

Verify the API is running:

```bash
curl http://localhost:8080/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "gmail-extractor-api"
}
```

---

## Networking

### Connecting to Existing Infrastructure

If integrating with existing MongoDB/Kafka:

1. **Edit `docker-compose.yml`**:
   ```yaml
   services:
     gmail-extractor:
       networks:
         - external-network
   
   networks:
     external-network:
       external: true
       name: your-existing-network
   ```

2. **Update environment variables** to point to your services:
   ```yaml
   environment:
     - MONGO_URI=mongodb://your-mongo-host:27017/
     - KAFKA_BOOTSTRAP_SERVERS=your-kafka-host:9092
   ```

---

## Volumes

### Persistent Data

The API stores:
- **Gmail tokens**: `/app/user_tokens` (user OAuth credentials)
- **Logs**: `/app/logs` (application logs)

Make sure to mount these as volumes:

```yaml
volumes:
  - ./user_tokens:/app/user_tokens
  - ./logs:/app/logs
```

---

## Security Notes

1. **Always use HTTPS** in production
2. **Set `SESSION_COOKIE_SECURE=True`** when using HTTPS
3. **Keep `JWT_SECRET` secret** and sync with main backend
4. **Restrict `ALLOWED_ORIGINS`** to your actual frontend domains
5. **Use environment files** (`.env`) instead of hardcoding secrets

---

## Troubleshooting

### Kafka Connection Issues
```bash
# Check if Kafka is ready
docker-compose logs kafka | grep "started"

# Wait 30s after startup for Kafka to be ready
```

### MongoDB Connection Issues
```bash
# Test connection
docker exec -it mongodb mongosh --eval "db.serverStatus()"
```

### Gmail OAuth Issues
- Verify redirect URI in Google Cloud Console matches your deployment URL
- Check `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct
