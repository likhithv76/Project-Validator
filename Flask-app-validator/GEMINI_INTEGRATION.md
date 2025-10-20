# Gemini AI Test Case Generation Integration

This project now supports AI-powered test case generation using Google's Gemini AI model alongside the existing parser-based approach.

## Configuration

### Environment Configuration

Create a `.env` file in the project root with the following settings:

```env
# Test Case Generation Configuration
TEST_CASE_GENERATOR_METHOD=AI

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# Optional: Fallback configuration
PARSER_FALLBACK_ENABLED=true
```

### Generation Methods

- **AI Mode** (`TEST_CASE_GENERATOR_METHOD=AI`): Uses Gemini AI to generate comprehensive test cases
- **PARSER Mode** (`TEST_CASE_GENERATOR_METHOD=PARSER`): Uses the original parser-based approach

## Features

### AI Generation (Gemini)
- **Intelligent Analysis**: Analyzes project structure and HTML content
- **Comprehensive Test Cases**: Generates realistic input variants and validation rules
- **Playwright Integration**: Creates appropriate browser automation tests
- **Context-Aware**: Understands Flask application patterns and conventions

### Parser Generation (Fallback)
- **Rule-Based**: Uses predefined parsing rules for HTML, CSS, and JavaScript
- **Structured Output**: Generates consistent test case structures
- **Reliable**: Proven approach with predictable results

## Usage

### In Creator Portal

1. **Upload Project**: Upload your Flask project ZIP file
2. **Configure Method**: The system automatically detects your configuration
3. **Generate Test Cases**: Click "Generate Testcases" button
4. **Review Results**: View the generated JSON configuration

### Configuration Display

The Creator Portal shows:
- Current generation method (AI/PARSER)
- Configuration status
- Helpful tips for setup

## API Key Setup

### Getting Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Copy the key to your `.env` file

### Security Notes

- Never commit API keys to version control
- Use environment variables in production
- The `.env` file is ignored by git

## Error Handling

### AI Generation Failures

- **API Key Missing**: Falls back to parser method if `PARSER_FALLBACK_ENABLED=true`
- **Network Issues**: Provides clear error messages
- **Invalid Response**: Attempts to parse and validate AI output

### Parser Fallback

- **Automatic Fallback**: Switches to parser when AI fails
- **Error Logging**: Detailed error messages for debugging
- **Graceful Degradation**: System continues to work even if AI is unavailable

## Generated Output

Both methods generate the same JSON structure:

```json
{
  "project": "Project Name",
  "description": "Project Description",
  "tasks": [
    {
      "id": 1,
      "name": "Task Name",
      "description": "Task description",
      "required_files": ["file1.html"],
      "validation_rules": {
        "type": "html",
        "file": "file1.html",
        "points": 10,
        "generatedTests": [],
        "analysis": {"elements": [], "selectors": []}
      },
      "playwright_test": {
        "route": "/route",
        "actions": [...],
        "validate": [...],
        "points": 10
      },
      "unlock_condition": {"min_score": 0, "required_tasks": []}
    }
  ]
}
```

## Dependencies

### New Dependencies

- `google-generativeai==0.8.3`: Google's Gemini AI Python SDK

### Installation

```bash
pip install google-generativeai==0.8.3
```

## Migration Guide

### From Parser to AI

1. Set up `.env` with your Gemini API key
2. Change `TEST_CASE_GENERATOR_METHOD=AI`
3. Restart the application
4. Test generation with a sample project

### Rollback to Parser

1. Change `TEST_CASE_GENERATOR_METHOD=PARSER` in `.env`
2. Restart the application
3. Parser method will be used immediately

## Troubleshooting

### Common Issues

1. **"Gemini AI not configured"**
   - Check `GEMINI_API_KEY` in `.env`
   - Verify API key is valid

2. **"AI generation failed"**
   - Check internet connection
   - Verify API key permissions
   - Enable parser fallback

3. **"Invalid JSON structure"**
   - AI response parsing failed
   - Check API key and model settings

### Debug Mode

Enable detailed logging by setting environment variables:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## Future Enhancements

- **Custom Prompts**: Allow users to customize AI prompts
- **Model Selection**: Support for different Gemini models
- **Batch Processing**: Generate test cases for multiple projects
- **Template System**: Predefined templates for common Flask patterns
