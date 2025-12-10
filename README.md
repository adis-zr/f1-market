# F1 Market

A fantasy prediction market for Formula 1 racing. Trade virtual shares in drivers and constructors using simulated credits, with prices driven by an automated market maker (AMM) and payouts based on real-world race performance.

---

## Features

### Trading & Markets
- **AMM-Powered Pricing** — Buy and sell shares with instant execution using a bonding curve price model
- **Dynamic Pricing** — Prices automatically adjust based on supply and demand (more buyers = higher prices)
- **Per-Event Markets** — Each race weekend generates fresh markets for all drivers
- **Real-Time Price History** — Track price movements with historical charts

### Portfolio Management
- **Position Tracking** — View all your open positions across active markets
- **P&L Analytics** — Track realized and unrealized profit/loss for every position
- **Wallet & Ledger** — Full transaction history with deposits, withdrawals, and trade records

### Settlement & Payouts
- **Performance-Based Payouts** — Shares settle at prices calculated from actual race results
- **Configurable Scoring Rules** — Flexible formula system for computing settlement prices
- **Automatic Settlement** — Events settle automatically after races conclude

### Authentication
- **Passwordless Login** — Email-based OTP authentication via Mailgun
- **Session Management** — Secure server-side sessions with Flask

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS 4 |
| **Backend** | Flask, SQLAlchemy, Gunicorn |
| **Database** | SQLite (development), PostgreSQL (production) |
| **State Management** | TanStack Query (React Query) |
| **Email** | Mailgun API |
| **Deployment** | Render (web services + managed Postgres) |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- (Optional) Mailgun account for email OTP

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/f1-market.git
   cd f1-market
   ```

2. **Install Python dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Configure environment variables** (optional)
   
   Create a `.env` file in the project root:
   ```bash
   # Email Authentication (Mailgun)
   MAILGUN_API_KEY=your_mailgun_key
   MAILGUN_DOMAIN=mg.yourdomain.com
   
   # Restrict OTP to specific emails (comma-separated)
   OTP_ALLOWED_EMAILS=user@example.com,admin@example.com
   
   # F1 Data (SportMonks - optional)
   SPORTSMONK_API_KEY=your_api_key
   ```

### Running Locally

Start both servers in separate terminals:

```bash
# Terminal 1: Backend (runs on http://localhost:5000)
python app.py

# Terminal 2: Frontend (runs on http://localhost:5173)
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser.

> **Note:** Without Mailgun configured, OTP codes are logged to the console for local development.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Pages   │  │Components│  │  Hooks   │  │  TanStack Query  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/REST
┌─────────────────────────────▼───────────────────────────────────┐
│                        Backend (Flask)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     API Routes                            │   │
│  │  /auth/*  │  /api/markets/*  │  /api/events/*  │  ...    │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐   │
│  │  MarketService  │  │ SettlementSvc   │  │  WalletService │   │
│  └─────────────────┘  └─────────────────┘  └────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Bonding Curve Pricing                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ SQLAlchemy ORM
┌─────────────────────────────▼───────────────────────────────────┐
│                      Database (SQLite/Postgres)                  │
│  Users │ Markets │ Positions │ Trades │ Wallets │ Events │ ...  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Sport** | Top-level category (e.g., F1) |
| **League** | Competition within a sport (e.g., Formula 1 World Championship) |
| **Season** | A year's worth of events |
| **Event** | A single race weekend |
| **Participant** | A driver |
| **Team** | A constructor (e.g., Red Bull, Ferrari) |
| **Asset** | Tradeable entity linked to a participant or team |
| **Market** | Trading venue for an asset within an event |
| **Position** | User's holding in a specific market |

---

## Key Technical Details

### Bonding Curve Pricing

Markets use an AMM (Automated Market Maker) with a square-root bonding curve:

```
Price(supply) = a × √supply + b
```

- **`a`** — Slope parameter controlling price sensitivity
- **`b`** — Baseline price (price at zero supply)

**Buy Cost** (integral from current supply `s` to `s + Δs`):
```
cost = (2a/3) × [(s + Δs)^1.5 - s^1.5] + b × Δs
```

**Sell Payout** (integral from `s - Δs` to `s`):
```
payout = (2a/3) × [s^1.5 - (s - Δs)^1.5] + b × Δs
```

This ensures:
- Buying pushes prices up, selling pushes them down
- Large orders move prices more than small orders
- Always-available liquidity (no order book needed)

### Settlement & Scoring

When an event finishes, positions are settled using:

```
payout_per_share = α × (primary_score / max_score) + β
```

- `primary_score` — Points earned in the race
- `max_score` — Maximum possible points (e.g., 25 for a win)
- `α`, `β` — Configurable parameters per scoring rule

Formula types supported:
- `LINEAR_NORMALIZED` — Linear scaling (default)
- `SIGMOID` — S-curve for more dramatic winner/loser separation
- `PIECEWISE` — Custom breakpoints for arbitrary mappings

### Database Schema

Key models in `db/models.py`:

| Model | Purpose |
|-------|---------|
| `User` | Authentication & roles |
| `Wallet` | Balance tracking per user |
| `LedgerEntry` | Immutable transaction log |
| `Market` | Bonding curve parameters, status |
| `Position` | User shares + avg entry price |
| `Trade` | Individual buy/sell records |
| `EventResult` | Race finishing positions/scores |
| `ScoringRule` | Settlement formula config |

### API Structure

| Endpoint Group | Base Path | Purpose |
|----------------|-----------|---------|
| Auth | `/auth/*` | OTP request/verify, session |
| Browse | `/api/sports`, `/api/events`, etc. | Read-only data exploration |
| Markets | `/api/markets/<id>/*` | Trading operations |
| Settlement | `/api/settlement/*` | Admin settlement controls |

---

## Project Structure

```
f1-market/
├── app.py                 # Flask application entry point
├── config.py              # Environment configuration
├── requirements.txt       # Python dependencies
├── render.yaml            # Render deployment blueprint
│
├── api/                   # API route handlers
│   ├── routes.py          # Health check, index
│   ├── browse_routes.py   # Read-only browsing endpoints
│   ├── market_routes.py   # Buy/sell/position endpoints
│   ├── settlement_routes.py
│   └── f1_routes.py       # F1-specific data endpoints
│
├── auth/                  # Authentication module
│   └── routes.py          # OTP request, verify, logout
│
├── db/                    # Database layer
│   ├── models.py          # SQLAlchemy models
│   ├── init.py            # DB initialization
│   └── reset.py           # DB reset utilities
│
├── pricing/               # Market pricing logic
│   └── bonding_curve.py   # AMM price functions
│
├── services/              # Business logic
│   ├── market_service.py  # Buy/sell operations
│   ├── settlement_service.py
│   └── wallet_service.py  # Balance management
│
├── f1/                    # F1 data integration
│   ├── client.py          # External API client
│   ├── cache.py           # Response caching
│   └── ...
│
├── scripts/               # Utility scripts
│   ├── seed_data.py       # Populate test data
│   └── simulate_event.py  # Test event simulation
│
├── tests/                 # Test suite
│   ├── conftest.py        # Pytest fixtures
│   ├── test_pricing.py
│   ├── test_market_service.py
│   └── test_settlement.py
│
└── frontend/              # React application
    ├── src/
    │   ├── api/           # API client & types
    │   ├── components/    # UI components
    │   ├── hooks/         # Custom React hooks
    │   ├── pages/         # Route pages
    │   └── lib/           # Utilities
    ├── package.json
    ├── vite.config.ts
    └── tailwind.config.js
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_pricing.py -v
```

### Seeding Test Data

```bash
# Populate database with sample data
python scripts/seed_data.py

# Simulate an event lifecycle
python scripts/simulate_event.py
```

### Database Commands

```bash
# Initialize database (creates tables)
python db/init.py

# Reset database (drop and recreate)
python db/reset.py
```

### Building for Production

```bash
# Build frontend
cd frontend
npm run build

# Frontend assets output to frontend/dist/
```

---

## Deployment

This project includes a `render.yaml` blueprint for one-click deployment to [Render](https://render.com):

- **f1-market-api** — Python web service (Gunicorn)
- **f1-market** — Static site (React build)
- **f1-market-db** — Managed PostgreSQL

Required environment variables in production:
- `SECRET_KEY` — Flask session secret (auto-generated)
- `INTERNAL_PROD_DATABASE_URL` — Postgres connection (auto-linked)
- `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` — For email OTP
- `OTP_ALLOWED_EMAILS` — Restrict who can log in
- `CORS_ORIGINS` — Allowed frontend origins

---

## Disclaimer

This is a **fantasy game** using fictional credits. No real money, real trading, or gambling is involved. All market prices are simulated and have no monetary value. This project is intended for educational and personal use only.

Use of Formula 1 data must comply with the terms of service of data providers. This project is not affiliated with Formula 1, the FIA, or any official organization.

---

## License

MIT

