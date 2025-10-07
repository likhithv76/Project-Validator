import streamlit as st
import zipfile
import tempfile
import os
import sys
import json
from pathlib import Path
import time

# --- Ensure validator module is reloaded each run ---
# --- Ensure validator module is accessible ---
import sys
from pathlib import Path
import importlib

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
validator_dir = project_root / "validator"
sys.path.insert(0, str(validator_dir))

import flexible_validator as fv
importlib.reload(fv)
from flexible_validator import run_flexible_validation



# --- Streamlit Page Config ---
st.set_page_config(page_title="Flask Project Validator", page_icon="🧠", layout="wide")

# --- Title ---
st.title("Automated Flask Project Validator")
st.markdown("Validate Flask-based student submissions with runtime checks, CRUD tests, and DB schema analysis.")

# --- Layout: two columns ---
col_left, col_right = st.columns([1, 1.5])

# ======================================================
# LEFT COLUMN: Inputs and Summary
# ======================================================
with col_left:
    st.header("Submission Details")

    student_id = st.text_input("Student ID", placeholder="Enter student ID")
    project_name = st.text_input("Project Name", placeholder="Enter project name")
    uploaded_file = st.file_uploader("Upload Flask project (.zip)", type=["zip"])

    run_validation = st.button("Run Validation", use_container_width=True)

    st.markdown("---")
    result_placeholder = st.empty()  # Placeholder for summary info after run
    st.markdown("---")

# ======================================================
# RIGHT COLUMN: Logs output
# ======================================================
with col_right:
    st.header("Validation Logs")
    log_box = st.empty()  # Dynamic log area for streaming updates
    st.markdown("Logs will appear here as the validation runs...")

# ======================================================
# VALIDATION LOGIC
# ======================================================
if run_validation and uploaded_file and student_id and project_name:
    with st.spinner("Running validation... this may take a moment ⏳"):
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, uploaded_file.name)

        # Save the uploaded ZIP file
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        # Extract project
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # --- Run validation ---
        # Show simulated log streaming while validation runs
        log_box.text("Starting validation...\n")

        result = run_flexible_validation(temp_dir)

        # --- Display logs ---
        if os.path.exists(result["log_file"]):
            with open(result["log_file"], "r", encoding="utf-8") as logf:
                content = logf.read()
                log_box.text(content)
        else:
            log_box.text("No logs found.")

        # --- Display summary info on the left ---
        summary_html = ""

        # Basic project info
        summary_html += f"**Project:** {project_name}<br>"
        summary_html += f"**Student ID:** {student_id}<br>"
        summary_html += f"**Result:** {'✅ PASSED' if result['success'] else '❌ FAILED'}<br><br>"

        # --- JSON results ---
        if os.path.exists(result["json_file"]):
            try:
                with open(result["json_file"], "r", encoding="utf-8") as jf:
                    data = json.load(jf)

                # Extract modules used (by parsing flask imports)
                events = data.get("events", [])
                modules = []
                for e in events:
                    msg = e.get("message", "")
                    if "import" in msg and "flask" in msg:
                        modules.append(msg)
                modules = list(set(modules))
                summary_html += f"**Modules Used:**<br>"
                if modules:
                    summary_html += "<ul>" + "".join([f"<li>{m}</li>" for m in modules]) + "</ul>"
                else:
                    summary_html += "No modules detected.<br>"

                # Extract DB schema
                db_info = data.get("db_inspection", [])
                if db_info:
                    summary_html += f"<br>**Database Schemas:**<br>"
                    for db in db_info:
                        summary_html += f"<b>{db['path']}</b><br>"
                        for tbl, cols in db.get("tables", {}).items():
                            summary_html += f"<b>• {tbl}</b> ({len(cols)} columns)<br>"
                            summary_html += "<ul>" + "".join([f"<li>{c['name']} ({c['type']})</li>" for c in cols]) + "</ul>"
                else:
                    summary_html += "<br>**Database Schemas:** None detected.<br>"

            except Exception as e:
                summary_html += f"<br>⚠️ Error reading summary JSON: {e}"

        else:
            summary_html += "No JSON summary available."

        # Render summary
        with col_left:
            result_placeholder.markdown(summary_html, unsafe_allow_html=True)

        st.success("Validation Completed.")

elif run_validation:
    st.error("Please fill in all fields and upload a valid project ZIP file.")
