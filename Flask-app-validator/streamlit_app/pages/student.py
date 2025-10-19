import streamlit as st
import tempfile
import os
import zipfile
from pathlib import Path
import sys

# Add validator directory to path
project_root = Path(__file__).resolve().parents[2]
validator_dir = project_root / "validator"
sys.path.insert(0, str(validator_dir))

try:
    from task_validator import TaskValidator
except ImportError:
    st.error("TaskValidator not found. Please ensure the validator module is properly configured.")
    st.stop()

st.set_page_config(page_title="Student Portal", layout="wide")

# Custom CSS for student page styling
st.markdown("""
<style>
    /* Custom button styling for VALIDATE and SUBMIT buttons */
    .stButton > button {
        background-color: #20B2AA !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        font-size: 14px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #1A9B94 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(32, 178, 170, 0.3) !important;
    }
    
    /* Upload button styling */
    .stButton > button[kind="primary"] {
        background-color: #6c757d !important;
        color: white !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #5a6268 !important;
    }
    
    /* File uploader styling */
    .stFileUploader > div > div > div {
        border: 2px dashed #e0e0e0 !important;
        border-radius: 10px !important;
        background-color: #fafafa !important;
    }
    
    .stFileUploader > div > div > div:hover {
        border-color: #20B2AA !important;
        background-color: #f0f8f7 !important;
    }
    
    /* Task header styling */
    .task-header {
        background: linear-gradient(135deg, #f0f0f0 0%, #e8e8e8 100%) !important;
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
        text-align: center !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    /* Requirements list styling */
    .requirements-list {
        background-color: #f8f9fa !important;
        border-left: 4px solid #20B2AA !important;
        padding: 15px !important;
        margin: 10px 0 !important;
        border-radius: 0 8px 8px 0 !important;
    }
    
    /* Test cases styling */
    .test-cases {
        background-color: #f8f9fa !important;
        border: 1px solid #e9ecef !important;
        border-radius: 8px !important;
        padding: 15px !important;
    }
    
    /* Section containers */
    .section-container {
        border: 2px solid #e0e0e0 !important;
        border-radius: 15px !important;
        padding: 20px !important;
        background-color: #fafafa !important;
        margin-bottom: 20px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
    }
    
    /* Progress metrics styling */
    .metric-container {
        background-color: #f8f9fa !important;
        border-radius: 10px !important;
        padding: 10px !important;
        text-align: center !important;
    }
    
    /* Back button styling */
    .back-button {
        background-color: #6c757d !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        margin-bottom: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Back to main page button
if st.button("← Back to Main Page", type="secondary"):
    st.switch_page("../app.py")

st.title("🎓 Student Task Validator")

# Student ID input
student_id = st.text_input("Enter Student ID:", value="student_001", help="Enter your unique student identifier")

# Initialize task validator
task_validator = TaskValidator()

# Get student progress
progress = task_validator.get_student_progress(student_id)

# Display progress summary
st.markdown("### 📊 Your Progress")
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
    st.stop()

# Find current task (first unlocked task that's not completed)
current_task = None
for task in all_tasks:
    task_id = task["id"]
    required_tasks = task.get("unlock_condition", {}).get("required_tasks", [])
    is_unlocked = all(rt in progress["completed_tasks"] for rt in required_tasks)
    
    if is_unlocked and task_id not in progress["completed_tasks"]:
        current_task = task
        break

# If no current task, show the first available task or last completed task
if not current_task:
    if progress["completed_tasks"]:
        # Show the last completed task
        last_completed = progress["completed_tasks"][-1]
        current_task = next((task for task in all_tasks if task["id"] == last_completed), all_tasks[0])
    else:
        current_task = all_tasks[0]

if current_task:
    # Two-column layout matching the image
    col_left, col_right = st.columns([1, 1.1])
    
    with col_left:
        # Task Information Section
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        
        # Task Header
        st.markdown(f"""
        <div class="task-header">
            <h2 style="margin: 0; color: #333;">Task {current_task['id']} : {current_task['name']}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Requirements Section
        st.markdown("**Requirements:**")
        
        # Get requirements from task description or create sample requirements
        requirements = [
            "Create a login page with username and password fields",
            "Implement form validation for empty fields",
            "Add proper error handling and user feedback",
            "Style the page with CSS for better user experience",
            "Ensure the page is responsive on different screen sizes"
        ]
        
        st.markdown('<div class="requirements-list">', unsafe_allow_html=True)
        for i, req in enumerate(requirements, 1):
            st.markdown(f"{i}. {req}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_right:
        # Upload Section
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        
        st.markdown("**Upload Your project as ZIP file**")
        st.markdown("*Note: File must be less than 1 MB*")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose file",
            type=["zip"],
            key=f"upload_task_{current_task['id']}",
            label_visibility="collapsed"
        )
        
        # Upload button
        if st.button("Upload", key=f"upload_btn_{current_task['id']}", type="primary"):
            if uploaded_file:
                st.success("File uploaded successfully!")
            else:
                st.warning("Please select a file first.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Action Buttons Section
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("VALIDATE", key=f"validate_btn_{current_task['id']}", 
                       type="primary", use_container_width=True):
                if uploaded_file:
                    with st.spinner(f"Validating Task {current_task['id']}..."):
                        # Save uploaded file temporarily
                        temp_path = tempfile.mktemp(suffix=".zip")
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        
                        # Run validation
                        result = task_validator.validate_task(current_task['id'], temp_path, student_id)
                        
                        # Display results
                        if result["success"]:
                            st.success(f"Task {current_task['id']} validation completed successfully!")
                            
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
                            st.error(f"Task {current_task['id']} validation failed: {result.get('error', 'Unknown error')}")
                        
                        # Clean up temp file
                        try:
                            os.unlink(temp_path)
                        except Exception:
                            pass
                else:
                    st.warning("Please upload a file first.")
        
        with col_btn2:
            if st.button("SUBMIT", key=f"submit_btn_{current_task['id']}", 
                       type="primary", use_container_width=True):
                if uploaded_file:
                    st.success("Task submitted successfully!")
                else:
                    st.warning("Please upload a file first.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Test Cases Section
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        
        st.markdown("**Test cases:**")
        
        # Sample test cases
        test_cases = [
            "Verify login form displays correctly with all required fields",
            "Test form validation for empty username and password fields",
            "Check error message display for invalid credentials",
            "Validate successful login redirects to dashboard page",
            "Ensure responsive design works on mobile devices"
        ]
        
        st.markdown('<div class="test-cases">', unsafe_allow_html=True)
        for i, test_case in enumerate(test_cases, 1):
            st.markdown(f"**Test Case {i}:** {test_case}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# Show other tasks in expandable sections
st.markdown("---")
st.subheader("📋 All Tasks")

for task in all_tasks:
    if task == current_task:
        continue
        
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
