import os
import re
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("API Key not found. Please ensure you have a .env file with your key.")

# --- INITIALIZE NEW UNIFIED CLIENT ---
client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

# --- AGENT PERSONA CONFIGURATIONS ---
discovery_config = types.GenerateContentConfig(
    system_instruction=(
        "You are a Lead Technical Business Analyst. Review the client's initial brief and "
        "ask exactly 3 targeted, highly technical clarifying questions that are necessary to create "
        "an accurate Software RFP and budget. Output ONLY the numbered questions."
    )
)

client_config = types.GenerateContentConfig(
    system_instruction="You are the Operations Director. Synthesize the initial brief and the answers to the BA's questions into a cohesive, detailed project background."
)

architect_config = types.GenerateContentConfig(
    system_instruction=(
        "You are a Senior Solutions Architect. Write a formal RFP including Executive Summary, Scope, Tech Stack, and Timeline based on the comprehensive brief. "
        "CRITICAL INSTRUCTION: At the very bottom of your response, you MUST provide a comma-separated list of the required roles enclosed in brackets. "
        "Example: [ROLES: Frontend Developer, Backend Developer, QA Engineer, Project Manager]"
    )
)

finance_config = types.GenerateContentConfig(
    system_instruction=(
        "You are a Financial Analyst. Review the RFP and generate a budget. "
        "You will be provided with specific hourly rates for the roles. You MUST use these exact roles and rates to calculate the final costs. "
        "Format the output as a clean Markdown data table."
    )
)

reviewer_config = types.GenerateContentConfig(
    system_instruction="You are the Agency Director. Review the budget. If it exceeds $100,000, suggest three scope cuts."
)

# --- SMART RETRY WRAPPER WITH NEW CLIENT ---
def generate_with_retry(prompt, config, max_retries=4):
    """Catches rate limits (429) and server overloads (503) automatically instead of crashing."""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            
            # 1. Handle standard 429 rate limits / quota issues
            if "429" in error_msg or "Quota" in error_msg or "ResourceExhausted" in error_msg:
                if attempt == max_retries - 1:
                    raise e
                print(f"⚠️ Rate limit hit. Waiting 65 seconds for Google to reset quota (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(65)
                
            # 2. Handle temporary 503 server overloads / high traffic spikes
            elif "503" in error_msg or "UNAVAILABLE" in error_msg.upper() or "DEMAND" in error_msg.upper():
                if attempt == max_retries - 1:
                    raise e
                print(f"⚠️ Google servers are busy (503). Taking a breath for 10 seconds (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(10)
                
            # 3. Raise any other unexpected exceptions immediately (e.g., invalid key)
            else:
                raise e

# --- PHASE 1: Discovery Phase ---
def generate_clarifying_questions(company_name, project_description):
    print("⏳ Agent 0 (Discovery) generating questions...")
    prompt = f"Client: {company_name}\nInitial Scope: {project_description}"
    return generate_with_retry(prompt, discovery_config)

# --- PHASE 2: Draft RFP & Extract Roles ---
def draft_rfp_and_get_roles(company_name, project_description, qa_answers):
    print("⏳ Agent 1 (Client) synthesizing requirements...")
    full_context = f"Company: {company_name}\nInitial Scope: {project_description}\nAdditional Details: {qa_answers}"
    client_brief = generate_with_retry(full_context, client_config)

    time.sleep(5) 

    print("⏳ Agent 2 (Architect) drafting RFP...")
    rfp_document = generate_with_retry(f"Comprehensive Client Brief:\n{client_brief}", architect_config)

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
    
    budget_document = generate_with_retry(finance_prompt, finance_config)

    time.sleep(5)

    print("⏳ Agent 4 (Manager) reviewing...")
    manager_review = generate_with_retry(f"--- RFP ---\n{rfp_document}\n\n--- BUDGET ---\n{budget_document}", reviewer_config)

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