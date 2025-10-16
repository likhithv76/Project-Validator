"""
Streamlit-based rule builder for creating dynamic validation rules.
Allows users to create custom validation rules through a form interface.
"""

import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from utils.rule_templates import (
    get_rule_template, create_html_rule, create_boilerplate_rule,
    create_requirements_rule, create_database_rule, create_security_rule,
    create_runtime_rule, validate_rule, save_rules_to_file, load_rules_from_file,
    get_available_rule_types, get_security_features, get_html_elements,
    get_css_classes, get_python_imports, get_flask_routes
)

def initialize_session_state():
    """Initialize session state variables."""
    if 'rules' not in st.session_state:
        st.session_state.rules = []
    if 'current_rule' not in st.session_state:
        st.session_state.current_rule = None
    if 'project_name' not in st.session_state:
        st.session_state.project_name = ""

def render_rule_form():
    """Render the rule creation form."""
    st.subheader("🔧 Create New Rule")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        rule_type = st.selectbox(
            "Rule Type",
            options=get_available_rule_types(),
            help="Select the type of validation rule to create"
        )
    
    with col2:
        points = st.number_input(
            "Points",
            min_value=0,
            max_value=100,
            value=10,
            help="Points awarded for passing this rule"
        )
    
    file_path = st.text_input(
        "File Path",
        placeholder="e.g., templates/index.html, app.py, requirements.txt",
        help="Path to the file this rule will validate"
    )
    
    # Render type-specific fields
    if rule_type == "html":
        render_html_rule_fields()
    elif rule_type == "boilerplate":
        render_boilerplate_rule_fields()
    elif rule_type == "requirements":
        render_requirements_rule_fields()
    elif rule_type == "database":
        render_database_rule_fields()
    elif rule_type == "security":
        render_security_rule_fields()
    elif rule_type == "runtime":
        render_runtime_rule_fields()
    
    # Add rule button
    if st.button("➕ Add Rule", type="primary"):
        if not file_path:
            st.error("Please enter a file path")
            return
        
        rule = create_rule_from_form(rule_type, file_path, points)
        if rule:
            st.session_state.rules.append(rule)
            st.success(f"Added {rule_type} rule for {file_path}")
            st.rerun()

def render_html_rule_fields():
    """Render fields specific to HTML rules."""
    st.markdown("**HTML Validation Options**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        elements = st.multiselect(
            "Required HTML Elements",
            options=get_html_elements(),
            help="Select HTML elements that must be present"
        )
        
        classes = st.multiselect(
            "Required CSS Classes",
            options=get_css_classes(),
            help="Select CSS classes that must be present"
        )
    
    with col2:
        content = st.text_area(
            "Required Content",
            placeholder="Enter required text content, one per line",
            help="Text content that must be present in the file"
        ).split('\n') if st.text_area else []
        
        inputs = st.text_area(
            "Required Input Fields",
            placeholder="Enter input field names, one per line",
            help="Form input fields that must be present"
        ).split('\n') if st.text_area else []
    
    # Store in session state for rule creation
    st.session_state.html_elements = elements
    st.session_state.html_classes = classes
    st.session_state.html_content = [c.strip() for c in content if c.strip()]
    st.session_state.html_inputs = [i.strip() for i in inputs if i.strip()]

def render_boilerplate_rule_fields():
    """Render fields specific to boilerplate rules."""
    st.markdown("**Boilerplate Structure Options**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        required_classes = st.multiselect(
            "Required CSS Classes",
            options=get_css_classes(),
            help="CSS classes that must be present"
        )
        
        required_functions = st.text_area(
            "Required JavaScript Functions",
            placeholder="Enter function names, one per line",
            help="JavaScript functions that must be present"
        ).split('\n') if st.text_area else []
    
    with col2:
        st.markdown("**Expected HTML Structure**")
        structure_json = st.text_area(
            "Structure JSON",
            placeholder='{"div": {"class": "container"}, "form": {"input": {"type": "text"}}}',
            help="JSON structure defining expected HTML hierarchy"
        )
        
        try:
            expected_structure = json.loads(structure_json) if structure_json else {}
        except json.JSONDecodeError:
            expected_structure = {}
            st.warning("Invalid JSON structure")
    
    # Store in session state
    st.session_state.boilerplate_classes = required_classes
    st.session_state.boilerplate_functions = [f.strip() for f in required_functions if f.strip()]
    st.session_state.boilerplate_structure = expected_structure

def render_requirements_rule_fields():
    """Render fields specific to requirements rules."""
    st.markdown("**Requirements File Options**")
    
    packages = st.text_area(
        "Required Packages",
        placeholder="Enter package names, one per line\ne.g.,\nFlask\nFlask-SQLAlchemy\nWerkzeug",
        help="Python packages that must be in requirements.txt"
    ).split('\n') if st.text_area else []
    
    st.session_state.requirements_packages = [p.strip() for p in packages if p.strip()]

def render_database_rule_fields():
    """Render fields specific to database rules."""
    st.markdown("**Database File Options**")
    
    must_exist = st.checkbox(
        "File Must Exist",
        value=True,
        help="Whether the database file must exist"
    )
    
    st.session_state.database_must_exist = must_exist

def render_security_rule_fields():
    """Render fields specific to security rules."""
    st.markdown("**Security Features**")
    
    security_features = st.multiselect(
        "Required Security Features",
        options=get_security_features(),
        help="Security features that must be implemented"
    )
    
    st.session_state.security_features = security_features

def render_runtime_rule_fields():
    """Render fields specific to runtime rules."""
    st.markdown("**Runtime Route Options**")
    
    routes = st.multiselect(
        "Required Routes",
        options=get_flask_routes(),
        help="Flask routes that must be present"
    )
    
    custom_routes = st.text_area(
        "Custom Routes",
        placeholder="Enter custom routes, one per line\n/register\n/login\n/logout",
        help="Additional custom routes that must be present"
    ).split('\n') if st.text_area else []
    
    all_routes = routes + [r.strip() for r in custom_routes if r.strip()]
    st.session_state.runtime_routes = all_routes

def create_rule_from_form(rule_type: str, file_path: str, points: int) -> Optional[Dict[str, Any]]:
    """Create a rule dictionary from the form data."""
    try:
        if rule_type == "html":
            return create_html_rule(
                file_path=file_path,
                elements=st.session_state.get('html_elements', []),
                classes=st.session_state.get('html_classes', []),
                content=st.session_state.get('html_content', []),
                inputs=st.session_state.get('html_inputs', []),
                points=points
            )
        
        elif rule_type == "boilerplate":
            return create_boilerplate_rule(
                file_path=file_path,
                expected_structure=st.session_state.get('boilerplate_structure', {}),
                required_classes=st.session_state.get('boilerplate_classes', []),
                required_functions=st.session_state.get('boilerplate_functions', []),
                points=points
            )
        
        elif rule_type == "requirements":
            return create_requirements_rule(
                file_path=file_path,
                packages=st.session_state.get('requirements_packages', []),
                points=points
            )
        
        elif rule_type == "database":
            return create_database_rule(
                file_path=file_path,
                must_exist=st.session_state.get('database_must_exist', True),
                points=points
            )
        
        elif rule_type == "security":
            return create_security_rule(
                file_path=file_path,
                security_features=st.session_state.get('security_features', []),
                points=points
            )
        
        elif rule_type == "runtime":
            return create_runtime_rule(
                file_path=file_path,
                routes=st.session_state.get('runtime_routes', []),
                points=points
            )
        
        return None
    
    except Exception as e:
        st.error(f"Error creating rule: {e}")
        return None

def render_rules_preview():
    """Render the preview of all rules."""
    st.subheader("📋 Rules Preview")
    
    if not st.session_state.rules:
        st.info("No rules created yet. Add some rules using the form above.")
        return
    
    # Display rules in a table
    for i, rule in enumerate(st.session_state.rules):
        with st.expander(f"Rule {i+1}: {rule['type']} - {rule['file']} ({rule['points']} points)"):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.json(rule)
            
            with col2:
                if st.button("🗑️ Delete", key=f"delete_{i}"):
                    st.session_state.rules.pop(i)
                    st.rerun()

def render_export_section():
    """Render the export and save section."""
    st.subheader("💾 Export Rules")
    
    if not st.session_state.rules:
        st.warning("No rules to export")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        project_name = st.text_input(
            "Project Name",
            value=st.session_state.project_name,
            placeholder="Enter project name for file naming",
            help="This will be used to name the rules file"
        )
        st.session_state.project_name = project_name
    
    with col2:
        st.markdown("**Export Options**")
        
        if st.button("📥 Download JSON", type="primary"):
            if not project_name:
                st.error("Please enter a project name")
                return
            
            # Create JSON data
            json_data = {"rules": st.session_state.rules}
            json_str = json.dumps(json_data, indent=2)
            
            # Download button
            st.download_button(
                label="Download Rules JSON",
                data=json_str,
                file_name=f"custom_rules_{project_name}.json",
                mime="application/json"
            )
    
    # Save to file system
    if st.button("💾 Save to File System"):
        if not project_name:
            st.error("Please enter a project name")
            return
        
        rules_dir = Path("rules")
        rules_dir.mkdir(exist_ok=True)
        
        file_path = rules_dir / f"custom_rules_{project_name}.json"
        
        if save_rules_to_file(st.session_state.rules, str(file_path)):
            st.success(f"Rules saved to {file_path}")
        else:
            st.error("Failed to save rules")

def render_import_section():
    """Render the import section."""
    st.subheader("📤 Import Rules")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # File upload
        uploaded_file = st.file_uploader(
            "Upload Rules JSON",
            type=['json'],
            help="Upload an existing rules JSON file"
        )
        
        if uploaded_file:
            try:
                rules_data = json.load(uploaded_file)
                imported_rules = rules_data.get("rules", [])
                
                if st.button("Import Rules"):
                    st.session_state.rules.extend(imported_rules)
                    st.success(f"Imported {len(imported_rules)} rules")
                    st.rerun()
            
            except json.JSONDecodeError:
                st.error("Invalid JSON file")
    
    with col2:
        # Load from existing files
        rules_dir = Path("rules")
        if rules_dir.exists():
            existing_files = list(rules_dir.glob("*.json"))
            
            if existing_files:
                st.markdown("**Load Existing Rules**")
                
                selected_file = st.selectbox(
                    "Select Rules File",
                    options=existing_files,
                    format_func=lambda x: x.name
                )
                
                if st.button("Load Rules"):
                    rules = load_rules_from_file(str(selected_file))
                    if rules:
                        st.session_state.rules = rules
                        st.success(f"Loaded {len(rules)} rules from {selected_file.name}")
                        st.rerun()
                    else:
                        st.error("Failed to load rules")

def main():
    """Main rule builder interface."""
    st.set_page_config(
        page_title="Rule Builder",
        page_icon="🔧",
        layout="wide"
    )
    
    st.title("🔧 Dynamic Rule Builder")
    st.markdown("Create custom validation rules for Flask applications")
    
    initialize_session_state()
    
    # Main layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_rule_form()
        st.divider()
        render_import_section()
    
    with col2:
        render_rules_preview()
        st.divider()
        render_export_section()
    
    # Rules summary
    if st.session_state.rules:
        st.divider()
        st.subheader("📊 Rules Summary")
        
        total_points = sum(rule.get('points', 0) for rule in st.session_state.rules)
        rule_types = {}
        
        for rule in st.session_state.rules:
            rule_type = rule.get('type', 'unknown')
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Rules", len(st.session_state.rules))
        
        with col2:
            st.metric("Total Points", total_points)
        
        with col3:
            st.metric("Rule Types", len(rule_types))
        
        # Rule type breakdown
        if rule_types:
            st.markdown("**Rule Type Breakdown:**")
            for rule_type, count in rule_types.items():
                st.write(f"- {rule_type}: {count} rules")

if __name__ == "__main__":
    main()
