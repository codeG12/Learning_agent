import streamlit as st
import os
from agent import agent_app
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from lms_tools import BrowserManager
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Agentic LMS Coordinator", page_icon="🤖", layout="wide")

st.title("🤖 Agentic LMS Coordinator")

# Initialize chat history and agent state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_state" not in st.session_state:
    st.session_state.agent_state = {"messages": [], "logs": []}

# Sidebar for configuration
with st.sidebar:
    st.header("Settings")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.agent_state = {"messages": [], "logs": []}
        st.rerun()

    if st.button("🛑 Quit Browser"):
        BrowserManager.quit_driver()
        st.success("Browser closed.")

    st.divider()
    st.write(f"**LMS**: {os.getenv('LMS_URL')}")
    st.write(f"**User**: {os.getenv('LMS_USER')}")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me to start a cohort or answer my questions..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare input for agent
    current_messages = st.session_state.agent_state.get("messages", [])
    current_messages.append(HumanMessage(content=prompt))

    inputs = {
        "messages": current_messages,
        "target_cohort_code": st.session_state.get("target_cohort_code", ""),
        "logs": st.session_state.agent_state.get("logs", [])
    }

    # Run agent and stream response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        # We use st.status to show background tool work
        with st.status("Agent is thinking...", expanded=False) as status:
            for event in agent_app.stream(inputs, config={"configurable": {"thread_id": "1"}}):
                if "agent" in event:
                    msg = event["agent"]["messages"][-1]
                    if msg.content:
                        full_response += msg.content
                        response_placeholder.markdown(full_response)
                    if msg.tool_calls:
                        for tc in msg.tool_calls:
                            st.write(f"🔧 **Calling Tool**: `{tc['name']}`")
                elif "tools" in event:
                    for msg in event["tools"]["messages"]:
                        # tool_name = msg.name
                        st.write(f"✅ **Tool Result**: {msg.content[:200]}...")

            status.update(label="Milestone processed!", state="complete")

        # Save agent's final message to state
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.session_state.agent_state["messages"].append(AIMessage(content=full_response))
