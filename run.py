from app import create_app

app = create_app()

if __name__ == '__main__':
    # Important: Using threaded=True to ensure background tasks work properly
    # Note: Using port 5000 for the main Flask app to avoid conflict with
    # Google OAuth flow which will use port 8080 for its temporary local server.
    # Ensure your Google Cloud OAuth redirect URI is set to http://localhost:8080/
    app.run(debug=True, port=5000, threaded=True)
