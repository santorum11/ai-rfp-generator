import streamlit as st
from rfp_crew import generate_clarifying_questions, draft_rfp_and_get_roles, calculate_budget_and_review
from fpdf import FPDF

st.set_page_config(page_title="Agentic RFP Builder", layout="wide")

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=11)
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_text)
    return bytes(pdf.output())

def markdown_to_csv(markdown_text):
    csv_lines = []
    for line in markdown_text.split('\n'):
        if '|' in line:
            clean_line = line.strip().strip('|')
            csv_lines.append(",".join([col.strip() for col in clean_line.split('|')]))
    return "\n".join(csv_lines)

# --- 🧠 SESSION STATE MEMORY ---
if "step" not in st.session_state:
    st.session_state.step = 1

st.title("🚀 Agentic RFP & Budget Estimation Platform")

# ==========================================
# STEP 1: INITIAL INPUT
# ==========================================
if st.session_state.step == 1:
    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("Client / Company Name:", placeholder="e.g., Acme Logistics")
    
    raw_input = st.text_area("Raw Project Scope:", height=150)

    if st.button("Step 1: Start Discovery Phase", type="primary"):
        if raw_input.strip() and company_name.strip():
            with st.spinner("Lead BA Agent is analyzing scope and generating questions..."):
                questions = generate_clarifying_questions(company_name, raw_input)
                st.session_state.company_name = company_name
                st.session_state.raw_input = raw_input
                st.session_state.questions = questions
                st.session_state.step = 2
                st.rerun()
        else:
            st.error("Please provide both a Company Name and a Project Scope.")

# ==========================================
# STEP 2: DISCOVERY (QA)
# ==========================================
elif st.session_state.step == 2:
    st.info("The AI needs a few more details to generate an accurate RFP.")
    st.markdown(f"### 🔍 Clarifying Questions\n{st.session_state.questions}")
    
    user_answers = st.text_area("Provide your answers here:", height=150)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Step 2: Draft RFP", type="primary"):
            if user_answers.strip():
                with st.spinner("AI Architect is drafting the RFP and identifying roles..."):
                    brief, rfp, roles = draft_rfp_and_get_roles(
                        st.session_state.company_name, 
                        st.session_state.raw_input, 
                        user_answers
                    )
                    st.session_state.client_brief = brief
                    st.session_state.rfp_text = rfp
                    # Format roles for the interactive data editor
                    st.session_state.role_data = [{"Role": r, "Rate ($/hr)": 50} for r in roles]
                    st.session_state.step = 3
                    st.rerun()
            else:
                st.error("Please provide answers to continue.")
    with col2:
        if st.button("Start Over"):
            st.session_state.step = 1
            st.rerun()

# ==========================================
# STEP 3: DYNAMIC ROLE EDITOR
# ==========================================
elif st.session_state.step == 3:
    st.success("✨ RFP Drafted!")
    st.markdown("### 💸 Adjust Roles & Rates")
    st.info("You can edit rates, add new roles (click the '+' at the bottom of the table), or delete roles by selecting a row and pressing 'Delete'.")
    
    # Interactive Data Editor
    edited_roles = st.data_editor(
        st.session_state.role_data,
        num_rows="dynamic",
        column_config={
            "Role": st.column_config.TextColumn("Role Required", required=True),
            "Rate ($/hr)": st.column_config.NumberColumn("Hourly Rate ($)", min_value=10, required=True)
        },
        use_container_width=True
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Step 3: Calculate Final Budget", type="primary"):
            # Convert edited table back to a dictionary for the backend
            custom_rates = {row["Role"]: row["Rate ($/hr)"] for row in edited_roles if row["Role"]}
            
            with st.spinner("Finance Agent calculating costs based on your custom team..."):
                final_out, budget_text = calculate_budget_and_review(
                    st.session_state.company_name,
                    st.session_state.client_brief,
                    st.session_state.rfp_text,
                    custom_rates
                )
                st.session_state.budget_text = budget_text
                st.session_state.final_out = final_out
                st.session_state.step = 4
                st.rerun()
    with col2:
        if st.button("Start Over"):
            st.session_state.step = 1
            st.rerun()

# ==========================================
# STEP 4: FINAL OUTPUT
# ==========================================
elif st.session_state.step == 4:
    st.success("✅ Multi-Agent Workflow Complete!")
    
    st.markdown("### 💾 Export Documents")
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
    with btn_col1:
        pdf_bytes = create_pdf(st.session_state.rfp_text)
        st.download_button("📄 Download RFP (PDF)", data=pdf_bytes, file_name=f"{st.session_state.company_name}_RFP.pdf", mime="application/pdf")
    with btn_col2:
        csv_data = markdown_to_csv(st.session_state.budget_text)
        st.download_button("📊 Download Budget (CSV)", data=csv_data, file_name=f"{st.session_state.company_name}_Budget.csv", mime="text/csv")
    with btn_col3:
        if st.button("Start a New Project"):
            st.session_state.step = 1
            st.rerun()
            
    st.markdown("---")
    st.markdown(st.session_state.final_out)