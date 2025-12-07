# Product Issue Miner

Internal tool to extract product issues from Zendesk tickets using Claude AI.

## Overview

Product Issue Miner is an automated system that analyzes customer support tickets from Zendesk and intelligently extracts product issues using Claude AI. It categorizes, prioritizes, and tracks issues to help product teams identify patterns and prioritize improvements.

## Tech Stack

- **Backend**: Python 3.11+ with FastAPI
- **Frontend**: Next.js with TypeScript
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **AI**: Anthropic Claude API
- **Hosting**: Railway

## Local Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- Git

### Getting Started

1. Clone the repository:
```bash
git clone <repository-url>
cd product-issue-miner
```

2. Start services with Docker Compose:
```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)

3. Install backend dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. Install frontend dependencies:
```bash
cd frontend
npm install
```

5. Set up environment variables:
```bash
# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env.local
```

### Running the Application

**Backend (FastAPI)**:
```bash
cd backend
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`

**Frontend (Next.js)**:
```bash
cd frontend
npm run dev
```

Frontend runs on `http://localhost:3000`

## Project Structure

```
product-issue-miner/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── api/            # API routes
│   │   └── tasks/          # Background tasks
│   ├── tests/              # Test suite
│   ├── alembic/            # Database migrations
│   └── requirements.txt
├── frontend/               # Next.js application
│   ├── src/
│   │   ├── app/           # Next.js app directory
│   │   ├── components/    # React components
│   │   └── lib/           # Utility functions
│   └── package.json
├── docker-compose.yml     # Local development services
└── README.md
```

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://miner:localdev@localhost:5432/issue_miner
REDIS_URL=redis://localhost:6379
CLAUDE_API_KEY=your-api-key-here
ZENDESK_API_KEY=your-zendesk-key-here
ZENDESK_SUBDOMAIN=your-subdomain
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Product Issue Miner
```

## Features

- Extract issues from Zendesk tickets
- AI-powered issue categorization and analysis
- Issue tracking and prioritization
- Dashboard with analytics and insights
- RESTful API for integration

## Development

### Running Tests

**Backend**:
```bash
cd backend
pytest
```

**Frontend**:
```bash
cd frontend
npm test
```

### Code Quality

```bash
# Backend linting
cd backend
black . && flake8 . && mypy app/

# Frontend linting
cd frontend
npm run lint
```

## Deployment

The application is configured for deployment on Railway. See deployment documentation for setup instructions.

## Contributing

1. Create a feature branch
2. Make your changes
3. Write tests
4. Submit a pull request

## License

Internal tool - All rights reserved
