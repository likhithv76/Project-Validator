import streamlit as st
import subprocess
import tempfile, zipfile, os, json
from pathlib import Path
import sys
import requests
from requests.exceptions import Timeout as RequestTimeout, RequestException
import asyncio
import threading
import time
sys.path.append(str(Path(__file__).parent.parent))
from gemini_generator import GeminiTestCaseGenerator

# Helper functions for project management
def load_existing_projects():
    """Load all existing projects from the projects directory."""
    projects = []
    projects_dir = Path("projects")
    
    if not projects_dir.exists():
        return projects
    
    # Look for configuration JSON files
    for config_file in projects_dir.glob("*_configuration.json"):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                project_data = json.load(f)
                project_data["config_file"] = str(config_file)
                project_data["name"] = project_data.get("project", config_file.stem.replace("_configuration", ""))
                projects.append(project_data)
        except Exception as e:
            st.error(f"Error loading project {config_file}: {e}")
    
    return projects

def display_project_details(project, project_idx):
    """Display detailed project information with CRUD operations."""
    st.markdown("---")
    st.markdown(f"#### 📋 {project['name']}")
    
    # Project metadata
    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        st.metric("Total Tasks", len(project.get('tasks', [])))
    with col_meta2:
        total_points = sum(
            task.get('validation_rules', {}).get('points', 0) + 
            task.get('playwright_test', {}).get('points', 0)
            for task in project.get('tasks', [])
        )
        st.metric("Total Points", total_points)
    # with col_meta3:
    #     st.metric("Config File", project.get('config_file', 'Unknown').split('/')[-1])
    
    # Project description
    if project.get('description'):
        st.markdown(f"**Description:** {project['description']}")
    
    # Creator prompt if available
    if project.get('creator_prompt'):
        with st.expander("Creator's Original Prompt", expanded=False):
            st.text(project['creator_prompt'])
    
    # CRUD Operations
    st.markdown("#### Project Operations")
    col_edit, col_delete, col_export = st.columns(3)
    
    with col_edit:
        if st.button("Edit Project", key=f"edit_project_{project_idx}"):
            st.session_state.editing_project = project
            st.session_state.editing_project_idx = project_idx
            st.rerun()
    
    with col_delete:
        if st.button("Delete Project", key=f"delete_project_{project_idx}", type="secondary"):
            st.session_state.confirm_delete_project = project_idx
    
    with col_export:
        if st.button("Export Project", key=f"export_project_{project_idx}"):
            export_project(project)
    
    # Handle delete confirmation
    if hasattr(st.session_state, 'confirm_delete_project') and st.session_state.confirm_delete_project == project_idx:
        st.warning("Are you sure you want to delete this project?")
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("Yes, Delete", key=f"confirm_delete_{project_idx}", type="primary"):
                delete_project(project_idx)
                st.success("Project deleted successfully!")
                st.rerun()
        with col_cancel:
            if st.button("Cancel", key=f"cancel_delete_{project_idx}"):
                del st.session_state.confirm_delete_project
                st.rerun()
    
    # Task management
    st.markdown("#### Task Management")
    tasks = project.get('tasks', [])
    
    if tasks:
        for i, task in enumerate(tasks):
            with st.expander(f"Task {task['id']}: {task['name']}", expanded=False):
                col_task_info, col_task_actions = st.columns([3, 1])
                
                with col_task_info:
                    st.write(f"**Description:** {task.get('description', 'No description')}")
                    st.write(f"**Required Files:** {', '.join(task.get('required_files', []))}")
                    
                    # Validation rules
                    validation_rules = task.get('validation_rules', {})
                    if validation_rules:
                        st.write(f"**Validation:** {validation_rules.get('type', 'Unknown')} ({validation_rules.get('points', 0)} pts)")
                    
                    # UI test
                    playwright_test = task.get('playwright_test', {})
                    if playwright_test:
                        st.write(f"**UI Test:** {playwright_test.get('route', 'No route')} ({playwright_test.get('points', 0)} pts)")
                    
                    # Unlock condition
                    unlock_condition = task.get('unlock_condition', {})
                    if unlock_condition:
                        min_score = unlock_condition.get('min_score', 0)
                        required_tasks = unlock_condition.get('required_tasks', [])
                        st.write(f"**Unlock:** Min score {min_score}, Required tasks: {required_tasks}")
                
                with col_task_actions:
                    if st.button("Edit", key=f"pm_edit_task_{i}", help="Edit task"):
                        st.session_state.editing_task = task
                        st.session_state.editing_task_idx = i
                        st.session_state.editing_task_project_idx = project_idx
                    
                    if st.button("Delete", key=f"pm_delete_task_{i}", help="Delete task"):
                        st.session_state.confirm_delete_task = (project_idx, i)
        
        # Handle task delete confirmation
        if hasattr(st.session_state, 'confirm_delete_task'):
            project_idx_del, task_idx_del = st.session_state.confirm_delete_task
            st.warning(f"Delete task {tasks[task_idx_del]['id']}: {tasks[task_idx_del]['name']}?")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("Yes, Delete Task", key=f"pm_confirm_delete_task_{task_idx_del}", type="primary"):
                    delete_task(project_idx_del, task_idx_del)
                    st.success("Task deleted successfully!")
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"pm_cancel_delete_task_{task_idx_del}"):
                    del st.session_state.confirm_delete_task
                    st.rerun()
    else:
        st.info("No tasks found in this project.")

def export_project(project):
    """Export project configuration as downloadable JSON."""
    json_str = json.dumps(project, indent=2)
    st.download_button(
        label="Download Project Configuration",
        data=json_str,
        file_name=f"{project['name'].replace(' ', '_')}_configuration.json",
        mime="application/json",
        key=f"export_project_{project['name'].replace(' ', '_')}"
    )

def delete_project(project_idx):
    """Delete a project and its associated files."""
    try:
        projects = load_existing_projects()
        if project_idx < len(projects):
            project = projects[project_idx]
            config_file = Path(project['config_file'])
            
            # Delete configuration file
            if config_file.exists():
                config_file.unlink()
            
            # Try to delete associated package directory
            project_name = project['name'].replace(' ', '_').lower()
            package_dir = Path("projects") / f"{project_name}_package"
            if package_dir.exists():
                import shutil
                shutil.rmtree(package_dir)
            
            # Try to delete package ZIP
            package_zip = Path("projects") / f"{project_name}_package.zip"
            if package_zip.exists():
                package_zip.unlink()
            
            st.success(f"Project '{project['name']}' deleted successfully!")
            
    except Exception as e:
        st.error(f"Error deleting project: {e}")

def delete_task(project_idx, task_idx):
    """Delete a task from a project."""
    try:
        projects = load_existing_projects()
        if project_idx < len(projects):
            project = projects[project_idx]
            tasks = project.get('tasks', [])
            
            if task_idx < len(tasks):
                deleted_task = tasks.pop(task_idx)
                
                # Update task IDs to maintain sequence
                for i, task in enumerate(tasks):
                    task['id'] = i + 1
                
                # Save updated project
                config_file = Path(project['config_file'])
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(project, f, indent=2)
                
                st.success(f"Task '{deleted_task['name']}' deleted successfully!")
                
    except Exception as e:
        st.error(f"Error deleting task: {e}")

def display_project_editor(project, project_idx):
    """Display project editing interface."""
    st.markdown("---")
    st.markdown("#### Edit Project")
    
    # Project basic info editing
    col_name, col_desc = st.columns(2)
    with col_name:
        new_name = st.text_input("Project Name", value=project.get('project', ''), key=f"edit_name_{project_idx}")
    with col_desc:
        new_description = st.text_area("Project Description", value=project.get('description', ''), key=f"edit_desc_{project_idx}")
    
    # Update project if changed
    if new_name != project.get('project', '') or new_description != project.get('description', ''):
        project['project'] = new_name
        project['description'] = new_description
        save_project(project)
    
    # Task editing
    st.markdown("#### Edit Tasks")
    tasks = project.get('tasks', [])
    
    for i, task in enumerate(tasks):
        with st.expander(f"Edit Task {task['id']}: {task['name']}", expanded=False):
            col_task_name, col_task_desc = st.columns(2)
            
            with col_task_name:
                new_task_name = st.text_input("Task Name", value=task.get('name', ''), key=f"edit_task_name_{i}")
            with col_task_desc:
                new_task_desc = st.text_area("Task Description", value=task.get('description', ''), key=f"edit_task_desc_{i}")
            
            # Required files
            current_files = task.get('required_files', [])
            available_files = [
                "app.py", "requirements.txt", "templates/base.html", 
                "templates/index.html", "templates/about.html", 
                "templates/contact.html", "templates/login.html",
                "templates/register.html", "templates/dashboard.html",
                "static/style.css", "static/script.js", "main.py", 
                "run.py", "config.py", "models.py", "views.py"
            ]
            
            for file in current_files:
                if file not in available_files:
                    available_files.append(file)
            
            new_required_files = st.multiselect(
                "Required Files",
                options=available_files,
                default=current_files,
                key=f"edit_required_files_{i}"
            )
            
            # Validation rules
            st.markdown("**Validation Rules:**")
            validation_rules = task.get('validation_rules', {})
            
            col_val_type, col_val_points = st.columns(2)
            with col_val_type:
                val_type = st.selectbox(
                    "Validation Type",
                    ["structure", "html", "css", "js", "python", "requirements"],
                    index=["structure", "html", "css", "js", "python", "requirements"].index(validation_rules.get('type', 'structure')),
                    key=f"edit_val_type_{i}"
                )
            with col_val_points:
                val_points = st.number_input(
                    "Validation Points",
                    min_value=1,
                    max_value=100,
                    value=validation_rules.get('points', 10),
                    key=f"edit_val_points_{i}"
                )
            
            val_file = st.text_input(
                "Validation File",
                value=validation_rules.get('file', ''),
                key=f"edit_val_file_{i}"
            )
            
            # UI Test
            st.markdown("**UI Test:**")
            playwright_test = task.get('playwright_test', {})
            
            col_ui_route, col_ui_points = st.columns(2)
            with col_ui_route:
                ui_route = st.text_input(
                    "Route",
                    value=playwright_test.get('route', ''),
                    key=f"edit_ui_route_{i}"
                )
            with col_ui_points:
                ui_points = st.number_input(
                    "UI Test Points",
                    min_value=1,
                    max_value=100,
                    value=playwright_test.get('points', 10),
                    key=f"edit_ui_points_{i}"
                )
            
            # Unlock condition
            st.markdown("**Unlock Condition:**")
            unlock_condition = task.get('unlock_condition', {})
            
            col_unlock_score, col_unlock_tasks = st.columns(2)
            with col_unlock_score:
                unlock_score = st.number_input(
                    "Minimum Score",
                    min_value=0,
                    max_value=100,
                    value=unlock_condition.get('min_score', 0),
                    key=f"edit_unlock_score_{i}"
                )
            with col_unlock_tasks:
                available_task_ids = [str(t['id']) for t in tasks if t['id'] != task['id']]
                current_required_tasks = unlock_condition.get('required_tasks', [])
                required_tasks_text = ", ".join(map(str, current_required_tasks))
                unlock_tasks = st.text_input(
                    "Required Tasks (comma-separated IDs)",
                    value=required_tasks_text,
                    key=f"edit_unlock_tasks_{i}"
                )
            
            # Save task changes
            if st.button("Save Task Changes", key=f"save_task_{i}"):
                # Update task
                task['name'] = new_task_name
                task['description'] = new_task_desc
                task['required_files'] = new_required_files
                
                # Update validation rules
                task['validation_rules'] = {
                    'type': val_type,
                    'points': val_points,
                    'file': val_file
                }
                
                # Update UI test
                task['playwright_test'] = {
                    'route': ui_route,
                    'points': ui_points,
                    'actions': playwright_test.get('actions', []),
                    'validate': playwright_test.get('validate', [])
                }
                
                # Update unlock condition
                try:
                    required_tasks_list = [int(x.strip()) for x in unlock_tasks.split(",") if x.strip()]
                except ValueError:
                    required_tasks_list = current_required_tasks
                
                task['unlock_condition'] = {
                    'min_score': unlock_score,
                    'required_tasks': required_tasks_list
                }
                
                # Save project
                save_project(project)
                st.success(f"Task '{new_task_name}' updated successfully!")
                st.rerun()
    
    # Add new task
    st.markdown("#### Add New Task")
    with st.expander("Add New Task", expanded=False):
        new_task_name = st.text_input("New Task Name", key=f"new_task_name_{project_idx}")
        new_task_desc = st.text_area("New Task Description", key=f"new_task_desc_{project_idx}")
        
        col_new_val_type, col_new_val_points = st.columns(2)
        with col_new_val_type:
            new_val_type = st.selectbox("Validation Type", ["structure", "html", "css", "js", "python"], key=f"new_val_type_{project_idx}")
        with col_new_val_points:
            new_val_points = st.number_input("Validation Points", min_value=1, max_value=100, value=10, key=f"new_val_points_{project_idx}")
        
        new_val_file = st.text_input("Validation File", key=f"new_val_file_{project_idx}")
        new_ui_route = st.text_input("UI Test Route", key=f"new_ui_route_{project_idx}")
        new_ui_points = st.number_input("UI Test Points", min_value=1, max_value=100, value=10, key=f"new_ui_points_{project_idx}")
        
        if st.button("Add Task", key=f"add_task_{project_idx}"):
            if new_task_name:
                new_task_id = max([t['id'] for t in tasks], default=0) + 1
                new_task = {
                    'id': new_task_id,
                    'name': new_task_name,
                    'description': new_task_desc,
                    'required_files': [],
                    'validation_rules': {
                        'type': new_val_type,
                        'points': new_val_points,
                        'file': new_val_file
                    },
                    'playwright_test': {
                        'route': new_ui_route,
                        'points': new_ui_points,
                        'actions': [],
                        'validate': []
                    },
                    'unlock_condition': {
                        'min_score': 0,
                        'required_tasks': []
                    }
                }
                
                tasks.append(new_task)
                save_project(project)
                st.success(f"Task '{new_task_name}' added successfully!")
                st.rerun()
            else:
                st.error("Please provide a task name.")
    
    # Close editor
    if st.button("Close Editor", key=f"close_editor_{project_idx}"):
        del st.session_state.editing_project
        del st.session_state.editing_project_idx
        st.rerun()

def save_project(project):
    """Save project to its configuration file."""
    try:
        config_file = Path(project['config_file'])
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(project, f, indent=2)
    except Exception as e:
        st.error(f"Error saving project: {e}")

def save_project_from_verification(project_data):
    """Save project configuration after comprehensive verification."""
    try:
        # Create projects directory (shared with student.py)
        projects_dir = Path("projects")
        projects_dir.mkdir(exist_ok=True)
        
        # Create project name
        project_name = project_data.get("project", "project").replace(" ", "_").lower()
        
        # Save JSON configuration to projects directory (for student.py to find)
        json_filename = f"{project_name}_configuration.json"
        json_path = projects_dir / json_filename
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2)
        
        return json_path
    except Exception as e:
        raise Exception(f"Error saving project after verification: {str(e)}")

# Helper functions for Playwright preview
def check_playwright_backend():
    try:
        response = requests.get("http://127.0.0.1:8001/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def run_comprehensive_task_verification(project_data, tmp_dir):
    """
    Comprehensive task verification that combines preview testing and reference screenshot capture.
    Creates detailed logs for each project and task analysis.
    Automatically saves the project after verification.
    """
    try:
        flask_process = start_flask_app(tmp_dir)
        # Poll Flask app readiness instead of fixed sleep
        try:
            wait_for_flask_ready("http://127.0.0.1:5000", timeout_seconds=15)
        except Exception:
            pass
        
        # Create comprehensive verification results
        verification_results = {
            "project_name": project_data.get("project", "Unknown Project"),
            "project_description": project_data.get("description", ""),
            "verification_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
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
            task_analysis = analyze_task_comprehensively(task, tmp_dir, project_data.get("project", "Unknown Project"))
            verification_results["tasks"].append(task_analysis)
            
            # Update summary
            verification_results["summary"]["total_tests"] += 1
            if task_analysis["test_status"] == "PASS":
                verification_results["summary"]["passed_tests"] += 1
            elif task_analysis["test_status"] in ["FAIL", "ERROR", "TIMEOUT"]:
                verification_results["summary"]["failed_tests"] += 1
                # Add error to summary if present
                if task_analysis.get("errors"):
                    verification_results["summary"]["errors"].extend(task_analysis["errors"])
                if task_analysis.get("test_message"):
                    verification_results["summary"]["errors"].append(f"Task {task_analysis['task_id']}: {task_analysis['test_message']}")
            
            if task_analysis["screenshot_captured"]:
                verification_results["summary"]["screenshots_captured"] += 1
        
        # Stop Flask app
        if flask_process:
            flask_process.terminate()
        
        # Save comprehensive log
        save_verification_log(verification_results, tmp_dir)
        
        # Automatically save project configuration after verification
        try:
            save_project_from_verification(project_data)
        except Exception as save_error:
            st.warning(f"Project was verified but could not be saved: {str(save_error)}")
        
        return verification_results
        
    except Exception as e:
        error_msg = f"Comprehensive verification failed: {str(e)}"
        st.error(error_msg)
        return {
            "project_name": project_data.get("project", "Unknown Project"),
            "verification_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error": error_msg,
            "tasks": [],
            "summary": {"total_tests": 0, "passed_tests": 0, "failed_tests": 0, "screenshots_captured": 0, "errors": [error_msg]}
        }

def start_flask_app(tmp_dir):
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
            # Start Flask app with better output handling
            process = subprocess.Popen([
                sys.executable, app_py
            ], cwd=tmp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
               text=True, bufsize=1)
            
            # Wait a bit for process to initialize
            time.sleep(0.5)
            
            # Check if process is still running (didn't crash immediately)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                st.warning(f"Flask app exited immediately. STDOUT: {stdout[:500]} STDERR: {stderr[:500]}")
                return None
            
            return process
    except Exception as e:
        st.error(f"Failed to start Flask app: {e}")
    return None

def wait_for_flask_ready(base_url: str, timeout_seconds: int = 30, interval: float = 0.5):
    """Poll the Flask app until it responds or timeout."""
    start = time.time()
    last_error = None
    while time.time() - start < timeout_seconds:
        try:
            r = requests.get(base_url, timeout=2)
            if r.status_code < 500:
                return True
        except Exception as e:
            last_error = e
        time.sleep(interval)
    raise TimeoutError(f"Flask app did not become ready in time. Last error: {last_error}")

def analyze_task_comprehensively(task, tmp_dir, project_name="Unknown Project"):
    """
    Comprehensive analysis of a single task including testing and screenshot capture.
    Returns detailed analysis with logs.
    """
    task_id = task.get("id", "unknown")
    task_name = task.get("name", "Unnamed Task")
    
    analysis = {
        "task_id": task_id,
        "task_name": task_name,
        "task_description": task.get("description", ""),
        "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "configuration_analysis": {},
        "test_status": "SKIP",
        "test_message": "",
        "test_details": {},
        "screenshot_captured": False,
        "screenshot_path": None,
        "validation_results": [],
        "playwright_logs": [],
        "errors": []
    }
    
    try:
        # Analyze task configuration
        analysis["configuration_analysis"] = analyze_task_configuration(task)
        
        playwright_test = task.get("playwright_test", {})
        route = playwright_test.get("route", "")
        
        if not route:
            analysis["test_status"] = "SKIP"
            analysis["test_message"] = "No route configured for UI testing"
            analysis["errors"].append("Missing route configuration")
            return analysis
        
        # Run comprehensive test (both validation and screenshot capture)
        test_result = run_comprehensive_task_test(task, tmp_dir, project_name)
        
        analysis["test_status"] = test_result["status"]
        analysis["test_message"] = test_result["message"]
        analysis["test_details"] = test_result.get("details", {})
        analysis["validation_results"] = test_result.get("validation_results", [])
        analysis["playwright_logs"] = test_result.get("logs", [])
        
        if test_result.get("screenshot"):
            analysis["screenshot_captured"] = True
            analysis["screenshot_path"] = test_result["screenshot"]
        
        if test_result.get("error"):
            analysis["errors"].append(test_result["error"])
            
    except Exception as e:
        analysis["test_status"] = "ERROR"
        analysis["test_message"] = f"Analysis failed: {str(e)}"
        analysis["errors"].append(str(e))
    
    return analysis

def analyze_task_configuration(task):
    """Analyze task configuration for completeness and validity."""
    config_analysis = {
        "required_files": task.get("required_files", []),
        "validation_rules": task.get("validation_rules", {}),
        "playwright_test": task.get("playwright_test", {}),
        "unlock_condition": task.get("unlock_condition", {}),
        "completeness_score": 0,
        "issues": [],
        "recommendations": []
    }
    
    # Check required files
    required_files = config_analysis["required_files"]
    if not required_files:
        config_analysis["issues"].append("No required files specified")
    else:
        config_analysis["completeness_score"] += 20
    
    # Check validation rules
    validation_rules = config_analysis["validation_rules"]
    if not validation_rules.get("type"):
        config_analysis["issues"].append("Validation type not specified")
    else:
        config_analysis["completeness_score"] += 20
    
    if not validation_rules.get("file"):
        config_analysis["issues"].append("Validation file not specified")
    else:
        config_analysis["completeness_score"] += 20
    
    # Check playwright test
    playwright_test = config_analysis["playwright_test"]
    if not playwright_test.get("route"):
        config_analysis["issues"].append("Playwright route not configured")
    else:
        config_analysis["completeness_score"] += 20
    
    if not playwright_test.get("actions"):
        config_analysis["recommendations"].append("Consider adding UI actions for better testing")
    else:
        config_analysis["completeness_score"] += 10
    
    if not playwright_test.get("validate"):
        config_analysis["recommendations"].append("Consider adding validation rules for UI testing")
    else:
        config_analysis["completeness_score"] += 10
    
    return config_analysis

def run_comprehensive_task_test(task, tmp_dir, project_name="Unknown Project"):
    """Run comprehensive test for a single task (validation + screenshot)."""
    try:
        playwright_test = task.get("playwright_test", {})
        route = playwright_test.get("route", "")
        
        if not route:
            return {
                "status": "SKIP",
                "message": "No route configured",
                "screenshot": None
            }
        
        # Prepare comprehensive test data
        test_data = {
            "base_url": "http://127.0.0.1:5000",
            "test_suite": "custom",
            # Group results under project_name to avoid clutter
            "project_name": f"creator_{project_name.replace(' ', '_').lower()}_task_{task['id']}",
            "timeout": 120,  # Increased timeout for complex validations
            "headless": True,
            "capture_screenshots": True,
            "task_config": {
                "task_id": task["id"],
                "route": route,
                "actions": playwright_test.get("actions", []),
                "validate": playwright_test.get("validate", []),
                "comprehensive_test": True  # Flag for comprehensive testing
            }
        }
        
        # Call Playwright backend for comprehensive test
        # Route Playwright results to Logs/<project>/screenshots via env override
        env = os.environ.copy()
        logs_base = Path("Logs") / project_name.replace(" ", "_").lower()
        (logs_base / "screenshots").mkdir(parents=True, exist_ok=True)
        env["CREATOR_RESULTS_DIR"] = str(logs_base)

        # Add retry logic for timeouts
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "http://127.0.0.1:8001/run-custom-task-test",
                    json={**test_data, "results_dir": str(logs_base)},
                    timeout=120  # Increased timeout
                )
                break  # Success, exit retry loop
            except RequestTimeout:
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retry
                    continue
                else:
                    raise
        
        if response.status_code == 200:
            result = response.json()
            # Handle multiple screenshots - take only the first one to avoid duplicates
            screenshot_path = None
            if result.get("screenshots") and len(result["screenshots"]) > 0:
                # Take the first screenshot to avoid duplicate display issues
                screenshot_path = result["screenshots"][0]
            
            # Get detailed validation count
            validation_results = result.get("results", [])
            total_validations = len([r for r in validation_results if r.get("validation_results")])
            passed_validations = sum(1 for r in validation_results for v in r.get("validation_results", []) if v.get("passed", False))
            
            status = "PASS" if result["failed_tests"] == 0 and passed_validations > 0 else "FAIL"
            
            # Create informative message
            if total_validations > 0:
                message = f"Validation: {passed_validations}/{len(validation_results[0].get('validation_results', []))} passed" if validation_results else "Test completed"
            else:
                message = f"Test: {result['passed_tests']}/{result['total_tests']} passed"
            
            return {
                "status": status,
                "message": message,
                "screenshot": screenshot_path,
                "details": result,
                "validation_results": result.get("results", []),
                "logs": result.get("logs", [])
            }
        else:
            return {
                "status": "ERROR",
                "message": f"Backend error: {response.status_code}",
                "screenshot": None,
                "error": f"HTTP {response.status_code}"
            }
            
    except RequestTimeout as e:
        return {
            "status": "TIMEOUT",
            "message": f"Test timed out after 120 seconds: {str(e)}",
            "screenshot": None,
            "error": f"Timeout: {str(e)}",
            "logs": [f"Test execution timed out. The application may be slow or unresponsive."]
        }
    except RequestException as e:
        return {
            "status": "ERROR",
            "message": f"Network error: {str(e)}",
            "screenshot": None,
            "error": str(e),
            "logs": [f"Failed to connect to Playwright backend: {str(e)}"]
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e),
            "screenshot": None,
            "error": str(e),
            "logs": [f"Unexpected error during test execution: {str(e)}"]
        }

def capture_reference_screenshots(project_data, tmp_dir):
    """Capture reference screenshots for all tasks."""
    try:
        # Start Flask app
        flask_process = start_flask_app(tmp_dir)
        time.sleep(3)
        
        screenshots = []
        for task in project_data.get("tasks", []):
            playwright_test = task.get("playwright_test", {})
            route = playwright_test.get("route", "")
            
            if route:
                screenshot = capture_task_screenshot(task, route)
                if screenshot:
                    screenshots.append({
                        "task_id": task["id"],
                        "task_name": task["name"],
                        "route": route,
                        "screenshot": screenshot
                    })
        
        # Stop Flask app
        if flask_process:
            flask_process.terminate()
        
        return screenshots
    except Exception as e:
        st.error(f"Screenshot capture failed: {str(e)}")
        return []

def capture_task_screenshot(task, route):
    """Capture screenshot for a single task."""
    try:
        # Use Playwright to capture screenshot
        test_data = {
            "base_url": "http://127.0.0.1:5000",
            "test_suite": "screenshot",
            "project_name": f"ref_task_{task['id']}",
            "timeout": 30,
            "headless": True,
            "capture_screenshots": True,
            "task_config": {
                "task_id": task["id"],
                "screenshot_only": True,
                "route": route,
                "actions": task.get("playwright_test", {}).get("actions", []),
                "validate": []
            }
        }
        
        response = requests.post(
            "http://127.0.0.1:8001/run-custom-task-test",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            # Handle multiple screenshots - take only the first one to avoid duplicates
            if result.get("screenshots") and len(result["screenshots"]) > 0:
                return result["screenshots"][0]
            return None
    except Exception as e:
        st.error(f"Screenshot failed for task {task['id']}: {e}")
    return None

def display_preview_results(results):
    """Display Playwright test results."""
    st.markdown("#### Preview Results")
    
    for result in results:
        col_status, col_info, col_screenshot = st.columns([1, 3, 2])
        
        with col_status:
            if result["status"] == "PASS":
                st.success("PASS")
            elif result["status"] == "FAIL":
                st.error("FAIL")
            elif result["status"] == "SKIP":
                st.warning("SKIP")
            else:
                st.error("ERROR")
        
        with col_info:
            st.write(f"**Task {result['task_id']}:** {result['task_name']}")
            st.write(f"*{result['message']}*")
        
        with col_screenshot:
            if result["screenshot"]:
                # Display screenshot if available
                try:
                    # This would need to be implemented based on how screenshots are stored
                    st.write("📸 Screenshot available")
                except:
                    st.write("📸 Screenshot captured")

def save_verification_log(verification_results, tmp_dir):
    """Save comprehensive verification log to file."""
    try:
        # Create logs directory
        logs_dir = Path("Logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create project-specific log directory
        project_name = verification_results["project_name"].replace(" ", "_").lower()
        project_log_dir = logs_dir / project_name
        # Ensure screenshots folder exists for this project
        (project_log_dir / "screenshots").mkdir(exist_ok=True)
        project_log_dir.mkdir(exist_ok=True)
        
        # Generate log filename with timestamp
        timestamp = verification_results["verification_timestamp"].replace(":", "-").replace(" ", "_")
        log_filename = f"comprehensive_verification_{timestamp}.json"
        log_path = project_log_dir / log_filename
        
        # Save comprehensive log
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(verification_results, f, indent=2)
        
        # Also save a human-readable summary
        summary_filename = f"verification_summary_{timestamp}.txt"
        summary_path = project_log_dir / summary_filename
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"COMPREHENSIVE TASK VERIFICATION REPORT\n")
            f.write(f"=====================================\n\n")
            f.write(f"Project: {verification_results['project_name']}\n")
            f.write(f"Description: {verification_results['project_description']}\n")
            f.write(f"Verification Time: {verification_results['verification_timestamp']}\n")
            f.write(f"Total Tasks: {verification_results['total_tasks']}\n\n")
            
            f.write(f"SUMMARY\n")
            f.write(f"-------\n")
            f.write(f"Total Tests: {verification_results['summary']['total_tests']}\n")
            f.write(f"Passed Tests: {verification_results['summary']['passed_tests']}\n")
            f.write(f"Failed Tests: {verification_results['summary']['failed_tests']}\n")
            f.write(f"Screenshots Captured: {verification_results['summary']['screenshots_captured']}\n")
            
            if verification_results['summary']['errors']:
                f.write(f"Errors: {len(verification_results['summary']['errors'])}\n")
            
            f.write(f"\nDETAILED TASK ANALYSIS\n")
            f.write(f"=====================\n\n")
            
            for task in verification_results['tasks']:
                f.write(f"Task {task['task_id']}: {task['task_name']}\n")
                f.write(f"  Description: {task['task_description']}\n")
                f.write(f"  Test Status: {task['test_status']}\n")
                f.write(f"  Test Message: {task['test_message']}\n")
                f.write(f"  Screenshot Captured: {'Yes' if task['screenshot_captured'] else 'No'}\n")
                
                config_analysis = task['configuration_analysis']
                f.write(f"  Configuration Score: {config_analysis['completeness_score']}/100\n")
                
                # Required files
                required_files = config_analysis.get('required_files', [])
                f.write(f"  Required Files: {', '.join(required_files) if required_files else 'None'}\n")
                
                # Validation rules
                validation_rules = config_analysis.get('validation_rules', {})
                f.write(f"  Validation Type: {validation_rules.get('type', 'Not specified')}\n")
                f.write(f"  Validation File: {validation_rules.get('file', 'Not specified')}\n")
                f.write(f"  Validation Points: {validation_rules.get('points', 'Not specified')}\n")
                
                # Playwright test
                playwright_test = config_analysis.get('playwright_test', {})
                f.write(f"  Playwright Route: {playwright_test.get('route', 'Not specified')}\n")
                f.write(f"  Playwright Actions: {len(playwright_test.get('actions', []))}\n")
                f.write(f"  Playwright Validations: {len(playwright_test.get('validate', []))}\n")
                f.write(f"  Playwright Points: {playwright_test.get('points', 'Not specified')}\n")
                
                if config_analysis['issues']:
                    f.write(f"  Issues:\n")
                    for issue in config_analysis['issues']:
                        f.write(f"    - {issue}\n")
                
                if config_analysis['recommendations']:
                    f.write(f"  Recommendations:\n")
                    for rec in config_analysis['r   ecommendations']:
                        f.write(f"    - {rec}\n")
                
                if task.get('validation_results'):
                    f.write(f"  Validation Results:\n")
                    for validation in task['validation_results']:
                        if isinstance(validation, dict):
                            status = "PASS" if validation.get('passed', False) else "FAIL"
                            f.write(f"    - {status}: {validation.get('rule', 'Unknown rule')}\n")
                            f.write(f"      {validation.get('message', '')}\n")
                
                if task.get('playwright_logs'):
                    f.write(f"  Playwright Execution Logs:\n")
                    for log_entry in task['playwright_logs']:
                        f.write(f"    {log_entry}\n")
                
                if task['errors']:
                    f.write(f"  Errors:\n")
                    for error in task['errors']:
                        f.write(f"    - {error}\n")
                
                f.write(f"\n")
        
        st.success(f"Comprehensive verification log saved to: {log_path}")
        st.info(f"Summary report saved to: {summary_path}")
        
    except Exception as e:
        st.error(f"Failed to save verification log: {str(e)}")

def display_comprehensive_verification_results(verification_results):
    st.markdown("#### Comprehensive Task Verification Results")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tasks", verification_results["total_tasks"])
    with col2:
        st.metric("Passed Tests", verification_results["summary"]["passed_tests"])
    with col3:
        st.metric("Failed Tests", verification_results["summary"]["failed_tests"])
    with col4:
        st.metric("Screenshots", verification_results["summary"]["screenshots_captured"])
    
    # Project information
    st.markdown("**Project Information:**")
    st.write(f"**Name:** {verification_results['project_name']}")
    st.write(f"**Description:** {verification_results['project_description']}")
    st.write(f"**Verification Time:** {verification_results['verification_timestamp']}")
    
    # Overall status
    if verification_results["summary"]["failed_tests"] == 0:
        st.success("All tasks passed verification!")
    else:
        st.warning(f"{verification_results['summary']['failed_tests']} tasks failed verification")
    
    # Simplified task results
    st.markdown("---")
    st.markdown("#### Task Summary")
    
    for task in verification_results["tasks"]:
        col_status, col_info, col_score = st.columns([1, 3, 1])
        
        with col_status:
            if task["test_status"] == "PASS":
                st.success("PASS")
            elif task["test_status"] == "FAIL":
                st.error("FAIL")
            elif task["test_status"] == "SKIP":
                st.warning("SKIP")
            else:
                st.error("ERROR")
        
        with col_info:
            st.write(f"**Task {task['task_id']}:** {task['task_name']}")
            st.write(f"*{task['test_message']}*")
            if task["screenshot_captured"]:
                st.write("📸 Screenshot captured")
                # Note: Only showing first screenshot to avoid duplicate download button errors
        
        with col_score:
            config_analysis = task["configuration_analysis"]
            st.metric("Score", f"{config_analysis['completeness_score']}/100")
    
    if verification_results["summary"]["errors"]:
        st.markdown("---")
        st.markdown("#### Errors")
        for error in verification_results["summary"]["errors"]:
            st.error(f"• {error}")

st.set_page_config(page_title="Creator Portal", layout="wide")

st.markdown("""<style>
.section { background: #fff; border:1px solid #ddd; border-radius:10px; padding:20px; margin-bottom:20px; }
</style>""", unsafe_allow_html=True)

st.title("Creator Portal")

# Upload project ZIP
uploaded_zip = st.file_uploader("Upload Base Project ZIP", type=["zip"])

if uploaded_zip:
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, uploaded_zip.name)
    with open(zip_path, "wb") as f:
        f.write(uploaded_zip.getvalue())
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp_dir)
        st.success("Uploaded and extracted project.")
    except (zipfile.BadZipFile, EOFError) as e:
        st.error("The uploaded ZIP appears to be corrupted or incomplete. Please re-upload a valid ZIP file.")
        st.stop()

    col_left, col_right = st.columns([0.4, 0.6])

    # ---------------------- LEFT PANEL: File Structure & Generation ----------------------
    with col_left:
        st.subheader("Project File Structure")
        root_path = tmp_dir

        def show_file_tree(path, level=0):
            indent = "  " * level
            try:
                items = sorted(os.listdir(path))
                for item in items:
                    item_path = os.path.join(path, item)
                    rel_path = os.path.relpath(item_path, root_path)

                    if os.path.isdir(item_path):
                        with st.expander(f"{indent} {item}", expanded=False):
                            show_file_tree(item_path, level + 1)
                    else:
                        file_ext = os.path.splitext(item)[1].lower()
                        icon = "HTML" if file_ext == '.html' else "Python" if file_ext == '.py' else "Text"
                        if st.button(f"{indent}{icon} {item}", key=f"file_{rel_path}"):
                            st.session_state.selected_file = item_path
                            st.session_state.selected_file_name = item
            except Exception as e:
                st.error(f"Error accessing directory {path}: {e}")

        show_file_tree(root_path)

        # Optional: File preview
        if hasattr(st.session_state, 'selected_file') and st.session_state.selected_file:
            selected_file = st.session_state.selected_file
            st.markdown(f"**Selected:** {st.session_state.selected_file_name}")
            try:
                file_ext = os.path.splitext(selected_file)[1].lower()
                with open(selected_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                st.code(content, language=file_ext[1:] if file_ext else 'text')
            except Exception as e:
                st.error(f"Error reading file: {e}")

        st.markdown("---")
        st.subheader("Auto-generate Testcases")

        # User prompt input for project context
        st.markdown("#### Project Context")
        user_prompt = st.text_area(
            "Describe Your Project (optional but recommended)",
            placeholder="E.g., A Flask web app with a login, register, and dashboard system. Students should build a complete authentication system with user management...",
            height=150,
            help="Provide context about your project's purpose, complexity, and functionality. This helps generate more relevant and appropriate tasks."
        )
        
        # Show helpful tips
        with st.expander("Tips for Writing Effective Project Descriptions", expanded=False):
            st.markdown("""
            **Good project descriptions include:**
            - **Purpose**: What the application does (e.g., "e-commerce site", "blog platform")
            - **Key Features**: Main functionality (e.g., "user authentication", "product catalog", "payment processing")
            - **Complexity Level**: Beginner, intermediate, or advanced
            - **Learning Goals**: What students should learn (e.g., "database integration", "API design", "security practices")
            
            **Examples:**
            - "A simple blog platform where students learn Flask basics, template inheritance, and basic CRUD operations"
            - "An e-commerce site with user authentication, product management, and shopping cart functionality"
            - "A task management app with user registration, project creation, and team collaboration features"
            """)

        # Initialize Gemini generator
        gemini_generator = GeminiTestCaseGenerator()
        generation_method = gemini_generator.get_generation_method()

        if st.button("Generate Testcases", use_container_width=True):
            st.info("Generating testcases... Please wait.")
            try:
                if generation_method == 'AI' and gemini_generator.is_ai_enabled():
                    # Use Gemini AI generation with user context
                    project_meta = {
                        "project": "Custom Flask Project",
                        "description": user_prompt or "Auto-generated project without user context"
                    }
                    result_json = gemini_generator.generate_project_json_with_ai(tmp_dir, project_meta)
                    
                    # Add user prompt to the generated JSON for reference
                    if user_prompt:
                        result_json["creator_prompt"] = user_prompt
                        result_json["generation_context"] = "Generated with user-provided project context"
                    else:
                        result_json["generation_context"] = "Generated without user context"
                    
                    # Save the generated JSON
                    project_file = os.path.join(tmp_dir, "project_tasks.json")
                    with open(project_file, "w") as f:
                        json.dump(result_json, f, indent=2)
                    
                    st.success("Testcases generated successfully!")
                    if user_prompt:
                        st.info(f"✅ Generated with your project context: '{user_prompt[:100]}{'...' if len(user_prompt) > 100 else ''}'")
                    
                    # Show task summary
                    st.markdown("#### 📋 Generated Tasks Summary")
                    tasks = result_json.get('tasks', [])
                    if tasks:
                        for task in tasks:
                            col_task_id, col_task_name, col_task_points = st.columns([1, 3, 1])
                            with col_task_id:
                                st.write(f"**Task {task['id']}**")
                            with col_task_name:
                                st.write(task.get('name', 'Unnamed Task'))
                            with col_task_points:
                                val_points = task.get('validation_rules', {}).get('points', 0)
                                ui_points = task.get('playwright_test', {}).get('points', 0)
                                st.write(f"**{val_points + ui_points} pts**")
                    else:
                        st.info("No tasks were generated.")
                    
                    st.session_state.generated_json = result_json
                    
                else:
                    # Fallback to original parser method
                    st.info("Generating testcases using parser method...")
                    node_script = Path(__file__).parent / "autoTestcaseGenerator.js"
                    result = subprocess.run(
                        ["node", str(node_script), tmp_dir],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        st.success("Testcases generated successfully!")
                        st.text_area("Generator Output Log", result.stdout, height=150)
                        project_json_path = os.path.join(tmp_dir, "project_tasks.json")
                        if os.path.exists(project_json_path):
                            with open(project_json_path, "r", encoding="utf-8") as f:
                                project_data = json.load(f)
                            
                            # Show task summary
                            st.markdown("#### 📋 Generated Tasks Summary")
                            tasks = project_data.get('tasks', [])
                            if tasks:
                                for task in tasks:
                                    col_task_id, col_task_name, col_task_points = st.columns([1, 3, 1])
                                    with col_task_id:
                                        st.write(f"**Task {task['id']}**")
                                    with col_task_name:
                                        st.write(task.get('name', 'Unnamed Task'))
                                    with col_task_points:
                                        val_points = task.get('validation_rules', {}).get('points', 0)
                                        ui_points = task.get('playwright_test', {}).get('points', 0)
                                        st.write(f"**{val_points + ui_points} pts**")
                            else:
                                st.info("No tasks were generated.")
                            
                            st.session_state.generated_json = project_data
                            # Store generation timestamp
                            from datetime import datetime
                            st.session_state.generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            st.error(f"Parser generation failed: {result.stderr}")
                    else:
                        st.error(f"Parser generation failed: {result.stderr}")
                        
            except Exception as e:
                st.error(f"Generation failed: {str(e)}")
                if generation_method == 'AI':
                    st.info("Tip: Check your GEMINI_API_KEY in .env or try switching to PARSER mode")

    # ---------------------- RIGHT PANEL: Task Configuration & Form ----------------------
    with col_right:
        st.subheader("Task Configuration & Form")
        
        # Check if we have generated JSON
        if hasattr(st.session_state, 'generated_json') and st.session_state.generated_json:
            project_data = st.session_state.generated_json
            
            # Project Info Section
            with st.expander("📋 Project Information", expanded=True):
                project_data["project"] = st.text_input("Project Name", value=project_data.get("project", ""))
                project_data["description"] = st.text_area("Project Description", value=project_data.get("description", ""))
                
                # Show project stats
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                with col_stats1:
                    st.metric("Total Tasks", len(project_data.get("tasks", [])))
                with col_stats2:
                    total_points = sum(
                        task.get('validation_rules', {}).get('points', 0) + 
                        task.get('playwright_test', {}).get('points', 0)
                        for task in project_data.get('tasks', [])
                    )
                    st.metric("Total Points", total_points)
                with col_stats3:
                    st.metric("Generation Method", generation_method)
            
            st.markdown("---")
            st.markdown("### 📝 Tasks Configuration")
            
            for i, task in enumerate(project_data["tasks"]):
                with st.expander(f"Task {task['id']}: {task['name']}", expanded=False):
                    col_task_header, col_delete = st.columns([4, 1])
                    with col_delete:
                        if st.button("Delete", key=f"tc_delete_task_{i}", help="Delete this task"):
                            project_data["tasks"].pop(i)
                            st.session_state.generated_json = project_data
                            st.rerun()
                    new_name = st.text_input(f"Task Name", value=task["name"], key=f"tc_task_name_{i}")
                    new_description = st.text_area(f"Description", value=task["description"], key=f"tc_task_desc_{i}")
                    
                    st.markdown("**Required Files:**")
                    
                    available_files = [
                        "app.py", "requirements.txt", "templates/base.html", 
                        "templates/index.html", "templates/about.html", 
                        "templates/contact.html", "static/style.css", "static/script.js",
                        "main.py", "run.py", "config.py", "models.py", "views.py",
                        "templates/login.html", "templates/register.html", "templates/dashboard.html",
                        "static/css/style.css", "static/js/script.js", "static/images/logo.png"
                    ]
                    
                    current_files = task.get("required_files", [])
                    for file in current_files:
                        if file not in available_files:
                            available_files.append(file)
                    
                    selected_files = st.multiselect(
                        "Select Required Files",
                        options=available_files,
                        default=current_files,
                        key=f"tc_required_files_{i}",
                        help="Select the files that students must include in their project"
                    )
                    
                    if new_name != task["name"]:
                        task["name"] = new_name
                    if new_description != task["description"]:
                        task["description"] = new_description
                    if selected_files != current_files:
                        task["required_files"] = selected_files
                    
                    st.markdown("**Validation Rules:**")
                    validation_rules = task.get("validation_rules", {})
                    
                    if isinstance(validation_rules, list):
                        validation_rules = {}
                    
                    analysis = validation_rules.get("analysis", {})
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        # Get current values
                        current_type = validation_rules.get("type", "html")
                        current_points = validation_rules.get("points", 10)
                        
                        # Create form inputs
                        # Handle case where current_type might not be in the list
                        type_options = ["html", "css", "js", "python"]
                        try:
                            type_index = type_options.index(current_type)
                        except ValueError:
                            type_index = 0  # Default to "html" if not found
                            
                        new_type = st.selectbox(
                            "Type", 
                            type_options, 
                            index=type_index,
                            key=f"tc_val_type_{i}"
                        )
                        
                        # Dynamic points based on complexity
                        elements_count = len(analysis.get("elements", []))
                        forms_count = len(analysis.get("forms", []))
                        complexity_score = min(50, elements_count * 2 + forms_count * 5)
                        new_points = st.number_input(
                            "Points", 
                            min_value=1, 
                            max_value=100, 
                            value=max(current_points, complexity_score),
                            key=f"tc_val_points_{i}"
                        )
                    
                    with col2:
                        current_file = validation_rules.get("file", "")
                        new_file = st.text_input(
                            "File", 
                            value=current_file,
                            key=f"tc_val_file_{i}"
                        )
                    
                    # Update validation rules only if changed
                    if new_type != current_type:
                        validation_rules["type"] = new_type
                    if new_points != current_points:
                        validation_rules["points"] = new_points
                    if new_file != current_file:
                        validation_rules["file"] = new_file
                    
                    # Initialize analysis variables
                    elements = []
                    forms = []
                    links = []
                    
                    # Show analysis results
                    if analysis:
                        st.markdown("**Analysis Results:**")
                        elements = analysis.get("elements", [])
                        forms = analysis.get("forms", [])
                        links = analysis.get("links", [])
                        
                        col_analysis1, col_analysis2, col_analysis3 = st.columns(3)
                        with col_analysis1:
                            st.metric("Elements Found", len(elements))
                        with col_analysis2:
                            st.metric("Forms Found", len(forms))
                        with col_analysis3:
                            st.metric("Links Found", len(links))
                        
                        # Show detected elements for reference
                        if elements:
                            with st.expander("Detected Elements", expanded=False):
                                for elem in elements[:10]:  # Show first 10
                                    st.write(f"• {elem.get('tag', 'unknown')} - {elem.get('class', 'no class')}")
                    
                    task["validation_rules"] = validation_rules
                    
                    # UI Test - populate from analysis
                    st.markdown("**UI Test:**")
                    ui_test = task.get("playwright_test", {}) or {}
                    
                    # Ensure ui_test is a dictionary, not a list
                    if isinstance(ui_test, list):
                        ui_test = {}
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        # Get current values
                        current_route = ui_test.get("route", "")
                        current_ui_points = ui_test.get("points", validation_rules.get("points", 10))
                        
                        # Generate route from file name
                        file_name = validation_rules.get("file", "")
                        route_suggestion = f"/{file_name.replace('.html', '').replace('.css', '').replace('.js', '')}" if file_name else ""
                        
                        new_route = st.text_input(
                            "Route", 
                            value=current_route or route_suggestion,
                            key=f"tc_pw_route_{i}"
                        )
                        new_ui_points = st.number_input(
                            "Points", 
                            min_value=1, 
                            max_value=100, 
                            value=max(1, int(current_ui_points)),
                            key=f"tc_ui_points_{i}"
                        )
                        
                        # Update only if changed
                        if new_route != current_route:
                            ui_test["route"] = new_route
                        if new_ui_points != current_ui_points:
                            ui_test["points"] = new_ui_points
                    
                    with col4:
                        # Generate actions from analysis
                        suggested_actions = []
                        if forms:
                            for form in forms:
                                if form.get("inputs"):
                                    suggested_actions.append(f"Fill form with {len(form['inputs'])} fields")
                        if links:
                            suggested_actions.append(f"Click {len(links)} links")
                        
                        # Convert actions to readable text format
                        actions = ui_test.get("actions", suggested_actions)
                        actions_text = ""
                        if isinstance(actions, list):
                            # If list of dicts → pretty lines; else stringify items safely
                            if actions and isinstance(actions[0], dict):
                                lines = []
                                for action in actions:
                                    if not isinstance(action, dict):
                                        lines.append(str(action))
                                        continue
                                    if action.get("click"):
                                        lines.append(f"Click: {action.get('selector_type', 'class')}={action.get('selector_value', '')}")
                                    elif action.get("input_variants"):
                                        variants = ", ".join([str(v) for v in action.get("input_variants", [])])
                                        lines.append(f"Fill {action.get('selector_type', 'class')}={action.get('selector_value', '')}: {variants}")
                                    else:
                                        lines.append(str(action))
                                actions_text = "\n".join(lines)
                            else:
                                actions_text = "\n".join([str(a) for a in actions]) if actions else ""
                        else:
                            # Not a list; stringify whatever came through
                            actions_text = str(actions) if actions else ""
                        actions_input = st.text_area(
                            "Actions (one per line)",
                            value=actions_text,
                            height=100,
                            key=f"tc_ui_actions_{i}"
                        )
                        
                        # Parse actions back to proper format
                        if actions_input.strip():
                            parsed_actions = []
                            for line in actions_input.strip().split("\n"):
                                line = line.strip()
                                if line.startswith("Click:"):
                                    # Parse click action
                                    parts = line.split("=", 1)
                                    if len(parts) == 2:
                                        selector_type = parts[0].replace("Click:", "").strip()
                                        selector_value = parts[1].strip()
                                        parsed_actions.append({
                                            "selector_type": selector_type,
                                            "selector_value": selector_value,
                                            "click": True
                                        })
                                elif line.startswith("Fill") and ":" in line:
                                    # Parse fill action
                                    fill_part, variants_part = line.split(":", 1)
                                    if "=" in fill_part:
                                        selector_part = fill_part.replace("Fill", "").strip()
                                        if "=" in selector_part:
                                            selector_type, selector_value = selector_part.split("=", 1)
                                            variants = [v.strip() for v in variants_part.split(",")]
                                            parsed_actions.append({
                                                "selector_type": selector_type.strip(),
                                                "selector_value": selector_value.strip(),
                                                "input_variants": variants
                                            })
                                else:
                                    # Keep as string for manual actions
                                    parsed_actions.append(line)
                            ui_test["actions"] = parsed_actions
                        else:
                            ui_test["actions"] = []
                    
                    # Validation section
                    st.markdown("**Validation Rules:**")
                    validation_rules_list = ui_test.get("validate", [])
                    if isinstance(validation_rules_list, list) and validation_rules_list and isinstance(validation_rules_list[0], dict):
                        # Convert dict validation rules to readable text
                        validation_text = []
                        for rule in validation_rules_list:
                            rule_type = rule.get("type", "unknown")
                            rule_value = rule.get("value", "")
                            validation_text.append(f"{rule_type}: {rule_value}")
                        validation_text = "\n".join(validation_text)
                    else:
                        validation_text = "\n".join(validation_rules_list) if validation_rules_list else ""
                    
                    validation_input = st.text_area(
                        "Validation Rules (one per line)",
                        value=validation_text,
                        height=100,
                        key=f"tc_ui_validate_{i}",
                        help="Format: type: value (e.g., 'text_present: Login successful')"
                    )
                    
                    # Parse validation rules back to proper format
                    if validation_input.strip():
                        parsed_validation = []
                        for line in validation_input.strip().split("\n"):
                            line = line.strip()
                            if ":" in line:
                                rule_type, rule_value = line.split(":", 1)
                                parsed_validation.append({
                                    "type": rule_type.strip(),
                                    "value": rule_value.strip()
                                })
                            else:
                                # Keep as string for manual rules
                                parsed_validation.append(line)
                        ui_test["validate"] = parsed_validation
                    else:
                        ui_test["validate"] = []
                    
                    task["playwright_test"] = ui_test
                    
                    # Unlock Condition
                    st.markdown("**Unlock Condition:**")
                    unlock_condition = task.get("unlock_condition", {})
                    
                    # Ensure unlock_condition is a dictionary, not a list
                    if isinstance(unlock_condition, list):
                        unlock_condition = {}
                    
                    col5, col6 = st.columns(2)
                    with col5:
                        current_min_score = unlock_condition.get("min_score", 0)
                        new_min_score = st.number_input(
                            "Min Score", 
                            min_value=0, 
                            max_value=100, 
                            value=current_min_score,
                            key=f"tc_unlock_score_{i}"
                        )
                    
                    with col6:
                        # Show available task IDs for reference
                        available_task_ids = [str(t["id"]) for t in project_data["tasks"] if t["id"] != task["id"]]
                        current_required_tasks = unlock_condition.get("required_tasks", [])
                        required_tasks_text = ", ".join(map(str, current_required_tasks))
                        st.caption(f"Available task IDs: {', '.join(available_task_ids)}")
                        required_tasks_input = st.text_input(
                            "Required Tasks (comma-separated IDs)",
                            value=required_tasks_text,
                            key=f"tc_unlock_tasks_{i}"
                        )
                        
                        # Parse required tasks
                        try:
                            new_required_tasks = [int(x.strip()) for x in required_tasks_input.split(",") if x.strip()]
                        except ValueError:
                            new_required_tasks = current_required_tasks
                    
                    # Update only if changed
                    if new_min_score != current_min_score:
                        unlock_condition["min_score"] = new_min_score
                    if new_required_tasks != current_required_tasks:
                        unlock_condition["required_tasks"] = new_required_tasks
                    
                    task["unlock_condition"] = unlock_condition
                    
                    st.divider()
            
            # Comprehensive Task Verification Section
            st.markdown("---")
            st.markdown("### 🧪 Test Verification")
            
            # Check if Playwright backend is available
            playwright_available = check_playwright_backend()
            
            if playwright_available:
                col_verify, col_status = st.columns([2, 1])
                with col_verify:
                    if st.button("🚀 Run Comprehensive Verification", use_container_width=True, type="primary"):
                        with st.spinner("Running comprehensive task verification..."):
                            verification_results = run_comprehensive_task_verification(project_data, tmp_dir)
                            st.session_state.comprehensive_verification_results = verification_results
                            st.success("Comprehensive verification completed!")
                
                with col_status:
                    if playwright_available:
                        st.success("✅ Backend Ready")
                    else:
                        st.error("❌ Backend Offline")
                
                # Display comprehensive verification results
                if hasattr(st.session_state, 'comprehensive_verification_results') and st.session_state.comprehensive_verification_results:
                    display_comprehensive_verification_results(st.session_state.comprehensive_verification_results)
            else:
                st.warning("⚠️ Playwright backend not available. Start the backend server to enable comprehensive verification.")
                st.code("python playwright_backend/start_server.py", language="bash")
            
            # Add new task button
            st.markdown("### Add New Task")
            col_add, col_spacer = st.columns([0.3, 0.7])
            with col_add:
                if st.button("Add New Task", use_container_width=True):
                    new_task_id = max([t["id"] for t in project_data["tasks"]], default=0) + 1
                    new_task = {
                        "id": new_task_id,
                        "name": f"New Task {new_task_id}",
                        "description": "Custom task description",
                        "required_files": [],
                        "validation_rules": {
                            "type": "html",
                            "file": "",
                            "points": 10,
                            "generatedTests": [],
                            "analysis": {}
                        },
                        "playwright_test": {
                            "route": "",
                            "actions": [],
                            "validate": [],
                            "points": 10
                        },
                        "unlock_condition": {
                            "min_score": 0,
                            "required_tasks": []
                        }
                    }
                    project_data["tasks"].append(new_task)
                    st.session_state.generated_json = project_data
                    st.rerun()
            
            # Action buttons
            st.markdown("---")
            st.markdown("### 💾 Save & Export")
            col_save, col_edit, col_spacer = st.columns([1, 1, 2])
            
            with col_save:
                if st.button("💾 Save Project Package", use_container_width=True, type="primary"):
                    # Create projects directory (shared with student.py)
                    projects_dir = Path("projects")
                    projects_dir.mkdir(exist_ok=True)
                    
                    # Create project package directory
                    project_name = project_data.get("project", "project").replace(" ", "_").lower()
                    package_dir = projects_dir / f"{project_name}_package"
                    package_dir.mkdir(exist_ok=True)
                    
                    # Save JSON configuration to projects directory (for student.py to find)
                    json_filename = f"{project_name}_configuration.json"
                    json_path = projects_dir / json_filename
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(project_data, f, indent=2)
                    
                    # Also save in package directory
                    package_json_path = package_dir / "project_configuration.json"
                    with open(package_json_path, "w", encoding="utf-8") as f:
                        json.dump(project_data, f, indent=2)
                    
                    # Copy ZIP file to package
                    zip_path = package_dir / uploaded_zip.name
                    with open(zip_path, "wb") as f:
                        f.write(uploaded_zip.getvalue())
                    
                    # Create project info file
                    info_path = package_dir / "README.txt"
                    with open(info_path, "w", encoding="utf-8") as f:
                        f.write(f"""Project Package: {project_data.get('project', 'Untitled Project')}
Description: {project_data.get('description', 'No description provided')}
Generated: {st.session_state.get('generation_time', 'Unknown')}
Tasks: {len(project_data.get('tasks', []))}

Files included:
- project_configuration.json: Task configuration and validation rules
- {uploaded_zip.name}: Original project ZIP file

To use this package:
1. Extract the ZIP file to get the project source code
2. Use the JSON configuration with your validation system
3. Run UI tests using the configured routes and actions
""")
                    
                    st.success(f"Project saved and available to students!")
                    st.info(f"Project '{project_data.get('project', 'Untitled')}' is now available in the Student Portal")
                    st.success(f"Files saved to: {projects_dir}")
                    st.caption(f"JSON config: {json_filename}")
                    st.caption(f"Package: {package_dir}")
                    
                    # Create downloadable ZIP of the entire package
                    import zipfile
                    package_zip_path = projects_dir / f"{project_name}_package.zip"
                    with zipfile.ZipFile(package_zip_path, 'w', zipfile.ZIP_DEFLATED) as package_zip:
                        for file_path in package_dir.rglob('*'):
                            if file_path.is_file():
                                package_zip.write(file_path, file_path.relative_to(package_dir))
                    
                    # Provide download for the complete package
                    with open(package_zip_path, "rb") as f:
                        package_content = f.read()
                    
                    st.download_button(
                        label="Download Complete Package",
                        data=package_content,
                        file_name=f"{project_name}_package.zip",
                        mime="application/zip",
                        help="Downloads the complete project package with JSON config and source ZIP",
                        key=f"download_package_{project_name}"
                    )
                    
                    # Also provide individual JSON download
                    with open(json_path, "r", encoding="utf-8") as f:
                        json_content = f.read()
                    st.download_button(
                        label="Download JSON Only",
                        data=json_content,
                        file_name=json_filename,
                        mime="application/json",
                        help="Downloads only the JSON configuration file",
                        key=f"download_json_{project_name}"
                    )
            
            with col_edit:
                if st.button("✏️ Edit Raw JSON", use_container_width=True):
                    st.session_state.edit_mode = not st.session_state.get('edit_mode', False)
            
            # Raw JSON editor
            if st.session_state.get('edit_mode', False):
                st.markdown("### Raw JSON Editor")
                json_text = st.text_area(
                    "Edit JSON Configuration",
                    value=json.dumps(project_data, indent=2),
                    height=400,
                    key="raw_json_editor"
                )
                
                if st.button("Update from JSON"):
                    try:
                        updated_data = json.loads(json_text)
                        st.session_state.generated_json = updated_data
                        st.success("JSON updated successfully!")
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")
        
        else:
            # Only show this message if no file has been uploaded
            if not uploaded_zip:
                st.info("Upload a project ZIP and generate testcases to configure tasks.")
            
            # Comprehensive Project Configuration Form
            st.markdown("### Create Project Configuration")
            
            # Project metadata
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("Project Name", value="")
            with col2:
                project_description = st.text_input("Project Description", value="")
            
            st.markdown("---")
            st.markdown("#### Add Tasks")
            
            # Initialize session state for tasks
            if 'tasks' not in st.session_state:
                st.session_state.tasks = []
            
            # Task creation form
            with st.expander("Add New Task", expanded=True):
                task_name = st.text_input("Task Name", placeholder="e.g., Login Validation")
                task_description = st.text_area("Task Description", placeholder="e.g., Auto-generated validation for login.html")
                
                col3, col4 = st.columns(2)
                with col3:
                    required_files = st.multiselect(
                        "Required Files",
                        options=[
                            "app.py", "requirements.txt", "templates/base.html", 
                            "templates/index.html", "templates/about.html", 
                            "templates/contact.html", "templates/login.html",
                            "templates/register.html", "templates/dashboard.html",
                            "static/style.css", "static/script.js", "main.py", 
                            "run.py", "config.py", "models.py", "views.py"
                        ],
                        default=[]
                    )
                
                with col4:
                    file_type = st.selectbox("File Type", ["structure", "html", "py", "css", "js"])
                    points = st.number_input("Points", min_value=1, max_value=50, value=1)
                
                # UI test configuration
                st.markdown("**UI Test Configuration:**")
                col5, col6 = st.columns(2)
                with col5:
                    route = st.text_input("Route", placeholder="/login")
                with col6:
                    ui_points = st.number_input("UI Test Points", min_value=1, max_value=50, value=1)
                
                # Actions for UI test
                st.markdown("**Actions:**")
                action_type = st.selectbox("Action Type", ["click", "input", "navigate"])
                
                if action_type == "input":
                    col7, col8 = st.columns(2)
                    with col7:
                        selector_type = st.selectbox("Selector Type", ["class", "id", "text"])
                        selector_value = st.text_input("Selector Value", placeholder="form-control")
                    with col8:
                        input_variants = st.text_area("Input Variants (one per line)", 
                                                   placeholder="test@example.com\ninvalid_email\nuser@domain")
                elif action_type == "click":
                    col7, col8 = st.columns(2)
                    with col7:
                        selector_type = st.selectbox("Selector Type", ["class", "id", "text"])
                        selector_value = st.text_input("Selector Value", placeholder="btn-primary")
                    with col8:
                        st.write("Click action will be added")
                
                # Validation rules
                st.markdown("**Validation Rules:**")
                validation_texts = st.text_area("Validation Texts (one per line)", 
                                               placeholder="Login successful\nInvalid credentials\nEmail is required")
                
                if st.button("Add Task", type="primary"):
                    if task_name and required_files:
                        # Create playwright actions
                        actions = []
                        if action_type == "input" and selector_value and input_variants:
                            actions.append({
                                "selector_type": selector_type,
                                "selector_value": selector_value,
                                "input_variants": [v.strip() for v in input_variants.split('\n') if v.strip()]
                            })
                        elif action_type == "click" and selector_value:
                            actions.append({
                                "selector_type": selector_type,
                                "selector_value": selector_value,
                                "click": True
                            })
                        
                        # Create validation rules
                        validate = []
                        
                        # Add custom validation texts
                        for text in validation_texts.split('\n'):
                            if text.strip():
                                validate.append({"type": "text_present", "value": text.strip()})
                        
                        # Create task
                        task_id = len(st.session_state.tasks) + 1
                        new_task = {
                            "id": task_id,
                            "name": task_name,
                            "description": task_description,
                            "required_files": required_files,
                            "validation_rules": {
                                "type": file_type,
                                "file": required_files[0] if (file_type != "structure" and required_files) else "",
                                "points": points,
                                "generatedTests": [],
                                "analysis": {"elements": [], "selectors": []}
                            },
                            "playwright_test": {
                                "route": route,
                                "actions": actions,
                                "validate": validate,
                                "points": ui_points
                            },
                            "unlock_condition": {"min_score": 0, "required_tasks": []}
                        }
                        
                        st.session_state.tasks.append(new_task)
                        st.success(f"Task '{task_name}' added!")
                        st.rerun()
                    else:
                        st.error("Please provide task name and at least one required file.")
            
            # Display current tasks
            if st.session_state.tasks:
                st.markdown("---")
                st.markdown("#### Current Tasks")
                for i, task in enumerate(st.session_state.tasks):
                    with st.expander(f"Task {task['id']}: {task['name']}", expanded=False):
                        col9, col10 = st.columns([3, 1])
                        with col9:
                            st.write(f"**Description:** {task['description']}")
                            st.write(f"**Required Files:** {', '.join(task['required_files'])}")
                            st.write(f"**Route:** {task['playwright_test']['route']}")
                            st.write(f"**Points:** {task['validation_rules']['points']} (validation) + {task['playwright_test']['points']} (UI test)")
                        with col10:
                            if st.button("Remove", key=f"tc_remove_{i}", help="Delete this task"):
                                st.session_state.tasks.pop(i)
                                st.rerun()
                
                # Generate final JSON
                st.markdown("---")
                st.markdown("#### Generate Project Configuration")
                
                if st.button("Generate Project JSON", type="primary"):
                    project_config = {
                        "project": project_name,
                        "description": project_description,
                        "tasks": st.session_state.tasks
                    }
                    
                    # Display the JSON
                    st.success("Project configuration generated!")
                    st.json(project_config)
                    
                    # Download button
                    json_str = json.dumps(project_config, indent=2)
                    st.download_button(
                        label="Download Project Configuration",
                        data=json_str,
                        file_name="project_configuration.json",
                        mime="application/json",
                        key="download_manual_config"
                    )

else:
    st.info("Please upload a project ZIP to begin.")

# Project Management Section (Full Width at Bottom)
st.markdown("---")
st.subheader("Project Management")

# Load existing projects
existing_projects = load_existing_projects()

if existing_projects:
    st.markdown("#### Existing Projects")
    
    # Project selection and management
    col_project_select, col_project_actions = st.columns([3, 1])
    
    with col_project_select:
        project_names = [f"{p['name']} ({len(p.get('tasks', []))} tasks)" for p in existing_projects]
        selected_project_idx = st.selectbox(
            "Select Project to Manage",
            range(len(existing_projects)),
            format_func=lambda x: project_names[x],
            key="project_selector"
        )
    
    with col_project_actions:
        if st.button("Refresh Projects", help="Reload projects from disk"):
            st.rerun()
    
    if selected_project_idx is not None:
        selected_project = existing_projects[selected_project_idx]
        display_project_details(selected_project, selected_project_idx)
        
        # Project editing interface
        if hasattr(st.session_state, 'editing_project') and st.session_state.editing_project_idx == selected_project_idx:
            display_project_editor(selected_project, selected_project_idx)
else:
    st.info("No existing projects found. Upload a project ZIP and generate testcases to create your first project.")
