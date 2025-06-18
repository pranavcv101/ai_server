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

def clean_json_response(text: str) -> str:
    """Extract and clean JSON from Gemini response"""
    # Try to find JSON block
    json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if json_match:
        return json_match.group(1)
    
    # Try to find any JSON-like structure
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json_match.group()
    
    return text

def is_initial_project_description(state: State) -> bool:
    """Check if this is the initial project description vs follow-up answers"""
    return len(state.get("conversation_history", [])) <= 1 or state.get("state") == "initial"

# Step 1: Extract all projects from the initial user message
def extract_projects(state: State) -> State:
    user_messages = state["messages"]
    
    # Skip extraction if we already have projects and this is a follow-up
    if state.get("projects") and not is_initial_project_description(state):
        return state
    
    prompt = f"""
    You are helping an employee fill out their self-appraisal form. Extract project details from their description.
    
    Required fields for each project:
    - delivery: What was delivered/completed
    - accomplishments: Key achievements and highlights
    - approach: Methods, strategies, or solutions used
    - improvement: Areas for improvement or lessons learned
    - timeframe: When the project took place
    
    Instructions:
    1. Identify each separate project mentioned
    2. Extract available information for each field
    3. If information is missing or unclear, leave the field empty
    4. Return valid JSON only
    
    Format:
    {{"projects": [{{"delivery": "...", "accomplishments": "...", "approach": "...", "improvement": "...", "timeframe": "..."}}, ...]}}
    
    Employee's description:
    {user_messages}
    """
    
    model = genai.GenerativeModel("gemini-2.0-flash")
    resp = model.generate_content(prompt)
    
    try:
        cleaned_json = clean_json_response(resp.text)
        parsed = json.loads(cleaned_json)
        extracted_projects = parsed.get("projects", [])
        
        # Initialize empty projects if none found
        if not extracted_projects:
            extracted_projects = [{"delivery": "", "accomplishments": "", "approach": "", "improvement": "", "timeframe": ""}]
        
        state["projects"] = extracted_projects
        state["current_index"] = 0
        state["state"] = "extracting"
        
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Raw response: {resp.text}")
        # Create a default project to fill
        state["projects"] = [{"delivery": "", "accomplishments": "", "approach": "", "improvement": "", "timeframe": ""}]
        state["current_index"] = 0
        state["state"] = "extracting"
    
    return state

# Step 2: Check for missing fields in the current project
def check_missing_fields(state: State) -> State:
    idx = state.get("current_index", 0)
    projects = state.get("projects", [])
    
    if idx >= len(projects):
        state["missing"] = []
        state["followup"] = ""
        state["state"] = "complete"
        return state
    
    project = projects[idx]
    missing = []
    
    for field in REQUIRED_FIELDS:
        value = project.get(field, "").strip()
        if not value or value.lower() in ["", "n/a", "none", "not specified"]:
            missing.append(field)
    
    state["missing"] = missing
    
    if missing:
        # Create a friendly follow-up message
        project_num = idx + 1
        total_projects = len(projects)
        
        if total_projects > 1:
            followup = f"Great! I've identified {total_projects} projects. Let's work on Project {project_num}.\n\n"
        else:
            followup = "Let me help you complete your project details.\n\n"
        
        missing_descriptions = [FIELD_DESCRIPTIONS[field] for field in missing]
        
        if len(missing) == 1:
            followup += f"I need more information about: {missing_descriptions[0]}"
        else:
            followup += f"I need more information about the following:\n"
            for i, desc in enumerate(missing_descriptions, 1):
                followup += f"{i}. {desc}\n"
        
        followup += "\nPlease provide these details, and I'll help organize them properly."
        state["followup"] = followup
        state["state"] = "filling"
    else:
        state["followup"] = ""
        state["state"] = "ready_for_next"
    
    return state

# Step 3: Update project with user's answer to missing fields
def update_project(state: State) -> State:
    user_msg = state.get("messages", "")
    idx = state.get("current_index", 0)
    missing = state.get("missing", [])
    projects = state.get("projects", [])
    
    if idx >= len(projects) or not missing:
        return state
    
    current_project = projects[idx]
    
    prompt = f"""
    An employee is providing information to complete their project details.
    
    Current project data: {json.dumps(current_project, indent=2)}
    
    Missing fields to fill: {missing}
    Field descriptions:
    {json.dumps({field: FIELD_DESCRIPTIONS[field] for field in missing}, indent=2)}
    
    Employee's response: "{user_msg}"
    
    Instructions:
    1. Map the employee's response to the appropriate missing fields
    2. Keep existing data unchanged
    3. Be intelligent about mapping - if they mention timeframes, map to timeframe field, etc.
    4. If unclear, make reasonable assumptions based on context
    5. Return complete project JSON with all fields
    6. Donot hallucainate and fill missing data incase of missing data ask for it and add it to the missing array please
    Return valid JSON format:
    {{"delivery": "...", "accomplishments": "...", "approach": "...", "improvement": "...", "timeframe": "..."}}
    """
    
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    try:
        resp = model.generate_content(prompt)
        cleaned_json = clean_json_response(resp.text)
        updated_data = json.loads(cleaned_json)
        
        # Update only the missing fields, preserve existing data
        for field in REQUIRED_FIELDS:
            if field in missing and updated_data.get(field):
                state["projects"][idx][field] = updated_data[field]
            elif not state["projects"][idx].get(field):
                # If field was empty and we have new data, update it
                if updated_data.get(field):
                    state["projects"][idx][field] = updated_data[field]
                    
    except Exception as e:
        print(f"Update error: {e}")
        # Fallback: Simple mapping based on field priority
        response_parts = user_msg.split('.')
        for i, field in enumerate(missing[:len(response_parts)]):
            if response_parts[i].strip():
                state["projects"][idx][field] = response_parts[i].strip()
    
    return state

# Step 4: Move to next project or finish
def next_or_end(state: State) -> str:
    """Determine next step in the conversation flow"""
    # Check if we have missing fields for current project
    if state.get("missing") and len(state["missing"]) > 0:
        return "ask_followup"
    
    # Move to next project if available
    current_idx = state.get("current_index", 0)
    total_projects = len(state.get("projects", []))
    
    if current_idx + 1 < total_projects:
        state["current_index"] = current_idx + 1
        return "check"
    
    # All projects completed
    state["state"] = "complete"
    return END

# Step 5: Ask for follow-up information
def ask_followup(state: State) -> State:
    """Handle the follow-up asking step"""
    # The followup message is already set in check_missing_fields
    return state

# Add nodes to graph
graph.add_node("extract", extract_projects)
graph.add_node("check", check_missing_fields)
graph.add_node("update", update_project)
graph.add_node("ask_followup", ask_followup)

# Define edges
graph.add_edge(START, "extract")
graph.add_edge("extract", "check")

# Conditional routing from check
graph.add_conditional_edges(
    "check", 
    next_or_end, 
    {
        "ask_followup": "ask_followup",
        END: END
    }
)

graph.add_edge("ask_followup", "update")
graph.add_edge("update", "check")

# Compile the graph - removed config parameter
compiled = graph.compile()