"""
Configuration settings for Playwright backend
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
TESTS_DIR = BASE_DIR / "tests"
RESULTS_DIR = BASE_DIR / "results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"
LOGS_DIR = RESULTS_DIR / "logs"

# Server settings
HOST = "127.0.0.1"
PORT = 8001

# Test settings
DEFAULT_TIMEOUT = 30
DEFAULT_HEADLESS = True
DEFAULT_CAPTURE_SCREENSHOTS = True

# Browser settings
BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor"
]

# Viewport settings
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}

# User agent
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Test suites
AVAILABLE_TEST_SUITES = [
    "default",
    "auth",
    "crud", 
    "security",
    "database",
    "navigation"
]

# Create directories if they don't exist
for directory in [RESULTS_DIR, SCREENSHOTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
