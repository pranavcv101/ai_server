import json
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List
import google.generativeai as genai
import re

# Set your Gemini API key
genai.configure(api_key="AIzaSyCTaa04YX2Mo7iEPLad9-4NJKqAdg6Wqsg")

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


# def is_initial_project_description(state: State) -> bool:
#     return len(state.get("conversation_history", [])) <= 1 or state.get("state") == "initial"

# def extract_project(state: State) -> State:
#     user_messages = state["messages"]
#     if state.get("project") and not is_initial_project_description(state):
#         return state

#     prompt = f"""
#     You are helping an employee fill out their self-appraisal form. Extract project details from their description.

#     Required fields:
#     - delivery: What was delivered/completed
#     - accomplishments: Key achievements and highlights
#     - approach: Methods, strategies, or solutions used
#     - improvement: Areas for improvement or lessons learned
#     - timeframe: When the project took place

#     Instructions:
#     1. Extract available information for each field
#     2. If information is missing or unclear, leave the field empty
#     3. Return valid JSON only

#     Format:
#     {{"project": {{"delivery": "...", "accomplishments": "...", "approach": "...", "improvement": "...", "timeframe": "..."}}}}

#     Employee's description:
#     {user_messages}
#     """

#     model = genai.GenerativeModel("gemini-2.0-flash")
#     resp = model.generate_content(prompt)

#     try:
#         cleaned_json = clean_json_response(resp.text)
#         parsed = json.loads(cleaned_json)
#         project = parsed.get("project", {field: "" for field in REQUIRED_FIELDS})
#         state["project"] = project
#         state["state"] = "extracting"
#     except Exception as e:
#         print(f"Error parsing Gemini response: {e}")
#         print(f"Raw response: {resp.text}")
#         state["project"] = {field: "" for field in REQUIRED_FIELDS}
#         state["state"] = "extracting"

#     return state

# def check_missing_fields(state: State) -> State:
#     project = state.get("project", {})
#     missing = []
#     for field in REQUIRED_FIELDS:
#         value = (project.get(field) or "").strip()
#         if not value or value.lower() in ["", "n/a", "none", "not specified"]:
#             missing.append(field)
#     state["missing"] = missing

#     if missing:
#         followup = "Let me help you complete your project details.\n\n"
#         missing_descriptions = [FIELD_DESCRIPTIONS[field] for field in missing]
#         if len(missing) == 1:
#             followup += f"I need more information about: {missing_descriptions[0]}"
#         else:
#             followup += "I need more information about the following:\n"
#             for i, desc in enumerate(missing_descriptions, 1):
#                 followup += f"{i}. {desc}\n"
#         followup += "\nPlease provide these details, and I'll help organize them properly."
#         state["followup"] = followup
#         state["state"] = "filling"
#     else:
#         state["followup"] = ""
#         state["state"] = "complete"
#     return state

# def update_project(state: State) -> State:
#     user_msg = state.get("messages", "")
#     missing = state.get("missing", [])
#     current_project = state.get("project", {field: "" for field in REQUIRED_FIELDS})

#     prompt = f"""
#     An employee is providing information to complete their project details.

#     Current project data: {json.dumps(current_project, indent=2)}

#     Missing fields: {missing}
#     Field descriptions:
#     {json.dumps({field: FIELD_DESCRIPTIONS[field] for field in missing}, indent=2)}

#     Employee's response: "{user_msg}"

#     Instructions:
#     1. Map the employee's response to the appropriate missing fields
#     2. Keep existing data unchanged
#     3. Return updated JSON
#     4. Don’t fill fields with hallucinated content. If info is missing, keep it blank.

#     Format:
#     {{"delivery": "...", "accomplishments": "...", "approach": "...", "improvement": "...", "timeframe": "..."}}
#     """

#     model = genai.GenerativeModel("gemini-2.0-flash")
#     try:
#         resp = model.generate_content(prompt)
#         cleaned_json = clean_json_response(resp.text)
#         updated_data = json.loads(cleaned_json)
#         for field in REQUIRED_FIELDS:
#             if updated_data.get(field):
#                 current_project[field] = updated_data[field]
#         state["project"] = current_project
#     except Exception as e:
#         print(f"Update error: {e}")
#     return state

# def next_or_end(state: State) -> str:
#     if state.get("missing"):
#         return "ask_followup"
#     return END

# def ask_followup(state: State) -> State:
    # return state

# Add nodes to graph
# graph.add_node("extract", extract_project)
# graph.add_node("check", check_missing_fields)
# graph.add_node("update", update_project)
# graph.add_node("ask_followup", ask_followup)

# # Define edges
# graph.add_edge(START, "extract")
# graph.add_edge("extract", "check")

# graph.add_conditional_edges(
#     "check", next_or_end, {"ask_followup": "ask_followup", END: END}
# )

# graph.add_edge("ask_followup", "update")
# graph.add_edge("update", "check")

#############
#############
#############
#############
#############
def clean_json_response(text: str) -> str:
    json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if json_match:
        return json_match.group(1)
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json_match.group()
    return text


def check(state: State) -> State:
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

    if not missing:
        state["followup"] = ""
        state["state"] = "complete"
        return state

    followup = "Let me help you complete your project details.\n\n"

    missing_descriptions = [FIELD_DESCRIPTIONS[field] for field in missing]
    if len(missing) == 1:
        followup += f"I need more information about: {missing_descriptions[0]}"
    else:
        followup += "I need more information about the following:\n"
        for i, desc in enumerate(missing_descriptions, 1):
            followup += f"{i}. {desc}\n"

    followup += "\nPlease provide these details, and I'll help organize them properly."

    state["followup"] = followup
    state["state"] = "filling"
    return state

graph.add_node("ext_up",ext_up)
graph.add_node("check",check)
graph.add_node("user_followup",user_followup)

##edges
graph.add_edge(START,"check")
graph.add_conditional_edges(
    "check",isComplete , { "no":"ext_up","yes":END }
)
graph.add_edge("ext_up","user_followup")
graph.add_edge("user_followup",END)


########
########
########
########
compiled = graph.compile()
