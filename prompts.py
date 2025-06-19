def get_api_routing_prompt(user_query: str) -> str:
    """
    Generates a detailed prompt to instruct the LLM to act as an API router.
    """
    api_documentation = """
    AVAILABLE APIs:
    1.  api_name: "get_past_appraisal_by_id"
        - Description: Use this to fetch a single, completed, historical appraisal for a specific employee.
        - URL: http://localhost:3000/appraisal/past-appraisals
        - Required Parameter: "employee_id" (The unique identifier for the employee).

    2.  api_name: "get_self_appraisal_by_id"
        - Description: Use this to fetch the current, in-progress self-appraisal that an employee is actively filling out.
        - URL: http://localhost:3000/self-appraisal
        - Required Parameter: "employee_id" (The unique identifier for the employee).

    3.  api_name: "get_appraisal_data"
        - Provides the values of all the appraisals 
        - URL: http://localhost:3000/appraisal
        - Required Parameter: Does not have input parameters since it returns all appraisal data.
    """

    # Provide high-quality examples (few-shot learning)
    examples = """
    EXAMPLES:
    ---
    User Query: "Show me the Q2 2024 appraisal for employee 7890."
    Reasoning: The user is asking for a specific, past appraisal for one person. This matches `get_past_appraisal_by_id`.
    Result:
    ```json
    {
      "api_name": "get_past_appraisal_by_id",
      "parameters": {
        "employee_id": "E7890"
      }
    }
    ```

    ---
    User Query: "Pull up all the appraisals"
    Reasoning: 
    Result:
    ```json
    {
      "api_name": "get_appraisal_data",
      "parameters": {
        "employee_id": "E1234"
      }
    }
    ```
    """

    # The final prompt structure
    prompt = f"""
    You are an intelligent API routing assistant for an HR management system.
    Your task is to analyze a user's request and determine which API endpoint to call and what parameters are needed.

    {api_documentation}

    Follow these rules:
    1.  Carefully analyze the user's query to understand their intent.
    2.  If the query is for a single person, extract their name or ID. Prefer ID if available.
    3.  If the query is for a completed/historical review, use `get_past_appraisal_by_id`.
    4.  If the query is for a current/in-progress self-review, use `get_self_appraisal_by_id`.
    5.  For all other queries (comparisons, team data, general questions), use `get_general_appraisal_data`.
    6.  You MUST respond with a single, valid JSON object containing the `api_name` and a `parameters` object. Do not add any other text or explanation outside the JSON.

    {examples}

    ---
    NOW, ANALYZE THE FOLLOWING REQUEST:
    User Query: "{user_query}"
    Reasoning:
    Result:
    """
    return prompt