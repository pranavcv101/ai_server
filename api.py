import requests
import json
from typing import Dict, Any

def fetch_all_appraisals() -> Dict[str, Any]:
    """Fetch all appraisal data from the server"""
    API_URL = "http://localhost:3000/appraisal"
    print(f"--- REAL API CALL: Fetching all appraisals from {API_URL} ---")
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        print(error_message)
        if http_err.response.status_code == 404:
            return {"success": False, "error": "No appraisals found on the server."}
        else:
            return {"success": False, "error": f"A server error occurred (Status code: {http_err.response.status_code})."}
    except requests.exceptions.RequestException as req_err:
        error_message = f"A network error occurred: {req_err}"
        print(error_message)
        return {"success": False, "error": "Could not connect to the appraisal server. Please ensure the server is running and accessible."}
    except json.JSONDecodeError:
        error_message = "Failed to parse the server's response. It was not valid JSON."
        print(error_message)
        return {"success": False, "error": "The server returned data in an unexpected format."}

def fetch_past_appraisals_by_employee(employee_id: str) -> Dict[str, Any]:
    """Fetch past appraisals for a specific employee"""
    API_URL = "http://localhost:3000/appraisal/past-appraisals"
    print(f"--- REAL API CALL: Fetching past appraisals for employee '{employee_id}' from {API_URL} ---")
    try:
        response = requests.get(f"{API_URL}/{employee_id}", timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        print(error_message)
        if http_err.response.status_code == 404:
            return {"success": False, "error": "Employee not found on the server."}
        else:
            return {"success": False, "error": f"A server error occurred (Status code: {http_err.response.status_code})."}
    except requests.exceptions.RequestException as req_err:
        error_message = f"A network error occurred: {req_err}"
        print(error_message)
        return {"success": False, "error": "Could not connect to the appraisal server. Please ensure the server is running and accessible."}
    except json.JSONDecodeError:
        error_message = "Failed to parse the server's response. It was not valid JSON."
        print(error_message)
        return {"success": False, "error": "The server returned data in an unexpected format."}

def fetch_self_appraisal_by_employee(employee_id: str) -> Dict[str, Any]:
    """Fetch self-appraisal data for a specific employee"""
    API_URL = "http://localhost:3000/self-appraisal"
    print(f"--- REAL API CALL: Fetching self-appraisal for employee '{employee_id}' from {API_URL} ---")
    try:
        response = requests.get(f"{API_URL}/{employee_id}", timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error occurred: {http_err}"
        print(error_message)
        if http_err.response.status_code == 404:
            return {"success": False, "error": "Self-appraisal not found for this employee."}
        else:
            return {"success": False, "error": f"A server error occurred (Status code: {http_err.response.status_code})."}
    except requests.exceptions.RequestException as req_err:
        error_message = f"A network error occurred: {req_err}"
        print(error_message)
        return {"success": False, "error": "Could not connect to the appraisal server. Please ensure the server is running and accessible."}
    except json.JSONDecodeError:
        error_message = "Failed to parse the server's response. It was not valid JSON."
        print(error_message)
        return {"success": False, "error": "The server returned data in an unexpected format."}