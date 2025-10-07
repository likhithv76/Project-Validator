import streamlit as st
import zipfile
import tempfile
import os
import sys
import json
from pathlib import Path
import time
import importlib

# --- Ensure validator module is accessible ---
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
# RIGHT COLUMN: Logs output (scrollable block)
# ======================================================
with col_right:
    st.header("Validation Logs")
    log_box = st.empty()  # single dynamic container

    log_box.markdown(
        """
        <div style="
            border:1px solid #444;
            border-radius:10px;
            background-color:#000;
            color:#0f0;
            padding:10px;
            height:450px;
            overflow-y:scroll;
            font-family:monospace;
            white-space:pre-wrap;
            font-size:13px;">
        Logs will appear here as the validation runs...
        </div>
        """,
        unsafe_allow_html=True,
    )


# ======================================================
# VALIDATION LOGIC
# ======================================================
if run_validation and uploaded_file and student_id and project_name:
    with st.spinner("Running validation... this may take a moment ⏳"):
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, uploaded_file.name)

        # Save uploaded ZIP
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        # Extract contents
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # Run validation
        log_box.markdown(
            """
            <div style="border:1px solid #ccc;border-radius:10px;background-color:#000;color:#0f0;padding:10px;height:450px;overflow-y:scroll;font-family:monospace;white-space:pre-wrap;font-size:13px;">
            Starting validation...
            </div>
            """,
            unsafe_allow_html=True,
        )

        result = run_flexible_validation(temp_dir)

        # Read logs
        log_html = ""
        if os.path.exists(result["log_file"]):
            with open(result["log_file"], "r", encoding="utf-8") as logf:
                content = logf.read()
                log_html = (
                    f"<div style='border:1px solid #ccc;border-radius:10px;background-color:#000;color:#0f0;"
                    f"padding:10px;height:450px;overflow-y:scroll;font-family:monospace;white-space:pre-wrap;"
                    f"font-size:13px;'>{content}</div>"
                )
        else:
            log_html = (
                "<div style='border:1px solid #ccc;border-radius:10px;padding:10px;height:450px;overflow-y:scroll;"
                "background-color:#f8f9fa;'>No logs found.</div>"
            )

        log_box.markdown(log_html, unsafe_allow_html=True)

        # --- Display summary info ---
        summary_html = ""

        # Project details
        summary_html += f"**Project:** {project_name}<br>"
        summary_html += f"**Student ID:** {student_id}<br>"
        summary_html += f"**Result:** {'✅ PASSED' if result['success'] else '❌ FAILED'}<br><br>"

        # Parse JSON file for more insights
        if os.path.exists(result["json_file"]):
            try:
                with open(result["json_file"], "r", encoding="utf-8") as jf:
                    data = json.load(jf)

                # --- Modules used ---
                events = data.get("events", [])
                modules = sorted(set(e["message"] for e in events if "import" in e.get("message", "").lower()))
                summary_html += "<b>Modules Used:</b><br>"
                if modules:
                    summary_html += "<ul>" + "".join([f"<li>{m}</li>" for m in modules]) + "</ul>"
                else:
                    summary_html += "No Flask modules detected.<br>"

                # --- Database schemas ---
                db_info = data.get("db_inspection", [])
                if db_info:
                    seen_dbs = set()
                    summary_html += "<br><b>Database Schemas:</b><br>"
                    for db in db_info:
                        db_name = Path(db["path"]).name
                        if db_name in seen_dbs:
                            continue
                        seen_dbs.add(db_name)
                        summary_html += f"<b>{db_name}</b><br>"
                        for tbl, cols in db.get("tables", {}).items():
                            summary_html += f"<b>• {tbl}</b> ({len(cols)} columns)<br>"
                            summary_html += "<ul>" + "".join(
                                [f"<li>{c['name']} ({c['type']})</li>" for c in cols]
                            ) + "</ul>"
                else:
                    summary_html += "<br><b>Database Schemas:</b> None detected.<br>"

                # --- Payloads used for testing ---
                crud_results = data.get("crud_results", [])
                if crud_results:
                    summary_html += "<br><b>Payloads Used for Testing:</b><br>"
                    for item in crud_results:
                        action = item.get("action", "")
                        endpoint = item.get("endpoint", "")
                        payload = item.get("payload", {})

                        # Only show if payload was actually sent
                        if action in ("GET", "CREATE", "UPDATE", "DELETE") and payload:
                            # Strip empty/default-like keys
                            sent_payload = {k: v for k, v in payload.items() if v not in ("", None)}

                            summary_html += (
                                f"<details style='margin-bottom:6px;'>"
                                f"<summary><code>{endpoint}</code> → {action}</summary>"
                                f"<pre style='background-color:#1e1e1e;color:#00ff90;"
                                f"padding:6px;border-radius:5px;font-size:13px;'>"
                                f"{json.dumps(sent_payload, indent=2)}</pre></details>"
                            )
                    if not any(i.get("payload") for i in crud_results):
                        summary_html += "No payloads were captured.<br>"
                else:
                    summary_html += "<br><b>Payloads Used for Testing:</b> None detected.<br>"

            except Exception as e:
                summary_html += f"<br> Error reading summary JSON: {e}"

        else:
            summary_html += "No JSON summary available."

        # Display results
        with col_left:
            result_placeholder.markdown(summary_html, unsafe_allow_html=True)

        st.success("Validation Completed.")

elif run_validation:
    st.error("Please fill in all fields and upload a valid project ZIP file.")
