
from langgraph.graph import StateGraph, START, END
from node_functions import start_node,check_role,employee_query,extract_update,check_appraisals,user_followup,isComplete
from node_functions import completed_appraisal,prev_summary_query,general_question,check_relevance
from node_functions import hr_lead_query,self_appraisal_summary,check_hr_lead_relevance,score_predicter
from models import State

graph = StateGraph(State)



graph.add_node("start_node",start_node)
graph.add_node("employee_query", employee_query)
graph.add_node("extract_update", extract_update)
graph.add_node("prev_employee_summary_query", prev_summary_query)
graph.add_node("general_question", general_question)
graph.add_node("user_followup", user_followup)
graph.add_node("check_appraisals", check_appraisals)
graph.add_node("completed_appraisal", completed_appraisal)

graph.add_node("hr_lead_query",hr_lead_query)
graph.add_node("score_predicter",score_predicter)
graph.add_node("prev_summary_query",prev_summary_query)
graph.add_node("self_appraisal_summary",self_appraisal_summary)



graph.add_node("hr_lead_general_question", general_question)

graph.add_edge(START, "start_node")
graph.add_conditional_edges(
    "start_node",
    check_role,
    {
        "hr_lead_query":"hr_lead_query",
        "employee_query":"employee_query"
    })
graph.add_conditional_edges(
    "employee_query",
    check_relevance,
    {
        "self_appraisal_input": "extract_update",
        "prev_employee_summary_query": "prev_employee_summary_query",
        "general_question": "general_question"
    })
graph.add_conditional_edges(
    "extract_update",
    isComplete,
    {
        "no": "user_followup",
        "yes": "completed_appraisal"
    })
graph.add_edge("user_followup","check_appraisals")
graph.add_edge("completed_appraisal", END)
graph.add_edge("prev_employee_summary_query", END)

graph.add_conditional_edges(
    "hr_lead_query",
    check_relevance,
    {
        "prev_summary_query":"prev_summary_query",
        "self_appraisal_summary":"self_appraisal_summary",
        "score_predicter":"score_predicter",
        "general_question":"hr_lead_general_question"
    })
graph.add_edge("prev_summary_query", END)
graph.add_edge("general_question", END)
graph.add_edge("hr_lead_general_question", END)
graph.add_edge("score_predicter", END)
graph.add_edge("check_appraisal",END)
graph.add_edge("self_appraisal_summary",END)
compiled = graph.compile()
