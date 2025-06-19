import json
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List
import google.generativeai as genai
import re

# Set your Gemini API key
genai.configure(api_key="AIzaSyCTaa04YX2Mo7iEPLad9-4NJKqAdg6Wqsg")
model = genai.GenerativeModel("gemini-2.0-flash")

class Project(TypedDict):
    delivery: str
    accomplishments: str
    approach: str
    improvement: str
    timeframe: str

class State(TypedDict):
    messages: str
    project: Project
    missing: List[str]
    followup: str
    conversation_history: List[dict]
    state: str
    role:str
    intent:str

# Initialize graph
graph = StateGraph(State)

# Helper: Required fields
REQUIRED_FIELDS = ["delivery", "accomplishments", "approach", "improvement", "timeframe"]
FIELD_DESCRIPTIONS = {
    "delivery": "Delivery Details - What was delivered/completed in this project?",
    "accomplishments": "Highlight of Accomplishments - What were your key achievements?",
    "approach": "Approach/Solution taken - What methods or strategies did you use?",
    "improvement": "Improvement possibilities - What could be done better next time?",
    "timeframe": "Time frame of the project/Job - When did this project take place?"
}


#############
#############
#############
#############
#############
def set_relevance(state: State) -> State:
    user_msg = state.get("messages", "")
    role = state.get("role", "").strip().lower()
    history = state.get("conversation_history", [])

    history_text = "\n".join([f"{item['role'].capitalize()}: {item['content']}" for item in history[-5:]])  # use last 5 turns

    if role in ["hr", "lead"]:
        prompt = f"""
        You are a message classifier for an HR appraisal assistant chatbot. The user is an {role.upper()}.

        The conversation so far:
        {history_text}

        User message:
        "{user_msg}"

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

        User message:
        "{user_msg}"

        Classify the intent into ONLY one of these:
        - "self_appraisal_input"
        - "prev_summary_query"
        - "general_question"

        Respond with just the category name.
        """

    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        response = model.generate_content(prompt)
        intent = response.text.strip().lower()
        state["intent"]=intent
    except Exception as e:
        print("Intent classification failed:", e)
        state["intent"] = "chit_chat_or_unknown"
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

def isComplete(state: State) -> str:
    if not state.get("missing"):  # Either None or empty list
        return "yes"
    return "no"

def ext_up(state: State) -> State:
    user_msg = state.get("messages", "")
    project = state.get("project", {})
    missing = state.get("missing", [])

    if not missing:
        return state  # Nothing to update

    prompt = f"""
    You are helping an employee complete their self-appraisal project information.
    
    Current project data:
    {json.dumps(project, indent=2)}
    
    The employee has NOT yet provided details for the following fields: {missing}
    
    Field descriptions:
    {json.dumps({field: FIELD_DESCRIPTIONS[field] for field in missing}, indent=2)}
    
    The employee just said:
    "{user_msg}"

    Based on this, try to fill in the missing fields only. 
    - Keep other existing fields unchanged.
    - If you can't extract clear info for a field, leave it empty.
    -If the employee gives additional information about feilds which are already filled , try to include the newly gained information without losing the previous

    Return valid JSON in this format:
    {{
      "delivery": "...",
      "accomplishments": "...",
      "approach": "...",
      "improvement": "...",
      "timeframe": "..."
    }}
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        response = model.generate_content(prompt)
        cleaned = clean_json_response(response.text)
        updated_fields = json.loads(cleaned)

        newly_filled = []

        for field in missing:
            new_val = (updated_fields.get(field) or "").strip()
            if new_val:
                project[field] = new_val
                newly_filled.append(field)

        # Remove the newly filled fields from missing
        state["missing"] = [f for f in missing if f not in newly_filled]
        state["project"] = project

    except Exception as e:
        print("Error during ext_up:", e)

    return state

def user_followup(state: State) -> State:
    missing = state.get("missing", [])
    project = state.get("project", {})
    history = state.get("conversation_history", [])

    if not missing:
        state["followup"] = ""
        state["state"] = "complete"
        return state

    first_missing = missing[0]

    # Use a smaller history slice for brevity
    history_text = "\n".join([
        f"{item['role'].capitalize()}: {item['content']}"
        for item in history[-3:]
    ])

    prompt = f"""
    You are helping an employee complete their self-appraisal form.

    The employee has been discussing the following:
    {history_text}

    The current project details are:
    {json.dumps(project, indent=2)}

    One of the missing feild is "{first_missing}"

    Description of that field:
    "{FIELD_DESCRIPTIONS[first_missing]}"

    Based on the above, generate a SHORT and FRIENDLY follow-up message asking  for this one missing detail.
    Also consider the previos conversation so that you know the context
    Keep it simple and clear.
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        response = model.generate_content(prompt)
        followup_message = response.text.strip()
    except Exception as e:
        print("Error generating follow-up message:", e)
        followup_message = f"Could you please let me know: {FIELD_DESCRIPTIONS[first_missing]}"

    state["followup"] = followup_message
    state["state"] = "filling"
    return state



def prev_summary_query():
    pass

def general_question(state: State) -> State:
    user_msg = state.get("messages", "")
    role = state.get("role", "").strip().lower()
    if role == "employee":
            prompt = f"""
            You are an assistant that helps employees:
            1. Fill out their self-appraisal form
            2. View or understand their past appraisal summaries

            However, the employee just asked:
            "{user_msg}"

            Politely remind them of your main purpose and guide them back to providing information related to self-appraisal or past reviews. 
            If the question is not relevant, kindly redirect them. Be friendly and helpful.
            """
    elif role in ["hr", "lead"]:
            prompt = f"""
            You are an assistant that helps HRs and Team Leads:
            - Review past appraisal summaries of employees
            - Provide performance insights and suggestions for evaluations

            However, the user just asked:
            "{user_msg}"

            If their question is unrelated to performance appraisal analysis or team evaluation, gently remind them of your purpose and suggest questions like:
            - "Show me John's last appraisal summary"
            - "What are the improvement areas for Team A?"
            Keep the tone professional and helpful.
            """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    state["followup"] = response.text.strip()
    return state

def check_relevance(state:State)->State:
    return state["intent"]

def check_role(state: State) -> State:
    return state["role"]

def set_role(state: State) -> State:
    return state


graph.add_node("check_role",set_role)
graph.add_node("HR_query",set_relevance)
graph.add_node("Lead_query",set_relevance)


####################
graph.add_node("set_relevance",set_relevance)
graph.add_node("ext_up",ext_up) 
graph.add_node("check_appraisals",check_appraisals)
graph.add_node("user_followup",user_followup)
graph.add_node("prev_summary_query",prev_summary_query)
graph.add_node("general_question",general_question)
#####################

##edges
graph.add_edge(START, "check_role")
graph.add_conditional_edges("check_role",
                            check_role,
                            {
                                "hr":"HR_query",
                                "lead":"Lead_query",
                                "employee":"set_relevance"
                            })
graph.add_conditional_edges("HR_query",
                            check_relevance,
                            {
                                "prev_summary_query":"prev_summary_query",
                                "general_question":"general_question"
                            })
graph.add_conditional_edges("Lead_query",
                            check_relevance,
                            {   
                                "prev_summary_query":"prev_summary_query",
                                "general_question":"general_question"
                            })
##############################
# graph.add_edge(START,"set_relevance")
graph.add_conditional_edges("set_relevance",
                            check_relevance,
                            {
                                "prev_summary_query":"prev_summary_query",
                                "general_question":"general_question"
                            })

graph.add_conditional_edges(
    "check_appraisals",isComplete , { "no":"ext_up","yes":END }
)
graph.add_edge("ext_up","user_followup")
graph.add_edge("user_followup",END)
graph.add_edge("general_question",END)
graph.add_edge("prev_summary_query",END)


########
########
########
########
compiled = graph.compile()
