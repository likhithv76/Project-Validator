"""
Startup script for Playwright backend server.
This script ensures all dependencies are available and starts the server.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        "fastapi",
        "uvicorn", 
        "playwright",
        "requests"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"Installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}: {e}")
                return False
    
    return True

def install_playwright_browsers():
    """Install Playwright browsers if not already installed."""
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("Playwright browsers installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Playwright browsers: {e}")
        return False

def main():
    """Main startup function."""
    print("Starting Playwright Backend Server...")
    
    # Check dependencies
    if not check_dependencies():
        print("Failed to install dependencies")
        sys.exit(1)
    
    # Install Playwright browsers
    if not install_playwright_browsers():
        print("Failed to install Playwright browsers")
        sys.exit(1)
    
    # Start the server
    try:
        from server import app
        import uvicorn
        
        print("Starting server on http://127.0.0.1:8001")
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
