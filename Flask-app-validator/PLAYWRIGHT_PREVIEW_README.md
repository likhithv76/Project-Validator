# Playwright Preview System for Creator Portal

## Overview

The Creator Portal now includes a comprehensive Playwright preview system that allows creators to:

1. **Test their tasks** with the same Playwright validation that students will face
2. **Capture reference screenshots** for comparison with student submissions
3. **Validate task configurations** before saving projects
4. **Ensure test cases work correctly** before publishing

## Features

### 🔍 Task Preview
- Run Playwright tests on all configured tasks
- Execute the same validation logic that students will encounter
- Show test results with pass/fail status
- Display validation details and error messages

### 📸 Reference Screenshots
- Capture reference images for each task
- Store screenshots for later comparison with student submissions
- Visual validation of task requirements

### ✅ Validation Results
- Real-time feedback on task configuration
- Detailed test execution results
- Error reporting and debugging information

## Setup

### 1. Start Playwright Backend
```bash
python playwright_backend/start_server.py
```

The backend will run on `http://127.0.0.1:8001`

### 2. Use Creator Portal
1. Upload your project ZIP file
2. Configure your tasks with routes, actions, and validation rules
3. Click "🔍 Preview All Tasks" to test your configuration
4. Click "📸 Capture Reference Screenshots" to save reference images
5. Review results and fix any issues before saving

## How It Works

### Task Configuration
Each task can include:
- **Route**: The URL path to test (e.g., `/login`, `/dashboard`)
- **Actions**: Playwright actions to execute (click, input, navigate)
- **Validation Rules**: What to check for (text presence, element existence, etc.)

### Test Execution
1. Creator uploads project ZIP
2. System extracts and starts Flask app
3. Playwright tests each task configuration
4. Results are displayed with pass/fail status
5. Screenshots are captured and stored

### Reference Screenshots
- Captured after executing all configured actions
- Stored for comparison with student submissions
- Used for visual validation and feedback

## API Endpoints

### Health Check
```
GET /health
```
Returns backend status and Playwright availability.

### Custom Task Test
```
POST /run-custom-task-test
```
Runs a custom task test with provided configuration.

**Request Body:**
```json
{
  "base_url": "http://127.0.0.1:5000",
  "project_name": "task_1",
  "timeout": 30,
  "headless": true,
  "capture_screenshots": true,
  "task_config": {
    "task_id": 1,
    "route": "/login",
    "actions": [
      {
        "type": "input",
        "selector_type": "class",
        "selector_value": "email-input",
        "input_variants": ["test@example.com"]
      },
      {
        "type": "click",
        "selector_type": "class",
        "selector_value": "submit-btn"
      }
    ],
    "validate": [
      {
        "type": "text_present",
        "value": "Login successful"
      }
    ]
  }
}
```

## Supported Actions

### Click Actions
```json
{
  "type": "click",
  "selector_type": "class|id|text",
  "selector_value": "button-class"
}
```

### Input Actions
```json
{
  "type": "input",
  "selector_type": "class|id|name",
  "selector_value": "input-field",
  "input_variants": ["value1", "value2"]
}
```

### Navigation Actions
```json
{
  "type": "navigate",
  "url": "/new-page"
}
```

## Supported Validation Rules

### Text Presence
```json
{
  "type": "text_present",
  "value": "Expected text content"
}
```

### Element Presence
```json
{
  "type": "element_present",
  "value": ".css-selector"
}
```

### Title Contains
```json
{
  "type": "title_contains",
  "value": "Page Title"
}
```

### URL Contains
```json
{
  "type": "url_contains",
  "value": "/expected-path"
}
```

## Troubleshooting

### Backend Not Available
- Ensure Playwright backend is running: `python playwright_backend/start_server.py`
- Check that port 8001 is not in use
- Verify Playwright is installed: `playwright install`

### Flask App Issues
- Ensure the uploaded ZIP contains a valid Flask application
- Check that `app.py` exists and is runnable
- Verify all dependencies are installed

### Test Failures
- Review task configuration for correct routes and selectors
- Check that validation rules match expected page content
- Use browser developer tools to verify selectors

## Benefits

1. **Quality Assurance**: Ensure tasks work before students see them
2. **Reference Images**: Capture expected results for comparison
3. **Debugging**: Identify configuration issues early
4. **Consistency**: Same validation logic for creators and students
5. **Visual Feedback**: Screenshots help understand test execution

This system ensures that creators can confidently publish well-tested tasks that will work correctly for students.



