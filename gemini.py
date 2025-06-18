import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

genai.configure(api_key="AIzaSyCTaa04YX2Mo7iEPLad9-4NJKqAdg6Wqsg")

model = genai.GenerativeModel("gemini-2.0-flash")

def generate_self_appraisal_suggestions(responses: list[str]) -> str:
    prompt = (
        "You are an AI assistant helping an employee reflect on their work.\n"
        "Summarize the following answers into strengths, weaknesses, goals, and performance rating out of 5:\n\n"
    )
    for i, answer in enumerate(responses, 1):
        prompt += f"Q{i}: {answer}\n"

    response = model.generate_content(prompt)
    return response.text.strip()
