import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Explicitly load variables from your .env file
load_dotenv()

# 2. Look for either GEMINI_API_KEY or GOOGLE_API_KEY
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

# 3. Safety check
if not api_key:
    raise ValueError("API Key not found. Please ensure you have a .env file with your key in the same folder.")

# 4. Configure the SDK
genai.configure(api_key=api_key)

# We use gemini-2.5-flash as it is highly optimized for speed and multi-step chaining
MODEL_NAME = "gemini-2.5-flash"

# ==========================================
# Phase 1: Define the Agents (Personas)
# ==========================================

# Agent 1: The Client
client_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are the Operations Director of a mid-sized logistics company. "
        "Describe your business needs, pain points, and rough timeline in a standard "
        "paragraph format. Keep it concise but detailed enough for a software team to understand."
    )
)

# Agent 2: The Solutions Architect
architect_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are a Senior Solutions Architect at a software services company. "
        "Write a formal Request for Proposal (RFP) based on the client's brief. "
        "Include: 1. Executive Summary, 2. Project Scope, 3. Proposed Technology Stack, "
        "4. Project Deliverables, and 5. Estimated Timeline (in weeks). "
        "Output standard Markdown."
    )
)

# Agent 3: The Financial Analyst
finance_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are a Financial Analyst for a software agency. Review the provided RFP "
        "and generate a detailed budget document. Break the budget down into: "
        "1. Roles required, 2. Estimated hours per role, 3. Hourly rate per role, "
        "4. Infrastructure/Cloud costs, and 5. Total Estimated Cost. "
        "Format this strictly as a clean Markdown data table."
    )
)

# Agent 4: The Manager / Reviewer
reviewer_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are the Agency Director. Review both the RFP and the Budget. "
        "State whether the budget accurately reflects the scope of the RFP. "
        "If the total budget exceeds $100,000, explicitly suggest three technical or "
        "feature areas where the client could cut scope to save money."
    )
)

# ==========================================
# Phase 2: Execute the Agentic Workflow
# ==========================================

# RENAME THIS FUNCTION TO MATCH WHAT app.py EXPECTS:
def create_rfp_workflow(project_description):
    print("🚀 Starting Agentic Workflow...\n")

    # Step 1: Client generates the raw brief
    print("⏳ Agent 1 (Client) is generating business requirements...")
    client_response = client_agent.generate_content(project_description)
    client_brief = client_response.text
    print("✅ Client Brief Generated.\n")

    # Step 2: Architect drafts the RFP based on the brief
    print("⏳ Agent 2 (Architect) is drafting the formal RFP...")
    rfp_response = architect_agent.generate_content(f"Client Brief:\n{client_brief}")
    rfp_document = rfp_response.text
    print("✅ RFP Document Generated.\n")

    # Step 3: Financial Analyst calculates the budget based on the RFP
    print("⏳ Agent 3 (Financial Analyst) is calculating the budget...")
    budget_response = finance_agent.generate_content(f"RFP Document:\n{rfp_document}")
    budget_document = budget_response.text
    print("✅ Budget Generated.\n")

    # Step 4: Manager reviews the combined output
    print("⏳ Agent 4 (Manager) is reviewing the proposal...")
    combined_docs = f"--- RFP ---\n{rfp_document}\n\n--- BUDGET ---\n{budget_document}"
    review_response = reviewer_agent.generate_content(combined_docs)
    manager_review = review_response.text
    print("✅ Review Complete.\n")

    # Combine the outputs nicely so your UI can display the final results
    final_output = f"""
# 📋 Project Proposal & Analysis

## 1. Executive Request Brief (Simulated Client)
{client_brief}

---

{rfp_document}

---

## 💰 Financial & Resource Plan
{budget_document}

---

## 🔍 Internal Review Board Comments
{manager_review}
"""
    return final_output

# ==========================================
# Run the Demo (Optional local testing)
# ==========================================
if __name__ == "__main__":
    seed_idea = "I need a custom web portal to track shipments and manage our delivery drivers via mobile."
    print(create_rfp_workflow(seed_idea))