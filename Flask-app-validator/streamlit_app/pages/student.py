import streamlit as st
import tempfile
import os
import zipfile
import json
from pathlib import Path
import sys

# --- Setup paths ---
project_root = Path(__file__).resolve().parents[2]
validator_dir = project_root / "validator"
projects_dir = project_root / "projects"  # <-- folder containing creator's JSON configs
sys.path.insert(0, str(validator_dir))

try:
    from task_validator import TaskValidator
except ImportError:
    st.error("TaskValidator not found. Please ensure the validator module is properly configured.")
    st.stop()

st.set_page_config(page_title="Student Portal", layout="wide")

# --- Header ---
st.title("Student Task Validator")

# Add refresh and clear cache buttons
col_title, col_refresh, col_clear = st.columns([0.6, 0.2, 0.2])
with col_refresh:
    if st.button("🔄 Refresh", help="Refresh available projects"):
        st.rerun()
with col_clear:
    if st.button("🗑️ Clear Cache", help="Clear student progress cache"):
        # Clear all student progress files
        logs_dir = Path("Logs")
        if logs_dir.exists():
            for student_dir in logs_dir.iterdir():
                if student_dir.is_dir() and student_dir.name.startswith(("student_", "test_")):
                    progress_file = student_dir / "progress.json"
                    if progress_file.exists():
                        progress_file.unlink()
                        st.success(f"✅ Cleared cache for {student_dir.name}")
            st.rerun()

# --- Load available project JSON files ---
project_files = list(projects_dir.glob("*_configuration.json"))

if not project_files:
    st.warning("No projects found. Please contact your instructor.")
    st.info("💡 Instructors can create projects using the Creator Portal.")
    if st.button("🔄 Refresh Projects"):
        st.rerun()
    st.stop()

# Create mapping for dropdown
project_names = [p.stem.replace("_", " ").title() for p in project_files]
project_map = dict(zip(project_names, project_files))

# --- Project selection ---
selected_project_name = st.selectbox("Select Project", project_names)
selected_project_path = project_map[selected_project_name]

with open(selected_project_path, "r", encoding="utf-8") as f:
    project_data = json.load(f)

st.subheader(f"📘 {project_data.get('project', 'Unnamed Project')}")
st.caption(project_data.get("description", ""))

# --- Student ID ---
student_id = st.text_input("Enter Student ID:", value="student_001", help="Enter your unique student identifier")

# --- Initialize validator ---
task_validator = TaskValidator()

# --- Load tasks from selected project ---
all_tasks = project_data.get("tasks", [])
if not all_tasks:
    st.warning("No tasks defined in this project.")
    st.stop()

# --- Load student progress ---
progress = task_validator.get_student_progress(student_id)

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

# --- Determine current unlocked task ---
current_task = None
for task in all_tasks:
    task_id = task["id"]
    required_tasks = task.get("unlock_condition", {}).get("required_tasks", [])
    is_unlocked = all(rt in progress["completed_tasks"] for rt in required_tasks)
    if is_unlocked and task_id not in progress["completed_tasks"]:
        current_task = task
        break

if not current_task:
    if progress["completed_tasks"]:
        last_completed = progress["completed_tasks"][-1]
        current_task = next((t for t in all_tasks if t["id"] == last_completed), all_tasks[0])
    else:
        current_task = all_tasks[0]

# --- Current Task UI ---
if current_task:
    col_left, col_right = st.columns([1, 1.1])

    with col_left:
        # Check if current task is completed
        is_current_completed = current_task["id"] in progress["completed_tasks"]
        status_icon = "✅" if is_current_completed else "🎯"
        
        st.markdown(f"### {status_icon} Task {current_task['id']}: {current_task['name']}")
        st.markdown(f"**Description:** {current_task['description']}")
        
        # Show completion status
        if is_current_completed:
            st.success("✅ This task has been completed!")
            # Show last validation results
            task_logs_dir = Path("Logs") / student_id / f"task_{current_task['id']}"
            if task_logs_dir.exists():
                json_files = list(task_logs_dir.glob("*.json"))
                if json_files:
                    latest_result = json_files[-1]
                    try:
                        with open(latest_result, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                        st.write(f"**Last Score:** {result_data.get('total_score', 0)} / {result_data.get('max_score', 0)}")
                        
                        # Show validation breakdown
                        static_val = result_data.get('static_validation', {})
                        playwright_val = result_data.get('playwright_validation', {})
                        
                        col_static, col_playwright = st.columns(2)
                        with col_static:
                            if static_val.get('success'):
                                st.success("✅ Static validation passed")
                            else:
                                st.error("❌ Static validation failed")
                        
                        with col_playwright:
                            if playwright_val.get('success'):
                                st.success("🎭 Playwright tests passed")
                            elif playwright_val.get('message'):
                                st.info(f"🎭 {playwright_val['message']}")
                            else:
                                st.warning("🎭 Playwright tests had issues")
                    except:
                        st.write("📊 Task completed (details unavailable)")
        else:
            st.info("🎯 Complete this task to unlock the next one")

        st.markdown("**Requirements:**")
        validation = current_task.get("validation_rules", {})
        must_have_elements = validation.get("mustHaveElements", [])
        must_have_classes = validation.get("mustHaveClasses", [])
        must_have_inputs = validation.get("mustHaveInputs", [])
        must_have_content = validation.get("mustHaveContent", [])

        if must_have_elements:
            st.write(f"- Elements: {', '.join(must_have_elements)}")
        if must_have_classes:
            st.write(f"- Classes: {', '.join(must_have_classes)}")
        if must_have_inputs:
            st.write(f"- Inputs: {', '.join(must_have_inputs)}")
        if must_have_content:
            st.write(f"- Content: {', '.join(must_have_content)}")

        st.info(f"Total Points: {validation.get('points', 0)}")

    with col_right:
        st.markdown("**Upload your project ZIP file**")
        uploaded_file = st.file_uploader("Upload ZIP", type=["zip"], key=f"upload_task_{current_task['id']}")

        if uploaded_file:
            st.success("File ready for validation.")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Validate", key=f"validate_{current_task['id']}"):
                if not uploaded_file:
                    st.warning("Please upload a ZIP first.")
                else:
                    with st.spinner("Validating your submission..."):
                        tmp = tempfile.mktemp(suffix=".zip")
                        with open(tmp, "wb") as f:
                            f.write(uploaded_file.getvalue())

                        result = task_validator.validate_task(current_task["id"], tmp, student_id)
                        if result.get("success"):
                            st.success(f"✅ Validation completed! Score: {result['total_score']} / {result['max_score']}")
                            task_validator.update_student_progress(student_id, result)
                            st.rerun()
                        else:
                            st.error(f"❌ Validation failed: {result.get('error', 'Unknown error')}")

        with col_b:
            if st.button("Submit", key=f"submit_{current_task['id']}"):
                st.success("Task submitted successfully!")

st.divider()
st.subheader("📋 All Tasks")

# --- Display all tasks below ---
for t in all_tasks:
    if t == current_task:
        continue
    
    # Check if task is completed
    is_completed = t["id"] in progress["completed_tasks"]
    task_status = "✅ Completed" if is_completed else "⏳ Pending"
    
    with st.expander(f"Task {t['id']}: {t['name']} - {task_status}"):
        # Task status and verification info
        col_status, col_verify = st.columns([0.7, 0.3])
        
        with col_status:
            st.write(f"**Description:** {t['description']}")
            st.write(f"**Points:** {t.get('validation_rules', {}).get('points', 0)}")
            
            if is_completed:
                st.success("✅ Task completed successfully!")
                # Show completion details if available
                task_logs_dir = Path("Logs") / student_id / f"task_{t['id']}"
                if task_logs_dir.exists():
                    json_files = list(task_logs_dir.glob("*.json"))
                    if json_files:
                        latest_result = json_files[-1]  # Get most recent result
                        try:
                            with open(latest_result, 'r', encoding='utf-8') as f:
                                result_data = json.load(f)
                            st.write(f"**Last Score:** {result_data.get('total_score', 0)} / {result_data.get('max_score', 0)}")
                            
                            # Show validation details
                            static_val = result_data.get('static_validation', {})
                            playwright_val = result_data.get('playwright_validation', {})
                            
                            if static_val.get('success'):
                                st.write("✅ Static validation passed")
                            if playwright_val.get('success'):
                                st.write("✅ Playwright validation passed")
                            elif playwright_val.get('message'):
                                st.write(f"ℹ️ Playwright: {playwright_val['message']}")
                        except Exception as e:
                            st.write("📊 Validation completed (details unavailable)")
        
        with col_verify:
            if is_completed:
                st.markdown("### Verification Status")
                st.success("✅ Verified")
                
                # Show verification details
                task_logs_dir = Path("Logs") / student_id / f"task_{t['id']}"
                if task_logs_dir.exists():
                    json_files = list(task_logs_dir.glob("*.json"))
                    if json_files:
                        latest_result = json_files[-1]
                        try:
                            with open(latest_result, 'r', encoding='utf-8') as f:
                                result_data = json.load(f)
                            
                            # Show screenshots if available
                            screenshots = result_data.get('screenshots', [])
                            if screenshots:
                                st.write("📸 Screenshots captured:")
                                for i, screenshot in enumerate(screenshots[:3]):  # Show first 3
                                    if Path(screenshot).exists():
                                        st.image(screenshot, caption=f"Screenshot {i+1}", width=200)
                            
                            # Show validation timestamp
                            timestamp = result_data.get('timestamp', '')
                            if timestamp:
                                st.caption(f"Verified: {timestamp[:19]}")
                                
                        except Exception as e:
                            st.write("📊 Verification completed")
            else:
                st.markdown("### Verification Status")
                st.info("⏳ Not verified")
                st.caption("Complete the task to see verification details")

        st.write("**Required Files:**")
        for rf in t.get("required_files", []):
            st.write(f"- {rf}")

        rules = t.get("validation_rules", {})
        if rules:
            st.write("**Validation Rules:**")
            if "mustHaveElements" in rules:
                st.write(f"Elements: {', '.join(rules['mustHaveElements'])}")
            if "mustHaveClasses" in rules:
                st.write(f"Classes: {', '.join(rules['mustHaveClasses'])}")
            if "mustHaveInputs" in rules:
                st.write(f"Inputs: {', '.join(rules['mustHaveInputs'])}")
            if "mustHaveContent" in rules:
                st.write(f"Content: {', '.join(rules['mustHaveContent'])}")

        pt = t.get("playwright_test", {})
        if pt:
            st.write("**Playwright Test:**")
            st.write(f"- Route: {pt.get('route', '/')}")
            st.write(f"- Points: {pt.get('points', 0)}")
            
            # Show Playwright validation status
            if is_completed:
                task_logs_dir = Path("Logs") / student_id / f"task_{t['id']}"
                if task_logs_dir.exists():
                    json_files = list(task_logs_dir.glob("*.json"))
                    if json_files:
                        latest_result = json_files[-1]
                        try:
                            with open(latest_result, 'r', encoding='utf-8') as f:
                                result_data = json.load(f)
                            playwright_val = result_data.get('playwright_validation', {})
                            
                            if playwright_val.get('success'):
                                st.success("🎭 Playwright tests passed")
                            elif playwright_val.get('message'):
                                st.info(f"🎭 Playwright: {playwright_val['message']}")
                            else:
                                st.warning("🎭 Playwright tests had issues")
                        except:
                            pass
