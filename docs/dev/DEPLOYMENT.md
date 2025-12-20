# Deployment Guide

This guide covers deploying F1 Market to production, with a focus on Render.

## Architecture Overview

The recommended production architecture is a **two-service deployment**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌───────────────────┐               ┌───────────────────┐
│   Frontend (SPA)  │               │   Backend (API)   │
│   Static/Node.js  │  ─────────►   │   Flask/Gunicorn  │
│   gridstock.io    │   HTTP/REST   │   *.onrender.com  │
└───────────────────┘               └─────────┬─────────┘
                                              │
                                              ▼
                                    ┌───────────────────┐
                                    │    PostgreSQL     │
                                    │  Managed Database │
                                    └───────────────────┘
```

**Services:**
- **Frontend**: React SPA served as static files or via Node.js
- **Backend**: Flask API with Gunicorn WSGI server
- **Database**: Managed PostgreSQL

---

## Render Deployment

Render is the primary deployment platform. The project includes a `render.yaml` blueprint for one-click deployment.

### Prerequisites

1. A Render account (https://render.com)
2. GitHub repository connected to Render
3. Mailgun account (for OTP emails)
4. SportMonks API key (for F1 data, optional)

### Quick Deploy

1. Fork/push the repository to GitHub
2. Go to Render Dashboard → **New** → **Blueprint**
3. Connect your repository
4. Render reads `render.yaml` and creates services
5. Configure environment variables
6. Deploy

### Manual Setup

If you prefer manual setup over the Blueprint:

#### Step 1: Create PostgreSQL Database

1. Render Dashboard → **New** → **PostgreSQL**
2. Configure:
   - **Name**: `f1-market-db`
   - **Database**: `f1market`
   - **Region**: Choose closest to your users
3. Click **Create Database**
4. Copy the **Internal Database URL**

#### Step 2: Create Backend Web Service

1. Render Dashboard → **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `f1-market-api` |
| **Region** | Same as database |
| **Branch** | `main` |
| **Root Directory** | (leave empty) |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT` |

4. Add environment variables (see below)
5. Click **Create Web Service**

#### Step 3: Create Frontend Service

**Option A: Static Site** (simpler)

1. Render Dashboard → **New** → **Static Site**
2. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `f1-market` |
| **Branch** | `main` |
| **Root Directory** | `frontend` |
| **Build Command** | `npm install && npm run build` |
| **Publish Directory** | `dist` |

3. Add environment variables:
   - `VITE_API_URL`: Your backend URL (e.g., `https://f1-market-api.onrender.com`)

**Option B: Node.js Service** (more control)

1. Render Dashboard → **New** → **Web Service**
2. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `f1-market` |
| **Branch** | `main` |
| **Root Directory** | `frontend` |
| **Runtime** | Node |
| **Build Command** | `npm install && npm run build` |
| **Start Command** | `npm start` |

The `frontend/server.js` Express server handles:
- Gzip compression
- Static file caching (1 year)
- SPA fallback routing

---

## Environment Variables

### Backend (Required)

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `production` |
| `SECRET_KEY` | Flask session secret | Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `INTERNAL_PROD_DATABASE_URL` | PostgreSQL URL | From Render database |

### Backend (Optional)

| Variable | Description | Example |
|----------|-------------|---------|
| `CORS_ORIGINS` | Allowed frontend origins | `https://gridstock.io,https://www.gridstock.io` |
| `MAILGUN_API_KEY` | Mailgun API key | `key-xxx...` |
| `MAILGUN_DOMAIN` | Mailgun domain | `mg.gridstock.io` |
| `MAILGUN_FROM_EMAIL` | Sender email | `noreply@gridstock.io` |
| `OTP_ALLOWED_EMAILS` | Email allowlist | `user1@example.com,user2@example.com` |
| `SPORTSMONK_API_KEY` | F1 data API key | `xxx...` |
| `F1_CACHE_TTL_MINUTES` | Cache TTL | `10` |

### Frontend

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://f1-market-api.onrender.com` |

---

## render.yaml Blueprint

The project includes a Render Blueprint for automated deployment:

```yaml
services:
  # Backend API
  - type: web
    name: f1-market-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT
    envVars:
      - key: FLASK_ENV
        value: production
      - key: SECRET_KEY
        generateValue: true
      - key: INTERNAL_PROD_DATABASE_URL
        fromDatabase:
          name: f1-market-db
          property: connectionString

  # Frontend
  - type: web
    name: f1-market-frontend
    runtime: node
    rootDir: frontend
    buildCommand: npm install && npm run build
    startCommand: npm start
    envVars:
      - key: VITE_API_URL
        fromService:
          name: f1-market-api
          type: web
          property: host

databases:
  - name: f1-market-db
    databaseName: f1market
    plan: free
```

---

## CORS Configuration

When frontend and backend are on different domains, configure CORS:

```bash
# Single origin
CORS_ORIGINS=https://gridstock.io

# Multiple origins (comma-separated)
CORS_ORIGINS=https://gridstock.io,https://www.gridstock.io
```

If `CORS_ORIGINS` is not set, all origins are allowed (less secure but works).

---

## Session Cookie Configuration

For cross-origin authentication (frontend and API on different domains):

| Setting | Value | Reason |
|---------|-------|--------|
| `SESSION_COOKIE_SAMESITE` | `None` | Allow cross-origin requests |
| `SESSION_COOKIE_SECURE` | `True` | Required when SameSite=None |
| `SESSION_COOKIE_HTTPONLY` | `True` | Prevent XSS access |
| `WTF_CSRF_SSL_STRICT` | `False` | Disable Referer check for cross-origin |

These are configured automatically in `config.py` when `FLASK_ENV=production`.

---

## Database Initialization

After first deployment, the database needs initialization:

### Automatic (Flask-Migrate)

Tables are created automatically on first request if using Flask-Migrate.

### Manual (via Render Shell)

1. Go to your backend service in Render
2. Click **Shell** tab
3. Run:

```bash
python db/init.py
```

This creates tables and default users.

### Seed F1 Data

To populate with F1 drivers, teams, and events:

```bash
python scripts/seed_data.py 2024
```

Requires `SPORTSMONK_API_KEY` to be set.

---

## Health Checks

The backend exposes a health check endpoint:

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

Configure Render to use this for health checks:
- **Health Check Path**: `/health`

---

## Monitoring

### Render Logs

- View logs in real-time from Render Dashboard
- Filter by service (frontend/backend)
- Search for errors

### Key Metrics to Watch

- Response times
- Error rates (5xx responses)
- Database connection pool
- Memory usage

### Alerts

Set up alerts in Render for:
- Service down
- High error rate
- High memory usage

---

## Troubleshooting

### Backend Issues

**Database Connection Errors**
```
OperationalError: could not connect to server
```

- Verify `INTERNAL_PROD_DATABASE_URL` is correct
- Check database is in same region
- Ensure database is running

**Session Issues**
```
Session not persisting
```

- Verify `SECRET_KEY` is set and consistent
- Check `SESSION_COOKIE_SECURE=True` and using HTTPS
- Verify CORS allows credentials

**Build Failures**
```
ModuleNotFoundError
```

- Check all dependencies in `requirements.txt`
- Verify Python version compatibility
- Check for missing system dependencies

### Frontend Issues

**API Connection Errors**
```
CORS error or Network error
```

- Verify `VITE_API_URL` is correct
- Check `CORS_ORIGINS` includes your frontend domain
- Ensure backend is running

**Build Failures**
```
npm ERR! or TypeScript errors
```

- Check Node.js version (should be 18+)
- Verify all dependencies in `package.json`
- Run `npm install` locally to test

**Routing Issues (404 on refresh)**

If using static hosting without `server.js`:
- Add `_redirects` file for SPA routing
- Or use Node.js service with Express

### OTP Not Received

- Check Mailgun is configured
- Verify domain is verified in Mailgun
- Check `OTP_ALLOWED_EMAILS` if set
- Check Mailgun logs for delivery status

---

## Alternative Deployment Options

### Heroku

```bash
# Create Heroku app
heroku create f1-market-api

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Deploy
git push heroku main
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
```

Build and run:

```bash
docker build -t f1-market-api .
docker run -p 8000:8000 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret \
  -e INTERNAL_PROD_DATABASE_URL=your-db-url \
  f1-market-api
```

### AWS Elastic Beanstalk

1. Install EB CLI: `pip install awsebcli`
2. Initialize: `eb init -p python-3.11 f1-market`
3. Create environment: `eb create f1-market-prod`
4. Set environment variables in AWS console
5. Deploy: `eb deploy`

---

## Security Checklist

Before going to production:

- [ ] `SECRET_KEY` is set to a strong random value
- [ ] `FLASK_ENV=production` is set
- [ ] HTTPS is enabled (Render does this automatically)
- [ ] `CORS_ORIGINS` restricts to your frontend domains
- [ ] `OTP_ALLOWED_EMAILS` restricts who can log in (if needed)
- [ ] Database credentials are not in code
- [ ] API keys are stored as environment variables
- [ ] Rate limiting is enabled (Flask-Limiter)

---

## Next Steps

- [Setup Guide](SETUP.md) - Local development
- [Architecture Guide](ARCHITECTURE.md) - System design
- [Testing Guide](TESTING.md) - Run tests before deploying
