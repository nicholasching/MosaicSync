from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from datetime import datetime, timedelta # Added timedelta here
import os
import json
import time

# Assuming your refactored scraper and gcal_service are in the parent directory
# Adjust the import paths if your project structure is different or if they become packages
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import scraper # Your refactored scraper.py
import gcal_service # Your gcal_service.py

# Using a Blueprint for routes. 'main' is the name of the blueprint.
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    current_app.logger.info("Index page requested.")
    # Default dates for the form (e.g., from scraper.py or config)
    # These should be in YYYY-MM-DD format for the date input field
    default_start = scraper.START_DATE.strftime("%Y-%m-%d")
    default_end = scraper.END_DATE.strftime("%Y-%m-%d")
    
    macid_user = current_app.config.get('MACID_USER', '')

    gcal_authorized = os.path.exists(current_app.config['TOKEN_FILE'])
    current_app.logger.info(f"Google Calendar authorized: {gcal_authorized}")

    return render_template(
        'index.html',
        default_start_date=default_start,
        default_end_date=default_end,
        macid_user=macid_user,
        gcal_authorized=gcal_authorized
    )

@main_bp.route('/authorize_gcal')
def authorize_gcal():
    current_app.logger.info("Attempting to authorize Google Calendar.")
    # This will trigger the OAuth flow defined in gcal_service.get_calendar_service()
    # The flow itself handles redirection to Google and then to our /oauth2callback
    # We just need to call it to start the process if token.json doesn't exist or is invalid.
    service = gcal_service.get_calendar_service() # This initiates the flow if needed
    if service:
        flash('Google Calendar authorized successfully!', 'success')
        current_app.logger.info("Google Calendar authorization successful.")
    else:
        flash('Failed to authorize Google Calendar. Check logs.', 'danger')
        current_app.logger.error("Google Calendar authorization failed.")
    return redirect(url_for('.index')) # Redirect back to index, which will re-check auth status

@main_bp.route('/oauth2callback')
def oauth2callback():
    current_app.logger.info("Received OAuth2 callback from Google.")
    # The gcal_service.get_calendar_service() when called by authorize_gcal
    # uses flow.run_local_server() which handles the callback directly.
    # However, if using a different OAuth flow (e.g., for web apps not using run_local_server),
    # you would handle the exchange of authorization code for tokens here.
    # For run_local_server, this route primarily serves as the redirect URI.
    
    # It's good practice to check if the token file was created.
    if os.path.exists(current_app.config['TOKEN_FILE']):
        flash('Google Calendar authorization completed.', 'success')
        current_app.logger.info("OAuth2 callback processed, token file should be present.")
    else:
        flash('Google Calendar authorization may not have completed successfully. Token file not found.', 'warning')
        current_app.logger.warning("OAuth2 callback processed, but token file was not found.")
    return redirect(url_for('.index'))


@main_bp.route('/import_schedule', methods=['POST'])
def import_schedule():
    current_app.logger.info("Import schedule route called.")
    if not os.path.exists(current_app.config['TOKEN_FILE']):
        flash("Google Calendar not authorized. Please authorize first.", "danger")
        return redirect(url_for('.index'))

    macid = request.form.get('macid')
    password = request.form.get('password')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    if not all([macid, password, start_date_str, end_date_str]):
        flash("All fields are required.", "danger")
        return redirect(url_for('.index'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
        return redirect(url_for('.index'))

    current_app.logger.info(f"Starting schedule import for {macid} from {start_date_str} to {end_date_str}")
    
    # --- Run Scraper ---
    all_schedule_data = []
    driver = None # Initialize driver to None for finally block
    try:
        current_app.logger.info("Setting up Selenium driver.")
        # Update scraper to accept start/end dates and credentials as parameters
        # For now, we assume scraper.py might still use its internal START_DATE, END_DATE or env vars
        # This needs to be refactored in scraper.py to accept these as arguments to its main/new function
        
        # --- Modification for scraper.py to accept parameters ---
        # Option 1: Modify scraper.main() to accept parameters (preferred)
        # Option 2: Set environment variables here (less ideal for web app context)
        
        # For now, let's assume a function `run_scraper(username, password, start_dt, end_dt)` exists in scraper.py
        # This is a placeholder for the actual integration.
        # You'll need to adjust scraper.py to provide such a function.
        
        # --- Placeholder for actual scraper call ---
        # This is where you would call your scraper's main logic.
        # For demonstration, let's simulate it or try to call the existing main.
        # To properly integrate, scraper.py's main() or a new function should:
        # 1. Accept username, password, start_date, end_date as arguments.
        # 2. Return the scraped data instead of just writing to a file.
        
        # --- Temporary: Using a direct call to scraper functions (requires scraper.py refactoring) ---
        current_app.logger.info("Initializing WebDriver...")
        driver = scraper.setup_driver()
        scraper.login_to_portal(driver, macid, password)
        scraper.navigate_to_weekly_schedule(driver) # Navigates and stays in iframe initially

        current_monday = start_date - timedelta(days=start_date.weekday()) # Ensure start is a Monday: For some reason, the first week of the term is not correctly parsed by the scraper, so start one week earlier
        loop_end_date = end_date

        driver.switch_to.default_content()

        while current_monday <= loop_end_date:
            current_app.logger.info(f"Scraping week starting {current_monday.strftime('%Y-%m-%d')}")
            weekly_events = scraper.scrape_week_data(driver, current_monday)
            if weekly_events:
                all_schedule_data.extend(weekly_events)
            current_monday += timedelta(days=7)
        
        current_app.logger.info(f"Scraping complete. Found {len(all_schedule_data)} events.")
        # --- End of temporary scraper call ---

    except Exception as e:
        current_app.logger.error(f"Error during scraping process: {e}", exc_info=True)
        flash(f"An error occurred during scraping: {e}", "danger")
        return redirect(url_for('.index'))
    finally:
        if driver:
            current_app.logger.info("Closing Selenium driver.")
            driver.quit()

    if not all_schedule_data:
        flash("No schedule data found for the given dates.", "info")
        return redirect(url_for('.index'))

    # --- Add to Google Calendar ---
    gcal = gcal_service.get_calendar_service()
    if not gcal:
        flash("Could not connect to Google Calendar service. Please try authorizing again.", "danger")
        return redirect(url_for('.index'))

    events_created_count = 0
    events_failed_count = 0
    for event_data in all_schedule_data:
        try:
            # Ensure event_data['time'] and event_data['date'] are present and correct
            if 'time' not in event_data or 'date' not in event_data:
                current_app.logger.warning(f"Skipping event due to missing time/date: {event_data}")
                events_failed_count += 1
                continue
            
            created = gcal_service.create_calendar_event(gcal, event_data)
            if created:
                events_created_count += 1
            else:
                events_failed_count += 1
        except Exception as e:
            current_app.logger.error(f"Error creating calendar event for {event_data.get('course')}: {e}", exc_info=True)
            events_failed_count += 1
            
    flash(f"Successfully created {events_created_count} events in Google Calendar. Failed to create {events_failed_count} events.", "success" if events_created_count > 0 else "warning")
    current_app.logger.info(f"Calendar import finished. Created: {events_created_count}, Failed: {events_failed_count}")

    return redirect(url_for('.index'))

# Need to register this blueprint in app/__init__.py
# Modify app/__init__.py:
# from .routes import main_bp
# app.register_blueprint(main_bp)
