# app/gemini.py
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

# Configure Gemini
genai.configure(api_key="AIzaSyCTaa04YX2Mo7iEPLad9-4NJKqAdg6Wqsg")

# Gemini model for fast responses (self-appraisal suggestions)
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


def summarize_appraisals(employee_name: str, appraisals: list[dict]) -> str:
    prompt = f"Summarize past appraisals for {employee_name}. Highlight:\n"
    prompt += "- Growth trends\n- Repeating strengths/challenges\n- Overall performance tone\n\n"

    for i, a in enumerate(appraisals):
        prompt += f"\nAppraisal {i + 1}:\n"
        if "self_appraisal" in a:
            prompt += f"Self-Appraisal: {a['self_appraisal']}\n"
        if "performance_factors" in a:
            for factor in a["performance_factors"]:
                prompt += f"{factor['competency']}: {factor['rating']} - Strengths: {factor['strengths']}, Improvements: {factor['improvements']}\n"
        if "idp" in a:
            prompt += f"IDP Goals: {a['idp']}\n"

    response = model.generate_content(prompt)
    return response.text.strip()

def rate_performance_factors(performance_factors: list[dict]) -> list[dict]:
    prompt = (
        "You are an HR expert AI assistant. Given a list of performance competencies "
        "with strengths and improvement needs, assign a score from 1 to 10 for each. "
        "Also provide a short reason for your score.\n\n"
        "Return in JSON format like:\n"
        "[\n"
        "  {\"competency\": \"Communication\", \"score\": 8, \"reason\": \"Excellent clarity, but slight delays in escalation.\"},\n"
        "  ...\n"
        "]\n\n"
        "Here is the input:\n"
    )

    for pf in performance_factors:
        prompt += f"\nCompetency: {pf['competency']}\n"
        prompt += f"Strengths: {pf['strengths']}\n"
        prompt += f"Improvement Needs: {pf['improvements']}\n"

    response = model.generate_content(prompt)
    try:
        json_str = response.text.strip().strip("```json").strip("```").strip()
        return json.loads(json_str)    
    except Exception as e:
        raise ValueError(f"AI response parsing failed: {e}\nRaw response: {response.text}")

def generate_hr_recommendations(appraisals: list[dict]) -> str:
    prompt = (
        "You are an AI HR assistant analyzing appraisal feedback from employees over time.\n"
        "Based on strengths and improvement areas, suggest:\n"
        "- Workshops\n"
        "- Upskilling sessions\n"
        "- Coaching topics\n"
        "- General HR interventions\n\n"
        "Here is the input appraisal data:\n"
    )

    for emp in appraisals:
        prompt += f"\nEmployee: {emp['employeeName']}\n"
        for pf in emp['performanceFactors']:
            prompt += f"  Competency: {pf['competency']}\n"
            prompt += f"    Strengths: {pf['strengths']}\n"
            prompt += f"    Improvement Needs: {pf['improvements']}\n"

    response = model.generate_content(prompt)
    return response.text.strip()