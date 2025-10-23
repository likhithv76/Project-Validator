import streamlit as st
import subprocess
import tempfile, zipfile, os, json
from pathlib import Path
import sys
import requests
import asyncio
import threading
import time
sys.path.append(str(Path(__file__).parent.parent))
from gemini_generator import GeminiTestCaseGenerator

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
    """
    try:
        flask_process = start_flask_app(tmp_dir)
        time.sleep(3)
        
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
        
        # Save comprehensive log
        save_verification_log(verification_results, tmp_dir)
        
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
            # Start Flask app
            process = subprocess.Popen([
                sys.executable, app_py
            ], cwd=tmp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return process
    except Exception as e:
        st.error(f"Failed to start Flask app: {e}")
    return None

def analyze_task_comprehensively(task, tmp_dir):
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
        test_result = run_comprehensive_task_test(task, tmp_dir)
        
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

def run_comprehensive_task_test(task, tmp_dir):
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
            "project_name": f"comprehensive_task_{task['id']}",
            "timeout": 30,
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
        response = requests.post(
            "http://127.0.0.1:8001/run-custom-task-test",
            json=test_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "status": "PASS" if result["failed_tests"] == 0 else "FAIL",
                "message": f"Comprehensive test: {result['passed_tests']}/{result['total_tests']} passed",
                "screenshot": result["screenshots"][0] if result["screenshots"] else None,
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
            
    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e),
            "screenshot": None,
            "error": str(e)
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
            return result["screenshots"][0] if result["screenshots"] else None
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
                st.success("✅ PASS")
            elif result["status"] == "FAIL":
                st.error("❌ FAIL")
            elif result["status"] == "SKIP":
                st.warning("⏭️ SKIP")
            else:
                st.error("💥 ERROR")
        
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
                st.write("Screenshot captured")
        
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

    col_left, col_right = st.columns([0.5, 0.5])

    # ---------------------- LEFT PANEL ----------------------
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

        # Initialize Gemini generator
        gemini_generator = GeminiTestCaseGenerator()
        generation_method = gemini_generator.get_generation_method()

        if st.button("Generate Testcases", use_container_width=True):
            st.info("Generating testcases... Please wait.")
            try:
                if generation_method == 'AI' and gemini_generator.is_ai_enabled():
                    # Use Gemini AI generation
                    project_meta = {
                        "project": "New Project",
                        "description": "Auto-generated progressive validation project"
                    }
                    result_json = gemini_generator.generate_project_json_with_ai(tmp_dir, project_meta)
                    
                    # Save the generated JSON
                    project_file = os.path.join(tmp_dir, "project_tasks.json")
                    with open(project_file, "w") as f:
                        json.dump(result_json, f, indent=2)
                    
                    st.success("Testcases generated")
                    st.json(result_json)
                    st.session_state.generated_json = result_json
                    
                else:
                    # Fallback to original parser method
                    st.info("📝 Generating testcases using parser method...")
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
                            st.json(project_data)
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
                    st.info("💡 Tip: Check your GEMINI_API_KEY in .env or try switching to PARSER mode")

    # ---------------------- RIGHT PANEL ----------------------
    with col_right:
        st.subheader("Task Configuration")
        
        # Check if we have generated JSON
        if hasattr(st.session_state, 'generated_json') and st.session_state.generated_json:
            project_data = st.session_state.generated_json
            
            # Project Info Section
            st.markdown("### Project Information")
            project_data["project"] = st.text_input("Project Name", value=project_data.get("project", ""))
            project_data["description"] = st.text_area("Project Description", value=project_data.get("description", ""))
            
            st.markdown("---")
            st.markdown("### Tasks Configuration")
            
            for i, task in enumerate(project_data["tasks"]):
                with st.expander(f"Task {task['id']}: {task['name']}", expanded=False):
                    col_task_header, col_delete = st.columns([4, 1])
                    with col_delete:
                        if st.button("Delete", key=f"delete_task_{i}", help="Delete this task"):
                            project_data["tasks"].pop(i)
                            st.session_state.generated_json = project_data
                            st.rerun()
                    new_name = st.text_input(f"Task Name", value=task["name"], key=f"task_name_{i}")
                    new_description = st.text_area(f"Description", value=task["description"], key=f"task_desc_{i}")
                    
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
                        key=f"required_files_{i}",
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
                            key=f"val_type_{i}"
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
                            key=f"val_points_{i}"
                        )
                    
                    with col2:
                        current_file = validation_rules.get("file", "")
                        new_file = st.text_input(
                            "File", 
                            value=current_file,
                            key=f"val_file_{i}"
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
                            key=f"pw_route_{i}"
                        )
                        new_ui_points = st.number_input(
                            "Points", 
                            min_value=1, 
                            max_value=100, 
                            value=current_ui_points,
                            key=f"ui_points_{i}"
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
                            key=f"ui_actions_{i}"
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
                        key=f"ui_validate_{i}",
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
                            key=f"unlock_score_{i}"
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
                            key=f"unlock_tasks_{i}"
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
            st.markdown("### Comprehensive Task Verification")
            
            # Check if Playwright backend is available
            playwright_available = check_playwright_backend()
            
            if playwright_available:
                if st.button("Run Comprehensive Verification", use_container_width=True, type="primary"):
                    with st.spinner("Running comprehensive task verification..."):
                        verification_results = run_comprehensive_task_verification(project_data, tmp_dir)
                        st.session_state.comprehensive_verification_results = verification_results
                        st.success("Comprehensive verification completed!")
                
                # Display comprehensive verification results
                if hasattr(st.session_state, 'comprehensive_verification_results') and st.session_state.comprehensive_verification_results:
                    display_comprehensive_verification_results(st.session_state.comprehensive_verification_results)
            else:
                st.warning("Playwright backend not available. Start the backend server to enable comprehensive verification.")
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
            col_save, col_edit = st.columns(2)
            
            with col_save:
                if st.button("Save Project Package", use_container_width=True):
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
                        help="Downloads the complete project package with JSON config and source ZIP"
                    )
                    
                    # Also provide individual JSON download
                    with open(json_path, "r", encoding="utf-8") as f:
                        json_content = f.read()
                    st.download_button(
                        label="Download JSON Only",
                        data=json_content,
                        file_name=json_filename,
                        mime="application/json",
                        help="Downloads only the JSON configuration file"
                    )
            
            with col_edit:
                if st.button("Edit Raw JSON", use_container_width=True):
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
                            if st.button("Remove", key=f"remove_{i}", help="Delete this task"):
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
                        mime="application/json"
                    )

else:
    st.info("Please upload a project ZIP to begin.")
