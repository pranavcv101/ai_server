import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from chatbot import compiled

app = FastAPI()

class ChatRequest(BaseModel):
    session_id: str = None
    message: str

# app.py
@app.post("/chat")
def chat(req: ChatRequest):
    state_input = {
        "messages": req.message,
        "delivery": "",
        "accomplishments": "",
        "approach": "",
        "improvement": "",
        "timeframe": "",
        "missing": []
    }
    
    try:
        # Get the final state after graph execution
        final_state = compiled.invoke(state_input)
        
        # Debug: Print the final state to see what we got
        print("Final state:", final_state)
        
        if final_state["missing"]:
            reply = f"Please provide more details about: {', '.join(final_state['missing'])}"
        else:
            summary = {
                "delivery": final_state["delivery"],
                "accomplishments": final_state["accomplishments"],
                "approach": final_state["approach"],
                "improvement": final_state["improvement"],
                "timeframe": final_state["timeframe"]
            }
            reply = f"Project Summary:\n{json.dumps(summary, indent=2)}"
        
        return {
            "reply": reply,
            "missing": final_state["missing"],
            "debug_state": final_state  # For debugging
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))