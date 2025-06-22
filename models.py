# app/models.py
from pydantic import BaseModel
from typing import TypedDict, List


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