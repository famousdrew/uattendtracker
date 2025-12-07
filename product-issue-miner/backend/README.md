# Product Issue Miner - Backend API

FastAPI backend for the Product Issue Miner application that analyzes Zendesk tickets and mines product issues using AI.

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

Required variables:
- `ZENDESK_EMAIL`: Your Zendesk user email
- `ZENDESK_API_TOKEN`: Your Zendesk API token
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `DATABASE_URL`: PostgreSQL connection string (use `postgresql+asyncpg://` prefix)
- `DASHBOARD_PASSWORD`: Password for dashboard access

### 4. Database Setup

Create a PostgreSQL database:

```bash
createdb product_issue_miner
```

Run initial migration:

```bash
alembic upgrade head
```

## Running the Application

### Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback migration

```bash
alembic downgrade -1
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
│   ├── versions/         # Migration scripts
│   └── env.py           # Alembic configuration
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration settings
│   ├── database.py      # Database setup
│   ├── models/          # SQLAlchemy models (to be created)
│   ├── api/             # API routes (to be created)
│   ├── services/        # Business logic (to be created)
│   └── schemas/         # Pydantic schemas (to be created)
├── requirements.txt     # Python dependencies
├── alembic.ini         # Alembic configuration
└── .env                # Environment variables (not in git)
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy 2.0**: Async ORM for database operations
- **PostgreSQL**: Primary database (via asyncpg)
- **Alembic**: Database migration tool
- **Pydantic**: Data validation using Python type annotations
- **Redis**: Caching and job queue (optional)
- **APScheduler**: Background job scheduling
- **Anthropic SDK**: Claude AI integration
- **HTTPX**: Async HTTP client for Zendesk API
