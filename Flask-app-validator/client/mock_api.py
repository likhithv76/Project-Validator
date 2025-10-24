

from flask import Flask, request, jsonify, send_file
import json
import os
import tempfile
import zipfile
from pathlib import Path
import uuid
from datetime import datetime
import subprocess
import time
import threading
import requests

app = Flask(__name__)

# Simple CORS headers without flask_cors dependency
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Mock data storage
mock_projects = {}
mock_student_progress = {}
mock_verification_results = {}

# Helper functions for comprehensive verification
def check_playwright_backend():
    """Check if Playwright backend is running"""
    try:
        response = requests.get("http://127.0.0.1:8001/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_flask_app(tmp_dir):
    """Start Flask app for testing"""
    try:
        # Find app.py in the extracted project
        app_py = os.path.join(tmp_dir, "app.py")
        if not os.path.exists(app_py):
            # Look for other Python files
            for file in os.listdir(tmp_dir):
                if file.endswith('.py') and file != '__init__.py':
                    app_py = os.path.join(tmp_dir, file)
                    break
        
        if os.path.exists(app_py):
            # Start Flask app
            process = subprocess.Popen([
                'python', app_py
            ], cwd=tmp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return process
    except Exception as e:
        print(f"Failed to start Flask app: {e}")
    return None

def analyze_task_comprehensively(task, tmp_dir):
    """Analyze a task comprehensively with testing and screenshots"""
    task_analysis = {
        "task_id": task.get("id"),
        "task_name": task.get("name"),
        "test_status": "PASS",  # Mock status
        "screenshot_captured": True,
        "validation_results": {
            "structure_check": "PASS",
            "content_check": "PASS",
            "playwright_test": "PASS"
        },
        "errors": [],
        "screenshot_path": f"screenshots/task_{task.get('id')}.png"
    }
    
    # Mock comprehensive analysis
    time.sleep(0.5)  # Simulate processing time
    
    return task_analysis

def run_comprehensive_task_verification(project_data, tmp_dir):
    """Run comprehensive task verification"""
    try:
        flask_process = start_flask_app(tmp_dir)
        time.sleep(2)
        
        verification_results = {
            "project_name": project_data.get("project", "Unknown Project"),
            "project_description": project_data.get("description", ""),
            "verification_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_tasks": len(project_data.get("tasks", [])),
            "tasks": [],
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "screenshots_captured": 0,
                "errors": []
            }
        }
        
        # Process each task comprehensively
        for task in project_data.get("tasks", []):
            task_analysis = analyze_task_comprehensively(task, tmp_dir)
            verification_results["tasks"].append(task_analysis)
            
            # Update summary
            verification_results["summary"]["total_tests"] += 1
            if task_analysis["test_status"] == "PASS":
                verification_results["summary"]["passed_tests"] += 1
            elif task_analysis["test_status"] == "FAIL":
                verification_results["summary"]["failed_tests"] += 1
            
            if task_analysis["screenshot_captured"]:
                verification_results["summary"]["screenshots_captured"] += 1
        
        # Stop Flask app
        if flask_process:
            flask_process.terminate()
        
        return verification_results
        
    except Exception as e:
        error_msg = f"Comprehensive verification failed: {str(e)}"
        return {
            "project_name": project_data.get("project", "Unknown Project"),
            "verification_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": error_msg,
            "tasks": [],
            "summary": {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "screenshots_captured": 0, "errors": [error_msg]}
        }

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get list of available projects"""
    projects = [
        {
            'id': 'simple_flask_web_app',
            'name': 'Simple Flask Web App',
            'description': 'A basic Flask application with home, about, and contact pages',
            'created': '2024-01-15',
            'tasks_count': 4
        },
        {
            'id': 'flask_crud_app',
            'name': 'Flask CRUD Application',
            'description': 'A Flask application with Create, Read, Update, Delete operations',
            'created': '2024-01-20',
            'tasks_count': 6
        }
    ]
    return jsonify(projects)

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project_data(project_id):
    """Get detailed project data"""
    if project_id == 'simple_flask_web_app':
        return jsonify({
            'project': 'Simple Flask Web App',
            'description': 'A basic Flask application with home, about, and contact pages',
            'tasks': [
                {
                    'id': 1,
                    'name': 'Project Setup',
                    'description': 'Set up your Flask project with the basic file structure including app.py, templates folder, and static folder',
                    'required_files': ['app.py', 'templates/', 'static/', 'requirements.txt'],
                    'validation_rules': {
                        'type': 'structure',
                        'points': 10,
                        'checks': ['app.py exists', 'templates folder exists', 'static folder exists']
                    },
                    'playwright_test': {
                        'route': '/',
                        'actions': [],
                        'validate': [{'type': 'status_code', 'value': 200}],
                        'points': 5
                    },
                    'unlock_condition': {'min_score': 0, 'required_tasks': []}
                },
                {
                    'id': 2,
                    'name': 'Home Page',
                    'description': 'Create a home page that displays a welcome message and navigation menu with links to About and Contact pages',
                    'required_files': ['templates/index.html', 'templates/base.html', 'app.py'],
                    'validation_rules': {
                        'type': 'html',
                        'file': 'templates/index.html',
                        'mustHaveElements': ['h1', 'nav', 'a'],
                        'mustHaveContent': ['Welcome', 'Home', 'About', 'Contact'],
                        'points': 15
                    },
                    'playwright_test': {
                        'route': '/',
                        'actions': [{'selector_type': 'class', 'selector_value': 'nav-link', 'click': True}],
                        'validate': [
                            {'type': 'text_present', 'value': 'Welcome', 'tag': 'h1'},
                            {'type': 'status_code', 'value': 200}
                        ],
                        'points': 10
                    },
                    'unlock_condition': {'min_score': 10, 'required_tasks': [1]}
                },
                {
                    'id': 3,
                    'name': 'About Page',
                    'description': 'Create an about page that displays information about your project',
                    'required_files': ['templates/about.html', 'templates/base.html', 'app.py'],
                    'validation_rules': {
                        'type': 'html',
                        'file': 'templates/about.html',
                        'mustHaveElements': ['h1', 'p'],
                        'mustHaveContent': ['About'],
                        'points': 10
                    },
                    'playwright_test': {
                        'route': '/about',
                        'actions': [],
                        'validate': [
                            {'type': 'text_present', 'value': 'About', 'tag': 'h1'},
                            {'type': 'status_code', 'value': 200}
                        ],
                        'points': 5
                    },
                    'unlock_condition': {'min_score': 25, 'required_tasks': [1, 2]}
                },
                {
                    'id': 4,
                    'name': 'Contact Page',
                    'description': 'Create a contact page with a form for user inquiries',
                    'required_files': ['templates/contact.html', 'templates/base.html', 'app.py'],
                    'validation_rules': {
                        'type': 'html',
                        'file': 'templates/contact.html',
                        'mustHaveElements': ['h1', 'form', 'input'],
                        'mustHaveContent': ['Contact', 'Name', 'Email', 'Message'],
                        'points': 15
                    },
                    'playwright_test': {
                        'route': '/contact',
                        'actions': [
                            {'selector_type': 'name', 'selector_value': 'name', 'input_variants': ['John Doe']},
                            {'selector_type': 'name', 'selector_value': 'email', 'input_variants': ['john@example.com']},
                            {'selector_type': 'name', 'selector_value': 'message', 'input_variants': ['Hello, this is a test message']},
                            {'selector_type': 'type', 'selector_value': 'submit', 'click': True}
                        ],
                        'validate': [
                            {'type': 'text_present', 'value': 'Contact', 'tag': 'h1'},
                            {'type': 'status_code', 'value': 200}
                        ],
                        'points': 10
                    },
                    'unlock_condition': {'min_score': 40, 'required_tasks': [1, 2, 3]}
                }
            ]
        })
    else:
        return jsonify({'error': 'Project not found'}), 404

@app.route('/api/student-progress/<student_id>/<project_id>', methods=['GET'])
def get_student_progress(student_id, project_id):
    """Get student progress for a specific project"""
    progress_key = f"{student_id}_{project_id}"
    
    if progress_key not in mock_student_progress:
        # Initialize with default progress
        mock_student_progress[progress_key] = {
            'student_id': student_id,
            'project_id': project_id,
            'completed_tasks': [],
            'current_task': 1,
            'total_score': 0,
            'last_updated': datetime.now().isoformat()
        }
    
    return jsonify(mock_student_progress[progress_key])

@app.route('/api/upload-project', methods=['POST'])
def upload_project():
    """Upload and analyze a project ZIP file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Create a mock project ID
    project_id = str(uuid.uuid4())
    
    # Mock file structure analysis with actual content
    mock_file_structure = {
        'app.py': '''from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)''',
        'requirements.txt': '''Flask==2.3.3
Werkzeug==2.3.7''',
        'templates': {
            'base.html': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Flask App{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">Flask App</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/">Home</a>
                <a class="nav-link" href="/about">About</a>
                <a class="nav-link" href="/contact">Contact</a>
            </div>
        </div>
    </nav>
    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>
</body>
</html>''',
            'index.html': '''{% extends "base.html" %}

{% block title %}Home - Flask App{% endblock %}

{% block content %}
<div class="jumbotron">
    <h1 class="display-4">Welcome to Flask App</h1>
    <p class="lead">This is a simple Flask application with Bootstrap styling.</p>
    <hr class="my-4">
    <p>Click the buttons below to explore different pages.</p>
    <a class="btn btn-primary btn-lg" href="/about" role="button">Learn more</a>
</div>
{% endblock %}''',
            'about.html': '''{% extends "base.html" %}

{% block title %}About - Flask App{% endblock %}

{% block content %}
<h1>About Us</h1>
<p>This is a demo Flask application showcasing basic web development concepts.</p>
<p>Features include:</p>
<ul>
    <li>Flask routing</li>
    <li>Template inheritance</li>
    <li>Bootstrap styling</li>
    <li>Responsive design</li>
</ul>
{% endblock %}''',
            'contact.html': '''{% extends "base.html" %}

{% block title %}Contact - Flask App{% endblock %}

{% block content %}
<h1>Contact Us</h1>
<form>
    <div class="mb-3">
        <label for="name" class="form-label">Name</label>
        <input type="text" class="form-control" id="name" name="name">
    </div>
    <div class="mb-3">
        <label for="email" class="form-label">Email</label>
        <input type="email" class="form-control" id="email" name="email">
    </div>
    <div class="mb-3">
        <label for="message" class="form-label">Message</label>
        <textarea class="form-control" id="message" name="message" rows="3"></textarea>
    </div>
    <button type="submit" class="btn btn-primary">Submit</button>
</form>
{% endblock %}'''
        },
        'static': {
            'css': {
                'style.css': '''/* Custom styles for Flask app */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.jumbotron {
    background-color: #f8f9fa;
    padding: 2rem 1rem;
    border-radius: 0.375rem;
}

.navbar-brand {
    font-weight: bold;
}

.form-control:focus {
    border-color: #007bff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}'''
            },
            'js': {
                'script.js': '''// Main JavaScript file for Flask app
document.addEventListener('DOMContentLoaded', function() {
    console.log('Flask app loaded successfully');
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            alert('Form submitted! (This is a demo)');
        });
    });
});'''
            }
        }
    }
    
    mock_projects[project_id] = {
        'id': project_id,
        'name': file.filename.replace('.zip', ''),
        'file_structure': mock_file_structure,
        'uploaded_at': datetime.now().isoformat()
    }
    
    return jsonify({
        'id': project_id,
        'name': file.filename.replace('.zip', ''),
        'fileStructure': mock_file_structure,
        'uploaded_at': datetime.now().isoformat()
    })

@app.route('/api/generate-testcases', methods=['POST'])
def generate_testcases():
    """Generate testcases for a project"""
    data = request.get_json()
    project_id = data.get('projectId')
    method = data.get('method', 'AI')
    
    if project_id not in mock_projects:
        return jsonify({'error': 'Project not found'}), 404
    
    # Mock testcase generation
    mock_project_data = {
        'project': 'Simple Flask Web App',
        'description': 'A basic Flask application with home, about, and contact pages',
        'tasks': [
            {
                'id': 1,
                'name': 'Project Setup',
                'description': 'Set up your Flask project with the basic file structure',
                'required_files': ['app.py', 'templates/', 'static/', 'requirements.txt'],
                'validation_rules': {
                    'type': 'structure',
                    'points': 10,
                    'checks': ['app.py exists', 'templates folder exists']
                },
                'playwright_test': {
                    'route': '/',
                    'actions': [],
                    'validate': [{'type': 'status_code', 'value': 200}],
                    'points': 5
                },
                'unlock_condition': {'min_score': 0, 'required_tasks': []}
            }
        ]
    }
    
    return jsonify(mock_project_data)

@app.route('/api/validate-task', methods=['POST'])
def validate_task():
    """Validate a student's task submission"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    student_id = request.form.get('studentId', 'student_001')
    task_id = int(request.form.get('taskId', 1))
    
    # Mock validation result
    import random
    success = random.choice([True, True, True, False])  # 75% success rate for demo
    
    if success:
        score = random.randint(15, 25)
        max_score = 25
        
        # Update student progress
        progress_key = f"{student_id}_simple_flask_web_app"
        if progress_key not in mock_student_progress:
            mock_student_progress[progress_key] = {
                'student_id': student_id,
                'project_id': 'simple_flask_web_app',
                'completed_tasks': [],
                'current_task': 1,
                'total_score': 0,
                'last_updated': datetime.now().isoformat()
            }
        
        if task_id not in mock_student_progress[progress_key]['completed_tasks']:
            mock_student_progress[progress_key]['completed_tasks'].append(task_id)
            mock_student_progress[progress_key]['total_score'] += score
            mock_student_progress[progress_key]['current_task'] = task_id + 1
            mock_student_progress[progress_key]['last_updated'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'total_score': score,
            'max_score': max_score,
            'message': 'Validation completed successfully',
            'static_validation': {'success': True, 'score': score // 2},
            'playwright_validation': {'success': True, 'score': score // 2}
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Validation failed: Some requirements not met',
            'error': 'Missing required files or incorrect implementation'
        })

@app.route('/api/save-project', methods=['POST'])
def save_project():
    """Save project configuration"""
    data = request.get_json()
    
    # Mock save operation
    project_name = data.get('project', 'Untitled Project')
    tasks_count = len(data.get('tasks', []))
    
    return jsonify({
        'success': True,
        'message': f'Project "{project_name}" saved successfully with {tasks_count} tasks',
        'project_id': str(uuid.uuid4())
    })

@app.route('/api/comprehensive-verification', methods=['POST'])
def comprehensive_verification():
    """Run comprehensive task verification with Flask app testing and screenshots"""
    data = request.get_json()
    project_id = data.get('projectId')
    
    if not project_id:
        return jsonify({'error': 'Project ID required'}), 400
    
    # Get project data
    project_data = mock_projects.get(project_id)
    if not project_data:
        return jsonify({'error': 'Project not found'}), 404
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Extract project files (mock extraction)
        project_structure = project_data.get('file_structure', {})
        
        # Create mock files for testing
        create_mock_project_files(tmp_dir, project_structure)
        
        # Run comprehensive verification
        verification_results = run_comprehensive_task_verification(project_data, tmp_dir)
        
        # Store results
        verification_id = str(uuid.uuid4())
        mock_verification_results[verification_id] = verification_results
        
        return jsonify({
            'verification_id': verification_id,
            'results': verification_results,
            'playwright_available': check_playwright_backend()
        })

def create_mock_project_files(tmp_dir, file_structure):
    """Create mock project files for testing"""
    def create_files_recursive(structure, base_path):
        for name, content in structure.items():
            file_path = os.path.join(base_path, name)
            if isinstance(content, dict):
                # Directory
                os.makedirs(file_path, exist_ok=True)
                create_files_recursive(content, file_path)
            else:
                # File
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    create_files_recursive(file_structure, tmp_dir)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    print("Starting Flask Project Validator Mock API Server...")
    print("Frontend URL: http://localhost:3000")
    print("API URL: http://localhost:5000")
    print("Health Check: http://localhost:5000/api/health")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
