# Fantasy Sports Stock Market Frontend

Modern React + TypeScript frontend for the fantasy sports stock market application.

## Tech Stack

- **Vite** - Build tool and dev server
- **React 19** - UI framework
- **TypeScript** - Type safety
- **React Router** - Client-side routing
- **TanStack Query (React Query)** - Data fetching and caching
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI component library
- **Recharts** - Charting library for price history

## Getting Started

### Install Dependencies

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will run on `http://localhost:5173` (or the next available port).

### Build

```bash
npm run build
```

### Environment Variables

Create a `.env` file in the frontend directory:

```
VITE_API_URL=http://localhost:5000
```

## Project Structure

```
src/
├── api/              # API client and endpoints
├── components/       # React components
│   ├── ui/          # shadcn/ui base components
│   ├── layout/      # Layout components
│   ├── market/      # Market-related components
│   ├── event/       # Event-related components
│   ├── portfolio/   # Portfolio components
│   └── wallet/      # Wallet components
├── hooks/           # React Query hooks
├── lib/             # Utilities and formatters
└── pages/           # Page components
```

## Features

- **Dashboard**: Overview of portfolio and featured markets
- **Markets**: Browse and filter markets by sport/status
- **Market Detail**: View market info, price history, and trade
- **Events**: Browse events and view results
- **Portfolio**: View all positions and P&L
- **Wallet**: View balance and transaction history

## API Integration

The frontend expects the backend to be running on `http://localhost:5000` (or the URL specified in `VITE_API_URL`).

All API requests use session-based authentication with cookies.
