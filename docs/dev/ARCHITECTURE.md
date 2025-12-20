# Architecture Guide

This document provides a deep technical dive into F1 Market's architecture, including the bonding curve pricing model, settlement scoring, and database design.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React)                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │   Pages    │  │ Components │  │   Hooks    │  │  TanStack Query  │   │
│  │            │  │            │  │            │  │  (React Query)   │   │
│  └────────────┘  └────────────┘  └────────────┘  └──────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ HTTP/REST + Session Cookies
┌─────────────────────────────────▼───────────────────────────────────────┐
│                            Backend (Flask)                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                          API Routes                               │   │
│  │  /auth/*  │  /api/markets/*  │  /api/events/*  │  /api/f1/*      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐    │
│  │   MarketService   │  │ SettlementService │  │   WalletService   │    │
│  │   (buy/sell)      │  │   (payouts)       │  │   (balance)       │    │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Bonding Curve Pricing                         │   │
│  │                 pricing/bonding_curve.py                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      Scoring Strategies                           │   │
│  │                    services/scoring.py                            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ SQLAlchemy ORM
┌─────────────────────────────────▼───────────────────────────────────────┐
│                        Database (SQLite/PostgreSQL)                      │
│  Users │ Markets │ Positions │ Trades │ Wallets │ Events │ Results      │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                       External APIs (Optional)                           │
│  ┌───────────────────┐  ┌───────────────────┐                           │
│  │  SportMonks F1    │  │      Mailgun      │                           │
│  │  (standings, etc) │  │   (OTP emails)    │                           │
│  └───────────────────┘  └───────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Frontend** | React 19 + TypeScript | Modern React with strong typing |
| **Build Tool** | Vite | Fast HMR, optimized builds |
| **Styling** | Tailwind CSS 4 | Utility-first, rapid UI development |
| **State** | TanStack Query v5 | Server state caching, auto-refetching |
| **Routing** | React Router v7 | Declarative routing |
| **Backend** | Flask 3.0 | Lightweight, flexible Python framework |
| **ORM** | SQLAlchemy | Powerful Python ORM with migrations |
| **Database** | SQLite (dev) / PostgreSQL (prod) | SQLite for simplicity, Postgres for scale |
| **Auth** | OTP via Mailgun | Passwordless, secure |
| **Production Server** | Gunicorn | Production-grade WSGI server |

---

## Core Concepts

The system is built around a sports ontology hierarchy:

```
Sport (e.g., F1)
└── League (e.g., Formula 1 World Championship)
    └── Season (e.g., 2024)
        └── Event (e.g., Monaco Grand Prix)
            └── Market (e.g., VER - Max Verstappen)
                ├── Positions (user holdings)
                ├── Trades (execution history)
                └── PriceHistory (price movements)
```

| Concept | Description |
|---------|-------------|
| **Sport** | Top-level category (e.g., F1, NBA) |
| **League** | Competition within a sport |
| **Season** | A year's worth of events |
| **Event** | A single race weekend or game |
| **Participant** | An individual (e.g., driver) |
| **Team** | A constructor or team |
| **Asset** | Tradeable entity linked to a participant or team |
| **Market** | Trading venue for an asset within an event |
| **Position** | User's holding in a specific market |

---

## Bonding Curve Pricing

Markets use an Automated Market Maker (AMM) with a **square-root bonding curve**. This ensures:
- Always-available liquidity (no order book needed)
- Dynamic price discovery based on supply/demand
- Large orders move prices more than small orders

### Price Formula

The price at any given supply `s` is:

```
P(s) = a × √s + b
```

Where:
- `s` = current supply (total shares outstanding)
- `a` = slope parameter (price sensitivity)
- `b` = baseline price (price at zero supply)

**Example:** With `a = 0.1` and `b = 1.0`:
- At supply 0: Price = 1.0
- At supply 100: Price = 0.1 × √100 + 1.0 = 2.0
- At supply 400: Price = 0.1 × √400 + 1.0 = 3.0

### Buy Cost (Integral)

To buy `Δs` shares starting from supply `s`, the total cost is the integral of the price function:

```
Cost = ∫[s to s+Δs] P(x) dx

Cost = (2a/3) × [(s + Δs)^(3/2) - s^(3/2)] + b × Δs
```

This is the **area under the price curve** from `s` to `s + Δs`.

### Sell Payout (Integral)

To sell `Δs` shares from supply `s`, the payout is:

```
Payout = ∫[s-Δs to s] P(x) dx

Payout = (2a/3) × [s^(3/2) - (s - Δs)^(3/2)] + b × Δs
```

### Why Square Root?

The square-root curve has desirable properties:
1. **Price increases with demand** - More buyers = higher price
2. **Diminishing marginal impact** - Each additional share has less price impact
3. **No arbitrage** - Buy cost ≥ sell payout for same quantity
4. **Continuous liquidity** - Always a price, always tradeable

### Implementation

See [pricing/bonding_curve.py](../../pricing/bonding_curve.py):

```python
def price(s: Decimal, a: Decimal, b: Decimal) -> Decimal:
    """Current price given supply s."""
    return a * decimal_sqrt(s) + b

def buy_cost(s: Decimal, delta_s: Decimal, a: Decimal, b: Decimal) -> Decimal:
    """Cost to buy delta_s shares from current supply s."""
    two_thirds = Decimal('2') / Decimal('3')
    integral_part = two_thirds * a * (decimal_pow_3_2(s + delta_s) - decimal_pow_3_2(s))
    baseline_part = b * delta_s
    return integral_part + baseline_part
```

All calculations use Python's `Decimal` with 50-digit precision to avoid floating-point errors.

---

## Settlement & Scoring

When an event finishes, positions are settled based on actual race results.

### Settlement Flow

```
1. Event finishes (race ends)
2. EventResult records are created for each participant
   - primary_score (e.g., F1 points: 25 for 1st, 18 for 2nd, etc.)
   - rank (finishing position)
   - status (finished, DNF, disqualified)
3. For each market in the event:
   a. Get the EventResult for the market's asset (participant)
   b. Compute payout_per_share using the ScoringRule
   c. For each Position in the market:
      - Credit user wallet: shares × payout_per_share
      - Record settlement in ledger
4. Mark market as SETTLED
5. Mark event as FINISHED
```

### Scoring Formulas

The system supports multiple scoring strategies, configured per ScoringRule.

#### 1. LINEAR_NORMALIZED (Default)

```
payout = α × (primary_score / max_score) + β
```

Where:
- `primary_score` = Points earned (e.g., 25 for race win)
- `max_score` = Maximum possible (e.g., 25)
- `α` (alpha) = Scaling factor
- `β` (beta) = Base payout

**Example:** For a race winner with `max_score=25`, `α=1.0`, `β=0.1`:
```
payout = 1.0 × (25/25) + 0.1 = 1.1 per share
```

#### 2. SIGMOID

```
payout = α × sigmoid(k × normalized) + β
sigmoid(x) = 1 / (1 + e^(-x))
```

The sigmoid creates an S-curve, rewarding excellence more than mediocrity. The `k` parameter controls steepness (default: 10).

#### 3. PIECEWISE

Defines different linear formulas for different performance ranges:

```json
{
  "breakpoints": [
    {"threshold": 0.0, "alpha": 0.5, "beta": 0.0},
    {"threshold": 0.5, "alpha": 1.0, "beta": 0.1},
    {"threshold": 0.8, "alpha": 1.5, "beta": 0.2}
  ]
}
```

Useful for tiered rewards (e.g., podium bonuses).

### Implementation

See [services/scoring.py](../../services/scoring.py) for the strategy pattern implementation:

```python
class LinearNormalizedStrategy(ScoringStrategy):
    def compute_payout(self, event_result, scoring_rule) -> Decimal:
        normalized = primary_score / max_score
        return alpha * normalized + beta
```

---

## Database Schema

### Entity Relationship Overview

```
User ─────────┬────────── Wallet ──────── LedgerEntry
              │
              ├────────── Position ───────┐
              │                           │
              └────────── Trade ──────────┤
                                          │
Sport ── League ── Season ── Event ───── Market ──────────────┘
                      │         │           │
                      │         │           └── PriceHistory
                      │         │           └── MarketSettlement
                      │         │
                      │         └── EventResult ── Participant
                      │
                      └── ParticipantTeamMembership
                                    │
Team ───────────────────────────────┘
```

### Key Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `User` | Authentication | email, role (PLAYER/ADMIN) |
| `Wallet` | Balance tracking | balance, locked_balance |
| `LedgerEntry` | Transaction log | amount, transaction_type |
| `Market` | Trading venue | a, b (bonding curve), status |
| `Position` | User holdings | shares, avg_entry_price, realized_pnl |
| `Trade` | Execution record | price, quantity, executed_at |
| `EventResult` | Race results | primary_score, rank, status |
| `ScoringRule` | Settlement config | max_score, alpha, beta, formula_type |

### Precision

All financial values use `Numeric(precision=18, scale=8)` for:
- 18 total digits
- 8 decimal places
- No floating-point rounding errors

---

## Authentication Flow

F1 Market uses passwordless OTP authentication:

```
1. User enters email
2. POST /auth/request-otp {email}
3. Server generates 6-digit OTP, hashes with Argon2
4. OTP sent via Mailgun (or logged in dev)
5. User enters OTP
6. POST /auth/verify-otp {email, otp}
7. Server verifies hash, creates/loads User
8. Session established (secure cookie)
9. CSRF token returned for subsequent requests
```

### Session Security

| Setting | Development | Production |
|---------|-------------|------------|
| HttpOnly | Yes | Yes |
| SameSite | Lax | None (cross-origin) |
| Secure | No | Yes (HTTPS only) |
| CSRF | Enabled | Enabled |

---

## Concurrency & Locking

The system uses database locks to prevent race conditions:

### Row-Level Locks

```python
# Lock market row during trade
market = Market.query.filter_by(id=market_id).with_for_update().first()

# Lock position row during update
position = Position.query.filter_by(
    user_id=user_id, market_id=market_id
).with_for_update().first()

# Lock wallet during balance updates
wallet = Wallet.query.filter_by(user_id=user_id).with_for_update().first()
```

### Nested Transactions

Wallet creation uses savepoints to handle the "get or create" pattern:

```python
try:
    wallet = create_wallet()
except IntegrityError:
    session.rollback()
    wallet = get_existing_wallet()
```

---

## API Structure

| Endpoint Group | Base Path | Purpose |
|----------------|-----------|---------|
| Auth | `/auth/*` | OTP login/logout |
| Browse | `/api/sports`, `/api/events`, etc. | Read-only data |
| Markets | `/api/markets/<id>/*` | Trading operations |
| F1 | `/api/f1/*` | Live F1 data from SportMonks |
| Settlement | `/api/events/<id>/settle` | Admin settlement |

See [API Reference](API_REFERENCE.md) for complete endpoint documentation.

---

## External Integrations

### SportMonks F1 API

Used for live F1 data:
- Driver standings
- Constructor standings
- Live race detection
- Race telemetry

Data is cached for 10 minutes (configurable).

### Mailgun

Used for OTP email delivery. Falls back to console logging in development.

---

## Project Structure

```
f1-market/
├── app.py                 # Flask entry point
├── config.py              # Environment configuration
├── requirements.txt       # Python dependencies
│
├── api/                   # API route handlers
│   ├── routes.py          # Health check
│   ├── browse_routes.py   # Read-only endpoints
│   ├── market_routes.py   # Trading endpoints
│   ├── settlement_routes.py
│   └── f1_routes.py       # F1 data endpoints
│
├── auth/                  # Authentication
│   └── routes.py          # OTP request/verify
│
├── db/                    # Database
│   ├── models.py          # SQLAlchemy models (18 total)
│   ├── init.py            # Initialization
│   └── reset.py           # Reset utilities
│
├── pricing/               # Pricing engine
│   └── bonding_curve.py   # AMM functions
│
├── services/              # Business logic
│   ├── market_service.py  # Buy/sell operations
│   ├── settlement_service.py
│   ├── wallet_service.py
│   └── scoring.py         # Settlement strategies
│
├── f1/                    # F1 integration
│   ├── client.py          # SportMonks client
│   └── cache.py           # Response caching
│
├── tests/                 # Test suite
│   ├── conftest.py        # Fixtures
│   └── test_*.py          # Test modules
│
└── frontend/              # React application
    ├── src/
    │   ├── api/           # API client
    │   ├── components/    # UI components
    │   ├── hooks/         # Custom hooks
    │   ├── pages/         # Route pages
    │   └── lib/           # Utilities
    └── package.json
```

---

## Next Steps

- [Setup Guide](SETUP.md) - Get started with development
- [Testing Guide](TESTING.md) - Run and write tests
- [API Reference](API_REFERENCE.md) - Endpoint documentation
- [Deployment Guide](DEPLOYMENT.md) - Deploy to production
