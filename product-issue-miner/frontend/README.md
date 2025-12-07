# Product Issue Miner - Frontend

Next.js dashboard for the Product Issue Miner application.

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Backend API running (default: http://localhost:8000)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Configure the API URL in `.env` if needed:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

### Production Build

Build the application:

```bash
npm run build
```

Start the production server:

```bash
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Home page
│   │   └── globals.css   # Global styles
│   └── lib/              # Utilities
│       ├── api.ts        # API client
│       └── auth.tsx      # Authentication context
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

## Features

- TypeScript for type safety
- Tailwind CSS for styling
- React Query for data fetching
- Recharts for data visualization
- Simple password authentication
- Responsive dashboard design

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

## Authentication

The dashboard uses a simple password authentication system. The password is stored in localStorage and sent with each API request via the `X-Dashboard-Password` header.

## Deployment

The application is configured for Docker deployment with `output: 'standalone'` in next.config.js.
