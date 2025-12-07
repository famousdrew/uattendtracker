# Testing Quick Start Guide

Get up and running with the Product Issue Miner test suite in minutes.

## Backend Tests (Python/pytest)

### 1. Install Dependencies

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\backend
pip install -r requirements.txt
```

This installs:
- pytest (testing framework)
- pytest-asyncio (async support)
- pytest-cov (coverage)
- pytest-mock (mocking)
- faker (test data)

### 2. Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=app --cov-report=html
# Then open: htmlcov/index.html

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::TestTicketModel::test_create_ticket -v

# Run by category
pytest -m database     # Database tests
pytest -m api          # API tests
pytest -m unit         # Fast unit tests
pytest -m zendesk      # Zendesk client tests
pytest -m analyzer     # Claude analyzer tests
pytest -m clustering   # Clustering tests
```

### 3. Verify Coverage

```bash
# Run with minimum coverage threshold
pytest --cov=app --cov-fail-under=70
```

## Frontend Tests (TypeScript/Vitest)

### 1. Install Dependencies

```bash
cd C:\dev\uattendissuetrack\product-issue-miner\frontend
npm install
```

This installs:
- vitest (testing framework)
- @vitest/coverage-v8 (coverage)

### 2. Run Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode (re-run on file changes)
npm run test:watch
```

### 3. View Coverage

Coverage reports are generated in `coverage/` directory:
- `coverage/index.html` - HTML report
- `coverage/coverage-final.json` - JSON report

## What Gets Tested

### Backend (100+ test cases)

1. **Models** (`test_models.py`)
   - Ticket CRUD operations
   - Issue validation and constraints
   - Cluster management
   - Model relationships

2. **Zendesk Client** (`test_zendesk.py`)
   - API authentication
   - Ticket search and retrieval
   - Comment fetching
   - Rate limiting
   - Error handling

3. **Claude Analyzer** (`test_analyzer.py`)
   - Issue extraction
   - JSON parsing
   - Taxonomy validation
   - Cluster naming
   - Confidence scoring

4. **Clustering Service** (`test_clusterer.py`)
   - Issue clustering algorithm
   - Keyword matching
   - Trend calculation
   - Unique customer counting
   - Cluster merging

5. **API Endpoints** (`test_api.py`)
   - GET /api/issues
   - GET /api/issues/summary
   - GET /api/clusters
   - GET /api/clusters/{id}
   - PATCH /api/clusters/{id}
   - Authentication

6. **Sync Service** (`test_sync.py`)
   - Incremental sync
   - Backfill sync
   - Ticket upsert
   - Error handling

### Frontend (25+ test cases)

1. **API Client** (`api.test.ts`)
   - Authentication headers
   - All API methods
   - Error handling
   - Request formatting
   - Response parsing

## Common Issues & Solutions

### Backend

**Import errors**:
```bash
# Make sure you're in the backend directory
cd C:\dev\uattendissuetrack\product-issue-miner\backend
pytest
```

**Module not found**:
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

**Tests hanging**:
- Check for missing `@pytest.mark.asyncio` decorator on async tests
- Ensure `pytest-asyncio` is installed

### Frontend

**Module not found**:
```bash
# Reinstall dependencies
npm install
```

**Tests not running**:
- Verify vitest is installed: `npm list vitest`
- Check vitest.config.ts exists

## Test Output Examples

### Successful Test Run
```
======================== test session starts ========================
collected 105 items

tests/test_models.py::TestTicketModel::test_create_ticket PASSED [ 1%]
tests/test_models.py::TestTicketModel::test_unique_id PASSED     [ 2%]
...
tests/test_sync.py::TestSyncService::test_backfill PASSED       [100%]

======================== 105 passed in 12.34s =======================
```

### Coverage Report
```
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
app/models/ticket.py              45      2    96%   77-78
app/models/issue.py               52      3    94%
app/services/zendesk.py          120     12    90%
app/services/analyzer.py          85      8    91%
app/services/clusterer.py        110     15    86%
app/api/issues.py                 95     10    89%
app/api/clusters.py               88      9    90%
------------------------------------------------------------
TOTAL                            595     59    90%
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
# GitHub Actions example
- name: Run Backend Tests
  run: |
    cd backend
    pip install -r requirements.txt
    pytest --cov=app --cov-report=xml --cov-fail-under=70

- name: Run Frontend Tests
  run: |
    cd frontend
    npm install
    npm run test:coverage
```

## Next Steps

1. Run tests to verify setup: `pytest` (backend) and `npm test` (frontend)
2. Check coverage: Look for modules below 70% and add tests
3. Set up pre-commit hooks to run tests before commits
4. Configure CI/CD to run tests on pull requests

## Need Help?

- Backend tests: See `backend/tests/README.md`
- Full coverage summary: See `TEST_COVERAGE_SUMMARY.md`
- Test examples: Look in any `test_*.py` file

## Test File Locations

### Backend
```
C:\dev\uattendissuetrack\product-issue-miner\backend\
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Includes test dependencies
└── tests/
    ├── conftest.py              # Shared fixtures
    ├── test_models.py           # Model tests
    ├── test_zendesk.py          # Zendesk client tests
    ├── test_analyzer.py         # AI analyzer tests
    ├── test_clusterer.py        # Clustering tests
    ├── test_api.py              # API endpoint tests
    └── test_sync.py             # Sync service tests
```

### Frontend
```
C:\dev\uattendissuetrack\product-issue-miner\frontend\
├── vitest.config.ts             # Vitest configuration
├── package.json                 # Includes test scripts
└── src/
    └── __tests__/
        └── api.test.ts          # API client tests
```

## Coverage Targets

- Minimum: 70% overall
- Models: 90%+
- Services: 85%+
- API endpoints: 80%+
