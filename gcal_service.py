import os
import sys  # Added sys import
import datetime
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly"  # Added to list calendars
]

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle (frozen)
        base_path = sys._MEIPASS
    else:
        # Running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

CREDENTIALS_FILE = resource_path('credentials.json')
TOKEN_FILE = resource_path('token.json')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_calendar_service():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE):
        # Ensure SCOPES includes all necessary permissions when loading credentials
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Error refreshing token: {e}. Token scopes: {creds.scopes if creds else 'N/A'}. Required scopes: {SCOPES}")
                # Check if the scopes in the token are a subset of the required SCOPES
                # If not, or if refresh fails for other reasons, force re-authentication.
                if not creds.scopes or not set(SCOPES).issubset(set(creds.scopes)):
                    logging.info("Token scopes do not match required scopes. Forcing re-authentication.")
                os.remove(TOKEN_FILE) # Remove invalid or insufficient token
                creds = None # Force re-authentication
        if not creds: # If still no creds (either never existed or refresh failed)
            if not os.path.exists(CREDENTIALS_FILE):
                logging.error(f"Credentials file '{CREDENTIALS_FILE}' not found. "
                              "Please download it from Google Cloud Console and place it in the project directory.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # Specify a fixed port for the local server
            creds = flow.run_local_server(port=8080) # Or any other available port
        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except HttpError as error:
        logging.error(f"An error occurred building the calendar service: {error}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

def parse_event_time(event_date_str, time_range_str, timezone="America/Toronto"):
    """
    Parses date string and time range string into start and end datetime objects
    with timezone information.
    Example: event_date_str="2025-01-30", time_range_str="09:30 - 10:20"
    """
    try:
        start_time_str, end_time_str = time_range_str.split(" - ")
        
        # Ensure times are in HH:MM format (e.g., "9:30" becomes "09:30")
        start_hour, start_minute = map(int, start_time_str.split(':'))
        end_hour, end_minute = map(int, end_time_str.split(':'))

        start_datetime_naive = datetime.datetime.strptime(f"{event_date_str} {start_hour:02d}:{start_minute:02d}", "%Y-%m-%d %H:%M")
        end_datetime_naive = datetime.datetime.strptime(f"{event_date_str} {end_hour:02d}:{end_minute:02d}", "%Y-%m-%d %H:%M")

        # Format for Google Calendar API (RFC3339)
        # Example: '2025-01-30T09:30:00-05:00' for EST (Toronto)
        # Google Calendar API handles timezone conversion if 'timeZone' field is provided for start and end.
        
        start_formatted = start_datetime_naive.isoformat()
        end_formatted = end_datetime_naive.isoformat()

        return {
            "dateTime": start_formatted,
            "timeZone": timezone,
        }, {
            "dateTime": end_formatted,
            "timeZone": timezone,
        }
    except ValueError as e:
        logging.error(f"Error parsing time string '{time_range_str}' for date '{event_date_str}': {e}")
        return None, None


def create_calendar_event(service, scraped_event_data, calendar_id='primary'):
    """
    Creates a new event in Google Calendar.
    scraped_event_data is a dictionary from the scraper, e.g.:
    {
        "week_of": "2025-01-27",
        "date": "2025-01-30",
        "course": "ENG 1P13",
        "type": "Lecture",
        "time": "09:30 - 10:20",
        "location": "BSB B136"
    }
    """
    if not service:
        logging.error("Calendar service is not available.")
        return None

    event_date_str = scraped_event_data.get("date")
    time_range_str = scraped_event_data.get("time")

    if not event_date_str or not time_range_str:
        logging.error(f"Missing date or time in event data: {scraped_event_data}")
        return None

    start_event_time, end_event_time = parse_event_time(event_date_str, time_range_str)
    if not start_event_time or not end_event_time:
        logging.error(f"Could not parse time for event: {scraped_event_data}")
        return None

    event_summary = f"{scraped_event_data.get('course', 'Event')} - {scraped_event_data.get('type', 'Class')}"
    event_location = scraped_event_data.get('location')
    event_description = (
        f"Course: {scraped_event_data.get('course', 'N/A')}\n"
        f"Type: {scraped_event_data.get('type', 'N/A')}\n"
        f"Scraped from week of: {scraped_event_data.get('week_of', 'N/A')}"
    )

    event_body = {
        "summary": event_summary,
        "location": event_location,
        "description": event_description,
        "start": start_event_time,
        "end": end_event_time,
        # "reminders": { # Optional: Add reminders
        #     "useDefault": False,
        #     "overrides": [
        #         {"method": "popup", "minutes": 10},
        #     ],
        # },
    }

    try:
        logging.info(f"Creating event: {event_summary} on {event_date_str}")
        created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        logging.info(f"Event created: {created_event.get('htmlLink')}")
        return created_event
    except HttpError as error:
        logging.error(f"An error occurred creating event: {error}")
        # Consider more specific error handling, e.g., for 409 (duplicate) if you implement duplicate checking
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during event creation: {e}")
        return None

def list_calendars(service):
    """Lists the user's calendars."""
    if not service:
        logging.error("Calendar service is not available for listing calendars.")
        return []
    try:
        calendar_list = service.calendarList().list().execute()
        return calendar_list.get('items', [])
    except HttpError as error:
        logging.error(f"An error occurred listing calendars: {error}")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while listing calendars: {e}")
        return []

if __name__ == "__main__":
    # This is for testing the gcal_service.py module directly
    # 1. Make sure you have 'credentials.json' from Google Cloud Console
    # 2. Run this script. It will open a browser for you to authenticate.
    # 3. After authentication, 'token.json' will be created.
    
    gcal_service = get_calendar_service()

    if gcal_service:
        logging.info("Successfully connected to Google Calendar API.")
        
        # Example: List next 10 events
        # now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        # print("Getting the upcoming 10 events")
        # events_result = (
        #     gcal_service.events()
        #     .list(
        #         calendarId="primary",
        #         timeMin=now,
        #         maxResults=10,
        #         singleEvents=True,
        #         orderBy="startTime",
        #     )
        #     .execute()
        # )
        # events = events_result.get("items", [])

        # if not events:
        #     print("No upcoming events found.")
        # else:
        #     for event in events:
        #         start = event["start"].get("dateTime", event["start"].get("date"))
        #         print(start, event["summary"])

        # Example: Create a test event (using data similar to what the scraper would provide)
        sample_scraped_event = {
            "week_of": "2025-05-12", # Example week
            "date": "2025-05-15",    # Example date (YYYY-MM-DD)
            "course": "TEST 101",
            "type": "Lecture",
            "time": "14:30 - 15:20", # Example time (HH:MM - HH:MM)
            "location": "My Room"
        }
        
        # Test parsing
        # start_test, end_test = parse_event_time(sample_scraped_event["date"], sample_scraped_event["time"])
        # print(f"Parsed start: {start_test}")
        # print(f"Parsed end: {end_test}")

        # create_calendar_event(gcal_service, sample_scraped_event)

    else:
        logging.error("Failed to connect to Google Calendar API.")
