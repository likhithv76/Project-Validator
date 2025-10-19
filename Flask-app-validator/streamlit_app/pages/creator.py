import streamlit as st
import subprocess
import tempfile, zipfile, os, json
from pathlib import Path

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
                        # Store generation timestamp
                        from datetime import datetime
                        st.session_state.generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        st.warning("Testcase JSON file not found.")
                else:
                    st.error("❌ Testcase generation failed.")
                    st.code(result.stderr)
            except Exception as e:
                st.error(f"Error running Node generator: {e}")

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
            
            # Tasks Editor
            for i, task in enumerate(project_data["tasks"]):
                with st.expander(f"Task {task['id']}: {task['name']}", expanded=False):
                    # Basic task info
                    task["name"] = st.text_input(f"Task Name", value=task["name"], key=f"task_name_{i}")
                    task["description"] = st.text_area(f"Description", value=task["description"], key=f"task_desc_{i}")
                    
                    # Required files - populate from analysis
                    st.markdown("**Required Files:**")
                    required_files_text = "\n".join(task.get("required_files", []))
                    task["required_files"] = st.text_area(
                        "Required Files (one per line)", 
                        value=required_files_text,
                        key=f"required_files_{i}"
                    ).split("\n")
                    
                    # Validation Rules - populate from analysis
                    st.markdown("**Validation Rules:**")
                    validation_rules = task.get("validation_rules", {})
                    analysis = validation_rules.get("analysis", {})
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        validation_rules["type"] = st.selectbox(
                            "Type", 
                            ["html", "css", "js", "python"], 
                            index=["html", "css", "js", "python"].index(validation_rules.get("type", "html")),
                            key=f"val_type_{i}"
                        )
                        
                        # Dynamic points based on complexity
                        elements_count = len(analysis.get("elements", []))
                        forms_count = len(analysis.get("forms", []))
                        complexity_score = min(50, elements_count * 2 + forms_count * 5)
                        validation_rules["points"] = st.number_input(
                            "Points", 
                            min_value=1, 
                            max_value=100, 
                            value=max(validation_rules.get("points", 10), complexity_score),
                            key=f"val_points_{i}"
                        )
                    
                    with col2:
                        validation_rules["file"] = st.text_input(
                            "File", 
                            value=validation_rules.get("file", ""),
                            key=f"val_file_{i}"
                        )
                    
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
                    
                    # Playwright Test - populate from analysis
                    st.markdown("**Playwright Test:**")
                    playwright_test = task.get("playwright_test", {})
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        # Generate route from file name
                        file_name = validation_rules.get("file", "")
                        route_suggestion = f"/{file_name.replace('.html', '').replace('.css', '').replace('.js', '')}" if file_name else ""
                        playwright_test["route"] = st.text_input(
                            "Route", 
                            value=playwright_test.get("route", route_suggestion),
                            key=f"pw_route_{i}"
                        )
                        playwright_test["points"] = st.number_input(
                            "Points", 
                            min_value=1, 
                            max_value=100, 
                            value=playwright_test.get("points", validation_rules.get("points", 10)),
                            key=f"pw_points_{i}"
                        )
                    
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
                        actions = playwright_test.get("actions", suggested_actions)
                        if isinstance(actions, list) and actions and isinstance(actions[0], dict):
                            # Convert dict actions to readable text
                            actions_text = []
                            for action in actions:
                                if action.get("click"):
                                    actions_text.append(f"Click: {action.get('selector_type', 'class')}={action.get('selector_value', '')}")
                                elif action.get("input_variants"):
                                    variants = ", ".join(action.get("input_variants", []))
                                    actions_text.append(f"Fill {action.get('selector_type', 'class')}={action.get('selector_value', '')}: {variants}")
                                else:
                                    actions_text.append(str(action))
                            actions_text = "\n".join(actions_text)
                        else:
                            actions_text = "\n".join(actions) if actions else ""
                        actions_input = st.text_area(
                            "Actions (one per line)",
                            value=actions_text,
                            height=100,
                            key=f"pw_actions_{i}"
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
                            playwright_test["actions"] = parsed_actions
                        else:
                            playwright_test["actions"] = []
                    
                    # Validation section
                    st.markdown("**Validation Rules:**")
                    validation_rules_list = playwright_test.get("validate", [])
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
                        key=f"pw_validate_{i}",
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
                        playwright_test["validate"] = parsed_validation
                    else:
                        playwright_test["validate"] = []
                    
                    task["playwright_test"] = playwright_test
                    
                    # Unlock Condition
                    st.markdown("**Unlock Condition:**")
                    unlock_condition = task.get("unlock_condition", {})
                    
                    col5, col6 = st.columns(2)
                    with col5:
                        unlock_condition["min_score"] = st.number_input(
                            "Min Score", 
                            min_value=0, 
                            max_value=100, 
                            value=unlock_condition.get("min_score", 0),
                            key=f"unlock_score_{i}"
                        )
                    
                    with col6:
                        # Show available task IDs for reference
                        available_task_ids = [str(t["id"]) for t in project_data["tasks"] if t["id"] != task["id"]]
                        required_tasks_text = ", ".join(map(str, unlock_condition.get("required_tasks", [])))
                        st.caption(f"Available task IDs: {', '.join(available_task_ids)}")
                        required_tasks_input = st.text_input(
                            "Required Tasks (comma-separated IDs)",
                            value=required_tasks_text,
                            key=f"unlock_tasks_{i}"
                        )
                        try:
                            unlock_condition["required_tasks"] = [int(x.strip()) for x in required_tasks_input.split(",") if x.strip()]
                        except ValueError:
                            unlock_condition["required_tasks"] = []
                    
                    task["unlock_condition"] = unlock_condition
                    
                    st.divider()
            
            # Add new task button
            st.markdown("### Add New Task")
            col_add, col_spacer = st.columns([0.3, 0.7])
            with col_add:
                if st.button("➕ Add New Task", use_container_width=True):
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
                if st.button("💾 Save Project Package", use_container_width=True):
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
3. Run Playwright tests using the configured routes and actions
""")
                    
                    st.success(f"✅ Project saved and available to students!")
                    st.info(f"📁 Project '{project_data.get('project', 'Untitled')}' is now available in the Student Portal")
                    st.success(f"📂 Files saved to: {projects_dir}")
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
                        label="📦 Download Complete Package",
                        data=package_content,
                        file_name=f"{project_name}_package.zip",
                        mime="application/zip",
                        help="Downloads the complete project package with JSON config and source ZIP"
                    )
                    
                    # Also provide individual JSON download
                    with open(json_path, "r", encoding="utf-8") as f:
                        json_content = f.read()
                    st.download_button(
                        label="📄 Download JSON Only",
                        data=json_content,
                        file_name=json_filename,
                        mime="application/json",
                        help="Downloads only the JSON configuration file"
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
                
                if st.button("🔄 Update from JSON"):
                    try:
                        updated_data = json.loads(json_text)
                        st.session_state.generated_json = updated_data
                        st.success("✅ JSON updated successfully!")
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON: {e}")
        
        else:
            st.info("👆 Upload a project ZIP and generate testcases to configure tasks.")
            
            # Simple task creation form
            st.markdown("### Create Manual Task")
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