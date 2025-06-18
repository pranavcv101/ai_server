# app/main.py
from fastapi import FastAPI, HTTPException
from models import AppraisalRequest, AppraisalSummary, AppraisalData
from gemini import generate_self_appraisal_suggestions, rate_performance_factors, summarize_appraisals
import httpx  # for making async HTTP requests
from models import PerformanceFactorRequest, PerformanceFactorResponse, PerformanceFactorRating


app = FastAPI()

BACKEND_URL = "http://localhost:3000/appraisals"

@app.post("/ai/self-appraisal", response_model=AppraisalSummary)
async def self_appraisal_summary(request: AppraisalRequest):
    """
    AI Assistant for Employees: Suggest summary from questionnaire answers.
    """
    try:
        summary = generate_self_appraisal_suggestions(request.responses)
        return AppraisalSummary(summary=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI summarization failed: {str(e)}")


@app.get("/ai/summarize/{employee_id}", response_model=AppraisalSummary)
async def summarize_past_appraisals(employee_id: int):
    """
    AI Summary for HR or Employee: Summarize past appraisals using employee ID.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/{employee_id}")
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch appraisal data from backend")

        appraisal_data = response.json()
        appraisals = [appraisal_data]  # format as list in case of future expansion
        employee_name = appraisal_data.get("employee", {}).get("name", "The employee")

        summary = summarize_appraisals(employee_name, appraisals)
        return AppraisalSummary(summary=summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI summarization failed: {str(e)}")



@app.post("/ai/score-performance", response_model=PerformanceFactorResponse)
async def score_performance_factors(request: PerformanceFactorRequest):
    try:
        # Convert request to list of dicts for Gemini
        input_data = [factor.dict() for factor in request.factors]
        scored = rate_performance_factors(input_data)

        # Validate and return
        ratings = [PerformanceFactorRating(**item) for item in scored]
        return PerformanceFactorResponse(ratings=ratings)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI scoring failed: {str(e)}")