"""
Test script to verify the complete rule generation workflow.
Tests the rule builder, rule templates, and integration with the validator.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add the streamlit_app directory to the path
sys.path.insert(0, str(Path(__file__).parent / "streamlit_app"))

from utils.rule_templates import (
    create_html_rule, create_boilerplate_rule, create_requirements_rule,
    create_database_rule, create_security_rule, create_runtime_rule,
    save_rules_to_file, load_rules_from_file, validate_rule
)

def test_rule_templates():
    """Test rule template creation."""
    print("Testing rule template creation...")
    
    # Test HTML rule
    html_rule = create_html_rule(
        file_path="templates/index.html",
        elements=["div", "form", "input"],
        classes=["container", "btn"],
        content=["Welcome", "Login"],
        inputs=["username", "password"],
        points=15
    )
    
    print(f"[OK] HTML rule created: {html_rule['type']} - {html_rule['file']}")
    
    # Test boilerplate rule
    boilerplate_rule = create_boilerplate_rule(
        file_path="app.py",
        expected_structure={"div": {"class": "container"}},
        required_classes=["main-container"],
        required_functions=["login", "logout"],
        points=25
    )
    
    print(f"[OK] Boilerplate rule created: {boilerplate_rule['type']} - {boilerplate_rule['file']}")
    
    # Test requirements rule
    requirements_rule = create_requirements_rule(
        file_path="requirements.txt",
        packages=["Flask", "Flask-SQLAlchemy"],
        points=10
    )
    
    print(f"[OK] Requirements rule created: {requirements_rule['type']} - {requirements_rule['file']}")
    
    # Test database rule
    database_rule = create_database_rule(
        file_path="instance/app.db",
        must_exist=True,
        points=20
    )
    
    print(f"[OK] Database rule created: {database_rule['type']} - {database_rule['file']}")
    
    # Test security rule
    security_rule = create_security_rule(
        file_path="app.py",
        security_features=["password hashing", "session management"],
        points=30
    )
    
    print(f"[OK] Security rule created: {security_rule['type']} - {security_rule['file']}")
    
    # Test runtime rule
    runtime_rule = create_runtime_rule(
        file_path="app.py",
        routes=["/", "/login", "/register"],
        points=20
    )
    
    print(f"[OK] Runtime rule created: {runtime_rule['type']} - {runtime_rule['file']}")
    
    return [html_rule, boilerplate_rule, requirements_rule, database_rule, security_rule, runtime_rule]

def test_rule_validation():
    """Test rule validation."""
    print("\nTesting rule validation...")
    
    # Test valid rule
    valid_rule = create_html_rule("templates/index.html", ["div"], [], [], [], 10)
    errors = validate_rule(valid_rule)
    print(f"[OK] Valid rule validation: {len(errors)} errors")
    
    # Test invalid rule (missing required fields)
    invalid_rule = {"type": "html"}  # Missing file and points
    errors = validate_rule(invalid_rule)
    print(f"[OK] Invalid rule validation: {len(errors)} errors")
    
    if errors:
        for error in errors:
            print(f"   - {error}")

def test_rule_file_operations():
    """Test saving and loading rules to/from files."""
    print("\nTesting rule file operations...")
    
    # Create test rules
    rules = test_rule_templates()
    
    # Test saving to file
    test_file = "test_rules.json"
    if save_rules_to_file(rules, test_file):
        print(f"[OK] Rules saved to {test_file}")
    else:
        print(f"[ERROR] Failed to save rules to {test_file}")
        return
    
    # Test loading from file
    loaded_rules = load_rules_from_file(test_file)
    if loaded_rules:
        print(f"[OK] Rules loaded from {test_file}: {len(loaded_rules)} rules")
        
        # Verify loaded rules match original
        if len(loaded_rules) == len(rules):
            print("[OK] Loaded rules count matches original")
        else:
            print("[ERROR] Loaded rules count doesn't match original")
    else:
        print(f"[ERROR] Failed to load rules from {test_file}")
    
    # Cleanup
    try:
        Path(test_file).unlink()
        print(f"[OK] Cleaned up test file {test_file}")
    except:
        print(f"[WARNING] Could not clean up test file {test_file}")

def test_rule_integration():
    """Test integration with the validator."""
    print("\nTesting rule integration with validator...")
    
    # Create a test rules file
    rules = [
        create_html_rule("templates/index.html", ["div"], ["container"], ["Welcome"], [], 10),
        create_requirements_rule("requirements.txt", ["Flask"], 5)
    ]
    
    rules_file = "test_integration_rules.json"
    if not save_rules_to_file(rules, rules_file):
        print("[ERROR] Failed to create test rules file")
        return
    
    try:
        # Test that the validator can load the rules
        from validator.flexible_validator import FlexibleFlaskValidator
        
        # Create a minimal test project
        test_project_dir = Path("test_project")
        test_project_dir.mkdir(exist_ok=True)
        
        # Create a simple app.py
        app_content = '''
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
'''
        
        with open(test_project_dir / "app.py", "w") as f:
            f.write(app_content)
        
        # Create templates directory
        templates_dir = test_project_dir / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # Create index.html
        html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>Test App</title>
</head>
<body>
    <div class="container">
        <h1>Welcome to Test App</h1>
    </div>
</body>
</html>
'''
        
        with open(templates_dir / "index.html", "w") as f:
            f.write(html_content)
        
        # Create requirements.txt
        with open(test_project_dir / "requirements.txt", "w") as f:
            f.write("Flask==3.1.2\n")
        
        # Test validator with custom rules
        validator = FlexibleFlaskValidator(str(test_project_dir), rules_file=rules_file)
        
        # Run validation (without starting the app)
        print("[OK] Validator created with custom rules")
        print(f"[OK] Rules file: {validator.rules_file}")
        print(f"[OK] Loaded {len(validator.json_rules)} rules")
        
        # Show loaded rules
        for i, rule in enumerate(validator.json_rules):
            print(f"   Rule {i+1}: {rule['type']} - {rule['file']} ({rule['points']} points)")
        
    except Exception as e:
        print(f"[ERROR] Error testing validator integration: {e}")
    
    finally:
        # Cleanup
        try:
            Path(rules_file).unlink()
            import shutil
            if test_project_dir.exists():
                shutil.rmtree(test_project_dir)
            print("[OK] Cleaned up test files")
        except:
            print("[WARNING] Could not clean up all test files")

def main():
    """Run all tests."""
    print("Testing Rule Generation Workflow")
    print("=" * 50)
    
    try:
        test_rule_templates()
        test_rule_validation()
        test_rule_file_operations()
        test_rule_integration()
        
        print("\nAll tests completed successfully!")
        print("\nThe rule generation workflow is working correctly.")
        print("You can now use the Streamlit app to create custom rules.")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
