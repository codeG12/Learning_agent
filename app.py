import os
import streamlit as st
import time
from agent import run_agent
from lms_tools import BrowserManager

st.set_page_config(page_title="Agentic LMS Coordinator", page_icon="🤖")

st.title("🤖 Agentic LMS Coordinator")
st.markdown("""
This agent automates the LMS Module Rerun and Scheduling process.
It interprets cohort codes, extracts data from master files, and syncs schedules.
""")

cohort_code = st.text_input("Enter Target Cohort Code", placeholder="e.g. PDDM-APM-0226-08Jun2026A")

if st.button("🚀 Start Process"):
    if not cohort_code:
        st.error("Please enter a valid cohort code.")
    else:
        st.info(f"Starting process for {cohort_code}...")

        log_container = st.empty()
        status_container = st.empty()

        thinking_stream = []

        try:
            for event in run_agent(cohort_code):
                # Format the thinking stream
                if "agent" in event:
                    msg = event["agent"]["messages"][-1]
                    if msg.content:
                        thinking_stream.append(f"**Agent**: {msg.content}")
                    if msg.tool_calls:
                        for tc in msg.tool_calls:
                            thinking_stream.append(f"🔧 **Tool Call**: {tc['name']}({tc['args']})")
                elif "tools" in event:
                    for msg in event["tools"]["messages"]:
                        thinking_stream.append(f"✅ **Tool Output**: {msg.content[:500]}...")

                # Update UI
                log_container.markdown("\n\n".join(thinking_stream))
                status_container.status("Processing milestone...")

            st.success("Milestone sequence complete!")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
        finally:
            # BrowserManager.quit_driver() # Keep it open for prototype view if needed
            pass

if st.sidebar.button("Quit Browser"):
    BrowserManager.quit_driver()
    st.sidebar.write("Browser session terminated.")

st.sidebar.header("Configuration")
st.sidebar.write(f"LMS URL: {os.getenv('LMS_URL', 'https://apps.claaslms.educlaas.com/authoring/home')}")
st.sidebar.write(f"Headless Mode: {st.sidebar.toggle('Headless', value=False, key='headless_toggle')}")
