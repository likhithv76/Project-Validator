# Playwright Backend for Flask Validator

This directory contains the Playwright-based UI testing backend that integrates with the Flask application validator.

## Overview

The Playwright backend provides headless browser testing capabilities for Flask applications, including:

- **Basic Navigation Tests**: Page loading, content validation, responsive design
- **Authentication Tests**: Login, registration, logout, session management
- **CRUD Operations Tests**: Create, read, update, delete functionality
- **Database Integration Tests**: Data persistence, relationships, performance
- **Security Tests**: XSS protection, SQL injection, input validation

## Architecture

```
playwright_backend/
├── server.py              # FastAPI server with REST endpoints
├── runner.py              # Playwright test execution engine
├── start_server.py        # Startup script with dependency management
├── config.py              # Configuration settings
├── tests/                 # Test suite directory
│   ├── test_basic_navigation.py
│   ├── test_authentication.py
│   ├── test_crud_operations.py
│   ├── test_database_integration.py
│   └── test_security.py
└── results/               # Test results and screenshots
    ├── logs/
    └── screenshots/
```

## API Endpoints

### `GET /health`
Health check endpoint to verify the server is running.

### `POST /run-ui-tests`
Run UI tests on a Flask application.

**Request Body:**
```json
{
    "base_url": "http://127.0.0.1:5000",
    "test_suite": "default",
    "project_name": "student_project",
    "timeout": 30,
    "headless": true,
    "capture_screenshots": true
}
```

**Response:**
```json
{
    "status": "completed",
    "results": [
        {
            "name": "test_home_page_loads",
            "status": "PASS",
            "duration": 1.42,
            "error": null,
            "screenshot": null
        }
    ],
    "screenshots": [],
    "logs": [],
    "total_tests": 1,
    "passed_tests": 1,
    "failed_tests": 0,
    "execution_time": 1.42
}
```

### `GET /test-suites`
List available test suites.

### `GET /results/{project_name}`
Get test results for a specific project.

### `DELETE /results/{project_name}`
Clear test results for a specific project.

## Usage

### Starting the Server

```bash
# Option 1: Using the startup script (recommended)
python start_server.py

# Option 2: Direct server start
python server.py

# Option 3: Using uvicorn directly
uvicorn server:app --host 127.0.0.1 --port 8001
```

### Integration with Flask Validator

The Playwright backend is automatically integrated with `flexible_validator.py`. When you run validation, it will:

1. Check if the Playwright backend is running
2. Start it automatically if not running
3. Execute UI tests on the Flask application
4. Include results in the validation report

### Manual Testing

You can also run tests manually by sending HTTP requests to the API:

```bash
# Health check
curl http://127.0.0.1:8001/health

# Run tests
curl -X POST http://127.0.0.1:8001/run-ui-tests \
  -H "Content-Type: application/json" \
  -d '{"base_url": "http://127.0.0.1:5000", "test_suite": "default"}'
```

## Test Suites

### Default Suite
Runs all available tests covering basic functionality.

### Authentication Suite (`auth`)
Focuses on login, registration, and session management tests.

### CRUD Suite (`crud`)
Tests create, read, update, delete operations.

### Security Suite (`security`)
Validates security features and vulnerability protection.

### Database Suite (`database`)
Tests database integration and data persistence.

### Navigation Suite (`navigation`)
Basic page loading and navigation tests.

## Configuration

Edit `config.py` to customize:

- Server host and port
- Test timeouts
- Browser settings
- Viewport sizes
- Available test suites

## Dependencies

- `fastapi`: Web framework for the API server
- `uvicorn`: ASGI server for FastAPI
- `playwright`: Browser automation
- `pytest-playwright`: Playwright testing utilities
- `beautifulsoup4`: HTML parsing for validation

## Installation

```bash
# Install Python dependencies
pip install fastapi uvicorn playwright pytest-playwright beautifulsoup4

# Install Playwright browsers
playwright install chromium
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Make sure the server is running on port 8001
2. **Browser Launch Failed**: Ensure Playwright browsers are installed
3. **Test Timeouts**: Increase timeout values in configuration
4. **Permission Errors**: Run with appropriate permissions for file operations

### Debug Mode

Set environment variable for detailed logging:
```bash
export PLAYWRIGHT_DEBUG=1
python start_server.py
```

### Logs

Check the `results/logs/` directory for detailed test execution logs.

## Security Considerations

- The backend runs in a sandboxed environment
- Browser processes are isolated
- File system access is restricted to results directory
- Network access is limited to localhost by default

## Performance

- Tests run in headless mode for speed
- Parallel execution is supported
- Screenshots are only captured on failures by default
- Results are cached to avoid redundant testing
