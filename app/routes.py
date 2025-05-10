from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from datetime import datetime, timedelta
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

@main_bp.route('/reset_progress', methods=['POST'])
def reset_progress():
    """Reset the import progress data in the session."""
    session.pop('import_progress', None)
    return jsonify({'status': 'success'})

@main_bp.route('/get_import_progress')
def get_import_progress():
    """Get the current import progress data from the session."""
    # Default progress data if none exists in session
    default_data = {'message': 'No import in progress', 'percentage': 0, 'status': 'not_started'}
    progress_data = session.get('import_progress', default_data)
    return jsonify(progress_data)

@main_bp.route('/import_schedule', methods=['POST'])
def import_schedule():
    current_app.logger.info("Import schedule route called.")
    # Reset progress data at the start of a new import
    session['import_progress'] = {'message': 'Starting import process...', 'percentage': 0, 'status': 'running'}
    
    if not os.path.exists(current_app.config['TOKEN_FILE']):
        flash("Google Calendar not authorized. Please authorize first.", "danger")
        session['import_progress'] = {'message': 'Error: Google Calendar not authorized.', 'percentage': 0, 'status': 'error'}
        return redirect(url_for('.index'))

    macid = request.form.get('macid')
    password = request.form.get('password')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    if not all([macid, password, start_date_str, end_date_str]):
        flash("All fields are required.", "danger")
        session['import_progress'] = {'message': 'Error: Missing required fields.', 'percentage': 0, 'status': 'error'}
        return redirect(url_for('.index'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        session['import_progress'] = {'message': 'Validated input dates.', 'percentage': 5, 'status': 'running'}
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
        session['import_progress'] = {'message': 'Error: Invalid date format.', 'percentage': 0, 'status': 'error'}
        return redirect(url_for('.index'))

    all_schedule_data = []
    driver = None
    try:
        session['import_progress'] = {'message': 'Setting up browser driver...', 'percentage': 10, 'status': 'running'}
        current_app.logger.info("Initializing WebDriver...")
        driver = scraper.setup_driver()
        
        session['import_progress'] = {'message': 'Logging into portal...', 'percentage': 15, 'status': 'running'}
        scraper.login_to_portal(driver, macid, password)
        
        session['import_progress'] = {'message': 'Navigating to weekly schedule page...', 'percentage': 20, 'status': 'running'}
        scraper.navigate_to_weekly_schedule(driver) 

        current_monday = start_date - timedelta(days=start_date.weekday())
        loop_end_date = end_date

        driver.switch_to.default_content()  # This is important! Otherwise, the first week will not be scraped correctly.
        total_weeks = (loop_end_date - current_monday).days // 7 + 1
        if total_weeks <= 0: total_weeks = 1  # Avoid division by zero

        weeks_processed = 0
        scraper_progress_start_percentage = 30
        scraper_progress_range = 40  # Percentage allocated for scraping

        while current_monday <= loop_end_date:
            weeks_processed += 1
            current_progress_percentage = scraper_progress_start_percentage
            if total_weeks > 0:
                current_progress_percentage += int((weeks_processed / total_weeks) * scraper_progress_range)
            
            session['import_progress'] = {
                'message': f'Scraping week {weeks_processed}/{total_weeks} (starting {current_monday.strftime("%Y-%m-%d")})...',
                'percentage': current_progress_percentage,
                'status': 'running'
            }
            
            weekly_events = scraper.scrape_week_data(driver, current_monday)
            if weekly_events:
                all_schedule_data.extend(weekly_events)
            current_monday += timedelta(days=7)
        
        session['import_progress'] = {
            'message': f'Scraping complete. Found {len(all_schedule_data)} events. Processing...',
            'percentage': scraper_progress_start_percentage + scraper_progress_range,
            'status': 'running'
        }

    except Exception as e:
        current_app.logger.error(f"Error during scraping process: {e}", exc_info=True)
        session['import_progress'] = {
            'message': f'Error during scraping: {str(e)}',
            'percentage': session.get('import_progress', {}).get('percentage', 20),
            'status': 'error'
        }
        flash(f"An error occurred during scraping: {e}", "danger")
        return redirect(url_for('.index'))
    finally:
        if driver:
            current_app.logger.info("Closing Selenium driver.")
            driver.quit()

    if not all_schedule_data:
        flash("No schedule data found for the given dates.", "info")
        session['import_progress'] = {
            'message': 'No schedule data found for the given dates.',
            'percentage': 100,
            'status': 'complete_with_info'
        }
        return redirect(url_for('.index'))

    session['import_progress'] = {'message': 'Connecting to Google Calendar...', 'percentage': 75, 'status': 'running'}
    gcal = gcal_service.get_calendar_service()
    if not gcal:
        flash("Could not connect to Google Calendar service. Please try authorizing again.", "danger")
        session['import_progress'] = {
            'message': 'Error: Could not connect to Google Calendar.',
            'percentage': 75,
            'status': 'error'
        }
        return redirect(url_for('.index'))

    events_created_count = 0
    events_failed_count = 0
    total_events_to_create = len(all_schedule_data)
    
    gcal_progress_start_percentage = 80
    gcal_progress_range = 20  # Percentage allocated for calendar operations

    for i, event_data in enumerate(all_schedule_data):
        current_gcal_progress = gcal_progress_start_percentage
        if total_events_to_create > 0:
            current_gcal_progress += int(((i + 1) / total_events_to_create) * gcal_progress_range)

        session['import_progress'] = {
            'message': f'Adding event {i+1}/{total_events_to_create} to Google Calendar ({event_data.get("course", "Event")})...',
            'percentage': current_gcal_progress,
            'status': 'running'
        }
        
        try:
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

    final_message = f"Successfully created {events_created_count} events. Failed: {events_failed_count} events."
    if events_created_count == 0 and events_failed_count > 0:
        final_status = 'error'
    elif events_failed_count > 0:
        final_status = 'complete_with_warnings'
    else:
        final_status = 'complete'
    
    session['import_progress'] = {'message': final_message, 'percentage': 100, 'status': final_status}
    flash(final_message, "success" if final_status == 'complete' else "warning")
    
    return redirect(url_for('.index'))

# Need to register this blueprint in app/__init__.py
# Modify app/__init__.py:
# from .routes import main_bp
# app.register_blueprint(main_bp)
