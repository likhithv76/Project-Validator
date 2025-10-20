import streamlit as st
import subprocess
import tempfile, zipfile, os, json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from gemini_generator import GeminiTestCaseGenerator

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
        st.subheader("Testcase Generation Configuration")
        
        # Initialize Gemini generator
        gemini_generator = GeminiTestCaseGenerator()
        generation_method = gemini_generator.get_generation_method()
        
        # Configuration section
        with st.expander("⚙️ Generation Settings", expanded=False):
            col_config1, col_config2 = st.columns(2)
            
            with col_config1:
                st.markdown("**Current Method:**")
                if generation_method == 'AI':
                    st.success(f"🤖 AI Generation (Gemini)")
                if not gemini_generator.is_ai_enabled():
                    st.warning("⚠️ Gemini AI not configured")
                    st.code("Set GEMINI_API_KEY in .env")
                else:
                    st.info(f"📝 Parser Generation")
                    
            with col_config2:
                st.markdown("**Configuration File:**")
                st.code(".env")
                if st.button("📁 Open Config", help="Edit .env to change settings"):
                    st.info("Edit .env file to change TEST_CASE_GENERATOR_METHOD")

        st.markdown("---")
        st.subheader("Auto-generate Testcases")

        if st.button("Generate Testcases", use_container_width=True):
            st.info("Generating testcases... Please wait.")
            try:
                if generation_method == 'AI' and gemini_generator.is_ai_enabled():
                    # Use Gemini AI generation
                    st.info("🤖 Generating testcases using Gemini AI...")
                    project_meta = {
                        "project": "New Project",
                        "description": "Auto-generated progressive validation project"
                    }
                    result_json = gemini_generator.generate_project_json_with_ai(tmp_dir, project_meta)
                    
                    # Save the generated JSON
                    project_file = os.path.join(tmp_dir, "project_tasks.json")
                    with open(project_file, "w") as f:
                        json.dump(result_json, f, indent=2)
                    
                    st.success("✅ AI-generated testcases completed!")
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
            
            # Tasks Editor
            for i, task in enumerate(project_data["tasks"]):
                with st.expander(f"Task {task['id']}: {task['name']}", expanded=False):
                    # Basic task info
                    new_name = st.text_input(f"Task Name", value=task["name"], key=f"task_name_{i}")
                    new_description = st.text_area(f"Description", value=task["description"], key=f"task_desc_{i}")
                    
                    # Required files - use multi-select
                    st.markdown("**Required Files:**")
                    
                    # Get available files from the project (if available)
                    available_files = [
                        "app.py", "requirements.txt", "templates/base.html", 
                        "templates/index.html", "templates/about.html", 
                        "templates/contact.html", "static/style.css", "static/script.js",
                        "main.py", "run.py", "config.py", "models.py", "views.py",
                        "templates/login.html", "templates/register.html", "templates/dashboard.html",
                        "static/css/style.css", "static/js/script.js", "static/images/logo.png"
                    ]
                    
                    # Add any files from the current task that aren't in the list
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
                    
                    # Update task data only if changed
                    if new_name != task["name"]:
                        task["name"] = new_name
                    if new_description != task["description"]:
                        task["description"] = new_description
                    if selected_files != current_files:
                        task["required_files"] = selected_files
                    
                    # Validation Rules - populate from analysis
                    st.markdown("**Validation Rules:**")
                    validation_rules = task.get("validation_rules", {})
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
                    
                    # Playwright Test - populate from analysis
                    st.markdown("**Playwright Test:**")
                    playwright_test = task.get("playwright_test", {}) or {}
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        # Get current values
                        current_route = playwright_test.get("route", "")
                        current_pw_points = playwright_test.get("points", validation_rules.get("points", 10))
                        
                        # Generate route from file name
                        file_name = validation_rules.get("file", "")
                        route_suggestion = f"/{file_name.replace('.html', '').replace('.css', '').replace('.js', '')}" if file_name else ""
                        
                        new_route = st.text_input(
                            "Route", 
                            value=current_route or route_suggestion,
                            key=f"pw_route_{i}"
                        )
                        new_pw_points = st.number_input(
                            "Points", 
                            min_value=1, 
                            max_value=100, 
                            value=current_pw_points,
                            key=f"pw_points_{i}"
                        )
                        
                        # Update only if changed
                        if new_route != current_route:
                            playwright_test["route"] = new_route
                        if new_pw_points != current_pw_points:
                            playwright_test["points"] = new_pw_points
                    
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
3. Run Playwright tests using the configured routes and actions
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
            st.info("Upload a project ZIP and generate testcases to configure tasks.")
            
            # Comprehensive Project Configuration Form
            st.markdown("### Create Project Configuration")
            
            # Project metadata
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("Project Name", value="New Project")
            with col2:
                project_description = st.text_input("Project Description", value="Auto-generated progressive validation project")
            
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
                        default=["templates/login.html"]
                    )
                
                with col4:
                    file_type = st.selectbox("File Type", ["html", "py", "css", "js"])
                    points = st.number_input("Points", min_value=1, max_value=50, value=10)
                
                # Playwright test configuration
                st.markdown("**Playwright Test Configuration:**")
                col5, col6 = st.columns(2)
                with col5:
                    route = st.text_input("Route", placeholder="/login")
                with col6:
                    playwright_points = st.number_input("Playwright Points", min_value=1, max_value=50, value=10)
                
                # Actions for playwright
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
                        validate = [
                            {"type": "text_present", "value": "successful"},
                            {"type": "text_present", "value": "Registration successful"},
                            {"type": "text_present", "value": "Login successful"}
                        ]
                        
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
                                "file": required_files[0] if required_files else "",
                                "points": points,
                                "generatedTests": [],
                                "analysis": {"elements": [], "selectors": []}
                            },
                            "playwright_test": {
                                "route": route,
                                "actions": actions,
                                "validate": validate,
                                "points": playwright_points
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
                            st.write(f"**Points:** {task['validation_rules']['points']} (validation) + {task['playwright_test']['points']} (playwright)")
                        with col10:
                            if st.button("Remove", key=f"remove_{i}"):
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