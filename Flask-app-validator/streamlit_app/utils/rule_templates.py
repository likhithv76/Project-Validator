"""
Rule templates and helper functions for dynamic rule generation.
Provides default structures for different types of validation rules.
"""

import json
from typing import Dict, List, Any, Optional

RULE_TEMPLATES = {
    "html": {
        "type": "html",
        "file": "",
        "mustHaveElements": [],
        "mustHaveClasses": [],
        "mustHaveContent": [],
        "mustHaveInputs": [],
        "points": 10
    },
    
    "boilerplate": {
        "type": "boilerplate",
        "file": "",
        "expected_structure": {},
        "required_classes": [],
        "required_functions": [],
        "points": 30
    },
    
    "requirements": {
        "type": "requirements",
        "file": "requirements.txt",
        "mustHavePackages": [],
        "points": 5
    },
    
    "database": {
        "type": "database",
        "file": "",
        "mustExist": True,
        "points": 10
    },
    
    "security": {
        "type": "security",
        "file": "",
        "mustHaveSecurity": [],
        "points": 15
    },
    
    "runtime": {
        "type": "runtime",
        "file": "",
        "mustHaveRoutes": [],
        "points": 20
    }
}

# Security features that can be checked
SECURITY_FEATURES = [
    "password hashing",
    "session management", 
    "user validation",
    "secret key",
    "csrf protection",
    "input validation",
    "error handling"
]

# Common HTML elements for validation
HTML_ELEMENTS = [
    "div", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "form", "input", "button", "a", "img", "nav", "main", "header", "footer",
    "section", "article", "aside", "ul", "ol", "li", "table", "tr", "td", "th"
]

# Common CSS classes for validation
CSS_CLASSES = [
    "container", "row", "col", "btn", "form-group", "form-control",
    "navbar", "nav", "card", "alert", "modal", "dropdown", "menu",
    "content", "sidebar", "header", "footer", "main", "section"
]

# Common Python imports for Flask apps
PYTHON_IMPORTS = [
    "from flask import Flask",
    "from flask import render_template",
    "from flask import request",
    "from flask import redirect",
    "from flask import url_for",
    "from flask import flash",
    "from flask import session",
    "from flask_sqlalchemy import SQLAlchemy",
    "from werkzeug.security import generate_password_hash",
    "from werkzeug.security import check_password_hash"
]

# Common Flask routes
FLASK_ROUTES = [
    "/", "/home", "/index", "/about", "/contact",
    "/login", "/register", "/logout", "/profile", "/dashboard",
    "/admin", "/api", "/api/users", "/api/posts"
]

def get_rule_template(rule_type: str) -> Dict[str, Any]:
    """
    Get a copy of the rule template for the specified type.
    
    Args:
        rule_type: Type of rule (html, boilerplate, requirements, etc.)
        
    Returns:
        Dictionary with default rule structure
    """
    if rule_type not in RULE_TEMPLATES:
        raise ValueError(f"Unknown rule type: {rule_type}")
    
    import copy
    return copy.deepcopy(RULE_TEMPLATES[rule_type])

def create_html_rule(
    file_path: str,
    elements: List[str] = None,
    classes: List[str] = None,
    content: List[str] = None,
    inputs: List[str] = None,
    points: int = 10
) -> Dict[str, Any]:
    """
    Create an HTML validation rule.
    
    Args:
        file_path: Path to the HTML file
        elements: List of required HTML elements
        classes: List of required CSS classes
        content: List of required content strings
        inputs: List of required input field names
        points: Points for this rule
        
    Returns:
        HTML rule dictionary
    """
    rule = get_rule_template("html")
    rule.update({
        "file": file_path,
        "mustHaveElements": elements or [],
        "mustHaveClasses": classes or [],
        "mustHaveContent": content or [],
        "mustHaveInputs": inputs or [],
        "points": points
    })
    return rule

def create_boilerplate_rule(
    file_path: str,
    expected_structure: Dict[str, Any] = None,
    required_classes: List[str] = None,
    required_functions: List[str] = None,
    points: int = 30
) -> Dict[str, Any]:
    """
    Create a boilerplate validation rule.
    
    Args:
        file_path: Path to the file
        expected_structure: Expected HTML structure
        required_classes: List of required CSS classes
        required_functions: List of required JavaScript functions
        points: Points for this rule
        
    Returns:
        Boilerplate rule dictionary
    """
    rule = get_rule_template("boilerplate")
    rule.update({
        "file": file_path,
        "expected_structure": expected_structure or {},
        "required_classes": required_classes or [],
        "required_functions": required_functions or [],
        "points": points
    })
    return rule

def create_requirements_rule(
    file_path: str = "requirements.txt",
    packages: List[str] = None,
    points: int = 5
) -> Dict[str, Any]:
    """
    Create a requirements validation rule.
    
    Args:
        file_path: Path to requirements file
        packages: List of required packages
        points: Points for this rule
        
    Returns:
        Requirements rule dictionary
    """
    rule = get_rule_template("requirements")
    rule.update({
        "file": file_path,
        "mustHavePackages": packages or [],
        "points": points
    })
    return rule

def create_database_rule(
    file_path: str,
    must_exist: bool = True,
    points: int = 10
) -> Dict[str, Any]:
    """
    Create a database validation rule.
    
    Args:
        file_path: Path to database file
        must_exist: Whether file must exist
        points: Points for this rule
        
    Returns:
        Database rule dictionary
    """
    rule = get_rule_template("database")
    rule.update({
        "file": file_path,
        "mustExist": must_exist,
        "points": points
    })
    return rule

def create_security_rule(
    file_path: str,
    security_features: List[str] = None,
    points: int = 15
) -> Dict[str, Any]:
    """
    Create a security validation rule.
    
    Args:
        file_path: Path to the file
        security_features: List of required security features
        points: Points for this rule
        
    Returns:
        Security rule dictionary
    """
    rule = get_rule_template("security")
    rule.update({
        "file": file_path,
        "mustHaveSecurity": security_features or [],
        "points": points
    })
    return rule

def create_runtime_rule(
    file_path: str,
    routes: List[str] = None,
    points: int = 20
) -> Dict[str, Any]:
    """
    Create a runtime validation rule.
    
    Args:
        file_path: Path to the file
        routes: List of required routes
        points: Points for this rule
        
    Returns:
        Runtime rule dictionary
    """
    rule = get_rule_template("runtime")
    rule.update({
        "file": file_path,
        "mustHaveRoutes": routes or [],
        "points": points
    })
    return rule

def validate_rule(rule: Dict[str, Any]) -> List[str]:
    """
    Validate a rule dictionary for completeness and correctness.
    
    Args:
        rule: Rule dictionary to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check required fields
    if "type" not in rule:
        errors.append("Rule must have a 'type' field")
    if "file" not in rule:
        errors.append("Rule must have a 'file' field")
    if "points" not in rule:
        errors.append("Rule must have a 'points' field")
    
    # Check type-specific fields
    rule_type = rule.get("type")
    
    if rule_type == "html":
        required_fields = ["mustHaveElements", "mustHaveClasses", "mustHaveContent", "mustHaveInputs"]
        for field in required_fields:
            if field not in rule:
                errors.append(f"HTML rule must have '{field}' field")
    
    elif rule_type == "boilerplate":
        required_fields = ["expected_structure", "required_classes", "required_functions"]
        for field in required_fields:
            if field not in rule:
                errors.append(f"Boilerplate rule must have '{field}' field")
    
    elif rule_type == "requirements":
        if "mustHavePackages" not in rule:
            errors.append("Requirements rule must have 'mustHavePackages' field")
    
    elif rule_type == "database":
        if "mustExist" not in rule:
            errors.append("Database rule must have 'mustExist' field")
    
    elif rule_type == "security":
        if "mustHaveSecurity" not in rule:
            errors.append("Security rule must have 'mustHaveSecurity' field")
    
    elif rule_type == "runtime":
        if "mustHaveRoutes" not in rule:
            errors.append("Runtime rule must have 'mustHaveRoutes' field")
    
    return errors

def save_rules_to_file(rules: List[Dict[str, Any]], file_path: str) -> bool:
    """
    Save a list of rules to a JSON file.
    
    Args:
        rules: List of rule dictionaries
        file_path: Path to save the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"rules": rules}, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving rules to {file_path}: {e}")
        return False

def load_rules_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load rules from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of rule dictionaries
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("rules", [])
    except Exception as e:
        print(f"Error loading rules from {file_path}: {e}")
        return []

def get_available_rule_types() -> List[str]:
    """Get list of available rule types."""
    return list(RULE_TEMPLATES.keys())

def get_security_features() -> List[str]:
    """Get list of available security features."""
    return SECURITY_FEATURES.copy()

def get_html_elements() -> List[str]:
    """Get list of common HTML elements."""
    return HTML_ELEMENTS.copy()

def get_css_classes() -> List[str]:
    """Get list of common CSS classes."""
    return CSS_CLASSES.copy()

def get_python_imports() -> List[str]:
    """Get list of common Python imports."""
    return PYTHON_IMPORTS.copy()

def get_flask_routes() -> List[str]:
    """Get list of common Flask routes."""
    return FLASK_ROUTES.copy()
