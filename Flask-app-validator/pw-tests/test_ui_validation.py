"""
Test script for Playwright UI validation with rule-based testing.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add the validator directory to the path
sys.path.insert(0, str(Path(__file__).parent / "validator"))

from flexible_validator import FlexibleFlaskValidator

def test_ui_validation():
    """Test the UI validation with the test Flask app."""
    print("Testing Playwright UI Validation with Rule-Based Testing")
    print("=" * 60)
    
    # Create test project directory
    test_project_dir = Path("test_flask_project")
    if not test_project_dir.exists():
        print("Test project directory not found. Please create it first.")
        return False
    
    # Create requirements.txt for the test project
    requirements_content = "Flask==3.1.2\n"
    with open(test_project_dir / "requirements.txt", "w") as f:
        f.write(requirements_content)
    
    print(f"Testing project: {test_project_dir}")
    
    try:
        # Initialize validator
        validator = FlexibleFlaskValidator(
            project_path=str(test_project_dir),
            rules_file="streamlit_app/rules/ui_rules_example.json"
        )
        
        print("Starting Flask app...")
        
        # Start the Flask app in a subprocess
        flask_process = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=test_project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for app to start
        print("Waiting for Flask app to start...")
        time.sleep(3)
        
        try:
            # Run validation
            print("Running validation with UI tests...")
            success = validator.run_validation()
            
            print("\nValidation Results:")
            print("-" * 40)
            print(f"Checks passed: {validator.checks_passed}/{validator.total_checks}")
            print(f"Errors: {len(validator.errors)}")
            print(f"Warnings: {len(validator.warnings)}")
            
            # Display UI test results
            ui_tests = validator.run_log.get('ui_tests', [])
            if ui_tests:
                print(f"\nUI Test Results ({len(ui_tests)} tests):")
                print("-" * 40)
                
                for test in ui_tests:
                    status = test.get('status', 'UNKNOWN')
                    test_name = test.get('test', 'Unknown')
                    route = test.get('route', '')
                    duration = test.get('duration', 0.0)
                    error = test.get('error', '')
                    points = test.get('points', 0)
                    
                    status_symbol = "[PASS]" if status == "PASS" else "[FAIL]"
                    print(f"{status_symbol} {test_name} ({route}) - {duration:.2f}s - {points} points")
                    if error:
                        print(f"    Error: {error}")
            else:
                print("\nNo UI test results found.")
            
            return success
            
        finally:
            # Stop Flask app
            print("\nStopping Flask app...")
            flask_process.terminate()
            try:
                flask_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                flask_process.kill()
            
    except Exception as e:
        print(f"Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ui_validation()
    if success:
        print("\n[PASS] UI validation test completed successfully")
    else:
        print("\n[FAIL] UI validation test failed")
