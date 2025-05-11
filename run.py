from app import create_app
import webbrowser
import threading
import sys
import os

app = create_app()

def open_browser():
    """Opens the web browser to the application."""
    print("Attempting to open browser to http://127.0.0.1:5000/")
    webbrowser.open_new_tab("http://127.0.0.1:5000/")

if __name__ == '__main__':
    # Explicitly define the intended debug mode for app.run()
    # This will determine how the browser opening is handled.
    INTENDED_DEBUG_MODE = True 

    is_bundled = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
    is_werkzeug_main_process = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if is_bundled:
        if INTENDED_DEBUG_MODE: # If Flask's reloader will be active
            if is_werkzeug_main_process: # Open browser only in the reloaded (main worker) process
                # Delay opening to give the server a chance to start
                print("Debug mode: Werkzeug main process detected, starting browser timer.")
                threading.Timer(3, open_browser).start()
            else:
                print("Debug mode: Initial process, browser will be opened by reloaded process.")
        else: # If not in debug mode (reloader not active)
            print("Non-debug mode: Starting browser timer directly.")
            threading.Timer(3, open_browser).start()
            
    # Important: Using threaded=True to ensure background tasks work properly
    # Note: Using port 5000 for the main Flask app to avoid conflict with
    # Google OAuth flow which will use port 8080 for its temporary local server.
    # Ensure your Google Cloud OAuth redirect URI is set to http://localhost:8080/
    
    # For a distributed .exe, you might want debug=False
    # For now, keeping it as per your current file.
    app.run(debug=INTENDED_DEBUG_MODE, port=5000, threaded=True)
