# Agentic LMS Coordinator Prototype

This project is an autonomous AI agent designed to orchestrate the LMS Module Rerun and Scheduling process.

## Features
- **Intelligent Cohort Parsing**: Automatically extracts SOC/EOC dates from target cohort codes.
- **Master Reference Lookup**: Maps module types to their master LMS templates.
- **Automated Rerun Generation**: Uses Selenium to interact with the LMS Authoring platform.
- **Dynamic Scheduling**: Calculates and applies due dates based on Excel schedule sheets.
- **Asset Syncing**: Uploads schedule PDFs from SharePoint to LMS and links them in the module calendar.

## Project Structure
- `app.py`: Streamlit-based user interface and orchestrator.
- `agent.py`: Core logic using LangGraph to follow the reasoning blueprint.
- `lms_tools.py`: Selenium-based actuators for web automation.
- `tools/utils.py`: Helper functions for date calculations and string cleaning.
- `.env`: Configuration for credentials and URLs.
- `master_reference.csv`: Mapping of module types to master links.

## Setup
1. Ensure Python 3.11+ is installed.
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` with your LMS and SharePoint details.
4. Run the prototype: `streamlit run app.py`

## Reasoning Blueprint
The agent follows a 6-milestone plan:
1. **Target ID**: Infer module type and lookup master link.
2. **Rerun Gen**: Generate new module from master rerun.
3. **Temporal Plan**: Adjust SOC (-2 days) and EOC (+2 days).
4. **Data Extraction**: Locate Excel schedule in SharePoint.
5. **Due Date Application**: Sync dates from Excel to LMS Course Outline.
6. **Asset Linking**: Sync PDF schedule to LMS calendar.
