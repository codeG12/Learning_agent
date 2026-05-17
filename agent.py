import operator
from typing import Annotated, Sequence, TypedDict, List
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from lms_tools import browser_navigate, browser_click, browser_fill, read_data_file, get_config, lookup_master_course, login_lms, human_in_the_loop_escalate
import os
from dotenv import load_dotenv

load_dotenv()

# Define the state schema
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    target_cohort_code: str
    logs: List[str]

# Define the tools
tools = [browser_navigate, browser_click, browser_fill, read_data_file, get_config, lookup_master_course, login_lms, human_in_the_loop_escalate]
tool_node = ToolNode(tools)

# Model selection logic
openai_key = os.getenv("OPENAI_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")
hf_key = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HUGGINGFACEHUB_API_TOKEN")

if hf_key:
    try:
        print("Attempting to use Hugging Face (Qwen/Qwen2.5-7B-Instruct)...")
        llm = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            task="text-generation",
            max_new_tokens=1024,
            huggingfacehub_api_token=hf_key,
        )
        model = ChatHuggingFace(llm=llm).bind_tools(tools)
    except Exception as e:
        print(f"Hugging Face initialization failed: {e}. Falling back...")
        hf_key = None

if not hf_key:
    if google_key and (google_key.startswith("AIza") or not openai_key):
        model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0).bind_tools(tools)
    else:
        model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools)

# Assertive System Prompt
SYSTEM_PROMPT = """You are an AUTONOMOUS CORE LOGIC ORCHESTRATOR.
Your goal is to EXECUTE the LMS workflow immediately upon receiving a target cohort code.

DO NOT ask for permission to proceed. EXECUTE the tools in order:

Step 1: Identify Target
- Extract the Programme-Module prefix (e.g., 'PDDM-OMC') from the input.
- Call lookup_master_course(prefix) to get the Master Code and exact Master Link.

Step 2: Access & Search
- Call login_lms() to handle authentication.
- Call browser_navigate(LMS_URL) to ensure you are on the Home page.
- Call browser_fill('Search', MASTER_CODE) then call browser_click('Search').

Step 3: Trigger Rerun
- Locate the search result matching MASTER_CODE.
- Call browser_click('Options') or 'three dots' for that result.
- Call browser_click('Re-run course').

Step 4: Configure & Commit
- Fill the rerun form: select 'CLaaS2SaaS', input the new TARGET_COHORT_CODE.
- Submit the form.

Step 5: Schedule Adjustments
- Navigate to Settings > Schedule and Details.
- Apply SOC - 2 Days, EOC + 2 Days rules.

Step 6: SharePoint & Assets
- Resolve SharePoint path, extract Excel dates, apply Rules A/B/C.
- Upload PDF, capture URL, and link to the calendar.

If a step fails, retry with an alternative approach or label. If still blocked, use human_in_the_loop_escalate.
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
        "messages": [HumanMessage(content=f"EXECUTE: Start the full process for cohort: {cohort_code}")],
        "logs": []
    }
    return agent_app.stream(initial_input)
