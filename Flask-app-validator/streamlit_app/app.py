import streamlit as st
import zipfile
import tempfile
import os
import sys
import time
import json
from pathlib import Path
import importlib

project_root = Path(__file__).resolve().parents[1]
validator_dir = project_root / "validator"
sys.path.insert(0, str(validator_dir))

import flexible_validator as fv
importlib.reload(fv)
from flexible_validator import run_flexible_validation

# Import task validator
try:
    from task_validator import TaskValidator
except ImportError:
    # Fallback for when running as standalone
    sys.path.append(str(validator_dir))
    from task_validator import TaskValidator

st.set_page_config(page_title="Flask Project Validator", page_icon="🧠", layout="wide")

# Define functions before they're used
def render_student_mode():
    """Render the student interface for task-based validation."""
    st.header("🎓 Student Mode")
    
    # Student ID input
    student_id = st.text_input("Student ID", value="student_001", help="Enter your unique student identifier")
    
    # Initialize task validator
    task_validator = TaskValidator()
    
    # Get student progress
    progress = task_validator.get_student_progress(student_id)
    
    # Display progress summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Completed Tasks", len(progress["completed_tasks"]))
    with col2:
        st.metric("Current Task", progress["current_task"])
    with col3:
        st.metric("Total Score", progress["total_score"])
    with col4:
        st.metric("Last Updated", progress["last_updated"][:10])
    
    st.divider()
    
    # Get all tasks
    all_tasks = task_validator.get_all_tasks()
    
    if not all_tasks:
        st.warning("No tasks available. Please contact your instructor.")
        return
    
    # Display tasks
    for task in all_tasks:
        task_id = task["id"]
        task_name = task["name"]
        task_description = task["description"]
        
        # Check if task is unlocked
        required_tasks = task.get("unlock_condition", {}).get("required_tasks", [])
        is_unlocked = all(rt in progress["completed_tasks"] for rt in required_tasks)
        
        # Task status
        if task_id in progress["completed_tasks"]:
            status = "✅ Completed"
            status_color = "success"
        elif is_unlocked:
            status = "🔓 Available"
            status_color = "info"
        else:
            status = "🔒 Locked"
            status_color = "secondary"
        
        # Create task expander
        with st.expander(f"Task {task_id}: {task_name} - {status}"):
            st.write(f"**Description:** {task_description}")
            st.write(f"**Status:** {status}")
            
            # Show required files
            required_files = task.get("required_files", [])
            if required_files:
                st.write("**Required Files:**")
                for file in required_files:
                    st.write(f"- {file}")
            
            # Show validation rules
            validation_rules = task.get("validation_rules", {})
            if validation_rules:
                st.write("**Validation Rules:**")
                rule_type = validation_rules.get("type", "unknown")
                points = validation_rules.get("points", 0)
                st.write(f"- Type: {rule_type}")
                st.write(f"- Points: {points}")
                
                if "mustHaveElements" in validation_rules:
                    st.write(f"- Required Elements: {', '.join(validation_rules['mustHaveElements'])}")
                if "mustHaveClasses" in validation_rules:
                    st.write(f"- Required Classes: {', '.join(validation_rules['mustHaveClasses'])}")
            
            # Show Playwright test info
            playwright_test = task.get("playwright_test")
            if playwright_test:
                st.write("**Playwright Test:**")
                route = playwright_test.get("route", "/")
                points = playwright_test.get("points", 0)
                st.write(f"- Route: {route}")
                st.write(f"- Points: {points}")
            
            # Task actions
            if is_unlocked and task_id not in progress["completed_tasks"]:
                st.write("**Actions:**")
                
                # File upload
                uploaded_file = st.file_uploader(
                    f"Upload project for Task {task_id}",
                    type=["zip"],
                    key=f"upload_task_{task_id}"
                )
                
                if uploaded_file:
                    if st.button(f"Validate Task {task_id}", key=f"validate_task_{task_id}"):
                        with st.spinner(f"Validating Task {task_id}..."):
                            # Save uploaded file temporarily
                            temp_path = tempfile.mktemp(suffix=".zip")
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.getvalue())
                            
                            # Run validation
                            result = task_validator.validate_task(task_id, temp_path, student_id)
                            
                            # Display results
                            if result["success"]:
                                st.success(f"Task {task_id} validation completed successfully!")
                                
                                # Show scores
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Score", f"{result['total_score']}/{result['max_score']}")
                                with col2:
                                    st.metric("Static Score", f"{result['static_validation']['score']}/{result['static_validation']['max_score']}")
                                with col3:
                                    st.metric("Playwright Score", f"{result['playwright_validation']['score']}/{result['playwright_validation']['max_score']}")
                                
                                # Show validation details
                                with st.expander("Static Validation Details"):
                                    static_results = result["static_validation"]
                                    for check in static_results.get("validation_results", []):
                                        status_icon = "✅" if check.get("passed", False) else "❌"
                                        st.write(f"{status_icon} {check.get('name', 'Unknown')} - {check.get('message', '')}")
                                
                                # Show Playwright results
                                playwright_results = result["playwright_validation"]
                                if playwright_results.get("screenshots"):
                                    st.write("**Playwright Test Screenshots:**")
                                    for screenshot in playwright_results["screenshots"]:
                                        if os.path.exists(screenshot):
                                            st.image(screenshot, caption=f"Screenshot: {os.path.basename(screenshot)}")
                                
                                # Update progress
                                task_validator.update_student_progress(student_id, result)
                                st.rerun()
                                
                            else:
                                st.error(f"Task {task_id} validation failed: {result.get('error', 'Unknown error')}")
                            
                            # Clean up temp file
                            try:
                                os.unlink(temp_path)
                            except Exception:
                                pass
            elif task_id in progress["completed_tasks"]:
                st.success("This task has been completed!")
            else:
                st.info("Complete the required tasks to unlock this task.")


def render_instructor_mode():
    """Render the instructor interface for task management."""
    st.header("👨‍🏫 Instructor Mode")
    st.markdown("Manage tasks, view student progress, and configure validation rules")
    
    # Initialize task validator
    task_validator = TaskValidator()
    
    # Tabs for different instructor functions
    tab1, tab2, tab3, tab4 = st.tabs(["Task Management", "Student Progress", "Task Editor", "System Status"])
    
    with tab1:
        st.subheader("📋 Task Management")
        
        # Display all tasks
        all_tasks = task_validator.get_all_tasks()
        
        if all_tasks:
            st.write(f"**Total Tasks:** {len(all_tasks)}")
            
            for task in all_tasks:
                with st.expander(f"Task {task['id']}: {task['name']}"):
                    st.write(f"**Description:** {task['description']}")
                    st.write(f"**Required Files:** {', '.join(task.get('required_files', []))}")
                    
                    # Show validation rules
                    validation_rules = task.get("validation_rules", {})
                    if validation_rules:
                        st.write("**Static Validation:**")
                        st.write(f"- Type: {validation_rules.get('type', 'unknown')}")
                        st.write(f"- Points: {validation_rules.get('points', 0)}")
                    
                    # Show Playwright test
                    playwright_test = task.get("playwright_test")
                    if playwright_test:
                        st.write("**Playwright Test:**")
                        st.write(f"- Route: {playwright_test.get('route', '/')}")
                        st.write(f"- Points: {playwright_test.get('points', 0)}")
                    
                    # Show unlock conditions
                    unlock_condition = task.get("unlock_condition", {})
                    if unlock_condition:
                        st.write("**Unlock Conditions:**")
                        st.write(f"- Min Score: {unlock_condition.get('min_score', 0)}")
                        st.write(f"- Required Tasks: {unlock_condition.get('required_tasks', [])}")
        else:
            st.info("No tasks configured. Use the Task Editor to create tasks.")
    
    with tab2:
        st.subheader("📊 Student Progress")
        
        # Get list of students
        logs_dir = Path("Logs")
        if logs_dir.exists():
            students = [d.name for d in logs_dir.iterdir() if d.is_dir() and d.name != "screenshots"]
            
            if students:
                selected_student = st.selectbox("Select Student", students)
                
                if selected_student:
                    progress = task_validator.get_student_progress(selected_student)
                    
                    # Display progress
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Completed Tasks", len(progress["completed_tasks"]))
                    with col2:
                        st.metric("Current Task", progress["current_task"])
                    with col3:
                        st.metric("Total Score", progress["total_score"])
                    
                    # Show task completion details
                    st.write("**Task Completion Details:**")
                    for task in all_tasks:
                        task_id = task["id"]
                        if task_id in progress["completed_tasks"]:
                            st.write(f"✅ Task {task_id}: {task['name']}")
                        else:
                            st.write(f"⏳ Task {task_id}: {task['name']}")
            else:
                st.info("No students found. Students will appear here after they start using the system.")
        else:
            st.info("No logs directory found.")
    
    with tab3:
        st.subheader("✏️ Task Editor")
        st.info("Task editing functionality will be implemented in the next phase.")
        st.write("This will allow you to:")
        st.write("- Create new tasks")
        st.write("- Edit existing task rules")
        st.write("- Configure Playwright tests")
        st.write("- Set unlock conditions")
    
    with tab4:
        st.subheader("🔧 System Status")
        
        # Check system components
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if task_validator.tasks_file.exists():
                st.success("✅ Tasks configuration loaded")
            else:
                st.error("❌ Tasks configuration not found")
        
        with col2:
            if Path("validator/flexible_validator.py").exists():
                st.success("✅ Static validator available")
            else:
                st.error("❌ Static validator not found")
        
        with col3:
            try:
                from playwright.sync_api import sync_playwright
                st.success("✅ Playwright available")
            except ImportError:
                st.error("❌ Playwright not installed")
        
        # Show system info
        st.write("**System Information:**")
        st.write(f"- Tasks File: {task_validator.tasks_file}")
        st.write(f"- Logs Directory: {task_validator.logs_dir}")
        st.write(f"- Total Tasks: {len(all_tasks)}")

# Sidebar navigation
st.sidebar.title("Flask Validator")
page = st.sidebar.selectbox(
    "Choose Page",
    ["Main Validator", "Task-Based Validation", "Rule Builder", "Rule Manager"]
)

if page == "🔧 Rule Builder":
    # Import and run rule builder
    from rule_builder import main
    main()
    st.stop()

elif page == "Task-Based Validation":
    # Task-based validation interface
    st.title("🎯 Task-Based Progressive Validation")
    st.markdown("Validate Flask projects through progressive tasks with static and dynamic testing")
    
    # Mode selection
    mode = st.sidebar.radio("Select Mode", ["Student Mode", "Instructor Mode"])
    
    if mode == "Student Mode":
        render_student_mode()
    else:
        render_instructor_mode()
    
    st.stop()

elif page == "Rule Manager":
    st.title("Rule Manager")
    st.markdown("Manage and view existing validation rules")
    
    # List existing rule files
    rules_dir = Path("rules")
    if rules_dir.exists():
        rule_files = list(rules_dir.glob("*.json"))
        
        if rule_files:
            st.subheader("Available Rule Files")
            
            for rule_file in rule_files:
                with st.expander(f"{rule_file.name}"):
                    try:
                        with open(rule_file, 'r', encoding='utf-8') as f:
                            rules_data = json.load(f)
                        
                        rules = rules_data.get("rules", [])
                        st.write(f"**Total Rules:** {len(rules)}")
                        st.write(f"**Total Points:** {sum(rule.get('points', 0) for rule in rules)}")
                        
                        # Show rule types
                        rule_types = {}
                        for rule in rules:
                            rule_type = rule.get('type', 'unknown')
                            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
                        
                        st.write("**Rule Types:**")
                        for rule_type, count in rule_types.items():
                            st.write(f"- {rule_type}: {count}")
                        
                        # Show rules preview
                        if st.checkbox(f"Show Rules Details", key=f"show_{rule_file.name}"):
                            st.json(rules_data)
                    
                    except Exception as e:
                        st.error(f"Error reading {rule_file.name}: {e}")
        else:
            st.info("No rule files found. Create some rules using the Rule Builder.")
    else:
        st.info("Rules directory not found. Create some rules using the Rule Builder.")
    
    st.stop()

# Main validator page
st.title("Automated Flask Project Validator")
st.markdown(
    """
    Validate Flask-based student submissions with runtime checks, CRUD tests, DB schema analysis,  
    structural HTML/boilerplate validation, and **Playwright UI testing**.
    """
)

col_left, col_right = st.columns([1, 1.8])

with col_left:
    st.header("Upload Project")
    uploaded_file = st.file_uploader("Upload Flask project (.zip)", type=["zip"])
    
    # Rule selection
    st.subheader("Validation Rules")
    rules_dir = Path("rules")
    
    if rules_dir.exists():
        rule_files = list(rules_dir.glob("*.json"))
        
        if rule_files:
            rule_file_options = ["Default Rules"] + [f.name for f in rule_files]
            selected_rule_file = st.selectbox(
                "Select Rule Set",
                options=rule_file_options,
                help="Choose which validation rules to use"
            )
            
            if selected_rule_file == "Default Rules":
                rules_file_path = None
            else:
                rules_file_path = str(rules_dir / selected_rule_file)
        else:
            rules_file_path = None
            st.info("No custom rules found. Using default rules.")
    else:
        rules_file_path = None
        st.info("Rules directory not found. Using default rules.")
    
    run_validation = st.button("Run Validation", use_container_width=True)

    st.markdown("---")
    result_placeholder = st.empty()
    st.markdown("---")

with col_right:
    st.header("Validation Logs")
    log_placeholder = st.empty()

    log_placeholder.markdown(
        """
        <div style="
            border:1px solid #444;
            border-radius:10px;
            background-color:#000;
            color:#0f0;
            padding:10px;
            height:550px;
            overflow-y:scroll;
            font-family:monospace;
            white-space:pre-wrap;
            font-size:13px;">
        Logs will appear here as the validation runs...
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_logs(log_path: str):
    """Render validation logs in a scrollable, color-coded block."""
    if not os.path.exists(log_path):
        st.warning("Log file not found.")
        return

    with open(log_path, "r", encoding="utf-8") as logf:
        lines = logf.readlines()

    styled_lines = []
    for line in lines:
        if "[CHECK] PASS" in line:
            color = "#00ff00"
        elif "[CHECK] FAIL" in line or "[ERROR]" in line:
            color = "#ff4d4d" 
        elif "[WARN]" in line:
            color = "#ffaa00" 
        elif "[INFO]" in line:
            color = "#00bfff" 
        elif "[APP]" in line:
            color = "#9999ff"
        else:
            color = "#cccccc"

        safe_line = line.replace("<", "&lt;").replace(">", "&gt;")
        styled_lines.append(f"<span style='color:{color}'>{safe_line}</span>")

    return f"""
        <div style="
            border:1px solid #444;
            border-radius:10px;
            background-color:#000;
            color:#ccc;
            padding:10px;
            height:550px;
            overflow-y:scroll;
            font-family:monospace;
            white-space:pre-wrap;
            line-height:1.4;
            font-size:13px;">
            {''.join(styled_lines)}
        </div>
    """

if run_validation and uploaded_file:
    with st.spinner("Running validation... this may take a moment ⏳"):
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, uploaded_file.name)

        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        result = run_flexible_validation(temp_dir, rules_file=rules_file_path)

        if os.path.exists(result["log_file"]):
            log_html = render_logs(result["log_file"])
            log_placeholder.markdown(log_html, unsafe_allow_html=True)
        else:
            log_placeholder.markdown(
                "<div style='color:#999;'>No log file found after validation.</div>",
                unsafe_allow_html=True,
            )

        success = result["success"]
        summary_color = "" if success else ""
        st.success(f"{summary_color} Validation {'Completed Successfully' if success else 'Failed'}")

        # Display UI test results if available
        ui_tests = result.get("ui_tests", [])
        if ui_tests:
            st.subheader("UI Test Results")
            
            # Calculate UI test statistics
            total_ui_tests = len(ui_tests)
            passed_ui_tests = sum(1 for test in ui_tests if test.get("status") == "PASS")
            failed_ui_tests = total_ui_tests - passed_ui_tests
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("UI Tests", total_ui_tests)
            with col2:
                st.metric("Passed", passed_ui_tests)
            with col3:
                st.metric("Failed", failed_ui_tests)
            
            # Show UI test details with screenshots
            with st.expander("View UI Test Details"):
                for i, test in enumerate(ui_tests):
                    status = test.get("status", "UNKNOWN")
                    name = test.get("name", f"Test {i+1}")
                    route = test.get("route", "")
                    duration = test.get("duration", 0.0)
                    error = test.get("error", "")
                    screenshot = test.get("screenshot", "")
                    points = test.get("points", 0)
                    
                    status_color = "🟢" if status == "PASS" else "🔴"
                    st.write(f"{status_color} **{name}** - Route: {route} - Duration: {duration:.2f}s - Points: {points}")
                    
                    if error:
                        st.error(f"Error: {error}")
                    
                    # Display screenshot if available
                    if screenshot and os.path.exists(screenshot):
                        try:
                            st.image(screenshot, caption=f"Screenshot: {name}", use_column_width=True)
                        except Exception as e:
                            st.warning(f"Could not display screenshot: {e}")
                    elif screenshot:
                        st.warning(f"Screenshot not found: {screenshot}")
                    
                    st.divider()

        result_placeholder.markdown(
            f"""
            <div style="background-color:#111;border:1px solid #333;border-radius:8px;padding:12px;">
            <b>Log File:</b> {result['log_file']}<br>
            <b>JSON Summary:</b> {result['json_file']}<br>
            <b>Errors:</b> {len(result['errors'])}<br>
            <b>Warnings:</b> {len(result['warnings'])}<br>
            <b>UI Tests:</b> {len(ui_tests)}<br>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif run_validation:
    st.error("Please upload a valid project ZIP file before running validation.")
