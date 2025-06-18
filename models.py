from pydantic import BaseModel
from typing import List

class AppraisalRequest(BaseModel):
    responses: List[str]

class AppraisalSummary(BaseModel):
    summary: str
