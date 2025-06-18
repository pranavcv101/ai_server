from fastapi import FastAPI, HTTPException
from models import AppraisalRequest, AppraisalSummary
from gemini import generate_self_appraisal_suggestions

app = FastAPI()




@app.post("/ai/self-appraisal", response_model=AppraisalSummary)
async def self_appraisal_summary(request: AppraisalRequest):
    try:
        summary = generate_self_appraisal_suggestions(request.responses)
        return AppraisalSummary(summary=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


