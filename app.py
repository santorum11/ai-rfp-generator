import streamlit as st
from rfp_crew import create_rfp_workflow

# Configure the Streamlit page layout
st.set_page_config(page_title="Agentic RFP Builder", layout="wide")

st.title("🚀 Agentic RFP & Budget Estimation Platform")
st.subheader("Automate end-to-end proposal creation using role-playing AI agents")

# Input field for raw project inputs
raw_input = st.text_area(
    "Enter raw project scope or initial client requirements:", 
    placeholder="e.g., Build a mobile e-commerce application for a retail chain with payment gateway integration and a real-time tracking dashboard...",
    height=200
)

if st.button("Generate Proposal", type="primary"):
    if raw_input.strip():
        # Visual loading indicators for the hackathon presentation
        with st.spinner("Executing Multi-Agent Workflow... [BA analyzing requirements ➔ Architect compiling budget ➔ Writer drafting final RFP]"):
            try:
                # Trigger the backend orchestration
                final_proposal = create_rfp_workflow(raw_input)
                
                st.success("✨ Proposal Package Generated Successfully!")
                st.markdown("---")
                st.markdown(final_proposal)
            except Exception as e:
                st.error(f"An error occurred during workflow execution: {e}")
    else:
        st.warning("Please provide a valid project description before initiating the crew workflow.")