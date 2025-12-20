# API Reference

Complete reference for all F1 Market API endpoints.

## Base URL

| Environment | URL |
|-------------|-----|
| Development | `http://localhost:5000` |
| Production | `https://your-api-domain.com` |

## Authentication

All authenticated endpoints require a valid session cookie. Obtain one by:
1. Request OTP with `/auth/request-otp`
2. Verify OTP with `/auth/verify-otp`

For CSRF protection, include the `X-CSRFToken` header with the token from `/auth/csrf-token`.

---

## Authentication Endpoints

### Request OTP

Request a one-time password to be sent to an email address.

```
POST /auth/request-otp
```

**Rate Limit:** 5 per hour

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Success Response (200):**
```json
{
  "message": "OTP sent to your email",
  "email": "user@example.com"
}
```

**Error Responses:**

| Status | Message | Description |
|--------|---------|-------------|
| 400 | Email is required | Missing email field |
| 400 | Invalid email format | Email validation failed |
| 403 | Email not authorized | Email not in allowlist |
| 429 | Rate limit exceeded | Too many requests |
| 500 | Server error occurred | Internal error |

---

### Verify OTP

Verify the OTP and create a session.

```
POST /auth/verify-otp
```

**Rate Limit:** 10 per hour

**Request Body:**
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Success Response (200):**
```json
{
  "message": "Login successful!",
  "email": "user@example.com",
  "username": "user",
  "role": "player"
}
```

**Error Responses:**

| Status | Message | Description |
|--------|---------|-------------|
| 400 | Email and OTP are required | Missing fields |
| 401 | Invalid or expired OTP | Wrong or expired code |
| 429 | Rate limit exceeded | Too many attempts |

---

### Get Current User

Get the currently logged-in user.

```
GET /auth/me
```

**Success Response (200) - Logged In:**
```json
{
  "email": "user@example.com",
  "username": "user",
  "role": "player",
  "logged_in": true
}
```

**Success Response (200) - Not Logged In:**
```json
{
  "logged_in": false
}
```

---

### Logout

Clear the current session.

```
POST /auth/logout
```

**Success Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

---

### Get CSRF Token

Get a CSRF token for protected requests.

```
GET /auth/csrf-token
```

**Success Response (200):**
```json
{
  "csrf_token": "IjQ5ZGM..."
}
```

---

## Browse Endpoints

Read-only endpoints for exploring data. No authentication required.

### Get Sports

List all sports.

```
GET /api/sports
```

**Response (200):**
```json
[
  {
    "id": 1,
    "code": "F1",
    "name": "Formula 1"
  }
]
```

---

### Get Leagues

List leagues, optionally filtered by sport.

```
GET /api/leagues
GET /api/leagues?sport_id=1
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sport_id` | int | No | Filter by sport ID |

**Response (200):**
```json
[
  {
    "id": 1,
    "sport_id": 1,
    "name": "Formula 1 World Championship"
  }
]
```

---

### Get Seasons

List seasons, optionally filtered by league.

```
GET /api/seasons
GET /api/seasons?league_id=1
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `league_id` | int | No | Filter by league ID |

**Response (200):**
```json
[
  {
    "id": 1,
    "league_id": 1,
    "year": 2024,
    "status": "active"
  }
]
```

---

### Get Events

List events with optional filters.

```
GET /api/events
GET /api/events?season_id=1&status=upcoming&limit=50
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sport_id` | int | No | Filter by sport |
| `season_id` | int | No | Filter by season |
| `status` | string | No | Filter by status: `upcoming`, `live`, `finished` |
| `limit` | int | No | Max results (default: 100, max: 1000) |

**Response (200):**
```json
[
  {
    "id": 1,
    "season_id": 1,
    "name": "Monaco Grand Prix",
    "venue": "Circuit de Monaco",
    "start_at": "2024-05-26T14:00:00+00:00",
    "end_at": "2024-05-26T16:00:00+00:00",
    "status": "upcoming",
    "metadata": {}
  }
]
```

---

### Get Event Markets

Get all markets for a specific event.

```
GET /api/events/:event_id/markets
```

**Response (200):**
```json
[
  {
    "market_id": 1,
    "event_id": 1,
    "asset_id": 1,
    "status": "open",
    "current_price": 1.5,
    "current_supply": 100.0,
    "market_type": "outright",
    "asset": {
      "id": 1,
      "type": "participant",
      "symbol": "VER",
      "display_name": "Max Verstappen",
      "participant": {
        "id": 1,
        "name": "Max Verstappen",
        "short_code": "VER"
      }
    },
    "event": {
      "id": 1,
      "name": "Monaco Grand Prix",
      "venue": "Circuit de Monaco",
      "start_at": "2024-05-26T14:00:00+00:00",
      "end_at": "2024-05-26T16:00:00+00:00",
      "status": "upcoming"
    }
  }
]
```

---

### Get Event Results

Get race results for an event.

```
GET /api/events/:event_id/results
```

**Response (200):**
```json
[
  {
    "id": 1,
    "event_id": 1,
    "participant_id": 1,
    "primary_score": 25.0,
    "rank": 1,
    "status": "finished",
    "participant": {
      "id": 1,
      "name": "Max Verstappen",
      "short_code": "VER"
    }
  }
]
```

---

### Get Markets

List markets with optional filters.

```
GET /api/markets
GET /api/markets?event_id=1&status=open&limit=50
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_id` | int | No | Filter by event |
| `sport_id` | int | No | Filter by sport |
| `status` | string | No | Filter by status: `open`, `closed`, `settled` |
| `limit` | int | No | Max results (default: 100, max: 1000) |

**Response (200):**
```json
[
  {
    "market_id": 1,
    "event_id": 1,
    "asset_id": 1,
    "status": "open",
    "current_price": 1.5,
    "current_supply": 100.0,
    "market_type": "outright",
    "bonding_curve_a": 1.0,
    "bonding_curve_b": 0.5,
    "asset": { ... },
    "event": { ... },
    "created_at": "2024-01-01T00:00:00+00:00",
    "updated_at": "2024-01-01T12:00:00+00:00"
  }
]
```

---

### Get Portfolio

Get all positions for the authenticated user.

```
GET /api/portfolio
```

**Authentication:** Required

**Response (200):**
```json
[
  {
    "position_id": 1,
    "market_id": 1,
    "shares": 10.0,
    "avg_entry_price": 1.5,
    "realized_pnl": 0.0,
    "current_price": 1.8,
    "unrealized_pnl": 3.0,
    "total_pnl": 3.0,
    "last_marked_at": null
  }
]
```

**Error Response (401):**
```json
{
  "error": "Authentication required"
}
```

---

### Get Wallet

Get wallet balance for the authenticated user.

```
GET /api/wallet
```

**Authentication:** Required

**Response (200):**
```json
{
  "user_id": 1,
  "available_balance": 850.0,
  "total_balance": 1000.0,
  "locked_balance": 150.0
}
```

---

### Get Ledger

Get transaction history for the authenticated user.

```
GET /api/wallet/ledger
GET /api/wallet/ledger?limit=50&type=buy
```

**Authentication:** Required

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | No | Max results (default: 100, max: 1000) |
| `type` | string | No | Filter by type: `deposit`, `withdrawal`, `buy`, `sell`, `settlement`, `fee` |

**Response (200):**
```json
[
  {
    "id": 1,
    "amount": -15.0,
    "transaction_type": "buy",
    "reference_type": "market",
    "reference_id": 1,
    "description": "Bought 10 shares of VER at 1.5",
    "created_at": "2024-01-01T12:00:00+00:00"
  }
]
```

---

## Market Trading Endpoints

### Get Market

Get detailed market information.

```
GET /api/markets/:market_id
```

**Response (200):**
```json
{
  "id": 1,
  "event_id": 1,
  "asset_id": 1,
  "status": "open",
  "current_price": 1.5,
  "current_supply": 100.0,
  "bonding_curve_a": 1.0,
  "bonding_curve_b": 0.5,
  "asset": { ... },
  "event": { ... }
}
```

**Error Response (404):**
```json
{
  "error": "Market not found"
}
```

---

### Buy Shares

Buy shares in a market.

```
POST /api/markets/:market_id/buy
```

**Authentication:** Required

**Request Body:**
```json
{
  "quantity": 10.0
}
```

**Validation:**
- Quantity must be positive
- Min: 0.01, Max: 1,000,000
- Max 8 decimal places

**Success Response (200):**
```json
{
  "shares": 10.0,
  "cost": 15.5,
  "price_per_share": 1.55,
  "new_price": 1.6,
  "new_supply": 110.0,
  "position": {
    "shares": 10.0,
    "avg_entry_price": 1.55
  }
}
```

**Error Responses:**

| Status | Message | Description |
|--------|---------|-------------|
| 400 | quantity is required | Missing field |
| 400 | Quantity must be positive | Invalid quantity |
| 400 | Insufficient balance | Not enough funds |
| 400 | Market is not open | Market closed/settled |
| 401 | Authentication required | Not logged in |
| 404 | Market not found | Invalid market ID |

---

### Sell Shares

Sell shares from a position.

```
POST /api/markets/:market_id/sell
```

**Authentication:** Required

**Request Body:**
```json
{
  "quantity": 5.0
}
```

**Success Response (200):**
```json
{
  "shares_sold": 5.0,
  "payout": 7.8,
  "price_per_share": 1.56,
  "new_price": 1.5,
  "new_supply": 95.0,
  "realized_pnl": 0.3,
  "position": {
    "shares": 5.0,
    "avg_entry_price": 1.55
  }
}
```

**Error Responses:**

| Status | Message | Description |
|--------|---------|-------------|
| 400 | Insufficient shares | Not enough shares to sell |
| 400 | Market is not open | Market closed/settled |
| 401 | Authentication required | Not logged in |

---

### Get Position

Get user's position in a market.

```
GET /api/markets/:market_id/positions
```

**Authentication:** Required

**Response (200) - Has Position:**
```json
{
  "shares": 10.0,
  "avg_entry_price": 1.55,
  "realized_pnl": 0.0,
  "unrealized_pnl": 0.5,
  "current_price": 1.6
}
```

**Response (200) - No Position:**
```json
{
  "shares": 0,
  "avg_entry_price": 0,
  "realized_pnl": 0
}
```

---

### Estimate Order

Preview cost/payout before executing a trade.

```
POST /api/markets/:market_id/estimate
```

**Request Body:**
```json
{
  "quantity": 10.0,
  "side": "buy"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `quantity` | number | Yes | Number of shares |
| `side` | string | No | `buy` (default) or `sell` |

**Response (200) - Buy:**
```json
{
  "side": "buy",
  "quantity": 10.0,
  "estimated_cost": 15.5,
  "price_per_share": 1.55,
  "current_supply": 100.0
}
```

**Response (200) - Sell:**
```json
{
  "side": "sell",
  "quantity": 5.0,
  "estimated_payout": 7.5,
  "price_per_share": 1.5,
  "current_supply": 100.0
}
```

---

### Get Price History

Get historical price data for a market.

```
GET /api/markets/:market_id/price-history
GET /api/markets/:market_id/price-history?limit=50
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | No | Max results (default: 100, max: 1000) |

**Response (200):**
```json
{
  "market_id": 1,
  "history": [
    {
      "timestamp": "2024-01-01T12:00:00+00:00",
      "price": 1.6,
      "reason": "buy"
    },
    {
      "timestamp": "2024-01-01T11:30:00+00:00",
      "price": 1.55,
      "reason": "buy"
    }
  ]
}
```

---

### Get Wallet (Market Context)

Get wallet info for trading context.

```
GET /api/markets/:market_id/wallet
```

**Authentication:** Required

**Response (200):**
```json
{
  "user_id": 1,
  "available_balance": 850.0,
  "total_balance": 1000.0,
  "locked_balance": 150.0
}
```

---

## F1 Data Endpoints

Real-time F1 data from SportMonks API. All endpoints require authentication.

### Get Standings

Get driver and constructor championship standings.

```
GET /api/f1/standings
GET /api/f1/standings?season=2024
```

**Authentication:** Required

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `season` | int | No | Year (defaults to current) |

**Response (200):**
```json
{
  "driver_standings": [
    {
      "position": 1,
      "driver_id": "12345",
      "driver_name": "Max Verstappen",
      "points": 575.0,
      "wins": null,
      "constructor_id": "67890"
    }
  ],
  "constructor_standings": [
    {
      "position": 1,
      "constructor_id": "67890",
      "constructor_name": "Red Bull Racing",
      "points": 860.0,
      "wins": null
    }
  ],
  "season": 2024
}
```

**Error Response (503):**
```json
{
  "message": "Failed to fetch standings from F1 API"
}
```

---

### Get Race Status

Check if a race is currently live.

```
GET /api/f1/race-status
```

**Authentication:** Required

**Response (200) - No Race:**
```json
{
  "race_ongoing": false
}
```

**Response (200) - Race Ongoing:**
```json
{
  "race_ongoing": true,
  "race_id": 12345
}
```

---

### Get Telemetry

Get live race data (only available during active race).

```
GET /api/f1/telemetry
GET /api/f1/telemetry?race_id=12345
```

**Authentication:** Required

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `race_id` | int | No | Stage/race ID |
| `session_key` | int | No | Alias for race_id |

**Response (200):**
```json
{
  "stage_id": 12345,
  "race_name": "Monaco Grand Prix",
  "track_id": 5,
  "season_id": 10,
  "time": {
    "status": "live",
    "starting_at": { ... }
  },
  "results": [ ... ],
  "timestamp": "2024-05-26T14:30:00+00:00"
}
```

**Error Response (404) - No Race:**
```json
{
  "message": "No race is currently ongoing",
  "race_ongoing": false
}
```

---

### Get Last Race

Get results from the most recent finished race.

```
GET /api/f1/last-race
GET /api/f1/last-race?season=2024
```

**Authentication:** Required

**Response (200):**
```json
{
  "race_found": true,
  "stage_id": 12340,
  "race_name": "Spain Grand Prix",
  "results": [ ... ]
}
```

**Error Response (404):**
```json
{
  "message": "No finished race found",
  "race_found": false
}
```

---

## Settlement Endpoints (Admin Only)

These endpoints require admin role.

### Settle Event

Settle an event and pay out all positions.

```
POST /api/events/:event_id/settle
```

**Authentication:** Required (Admin)

**Request Body (optional):**
```json
{
  "source": "event_result"
}
```

**Response (200):**
```json
{
  "event_id": 1,
  "markets_settled": 20,
  "total_positions": 150,
  "total_payout": 5000.0
}
```

**Error Responses:**

| Status | Message | Description |
|--------|---------|-------------|
| 400 | Event has no results | Missing EventResult records |
| 400 | Event already settled | Already processed |
| 403 | Admin access required | Not an admin |

---

### Preview Settlement

Preview what settlement would look like without executing.

```
GET /api/events/:event_id/settlement-preview
```

**Authentication:** Required (Admin)

**Response (200):**
```json
{
  "event_id": 1,
  "markets": [
    {
      "market_id": 1,
      "asset_symbol": "VER",
      "payout_per_share": 1.0,
      "positions_count": 15,
      "total_shares": 150.0,
      "total_payout": 150.0
    }
  ],
  "total_payout": 5000.0
}
```

---

### Get Event

Get event details.

```
GET /api/events/:event_id
```

**Response (200):**
```json
{
  "event_id": 1,
  "name": "Monaco Grand Prix",
  "venue": "Circuit de Monaco",
  "status": "upcoming",
  "start_at": "2024-05-26T14:00:00+00:00",
  "end_at": "2024-05-26T16:00:00+00:00",
  "season_id": 1,
  "metadata": {}
}
```

---

## Health Check

### Health

Check if the API is running.

```
GET /health
```

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00+00:00"
}
```

---

## Common Error Responses

All endpoints may return these error responses:

| Status | Description |
|--------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

**Error Response Format:**
```json
{
  "error": "Description of what went wrong"
}
```

Or for some endpoints:
```json
{
  "message": "Description of what went wrong"
}
```

---

## Status Enums

### Event Status
- `upcoming` - Event hasn't started
- `live` - Event is in progress
- `finished` - Event has completed

### Market Status
- `open` - Trading allowed
- `closed` - Trading paused
- `settled` - Payouts completed

### Season Status
- `upcoming` - Season hasn't started
- `active` - Season in progress
- `finished` - Season completed

### Transaction Types
- `deposit` - Credit added
- `withdrawal` - Credit removed
- `buy` - Shares purchased
- `sell` - Shares sold
- `settlement` - Settlement payout
- `fee` - Fee charged

### Result Status
- `finished` - Completed normally
- `dnf` - Did not finish
- `disqualified` - Disqualified
