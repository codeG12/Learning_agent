import os
import time
from typing import Optional
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from langchain.tools import tool
from dotenv import load_dotenv

load_dotenv()

class BrowserManager:
    _driver = None

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            chrome_options = Options()
            if os.getenv('HEADLESS', 'false').lower() == 'true':
                chrome_options.add_argument('--headless')
            cls._driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            cls._driver.implicitly_wait(10)
        return cls._driver

    @classmethod
    def quit_driver(cls):
        if cls._driver:
            cls._driver.quit()
            cls._driver = None

@tool
def browser_navigate(url: str) -> str:
    """Opens or changes the current browser window context to the specified URL."""
    try:
        driver = BrowserManager.get_driver()
        driver.get(url)
        return f'Successfully navigated to {url}. Current page title: {driver.title}'
    except Exception as e:
        return f'Error navigating to {url}: {str(e)}'

@tool
def browser_click(semantic_target: str) -> str:
    """Locates an element on screen using fuzzy/semantic text and clicks it."""
    try:
        driver = BrowserManager.get_driver()
        # Simple semantic search using XPath for text
        xpath = f"//*[contains(text(), '{semantic_target}') or contains(@aria-label, '{semantic_target}') or contains(@placeholder, '{semantic_target}')]"
        element = driver.find_element(By.XPATH, xpath)
        element.click()
        return f"Clicked on element matching '{semantic_target}'"
    except Exception as e:
        return f"Error clicking element '{semantic_target}': {str(e)}"

@tool
def browser_fill(field_label: str, text: str) -> str:
    """Safely inputs text into form fields by identifying their semantic purpose."""
    try:
        driver = BrowserManager.get_driver()
        xpath = f"//input[contains(@placeholder, '{field_label}') or contains(@name, '{field_label}') or @id=//label[contains(text(), '{field_label}')]/@for]"
        element = driver.find_element(By.XPATH, xpath)
        element.clear()
        element.send_keys(text)
        return f"Filled '{field_label}' with '{text}'"
    except Exception as e:
        return f"Error filling field '{field_label}': {str(e)}"

@tool
def read_data_file(path_or_url: str) -> str:
    """Parses files (CSV, Excel) and loads their contents into context."""
    try:
        if path_or_url.endswith('.csv'):
            # Try common encodings
            for enc in ['utf-8', 'utf-16', 'iso-8859-1']:
                try:
                    df = pd.read_csv(path_or_url, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return f"Error: Could not decode CSV file {path_or_url} with common encodings."
        elif path_or_url.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(path_or_url)
        else:
            return "Unsupported file format. Please provide a CSV or Excel file."

        return f"Loaded data from {path_or_url}. Preview:\n{df.head().to_string()}"
    except Exception as e:
        return f"Error reading file {path_or_url}: {str(e)}"
@tool
def get_config(key: str) -> str:
    """Retrieves a configuration value (e.g., LMS_USER, LMS_PASS) from environment variables."""
    value = os.getenv(key)
    if value:
        return f"{key}={value}"
    return f"Configuration for '{key}' not found."

@tool
def human_in_the_loop_escalate(issue_description: str) -> str:
    """Pauses execution and alerts a supervisor if an irrecoverable failure occurs."""
    # In a prototype, we can just print and wait or return a specific signal
    print(f"\n[ESCALATION]: {issue_description}")
    return f"AGENT_PAUSED: {issue_description}. Awaiting human intervention."
