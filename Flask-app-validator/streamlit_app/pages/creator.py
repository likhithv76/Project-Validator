import streamlit as st
import subprocess
import tempfile, zipfile, os, json
from pathlib import Path
from streamlit_file_browser import st_file_browser

st.set_page_config(page_title="Creator Portal", layout="wide")

st.markdown("""<style>
.section { background: #fff; border:1px solid #ddd; border-radius:10px; padding:20px; margin-bottom:20px; }
</style>""", unsafe_allow_html=True)

st.title("Creator Portal")

# Tab selection
tab1, tab2 = st.tabs(["Project Upload & Preview", "Task Configuration Editor"])

with tab1:
    # Upload project ZIP
    uploaded_zip = st.file_uploader("Upload Base Project ZIP", type=["zip"])

    if uploaded_zip:
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, uploaded_zip.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.getvalue())
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp_dir)
        st.success("Uploaded and extracted project.")

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
                            with st.expander(f"{indent}📁 {item}", expanded=False):
                                show_file_tree(item_path, level + 1)
                        else:
                            file_ext = os.path.splitext(item)[1].lower()
                            icon = "🌐" if file_ext == '.html' else "📄" if file_ext == '.py' else "📝"
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

            if st.button("⚙️ Generate Testcases", use_container_width=True):
                st.info("Generating testcases... Please wait.")
                try:
                    node_script = Path("streamlit_app/pages/autoTestcaseGenerator.js").resolve()
                    result = subprocess.run(
                        ["node", str(node_script), tmp_dir],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        st.success("✅ Testcases generated successfully!")
                        st.text_area("Generator Output Log", result.stdout, height=150)
                        project_json_path = os.path.join(tmp_dir, "project_tasks.json")
                        if os.path.exists(project_json_path):
                            with open(project_json_path, "r", encoding="utf-8") as f:
                                project_data = json.load(f)
                            st.json(project_data)
                            st.session_state.generated_json = project_data
                        else:
                            st.warning("Testcase JSON file not found.")
                    else:
                        st.error("❌ Testcase generation failed.")
                        st.code(result.stderr)
                except Exception as e:
                    st.error(f"Error running Node generator: {e}")

        # ---------------------- RIGHT PANEL ----------------------
        with col_right:
            st.subheader("Create New Task")
            task_name = st.text_input("Task Name")
            task_desc = st.text_area("Task Description")
            requirements = st.text_area("Requirements (one per line)")
            testcases = st.text_area("Test Cases (one per line)")

            if st.button("Save Task"):
                task = {
                    "name": task_name,
                    "description": task_desc,
                    "requirements": requirements.splitlines(),
                    "testcases": testcases.splitlines(),
                }
                st.success(f"Task '{task_name}' saved (prototype).")
                st.write(task)
    else:
        st.info("Please upload a project ZIP to begin.")

with tab2:
    st.subheader("Project Configuration Editor")
    
    # Upload existing project JSON
    json_path = st.file_uploader("Upload existing project JSON", type=["json"], key="json_uploader")
    
    if json_path:
        try:
            data = json.load(json_path)
            st.success("JSON loaded successfully!")
        except Exception as e:
            st.error(f"Error loading JSON: {e}")
            st.stop()
    else:
        # Initialize with default structure if no JSON uploaded
        data = {
            "project": "",
            "description": "",
            "tasks": []
        }
        st.info("No JSON uploaded yet. You can create a new project configuration below.")

    # Editable Project Info
    st.subheader("Project Info")
    data["project"] = st.text_input("Project Name", value=data.get("project", ""))
    data["description"] = st.text_area("Project Description", value=data.get("description", ""))

    st.subheader("Tasks")

    # Editable task blocks
    for i, task in enumerate(data["tasks"]):
        with st.expander(f"Task {task['id']}: {task['name']}", expanded=False):
            task["name"] = st.text_input(f"Task Name {i+1}", task["name"])
            task["description"] = st.text_area(f"Description {i+1}", task["description"])
            task["required_files"] = st.text_area(
                f"Required Files {i+1}", 
                "\n".join(task.get("required_files", []))
            ).split("\n")

            st.markdown("**Validation Rules (JSON)**")
            task["validation_rules"] = st.json(task.get("validation_rules", {}))

            st.markdown("**Playwright Test (JSON)**")
            task["playwright_test"] = st.json(task.get("playwright_test", {}))

            st.markdown("**Unlock Condition**")
            task["unlock_condition"] = st.json(task.get("unlock_condition", {}))

            st.divider()

    # Add Task button
    if st.button("Add New Task"):
        new_id = len(data["tasks"]) + 1
        data["tasks"].append({
            "id": new_id,
            "name": f"Task {new_id}",
            "description": "New task description",
            "required_files": [],
            "validation_rules": {},
            "playwright_test": {},
            "unlock_condition": {"min_score": 0, "required_tasks": []}
        })
        st.rerun()

    # Save JSON
    if st.button("Save Project JSON"):
        output_path = Path("updated_project.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        st.success(f"Saved updated project to {output_path}")
        
        # Provide download link
        with open(output_path, "r", encoding="utf-8") as f:
            json_content = f.read()
        st.download_button(
            label="Download Project JSON",
            data=json_content,
            file_name="project_config.json",
            mime="application/json"
        )