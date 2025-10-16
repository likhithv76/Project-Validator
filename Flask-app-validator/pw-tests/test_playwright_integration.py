"""
Test script to verify Playwright integration with flexible_validator.py
"""

import sys
import os
from pathlib import Path

# Add the validator directory to the path
sys.path.insert(0, str(Path(__file__).parent / "validator"))

from flexible_validator import FlexibleFlaskValidator

def test_playwright_integration():
    """Test the Playwright integration."""
    print("Testing Playwright Integration...")
    print("=" * 50)
    
    # Create a simple test Flask app for testing
    test_app_code = '''
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route("/")
def home():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Flask App</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
        <h1>Welcome to Test Flask App</h1>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
        </nav>
        <main>
            <p>This is a test Flask application for Playwright testing.</p>
            <form method="POST" action="/submit">
                <label for="name">Name:</label>
                <input type="text" id="name" name="name" required>
                <label for="email">Email:</label>
                <input type="email" id="email" name="email" required>
                <button type="submit">Submit</button>
            </form>
        </main>
    </body>
    </html>
    """)

@app.route("/about")
def about():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>About - Test Flask App</title>
    </head>
    <body>
        <h1>About Us</h1>
        <p>This is the about page.</p>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """)

@app.route("/submit", methods=["POST"])
def submit():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Success - Test Flask App</title>
    </head>
    <body>
        <h1>Form Submitted Successfully!</h1>
        <p>Thank you for your submission.</p>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
'''
    
    # Create test project directory
    test_project_dir = Path("test_flask_project")
    test_project_dir.mkdir(exist_ok=True)
    
    # Write test app
    app_file = test_project_dir / "app.py"
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(test_app_code)
    
    # Create requirements.txt
    requirements_file = test_project_dir / "requirements.txt"
    with open(requirements_file, "w", encoding="utf-8") as f:
        f.write("Flask==3.1.2\n")
    
    # Create templates directory and basic template
    templates_dir = test_project_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create a simple base template
    base_template = templates_dir / "base.html"
    with open(base_template, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Flask App{% endblock %}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>""")
    
    try:
        # Run validation with Playwright tests
        print("Running validation with Playwright UI tests...")
        validator = FlexibleFlaskValidator(str(test_project_dir))
        success = validator.run_validation(host="127.0.0.1", port=5000)
        
        print(f"\nValidation {'PASSED' if success else 'FAILED'}")
        print(f"Checks passed: {validator.checks_passed}/{validator.total_checks}")
        
        # Show UI test results
        ui_tests = validator.run_log.get("ui_tests", [])
        if ui_tests:
            print(f"\nUI Test Results:")
            print("-" * 30)
            for test in ui_tests:
                status = test.get("status", "UNKNOWN")
                name = test.get("name", "Unknown")
                duration = test.get("duration", 0.0)
                error = test.get("error", "")
                
                print(f"{status}: {name} ({duration:.2f}s)")
                if error:
                    print(f"  Error: {error}")
        else:
            print("\nNo UI test results found")
        
        return success
        
    except Exception as e:
        print(f"Error during validation: {e}")
        return False
    
    finally:
        # Cleanup
        import shutil
        if test_project_dir.exists():
            shutil.rmtree(test_project_dir)

if __name__ == "__main__":
    success = test_playwright_integration()
    sys.exit(0 if success else 1)
