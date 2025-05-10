# mcmaster_schedule_scraper.py
from datetime import datetime, timedelta
import os, json, re
import time
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv, dotenv_values
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv() # Load environment variables from .env file

MACID     = os.environ["MACID_USER"]                            # store creds in env vars or a secrets vault
PASSWORD  = os.environ["MACID_PASS"]
START     = datetime(2025,  1,  6) - timedelta(days=7)        # first Monday of term: For some reason, the first week of the term is not correctly parsed by the scraper, so start one week earlier
END       = datetime(2025,  4, 13)                            # last Sunday  of term

driver = webdriver.Chrome()               # or Edge/Firefox
driver.get("https://csprd.mcmaster.ca/psp/prcsprd/?cmd=login")  # login page

# ---- 1) log in --------------------------------------------------------------
driver.find_element(By.ID, "userid").send_keys(MACID)
driver.find_element(By.ID, "pwd").send_keys(PASSWORD)
driver.find_element(By.NAME, "Submit").click()

# Duo or SSO step here?  Selenium will wait while you approve on your phone.
WebDriverWait(driver, 90).until(
    EC.title_contains("Homepage")
)

# ---- 2) open My Weekly Schedule --------------------------------------------
driver.get(
    "https://csprd.mcmaster.ca/psp/prcsprd/EMPLOYEE/SA/c/SA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL?"  # exact URL may vary
)

# 1) switch to the main content iframe first
WebDriverWait(driver, 10).until(
    EC.frame_to_be_available_and_switch_to_it((By.NAME, "TargetContent"))
)
# (the frame is sometimes named "TargetContent", "ptifrmtgtframe", or has id="TargetContent";
#  adjust the locator if your instance uses a different name/id)

# 2) find the <a> that triggers the schedule page
weekly_link = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.ID, "DERIVED_SSS_SCL_SS_WEEKLY_SCHEDULE"))
)
time.sleep(1)

# 3) click it
weekly_link.click()

# …do whatever you need on the Weekly Schedule page…

# when you’re done and need to access something outside the iframe:
driver.switch_to.default_content()
time.sleep(1)

weeks_data = []
cur = START

while cur <= END:

    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.NAME, "TargetContent"))
    )

    # 2a) put Monday’s date into “Show Week of”
    date_box = driver.find_element(By.ID, "DERIVED_CLASS_S_START_DT")

    current_value_len = len(date_box.get_attribute('value'))
    for _ in range(current_value_len):
            date_box.send_keys(Keys.BACKSPACE)
            # time.sleep(0.05) # Optional small delay if needed

    # Optional short pause after clearing
    time.sleep(0.5)

    # 2a) put Monday’s date into “Show Week of”
    date_box.send_keys(cur.strftime("%d/%m/%Y"))
    # Optional short pause after sending keys
    time.sleep(0.5)


    # 2b) click Refresh
    driver.find_element(By.ID, "DERIVED_CLASS_S_SSR_REFRESH_CAL$8$").click()
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element_value((By.ID, "DERIVED_CLASS_S_START_DT"), cur.strftime("%d/%m/%Y"))
    )

    # REQUIRED: wait for the page to load completely before parsing
    time.sleep(1)

    # 2c) parse the weekly table
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Correct selector based on inspecting the HTML:
    # Selects table cells (td) within the main schedule table that have a class containing 'PSLEVEL3GRID'
    selector = "table#WEEKLY_SCHED_HTMLAREA td[class*='PSLEVEL3GRID']"
    print(f"DEBUG: Using selector: '{selector}'")

    offset = -2
    count = 0

    delayArr = [0, 0, 0, 0, 0, 0, 0]

    # Now 'cell' will be a <td> element containing schedule info
    for cell in soup.select(selector):
        print(f"DEBUG: Found cell: {cell}")

        if (offset > 5 and count == 0):
            offset -= 6
            count += 1
        elif (offset > 5 and count == 1):
            offset -= 7
            count = 0
        else:
            offset += 1

        while (delayArr[offset % len(delayArr)] > 0):
            print(f"DEBUG: Before Offset: {offset}; Delay: {delayArr[offset % len(delayArr)]}")
            delayArr[offset % len(delayArr)] -= 1
            if (offset < 6):
                offset = offset + 1
            elif (offset > 5 and count == 0):
                offset -= 6 - 1
                count += 1
            elif (offset > 5 and count == 1):
                offset -= 7 - 1
                count = 0

        print(offset)
        print(cur + timedelta(days=offset))
        
        # Extract all text pieces from the cell and join them
        text = " ".join(cell.stripped_strings)

        # Skip empty cells or cells that only contain non-breaking spaces
        if not text or text.isspace():
            continue

        print(f"DEBUG: Processing text: '{text}'")
        # Adjusted regex to handle course code, section, 24-hour time, and 'Laboratory' type
        # Example: ENGINEER    1P13B - C01 Lecture 09:30 - 10:20 Peter George Centre for L&L M21
        m = re.match(
            r"(?P<course>[A-Z\s]+\s+\w+)\s+-\s+\w+\s+"  # Course Name/Code (e.g., "ENGINEER    1P13B") then skip section ("- C01")
            r"(?P<type>Lecture|Tutorial|Lab|Laboratory|Core)\s+"  # Type
            r"(?P<time>\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})\s+"  # Time (e.g., "09:30 - 10:20")
            r"(?P<location>.+)",  # Location
            text, 
            re.IGNORECASE | re.DOTALL
        )

        # Extract the "rowspan" property of the parent <td> element
        rowspan = int(cell.get("rowspan", "1"))  # Default to "1" if rowspan is not present

        # Add rowspan to the JSON output
        if m:
            print(f"DEBUG: Match found: {m.groupdict()}, rowspan: {rowspan}")
            event_date = cur + timedelta(days=offset)
            
            course_details = m.groupdict()
            
            # Clean the course name: replace multiple spaces with a single space
            if 'course' in course_details and course_details['course']:
                # Replace any sequence of one or more whitespace characters with a single space,
                # and trim leading/trailing whitespace.
                course_details['course'] = re.sub(r'\s+', ' ', course_details['course']).strip()
            
            weeks_data.append({
                "week_of": cur.strftime("%Y-%m-%d"),
                "date": event_date.strftime("%Y-%m-%d"),
                **course_details
            })
        else:
            print(f"DEBUG: No match for text: '{text}', rowspan: {rowspan}")

        if (rowspan > 1 and offset != -1):
            delayArr[offset % len(delayArr)] = rowspan - 1

    cur += timedelta(days=7)

    # when you’re done and need to access something outside the iframe:
    driver.switch_to.default_content()
    time.sleep(1)

driver.quit()

# ---- 3) save ----------------------------------------------------------------
with open("schedule.json", "w", encoding="utf-8") as f:
    json.dump(weeks_data, f, indent=2)
print("Wrote", len(weeks_data), "meeting blocks to schedule.json")
print("Done!")