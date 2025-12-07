# Product Issue Miner - Test Suite

Comprehensive test coverage for the Product Issue Miner application, focusing on critical paths including Zendesk sync, Claude analysis, clustering algorithms, and API endpoints.

## Test Structure

```
backend/tests/
├── conftest.py              # Pytest fixtures and test configuration
├── test_models.py           # Database model CRUD tests
├── test_zendesk.py          # Zendesk API client tests
├── test_analyzer.py         # Claude AI analyzer tests
├── test_clusterer.py        # Issue clustering algorithm tests
├── test_api.py              # FastAPI endpoint tests
└── test_sync.py             # Sync service tests
```

## Installation

Install test dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Test dependencies include:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `faker` - Test data generation

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_models.py
pytest tests/test_zendesk.py
pytest tests/test_analyzer.py
```

### Run Tests by Marker
```bash
# Database tests only
pytest -m database

# API tests only
pytest -m api

# Unit tests (fast, no external dependencies)
pytest -m unit

# Integration tests
pytest -m integration
```

### Run with Coverage
```bash
# Terminal coverage report
pytest --cov=app --cov-report=term-missing

# HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Run in Verbose Mode
```bash
pytest -v
```

### Run Specific Test
```bash
pytest tests/test_models.py::TestTicketModel::test_create_ticket
```

## Test Markers

Tests are categorized with markers for selective execution:

- `@pytest.mark.unit` - Fast unit tests with no external dependencies
- `@pytest.mark.integration` - Integration tests requiring database/services
- `@pytest.mark.database` - Tests requiring database connection
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.zendesk` - Zendesk client functionality tests
- `@pytest.mark.analyzer` - Claude AI analyzer tests
- `@pytest.mark.clustering` - Clustering algorithm tests
- `@pytest.mark.sync` - Sync service tests
- `@pytest.mark.slow` - Slow-running tests

## Test Coverage

### Test Models (`test_models.py`)
- Ticket model CRUD operations
- ExtractedIssue model validation
- IssueCluster model operations
- Model relationships and cascade deletes
- Constraint validation (categories, severities, issue types)

### Zendesk Client (`test_zendesk.py`)
- Authentication and client initialization
- Ticket search with pagination
- Comment fetching and formatting
- Rate limiting enforcement
- Error handling and retry logic (429, 5xx errors)
- Request/response parsing

### Claude Analyzer (`test_analyzer.py`)
- Issue extraction from tickets
- JSON response parsing
- Taxonomy validation
- Confidence scoring
- Cluster naming
- Error handling for malformed responses

### Clustering Service (`test_clusterer.py`)
- Issue clustering algorithm
- Keyword matching and similarity
- Trend calculation (7-day rolling)
- Unique customer counting
- Cluster merging
- Existing cluster assignment

### API Endpoints (`test_api.py`)
- GET /api/issues with filters
- GET /api/issues/summary
- GET /api/clusters with sorting/filtering
- GET /api/clusters/{id}
- PATCH /api/clusters/{id}
- Authentication requirements
- Pagination
- Error responses (401, 404, 400)

### Sync Service (`test_sync.py`)
- Incremental sync
- Backfill sync (last N days)
- Ticket upsert logic (insert/update)
- Sync state tracking
- Error handling during sync
- Comment aggregation
- Requester/organization fetching

## Fixtures

### Database Fixtures
- `test_engine` - In-memory SQLite database engine
- `db_session` - Async database session with rollback
- `create_ticket` - Factory for creating test tickets
- `create_issue` - Factory for creating test issues
- `create_cluster` - Factory for creating test clusters

### Mock Fixtures
- `mock_zendesk_client` - Mocked Zendesk API client
- `mock_claude_analyzer` - Mocked Claude AI analyzer
- `auth_header` - Valid authentication header
- `invalid_auth_header` - Invalid authentication header

### Sample Data Fixtures
- `sample_zendesk_ticket` - Sample ticket data
- `sample_zendesk_comments` - Sample comment data
- `sample_ticket_with_comments` - Complete ticket with comments
- `sample_extracted_issue_data` - Sample issue data
- `sample_ticket_with_issues` - Ticket with multiple issues
- `sample_cluster_with_issues` - Cluster with issues and tickets

## Configuration

Test configuration is in `pytest.ini`:

- **Coverage threshold**: 70% minimum
- **Asyncio mode**: auto
- **Test discovery**: `test_*.py` files
- **Output**: Progress style with coverage reports

## Writing New Tests

### Test Naming Convention
- Test files: `test_<module>.py`
- Test classes: `Test<Feature>`
- Test functions: `test_<behavior>`

### Example Test
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
@pytest.mark.database
async def test_create_ticket(db_session: AsyncSession, create_ticket):
    """Test creating a new ticket."""
    ticket = await create_ticket(
        zendesk_ticket_id=12345,
        subject="Test ticket"
    )

    assert ticket.id is not None
    assert ticket.zendesk_ticket_id == 12345
    assert ticket.subject == "Test ticket"
```

### Async Testing
All async tests must use:
- `@pytest.mark.asyncio` decorator
- `async def` function definition
- `await` for async operations

### Mocking External Services
Always mock external API calls (Zendesk, Claude) to:
- Avoid real API calls during tests
- Ensure tests are deterministic
- Speed up test execution

Example:
```python
def test_zendesk_search(mock_zendesk_client):
    mock_zendesk_client.search_tickets.return_value = {
        "results": [{"id": 123}],
        "count": 1
    }

    # Test code using mock
```

## Continuous Integration

To run tests in CI/CD:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=app --cov-report=xml --cov-report=term

# Check coverage threshold
pytest --cov=app --cov-fail-under=70
```

## Troubleshooting

### Import Errors
If you get import errors, ensure you're running pytest from the `backend/` directory:
```bash
cd backend
pytest
```

### Database Errors
Tests use in-memory SQLite by default. No database setup required.

### Async Errors
Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

### Coverage Not Working
Install coverage tools:
```bash
pip install pytest-cov
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Mock External Services**: Never make real API calls in tests
3. **Use Fixtures**: Reuse common setup via fixtures
4. **Descriptive Names**: Test names should describe behavior
5. **Test Edge Cases**: Include error handling and boundary tests
6. **Keep Tests Fast**: Mock slow operations, use in-memory DB
7. **Clean Data**: Use transactions/rollbacks for database tests

## Coverage Goals

Target coverage by module:
- Models: 90%+
- Services: 85%+
- API endpoints: 80%+
- Overall: 70%+ minimum

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)
