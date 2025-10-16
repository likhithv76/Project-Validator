"""
FastAPI server for Playwright UI testing backend.
Provides endpoints to run headless UI tests on Flask applications.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from runner import PlaywrightTestRunner

app = FastAPI(
    title="Playwright UI Test Backend",
    description="Headless UI testing service for Flask applications",
    version="1.0.0"
)

# Global test runner instance
test_runner = None

class TestRequest(BaseModel):
    base_url: str = "http://127.0.0.1:5000"
    test_suite: str = "default"
    project_name: str = "student_project"
    timeout: int = 30
    headless: bool = True
    capture_screenshots: bool = True

class TestResult(BaseModel):
    name: str
    status: str  # PASS, FAIL, SKIP
    duration: float
    error: Optional[str] = None
    screenshot: Optional[str] = None

class TestResponse(BaseModel):
    status: str  # completed, failed, timeout
    results: List[TestResult]
    screenshots: List[str]
    logs: List[str]
    total_tests: int
    passed_tests: int
    failed_tests: int
    execution_time: float

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "playwright_available": test_runner is not None
    }

@app.post("/run-ui-tests", response_model=TestResponse)
async def run_ui_tests(request: TestRequest):
    """
    Run Playwright UI tests on the specified Flask application.
    
    Args:
        request: Test configuration including base URL and test suite
        
    Returns:
        TestResponse with detailed results
    """
    global test_runner
    
    start_time = time.time()
    
    try:
        # Initialize test runner if not already done
        if test_runner is None:
            test_runner = PlaywrightTestRunner()
            await test_runner.initialize()
        
        # Run the tests
        results = await test_runner.run_tests(
            base_url=request.base_url,
            test_suite=request.test_suite,
            project_name=request.project_name,
            timeout=request.timeout,
            headless=request.headless,
            capture_screenshots=request.capture_screenshots
        )
        
        execution_time = time.time() - start_time
        
        # Calculate statistics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["status"] == "PASS")
        failed_tests = sum(1 for r in results if r["status"] == "FAIL")
        
        # Extract screenshots and logs
        screenshots = [r.get("screenshot", "") for r in results if r.get("screenshot")]
        logs = test_runner.get_logs()
        
        return TestResponse(
            status="completed",
            results=[TestResult(**r) for r in results],
            screenshots=screenshots,
            logs=logs,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        return TestResponse(
            status="failed",
            results=[],
            screenshots=[],
            logs=[f"Error: {str(e)}"],
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            execution_time=execution_time
        )

@app.get("/test-suites")
async def list_test_suites():
    """List available test suites."""
    tests_dir = Path(__file__).parent / "tests"
    if not tests_dir.exists():
        return {"test_suites": []}
    
    test_files = list(tests_dir.glob("test_*.py"))
    suites = [f.stem for f in test_files]
    
    return {"test_suites": suites}

@app.get("/results/{project_name}")
async def get_test_results(project_name: str):
    """Get test results for a specific project."""
    results_dir = Path(__file__).parent / "results" / project_name
    if not results_dir.exists():
        raise HTTPException(status_code=404, detail="No results found for this project")
    
    # Find the most recent result
    result_files = list(results_dir.glob("*.json"))
    if not result_files:
        raise HTTPException(status_code=404, detail="No result files found")
    
    latest_result = max(result_files, key=lambda f: f.stat().st_mtime)
    
    try:
        with open(latest_result, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading results: {str(e)}")

@app.delete("/results/{project_name}")
async def clear_test_results(project_name: str):
    """Clear test results for a specific project."""
    results_dir = Path(__file__).parent / "results" / project_name
    if results_dir.exists():
        import shutil
        shutil.rmtree(results_dir)
        return {"message": f"Results cleared for project: {project_name}"}
    else:
        raise HTTPException(status_code=404, detail="No results found for this project")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
