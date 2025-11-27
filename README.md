# F1 Stock Market
A Python-powered fantasy trading game where players buy and sell F1 drivers and constructors using simulated credits. Prices update based on real-world performance throughout the season. No real money involved.

## Features
- Dynamic stock prices for all drivers and constructors  
- Buy/sell trades using simulated credits  
- Portfolio tracking and trade history  
- League leaderboard based on portfolio value  
- Automatic price updates after qualifying and races  
- FastF1 integration for real F1 session data

## Tech Stack
- **Backend:** Flask, SQLAlchemy
- **Database:** SQLite (development), PostgreSQL (production)
- **Frontend:** React, TypeScript, Vite, Tailwind CSS

## Getting Started

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)
- Node.js 16+ and npm (for frontend)

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Set up environment variables (optional):**
   
   Create a `.env` file in the root directory for local development:
   ```bash
   # Optional: For F1 API access (SportMonks)
   SPORTSMONK_API_KEY=your_api_key_here
   
   # Optional: For email OTP (Mailgun)
   MAILGUN_API_KEY=your_mailgun_key
   MAILGUN_DOMAIN=your_mailgun_domain
   
   # Optional: Email allowlist for OTP (comma-separated)
   OTP_ALLOWED_EMAILS=your@email.com,another@email.com
   ```
   
   Note: The app will work without these, but some features (F1 data, email OTP) may be limited.

4. **Initialize the database (optional - will be created automatically on first run):**
   ```bash
   python db/init.py
   ```

### Running the Application

You need to run both the backend and frontend servers.

1. **Start the Flask backend server:**
   ```bash
   python app.py
   ```
   The backend will run on `http://localhost:5000`

2. **Start the frontend development server (in a new terminal):**
   ```bash
   cd frontend
   npm run dev
   ```
   The frontend will run on `http://localhost:5173` (or another port if 5173 is taken)

3. **Access the application:**
   - Open your browser and navigate to `http://localhost:5173`
   - The frontend will automatically communicate with the backend at `http://localhost:5000`

### Building for Production

To build the frontend for production:
```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/` and can be served by your web server.

### API Endpoints

- `POST /login` - Login with username and password
- `POST /register` - Register a new user
- `GET /me` - Get current logged-in user
- `POST /logout` - Logout current user
- `GET /health` - Health check endpoint

## Project Structure (Planned)

## Disclaimer
This project is a fantasy game that uses fictional credits. It does not involve real money, real trading, or gambling of any kind. All stock prices are simulated and have no monetary value. This project is intended for private, personal use only.

Any use of Formula 1 data must comply with the terms of service of the data providers (e.g., FastF1, OpenF1). This project is not affiliated with Formula 1, the FIA, or any official organization.
