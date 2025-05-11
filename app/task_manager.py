"""
Background task handling for the Schedule Scraper application.
This module provides functionality to run tasks in the background while 
updating progress that can be queried by the main application.
"""
import threading
import time
from datetime import datetime, timedelta
import logging
import os
from flask import current_app

# Import scraper modules - these will be used from the background thread
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
import scraper
import gcal_service

logger = logging.getLogger(__name__)

# Global dictionary to store task progress
task_progress = {}

class ImportTask(threading.Thread):
    """Thread class for handling schedule imports in the background."""
    
    def __init__(self, app, session_id, macid, password, start_date, end_date):
        """Initialize the import task with user credentials and date range."""
        threading.Thread.__init__(self)
        self.daemon = True  # Make thread a daemon so it closes when the main app closes
        self.app = app  # Store Flask app for creating context
        self.session_id = session_id
        self.macid = macid
        self.password = password
        self.start_date = start_date
        self.end_date = end_date
        # Initialize task progress
        task_progress[session_id] = {
            "message": "Starting import process...",
            "percentage": 0,
            "status": "running"
        }
    
    def update_progress(self, message, percentage, status="running"):
        """Update the progress of the current task."""
        task_progress[self.session_id] = {
            "message": message,
            "percentage": percentage,
            "status": status
        }
        logger.info(f"Progress updated: {percentage}% - {message}")
    
    def run(self):
        """Run the import process."""
        driver = None
        
        # Create application context for this thread
        with self.app.app_context():
            try:
                self.update_progress("Setting up browser driver...", 10)
                driver = scraper.setup_driver()
                
                try:
                    self.update_progress("Logging into portal...", 15)
                    scraper.login_to_portal(driver, self.macid, self.password)
                    
                    self.update_progress("Navigating to weekly schedule page...", 20)
                    scraper.navigate_to_weekly_schedule(driver)
                    
                    current_monday = self.start_date - timedelta(days=self.start_date.weekday())
                    loop_end_date = self.end_date
                    
                    driver.switch_to.default_content()
                    total_weeks = (loop_end_date - current_monday).days // 7 + 1
                    if total_weeks <= 0:
                        total_weeks = 1
                    
                    all_schedule_data = []
                    weeks_processed = 0
                    scraper_progress_start_percentage = 30
                    scraper_progress_range = 40
                    
                    while current_monday <= loop_end_date:
                        weeks_processed += 1
                        current_progress_percentage = scraper_progress_start_percentage
                        if total_weeks > 0:
                            current_progress_percentage += int((weeks_processed / total_weeks) * scraper_progress_range)
                        
                        self.update_progress(
                            f'Scraping week {weeks_processed}/{total_weeks} (starting {current_monday.strftime("%Y-%m-%d")})...',
                            current_progress_percentage
                        )
                        
                        weekly_events = scraper.scrape_week_data(driver, current_monday)
                        if weekly_events:
                            all_schedule_data.extend(weekly_events)
                        current_monday += timedelta(days=7)
                        # Add a small delay to ensure progress updates are visible
                        time.sleep(0.1)  
                    
                    self.update_progress(
                        f'Scraping complete. Found {len(all_schedule_data)} events. Processing...',
                        scraper_progress_start_percentage + scraper_progress_range
                    )
                    
                    if not all_schedule_data:
                        self.update_progress(
                            'No schedule data found for the given dates.',
                            100,
                            'complete_with_info'
                        )
                        return
                    
                    token_file = current_app.config["TOKEN_FILE"]
                    self.update_progress('Connecting to Google Calendar...', 75)
                    if not os.path.exists(token_file):
                        self.update_progress(
                            'Error: Google Calendar not authorized.',
                            75,
                            'error'
                        )
                        return
                    
                    gcal = gcal_service.get_calendar_service()
                    if not gcal:
                        self.update_progress(
                            'Error: Could not connect to Google Calendar.',
                            75,
                            'error'
                        )
                        return
                    
                    events_created_count = 0
                    events_failed_count = 0
                    total_events_to_create = len(all_schedule_data)
                    
                    gcal_progress_start_percentage = 80
                    gcal_progress_range = 20
                    
                    for i, event_data in enumerate(all_schedule_data):
                        current_gcal_progress = gcal_progress_start_percentage
                        if total_events_to_create > 0:
                            current_gcal_progress += int(((i + 1) / total_events_to_create) * gcal_progress_range)
                        
                        self.update_progress(
                            f'Adding event {i+1}/{total_events_to_create} to Google Calendar ({event_data.get("course", "Event")})...',
                            current_gcal_progress
                        )
                        
                        try:
                            if "time" not in event_data or "date" not in event_data:
                                logger.warning(f"Skipping event due to missing time/date: {event_data}")
                                events_failed_count += 1
                                continue
                            
                            created = gcal_service.create_calendar_event(gcal, event_data)
                            if created:
                                events_created_count += 1
                            else:
                                events_failed_count += 1
                        except Exception as e:
                            logger.error(f"Error creating calendar event: {e}", exc_info=True)
                            events_failed_count += 1
                        
                        # Add a small delay to ensure progress updates are visible
                        time.sleep(0.1)
                    
                    final_message = f"Successfully created {events_created_count} events. Failed: {events_failed_count} events."
                    if events_created_count == 0 and events_failed_count > 0:
                        final_status = "error"
                    elif events_failed_count > 0:
                        final_status = "complete_with_warnings"
                    else:
                        final_status = "complete"
                    
                    self.update_progress(final_message, 100, final_status)
                
                except Exception as e:
                    logger.error(f"Error during scraping process: {e}", exc_info=True)
                    self.update_progress(
                        f'Error during scraping: {str(e)}',
                        self.get_current_percentage(),
                        'error'
                    )
                finally:
                    if driver:
                        logger.info("Closing Selenium driver.")
                        driver.quit()
                        
            except Exception as e:
                logger.error(f"Error during driver setup: {e}", exc_info=True)
                self.update_progress(
                    f'Error setting up browser: {str(e)}',
                    10,
                    'error'
                )
    
    def get_current_percentage(self):
        """Get the current percentage from the task progress."""
        return task_progress.get(self.session_id, {}).get("percentage", 0)


def get_task_progress(session_id):
    """Get the current progress of a task."""
    return task_progress.get(session_id, {
        "message": "No import in progress",
        "percentage": 0,
        "status": "not_started"
    })


def start_import_task(app, session_id, macid, password, start_date, end_date):
    """Start an import task in the background."""
    task = ImportTask(app, session_id, macid, password, start_date, end_date)
    task.start()
    return True
