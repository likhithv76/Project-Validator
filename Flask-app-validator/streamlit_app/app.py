import streamlit as st
import zipfile
import tempfile
import os
import sys
from pathlib import Path
import importlib

project_root = Path(__file__).resolve().parents[1]
validator_dir = project_root / "validator"
sys.path.insert(0, str(validator_dir))

import flexible_validator as fv
importlib.reload(fv)
from flexible_validator import run_flexible_validation

st.set_page_config(page_title="Flask Project Validator", page_icon="🧠", layout="wide")

st.title("Automated Flask Project Validator")
st.markdown("Validate Flask-based student submissions with runtime checks, CRUD tests, and DB schema analysis.")

col_left, col_right = st.columns([1, 1.5])

with col_left:
    st.header("Upload Project")
    uploaded_file = st.file_uploader("Upload Flask project (.zip)", type=["zip"])
    run_validation = st.button("Run Validation", use_container_width=True)

    st.markdown("---")
    result_placeholder = st.empty()
    st.markdown("---")

with col_right:
    st.header("Validation Logs")
    log_box = st.empty()
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
            with open(result["log_file"], "r", encoding="utf-8") as logf:
                content = logf.read()
                log_box.markdown(
                    f"<div style='border:1px solid #333;border-radius:10px;background-color:#000;color:#0f0;"
                    f"padding:10px;height:450px;overflow-y:scroll;font-family:monospace;white-space:pre-wrap;"
                    f"font-size:13px;'>{content}</div>",
                    unsafe_allow_html=True,
                )

        st.success("Validation Completed.")

elif run_validation:
    st.error("Please upload a valid project ZIP file.")