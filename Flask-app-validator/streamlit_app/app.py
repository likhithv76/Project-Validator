import streamlit as st
import zipfile
import tempfile
import os
import sys
import time
from pathlib import Path
import importlib

project_root = Path(__file__).resolve().parents[1]
validator_dir = project_root / "validator"
sys.path.insert(0, str(validator_dir))

import flexible_validator as fv
importlib.reload(fv)
from flexible_validator import run_flexible_validation

st.set_page_config(page_title="Flask Project Validator", page_icon="🧠", layout="wide")
st.title(" Automated Flask Project Validator")
st.markdown(
    """
    Validate Flask-based student submissions with runtime checks, CRUD tests, DB schema analysis,  
    and structural HTML/boilerplate validation.
    """
)

col_left, col_right = st.columns([1, 1.8])

with col_left:
    st.header("📂 Upload Project")
    uploaded_file = st.file_uploader("Upload Flask project (.zip)", type=["zip"])
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

        result = run_flexible_validation(temp_dir)

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

        result_placeholder.markdown(
            f"""
            <div style="background-color:#111;border:1px solid #333;border-radius:8px;padding:12px;">
            <b>Log File:</b> {result['log_file']}<br>
            <b>JSON Summary:</b> {result['json_file']}<br>
            <b>Errors:</b> {len(result['errors'])}<br>
            <b>Warnings:</b> {len(result['warnings'])}<br>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif run_validation:
    st.error("Please upload a valid project ZIP file before running validation.")
