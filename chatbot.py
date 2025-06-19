import json
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List
import google.generativeai as genai
import re
import requests


genai.configure(api_key="AIzaSyCTaa04YX2Mo7iEPLad9-4NJKqAdg6Wqsg")
model = genai.GenerativeModel("gemini-2.5-flash")

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

graph = StateGraph(State)

REQUIRED_FIELDS = ["delivery", "accomplishments", "approach", "improvement", "timeframe"]
FIELD_DESCRIPTIONS = {
    "delivery": "Delivery Details - What was delivered/completed in this project?",
    "accomplishments": "Highlight of Accomplishments - What were your key achievements?",
    "approach": "Approach/Solution taken - What methods or strategies did you use?",
    "improvement": "Improvement possibilities - What could be done better next time?",
    "timeframe": "Time frame of the project/Job - When did this project take place?"
}

def fetch_data_from_server(employee_id: str) -> dict:
    API_URL = "http://localhost:3000/appraisal/past-appraisals"
    params = {"employee_id": employee_id}

    print(f"--- REAL API CALL: Fetching data for '{employee_id}' from {API_URL} ---")

    try:
        response = requests.get(f"{API_URL}/{employee_id}", timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}

    except requests.exceptions.HTTPError as http_err:
        # This handles errors like 404 Not Found specifically
        error_message = f"HTTP error occurred: {http_err}"
        print(error_message)
        if http_err.response.status_code == 404:
            return {"success": False, "error": "Employee not found on the server."}
        else:
            return {"success": False, "error": f"A server error occurred (Status code: {http_err.response.status_code})."}

    except requests.exceptions.RequestException as req_err:
        # This is a general catch-all for network issues (e.g., server is down)
        error_message = f"A network error occurred: {req_err}"
        print(error_message)
        return {"success": False, "error": "Could not connect to the appraisal server. Please ensure the server is running and accessible."}
    
    except json.JSONDecodeError:
        # This handles cases where the server returns a non-JSON response
        error_message = "Failed to parse the server's response. It was not valid JSON."
        print(error_message)
        return {"success": False, "error": "The server returned data in an unexpected format."}


def set_relevance(state: State) -> State:
    user_msg = state.get("messages", "")
    role = state.get("role", "").strip().lower()
    history = state.get("conversation_history", [])

    history_text = "\n".join([f"{item['role'].capitalize()}: {item['content']}" for item in history[-5:]])

    if role in ["hr", "lead"]:
        prompt = f"""
        You are a message classifier for an HR appraisal assistant chatbot. The user is an {role.upper()}.
        The conversation so far:
        {history_text}
        User message: "{user_msg}"
        Classify the intent into ONLY one of these:
        - "prev_summary_query"
        - "general_question"
        Respond with just the category name.
        """
    else:  # For employee
        prompt = f"""
        You are a message classifier for an HR appraisal assistant chatbot. The user is an EMPLOYEE.
        The conversation so far:
        {history_text}
        User message: "{user_msg}"
        Classify the intent into ONLY one of these:
        - "self_appraisal_input"
        - "prev_summary_query"
        - "general_question"
        Respond with just the category name.
        """

    try:
        response = model.generate_content(prompt)
        intent = response.text.strip().lower()
        allowed_intents = ["self_appraisal_input", "prev_summary_query", "general_question"]
        if intent not in allowed_intents:
            intent = "general_question"
        state["intent"] = intent
    except Exception as e:
        print("Intent classification failed:", e)
        state["intent"] = "general_question"
    return state


def clean_json_response(text: str) -> str:
    json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if json_match:
        return json_match.group(1)
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json_match.group()
    return text


def check_appraisals(state: State) -> State:
    project = state.get("project", {})
    missing = []
    for field in REQUIRED_FIELDS:
        value = (project.get(field) or "").strip()
        if not value or value.lower() in ["", "n/a", "none", "not specified"]:
            missing.append(field)
    state["missing"] = missing
    return state


def ext_up(state: State) -> State:
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
    The next thing you need to ask about is: "{first_missing}"
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
        prompt = f"From the message: '{user_msg}', extract the employee's name or ID (e.g., 'John Doe', 'E7890'). If no specific employee is mentioned, respond with NONE."
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
        state["followup"] = "I'm sorry, I need to know which employee's summary you'd like to see. Please specify their name or ID."
        return state

    api_response = fetch_data_from_server(employee_id_to_query)

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


def set_role(state: State) -> State:
    return state

def check_relevance(state: State) -> str:
    return state["intent"]

def isComplete(state: State) -> str:
    if not state.get("missing"):
        return "yes"
    return "no"

    

graph.add_node("set_relevance", set_relevance)
graph.add_node("check_appraisals", check_appraisals)
graph.add_node("ext_up", ext_up)
graph.add_node("user_followup", user_followup)
graph.add_node("prev_summary_query", prev_summary_query)
graph.add_node("general_question", general_question)



graph.add_edge(START, "set_relevance")
graph.add_conditional_edges("set_relevance", check_relevance, {"self_appraisal_input": "ext_up", "prev_summary_query": "prev_summary_query", "general_question": "general_question"})
graph.add_conditional_edges("ext_up", isComplete, {"no": "user_followup", "yes": END})
graph.add_edge("user_followup", END)
graph.add_edge("general_question", END)
graph.add_edge("prev_summary_query", END)

compiled = graph.compile()
