from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from datetime import datetime, timedelta
import os
import json
import time
import uuid

# Assuming your refactored scraper and gcal_service are in the parent directory
# Adjust the import paths if your project structure is different or if they become packages
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import scraper # Your refactored scraper.py
import gcal_service # Your gcal_service.py
from .task_manager import start_import_task, get_task_progress

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
    """Reset the import progress data."""
    # Generate a unique session ID for tracking this import
    session['import_session_id'] = str(uuid.uuid4())
    return jsonify({'status': 'success'})

@main_bp.route('/get_import_progress')
def get_import_progress():
    """Get the current import progress data."""
    # If no session ID exists, return default "not started" state
    session_id = session.get('import_session_id')
    if not session_id:
        default_data = {'message': 'No import in progress', 'percentage': 0, 'status': 'not_started'}
        return jsonify(default_data)
    
    # Get progress from the task manager
    progress_data = get_task_progress(session_id)
    return jsonify(progress_data)

@main_bp.route('/import_schedule', methods=['POST'])
def import_schedule():
    current_app.logger.info("Import schedule route called.")
    
    if 'import_session_id' not in session:
        session['import_session_id'] = str(uuid.uuid4())
    
    session_id = session['import_session_id']
    
    if not os.path.exists(current_app.config['TOKEN_FILE']):
        current_app.logger.warning("Google Calendar not authorized during import attempt.")
        return jsonify({'status': 'error', 'message': 'Google Calendar not authorized. Please authorize first.'}), 403

    macid = request.form.get('macid')
    password = request.form.get('password')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    if not all([macid, password, start_date_str, end_date_str]):
        current_app.logger.warning("Import failed due to missing fields.")
        return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        current_app.logger.warning("Import failed due to invalid date format.")
        return jsonify({'status': 'error', 'message': 'Invalid date format. Please use YYYY-MM-DD.'}), 400
    
    app = current_app._get_current_object()
    start_import_task(app, session_id, macid, password, start_date, end_date)
    
    current_app.logger.info(f"Import task started for session_id: {session_id}")
    return jsonify({'status': 'success', 'message': 'Import process initiated. Monitoring progress...'})

# Need to register this blueprint in app/__init__.py
# Modify app/__init__.py:
# from .routes import main_bp
# app.register_blueprint(main_bp)
