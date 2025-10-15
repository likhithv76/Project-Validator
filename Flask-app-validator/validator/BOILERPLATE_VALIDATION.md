# Boilerplate Conformance Validation

The Flexible Flask Validator now supports **boilerplate conformance validation** - a structural and naming compliance layer that ensures student projects follow instructor-defined templates exactly.

## 🎯 What It Validates

✅ **HTML Structure**: Ensures proper nesting and hierarchy (e.g., `<div><div><form><button></button></form></div></div>`)

✅ **Class Names**: Validates that required CSS classes are present (e.g., `container`, `form-section`, `submit-btn`)

✅ **JavaScript Functions**: Ensures required JS functions exist (e.g., `validateForm()`, `handleSubmit()`)

✅ **File Structure**: Validates that expected files exist in the correct locations

## 📋 How to Use

### Step 1: Create Boilerplate Rules File

Create a JSON file (e.g., `boilerplateRules.json`) with your structural requirements:

```json
{
  "rules": [
    {
      "type": "boilerplate",
      "file": "templates/register.html",
      "expected_structure": {
        "div": {
          "div": {
            "form": {
              "div": {},
              "div": {},
              "button": {}
            }
          }
        }
      },
      "required_classes": ["form-container", "submit-btn", "form-group"],
      "required_functions": ["validateForm", "submitHandler"],
      "points": 15
    }
  ]
}
```

### Step 2: Run Validation with Boilerplate Rules

```bash
python flexible_validator.py /path/to/student/project 127.0.0.1 5000 boilerplateRules.json
```

Or in Python:
```python
from validator.flexible_validator import FlexibleFlaskValidator

validator = FlexibleFlaskValidator("/path/to/project", rules_file="boilerplateRules.json")
success = validator.run_validation()
```

## 🔧 Rule Configuration

### HTML Structure Validation

Define the expected nested HTML structure:

```json
"expected_structure": {
  "div": {                    // Must have a <div> at root level
    "div": {                  // Inside that div, must have another <div>
      "form": {               // Inside that div, must have a <form>
        "div": {},            // Inside form, must have a <div>
        "button": {}          // Inside form, must have a <button>
      }
    }
  }
}
```

### Required Classes

Specify CSS classes that must be present somewhere in the HTML:

```json
"required_classes": ["container", "form-group", "submit-btn"]
```

### Required JavaScript Functions

Specify JavaScript functions that must exist in any `.js` file:

```json
"required_functions": ["validateForm", "handleSubmit", "loadData"]
```

## 📊 Example Output

### ✅ Successful Validation
```
PASS: Boilerplate: templates/register.html - Boilerplate structure matches expected template.
```

### ❌ Failed Validation
```
FAIL: Boilerplate: templates/register.html - Structure: Missing <button> inside <form>; Missing classes: ['submit-btn']; Missing JS functions: ['submitHandler']
```

## 🎓 Educational Benefits

1. **Consistency**: Ensures all students follow the same structural patterns
2. **Best Practices**: Enforces proper HTML nesting and semantic structure
3. **Naming Conventions**: Validates CSS class naming standards
4. **Functionality**: Ensures required JavaScript functions are implemented
5. **Detailed Feedback**: Provides specific error messages for easy debugging

## 🔍 Advanced Features

### Multiple File Validation
You can validate multiple files in a single rules file:

```json
{
  "rules": [
    {
      "type": "boilerplate",
      "file": "templates/login.html",
      "expected_structure": { "div": { "form": {} } },
      "required_classes": ["login-form"],
      "points": 10
    },
    {
      "type": "boilerplate", 
      "file": "templates/dashboard.html",
      "expected_structure": { "div": { "table": {} } },
      "required_classes": ["data-table"],
      "points": 15
    }
  ]
}
```

### Flexible Structure Matching
The structure validation is flexible - it only checks for the presence of required elements, not their exact positioning or additional elements.

### JavaScript Function Detection
The validator searches all `.js` files in the project for function definitions using the pattern `function functionName(`.

## 🚀 Integration with Existing Validator

The boilerplate validation integrates seamlessly with your existing validation pipeline:

- Runs alongside HTML, requirements, database, security, and runtime validations
- Uses the same logging and reporting system
- Contributes to the overall validation score
- Appears in both text logs and JSON summaries

## 📝 Best Practices for Instructors

1. **Start Simple**: Begin with basic structure requirements and add complexity gradually
2. **Focus on Learning**: Use boilerplate rules to enforce concepts students should learn
3. **Provide Examples**: Give students example HTML that matches your boilerplate requirements
4. **Iterative Refinement**: Update rules based on common student mistakes
5. **Clear Documentation**: Explain the reasoning behind structural requirements

## 🔧 Technical Requirements

- **BeautifulSoup4**: Required for HTML parsing (automatically installed with requirements.txt)
- **Python 3.6+**: Compatible with existing validator requirements
- **JSON**: Rules file must be valid JSON format

The boilerplate validation feature maintains the lightweight nature of your validator while adding powerful structural compliance checking that helps ensure consistent, well-structured student projects.
