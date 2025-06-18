import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from chatbot import compiled
from typing import Dict, Any

app = FastAPI()

# Add debug handler for 422 errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation Error", 
            "errors": exc.errors(),
            "received_body": str(exc.body)
        }
    )

# In-memory session storage (use Redis/database in production)
sessions: Dict[str, Dict[str, Any]] = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

def get_or_create_session(session_id: str) -> Dict[str, Any]:
    """Get existing session or create a new one"""
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "projects": [],
            "current_index": 0,
            "missing": [],
            "followup": "",
            "conversation_history": [],
            "state": "initial"  # initial, extracting, filling, complete
        }
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
    
    try:
        # Process the message through the graph
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
        return {
            "final":final_state
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/session/{session_id}")
def get_session(session_id: str):
    """Get current session state"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    # return {
    #     "session_id": session_id,
    #     "projects": session["projects"],
    #     "current_project": session["current_index"] + 1 if session["projects"] else 0,
    #     "total_projects": len(session["projects"]),
    #     "state": session.get("state", "initial"),
    #     "conversation_history": session.get("conversation_history", [])
    # }
    return session

@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Clear a session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session cleared successfully"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/health")
def health_check():
    return {"status": "healthy", "active_sessions": len(sessions)}