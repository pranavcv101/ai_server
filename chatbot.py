# chatbot_graph.py
import json
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
import google.generativeai as genai

# Set your Gemini API key
genai.configure(api_key="AIzaSyCTaa04YX2Mo7iEPLad9-4NJKqAdg6Wqsg")

class State(TypedDict):
    messages: str
    delivery: str
    accomplishments: str
    approach: str
    improvement: str
    timeframe: str
    missing: list[str]  # Add this to track missing fields

graph = StateGraph(State)

def extract_fields(state: State):
    user_messages = state["messages"]
    
    prompt = f"""Extract the following fields from this project description in JSON format:
- delivery: What was delivered?
- accomplishments: What were the key achievements?
- approach: What methodology or technologies were used?
- improvement: What could be improved?
- timeframe: When was this project done?

Return ONLY JSON. Message:
{user_messages}"""
    
    model = genai.GenerativeModel("gemini-2.0-flash")
    resp = model.generate_content(prompt)
    
    try:
        parsed = json.loads(resp.text)
        # Ensure all expected fields exist in the parsed data
        for field in ["delivery", "accomplishments", "approach", "improvement", "timeframe"]:
            if field not in parsed:
                parsed[field] = ""
    except Exception as e:
        print("Error parsing Gemini response:", e)
        parsed = {
            "delivery": "",
            "accomplishments": "",
            "approach": "",
            "improvement": "",
            "timeframe": ""
        }
    
    # Update the state with all fields
    state.update(parsed)
    return state

def check_completeness(state: State):
    missing = [field for field in ["delivery", "accomplishments", "approach", "improvement", "timeframe"] 
              if not state.get(field)]
    state["missing"] = missing
    return state

graph.add_node("extract", extract_fields)
graph.add_node("check", check_completeness)

graph.add_edge(START, "extract")
graph.add_edge("extract", "check")
graph.add_edge("check", END)

compiled = graph.compile()