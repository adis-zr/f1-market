# Testing F1 API Integration

This guide explains how to test the F1 API integration using SportMonks F1 API.

## Prerequisites

1. **Set up SportMonks API key:**
   
   Create a `.env` file in the project root:
   ```
   SPORTSMONK_API_KEY=your_api_key_here
   ```
   
   The application automatically loads variables from `.env` using `python-dotenv`.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Flask server:**
   ```bash
   python app.py
   ```
   The server will run on `http://localhost:5000`

## Quick Test

Run the provided test script:

```bash
python test_f1_api.py
```

This script will:
1. Request an OTP for your email
2. Verify the OTP to log in
3. Test all F1 endpoints
4. Verify authentication is required

## Manual Testing

### Step 1: Authenticate

Request an OTP:
```bash
curl -X POST http://localhost:5000/request-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}' \
  -c cookies.txt
```

Verify OTP (check console or email for code):
```bash
curl -X POST http://localhost:5000/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com", "otp": "123456"}' \
  -c cookies.txt
```

### Step 2: Test F1 Endpoints

All F1 endpoints require authentication (you must be logged in).

#### Get Standings
```bash
# Current season (defaults to current year)
curl -X GET http://localhost:5000/api/f1/standings -b cookies.txt

# Specific season
curl -X GET "http://localhost:5000/api/f1/standings?season=2024" -b cookies.txt
```

#### Check Race Status
```bash
curl -X GET http://localhost:5000/api/f1/race-status -b cookies.txt
```

#### Get Telemetry (if race is ongoing)
```bash
curl -X GET http://localhost:5000/api/f1/telemetry -b cookies.txt

# Or with specific stage ID
curl -X GET "http://localhost:5000/api/f1/telemetry?race_id=12345" -b cookies.txt
```

## API Endpoints

### `/api/f1/standings` (GET)
Returns driver and constructor championship standings from SportMonks API.

**Query Parameters:**
- `season` (optional): Year (defaults to current year)

**Response:**
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

**Note:** 
- Standings come directly from SportMonks API (not calculated)
- `wins` field is `null` as SportMonks doesn't expose this in the standings endpoints
- Results are cached for 10 minutes

### `/api/f1/race-status` (GET)
Checks if a race (stage) is currently live.

**Response:**
```json
{
  "race_ongoing": false,
  "race_id": null
}
```

Or if race is ongoing:
```json
{
  "race_ongoing": true,
  "race_id": 12345
}
```

### `/api/f1/telemetry` (GET)
Returns live race data for an ongoing race. This is NOT full car telemetry - it's live results from SportMonks.

**Query Parameters:**
- `race_id` (optional): Specific stage ID
- `session_key` (optional): Alias for `race_id`

**Response (no race ongoing):**
```json
{
  "message": "No race is currently ongoing",
  "race_ongoing": false
}
```

**Response (race ongoing):**
```json
{
  "stage_id": 12345,
  "race_name": "Monaco Grand Prix",
  "track_id": 5,
  "season_id": 10,
  "time": {
    "status": "live",
    "starting_at": {...}
  },
  "results": [...],
  "timestamp": "2024-01-01T12:00:00"
}
```

## How It Works

### SportMonks F1 API Endpoints Used

The service uses these SportMonks F1 API endpoints:

1. **`/seasons`** - Get all F1 seasons, then finds season ID by matching year in `name` field
2. **`/drivers/season/{season_id}`** - Get driver standings for a season
   - Uses `include=driver` parameter to get driver details
3. **`/teams/season/{season_id}`** - Get constructor (team) standings for a season
4. **`/livescores/now`** - Check for currently live races and get live results
   - Returns stages with `time.status == "live"` or within 3-hour window of start time
   - Contains `results.data` array with current race positions

### Standings

- **Driver standings** come from `/drivers/season/{season_id}` endpoint
- **Constructor standings** come from `/teams/season/{season_id}` endpoint
- Both are **directly from the API** (not calculated)
- Season ID is resolved by matching year (e.g., "2024") to season `name` field
- Results are cached for 10 minutes

### Live Race Detection

- Uses `/livescores/now` endpoint
- Checks `time.status == "live"` in stage objects
- Fallback: checks if current time is within 3 hours of `time.starting_at.timestamp`
- Returns the first live stage found

### Telemetry

- **Not full car telemetry** - this is live race results from SportMonks
- Data comes from `/livescores/now` endpoint
- Returns stage information including:
  - Stage ID, name, track ID, season ID
  - Time information (status, starting_at)
  - Results array with current positions
- Only available when a race is actually live

## Caching

- Standings and season IDs are cached in memory for **10 minutes**
- Cache keys are prefixed with provider name: `sportmonks:{key}`
- Cache is automatically expired after TTL
- Repeated requests within 10 minutes return cached data

## Troubleshooting

### "Authentication required" (401)
- Make sure you've logged in first (verified OTP)
- Check that cookies are being sent with requests
- For cURL, use `-b cookies.txt` to send cookies

### "Failed to fetch standings from F1 API" (503)
- Check your internet connection
- Verify `SPORTSMONK_API_KEY` is set in `.env` file
- Check that your API key is valid and has F1 access
- Check server logs for detailed error messages
- The service needs to resolve season ID first - check if `/seasons` endpoint works

### "No race is currently ongoing" (404)
- This is normal when no race is live
- Telemetry is only available during active race sessions
- Check `/api/f1/race-status` first to see if a race is ongoing

### API Key Not Working
- Verify the key is in `.env` file in the project root
- Check server logs for "SportMonks API key not configured"
- Make sure the `.env` file is being loaded (check that other env vars work)

### Season Not Found
- The service matches season year (e.g., 2024) to season `name` field
- If season ID can't be resolved, standings will fail
- Check server logs for "Could not resolve SportMonks season ID for {year}"

## Configuration

You can configure the service via `.env` file:

```
SPORTSMONK_API_KEY=your_api_key_here
F1_SPORTSMONK_BASE_URL=https://f1.sportmonks.com/api/v1.0  # Optional, defaults to this
F1_CACHE_TTL_MINUTES=10  # Optional, defaults to 10
```

The application automatically loads variables from `.env` using `python-dotenv`.

## Response Field Details

### Driver Standings Fields
- `position`: Integer position in championship
- `driver_id`: SportMonks driver ID (string)
- `driver_name`: Full driver name (from included driver object)
- `points`: Float points total
- `wins`: Always `null` (not exposed by SportMonks in this endpoint)
- `constructor_id`: SportMonks team ID (string)

### Constructor Standings Fields
- `position`: Integer position in championship
- `constructor_id`: SportMonks team ID (string)
- `constructor_name`: Team name
- `points`: Float points total
- `wins`: Always `null` (not exposed by SportMonks in this endpoint)

### Telemetry Fields
- `stage_id`: SportMonks stage (race) ID
- `race_name`: Name of the race/stage
- `track_id`: SportMonks track ID
- `season_id`: SportMonks season ID
- `time`: Time information object with status and starting_at
- `results`: Array of current race results/positions
- `timestamp`: ISO timestamp when data was fetched

