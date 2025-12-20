# Development Setup Guide

This guide walks you through setting up F1 Market for local development.

## Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | 3.10+ | Required for backend |
| Node.js | 18+ | Required for frontend |
| npm | 9+ | Comes with Node.js |
| Git | 2.x | For version control |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/f1-market.git
cd f1-market

# Backend setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
cd ..

# Start both servers (in separate terminals)
python app.py          # Terminal 1: Backend on http://localhost:5000
cd frontend && npm run dev  # Terminal 2: Frontend on http://localhost:5173
```

Open http://localhost:5173 in your browser.

---

## Detailed Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/f1-market.git
cd f1-market
```

### 2. Backend Setup

Create and activate a Python virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Environment Variables (Optional)

Create a `.env` file in the project root for local configuration:

```bash
# Email Authentication (Mailgun) - Optional for local dev
MAILGUN_API_KEY=your_mailgun_key
MAILGUN_DOMAIN=mg.yourdomain.com

# F1 Data (SportMonks) - Optional
SPORTSMONK_API_KEY=your_api_key

# Restrict OTP to specific emails - Optional
OTP_ALLOWED_EMAILS=user@example.com,admin@example.com
```

> **Note:** Without Mailgun configured, OTP codes are logged to the console for local development.

---

## Environment Variables Reference

### Core Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | No | `development` | Set to `production` for production |
| `SECRET_KEY` | Prod only | Auto-generated | Flask session secret (required in production) |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INTERNAL_PROD_DATABASE_URL` | Prod only | SQLite | PostgreSQL connection URL for production |

In development, SQLite is used automatically (`app.db` in project root).

### Email (Mailgun)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAILGUN_API_KEY` | No | None | Mailgun API key for sending OTP emails |
| `MAILGUN_DOMAIN` | No | None | Mailgun domain (e.g., `mg.yourdomain.com`) |
| `MAILGUN_FROM_EMAIL` | No | Auto | Sender email (derived from domain if not set) |
| `OTP_ALLOWED_EMAILS` | No | All | Comma-separated list of allowed email addresses |

### F1 Data (SportMonks)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SPORTSMONK_API_KEY` | No | None | SportMonks API key for F1 data |
| `F1_SPORTSMONK_BASE_URL` | No | `https://f1.sportmonks.com/api/v1.0` | API base URL |
| `F1_CACHE_TTL_MINUTES` | No | `10` | Cache TTL for API responses |
| `F1_PROVIDER` | No | `sportmonks` | F1 data provider |

### CORS (Production)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | No | All | Comma-separated list of allowed frontend origins |

---

## Running the Application

### Backend Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux

# Start Flask development server
python app.py
```

The backend runs on **http://localhost:5000** with:
- Auto-reload on code changes
- Debug mode enabled
- SQLite database (auto-created)

### Frontend Server

```bash
cd frontend
npm run dev
```

The frontend runs on **http://localhost:5173** with:
- Hot module replacement (HMR)
- Vite dev server
- Proxied API requests to backend

### Both Servers Together

You need two terminal windows:

```bash
# Terminal 1: Backend
python app.py

# Terminal 2: Frontend
cd frontend && npm run dev
```

---

## Database Management

### Initialize Database

Tables are created automatically on first run, but you can explicitly initialize:

```bash
python db/init.py
```

This creates:
- All database tables
- Default users (admin@example.com, user@example.com, test@example.com)

### Seed F1 Data

Populate the database with F1 drivers, teams, and events:

```bash
# Seed current year
python scripts/seed_data.py

# Seed specific year
python scripts/seed_data.py 2024
```

> **Note:** Requires `SPORTSMONK_API_KEY` to be set for real data. Without it, uses placeholder data.

### Reset Database

Drop all tables and recreate:

```bash
python db/reset.py
```

> **Warning:** This deletes all data. Use with caution.

### Simulate Event Lifecycle

Test the full event flow (create markets, simulate trading, settle):

```bash
python scripts/simulate_event.py
```

---

## Common Development Tasks

### Run Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_pricing.py -v

# Run with coverage report
pytest --cov=. --cov-report=html
```

### Lint Code

```bash
# Frontend (ESLint)
cd frontend
npm run lint
```

### Build Frontend for Production

```bash
cd frontend
npm run build
# Output: frontend/dist/
```

### Database Migrations

If you modify models in `db/models.py`:

```bash
# Generate migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade
```

---

## IDE Configuration

### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance
- ESLint
- Tailwind CSS IntelliSense
- Prettier

Recommended settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "editor.formatOnSave": true,
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

### PyCharm

1. Set Python interpreter to `venv/bin/python`
2. Mark `frontend/node_modules` as excluded
3. Enable Flask support in project settings

---

## Troubleshooting

### "Module not found" errors

Make sure your virtual environment is activated:

```bash
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### Frontend can't connect to backend

1. Verify backend is running on port 5000
2. Check for CORS errors in browser console
3. Ensure `VITE_API_URL` is not set (defaults to `http://localhost:5000`)

### OTP not received

Without Mailgun configured, OTP codes are printed to the console. Check your terminal running the backend.

### Database locked (SQLite)

SQLite can have locking issues with concurrent access. In development:
1. Restart the Flask server
2. Delete `app.db` and re-initialize if corrupt

### Port already in use

```bash
# Find process using port 5000
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Kill the process or use a different port
FLASK_RUN_PORT=5001 python app.py
```

---

## Next Steps

- [Architecture Guide](ARCHITECTURE.md) - Understand the system design
- [Testing Guide](TESTING.md) - Learn how to write and run tests
- [API Reference](API_REFERENCE.md) - Explore the API endpoints
- [Contributing](../../CONTRIBUTING.md) - Contribute to the project
