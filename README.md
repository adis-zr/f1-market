# F1 Market

A fantasy prediction market for Formula 1 racing. Trade virtual shares in drivers and constructors using simulated credits, with prices driven by an automated market maker (AMM) and payouts based on real-world race performance.

**This is a fantasy game using fictional credits. No real money is involved.**

---

## Features

- **AMM-Powered Pricing** - Buy and sell shares with instant execution using a bonding curve
- **Dynamic Pricing** - Prices adjust based on supply and demand
- **Per-Event Markets** - Fresh markets for each race weekend
- **Performance-Based Payouts** - Positions settle based on actual race results
- **Passwordless Login** - Email-based OTP authentication
- **Real-Time F1 Data** - Live standings and race information

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/f1-market.git
cd f1-market

# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### Run

```bash
# Terminal 1: Backend (http://localhost:5000)
python app.py

# Terminal 2: Frontend (http://localhost:5173)
cd frontend && npm run dev
```

Open http://localhost:5173

---

## Documentation

### For Developers

| Document | Description |
|----------|-------------|
| [Setup Guide](docs/dev/SETUP.md) | Local development setup |
| [Architecture](docs/dev/ARCHITECTURE.md) | System design, bonding curves, scoring |
| [Testing](docs/dev/TESTING.md) | Running and writing tests |
| [Deployment](docs/dev/DEPLOYMENT.md) | Production deployment (Render, etc.) |
| [API Reference](docs/dev/API_REFERENCE.md) | Complete API documentation |

### For Users

| Document | Description |
|----------|-------------|
| [User Guide](docs/user/USER_GUIDE.md) | How to trade, manage portfolio, understand payouts |

### For Contributors

| Document | Description |
|----------|-------------|
| [Contributing](CONTRIBUTING.md) | How to contribute to the project |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Backend | Flask, SQLAlchemy, Gunicorn |
| Database | SQLite (dev), PostgreSQL (prod) |
| State | TanStack Query (React Query) |
| Deployment | Render |

---

## Project Structure

```
f1-market/
├── api/                # API routes
├── auth/               # Authentication (OTP)
├── db/                 # Database models
├── pricing/            # Bonding curve pricing
├── services/           # Business logic
├── tests/              # Test suite
├── frontend/           # React application
└── docs/               # Documentation
    ├── dev/            # Developer docs
    └── user/           # User docs
```

---

## License

MIT

---

## Disclaimer

This is a **fantasy game** using fictional credits. No real money, trading, or gambling is involved. All market prices are simulated and have no monetary value. This project is for educational and personal use only.

Use of Formula 1 data must comply with the terms of service of data providers. This project is not affiliated with Formula 1, the FIA, or any official organization.
