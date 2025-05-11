# mcmaster_schedule_scraper.py
from datetime import datetime, timedelta
import os, json, re
import time
import logging
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# --- Configuration & Setup ---
load_dotenv() # Load environment variables from .env file

MACID = os.environ.get("MACID_USER")
PASSWORD = os.environ.get("MACID_PASS")
# For some reason, the first week of the term is not correctly parsed by the scraper, so start one week earlier (this is currently a workaround and done in routes.py)
START_DATE = datetime(2025, 1, 6)
END_DATE = datetime(2025, 1, 12)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def setup_driver():
    """Initializes and returns the Selenium WebDriver."""
    # chrome_options = Options()
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--disable-gpu")
    # driver = webdriver.Chrome(options=chrome_options)
    driver = webdriver.Chrome()  # or Edge/Firefox
    return driver


def login_to_portal(driver, username, password):
    """Logs into the McMaster portal."""
    logging.info("Navigating to login page.")
    driver.get("https://csprd.mcmaster.ca/psp/prcsprd/?cmd=login")
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "userid")))
        driver.find_element(By.ID, "userid").send_keys(username)
        driver.find_element(By.ID, "pwd").send_keys(password)
        driver.find_element(By.NAME, "Submit").click()
        logging.info("Login submitted. Waiting for homepage.")
        WebDriverWait(driver, 90).until(EC.title_contains("Homepage"))
        logging.info("Login successful.")
    except TimeoutException:
        logging.error("Timeout during login process.")
        raise
    except NoSuchElementException:
        logging.error("Login form element not found.")
        raise


def navigate_to_weekly_schedule(driver):
    """Navigates to the 'My Weekly Schedule' page."""
    logging.info("Navigating to student center.")
    driver.get(
        "https://csprd.mcmaster.ca/psp/prcsprd/EMPLOYEE/SA/c/SA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL?"
    )
    try:
        logging.info("Switching to main content iframe.")
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "TargetContent"))
        )
        logging.info("Locating weekly schedule link.")
        weekly_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "DERIVED_SSS_SCL_SS_WEEKLY_SCHEDULE"))
        )
        time.sleep(1) # Brief pause before click
        weekly_link.click()
        logging.info("Clicked weekly schedule link.")
        # The page is now within the iframe. We'll switch back to default_content after processing each week.
    except TimeoutException:
        logging.error("Timeout navigating to weekly schedule or finding elements.")
        driver.switch_to.default_content() # Ensure we are not stuck in an iframe on error
        raise
    except NoSuchElementException:
        logging.error("Element not found during schedule navigation.")
        driver.switch_to.default_content() # Ensure we are not stuck in an iframe on error
        raise


def parse_html_to_events(soup, base_date_for_week):
    """Parses the HTML soup of a weekly schedule table and extracts event data."""
    events_this_week = []
    selector = "table#WEEKLY_SCHED_HTMLAREA td[class*='PSLEVEL3GRID']"
    logging.debug(f"Using selector: '{selector}' for date: {base_date_for_week.strftime('%Y-%m-%d')}")

    offset = -2
    count = 0
    delayArr = [0, 0, 0, 0, 0, 0, 0] # To handle rowspan for events spanning multiple time slots on the same day

    cells = soup.select(selector)
    if not cells:
        logging.warning(f"No schedule cells found for week starting {base_date_for_week.strftime('%Y-%m-%d')}. The page might be empty or structure changed.")
        return events_this_week

    for cell in cells:
        logging.debug(f"Raw cell: {cell}")

        if (offset > 5 and count == 0):
            offset -= 6
            count += 1
        elif (offset > 5 and count == 1):
            offset -= 7
            count = 0
        else:
            offset += 1
        
        while (delayArr[offset % len(delayArr)] > 0):
            logging.debug(f"Before Offset: {offset}; Delay: {delayArr[offset % len(delayArr)]}")
            delayArr[offset % len(delayArr)] -= 1
            if (offset < 6):
                offset = offset + 1
            elif (offset > 5 and count == 0):
                offset -= 6 - 1
                count += 1
            elif (offset > 5 and count == 1):
                offset -= 7 - 1
                count = 0
        
        logging.debug(f"Current offset: {offset}, Calculated date: {base_date_for_week + timedelta(days=offset)}")

        text = " ".join(cell.stripped_strings)
        if not text or text.isspace():
            continue

        logging.debug(f"Processing text: '{text}'")
        m = re.match(
            r"(?P<course>[A-Z\s]+\s+\w+)\s+-\s+\w+\s+"
            r"(?P<type>Lecture|Tutorial|Lab|Laboratory|Core)\s+"
            r"(?P<time>\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})\s+"
            r"(?P<location>.+)",
            text,
            re.IGNORECASE | re.DOTALL
        )

        rowspan = int(cell.get("rowspan", "1"))

        if m:
            event_date = base_date_for_week + timedelta(days=offset)
            course_details = m.groupdict()
            if 'course' in course_details and course_details['course']:
                course_details['course'] = re.sub(r'\s+', ' ', course_details['course']).strip()
            
            events_this_week.append({
                "week_of": base_date_for_week.strftime("%Y-%m-%d"),
                "date": event_date.strftime("%Y-%m-%d"),
                **course_details
            })
            logging.debug(f"Match found: {course_details}, rowspan: {rowspan}, date: {event_date.strftime('%Y-%m-%d')}")
        else:
            logging.debug(f"No match for text: '{text}', rowspan: {rowspan}")

        if (rowspan > 1 and offset != -1): # Ensure offset is valid index
             # This logic for rowspan seems to be for events that span multiple *time slots* on the *same day*.
             # The original delayArr logic might need review if it's intended for multi-day events.
             # For now, replicating existing logic.
            if 0 <= (offset % len(delayArr)) < len(delayArr):
                 delayArr[offset % len(delayArr)] = rowspan - 1
            else:
                logging.warning(f"Invalid offset {offset} for delayArr access.")


    return events_this_week


def scrape_week_data(driver, current_monday):
    """Inputs date, refreshes schedule, and parses data for the given week."""
    logging.info(f"Scraping week of: {current_monday.strftime('%d/%m/%Y')}")
    try:
        # Ensure we are in the correct iframe for date input and refresh
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "TargetContent"))
        )

        date_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "DERIVED_CLASS_S_START_DT"))
        )
        
        # Clear the date box
        current_value_len = len(date_box.get_attribute('value'))
        for _ in range(current_value_len):
            date_box.send_keys(Keys.BACKSPACE)
        time.sleep(0.2) # Short pause after clearing

        date_box.send_keys(current_monday.strftime("%d/%m/%Y"))
        time.sleep(0.2) # Short pause after sending keys

        refresh_button = driver.find_element(By.ID, "DERIVED_CLASS_S_SSR_REFRESH_CAL$8$")
        refresh_button.click()
        
        # Wait for an element within the schedule to indicate it has reloaded.
        # This could be the table itself or a specific known element.
        # If the table reloads, an old reference to it would become stale.
        # For simplicity, let's wait for the date box to update AND a brief pause for content to load.
        # A more robust wait would be for a specific element in the schedule table to be present/visible again.
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element_value((By.ID, "DERIVED_CLASS_S_START_DT"), current_monday.strftime("%d/%m/%Y"))
        )
        # Add a slightly longer, more reliable wait for the table to actually refresh its content.
        # This might involve waiting for a specific element in the table to be stale and then reappear,
        # or simply waiting for the loading indicator (if any) to disappear.
        # For now, a slightly increased explicit wait after the date is confirmed.
        time.sleep(1.5) # Increased wait for schedule content to refresh after date input confirmation

        logging.info(f"Refreshed schedule for week: {current_monday.strftime('%d/%m/%Y')}")
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        weekly_events = parse_html_to_events(soup, current_monday)
        
        driver.switch_to.default_content() # Switch out of iframe
        time.sleep(0.5) # Brief pause after switching from iframe
        return weekly_events

    except TimeoutException:
        logging.error(f"Timeout during scraping week {current_monday.strftime('%d/%m/%Y')}.")
        driver.switch_to.default_content() # Ensure we are not stuck in an iframe on error
        return [] # Return empty list on error for this week
    except NoSuchElementException:
        logging.error(f"Element not found during scraping week {current_monday.strftime('%d/%m/%Y')}.")
        driver.switch_to.default_content() # Ensure we are not stuck in an iframe on error
        return [] # Return empty list on error for this week
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping week {current_monday.strftime('%d/%m/%Y')}: {e}")
        driver.switch_to.default_content() # Ensure we are not stuck in an iframe on error
        return []


def main():
    """Main function to orchestrate the scraping process."""
    if not MACID or not PASSWORD:
        logging.error("MACID_USER and MACID_PASS environment variables must be set.")
        return

    driver = setup_driver()
    all_schedule_data = []
    try:
        login_to_portal(driver, MACID, PASSWORD)
        navigate_to_weekly_schedule(driver) # Navigates and stays in iframe initially

        current_monday = START_DATE
        while current_monday <= END_DATE:
            # The navigate_to_weekly_schedule leaves us in the iframe.
            # scrape_week_data expects to switch into TargetContent itself,
            # and switches out after it's done.
            # So, before the first call and between calls, we should be in default_content.
            # The first call to navigate_to_weekly_schedule handles getting into the iframe.
            # Subsequent calls to scrape_week_data will handle iframe switching internally.

            # If not the first iteration, ensure we are in default content before scrape_week_data
            # (which will then switch into the iframe)
            if current_monday != START_DATE:
                 pass # scrape_week_data handles iframe switching

            weekly_events = scrape_week_data(driver, current_monday)
            if weekly_events:
                all_schedule_data.extend(weekly_events)
            
            current_monday += timedelta(days=7)
            # No need for explicit sleep here if WebDriverWait is used effectively within scrape_week_data
            # However, a small politeness delay can be added if desired.
            # time.sleep(1)


    except Exception as e:
        logging.error(f"An error occurred in the main process: {e}")
    finally:
        logging.info("Closing browser.")
        driver.quit()

    if all_schedule_data:
        output_filename = "schedule.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(all_schedule_data, f, indent=2)
        logging.info(f"Wrote {len(all_schedule_data)} meeting blocks to {output_filename}")
    else:
        logging.info("No schedule data was scraped.")
    
    logging.info("Done!")


if __name__ == "__main__":
    main()