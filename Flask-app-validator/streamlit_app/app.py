import streamlit as st

st.set_page_config(page_title="Flask Validator", layout="wide")

st.markdown("""
<style>
body { background-color: #fafafa !important; }
.header {
    text-align: center;
    margin-top: 3rem;
    margin-bottom: 2rem;
}
.btn {
    background-color: #007b83;
    color: white;
    font-weight: 500;
    padding: 0.7rem 1.5rem;
    border-radius: 8px;
    border: none;
}
.btn:hover { background-color: #005f66; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header">
    <h1>Flask Project Validator</h1>
    <p>Choose your workspace below</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    if st.button("Go to Creator Page", use_container_width=True):
        st.switch_page("pages/creator.py")

with col2:
    if st.button("Go to Student Page", use_container_width=True):
        st.switch_page("pages/student.py")

# Default redirect to creator page
st.switch_page("pages/creator.py")
