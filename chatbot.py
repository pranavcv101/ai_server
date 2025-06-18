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
    projects: List[Project]
    current_index: int
    missing: List[str]
    followup: str
    conversation_history: List[dict]
    state: str

# Required fields and descriptions
REQUIRED_FIELDS = ["delivery", "accomplishments", "approach", "improvement", "timeframe"]
FIELD_DESCRIPTIONS = {
    "delivery": "Delivery Details - What was delivered/completed in this project?",
    "accomplishments": "Highlight of Accomplishments - What were your key achievements?",
    "approach": "Approach/Solution taken - What methods or strategies did you use?",
    "improvement": "Improvement possibilities - What could be done better next time?",
    "timeframe": "Time frame of the project/Job - When did this project take place?"
}

# Util to clean response
def clean_json_response(text: str) -> str:
    json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if json_match:
        return json_match.group(1)
    json_match = re.search(r'\{[\s\S]*\}', text)
    return json_match.group() if json_match else text

# Extraction node
def extract_projects(state: State) -> State:
    if state.get("projects"):
        return state

    prompt = f"""
    You are helping an employee fill a self-appraisal form. Extract project data.
    Fields: {REQUIRED_FIELDS}
    Instructions:
    - Identify each project
    - Extract available fields
    - Do NOT guess missing fields
    - Return only valid JSON:
      {{"projects": [{{"delivery": "", ...}}]}}

    Employee:
    {state["messages"]}
    """
    
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    try:
        cleaned = clean_json_response(response.text)
        parsed = json.loads(cleaned)
        state["projects"] = parsed.get("projects", []) or [{f: "" for f in REQUIRED_FIELDS}]
    except:
        state["projects"] = [{f: "" for f in REQUIRED_FIELDS}]

    state["current_index"] = 0
    return state

# Check missing fields
def check_missing_fields(state: State) -> State:
    idx = state["current_index"]
    project = state["projects"][idx]
    state["missing"] = [f for f in REQUIRED_FIELDS if not project.get(f)]

    if state["missing"]:
        missing = state["missing"]
        descriptions = [FIELD_DESCRIPTIONS[f] for f in missing]
        followup = "Please provide the following:\n" + "\n".join(f"- {d}" for d in descriptions)
        state["followup"] = followup
        state["state"] = "filling"
    else:
        state["followup"] = ""
        state["state"] = "ready_for_next"

    return state

# Update the project
def update_project(state: State) -> State:
    idx = state["current_index"]
    project = state["projects"][idx]
    missing = state["missing"]
    user_msg = state["messages"]

    prompt = f"""
    Employee is giving info to complete project fields.
    Current: {json.dumps(project)}
    Missing: {missing}
    Answer: "{user_msg}"

    Map this input to missing fields only. Do NOT guess. Return JSON:
    {{"delivery": "...", ...}}
    """
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        resp = model.generate_content(prompt)
        cleaned = clean_json_response(resp.text)
        update = json.loads(cleaned)
        for f in missing:
            if update.get(f):
                project[f] = update[f]
    except:
        pass

    state["projects"][idx] = project
    return state

# Decide next step
def next_or_end(state: State) -> str:
    if state.get("missing") and len(state["missing"]) > 0:
        # Ask user for more input, then wait
        return "ask_followup"

    # Done with current project, go to next
    current_idx = state.get("current_index", 0)
    total_projects = len(state.get("projects", []))
    if current_idx + 1 < total_projects:
        state["current_index"] = current_idx + 1
        return "check"

    # All done
    state["state"] = "complete"
    return END

# Ask follow-up
def ask_followup(state: State) -> State:
    # This is just preparing the followup message — not looping
    state["state"] = "waiting_for_user"
    return state

# LangGraph setup
graph = StateGraph(State)
graph.add_node("extract", extract_projects)
graph.add_node("check", check_missing_fields)
graph.add_node("update", update_project)
graph.add_node("ask_followup", ask_followup)

graph.set_entry_point("extract")
graph.add_edge("extract", "check")
graph.add_edge("ask_followup", "update")
graph.add_edge("update", "check")
graph.add_conditional_edges("check", next_or_end, {"ask_followup": "ask_followup", END: END})

compiled = graph.compile()