#!/usr/bin/env python3
"""
Debug script for Task 2 validation issue.
"""

import os
import sys
import tempfile
import zipfile
from pathlib import Path

# Add validator directory to path
project_root = Path(__file__).resolve().parent
validator_dir = project_root / "validator"
sys.path.insert(0, str(validator_dir))

from task_validator import TaskValidator


def debug_task2():
    """Debug Task 2 validation specifically."""
    print("Debugging Task 2 validation...")
    
    # Initialize task validator
    task_validator = TaskValidator()
    
    # Get Task 2
    task2 = task_validator.get_task(2)
    if not task2:
        print("ERROR: Task 2 not found")
        return
    
    print(f"Task 2: {task2['name']}")
    print(f"Description: {task2['description']}")
    print(f"Required files: {task2.get('required_files', [])}")
    print(f"Validation rules: {task2.get('validation_rules', {})}")
    
    # Use the existing test Flask project
    test_project_path = "test_flask_project"
    if not os.path.exists(test_project_path):
        print("ERROR: test_flask_project directory not found")
        return
    
    # Create ZIP file from test project
    zip_path = os.path.join(tempfile.gettempdir(), "debug_task2.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(test_project_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, test_project_path)
                zipf.write(file_path, arcname)
    
    print(f"Created test ZIP: {zip_path}")
    
    # Test Task 2 validation
    student_id = "debug_student"
    print(f"\nTesting Task 2 validation for student: {student_id}")
    
    try:
        result = task_validator.validate_task(2, zip_path, student_id)
        
        print(f"\nResult:")
        print(f"Success: {result.get('success', False)}")
        print(f"Error: {result.get('error', 'None')}")
        print(f"Task passed: {result.get('task_passed', False)}")
        print(f"Total score: {result.get('total_score', 0)}/{result.get('max_score', 0)}")
        
        if 'traceback' in result:
            print(f"\nTraceback:")
            print(result['traceback'])
        
        # Show static validation details
        static_results = result.get('static_validation', {})
        print(f"\nStatic validation:")
        print(f"  Success: {static_results.get('success', False)}")
        print(f"  Score: {static_results.get('score', 0)}/{static_results.get('max_score', 0)}")
        print(f"  Errors: {static_results.get('errors', [])}")
        print(f"  Warnings: {static_results.get('warnings', [])}")
        
        # Show Playwright validation details
        playwright_results = result.get('playwright_validation', {})
        print(f"\nPlaywright validation:")
        print(f"  Success: {playwright_results.get('success', False)}")
        print(f"  Score: {playwright_results.get('score', 0)}/{playwright_results.get('max_score', 0)}")
        print(f"  Error: {playwright_results.get('error', 'None')}")
        
    except Exception as e:
        print(f"ERROR during validation: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    # Cleanup
    try:
        os.unlink(zip_path)
        print(f"\nCleaned up: {zip_path}")
    except Exception as e:
        print(f"Cleanup warning: {e}")


if __name__ == "__main__":
    debug_task2()


