import os
import re
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found.")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

MODEL_NAME = "llama-3.3-70b-versatile"

# --- ENHANCED AGENT PERSONA SYSTEM INSTRUCTIONS ---
DISCOVERY_SYSTEM = (
    "You are a Lead Technical Business Analyst. Review the client's initial brief and "
    "ask exactly 3 targeted, highly technical clarifying questions. Output ONLY the numbered questions."
)

CLIENT_SYSTEM = (
    "You are the Operations Director. Synthesize the initial brief and the answers into a "
    "comprehensive, multi-paragraph project background. Be formal and detailed."
)

ARCHITECT_SYSTEM = (
    "You are a Senior Solutions Architect. Write a professional, comprehensive, and LONG Software RFP. "
    "Your response must be at least 800-1000 words. "
    "Use standard Markdown headers (##) for each section. "
    "INCLUDE THESE SECTIONS: \n"
    "## 1. Executive Summary\n"
    "## 2. Project Goals & Objectives\n"
    "## 3. Detailed Technical Scope\n"
    "## 4. Recommended Technology Stack\n"
    "## 5. Functional & Non-Functional Requirements\n"
    "## 6. Implementation Timeline & Milestones\n"
    "## 7. Quality Assurance & Testing Plan\n\n"
    "CRITICAL: At the very end of your response, provide the roles in brackets: [ROLES: Role 1, Role 2]"
)

FINANCE_SYSTEM = (
    "You are a Financial Analyst. Create a detailed budget table using the provided roles, rates, and currency."
)

REVIEWER_SYSTEM = "You are the Agency Director. Audit the RFP and Budget for risks. Suggest 3 improvements."

# --- ROBUST INTERFACE WRAPPER ---
def generate_with_retry(prompt, system_instruction, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6, # Increased temperature slightly for more detailed writing
                max_tokens=4096   # Ensure the model doesn't cut off early
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt == max_retries - 1: raise e
            time.sleep(3)

def generate_clarifying_questions(company_name, project_description, status_callback=None):
    if status_callback: status_callback("🕵️ Lead BA Agent is evaluating boundaries...")
    prompt = f"Client: {company_name}\nScope: {project_description}"
    return generate_with_retry(prompt, DISCOVERY_SYSTEM)

def draft_rfp_and_get_roles(company_name, project_description, qa_answers, status_callback=None):
    if status_callback: status_callback("📝 Synthesizing corporate context...")
    full_context = f"Company: {company_name}\nScope: {project_description}\nAnswers: {qa_answers}"
    client_brief = generate_with_retry(full_context, CLIENT_SYSTEM)

    if status_callback: status_callback("🏗️ Solutions Architect is drafting a COMPREHENSIVE RFP...")
    rfp_document = generate_with_retry(f"Brief:\n{client_brief}", ARCHITECT_SYSTEM)

    roles = []
    match = re.search(r'\[ROLES:\s*(.*?)\]', rfp_document, re.IGNORECASE)
    if match:
        roles = [role.strip() for role in match.group(1).split(',')]
    else:
        roles = ["Frontend Developer", "Backend Developer", "Project Manager"]

    clean_rfp = re.sub(r'\[ROLES:\s*(.*?)\]', '', rfp_document, flags=re.IGNORECASE).strip()
    return client_brief, clean_rfp, roles

def calculate_budget_and_review(company_name, client_brief, rfp_document, custom_rates, currency_symbol, status_callback=None):
    if status_callback: status_callback(f"📊 Calculating budget in {currency_symbol}...")
    rates_text = "\n".join([f"- {role}: {currency_symbol}{rate}/hr" for role, rate in custom_rates.items()])
    finance_prompt = f"RFP:\n{rfp_document}\n\nRoles/Rates ({currency_symbol}):\n{rates_text}"
    budget_document = generate_with_retry(finance_prompt, FINANCE_SYSTEM)

    if status_callback: status_callback("🔍 Agency Director auditing items...")
    manager_review = generate_with_retry(f"RFP:\n{rfp_document}\nBudget:\n{budget_document}", REVIEWER_SYSTEM)

    final_output = f"# 📋 Proposal for {company_name}\n\n## 1. Executive Brief\n{client_brief}\n\n---\n\n{rfp_document}\n\n---\n\n## 💰 Budget ({currency_symbol})\n{budget_document}\n\n---\n\n## 🔍 Reviewer Comments\n{manager_review}"
    return final_output, budget_document