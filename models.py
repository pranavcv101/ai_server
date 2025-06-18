# app/models.py
from pydantic import BaseModel
from typing import List


class AppraisalRequest(BaseModel):
    responses: List[str]  # For the self-appraisal questionnaire


class AppraisalSummary(BaseModel):
    summary: str


class AppraisalData(BaseModel):
    employeeName: str
    appraisals: list  # Raw data as returned from your Node.js backend

class PerformanceFactorInput(BaseModel):
    competency: str
    strengths: str
    improvements: str

class PerformanceFactorRating(BaseModel):
    competency: str
    score: int
    reason: str

class PerformanceFactorRequest(BaseModel):
    factors: List[PerformanceFactorInput]

class PerformanceFactorResponse(BaseModel):
    ratings: List[PerformanceFactorRating]