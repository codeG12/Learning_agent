import operator
from typing import Annotated, Sequence, TypedDict, List
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from lms_tools import browser_navigate, browser_click, browser_fill, read_data_file, get_config, human_in_the_loop_escalate
import os
from dotenv import load_dotenv

load_dotenv()

# Define the state schema
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    target_cohort_code: str
    logs: List[str]

# Define the tools
tools = [browser_navigate, browser_click, browser_fill, read_data_file, get_config, human_in_the_loop_escalate]
tool_node = ToolNode(tools)

# Model selection logic
openai_key = os.getenv("OPENAI_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")

if google_key and (google_key.startswith("AIza") or not openai_key):
    print("Using Google Gemini model (Flash)...")
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0).bind_tools(tools)
else:
    print("Using OpenAI model...")
    model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools)

# System Prompt
SYSTEM_PROMPT = """You are an autonomous AI Agent / Core Logic Orchestrator specializing in workflow automation.
Your objective: Successfully execute the LMS Module Rerun and Scheduling process.

Reasoning Blueprint:
1. Target ID: Infer module type from TARGET_COHORT_CODE. Search master_reference.csv for the Master Cohort Code.
   - Form the Master Link using the pattern: https://apps.claaslms.educlaas.com/authoring/course/course-v1:EDUCLaaS+{MODULE_TYPE}+{MASTER_COHORT_CODE}
   - Example: For APM and master code PDDM-APM-Master-13Jan2025, the link is https://apps.claaslms.educlaas.com/authoring/course/course-v1:EDUCLaaS+APM+PDDM-APM-Master-13Jan2025
2. Rerun Gen: Navigate to the constructed Master Link, verify content, and trigger Rerun.
3. Temporal Plan: Adjust SOC (-2 days) and EOC (+2 days).
4. Data Extraction: Locate Excel schedule in SharePoint.
5. Due Date Application: Sync dates from Excel to LMS.
6. Asset Linking: Sync PDF schedule to LMS calendar.

Guardrails:
- Use get_config for LMS_USER, LMS_PASS.
- Attempt self-correction up to 2 times.
"""

def call_model(state: AgentState):
    messages = state['messages']
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

agent_app = workflow.compile()

def run_agent(cohort_code: str):
    initial_input = {
        "target_cohort_code": cohort_code,
        "messages": [HumanMessage(content=f"Start the LMS process for cohort: {cohort_code}")],
        "logs": []
    }
    return agent_app.stream(initial_input)
