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
projects_dir = project_root / "projects"
sys.path.insert(0, str(validator_dir))

try:
    if 'task_validator' in sys.modules:
        del sys.modules['task_validator']
    
    from task_validator import TaskValidator
    
except ImportError as e:
    st.error(f"TaskValidator import failed: {e}")
    st.error("Please ensure the validator module is properly configured.")
    st.stop()

st.set_page_config(page_title="Student Portal", layout="wide")

# --- Header ---
st.title("Student Task Validator")

# Add refresh and clear cache buttons
col_title, col_refresh, col_clear = st.columns([0.6, 0.2, 0.2])
with col_refresh:
    if st.button("Refresh", help="Refresh available projects"):
        st.rerun()
with col_clear:
    if st.button("Clear Cache", help="Clear student progress cache"):
        # Clear all student progress files
        logs_dir = Path("Logs")
        if logs_dir.exists():
            for student_dir in logs_dir.iterdir():
                if student_dir.is_dir() and student_dir.name.startswith(("student_", "test_")):
                    progress_file = student_dir / "progress.json"
                    if progress_file.exists():
                        progress_file.unlink()
                        st.success(f"Cleared cache for {student_dir.name}")
            st.rerun()

# --- Load available project JSON files ---
project_files = list(projects_dir.glob("*_configuration.json"))

if not project_files:
    st.warning("No projects found. Please contact your instructor.")
    st.info("Instructors can create projects using the Creator Portal.")
    if st.button("Refresh Projects"):
        st.rerun()
    st.stop()

# Create mapping for dropdown
project_names = [p.stem.replace("_configuration", "").replace("_", " ").title() for p in project_files]
project_map = dict(zip(project_names, project_files))

# --- Project selection ---
selected_project_name = st.selectbox("Select Project", project_names)
selected_project_path = project_map[selected_project_name]

with open(selected_project_path, "r", encoding="utf-8") as f:
    project_data = json.load(f)

st.subheader(f"{project_data.get('project', 'Unnamed Project')}")
st.caption(project_data.get("description", ""))

# --- Student ID ---
student_id = st.text_input("Enter Student ID:", value="student_001", help="Enter your unique student identifier")

# --- Initialize validator ---
task_validator = TaskValidator()

# Ensure the validator uses the selected project's configuration JSON
try:
    task_validator.load_project_config(str(selected_project_path))
except Exception as e:
    st.error(f"Failed to load project configuration: {e}")

# --- Load tasks from selected project ---
all_tasks = project_data.get("tasks", [])
if not all_tasks:
    st.warning("No tasks defined in this project.")
    st.stop()

# --- Load student progress for this specific project ---
project_id = project_data.get("project", "unknown").replace(" ", "_").lower()

# Debug: Check method signature
import inspect
try:
    sig = inspect.signature(task_validator.get_student_progress)
    st.write(f"Method signature: {sig}")
except Exception as e:
    st.write(f"Error getting signature: {e}")

progress = task_validator.get_student_progress(student_id, project_id)

st.markdown("### Your Progress")
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

# Check if all tasks are completed
all_tasks_completed = len(progress["completed_tasks"]) == len(all_tasks)
if all_tasks_completed:
    st.success("Congratulations! You have completed all tasks!")
    st.info("Scroll down to see all completed tasks.")
    # Don't show current task section when all tasks are completed
    current_task = None

# --- Current Task UI ---
if current_task and not all_tasks_completed:
    col_left, col_right = st.columns([1, 1.1])

    with col_left:
        # Check if current task is completed
        is_current_completed = current_task["id"] in progress["completed_tasks"]
        status_icon = "Completed" if is_current_completed else "In Progress"
        
        st.markdown(f"### {status_icon} Task {current_task['id']}: {current_task['name']}")
        st.markdown(f"**Description:** {current_task['description']}")
        
        # Show completion status
        if is_current_completed:
            st.success("This task has been completed!")
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
                                st.success("Static validation passed")
                            else:
                                st.error("Static validation failed")
                        
                        with col_playwright:
                            if playwright_val.get('success'):
                                task_name = current_task.get('name', f'Task {current_task.get("id", "?")}')
                                st.success(f"{task_name} passed")
                            elif playwright_val.get('message'):
                                # Extract the actual error from the message
                                error_msg = playwright_val['message']
                                if "UI test failed:" in error_msg:
                                    error_msg = error_msg.replace("UI test failed: ", "")
                                st.error(f"Task failed: {error_msg}")
                            else:
                                st.warning("Task validation had issues")
                    except:
                        st.write("Task completed (details unavailable)")
        else:
            st.info("Complete this task to unlock the next one")

        st.markdown("**Requirements:**")
        validation = current_task.get("validation_rules", {})
        
        if isinstance(validation, list):
            validation = {}
        
        must_have_elements = validation.get("mustHaveElements", [])
        must_have_classes = validation.get("mustHaveClasses", [])
        must_have_inputs = validation.get("mustHaveInputs", [])
        must_have_content = validation.get("mustHaveContent", [])

        if must_have_elements:
            # Handle case where elements might be dicts or strings
            element_strings = []
            for elem in must_have_elements:
                if isinstance(elem, dict):
                    element_strings.append(f"{elem.get('tag', 'unknown')} - {elem.get('class', 'no class')}")
                else:
                    element_strings.append(str(elem))
            st.write(f"- Elements: {', '.join(element_strings)}")
        if must_have_classes:
            class_strings = []
            for cls in must_have_classes:
                if isinstance(cls, dict):
                    class_strings.append(f"{cls.get('element', '')}.{cls.get('class', '')}")
                else:
                    class_strings.append(str(cls))
            st.write(f"- Classes: {', '.join(class_strings)}")
        if must_have_inputs:
            # Handle case where inputs might be dicts or strings
            input_strings = []
            for inp in must_have_inputs:
                if isinstance(inp, dict):
                    input_strings.append(f"{inp.get('type', 'unknown')} - {inp.get('name', 'no name')}")
                else:
                    input_strings.append(str(inp))
            st.write(f"- Inputs: {', '.join(input_strings)}")
        if must_have_content:
            # Handle case where content might be dicts or strings
            content_strings = []
            for content in must_have_content:
                if isinstance(content, dict):
                    content_strings.append(f"{content.get('text', 'no text')} - {content.get('selector', 'no selector')}")
                else:
                    content_strings.append(str(content))
            st.write(f"- Content: {', '.join(content_strings)}")

        st.info(f"Total Points: {validation.get('points', 0)}")

    with col_right:
        st.markdown("**Upload your project ZIP file**")
        uploaded_file = st.file_uploader("Upload ZIP", type=["zip"], key=f"upload_task_{current_task['id']}")

        if uploaded_file:
            st.success("File ready for validation.")

        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_a:
            if st.button("Validate", key=f"validate_{current_task['id']}", help="Validate your current upload"):
                if not uploaded_file:
                    st.warning("Please upload a ZIP first.")
                else:
                    with st.spinner("Validating your submission..."):
                        tmp = tempfile.mktemp(suffix=".zip")
                        with open(tmp, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        
                        try:
                            task_validator.load_project_config(str(selected_project_path))
                        except Exception:
                            pass
                        
                        result = task_validator.validate_task(current_task["id"], tmp, student_id)
                        if result.get("success"):
                            st.success(f"Validation completed! Score: {result['total_score']} / {result['max_score']}")
                            task_validator.update_student_progress(student_id, result, project_id)
                            st.rerun()
                        else:
                            error_msg = result.get('message') or result.get('error') or 'Unknown error'
                            st.error(f"Validation failed: {error_msg}")

        with col_b:
            if st.button("Submit", key=f"submit_{current_task['id']}", help="Submit your current upload"):
                if not uploaded_file:
                    st.warning("Please upload a ZIP first.")
                else:
                    st.success("Task submitted successfully!")

        with col_c:
            if st.button("Re-upload", key=f"reupload_{current_task['id']}", help="Upload a new ZIP file"):
                st.rerun()

st.divider()
st.subheader("All Tasks")

for t in all_tasks:
    if t == current_task:
        continue
    
    is_completed = t["id"] in progress["completed_tasks"]
    task_status = "Completed" if is_completed else "Pending"
    
    with st.expander(f"Task {t['id']}: {t['name']} - {task_status}"):
        col_status, col_verify = st.columns([0.7, 0.3])
        
        with col_status:
            st.write(f"**Description:** {t['description']}")
            validation_rules = t.get('validation_rules', {})
            if isinstance(validation_rules, list):
                validation_rules = {}
            st.write(f"**Points:** {validation_rules.get('points', 0)}")
            
            if is_completed:
                st.success("Task completed successfully!")
                task_logs_dir = Path("Logs") / student_id / f"task_{t['id']}"
                if task_logs_dir.exists():
                    json_files = list(task_logs_dir.glob("*.json"))
                    if json_files:
                        latest_result = json_files[-1]  # Get most recent result
                        try:
                            with open(latest_result, 'r', encoding='utf-8') as f:
                                result_data = json.load(f)
                            st.write(f"**Last Score:** {result_data.get('total_score', 0)} / {result_data.get('max_score', 0)}")
                            
                            static_val = result_data.get('static_validation', {})
                            playwright_val = result_data.get('playwright_validation', {})
                            
                            if static_val.get('success'):
                                st.write("Static validation passed")
                            if playwright_val.get('success'):
                                task_name = t.get('name', f'Task {t.get("id", "?")}')
                                st.write(f"{task_name} passed")
                            elif playwright_val.get('message'):
                                error_msg = playwright_val['message']
                                if "UI test failed:" in error_msg:
                                    error_msg = error_msg.replace("UI test failed: ", "")
                                st.write(f"Task failed: {error_msg}")
                        except Exception as e:
                            st.write("Validation completed (details unavailable)")
        
        with col_verify:
            if is_completed:
                st.markdown("### Verification Status")
                st.success("Verified")
                
                # Add re-upload option for completed tasks
                st.markdown("### Re-attempt Task")
                if st.button("Re-upload & Validate", key=f"retry_{t['id']}", help="Upload a new version and validate again"):
                    st.info("Please upload your updated project ZIP file below.")
                    st.session_state[f"retry_task_{t['id']}"] = True
                
                task_logs_dir = Path("Logs") / student_id / f"task_{t['id']}"
                if task_logs_dir.exists():
                    json_files = list(task_logs_dir.glob("*.json"))
                    if json_files:
                        latest_result = json_files[-1]
                        try:
                            with open(latest_result, 'r', encoding='utf-8') as f:
                                result_data = json.load(f)
                            
                            screenshots = result_data.get('screenshots', [])
                            if screenshots:
                                st.write("Screenshots captured:")
                                
                                # Smart screenshot selection - prefer final.png over initial.png for same page
                                screenshot_groups = {}
                                for screenshot in screenshots:
                                    screenshot_path = Path(screenshot).resolve()
                                    if screenshot_path.exists():
                                        filename = screenshot_path.name
                                        # Group screenshots by base name (without initial/final prefix)
                                        base_name = filename.replace('initial.png', '').replace('final.png', '').replace('screenshot_', '')
                                        if base_name not in screenshot_groups:
                                            screenshot_groups[base_name] = []
                                        screenshot_groups[base_name].append(screenshot)
                                
                                # Select best screenshot from each group (prefer final.png)
                                unique_screenshots = []
                                for group_screenshots in screenshot_groups.values():
                                    # Sort to prefer final.png over initial.png
                                    group_screenshots.sort(key=lambda x: (
                                        0 if 'final.png' in x else 1,  # final.png first
                                        x  # then alphabetically
                                    ))
                                    unique_screenshots.append(group_screenshots[0])  # Take the best one
                                
                                # Display unique screenshots (limit to 3 to avoid UI clutter)
                                for i, screenshot in enumerate(unique_screenshots[:3]):
                                    screenshot_path = Path(screenshot).resolve()
                                    try:
                                        screenshot_name = f"Screenshot {i+1}"
                                        
                                        st.markdown(f"**{screenshot_name}**")
                                        
                                        with open(screenshot_path, "rb") as img_file:
                                            img_data = img_file.read()
                                        
                                        # Determine screenshot type for better caption
                                        screenshot_type = "Final state" if 'final.png' in screenshot_path.name else "Initial state" if 'initial.png' in screenshot_path.name else "Screenshot"
                                        st.image(img_data, caption=f"{screenshot_type} - Click to view full size", width='stretch')
                                        
                                        st.download_button(
                                            label="📥 Download Image",
                                            data=img_data,
                                            file_name=screenshot_path.name,
                                            mime="image/png",
                                            key=f"download_task_{t['id']}_screenshot_{i}"
                                        )
                                        st.caption(f"File: {screenshot_path.name}")
                                    except Exception as e:
                                        st.write(f"Could not display screenshot {i+1}: {str(e)}")
                                
                                # Show count if there were more screenshots
                                if len(unique_screenshots) > 3:
                                    st.caption(f"... and {len(unique_screenshots) - 3} more screenshots")
                                
                                # Add note about screenshot selection
                                if len(screenshots) > len(unique_screenshots):
                                    st.caption("💡 Showing final state screenshots (preferred over initial state)")
                            
                            # Show validation timestamp
                            timestamp = result_data.get('timestamp', '')
                            if timestamp:
                                st.caption(f"Verified: {timestamp[:19]}")
                                
                        except Exception as e:
                            st.write("Verification completed")
            else:
                st.markdown("### Verification Status")
                st.info("Not verified")
                st.caption("Complete the task to see verification details")

        st.write("**Required Files:**")
        for rf in t.get("required_files", []):
            st.write(f"- {rf}")

        rules = t.get("validation_rules", {})
        if isinstance(rules, list):
            rules = {}
        if rules:
            st.write("**Validation Rules:**")
            if "mustHaveElements" in rules:
                st.write(f"Elements: {', '.join(rules['mustHaveElements'])}")
            if "mustHaveClasses" in rules:
                classes = rules['mustHaveClasses']
                if isinstance(classes, list) and classes:
                    # Handle both string and dict formats
                    class_strings = []
                    for cls in classes:
                        if isinstance(cls, dict):
                            class_strings.append(f"{cls.get('element', '')}.{cls.get('class', '')}")
                        else:
                            class_strings.append(str(cls))
                    st.write(f"Classes: {', '.join(class_strings)}")
            if "mustHaveInputs" in rules:
                st.write(f"Inputs: {', '.join(rules['mustHaveInputs'])}")
            if "mustHaveContent" in rules:
                st.write(f"Content: {', '.join(rules['mustHaveContent'])}")

        pt = t.get("playwright_test", {})
        if pt:
            st.write("**UI Test:**")
            st.write(f"- Route: {pt.get('route', '/')}")
            st.write(f"- Points: {pt.get('points', 0)}")
            
            # Show UI test validation status
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
                                task_name = t.get('name', f'Task {t.get("id", "?")}')
                                st.success(f"{task_name} passed")
                            elif playwright_val.get('message'):
                                # Extract the actual error from the message
                                error_msg = playwright_val['message']
                                if "UI test failed:" in error_msg:
                                    error_msg = error_msg.replace("UI test failed: ", "")
                                st.error(f"Task failed: {error_msg}")
                            else:
                                st.warning("Task validation had issues")
                        except:
                            pass

        # Re-upload section for completed tasks
        if is_completed and st.session_state.get(f"retry_task_{t['id']}", False):
            st.markdown("---")
            st.markdown("### Re-attempt This Task")
            
            retry_upload = st.file_uploader(
                f"Upload updated ZIP for Task {t['id']}", 
                type=["zip"], 
                key=f"retry_upload_{t['id']}"
            )
            
            if retry_upload:
                st.success("Updated file ready for validation.")
                
                col_retry_a, col_retry_b = st.columns(2)
                with col_retry_a:
                    if st.button("Validate Update", key=f"validate_retry_{t['id']}"):
                        with st.spinner("Validating your updated submission..."):
                            tmp = tempfile.mktemp(suffix=".zip")
                            with open(tmp, "wb") as f:
                                f.write(retry_upload.getvalue())
                            
                            try:
                                task_validator.load_project_config(str(selected_project_path))
                            except Exception:
                                pass
                            
                            result = task_validator.validate_task(t["id"], tmp, student_id)
                            if result.get("success"):
                                st.success(f"Updated validation completed! Score: {result['total_score']} / {result['max_score']}")
                                task_validator.update_student_progress(student_id, result, project_id)
                                st.session_state[f"retry_task_{t['id']}"] = False
                                st.rerun()
                            else:
                                error_msg = result.get('message') or result.get('error') or 'Unknown error'
                                st.error(f"Updated validation failed: {error_msg}")
                
                with col_retry_b:
                    if st.button("Cancel", key=f"cancel_retry_{t['id']}"):
                        st.session_state[f"retry_task_{t['id']}"] = False
                        st.rerun()
