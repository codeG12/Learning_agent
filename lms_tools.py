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
    """Locates an element on screen using fuzzy/semantic text and clicks it.
    Handles text, aria-labels, and common icon button patterns.
    """
    try:
        driver = BrowserManager.get_driver()
        # Search patterns: Text match, Aria-label match, Placeholder match, or specific ID
        # Also includes common patterns for three-dot menus if target is 'options' or 'menu'
        xpath_patterns = [
            f"//*[contains(text(), '{semantic_target}')]",
            f"//*[@aria-label[contains(., '{semantic_target}')]]",
            f"//*[@title[contains(., '{semantic_target}')]]",
            f"//*[@placeholder[contains(., '{semantic_target}')]]"
        ]

        # Specific fallback for known icons
        if semantic_target.lower() in ['options', 'menu', 'three dots']:
            xpath_patterns.append("//*[contains(@class, 'fa-ellipsis') or contains(@class, 'more-actions') or contains(@class, 'action-button')]")
        if semantic_target.lower() in ['search', 'magnifying glass']:
            xpath_patterns.append("//button[contains(@class, 'search')]")
            xpath_patterns.append("//*[contains(@class, 'fa-search')]")

        for xpath in xpath_patterns:
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    el.click()
                    return f"Clicked on element matching '{semantic_target}' using xpath: {xpath}"

        return f"Could not find a clickable element for '{semantic_target}'"
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
            for enc in ['utf-8', 'utf-16', 'iso-8859-1']:
                try:
                    df = pd.read_csv(path_or_url, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return f"Error: Could not decode CSV file {path_or_url}"
        elif path_or_url.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(path_or_url)
        else:
            return "Unsupported file format."

        # Return more rows for better context
        return f"Loaded data from {path_or_url}. Full content:\n{df.to_string()}"
    except Exception as e:
        return f"Error reading file {path_or_url}: {str(e)}"

@tool
def lookup_master_course(prefix: str) -> str:
    """Searches master_reference.csv using positional indices to find the Master Code and Link matching the prefix (e.g., 'PDDM-OMC')."""
    try:
        # Load without specific names to use indices if needed
        df = pd.read_csv('master_reference.csv')

        # Column 1 (index 1) is typically 'Course run'
        # Column 2 (index 2) is typically 'New LMS Link'
        # We search column 1 for the prefix
        matches = df[df.iloc[:, 1].str.contains(prefix, case=False, na=False)]

        if matches.empty:
            return f"No master course found matching: {prefix}"

        # Get the last match (most recent)
        result = matches.iloc[-1]
        master_code = result.iloc[1]
        master_link = result.iloc[2]

        return f"EXACT_MATCH: MasterCode='{master_code}', UseThisLink='{master_link}'"
    except Exception as e:
        return f"Error searching master reference: {str(e)}"


@tool
def get_config(key: str) -> str:
    """Retrieves a configuration value (e.g., LMS_USER, LMS_PASS) from environment variables."""
    value = os.getenv(key)
    if value:
        return f"{key}={value}"
    return f"Configuration for '{key}' not found."

@tool
def login_lms() -> str:
    """Performs the full login sequence for LMS Studio using Staff Login and handling MFA."""
    try:
        driver = BrowserManager.get_driver()
        url = os.getenv('LMS_URL', 'https://apps.claaslms.educlaas.com/authoring/home')
        user = os.getenv('LMS_USER')
        password = os.getenv('LMS_PASS')

        if not user or not password:
            return "Error: LMS_USER or LMS_PASS not set in environment."

        driver.get(url)
        time.sleep(3)

        # 1. Look for 'Learner Login'
        try:
            learner_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Learner Login') or contains(text(), 'Learner login')]")
            learner_btn.click()
            time.sleep(3)
        except:
            print("Learner Login button not found, checking if already on login page...")

        # 2. Check if already logged in
        if "Studio home" in driver.title or len(driver.find_elements(By.CLASS_NAME, "user-menu")) > 0:
            return "Already logged in to LMS Studio."

        # 3. Fill credentials (Microsoft/SSO typically)
        try:
            # Look for email field (could be type='email' or name='loginfmt' for MS)
            email_field = driver.find_element(By.XPATH, "//input[@type='email' or @name='loginfmt' or @name='email']")
            email_field.clear()
            email_field.send_keys(user)
            email_field.send_keys(Keys.ENTER)
            time.sleep(2)

            # Look for password
            pass_field = driver.find_element(By.XPATH, "//input[@type='password' or @name='passwd' or @name='password']")
            pass_field.clear()
            pass_field.send_keys(password)
            pass_field.send_keys(Keys.ENTER)
            time.sleep(3)
        except Exception as e:
            return f"Credential entry failed: {str(e)}. Please check if the login screen is visible."

        # 4. Handle MFA
        # Check for common MFA indicators (e.g., 'Enter code', 'Approve a request', 'Verify your identity')
        mfa_keywords = ['Verify your identity', 'Approve', 'Enter code', 'MFA', 'Authenticator']
        page_source = driver.page_source
        if any(word in page_source for word in mfa_keywords):
            print("\n[ACTION REQUIRED]: MFA detected. Please check your phone/app and approve the login in the browser window.")
            # Wait loop to see if login completes
            for _ in range(6): # Wait up to 60 seconds
                if "Studio home" in driver.title or len(driver.find_elements(By.CLASS_NAME, "user-menu")) > 0:
                    return f"Successfully logged into LMS as {user} (MFA verified)."
                time.sleep(10)
            return "MFA timeout. Please complete the login manually and tell the agent to 'Proceed'."

        return f"Logged into LMS as {user}."
    except Exception as e:
        return f"Login failed: {str(e)}"
@tool
def human_in_the_loop_escalate(issue_description: str) -> str:
    """Pauses execution and alerts a supervisor if an irrecoverable failure occurs."""
    # In a prototype, we can just print and wait or return a specific signal
    print(f"\n[ESCALATION]: {issue_description}")
    return f"AGENT_PAUSED: {issue_description}. Awaiting human intervention."
