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
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript

## Getting Started

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize the database (optional - will be created automatically on first run):**
   ```bash
   python init_db.py
   ```

### Running the Application

1. **Start the Flask backend server:**
   ```bash
   python app.py
   ```
   The backend will run on `http://localhost:5000`

2. **Serve the frontend (in a new terminal):**
   
   Since sessions use cookies, the frontend must be served over HTTP (not opened as a file). Use one of these options:
   
   **Option A: Python HTTP Server**
   ```bash
   python -m http.server 8000
   ```
   Then open `http://localhost:8000` in your browser.
   
   **Option B: Any other web server**
   - Serve the `index.html`, `app.js`, and `style.css` files from any web server
   - Make sure it's accessible via HTTP (e.g., `http://localhost:8000`)

3. **Access the application:**
   - Open your browser and navigate to `http://localhost:8000` (or whatever port you used)
   - The frontend will communicate with the backend at `http://localhost:5000`

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
