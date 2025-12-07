# Services Module

This module contains external API clients and business logic services for the Product Issue Miner application.

## Overview

The services module provides:
- **Zendesk API client** - For fetching support tickets
- **Claude AI analyzer** - For extracting product issues from tickets
- **Sync service** - For orchestrating Zendesk data synchronization
- **Analysis pipeline** - For processing tickets through AI analysis

## Claude AI Integration

### Files

#### `prompts.py`
Contains all prompt templates and product taxonomy:

- **Product Taxonomy**:
  - `CATEGORIES`: Main product areas (TIME_AND_ATTENDANCE, PAYROLL, SETTINGS)
  - `ISSUE_TYPES`: Types of issues (bug, friction, ux_confusion, feature_request, etc.)
  - `SEVERITIES`: Issue severity levels (critical, high, medium, low)

- **System Prompts**:
  - `EXTRACTION_SYSTEM_PROMPT`: Instructs Claude on how to analyze tickets
  - `CLUSTER_NAMING_PROMPT`: Instructs Claude on how to name issue clusters

- **Prompt Builders**:
  - `build_extraction_user_prompt(ticket)`: Creates user prompt for issue extraction
  - `build_cluster_naming_prompt(issues)`: Creates user prompt for cluster naming

#### `analyzer.py`
Provides the `IssueAnalyzer` class for Claude AI interactions:

- **Configuration**:
  - Model: `claude-sonnet-4-5-20250514`
  - Max tokens for extraction: 1024
  - Max tokens for naming: 256

- **Methods**:
  - `extract_issues(ticket)`: Extract product issues from a ticket
  - `name_cluster(issues)`: Generate name and summary for issue cluster
  - `_validate_issue(issue)`: Validate extracted issue against taxonomy

- **Factory Function**:
  - `get_analyzer()`: Creates analyzer instance with settings from environment

## Usage Examples

### Extracting Issues from a Ticket

```python
from app.services import get_analyzer

# Get analyzer instance (uses ANTHROPIC_API_KEY from settings)
analyzer = get_analyzer()

# Prepare ticket data
ticket = {
    'zendesk_ticket_id': 12345,
    'subject': 'Clock-in button not working',
    'description': 'Employees cannot clock in on Android app',
    'public_comments': 'User: Still having issues after update',
    'internal_notes': 'Agent: Confirmed bug on Android 14',
    'requester_email': 'test@example.com',
    'requester_org_name': 'Test Company',
    'tags': ['mobile', 'android', 'clock-in'],
    'ticket_created_at': '2024-01-15T10:30:00Z'
}

# Extract issues
result = analyzer.extract_issues(ticket)

# Result structure:
# {
#     "issues": [
#         {
#             "category": "TIME_AND_ATTENDANCE",
#             "subcategory": "punch_in_out",
#             "issue_type": "bug",
#             "severity": "high",
#             "summary": "Clock-in button unresponsive on Android 14",
#             "detail": "...",
#             "representative_quote": "...",
#             "confidence": 0.92
#         }
#     ],
#     "no_product_issue": false,
#     "skip_reason": null
# }
```

### Naming an Issue Cluster

```python
from app.services import get_analyzer

analyzer = get_analyzer()

# Group of similar issues
issues = [
    {
        'category': 'TIME_AND_ATTENDANCE',
        'subcategory': 'punch_in_out',
        'summary': 'Clock-in button unresponsive on Android 14',
        'representative_quote': 'Button takes 3-4 taps to work'
    },
    {
        'category': 'TIME_AND_ATTENDANCE',
        'subcategory': 'punch_in_out',
        'summary': 'Android app clock-in delay after OS update',
        'representative_quote': 'Have to tap multiple times'
    }
]

# Generate cluster name
result = analyzer.name_cluster(issues)

# Result structure:
# {
#     "cluster_name": "Android 14 clock-in button tap delay",
#     "cluster_summary": "Multiple users report the clock-in button..."
# }
```

### Using the Taxonomy

```python
from app.services import CATEGORIES, ISSUE_TYPES, SEVERITIES

# Get all categories
print(CATEGORIES.keys())
# dict_keys(['TIME_AND_ATTENDANCE', 'PAYROLL', 'SETTINGS'])

# Get subcategories for TIME_AND_ATTENDANCE
print(CATEGORIES['TIME_AND_ATTENDANCE'])
# ['hardware_issues', 'punch_in_out', 'biometric_registration', 'pto', 'reporting', 'corrections']

# Get all issue types
print(ISSUE_TYPES)
# ['bug', 'friction', 'ux_confusion', 'feature_request', 'documentation_gap', 'data_issue']

# Get all severity levels
print(SEVERITIES)
# ['critical', 'high', 'medium', 'low']
```

## Product Taxonomy

### Categories

#### TIME_AND_ATTENDANCE
- `hardware_issues`: Terminal/hardware problems
- `punch_in_out`: Clock in/out functionality
- `biometric_registration`: Fingerprint/facial recognition enrollment
- `pto`: Paid time off and leave management
- `reporting`: Time and attendance reports
- `corrections`: Time correction requests

#### PAYROLL
- `pay_runs`: Payroll processing runs
- `tax_questions`: Tax withholding and compliance
- `direct_deposits`: Direct deposit setup and issues
- `reporting`: Payroll reports
- `errors`: Calculation errors and discrepancies

#### SETTINGS
- `employee_registration`: Adding/managing employees
- `biometric_enrollment`: Biometric setup
- `deductions`: Payroll deductions configuration

### Issue Types

- `bug`: Software defect or malfunction
- `friction`: Feature works but is cumbersome
- `ux_confusion`: Users don't understand how to use feature
- `feature_request`: Request for new functionality
- `documentation_gap`: Missing or unclear documentation
- `data_issue`: Data integrity or accuracy problem

### Severity Levels

- `critical`: Money/compliance issues, complete blockers
- `high`: Major workflow blocked, workaround painful
- `medium`: Impaired but functional
- `low`: Minor inconvenience

## Error Handling

The analyzer includes comprehensive error handling:

1. **JSON Parse Errors**: If Claude returns invalid JSON, the analyzer returns a safe fallback response
2. **API Errors**: Claude API errors are logged and re-raised for upstream handling
3. **Validation Errors**: Invalid taxonomy values are logged and filtered out
4. **Missing Configuration**: Factory function raises ValueError if API key is missing

## Testing

Run the test suite to validate the integration:

```bash
cd backend
python test_analyzer.py
```

The test suite validates:
- Taxonomy definitions
- Prompt generation
- Issue validation logic (if anthropic module is available)

## Configuration

Required environment variables (set in `.env`):

```bash
ANTHROPIC_API_KEY=your-anthropic-api-key
```

See `.env.example` for complete configuration template.

## Logging

The analyzer uses Python's standard logging module:

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Analyzer will log:
# - Invalid issues extracted (WARNING)
# - JSON parse errors (ERROR)
# - Claude API errors (ERROR)
```

## API Costs

The analyzer uses Claude Sonnet 4.5 which has the following costs (as of Jan 2025):
- Input: $3 per million tokens
- Output: $15 per million tokens

Typical token usage per ticket:
- Input: ~500-1500 tokens (ticket content + system prompt)
- Output: ~100-400 tokens (extracted issues)

Estimated cost per ticket: $0.002 - $0.008

For cluster naming:
- Input: ~200-800 tokens
- Output: ~50-100 tokens

Estimated cost per cluster: $0.001 - $0.003

## Architecture Notes

### Why Separate Prompts Module?

The prompts module is separated from the analyzer for several reasons:
1. **Testability**: Prompts can be tested without API calls
2. **Version Control**: Prompt changes are clearly tracked
3. **Reusability**: Prompts can be used in other contexts (testing, debugging)
4. **Maintainability**: Taxonomy and prompts are easy to update

### Why Factory Function?

The `get_analyzer()` factory function:
1. Encapsulates configuration loading
2. Provides a clear dependency injection point
3. Makes testing easier (can inject mock analyzers)
4. Follows FastAPI dependency injection patterns

### Validation Strategy

Issues are validated after extraction to ensure:
1. Claude stays within defined taxonomy
2. Downstream code can rely on valid categories
3. Bad extractions don't corrupt the database
4. We can measure Claude's accuracy over time

## Future Enhancements

Potential improvements:
1. **Caching**: Cache issue extractions to reduce API costs
2. **Batch Processing**: Process multiple tickets in single API call
3. **Fine-tuning**: Create fine-tuned model for better accuracy
4. **Confidence Thresholds**: Automatically flag low-confidence extractions
5. **Multi-language Support**: Add prompts for non-English tickets
6. **Prompt Versioning**: Track prompt versions and A/B test improvements
