import os
import re
import time
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("API Key not found. Please ensure you have a .env file with your key.")

genai.configure(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

# --- AGENT PERSONAS ---
# NEW: The Discovery Agent
discovery_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are a Lead Technical Business Analyst. Review the client's initial brief and "
        "ask exactly 3 targeted, highly technical clarifying questions that are necessary to create "
        "an accurate Software RFP and budget. Output ONLY the numbered questions."
    )
)

client_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction="You are the Operations Director. Synthesize the initial brief and the answers to the BA's questions into a cohesive, detailed project background."
)

architect_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are a Senior Solutions Architect. Write a formal RFP including Executive Summary, Scope, Tech Stack, and Timeline based on the comprehensive brief. "
        "CRITICAL INSTRUCTION: At the very bottom of your response, you MUST provide a comma-separated list of the required roles enclosed in brackets. "
        "Example: [ROLES: Frontend Developer, Backend Developer, QA Engineer, Project Manager]"
    )
)

finance_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are a Financial Analyst. Review the RFP and generate a budget. "
        "You will be provided with specific hourly rates for the roles. You MUST use these exact roles and rates to calculate the final costs. "
        "Format the output as a clean Markdown data table."
    )
)

reviewer_agent = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction="You are the Agency Director. Review the budget. If it exceeds $100,000, suggest three scope cuts."
)

# --- SMART RETRY WRAPPER ---
def generate_with_retry(agent, prompt, max_retries=4):
    for attempt in range(max_retries):
        try:
            return agent.generate_content(prompt).text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota" in error_msg or "ResourceExhausted" in error_msg:
                if attempt == max_retries - 1:
                    raise e
                print(f"⚠️ Rate limit hit. Waiting 65 seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(65)
            else:
                raise e

# --- PHASE 1: Discovery Phase ---
def generate_clarifying_questions(company_name, project_description):
    print("⏳ Agent 0 (Discovery) generating questions...")
    prompt = f"Client: {company_name}\nInitial Scope: {project_description}"
    return generate_with_retry(discovery_agent, prompt)

# --- PHASE 2: Draft RFP & Extract Roles ---
def draft_rfp_and_get_roles(company_name, project_description, qa_answers):
    print("⏳ Agent 1 (Client) synthesizing requirements...")
    full_context = f"Company: {company_name}\nInitial Scope: {project_description}\nAdditional Details: {qa_answers}"
    client_brief = generate_with_retry(client_agent, full_context)

    time.sleep(5) 

    print("⏳ Agent 2 (Architect) drafting RFP...")
    rfp_document = generate_with_retry(architect_agent, f"Comprehensive Client Brief:\n{client_brief}")

    roles = []
    match = re.search(r'\[ROLES:\s*(.*?)\]', rfp_document, re.IGNORECASE)
    if match:
        roles = [role.strip() for role in match.group(1).split(',')]
    else:
        roles = ["Frontend Developer", "Backend Developer", "Project Manager"]

    clean_rfp = re.sub(r'\[ROLES:\s*(.*?)\]', '', rfp_document, flags=re.IGNORECASE).strip()
    return client_brief, clean_rfp, roles

# --- PHASE 3: Calculate Budget with Custom Roles/Rates ---
def calculate_budget_and_review(company_name, client_brief, rfp_document, custom_rates):
    print("⏳ Agent 3 (Finance) calculating budget with custom rates...")
    
    rates_text = "\n".join([f"- {role}: ${rate}/hr" for role, rate in custom_rates.items()])
    finance_prompt = f"RFP Document:\n{rfp_document}\n\nCRITICAL: Use ONLY these exact roles and hourly rates for your estimation table:\n{rates_text}"
    
    budget_document = generate_with_retry(finance_agent, finance_prompt)

    time.sleep(5)

    print("⏳ Agent 4 (Manager) reviewing...")
    manager_review = generate_with_retry(reviewer_agent, f"--- RFP ---\n{rfp_document}\n\n--- BUDGET ---\n{budget_document}")

    final_output = f"""
# 📋 Project Proposal for {company_name}

## 1. Executive Request Brief
{client_brief}

---

{rfp_document}

---

## 💰 Financial Plan (Based on Client Rates)
{budget_document}

---

## 🔍 Internal Review Board Comments
{manager_review}
"""
    return final_output, budget_document