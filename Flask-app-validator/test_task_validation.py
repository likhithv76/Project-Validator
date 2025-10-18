#!/usr/bin/env python3
"""
Test script for task-based validation system.
This script tests the integration between TaskValidator and the existing validation system.
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


def create_test_project():
    """Create a simple test Flask project for validation."""
    temp_dir = tempfile.mkdtemp()
    
    # Create app.py
    app_content = '''
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password too short')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return render_template('register.html')
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful!')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
'''
    
    with open(os.path.join(temp_dir, 'app.py'), 'w') as f:
        f.write(app_content)
    
    # Create templates directory
    templates_dir = os.path.join(temp_dir, 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Create base.html
    base_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Flask Auth{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">Flask Auth</a>
        </div>
    </nav>
    
    <div class="container mt-4">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-info">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''
    
    with open(os.path.join(templates_dir, 'base.html'), 'w') as f:
        f.write(base_html)
    
    # Create index.html
    index_html = '''
{% extends "base.html" %}

{% block title %}Home - Flask Auth{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8">
        <h1>Welcome to Flask Auth</h1>
        <p class="lead">A simple authentication system built with Flask.</p>
        <a href="{{ url_for('login') }}" class="btn btn-primary">Login</a>
        <a href="{{ url_for('register') }}" class="btn btn-outline-primary">Register</a>
    </div>
</div>
{% endblock %}
'''
    
    with open(os.path.join(templates_dir, 'index.html'), 'w') as f:
        f.write(index_html)
    
    # Create login.html
    login_html = '''
{% extends "base.html" %}

{% block title %}Login - Flask Auth{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h4>Login</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control login_username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control login_password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary login_submit">Login</button>
                </form>
                <p class="mt-3">Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''
    
    with open(os.path.join(templates_dir, 'login.html'), 'w') as f:
        f.write(login_html)
    
    # Create register.html
    register_html = '''
{% extends "base.html" %}

{% block title %}Register - Flask Auth{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h4>Create Account</h4>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control register_form_username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control register_form_email" name="email" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control register_form_password" name="password" required>
                    </div>
                    <div class="mb-3">
                        <label for="confirm_password" class="form-label">Confirm Password</label>
                        <input type="password" class="form-control register_form_confirm_password" name="confirm_password" required>
                    </div>
                    <button type="submit" class="btn btn-primary register_form_submit_button">Register</button>
                </form>
                <p class="mt-3">Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''
    
    with open(os.path.join(templates_dir, 'register.html'), 'w') as f:
        f.write(register_html)
    
    # Create dashboard.html
    dashboard_html = '''
{% extends "base.html" %}

{% block title %}Dashboard - Flask Auth{% endblock %}

{% block content %}
<div class="dashboard-container">
    <div class="row">
        <div class="col-md-8">
            <h2>Dashboard</h2>
            <p>Welcome back, {{ user.username }}!</p>
            <div class="card">
                <div class="card-header">
                    <h5>User Profile</h5>
                </div>
                <div class="card-body user_profile">
                    <p><strong>Username:</strong> {{ user.username }}</p>
                    <p><strong>Email:</strong> {{ user.email }}</p>
                    <button class="btn btn-danger logout_button">Logout</button>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''
    
    with open(os.path.join(templates_dir, 'dashboard.html'), 'w') as f:
        f.write(dashboard_html)
    
    # Create requirements.txt
    requirements_content = '''
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Werkzeug==2.3.7
'''
    
    with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
        f.write(requirements_content)
    
    # Create instance directory
    instance_dir = os.path.join(temp_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    
    # Create empty database file
    with open(os.path.join(instance_dir, 'users.db'), 'w') as f:
        f.write('')  # Empty file, will be created by Flask
    
    return temp_dir


def test_task_validation():
    """Test the task validation system."""
    print("Testing Task-Based Validation System")
    print("=" * 50)
    
    # Initialize task validator
    task_validator = TaskValidator()
    
    # Get available tasks
    tasks = task_validator.get_all_tasks()
    print(f"Found {len(tasks)} tasks:")
    for task in tasks:
        print(f"  - Task {task['id']}: {task['name']}")
    
    if not tasks:
        print("ERROR: No tasks found. Please check tasks.json configuration.")
        return
    
    # Create test project
    print("\nCreating test Flask project...")
    test_project_dir = create_test_project()
    
    # Create ZIP file
    zip_path = os.path.join(tempfile.gettempdir(), "test_flask_project.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(test_project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, test_project_dir)
                zipf.write(file_path, arcname)
    
    print(f"SUCCESS: Test project created: {zip_path}")
    
    # Test each task
    student_id = "test_student_001"
    print(f"\nTesting as student: {student_id}")
    
    for task in tasks:
        task_id = task['id']
        task_name = task['name']
        
        print(f"\nTesting Task {task_id}: {task_name}")
        print("-" * 30)
        
        try:
            # Run validation
            result = task_validator.validate_task(task_id, zip_path, student_id)
            
            if result['success']:
                print(f"PASS: Task {task_id} PASSED")
                print(f"   Total Score: {result['total_score']}/{result['max_score']}")
                print(f"   Static Score: {result['static_validation']['score']}/{result['static_validation']['max_score']}")
                print(f"   Playwright Score: {result['playwright_validation']['score']}/{result['playwright_validation']['max_score']}")
                
                # Update progress
                task_validator.update_student_progress(student_id, result)
                
            else:
                print(f"FAIL: Task {task_id} FAILED")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"ERROR: Task {task_id} ERROR: {str(e)}")
    
    # Show final progress
    print(f"\nFinal Progress for {student_id}:")
    progress = task_validator.get_student_progress(student_id)
    print(f"   Completed Tasks: {progress['completed_tasks']}")
    print(f"   Current Task: {progress['current_task']}")
    print(f"   Total Score: {progress['total_score']}")
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree(test_project_dir)
        os.unlink(zip_path)
        print("\nCleanup completed")
    except Exception as e:
        print(f"Cleanup warning: {e}")
    
    print("\nTest completed!")


if __name__ == "__main__":
    test_task_validation()
