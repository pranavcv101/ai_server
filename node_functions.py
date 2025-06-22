from typing import TypedDict, List
import google.generativeai as genai
import json
import re
import requests

from api import fetch_all_appraisals,fetch_past_appraisals_by_employee,fetch_self_appraisal_by_employee
class Project(TypedDict):
    delivery: str
    accomplishments: str
    approach: str
    improvement: str
    timeframe: str

class State(TypedDict):
    session_id: str
    messages: str
    project: Project
    missing: List[str]
    followup: str
    conversation_history: List[dict]
    state: str
    role:str
    intent:str


genai.configure(api_key="AIzaSyCTaa04YX2Mo7iEPLad9-4NJKqAdg6Wqsg")
model = genai.GenerativeModel("gemini-2.5-flash")

REQUIRED_FIELDS = ["delivery", "accomplishments", "approach", "improvement", "timeframe"]
FIELD_DESCRIPTIONS = {
    "delivery": "Delivery Details - What was delivered/completed in this project?",
    "accomplishments": "Highlight of Accomplishments - What were your key achievements?",
    "approach": "Approach/Solution taken - What methods or strategies did you use?",
    "improvement": "Improvement possibilities - What could be done better next time?",
    "timeframe": "Time frame of the project/Job - When did this project take place?"
}

def clean_json_response(text: str) -> str:
    json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if json_match:
        return json_match.group(1)
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json_match.group()
    return text

def start_node(state:State)->State:
    return state

def check_role(state:State)->str:
    return state["role"]

def employee_query(state: State) -> State:
    user_msg = state.get("messages", "")
    role = state.get("role", "").strip().lower()
    history = state.get("conversation_history", [])
    history_text = "\n".join([f"{item['role'].capitalize()}: {item['content']}" for item in history[-5:]])

    prompt = f"""
    You are a message classifier for an  appraisal assistant. The user is an EMPLOYEE.
    The conversation so far:
    {history_text}
    User message: "{user_msg}"

    Classify the intent into ONLY one of these:
    - "self_appraisal_input"
    - "prev_summary_query"
    - "general_question"
    Respond with just the category name.
    """
    allowed_intents = ["self_appraisal_input", "prev_summary_query", "general_question"]

    try:
        response = model.generate_content(prompt)
        intent = response.text.strip().lower()
        if intent not in allowed_intents:
            # If the LLM returns something unexpected, default to a safe option.
            intent = "general_question"
        state["intent"] = intent
    except Exception as e:
        print("Intent classification failed:", e)
        state["intent"] = "general_question"
    return state

def extract_update(state: State) -> State:
    user_msg = state.get("messages", "")
    project = state.get("project", {})
    history = state.get("conversation_history", [])
    history_text = "\n".join([f"{item['role'].capitalize()}: {item['content']}" for item in history])

    context_text = "The employee is starting a new self-appraisal entry."
    if any(project.values()):
         context_text = f"""
    The employee is updating their self-appraisal.
    Current project data:
    {json.dumps(project, indent=2)}
    """

    prompt = f"""
    You are helping an employee complete their self-appraisal.
    {context_text}
    The employee just said: "{user_msg}"
    Based on their message and the conversation history, extract information and update the following fields.
    If information for a field is already present, append the new information unless it's a direct correction.
    Do not lose existing data. If you cannot extract info for a field, leave its value as it is in the current data.

    Field descriptions:
    {json.dumps(FIELD_DESCRIPTIONS, indent=2)}

    Return ONLY a valid JSON object with all fields.
    ```json
    {{
      "delivery": "...",
      "accomplishments": "...",
      "approach": "...",
      "improvement": "...",
      "timeframe": "..."
    }}
    ```
    """
    try:
        response = model.generate_content(prompt)
        cleaned = clean_json_response(response.text)
        updated_fields = json.loads(cleaned)
        for field, value in updated_fields.items():
            if value and field in project:
                if project[field] and value not in project[field]:
                    project[field] = f"{project[field]}\n{value}"
                else:
                    project[field] = value
            elif value:
                 project[field] = value
        state["project"] = project
    except Exception as e:
        print("Error during ext_up:", e)
    return check_appraisals(state)


def check_appraisals(state: State) -> State:
    project = state.get("project", {})
    missing = []
    for field in REQUIRED_FIELDS:
        value = (project.get(field) or "").strip()
        if not value or value.lower() in ["", "n/a", "none", "not specified"]:
            missing.append(field)
    state["missing"] = missing
    return state


def user_followup(state: State) -> State:
    missing = state.get("missing", [])
    if not missing:
        state["followup"] = "Great, all the project details are complete! You can review the information or let me know if you want to start another entry."
        state["state"] = "complete"
        return state

    first_missing = missing[0]
    prompt = f"""
    You are a friendly HR assistant helping an employee with their self-appraisal.
    You have asked some questions and now you need to ask for the next piece of missing information.
    One of the feild you need to ask about is: "{first_missing}"
    The description for this is: "{FIELD_DESCRIPTIONS[first_missing]}"
    Generate a SHORT, friendly, and conversational follow-up question to ask the user for this specific information.
    """
    try:
        response = model.generate_content(prompt)
        state["followup"] = response.text.strip()
    except Exception as e:
        print("Error generating follow-up message:", e)
        state["followup"] = f"That's helpful, thank you. Now, could you please tell me about the {first_missing}?"
    state["state"] = "filling"
    return state

def general_question(state: State) -> State:
    user_msg = state.get("messages", "")
    role = state.get("role", "").strip().lower()
    history = state.get("conversation_history", [])
    history_text = "\n".join([f"{item['role'].capitalize()}: {item['content']}" for item in history])
    if role == "employee":
        prompt = f"""
        You are an assistant that helps employees:
        1. Fill out their self-appraisal form
        2. View or understand their past appraisal summaries

        The employee just asked: "{user_msg}"
        The previous conversation history is: {history_text} 
        You are allowed to take relevant information from the conversation history to answer their question.
        Politely state your purpose and gently guide them back to one of your functions. Be friendly and helpful.
        """
    else:
        prompt = f"""
        You are an assistant that helps HR and Team Leads review past appraisal summaries of their employees.
        The user just asked: "{user_msg}"
        The previous conversation history is: {history_text} 
        You are allowed to take relevant information from the conversation history to answer their question.
        If their question is unrelated to performance reviews, gently remind them of your purpose.
        Suggest valid questions like "Show me John's last appraisal summary" or "Pull up the Q2 review for E7890".
        Keep the tone professional and helpful.
        """
    response = model.generate_content(prompt)
    state["followup"] = response.text.strip()
    return state

def prev_summary_query(state: State) -> State:
    employee_id_to_query = ""
    user_msg = state.get("messages", "")
    role = state.get("role")

    if role == "employee":
        employee_id_to_query = state.get("session_id", "")
    elif role in ["hr", "lead"]:
        prompt = f"From the message: '{user_msg}', extract the ID (e.g., 1 , 2 , 8632 etc). If no specific employee is mentioned, respond with NONE."
        try:
            response = model.generate_content(prompt)
            extracted_id = response.text.strip()
            if extracted_id.upper() != 'NONE':
                employee_id_to_query = extracted_id
        except Exception as e:
            print(f"Error extracting employee ID for {role}: {e}")
            state["followup"] = "I had trouble understanding which employee you're asking about. Please try again."
            return state

    if not employee_id_to_query:
        state["followup"] = "I'm sorry, I need to know which employee's summary you'd like to see. Please specify their ID."
        return state

    api_response = fetch_past_appraisals_by_employee(employee_id_to_query)

    if api_response.get("success"):
        raw_data = api_response["data"]
        summary_prompt = f"""
        Based on the following appraisal data, write a concise, professional summary for a {role}.
        Data: {json.dumps(raw_data, indent=2)}
        Generate a friendly, human-readable summary. Start by addressing the user (e.g., "Here is the summary for...").
        """
        try:
            summary_response = model.generate_content(summary_prompt)
            state["followup"] = summary_response.text.strip()
        except Exception as e:
            print(f"Error generating summary: {e}")
            state["followup"] = f"I found the data but couldn't create a summary. Raw info:\n{json.dumps(raw_data, indent=2)}"
    else:
        error_message = api_response.get("error", "An unknown error occurred")
        state["followup"] = f"Sorry, I could not retrieve the summary for '{employee_id_to_query}'. The system reported: '{error_message}'."

    state["state"] = "complete"
    return state

def check_relevance(state: State) -> str:
    return state["intent"]

def isComplete(state: State) -> str:
    if not state.get("missing"):
        return "yes"
    return "no"


def completed_appraisal(state: State) -> State:
    if len(state.get("missing", [])) == 0:
        state["followup"] = "Great! All projects have been captured successfully. Here's your complete self-appraisal data:\n\n"
        for field in REQUIRED_FIELDS:
            value = state["project"].get(field, "N/A")
            state["followup"] += f"**{FIELD_DESCRIPTIONS[field]}**: {value}\n"
        state["state"] = "complete"
    return state
    

# This function would go in your node_functions.py file
# Make sure the 'State' type and the 'model' object are available in this scope

def hr_lead_query(state: State) -> State:
   
    user_msg = state.get("messages", "")
    history = state.get("conversation_history", [])
    # Format the last 5 turns of conversation for context
    history_text = "\n".join([f"{item['role'].capitalize()}: {item['content']}" for item in history[-5:]])

    # The list of valid intents for an HR Lead
    allowed_intents = [
        "prev_summary_query",
        "self_appraisal_summary",
        "score_predicter",
        "general_question"
    ]

    # A detailed prompt to guide the LLM's classification
    prompt = f"""
    You are an intelligent message classifier for an HR appraisal assistant.
    The user is an HR LEAD. Their role is to review employee appraisals, generate summaries, and predict performance scores.

    The conversation so far:
    {history_text}

    User message: "{user_msg}"

    Based on the user's message, classify their intent into ONLY one of the following categories:
    - "prev_summary_query": The HR Lead is asking for a summary of a past appraisal for a specific employee. (e.g., "Show me last year's summary for John Doe", "What was Jane's review in Q2?")
    - "self_appraisal_summary": The HR Lead wants you to generate a new summary based on an employee's recent self-appraisal text. (e.g., "Summarize this self-appraisal for me.", "Can you give me the key points from this?")
    - "score_predicter": The HR Lead is asking for a predicted performance score based on appraisal data. (e.g., "What score would you predict for this employee?", "Predict the performance rating.")
    - "general_question": The user is asking a general question that doesn't fit the other categories. (e.g., "What are the deadlines for this quarter?", "How does this tool work?")

    Respond with only the category name and nothing else.
    """

    try:
        # Assuming 'model' is your initialized generative AI model (e.g., from genai.GenerativeModel)
        response = model.generate_content(prompt)
        
        # Clean up the response to be safe
        intent = response.text.strip().lower().replace('"', '')

        # Fallback to a safe default if the LLM hallucinates an invalid category
        if intent not in allowed_intents:
            print(f"Warning: LLM returned an unexpected intent '{intent}'. Defaulting to 'general_question'.")
            intent = "general_question"
        
        # Update the state with the classified intent
        state["intent"] = intent

    except Exception as e:
        print(f"Error during HR intent classification: {e}")
        # If the API call fails for any reason, default to a safe intent
        state["intent"] = "general_question"
        
    return state

# This function would go in your node_functions.py file
# It assumes 'model' and 'fetch_self_appraisal_by_employee' are available in its scope.

def self_appraisal_summary(state: State) -> State:
    employee_id_to_query = ""
    user_msg = state.get("messages", "")
    role = state.get("role")

    # Step 1: Determine which employee's appraisal to summarize
    if role == "employee":
        # An employee can only summarize their own appraisal
        employee_id_to_query = state.get("session_id", "")
    elif role in ["hr", "lead"]:
        # An HR/Lead must specify which employee
        prompt = f"From the user's request: '{user_msg}', extract the employee's ID (e.g., 101, 102, 8632). If no specific employee ID is mentioned, respond with NONE."
        try:
            response = model.generate_content(prompt)
            extracted_id = response.text.strip().replace('"', '')
            if extracted_id.upper() != 'NONE':
                employee_id_to_query = extracted_id
        except Exception as e:
            print(f"Error extracting employee ID for {role}: {e}")
            state["followup"] = "I had trouble understanding which employee you're asking about. Please specify their ID (e.g., 'summarize for employee 101')."
            return state

    if not employee_id_to_query:
        state["followup"] = "I'm sorry, I need to know whose appraisal you'd like to summarize. Please specify their ID."
        return state

    # Step 2: Fetch the raw self-appraisal data using the helper function
    try:
        appraisal_text = fetch_self_appraisal_by_employee(employee_id_to_query)
        if not appraisal_text:
            state["followup"] = f"I'm sorry, I could not find any self-appraisal data for employee ID {employee_id_to_query}."
            return state
    except Exception as e:
        print(f"Database/fetch error for employee {employee_id_to_query}: {e}")
        state["followup"] = "I encountered an error trying to retrieve the appraisal data. Please try again later."
        return state

    # Step 3: Generate the summary using the LLM
    summary_prompt = f"""
    You are an expert HR Analyst. Your task is to summarize an employee's self-appraisal text into a structured, professional summary. 
    Focus on key achievements, stated areas for improvement, and future goals. Use clear bullet points.

    Here is the raw self-appraisal text:
    ---
    {appraisal_text}
    ---

    Please provide the summary.
    """
    try:
        summary_response = model.generate_content(summary_prompt)
        summary = summary_response.text
        # The final summary is placed in the 'followup' field to be sent to the user.
        state["followup"] = f"Here is the summary for employee {employee_id_to_query}:\n\n{summary}"
    except Exception as e:
        print(f"Error generating summary for employee {employee_id_to_query}: {e}")
        state["followup"] = "I was able to retrieve the appraisal, but encountered an error while trying to summarize it."
    
    return state




# This list remains the single source of truth for valid competencies.
# It should be defined where the node function can access it.
COMPETENCIES_LIST = [
    "Technical",
    "Functional",
    "Communication",
    "Energy & Drive",
    "Responsibilites & Trust",
    "Teamwork",
    "Managing Processes & Work"
]

def score_predicter(state: State) -> State:
    """
    Analyzes a user's message to identify a competency, and then predicts a
    performance score (1-10) based on the described strengths and weaknesses.
    
    The entire process uses a single LLM call with a detailed prompt and
    expects a structured JSON response.
    """
    user_msg = state.get("messages", "")

    # This single, comprehensive prompt asks the LLM to do everything at once.
    scoring_prompt = f"""
    You are a senior HR Manager, an expert in performance evaluation. Your task is to analyze an employee's performance description, identify the single most relevant competency from a given list, and predict a performance score on a scale of 1 to 10.

    **Step 1: Identify the Competency**
    Read the user's message and determine which one of these competencies it refers to:
    {COMPETENCIES_LIST}

    **Step 2: Use the Scoring Rubric**
    Analyze the strengths and weaknesses in the message against this rubric:
    - **1-2 (Significant Improvement Needs):** Major gaps in skill or execution.
    - **3-4 (Improvement Needs):** Performance is inconsistent and below expectations.
    - **5-6 (Meets Expectations):** A capable performer who generally meets requirements.
    - **7-8 (Exceeds Expectations):** A strong performer who consistently exceeds expectations.
    - **9-10 (Exceptional):** A role model who far exceeds expectations; an expert.

    **User's Message to Analyze:**
    "{user_msg}"

    **Instructions:**
    Provide your response as a single, clean JSON object with three keys:
    1. "competency": The name of the competency you identified from the list. This value MUST be one of the strings from the provided list.
    2. "score": An integer between 1 and 10 based on your analysis.
    3. "reasoning": A brief, one-sentence explanation for your score.

    Example Response Format: {{"competency": "Technical", "score": 8, "reasoning": "The employee shows exceptional skill in modern technologies but has a noted weakness in a key legacy area."}}
    """

    try:
        score_response = model.generate_content(scoring_prompt)
        raw_text = score_response.text
        
        # Use regex to reliably find the JSON block, even if the LLM adds extra text.
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not json_match:
            raise ValueError("The model's response did not contain a valid JSON object.")
            
        parsed_json = json.loads(json_match.group(0))
        
        competency = parsed_json.get("competency")
        score = parsed_json.get("score")
        reasoning = parsed_json.get("reasoning")

        # --- Validation Step ---
        if not all([competency, score, reasoning]):
            raise ValueError("The returned JSON is missing one or more required keys.")
        if competency not in COMPETENCIES_LIST:
            raise ValueError(f"The model returned an invalid competency '{competency}' not in the official list.")
        if not isinstance(score, int) or not (1 <= score <= 10):
            raise ValueError("The score must be an integer between 1 and 10.")

        # --- Format the Final Output ---
        final_output = (
            f"**Prediction for {competency}**\n\n"
            f"**Predicted Score:** {score}/10\n"
            f"**Reasoning:** {reasoning}"
        )
        state["followup"] = final_output

    except Exception as e:
        print(f"Error during score prediction: {e}")
        # Provide a helpful error message to the user
        state["followup"] = "I'm sorry, I encountered an error while trying to predict the score. Please ensure your message clearly mentions a competency and describes performance."

    return state