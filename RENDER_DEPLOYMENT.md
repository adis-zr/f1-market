# Render Deployment Guide

This guide explains how to deploy the F1 Market application to Render.

## Architecture

You have two deployment options:

### Option 1: Two Services (Recommended)
- **Backend Service**: Flask API
- **Frontend Service**: Static site (serves built React app)

### Option 2: Single Service
- **Web Service**: Flask API that also serves the built frontend

This guide covers **Option 1** (recommended for better separation and scaling).

---

## Prerequisites

1. **PostgreSQL Database**: Create a PostgreSQL database on Render
2. **Backend Web Service**: Flask API
3. **Frontend Static Site**: React app (built and served as static files)

---

## Step 1: Create PostgreSQL Database

1. Go to your Render dashboard
2. Click "New +" → "PostgreSQL"
3. Configure:
   - **Name**: `f1-market-db` (or your preferred name)
   - **Database**: `f1market` (or your preferred name)
   - **User**: Auto-generated
   - **Region**: Choose closest to your services
4. Click "Create Database"
5. **Save the connection string** - you'll need `INTERNAL_PROD_DATABASE_URL`

---

## Step 2: Create Backend Web Service

1. Go to Render dashboard → "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure the service:

### Basic Settings
- **Name**: `f1-market-api` (or your preferred name)
- **Region**: Same as database
- **Branch**: `main` (or your default branch)
- **Root Directory**: Leave empty (root of repo)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`

### Environment Variables

Add these environment variables in the Render dashboard:

#### Required
```
FLASK_ENV=production
SECRET_KEY=<generate a random secret key, e.g., use: python -c "import secrets; print(secrets.token_hex(32))">
INTERNAL_PROD_DATABASE_URL=<from PostgreSQL service, use Internal Database URL>
```

#### Optional (but recommended)
```
# CORS (restrict frontend origins, comma-separated)
CORS_ORIGINS=https://your-frontend.onrender.com

# Mailgun (for OTP emails)
MAILGUN_API_KEY=<your-mailgun-api-key>
MAILGUN_DOMAIN=<your-mailgun-domain>
MAILGUN_FROM_EMAIL=noreply@yourdomain.com

# F1 API (SportMonks)
SPORTSMONK_API_KEY=<your-sportmonks-api-key>
F1_SPORTSMONK_BASE_URL=https://f1.sportmonks.com/api/v1.0
F1_PROVIDER=sportmonks
F1_CACHE_TTL_MINUTES=10

# Email allowlist (comma-separated)
OTP_ALLOWED_EMAILS=user1@example.com,user2@example.com
```

### Advanced Settings
- **Auto-Deploy**: `Yes` (deploys on git push)
- **Health Check Path**: `/health` (if you have a health endpoint)

4. Click "Create Web Service"

**Note**: After the backend is deployed, note its URL (e.g., `https://f1-market-api.onrender.com`)

---

## Step 3: Create Frontend Static Site

1. Go to Render dashboard → "New +" → "Static Site"
2. Connect your GitHub repository
3. Configure the service:

### Basic Settings
- **Name**: `f1-market` (or your preferred name)
- **Branch**: `main` (or your default branch)
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `frontend/dist`

### Environment Variables

Add this environment variable:

```
VITE_API_URL=<your-backend-service-url>
```

For example: `VITE_API_URL=https://f1-market-api.onrender.com`

4. Click "Create Static Site"

---

## Step 4: Configure CORS (Optional but Recommended)

If your frontend and backend are on different domains, set the `CORS_ORIGINS` environment variable in your backend service:

```
CORS_ORIGINS=https://your-frontend.onrender.com
```

For multiple origins, use comma-separated values:
```
CORS_ORIGINS=https://your-frontend.onrender.com,https://another-domain.com
```

If not set, CORS will allow all origins (works but less secure).

---

## Step 5: Database Initialization

After the first deployment, you may want to initialize the database:

1. SSH into your backend service (if available) or use Render's shell
2. Run: `python db/init.py` (optional - tables are created automatically)

---

## Environment Variables Summary

### Backend Service
| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_ENV` | Yes | Set to `production` |
| `SECRET_KEY` | Yes | Random secret for sessions |
| `INTERNAL_PROD_DATABASE_URL` | Yes | PostgreSQL connection string |
| `MAILGUN_API_KEY` | No | For sending OTP emails |
| `MAILGUN_DOMAIN` | No | Your Mailgun domain |
| `CORS_ORIGINS` | No | Comma-separated list of allowed frontend origins |
| `SPORTSMONK_API_KEY` | No | For F1 data |
| `OTP_ALLOWED_EMAILS` | No | Comma-separated email allowlist |

### Frontend Service
| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API URL |

---

## Troubleshooting

### Backend Issues

1. **Database Connection Errors**
   - Verify `INTERNAL_PROD_DATABASE_URL` is correct
   - Check that the database is in the same region
   - Ensure the database is running

2. **Session Issues**
   - Verify `SECRET_KEY` is set
   - Check CORS configuration allows credentials

3. **Build Failures**
   - Check Python version compatibility
   - Verify all dependencies in `requirements.txt`

### Frontend Issues

1. **API Connection Errors**
   - Verify `VITE_API_URL` is correct
   - Check CORS settings on backend
   - Ensure backend service is running

2. **Build Failures**
   - Check Node.js version (Render uses Node 18+ by default)
   - Verify all dependencies in `package.json`

---

## Alternative: Single Service Deployment

If you prefer a single service, you can:

1. Modify `app.py` to serve static files from `frontend/dist`
2. Add a build step that runs `cd frontend && npm install && npm run build`
3. Use a single Web Service with both build commands

This is more complex but reduces the number of services.

---

## Monitoring

- Check Render logs for both services
- Monitor database connections
- Set up health checks on `/health` endpoint

---

## Updates

After making changes:
1. Push to your repository
2. Render will automatically rebuild and redeploy
3. Frontend will rebuild with new `VITE_API_URL` if changed

