"""
Simple test to verify the flexible validator works without Playwright
"""

import sys
import os
from pathlib import Path

# Add the validator directory to the path
sys.path.insert(0, str(Path(__file__).parent / "validator"))

from flexible_validator import FlexibleFlaskValidator

def test_simple_validation():
    """Test basic validation without Playwright."""
    print("Testing Simple Validation (without Playwright)...")
    print("=" * 50)
    
    # Create a simple test Flask app
    test_app_code = '''
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
'''
    
    # Create test project directory
    test_project_dir = Path("simple_test_project")
    test_project_dir.mkdir(exist_ok=True)
    
    # Write test app
    app_file = test_project_dir / "app.py"
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(test_app_code)
    
    # Create requirements.txt
    requirements_file = test_project_dir / "requirements.txt"
    with open(requirements_file, "w", encoding="utf-8") as f:
        f.write("Flask==3.1.2\n")
    
    # Create templates directory
    templates_dir = test_project_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create index.html template
    index_template = templates_dir / "index.html"
    with open(index_template, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Home - Test App</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <h1>Welcome to Test App</h1>
    <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
    </nav>
    <main>
        <p>This is the home page.</p>
    </main>
</body>
</html>""")
    
    # Create about.html template
    about_template = templates_dir / "about.html"
    with open(about_template, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>About - Test App</title>
</head>
<body>
    <h1>About Us</h1>
    <p>This is the about page.</p>
    <a href="/">Back to Home</a>
</body>
</html>""")
    
    try:
        # Run validation (this will skip UI tests since Playwright backend isn't running)
        print("Running validation...")
        validator = FlexibleFlaskValidator(str(test_project_dir))
        success = validator.run_validation(host="127.0.0.1", port=5000)
        
        print(f"\nValidation {'PASSED' if success else 'FAILED'}")
        print(f"Checks passed: {validator.checks_passed}/{validator.total_checks}")
        
        # Show some key results
        print(f"\nKey Results:")
        print("-" * 30)
        for result in validator.validation_results[-10:]:  # Show last 10 results
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status}: {result['name']} - {result['message']}")
        
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
    success = test_simple_validation()
    sys.exit(0 if success else 1)
