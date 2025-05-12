# McMaster Schedule Importer

A web application that scrapes your McMaster University course schedule from Mosaic and imports it directly into Google Calendar.


https://github.com/user-attachments/assets/a1a18a10-496c-4392-b997-4abd2f2f9a99


## Features

- **Automated Scraping**: Log in to Mosaic and extract your course schedule automatically.
- **Google Calendar Integration**: Import your classes as events in Google Calendar with proper details.
- **Select Target Google Calendar**: Choose which of your Google Calendars to import the schedule into.
- **Date Range Selection**: Specify which weeks of the term you want to import.
- **Real-time Progress Updates**: Watch the progress as your schedule is scraped and imported.
- **Error Handling**: Robust error handling with descriptive messages.
- **Distributable Executable**: Bundled application for Windows and macOS using PyInstaller, allowing easy execution without a Python environment.
- **Automatic Browser Launch**: The application automatically opens in your default web browser when the executable is run.

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

5. Create a `.env` file in the project root with the following content:
   ```
   MACID_USER=your_macid_username
   MACID_PASS=your_macid_password
   ```
   Note: These will be the default values in the web form but can be overridden.

## Usage

### Running from Source

1. Start the application:
   ```
   python run.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

3. Follow the steps in the web interface:
   - Authorize Google Calendar access (you'll only need to do this once, or if scopes change).
   - Select your target Google Calendar from the dropdown.
   - Enter your MacID and password.
   - Select the date range for your schedule.
   - Click "Import Schedule"
   - Monitor the progress until completion.

### Running the Bundled Executable (MosaicSync.exe)

1.  Download the `MosaicSync.exe` (for Windows) or the corresponding macOS application from the releases page (once available).
2.  Ensure `credentials.json` is in the same directory as the executable, or in a `data` subdirectory if configured that way in the `.spec` file. The first time you run it, `token.json` will be created in the same directory after you authorize with Google.
3.  Double-click the executable. It will start the local server and automatically open the web interface in your default browser (`http://127.0.0.1:5000/`).
4.  Follow the steps in the web interface as outlined above (select calendar, enter credentials, import).
5.  To stop the application, close the terminal window that opened when you launched the executable.

## Project Structure

```
.
├── app/                      # Flask application
│   ├── __init__.py           # Flask app initialization
│   ├── routes.py             # Web routes
│   ├── static/               # Static assets
│   │   ├── css/              # Stylesheets
│   │   └── js/               # JavaScript files
│   ├── templates/            # HTML templates
│   │   ├── base.html         # Base template
│   │   └── index.html        # Main page
│   └── task_manager.py       # Handles background import tasks
├── build/                    # PyInstaller build directory (temporary)
├── dist/                     # PyInstaller output directory (contains executable)
├── .env                      # Environment variables (for development)
├── .gitignore                # Specifies intentionally untracked files
├── config.py                 # Configuration settings
├── credentials.json          # Google OAuth credentials (REQUIRED)
├── gcal_service.py           # Google Calendar API service
├── mosaicsync.ico             # Application icon
├── mosaicsync.spec            # PyInstaller specification file
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
├── scraper.py                # Mosaic scraping functionality
└── token.json                # Google API authentication token (generated after auth)
```

## Building from Source / Creating Executable

This project uses PyInstaller to bundle the Flask application into a standalone executable.

### Prerequisites

- Python 3.10+
- All dependencies from `requirements.txt` installed.
- PyInstaller: `pip install pyinstaller`

### Steps

1.  **Prepare `credentials.json`**: Ensure your `credentials.json` file from Google Cloud Console is in the project root.
2.  **Modify `mosaicsync.spec` (if needed)**:
    *   This file tells PyInstaller how to build the executable.
    *   It includes paths to static files, templates, and `credentials.json`.
    *   The `datas` section is crucial for including non-Python files.
    *   For a production build without a console window (on Windows), you can change `console=True` to `console=False` in the `.spec` file.
3.  **Build the Executable**:
    Open your terminal in the project root directory and run:
    ```bash
    pyinstaller mosaicsync.spec
    ```
    Or, for a one-file executable (may have slower startup):
    ```bash
    pyinstaller --onefile run.py --name MosaicSync --add-data "app/static:app/static" --add-data "app/templates:app/templates" --add-data "credentials.json:." --add-data "mosaicsync.ico:." --windowed --icon=mosaicsync.ico
    ```
    *(Note: The `.spec` file provides more control and is the recommended method for this project due to the `resource_path` function usage).*

4.  **Find the Executable**:
    The bundled application will be in the `dist/MosaicSync` folder (or `dist/MosaicSync.exe` if using `--onefile`).

5.  **Distribution**:
    *   For Windows, distribute the `MosaicSync` folder (or `MosaicSync.exe`). Users will need to place their `credentials.json` alongside the executable (or as configured in the spec). `token.json` will be generated upon first Google authentication.
    *   For macOS, the process is similar. You'll run PyInstaller on a macOS machine. The output will be a `.app` bundle.

## Development

### Future Improvements

- Add duplicate event detection to avoid creating the same event twice
- Add event categorization by course type (lectures, labs, tutorials)
- Improve error handling and retry mechanisms
- Add support for different term schedules
- Package for macOS and Linux

## Security Notes

- This application requires your Mosaic credentials to log in and scrape your schedule.
- Credentials are only stored in your local `.env` file and not transmitted beyond the authentication with Mosaic.
- Google Calendar access is obtained through OAuth 2.0, which does not expose your Google password.
- The application requests only the minimum required permissions to create calendar events.
