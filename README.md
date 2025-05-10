# McMaster Schedule Importer

A web application that scrapes your McMaster University course schedule from Mosaic and imports it directly into Google Calendar.

## Features

- **Automated Scraping**: Log in to Mosaic and extract your course schedule automatically.
- **Google Calendar Integration**: Import your classes as events in Google Calendar with proper details.
- **Date Range Selection**: Specify which weeks of the term you want to import.
- **Real-time Progress Updates**: Watch the progress as your schedule is scraped and imported.
- **Error Handling**: Robust error handling with descriptive messages.

## Installation

### Prerequisites

- Python 3.10+ 
- Google Cloud Platform account with Google Calendar API enabled
- Google OAuth 2.0 credentials (for Google Calendar access)

### Setup

1. Clone this repository:
   ```
   git clone <your-repo-url>
   cd schedule-scraper
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Setup Google Cloud OAuth credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop application type)
   - Download the credentials JSON file
   - Rename it to `credentials.json` and place it in the project root directory
   - Ensure http://localhost:8080/ is added as an authorized redirect URI

5. Create a `.env` file in the project root with the following content:
   ```
   MACID_USER=your_macid_username
   MACID_PASS=your_macid_password
   ```
   Note: These will be the default values in the web form but can be overridden.

## Usage

1. Start the application:
   ```
   python run.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000/
   ```

3. Follow the steps in the web interface:
   - Authorize Google Calendar access (you'll only need to do this once)
   - Enter your MacID and password
   - Select the date range for your schedule
   - Click "Import Schedule"
   - Monitor the progress until completion

## Project Structure

```
.
├── app/                      # Flask application
│   ├── __init__.py           # Flask app initialization
│   ├── routes.py             # Web routes
│   ├── static/               # Static assets
│   │   ├── css/              # Stylesheets
│   │   └── js/               # JavaScript files
│   └── templates/            # HTML templates
│       ├── base.html         # Base template
│       └── index.html        # Main page
├── .env                      # Environment variables
├── config.py                 # Configuration settings
├── credentials.json          # Google OAuth credentials
├── gcal_service.py           # Google Calendar API service
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
├── scraper.py                # Mosaic scraping functionality
└── token.json                # Google API authentication token
```

## Development

### Future Improvements

- Add duplicate event detection to avoid creating the same event twice
- Add an option to select which calendar to add events to
- Add event categorization by course type (lectures, labs, tutorials)
- Improve error handling and retry mechanisms
- Add support for different term schedules

## Security Notes

- This application requires your Mosaic credentials to log in and scrape your schedule.
- Credentials are only stored in your local `.env` file and not transmitted beyond the authentication with Mosaic.
- Google Calendar access is obtained through OAuth 2.0, which does not expose your Google password.
- The application requests only the minimum required permissions to create calendar events.

## License

[MIT License](LICENSE)