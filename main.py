# app/main.py
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models import AppraisalRequest, AppraisalSummary, AppraisalData
from gemini import generate_self_appraisal_suggestions, rate_performance_factors, summarize_appraisals
from models import HRRecommendationRequest, HRRecommendationResponse
from gemini import generate_hr_recommendations
import httpx  # for making async HTTP requests
from models import PerformanceFactorRequest, PerformanceFactorResponse, PerformanceFactorRating
from chatbot import compiled

app = FastAPI()

BACKEND_URL_PAST_APPRAISAL_BY_ID = "http://localhost:3000/appraisal/past-appraisals"
BACKEND_URL_SELF_APPRAISAL_BY_ID = "http://localhost:3000/self-appraisal"
BACKEND_URL_APPRAISALS = "http://localhost:3000/appraisal"

sessions: Dict[str, Dict[str, Any]] = {}


class ChatRequest(BaseModel):
    session_id: str
    role:str
    message: str

def get_or_create_session(session_id: str) -> Dict[str, Any]:
    """Get existing session or create a new one"""
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "messages": [],
            "project": {},
            "current_index": 0,
            "missing": [],
            "followup": "",
            "conversation_history": [],
            "state": "",  # initial, extracting, filling, complete
            "role":"",
            "intent":""     }
    return sessions[session_id]


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    # Get or create session
    session_memory = get_or_create_session(req.session_id)
    
    # Add current message to history
    session_memory["conversation_history"].append({"role": "user", "content": req.message})
    session_memory["messages"] = req.message
    session_memory["state"]="initial"
    session_memory["role"]=req.role
    
    try:
        # Process the message through the graph
        # final_state = await compiled.invoke_async(session_memory)
        final_state = compiled.invoke(session_memory)

        
        # Update session with new state
        sessions[req.session_id] = final_state
        
        # # Determine response
        # if final_state["followup"]:
        #     reply = final_state["followup"]
        #     # Add bot response to history
        #     final_state["conversation_history"].append({"role": "assistant", "content": reply})
        # else:
        #     reply = f"Great! All projects have been captured successfully. Here's your complete self-appraisal data:\n\n"
        #     for i, project in enumerate(final_state['projects'], 1):
        #         reply += f"**Project {i}:**\n"
        #         reply += f"• Delivery Details: {project.get('delivery', 'N/A')}\n"
        #         reply += f"• Accomplishments: {project.get('accomplishments', 'N/A')}\n"
        #         reply += f"• Approach/Solution: {project.get('approach', 'N/A')}\n"
        #         reply += f"• Improvements: {project.get('improvement', 'N/A')}\n"
        #         reply += f"• Timeframe: {project.get('timeframe', 'N/A')}\n\n"
            
        #     final_state["conversation_history"].append({"role": "assistant", "content": reply})
        #     final_state["state"] = "complete"
        
        # return {
        #     "reply": reply,
        #     "projects": final_state["projects"],
        #     "missing": final_state["missing"],
        #     "session_state": final_state["state"],
        #     "total_projects": len(final_state["projects"]),
        #     "current_project": final_state["current_index"] + 1 if final_state["projects"] else 0
        # }
        if final_state["state"] == "complete":
            del sessions[req.session_id]
            
        return {
            "final":final_state
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

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


# Route 2: AI Summary of Past Appraisals by Employee ID
@app.get("/ai/past-appraisal-summarize/{employee_id}", response_model=AppraisalSummary)
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




# ✅ Route 3: AI Summary for Specific Self-Appraisal Entry by ID
@app.get("/ai/self-appraisal-summary/{id}", response_model=AppraisalSummary)
async def summarize_self_appraisal(id: int):
    """
    AI Summary for a specific Self Appraisal Entry by ID.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL_SELF_APPRAISAL_BY_ID}/{id}")

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch self appraisal data from backend")

        data = response.json()

        if not data or "appraisal" not in data:
            raise HTTPException(status_code=404, detail="No self appraisal data found")

        # Format questions + answers for Gemini
        responses = [
            f"What were the delivery details? - {data.get('delivery_details')}",
            f"What were the accomplishments? - {data.get('accomplishments')}",
            f"What was your approach to the solution? - {data.get('approach_solution')}",
            f"What are possible improvements? - {data.get('improvement_possibilities')}",
            f"What was the project time frame? - {data.get('project_time_frame')}"
        ]

        summary = generate_self_appraisal_suggestions(responses)
        return AppraisalSummary(summary=summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI summarization failed: {str(e)}")



@app.post("/ai/score-performance", response_model=PerformanceFactorResponse)
async def score_performance_factors(request: PerformanceFactorRequest):
    try:
        # Convert request to list of dicts for Gemini
        input_data = [factor.model_dump() for factor in request.factors]
        scored = rate_performance_factors(input_data)

        # Validate and return
        ratings = [PerformanceFactorRating(**item) for item in scored]
        return PerformanceFactorResponse(ratings=ratings)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI scoring failed: {str(e)}")
    




@app.get("/ai/hr-recommendations/{employee_id}", response_model=HRRecommendationResponse)
async def hr_recommendations(employee_id: int):
    """
    AI HR Recommendations:
    Fetch past appraisal data for a given employee ID from the backend,
    then use Gemini to generate recommendations such as workshops, upskill sessions,
    and coaching topics.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Fetch appraisal data for the given employee from the backend API.
            response = await client.get(f"{BACKEND_URL_APPRAISALS}/{employee_id}")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500, 
                detail="Failed to fetch appraisal data from backend"
            )

        appraisal_data = response.json()

        if not appraisal_data:
            raise HTTPException(
                status_code=404, 
                detail="No appraisals found for this employee"
            )

        # If the backend returns a single appraisal (object), wrap it in a list.
        # Otherwise, if it returns a list, use it directly.
        if isinstance(appraisal_data, dict):
            appraisal_data_list = [appraisal_data]
        else:
            appraisal_data_list = appraisal_data

        # Extract the employee name from the first appraisal entry.
        employee_name = appraisal_data_list[0].get("employee", {}).get("name", "The employee")

        # Here, we assume each appraisal in appraisal_data_list contains a key
        # "performance_factors" and that you want to pass the entire appraisal data
        # for generating recommendations.
        # The generate_hr_recommendations() function should know how to iterate over
        # these entries and pick out the necessary details.
        recommendations = generate_hr_recommendations(appraisal_data_list)
        return HRRecommendationResponse(recommendations=recommendations)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI recommendation generation failed: {str(e)}"
        )