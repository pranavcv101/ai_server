# app/main.py
from fastapi import FastAPI, HTTPException
from models import AppraisalRequest, AppraisalSummary, AppraisalData
from gemini import generate_self_appraisal_suggestions, rate_performance_factors, summarize_appraisals
from models import HRRecommendationRequest, HRRecommendationResponse
from gemini import generate_hr_recommendations
import httpx  # for making async HTTP requests



BACKEND_URL_PAST_APPRAISAL_BY_ID = "http://localhost:3000/appraisal/past-appraisals"
BACKEND_URL_SELF_APPRAISAL_BY_ID = "http://localhost:3000/self-appraisal"
BACKEND_URL_APPRAISALS = "http://localhost:3000/appraisal"


async def summarize_past_appraisals(employee_id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL_PAST_APPRAISAL_BY_ID}/{employee_id}")
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch appraisal data from backend")

        appraisal_data_list = response.json()

        if not appraisal_data_list:
            raise HTTPException(status_code=404, detail="No appraisals found for this employee")

        employee_name = appraisal_data_list[0].get("employee", {}).get("name", "The employee")
        summary = summarize_appraisals(employee_name, appraisal_data_list)
        return AppraisalSummary(summary=summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI summarization failed: {str(e)}")
