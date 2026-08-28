import streamlit as st


st.set_page_config(page_title="OneCall AI", page_icon="⚕️", layout="wide")

st.title("OneCall AI")
st.subheader("One member. One representative. One resolution.")
st.write("Reducing transfers, repeat calls, handle time, and servicing cost.")

st.info("Multi-agent healthcare payer servicing prototype using synthetic data only.")

scenario = st.selectbox(
    "Select a demo member-service scenario",
    (
        "Claim denied despite approved authorization",
        "Authorization actually missing",
        "Coverage showing inactive",
        "Payer system failure and recovery",
    ),
)

if st.button("Investigate with OneCall AI"):
    st.write(scenario)
