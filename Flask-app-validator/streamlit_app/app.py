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

st.set_page_config(page_title="Flask Project Validator", page_icon="🧠", layout="wide")

# Sidebar navigation
st.sidebar.title("Flask Validator")
page = st.sidebar.selectbox(
    "Choose Page",
    ["Main Validator", "Rule Builder", "Rule Manager"]
)

if page == "🔧 Rule Builder":
    # Import and run rule builder
    from rule_builder import main
    main()
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
